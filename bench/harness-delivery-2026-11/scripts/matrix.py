"""Order of the session matrix, resume, and the loop that runs it.

usage: matrix.py --packs k2,z4 [--harnesses claude,opencode,dsh,pi] [--dry-run] [--out DIR] [--logs DIR]

Repetition 1 runs the first pack and then the second; repetition 2 runs them in the reverse order. Inside a
pack block the tasks go a b c d T1 T5 T7, and task i starts with harness i mod n. A session that already has
a record does not run again. The rig serves one pack at a time: the loop asks rig-server.sh to switch packs
between blocks and to stop at the end, which restarts the user's own server.
The matrix runs on the rig, next to the server. Set RIG_SSH (user@host) to drive the rig from another machine;
then RIG_HOST (default mac-studio) and RIG_REPO (the rig checkout) apply.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import harness
import run_session
import tasks
from harness import Target

HERE = Path(__file__).resolve().parents[1]

def rig_argv(*args: str) -> list[str]:
    """How to call rig-server.sh: directly (the matrix runs on the rig), or over ssh when RIG_SSH is set."""
    ssh = os.environ.get("RIG_SSH")
    if not ssh:
        return ["bash", str(HERE / "scripts" / "rig-server.sh"), *args]
    repo = os.environ.get("RIG_REPO", "LocalProjects/macstudio-local-llm-swiftunc")
    return ["ssh", "-o", "BatchMode=yes", ssh, "bash",
            f"{repo}/bench/harness-delivery-2026-11/scripts/rig-server.sh", *args]


def rig_host() -> str:
    """Host the harnesses use to reach the server."""
    return os.environ.get("RIG_HOST") or ("mac-studio" if os.environ.get("RIG_SSH") else "127.0.0.1")


@dataclass(frozen=True)
class Session:
    pack: str
    harness: str
    task: str
    rep: int


def order(packs: tuple[str, str], harnesses: tuple[str, ...], out: Path) -> list[Session]:
    """Every session still to run, in run order."""
    sessions = []
    for rep, block in ((1, packs), (2, packs[::-1])):
        for pack in block:
            for i, task in enumerate(tasks.TASKS):
                for j in range(len(harnesses)):
                    sessions.append(Session(pack, harnesses[(i + j) % len(harnesses)], task, rep))
    return [s for s in sessions if not run_session.record_path(out, s.pack, s.harness, s.task, s.rep).is_file()]


def _rig(*args: str, timeout: int = 900) -> str:
    r = subprocess.run(rig_argv(*args), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"rig-server.sh {' '.join(args)} failed: {r.stdout[-400:]}{r.stderr[-400:]}")
    return r.stdout


def switch_server(pack: str) -> Target:
    """Serve pack on the rig and return where it listens."""
    env = dict(line.split("=", 1) for line in _rig("start", pack).splitlines() if "=" in line)
    port = int(env["BASE_URL"].rstrip("/").removesuffix("/v1").rsplit(":", 1)[1])
    return Target(rig_host(), port, env["MODEL_ID"])


def stop_server() -> None:
    _rig("stop")


def run_matrix(packs: tuple[str, str], harnesses: tuple[str, ...], out: Path, logs: Path,
               switch: Callable[[str], Target] = switch_server, run: Callable[..., dict] = run_session.run,
               stop: Callable[[], None] = stop_server, log=print) -> int:
    """Run every pending session. Returns how many ran. Always stops the rig server at the end."""
    pending = order(packs, harnesses, out)
    current, target, n = None, None, 0
    try:
        for s in pending:
            if s.pack != current:
                target, current = switch(s.pack), s.pack
                log(f"=== {time.strftime('%F %T')} pack {s.pack} -> {target.url} {target.model_id}")
            r = run(s.harness, s.task, s.pack, s.rep, target, out, logs)
            n += 1
            log(f"{time.strftime('%F %T')} {n}/{len(pending)} {s.pack} {s.harness} {s.task} r{s.rep} "
                f"done={r['task_done']} wall={r['wall_s']} timeout={r['timeout']}")
    finally:
        stop()
    return n


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--packs", required=True, help="base,candidate")
    ap.add_argument("--harnesses", default=",".join(harness.HARNESSES))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=HERE / "results")
    ap.add_argument("--logs", type=Path, default=HERE / "logs")
    a = ap.parse_args(argv)
    packs, names = tuple(a.packs.split(",")), tuple(a.harnesses.split(","))
    if len(packs) != 2 or any(n not in harness.HARNESSES for n in names):
        ap.error("--packs takes two packs; --harnesses takes names from " + ",".join(harness.HARNESSES))
    if a.dry_run:
        for s in order(packs, names, a.out):
            print(s.pack, s.harness, s.task, f"r{s.rep}")
        return 0
    run_matrix(packs, names, a.out, a.logs, log=lambda m: print(m, flush=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
