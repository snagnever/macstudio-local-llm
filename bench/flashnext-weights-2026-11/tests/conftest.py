import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def _env():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "PARALLEL_", "SPLASH_", "http_", "HTTP_"))}


def show_arm(arm, extra_env=None):
    env = _env() | (extra_env or {})
    return subprocess.run(["bash", str(HERE / "scripts" / "run-arm.sh"), arm, "262144", "--print"],
                          capture_output=True, text=True, env=env, check=True).stdout
