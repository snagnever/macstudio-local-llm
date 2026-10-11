import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / "tools" / "scripts" / "serve-flashnext-daily-driver.sh"
SWIFT = "Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"


def _print(*args, extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("FLASHNEXT_")}
    env.update(extra or {})
    return subprocess.run(["bash", str(LAUNCHER), *args, "--print"], capture_output=True, text=True,
                          env=env, check=True).stdout


def test_daily_default_is_swift15_pack():
    # Promovido pela campanha bench/swift15-flashnext-2026-10 (G1, G2 e G3 passam).
    assert SWIFT in _print()


def test_model_override_still_wins():
    assert "/tmp/other-pack" in _print(extra={"FLASHNEXT_MODEL": "/tmp/other-pack"})
