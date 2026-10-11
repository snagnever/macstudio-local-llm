import json
import re
import sys
from pathlib import Path

import pytest

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "scripts"))
import render_page as R  # noqa: E402

REAL_RESULTS = CAMPAIGN / "results"
REAL_REPORTS = CAMPAIGN.parent / "engine-updates-2026-10" / "results" / "reports-2026-10.json"


def b2(idx, ok, s, fin="stop", comp=100, rc=10):
    return {"dataset_idx": idx, "lcb_question_id": None, "correct": ok, "elapsed_s": s,
            "finish_reason": fin, "completion_tokens": comp, "reasoning_chars": rc}


def tool(cid, ok, t1, t2=None, multi=False):
    return {"case_id": cid, "score_pass": ok, "turn_1_elapsed_s": t1, "turn_2_elapsed_s": t2,
            "multi_turn": multi, "turn_1_finish_reason": "tool_calls", "completion_tokens": 40}


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def speed_entry(t):
    return {"cold_ttft_s": 30.0, "warm_ttft_s": {"identical": 0.2, "append": 1.8, "tool_turn": 1.8},
            "hit": {"identical": 1.0, "append": 0.96, "tool_turn": 0.96}, "prefill_tps": 790.0,
            "decode_tps": 80.0, "t_turno_s": t, "correctness": "ok", "wired_peak_gb": 96.0,
            "swap_delta_gb": 0, "mtp_acceptance": 0.8, "errors": 0, "n": 13, "gates_failed": [], "warnings": []}


def group(arm, cand, ctx, canonical, t):
    return {"arm": arm, "cand": cand, "context": ctx, "canonical": canonical, "mode": "canonical",
            "t_turno_s": t, "cold_ttft_s": 40.0, "ttft_s": {"tool_turn": 2.4}, "hit": {"tool_turn": 0.96},
            "decode_tps": 66.0, "prefill_tps": 550.0, "mtp_acceptance": None, "wired_peak_gb": 91.0,
            "campaign": "engine-updates-2026-10", "gates_failed": []}


@pytest.fixture
def fake(tmp_path):
    res = tmp_path / "results"
    for prof in ("t1", "t0"):
        write_jsonl(res / "ab" / prof / "n2" / "gpqa.jsonl",
                    [b2(1, True, 60.0), b2(2, False, 100.0, fin="length"), b2(3, True, 20.0)])
        write_jsonl(res / "ab" / prof / "w1" / "gpqa.jsonl",
                    [b2(1, True, 20.0), b2(2, True, 30.0), b2(3, False, 10.0)])
        write_jsonl(res / "ab" / prof / "n2" / "jdhodges.jsonl",
                    [tool("a", True, 2.0), tool("b", True, 3.0, 5.0, True), tool("c", False, 4.0)])
        write_jsonl(res / "ab" / prof / "w1" / "jdhodges.jsonl",
                    [tool("a", True, 1.0), tool("b", True, 2.0, 7.0, True), tool("c", True, 3.0)])
    # w1 não tem o IF em t0: a suíte tem de aparecer como ausente, não sumir.
    write_jsonl(res / "ab" / "t1" / "n2" / "if.jsonl", [{"id": "if01", "passed": True, "elapsed_s": 2.0,
                                                         "finish_reason": "stop", "completion_tokens": 30}])
    write_jsonl(res / "ab" / "t1" / "w1" / "if.jsonl", [{"id": "if01", "passed": False, "elapsed_s": 1.0,
                                                         "finish_reason": "stop", "completion_tokens": 30}])
    write_jsonl(res / "ab" / "t0" / "n2" / "if.jsonl", [{"id": "if01", "passed": True, "elapsed_s": 2.0,
                                                         "finish_reason": "stop", "completion_tokens": 30}])
    (res / "humaneval-regrade.json").write_text(json.dumps(
        {"n2-t1": {"n": 164, "strict": 144, "with_imports": 158}}), encoding="utf-8")
    (res / "tturno-summary.json").write_text(json.dumps(
        {"n2@32768": speed_entry(8.1), "w1@32768": speed_entry(7.9),
         "n2@131072": speed_entry(8.9), "w1@131072": speed_entry(8.6)}), encoding="utf-8")
    rep = tmp_path / "reports.json"
    rep.write_text(json.dumps({"rig": [{"lab": "Chip", "val": "Apple M4 Max"}], "groups": [
        group("o1", "o1", 32768, True, 10.06), group("m1p", "m1", 32768, True, 8.84),
        group("m1x", "m1", 131072, True, 15.1), group("m1s", "m1", 131072, False, None),
        group("n2", "n2", 32768, True, 8.23),
    ]}), encoding="utf-8")
    return res, rep


