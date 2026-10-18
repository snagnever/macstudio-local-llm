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


def test_daily_passes_no_max_concurrent_by_default():
    # bench/flashnext-concurrency-2026-10: 26.10.1 already batches decode with its default of 1.
    assert "--max-concurrent" not in _print()


def test_max_concurrent_override_reaches_daily_command():
    assert "--max-concurrent 2" in _print(extra={"FLASHNEXT_MAX_CONCURRENT": "2"})


def test_256k_profile_uses_the_measured_two_session_config():
    out = _print("256k")
    assert "--ctx-size 262144" in out and "--max-concurrent 2" in out
    assert "--prefix-cache-mem 4GB" in out and "16GB" not in out and "--kv-quant" not in out


def test_512k_profile_forces_one_slot_even_with_override():
    out = _print("512k", extra={"FLASHNEXT_MAX_CONCURRENT": "2"})
    assert "--max-concurrent 1" in out and "--max-concurrent 2" not in out
