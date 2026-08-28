#!/usr/bin/env python3
"""Small persistent watchdog for the Qwen3.8 benchmark stage queue."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional


CAMPAIGN = Path(__file__).resolve().parents[1]
DEFAULT_STATE = CAMPAIGN / "logs" / "campaign-supervisor-state.json"
DEFAULT_LOG_DIR = CAMPAIGN / "logs" / "supervised"
DEFAULT_STAGES = (
    "omlx-oq8e-smoke",
    "mtplx-smoke",
    "mtplx-32k",
    "omlx-oq4e-dflash-32k",
    "specprefill-16k",
    "specprefill-32k",
    "ane-16k",
    "ane-32k",
    "dspark-smoke",
    "dspark-decode-8k",
    "dspark-cache-32k",
    "dspark-decode-32k",
    "cache-65k",
    "tool-loop",
    "native-262k",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")


class ScreenClient:
    def __init__(self, binary: str, wrapper: Path, cwd: Path):
        self.binary = binary
        self.wrapper = wrapper
        self.cwd = cwd

    def list_sessions(self) -> set[str]:
        result = subprocess.run(
            [self.binary, "-ls"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        listing = f"{result.stdout}\n{result.stderr}"
        return set(re.findall(r"\d+\.([^\s]+)\s+\(", listing))

    def launch(self, session: str, stage: str, log_path: Path, exit_path: Path) -> None:
        environment = os.environ.copy()
        environment.pop("STY", None)
        subprocess.run(
            [
                self.binary,
                "-dmS",
                session,
                "bash",
                str(self.wrapper),
                stage,
                str(log_path),
                str(exit_path),
            ],
            cwd=self.cwd,
            env=environment,
            check=True,
        )


class Supervisor:
    def __init__(
        self,
        *,
        state_path: Path,
        log_dir: Path,
        stages: list[str],
        screen,
        session_prefix: str = "qwen38-campaign",
        ignored_sessions: Optional[set[str]] = None,
        now: Callable[[], str] = utc_now,
    ):
        if not stages:
            raise ValueError("the supervised stage queue cannot be empty")
        self.state_path = state_path
        self.log_dir = log_dir
        self.stages = stages
        self.screen = screen
        self.session_prefix = session_prefix
        self.ignored_sessions = ignored_sessions or set()
        self.now = now

    def _initial_state(self) -> dict:
        return {
            "schema_version": 1,
            "stages": self.stages,
            "current_index": 0,
            "completed_stages": [],
            "status": "idle",
            "stage": self.stages[0],
            "attempt": 0,
            "last_check_at": None,
            "stalled_checks": 0,
        }

    def _load(self) -> dict:
        if not self.state_path.exists():
            return self._initial_state()
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("stages") != self.stages:
            raise ValueError(
                "the persisted supervisor queue differs from --stages; "
                "use a new state path or resolve the existing state first"
            )
        return state

    def _save(self, state: dict) -> dict:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.state_path)
        return state

    @contextmanager
    def _lock(self):
        lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _external_sessions(self, sessions: Iterable[str], managed: Optional[str]) -> list[str]:
        return sorted(
            session
            for session in sessions
            if session.startswith("qwen38-")
            and session != managed
            and session not in self.ignored_sessions
        )

    def _launch(self, state: dict, sessions: set[str]) -> dict:
        index = int(state["current_index"])
        if index >= len(self.stages):
            state.update(
                status="complete",
                stage=None,
                session=None,
                completed_at=self.now(),
                last_check_at=self.now(),
            )
            return self._save(state)

        external = self._external_sessions(sessions, state.get("session"))
        if external:
            state.update(
                status="external_busy",
                stage=self.stages[index],
                external_sessions=external,
                last_check_at=self.now(),
            )
            return self._save(state)

        stage = self.stages[index]
        attempt = int(state.get("attempt") or 0) + 1
        stem = f"{index + 1:02d}-{_slug(stage)}-a{attempt}"
        session = f"{self.session_prefix}-{index + 1:02d}-{_slug(stage)}"
        log_path = self.log_dir / f"{stem}.log"
        exit_path = self.log_dir / f"{stem}.exit"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.screen.launch(session, stage, log_path, exit_path)
        state.update(
            status="running",
            stage=stage,
            attempt=attempt,
            session=session,
            log_path=str(log_path),
            exit_path=str(exit_path),
            log_size=log_path.stat().st_size if log_path.exists() else 0,
            stalled_checks=0,
            started_at=self.now(),
            last_check_at=self.now(),
            external_sessions=[],
            exit_code=None,
            message=None,
        )
        return self._save(state)

    def _finish(self, state: dict, exit_code: int, sessions: set[str]) -> dict:
        state["exit_code"] = exit_code
        state["last_check_at"] = self.now()
        if exit_code != 0:
            state.update(
                status="needs_agent_review",
                message=(
                    f"stage {state.get('stage')} exited with {exit_code}; "
                    "automatic retry is disabled to preserve partial measurements"
                ),
            )
            return self._save(state)

        completed = list(state.get("completed_stages") or [])
        if state.get("stage") not in completed:
            completed.append(state.get("stage"))
        state.update(
            completed_stages=completed,
            current_index=int(state["current_index"]) + 1,
            status="idle",
            stage=None,
            session=None,
            attempt=0,
            finished_at=self.now(),
            stalled_checks=0,
        )
        self._save(state)
        return self._launch(state, sessions)

    def once(self) -> dict:
        with self._lock():
            state = self._load()
            sessions = self.screen.list_sessions()
            managed = state.get("session")
            exit_path = Path(state["exit_path"]) if state.get("exit_path") else None

            if managed and managed in sessions:
                log_path = Path(state["log_path"])
                size = log_path.stat().st_size if log_path.exists() else 0
                previous_size = int(state.get("log_size") or 0)
                stalled = int(state.get("stalled_checks") or 0)
                stalled = stalled + 1 if size <= previous_size else 0
                state.update(
                    status=("running_stalled" if stalled >= 3 else "running"),
                    log_size=size,
                    stalled_checks=stalled,
                    last_check_at=self.now(),
                    message=(
                        "no log growth for three supervisor intervals; process left running"
                        if stalled >= 3
                        else None
                    ),
                )
                return self._save(state)

            if exit_path and exit_path.exists():
                try:
                    exit_code = int(exit_path.read_text(encoding="utf-8").strip())
                except ValueError:
                    state.update(
                        status="needs_agent_review",
                        last_check_at=self.now(),
                        message=f"invalid exit marker: {exit_path}",
                    )
                    return self._save(state)
                return self._finish(state, exit_code, sessions)

            if managed and state.get("status") in {"running", "running_stalled"}:
                state.update(
                    status="needs_agent_review",
                    last_check_at=self.now(),
                    message=f"screen session {managed} vanished without an exit marker",
                )
                return self._save(state)

            if state.get("status") == "needs_agent_review":
                state["last_check_at"] = self.now()
                return self._save(state)

            return self._launch(state, sessions)

    def retry(self) -> dict:
        """Acknowledge a reviewed failure and start a fresh numbered attempt."""
        with self._lock():
            state = self._load()
            if state.get("status") != "needs_agent_review":
                raise ValueError("retry requires status=needs_agent_review")
            sessions = self.screen.list_sessions()
            managed = state.get("session")
            if managed and managed in sessions:
                raise RuntimeError(f"managed session is still active: {managed}")
            state.update(
                status="idle",
                session=None,
                log_path=None,
                exit_path=None,
                exit_code=None,
                message="review acknowledged; starting a fresh attempt",
                last_check_at=self.now(),
            )
            self._save(state)
            return self._launch(state, sessions)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("once", "loop", "retry", "status"))
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--interval", type=int, default=1200)
    parser.add_argument(
        "--stages",
        default=",".join(DEFAULT_STAGES),
        help="comma-separated run-campaign.sh stage queue",
    )
    parser.add_argument("--screen-bin", default="screen")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stages = [stage.strip() for stage in args.stages.split(",") if stage.strip()]
    screen = ScreenClient(
        args.screen_bin,
        CAMPAIGN / "scripts" / "run-supervised-stage.sh",
        CAMPAIGN.parents[1],
    )
    supervisor = Supervisor(
        state_path=args.state,
        log_dir=args.log_dir,
        stages=stages,
        screen=screen,
        ignored_sessions={"qwen38-supervisor20", "qwen38-monitor20"},
    )

    if args.command == "status":
        state = supervisor._load()
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0
    if args.command == "once":
        print(json.dumps(supervisor.once(), indent=2, sort_keys=True))
        return 0
    if args.command == "retry":
        print(json.dumps(supervisor.retry(), indent=2, sort_keys=True))
        return 0
    if args.interval <= 0:
        raise ValueError("--interval must be greater than zero")

    while True:
        started = time.monotonic()
        try:
            state = supervisor.once()
            print(json.dumps(state, sort_keys=True), flush=True)
        except Exception as error:  # keep the watchdog alive for agent inspection
            print(f"supervisor check failed: {error}", file=sys.stderr, flush=True)
        elapsed = time.monotonic() - started
        time.sleep(max(1.0, args.interval - elapsed))


if __name__ == "__main__":
    raise SystemExit(main())
