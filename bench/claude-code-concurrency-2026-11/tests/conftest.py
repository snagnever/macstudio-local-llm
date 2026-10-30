import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SCRIPTS = HERE / "scripts"
REPO = HERE.parents[1]
RUN_CANDIDATE = REPO / "bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh"


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "PARALLEL_", "SPLASH_"))}
    env.update(extra or {})
    return env


def run(*args, env=None, check=True):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True,
                          env=env or clean_env(), check=check)


def run_candidate_print(arm, ctx, env_extra=None):
    return run("bash", RUN_CANDIDATE, arm, ctx, "--tag", "r1", "--print", env=clean_env(env_extra)).stdout
