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


# --- fix round 1 -------------------------------------------------------------------------------

def _lib(script: str, results: Path) -> str:
    """Source run-campaign.sh in library mode (functions only), point R at a temp dir, run script."""
    e = {k: v for k, v in os.environ.items() if not k.startswith(("QWEN38_", "FLASHNEXT_"))}
    e["QWEN38_CAMPAIGN_LIB"] = "1"
    src = f'source "{C}/scripts/run-campaign.sh"; R="{results}"; {script}'
    out = subprocess.run(["/bin/bash", "-c", src], capture_output=True, text=True, env=e)
    assert out.returncode == 0, out.stderr
    return out.stdout


def _jsonl(path: Path, n: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join('{"x": %d}\n' % i for i in range(n)))


def test_medium_and_xhigh_go_to_separate_decide_calls():
    out = _dry("--only", "P1")
    decide = [l for l in out.splitlines() if "decide.py" in l]
    assert not [l for l in decide if "p1m" in l and "p1x" in l]
    assert any("--glob k27-*-p1m.jsonl" in l and "(medium)" in l and "--ctx 32768,131072" in l for l in decide)
    assert any("--glob k27-*-p1x.jsonl" in l and "(xhigh)" in l and "--base" not in l for l in decide)


def test_campaign_passes_skip_gates_arms_to_driver_gate():
    assert "driver_gate.py" in _dry() and "--skip-gates-arms k27,l27,l27n" in _dry()


def test_have_result_needs_13_lines(tmp_path):
    _jsonl(tmp_path / "k27-32768-t1.0-p1x.jsonl", 12)
    _jsonl(tmp_path / "k27-131072-t1.0-p1x.jsonl", 13)
    out = _lib("have_result k27 32768 p1x && echo A; have_result k27 131072 p1x && echo B; "
               "have_result k27 65536 p1x && echo C; true", tmp_path)
    assert out.split() == ["B"]


def test_idle_gate_does_not_sleep_after_last_failure(tmp_path):
    out = _lib('run() { return 1; }; say() { :; }; sleep() { echo slept; }; idle_gate; echo rc=$?', tmp_path)
    assert out.split() == ["slept", "slept", "rc=75"]


def _p4(tmp_path, bands):
    for ctx in bands:
        _jsonl(tmp_path / f"o27q4-{ctx}-t1.0-p2x.jsonl", 13)
    stubs = ('run() { echo "run: $*"; }; run_arm() { echo "arm $1 $2 $3"; }; run_think() { :; }; '
             'idle_gate() { return 0; }; gate_set() { echo "gate $1=$2"; }; say() { echo "$*"; }; ')
    return _lib(stubs + "run_phase P4", tmp_path)


def test_p4_runs_when_o27q4_p2x_complete_on_both_bands(tmp_path):
    out = _p4(tmp_path, (32768, 131072))
    assert "arm o27sw 131072 p4x" in out and "P4 skipped" not in out


def test_p4_skipped_when_o27q4_p2x_incomplete(tmp_path):
    out = _p4(tmp_path, (32768,))
    assert "P4 skipped" in out and "arm o27sw" not in out and "gate P4_PASS=skipped" in out


def test_battery_skips_labels_already_done(tmp_path):
    _jsonl(tmp_path / "q/t1/o27q4-medium/humaneval.jsonl", 1)
    _jsonl(tmp_path / "q/t1/o27q4-xhigh/gpqa.jsonl", 1)
    _jsonl(tmp_path / "q/t1/o27sw-xhigh/gpqa.jsonl", 1)
    stubs = ('run() { echo "run: $*"; }; idle_gate() { echo idle; }; pause() { :; }; gate_get() { :; }; '
             'say() { echo "$*"; }; ')
    out = _lib(stubs + "run_battery", tmp_path)
    battery = [l for l in out.splitlines() if "run-battery.sh" in l]
    assert not [l for l in battery if " o27q4 " in l]
    assert len(battery) == 1 and "o27sw q --effort medium" in battery[0]
    assert out.count("idle") == 1  # o27q4 is fully done: no idle-gate for it


def _driver_rows(arm, t32, t128, hit=0.99, swap=0.0):
    out = []
    for ctx, ttft, dec in ((32768, (t32 - 512 / 60) * 1000, 60.0), (131072, ((t128 or 0) - 512 / 50) * 1000, 50.0)):
        if t128 is None and ctx == 131072:
            continue
        for s in ("cold", "identical", "append", "tool_turn"):
            out.append({"arm": arm, "context_target": ctx, "scenario": s, "finish_reason": "stop", "error": None,
                        "correct": True, "decode_tps": dec, "ttft_ms": ttft, "cache_hit_ratio": hit,
                        "swap_delta_gb": swap, "session_id": f"{arm}-{ctx}", "runtime": "x"})
    return out


def _driver_gate(tmp_path, arms, *extra):
    import json, sys
    sys.path.insert(0, str(C / "scripts")); import driver_gate
    for arm, t32, t128, kw in arms:
        for ctx in (32768, 131072):
            rs = [r for r in _driver_rows(arm, t32, t128, **kw) if r["context_target"] == ctx]
            if rs:
                (tmp_path / f"{arm}-{ctx}-t1.0-p1m.jsonl").write_text("\n".join(json.dumps(r) for r in rs) + "\n")
    out = tmp_path / "gates.env"
    assert driver_gate.main(["--results-dir", str(tmp_path), "--w1", "7.9", "8.6", "--ratio", "1.25",
                             *extra, "--out", str(out)]) == 0
    return out.read_text()


def test_driver_gate_ignores_hit_gates_only_for_listed_arms(tmp_path):
    arms = [("k27", 8.0, 9.0, {"hit": 0.0}), ("o27q4", 15.0, 20.0, {})]
    assert "P5_GO=0" in _driver_gate(tmp_path, arms)
    assert "P5_GO=k27" in _driver_gate(tmp_path, arms, "--skip-gates-arms", "k27,l27,l27n")
    assert "P5_GO=0" in _driver_gate(tmp_path, arms, "--skip-gates-arms", "l27")


def test_driver_gate_excludes_arm_with_non_hit_failed_gate(tmp_path):
    arms = [("k27", 8.0, 9.0, {"swap": 2.0})]
    assert "P5_GO=0" in _driver_gate(tmp_path, arms, "--skip-gates-arms", "k27")


def test_driver_gate_excludes_arm_without_128k(tmp_path):
    arms = [("k27", 8.0, None, {})]
    assert "P5_GO=0" in _driver_gate(tmp_path, arms)
