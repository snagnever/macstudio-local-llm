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
    assert order == ["P0", "P1", "P3", "P7", "PQ"]
    assert out.rstrip().splitlines()[-1].startswith("restart daily driver")
    assert "stop daily driver" in "\n".join(out.splitlines()[:3])


def test_every_arm_runs_both_efforts_and_both_bands():
    out = _dry()
    assert re.search(r"FLASHNEXT_EFFORT=xhigh bash \S*run-arm\.sh k27 32768 --repeat 3 --tag p1x", out)
    assert re.search(r"FLASHNEXT_EFFORT=medium bash \S*run-arm\.sh k27 131072 --repeat 3 --tag p1m", out)
    assert re.search(r"FLASHNEXT_EFFORT=xhigh bash \S*run-arm\.sh s27r 131072 --repeat 3 --tag p0x", out)


def test_band_order_alternates():
    out = _dry("--only", "P8")
    lines = [l for l in out.splitlines() if "run-arm.sh" in l and "p8x" in l]
    arms_32 = [l.split("run-arm.sh ")[1].split()[0] for l in lines if " 32768 " in l]
    arms_128 = [l.split("run-arm.sh ")[1].split()[0] for l in lines if " 131072 " in l]
    assert arms_32 == ["r27m", "w27m"] and arms_128 == ["w27m", "r27m"]


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


def test_p4_skipped_when_its_base_is_in_no_phase(tmp_path):
    # scope B: P2 holds only o27q8, so P4's base o27q4 belongs to no phase
    out = _p4(tmp_path, (32768, 131072))
    assert "P4 skipped: base o27q4 is in no phase" in out and "arm o27sw" not in out


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


# --- task 5b: P7/P8 (Swift 1.5 on mlx-serve), 8K smoke, new order ---

def test_p3_has_only_r27d_and_p8_pairs_r27m_with_w27m():
    p3, p8 = _dry("--only", "P3"), _dry("--only", "P8")
    assert "run-arm.sh r27d 32768" in p3 and "r27m" not in p3
    assert "r27m" in p8 and "w27m" in p8


def test_smoke_runs_before_first_band_of_p7_and_p8():
    p7, p8 = _dry("--only", "P7"), _dry("--only", "P8")
    assert "smoke w27d 8192 p7s" in p7 and "smoke w27m 8192 p8s" in p8
    assert re.search(r"FLASHNEXT_EFFORT=medium bash \S*run-arm\.sh w27d 8192 --repeat 1 --tag p7s", p7)
    assert "smoke_check.py" in p7 and "--mode dflash" in p7 and "--min-decode 60" in p7
    assert "--mode mtp" in p8 and "--min-decode 40" in p8
    assert p7.index("smoke w27d 8192 p7s") < p7.index("idle-gate.sh") < p7.index("--tag p7x")
    assert p8.index("smoke w27m 8192 p8s") < p8.index("--tag p8x")


def test_p7_decision_uses_r27d_base_glob_p3x():
    d = [l for l in _dry("--only", "P7").splitlines() if "decide.py" in l and "--base" in l]
    assert d and "--base r27d" in d[0] and "--threshold 1.03" in d[0]
    assert "--glob r27d-*-p3x.jsonl" in d[0] and "--glob w27d-*-p7x.jsonl" in d[0]


def _smoke_phase(tmp_path, phase, check_rc):
    for ctx in (32768, 131072):
        _jsonl(tmp_path / f"r27d-{ctx}-t1.0-p3x.jsonl", 13)  # P7 base
    stubs = ('run() { echo "run: $*"; case "$*" in *smoke_check*) return %d;; esac; }; '
             'run_arm() { echo "arm $1 $2 $3"; }; run_think() { :; }; idle_gate() { return 0; }; '
             'gate_set() { echo "gate $1=$2"; }; say() { echo "$*"; }; pause() { :; }; ' % check_rc)
    return _lib(stubs + f"run_phase {phase}", tmp_path)


def test_p7_smoke_fail_skips_whole_phase(tmp_path):
    out = _smoke_phase(tmp_path, "P7", 1)
    assert "phase P7 skipped (smoke)" in out and "gate P7_SMOKE=0" in out and "gate P7_PASS=skipped" in out
    assert "arm w27d" not in out


def test_p7_smoke_pass_runs_bands(tmp_path):
    out = _smoke_phase(tmp_path, "P7", 0)
    assert "gate P7_SMOKE=1" in out and "arm w27d 32768 p7x" in out


def test_p8_smoke_fail_drops_only_w27m(tmp_path):
    out = _smoke_phase(tmp_path, "P8", 1)
    assert "gate P8_SMOKE_w27m=0" in out and "arm r27m 32768 p8x" in out and "arm w27m" not in out


def test_smoke_not_rerun_when_result_exists(tmp_path):
    _jsonl(tmp_path / "w27d-8192-t1.0-p7s.jsonl", 3)
    out = _smoke_phase(tmp_path, "P7", 0)
    assert "run-arm.sh w27d 8192" not in out and "smoke w27d 8192 p7s (exists)" in out


# --- 2026-10-13 cut: fastest stacks only ---

def test_cut_keeps_later_phases_runnable_and_drops_o27q8_and_p0_medium():
    out = _dry("--skip-battery")  # the battery (PQ) is revised in Task 7
    arms = {l.split("run-arm.sh ")[1].split()[0] for l in out.splitlines() if "run-arm.sh " in l}
    assert arms == {"s27r", "k27", "r27d", "w27d"}
    assert "s27r 131072 --repeat 3 --tag p0m" not in out and "s27r 32768 --repeat 3 --tag p0x" in out
    assert "k27 131072 --repeat 3 --tag p1m" in out
    assert "run-arm.sh o27q8 32768" in _dry("--only", "P2")
    assert "--ctx 131072" in [l for l in _dry("--only", "P1").splitlines() if "decide.py" in l and "--base s27r" in l][0]


def test_campaign_stops_after_p1_unless_it_passes():
    src = (C / "scripts/run-campaign.sh").read_text()
    assert 'STOP_UNLESS_PASS' in src and "campaign ends here" in src
    assert 'STOP_UNLESS_PASS="P1"' in (C / "scripts/phases.sh").read_text()
