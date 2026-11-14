"""One session: a fresh copy of the task repository, one harness with a time limit, the hidden check, one record.

usage: run_session.py --harness H --task T --pack P --rep N --host HOST --port PORT --model ID
                      [--limit-s S] [--out DIR] [--logs DIR]

The record (results/sessions/<pack>-<harness>-<task>-r<rep>.json) holds no session text. The transcript, the
repository copy and the session HOME stay under logs/.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import checks
import harness
import tasks
from harness import Target

HERE = Path(__file__).resolve().parents[1]
FIELDS = {"harness", "harness_version", "pack", "task", "rep", "model_id", "task_done", "steps_passed", "cheat",
          "wall_s", "exit", "timeout", "claimed_done", "turns", "input_tokens", "output_tokens"}
GRACE_S = 10


def session_name(pack: str, name: str, task: str, rep: int) -> str:
    return f"{pack}-{name}-{task}-r{rep}"


def record_path(out: Path, pack: str, name: str, task: str, rep: int) -> Path:
    return Path(out) / "sessions" / f"{session_name(pack, name, task, rep)}.json"


def _kill_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def _execute(cmd: harness.Cmd, log: Path, limit_s: int) -> tuple[int | None, bool, float]:
    """Run the harness in its own process group. Returns (exit code, timed out, wall seconds)."""
    t0 = time.monotonic()
    with log.open("wb") as fh:
        try:
            proc = subprocess.Popen(cmd.argv, cwd=cmd.cwd, env=cmd.env, stdin=subprocess.DEVNULL, stdout=fh,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            fh.write(f"run_session: cannot start {cmd.argv[0]}: {exc}\n".encode())
            return None, False, 0.0
        timed_out = False
        try:
            proc.wait(timeout=limit_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=GRACE_S)
            except subprocess.TimeoutExpired:
                pass
        wall = time.monotonic() - t0
        _kill_group(proc.pid, signal.SIGKILL)  # children the harness left behind
        proc.wait()
    return (None if timed_out else proc.returncode), timed_out, wall


def _usage(name: str, log: Path) -> dict:
    """Turns and tokens when the harness prints them. Claude Code: the last stream-json result object."""
    usage = {"turns": None, "input_tokens": None, "output_tokens": None}
    if name != "claude":
        return usage
    for line in reversed(log.read_text(errors="replace").splitlines()):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("type") == "result":
            u = obj.get("usage") or {}
            cached = (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
            usage.update(turns=obj.get("num_turns"), output_tokens=u.get("output_tokens"),
                         input_tokens=(u.get("input_tokens") or 0) + cached if u else None)
            break
    return usage


def _check(task: str, repo: Path, home: Path) -> checks.CheckResult:
    """Run the hidden check in the same sandbox as the session: it executes code the session wrote."""
    spec = tasks.TASKS[task]
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    cmd = harness.sandboxed(
        harness.Cmd([sys.executable, str(HERE / "scripts" / "checks.py"), task, str(repo)], env, repo),
        read=(HERE / "scripts", spec.repo_src, tasks.CLAUDE_TASKS, Path(sys.prefix), Path(sys.base_prefix)))
    try:
        out = subprocess.run(cmd.argv, cwd=cmd.cwd, env=cmd.env, capture_output=True, text=True, timeout=1800)
        return checks.CheckResult(**json.loads(out.stdout.strip().splitlines()[-1]))
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError, TypeError):
        return checks.CheckResult(task_done=False, cheat=["check_failed"])


def run(name: str, task: str, pack: str, rep: int, target: Target, out: Path, logs: Path,
        limit_s: int | None = None) -> dict:
    """Run one session and write its record. Returns the record."""
    spec = tasks.TASKS[task]
    sid = session_name(pack, name, task, rep)
    out, logs = Path(out), Path(logs)
    repo, home, log = logs / "work" / sid, logs / "home" / sid, logs / "sessions" / f"{sid}.log"
    for d in (repo, home):
        shutil.rmtree(d, ignore_errors=True)
    for d in (repo.parent, home, log.parent, record_path(out, pack, name, task, rep).parent):
        d.mkdir(parents=True, exist_ok=True)
    tasks.fresh_copy(task, repo)
    # Own git root: a harness that looks upward must stop at the copy, not at the campaign repository.
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    harness.prepare(name, home, target)
    cmd = harness.sandboxed(harness.command(name, tasks.prompt(task), repo, home, target))
    code, timed_out, wall = _execute(cmd, log, spec.limit_s if limit_s is None else limit_s)
    result = _check(task, repo, home)
    record = {"harness": name, "harness_version": harness.version(name), "pack": pack, "task": task, "rep": rep,
              "model_id": target.model_id, "task_done": result.task_done, "steps_passed": result.steps_passed,
              "cheat": result.cheat, "wall_s": round(wall, 1), "exit": code, "timeout": timed_out,
              "claimed_done": not timed_out and code == 0, **_usage(name, log)}
    record_path(out, pack, name, task, rep).write_text(json.dumps(record, indent=1) + "\n")
    return record


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--harness", required=True, choices=harness.HARNESSES)
    ap.add_argument("--task", required=True, choices=sorted(tasks.TASKS))
    ap.add_argument("--pack", required=True)
    ap.add_argument("--rep", required=True, type=int)
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", required=True, type=int)
    ap.add_argument("--model", required=True)
    ap.add_argument("--limit-s", type=int)
    ap.add_argument("--out", type=Path, default=HERE / "results")
    ap.add_argument("--logs", type=Path, default=HERE / "logs")
    a = ap.parse_args(argv)
    record = run(a.harness, a.task, a.pack, a.rep, Target(a.host, a.port, a.model), a.out, a.logs, a.limit_s)
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
