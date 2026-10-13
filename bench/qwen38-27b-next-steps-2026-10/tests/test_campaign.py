import os, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"


def _dry(*args, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("QWEN38_", "FLASHNEXT_"))}
    e.update(env)
    out = subprocess.run(["bash", str(C / "scripts/run-campaign.sh"), "--dry-run", *args],
                         capture_output=True, text=True, env=e)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_dry_run_lists_phases_in_order_and_restarts_driver():
    out = _dry()
    order = [m.group(1) for m in re.finditer(r"^=== phase (P\w)", out, re.M)]
    assert order == ["P0", "P1", "P2", "P3", "P4", "P6", "PQ"]
    assert out.rstrip().splitlines()[-1].startswith("restart daily driver")
    assert "stop daily driver" in "\n".join(out.splitlines()[:3])


def test_every_arm_runs_both_efforts_and_both_bands():
    out = _dry()
    assert re.search(r"FLASHNEXT_EFFORT=xhigh bash \S*run-arm\.sh k27 32768 --repeat 3 --tag p1x", out)
    assert re.search(r"FLASHNEXT_EFFORT=medium bash \S*run-arm\.sh k27 131072 --repeat 3 --tag p1m", out)
    assert re.search(r"FLASHNEXT_EFFORT=xhigh bash \S*run-arm\.sh s27r 131072 --repeat 3 --tag p0x", out)


def test_band_order_alternates():
    out = _dry("--only", "P2")
    lines = [l for l in out.splitlines() if "run-arm.sh" in l and "p2x" in l]
    arms_32 = [l.split("run-arm.sh ")[1].split()[0] for l in lines if " 32768 " in l]
    arms_128 = [l.split("run-arm.sh ")[1].split()[0] for l in lines if " 131072 " in l]
    assert arms_32 == ["o27q8", "o27q4"] and arms_128 == ["o27q4", "o27q8"]


def test_idle_gate_precedes_each_band_and_decide_follows_phase():
    out = _dry("--only", "P1")
    assert out.count("idle-gate.sh --minutes 10") == 2
    assert "decide.py" in out and "--glob k27-*-p1x.jsonl" in out and "--glob s27r-*-p0x.jsonl" in out
    assert "--skip-gates hit_append,hit_tool_turn" in out  # Splash may not report cached_tokens
    assert "empty_answers.py" in out


def test_llama_phase_is_capped_at_64k():
    out = _dry("--only", "P6")
    assert "l27 65536" in out and "131072" not in out  # think probes of P6 also run at 64K


def test_from_skips_earlier_phases():
    out = _dry("--from", "P3")
    assert "=== phase P1" not in out and "=== phase P3" in out


def test_skip_battery_drops_pq():
    assert "=== phase PQ" not in _dry("--skip-battery")


def test_only_pq_runs_only_the_battery():
    out = _dry("--only", "PQ")
    assert [m.group(1) for m in re.finditer(r"^=== phase (P\w)", out, re.M)] == ["PQ"]
    assert "run-arm.sh" not in out


def test_driver_gate_picks_only_arms_within_ratio(tmp_path):
    import json, sys
    sys.path.insert(0, str(C / "scripts")); import driver_gate
    def rows(arm, t32, t128):
        out = []
        for ctx, ttft, dec in ((32768, (t32 - 512 / 60) * 1000, 60.0), (131072, (t128 - 512 / 50) * 1000, 50.0)):
            for s in ("cold", "identical", "append", "tool_turn"):
                out.append({"arm": arm, "context_target": ctx, "scenario": s, "finish_reason": "stop", "error": None,
                            "correct": True, "decode_tps": dec, "ttft_ms": ttft, "cache_hit_ratio": 0.99,
                            "swap_delta_gb": 0.0, "session_id": f"{arm}-{ctx}", "runtime": "x"})
        return out
    for arm, t32, t128 in (("k27", 9.0, 10.0), ("o27q4", 15.0, 20.0)):
        (tmp_path / f"{arm}-32768-t1.0-p1m.jsonl").write_text("\n".join(json.dumps(r) for r in rows(arm, t32, t128) if r["context_target"] == 32768) + "\n")
        (tmp_path / f"{arm}-131072-t1.0-p1m.jsonl").write_text("\n".join(json.dumps(r) for r in rows(arm, t32, t128) if r["context_target"] == 131072) + "\n")
    out = tmp_path / "gates.env"; out.write_text("P1_PASS=1\n")
    assert driver_gate.main(["--results-dir", str(tmp_path), "--w1", "7.9", "8.6", "--ratio", "1.25", "--out", str(out)]) == 0
    assert "P5_GO=k27" in out.read_text() and "P1_PASS=1" in out.read_text()