def test_quality_counts_per_profile_and_arm(fake):
    d = R.collect(*fake)
    q = d["quality"]["t1"]
    assert q["n2"]["gpqa"] == {"n": 3, "passed": 2, "missing": False}
    assert q["w1"]["gpqa"]["passed"] == 2


def test_missing_suite_is_marked_not_dropped(fake):
    d = R.collect(*fake)
    assert d["quality"]["t0"]["w1"]["if"] == {"n": 0, "passed": None, "missing": True}
    assert d["time"]["t0"]["if"]["arms"]["w1"]["missing"] is True
    assert d["time"]["t0"]["if"]["ratio"] is None


def test_time_stats_points_and_ratio(fake):
    t = R.collect(*fake)["time"]["t1"]["gpqa"]
    n2 = t["arms"]["n2"]
    assert n2["median_s"] == 60.0 and n2["total_s"] == 180.0 and n2["truncated"] == 1
    assert {"id": "2", "s": 100.0, "ok": False, "trunc": True} in n2["points"]
    assert t["ratio"] == round(20.0 / 60.0, 2)


def test_tool_latency_turn2_only_multi_turn(fake):
    lat = R.collect(*fake)["tool_latency"]["t1"]["jdhodges"]
    assert lat["n2"]["turn1_median_s"] == 3.0
    assert lat["n2"]["turn2_median_s"] == 5.0 and lat["n2"]["turn2_n"] == 1
    assert lat["w1"]["passed"] == 3 and lat["w1"]["n"] == 3


def test_humaneval_regrade_passed_through(fake):
    assert R.collect(*fake)["humaneval_regrade"]["n2-t1"]["with_imports"] == 158


def test_speed_uses_same_session_arms_then_canonical_groups(fake):
    sp = R.collect(*fake)["speed"]
    rows32 = {r["arm"]: r for r in sp["32768"]}
    assert rows32["w1"]["t_turno_s"] == 7.9 and rows32["w1"]["source"] == "swift15-flashnext-2026-10"
    assert rows32["m1p"]["series"] == "m1" and rows32["m1p"]["ttft_tool_turn_s"] == 2.4
    # o n2 da Etapa G não vira uma segunda linha: ele entra como referência de deriva.
    assert [r["arm"] for r in sp["32768"]].count("n2") == 1
    assert sp["drift"]["32768"] == 8.23
    arms128 = [r["arm"] for r in sp["131072"]]
    assert "m1x" in arms128 and "m1s" not in arms128


def test_series_without_group_in_band_is_listed_as_absent(fake):
    rows128 = {r["arm"]: r for r in R.collect(*fake)["speed"]["131072"]}
    assert rows128["o1"]["t_turno_s"] is None and rows128["o1"]["absent"]


@pytest.mark.skipif(not REAL_REPORTS.is_file(), reason="sem o reports-2026-10.json")
def test_real_data_matches_summary_md():
    d = R.collect(REAL_RESULTS, REAL_REPORTS)
    hi = d["humaneval_regrade"]
    assert [hi[k]["with_imports"] for k in ("n2-t1", "w1-t1", "n2-t0", "w1-t0")] == [158, 158, 155, 157]
    assert [d["quality"][p][a]["gpqa"]["passed"] for p in ("t1", "t0") for a in ("n2", "w1")] == [45, 43, 39, 42]
    g = d["time"]["t1"]["gpqa"]["arms"]
    assert (g["n2"]["median_s"], g["w1"]["median_s"]) == (63.9, 22.3)
    assert d["time"]["t1"]["gpqa"]["ratio"] == 0.35
    rows = {r["arm"]: r for r in d["speed"]["131072"]}
    assert rows["w1"]["t_turno_s"] == 8.6 and rows["m1x"]["t_turno_s"] == 15.1
