import json, subprocess, sys
from pathlib import Path

C = Path(__file__).resolve().parents[1]
SCRIPT = C / "scripts/smoke_check.py"


def _run(tmp_path, rows, boot, mode="dflash", min_decode=60, make_boot=True):
    j = tmp_path / "s.jsonl"
    j.write_text("".join(json.dumps(r) + "\n" for r in rows))
    b = tmp_path / "boot.log"
    if make_boot:
        b.write_text(boot)
    out = subprocess.run([sys.executable, str(SCRIPT), "--jsonl", str(j), "--boot-log", str(b),
                          "--mode", mode, "--min-decode", str(min_decode)], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


GOOD = [{"decode_tps": 70.0, "reasoning_chars": 40}, {"decode_tps": 80.0, "reasoning_chars": 12},
        {"decode_tps": 90.0, "reasoning_chars": 7}]
BOOT = "x\n  [spec-stats] lazy=0/0\n  [spec-stats] mode=dflash attempts=3 accepts=9\n"


def test_pass(tmp_path):
    rc, msg = _run(tmp_path, GOOD, BOOT)
    assert rc == 0 and msg.startswith("ok") and len(msg.splitlines()) == 1


def test_zero_reasoning_fails(tmp_path):
    rc, msg = _run(tmp_path, GOOD + [{"decode_tps": 80.0, "reasoning_chars": 0}], BOOT)
    assert rc == 1 and "reasoning" in msg


def test_missing_spec_stats_fails(tmp_path):
    rc, msg = _run(tmp_path, GOOD, "[spec-stats] lazy=0/0\n")
    assert rc == 1 and "spec-stats" in msg


def test_missing_boot_log_fails(tmp_path):
    rc, msg = _run(tmp_path, GOOD, "", make_boot=False)
    assert rc == 1 and "boot log" in msg


def test_wrong_mode_fails(tmp_path):
    rc, msg = _run(tmp_path, GOOD, BOOT, mode="mtp")
    assert rc == 1 and "mode" in msg


def test_median_decode_below_min_fails(tmp_path):
    rows = [{"decode_tps": d, "reasoning_chars": 5} for d in (10.0, 50.0, 90.0)]
    rc, msg = _run(tmp_path, rows, BOOT)
    assert rc == 1 and "decode" in msg
    rc, _ = _run(tmp_path, rows, BOOT, min_decode=50)
    assert rc == 0


def test_empty_or_missing_jsonl_fails(tmp_path):
    rc, msg = _run(tmp_path, [], BOOT)
    assert rc == 1 and "no records" in msg
    out = subprocess.run([sys.executable, str(SCRIPT), "--jsonl", str(tmp_path / "nope.jsonl"),
                          "--boot-log", str(tmp_path / "b"), "--mode", "mtp", "--min-decode", "60"],
                         capture_output=True, text=True)
    assert out.returncode == 1 and "no records" in out.stdout
