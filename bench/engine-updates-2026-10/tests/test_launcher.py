import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LAUNCHER = REPO / "tools" / "scripts" / "serve-flashnext-daily-driver.sh"


def _print(profile):
    return subprocess.run(["bash", str(LAUNCHER), profile, "--print"],
                          capture_output=True, text=True, check=True).stdout


def test_512k_profile_uses_kv4():
    # KV 8-bit a 512K recusava prefill (PrefillDoesNotFit) às vezes; KV 4-bit passou 3 reps sem recusa (n2q4).
    out = _print("512k")
    assert "--kv-quant 4" in out and "--kv-quant 8" not in out
    assert "--ctx-size 524288" in out


def test_daily_profile_has_no_kv_quant():
    assert "--kv-quant" not in _print("daily")
