import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SCRIPTS = HERE / "scripts"
REPO = HERE.parents[1]
RUN_CANDIDATE = REPO / "bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh"
sys.path.insert(0, str(SCRIPTS))


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "PARALLEL_"))}
    env.update(extra or {})
    return env


def run(*args, env=None, check=True):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True,
                          env=env or clean_env(), check=check)


def run_candidate_print(arm, ctx, *extra):
    return run("bash", RUN_CANDIDATE, arm, ctx, "--repeat", "3", "--tag", "e1", *extra, "--print").stdout
