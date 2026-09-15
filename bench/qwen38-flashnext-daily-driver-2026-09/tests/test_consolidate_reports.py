from __future__ import annotations

import json
import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "scripts"))
import consolidate_reports as cr  # noqa: E402
import render_overview as ro  # noqa: E402
import render_perf_lines as rpl  # noqa: E402


def _record(scenario, ttft_s=1.0, decode=50.0, hit=0.95, finish="stop", error=None, correct=True, ctx=32768):
    return {
        "arm": "c1", "context_target": ctx, "scenario": scenario, "ttft_ms": ttft_s * 1000,
        "decode_tps": decode, "prompt_tps": 700.0, "cache_hit_ratio": hit, "finish_reason": finish,
        "error": error, "correct": correct, "ram_peak_gb": 90.0, "mem_free_min_gb": 0.1,
        "swap_delta_gb": 0.0, "mtp_acceptance": 0.6, "session_id": "s1",
    }


def _canon(data, cand, ctx):
    return next(g for g in data["groups"] if g["canonical"] and g["cand"] == cand and g["context"] == ctx)


def test_stage_for_maps_file_suffixes():
    assert cr.stage_for(8192, "1.0", None) == ("0", "canonical", "")
    assert cr.stage_for(32768, "1.0", None) == ("A", "canonical", "")
    assert cr.stage_for(32768, "1.0", "b")[0] == "B"
    assert cr.stage_for(524288, "1.0", "yarn2")[0] == "probe"
    assert cr.stage_for(262144, "1.0", "c") == ("C", "canonical", "")
    assert cr.stage_for(524288, "1.0", "yarn2-c") == ("C", "canonical", "YaRN 2.0 + KV 8-bit")
    assert cr.stage_for(32768, "0", None) == ("diag", "diag", "temp 0")
    assert cr.stage_for(32768, "0", "nomtp")[2] == "temp 0 · MTP off"
    assert cr.stage_for(131072, "1.0", "mem102g")[1] == "diag"


def test_build_group_uses_raw_medians_and_counts_truncation(tmp_path):
    records = [
        _record("cold", ttft_s=37.0, hit=0.0),
        _record("identical", ttft_s=0.1, decode=56.0, hit=1.0),
        _record("append", ttft_s=1.9, decode=55.0),
        _record("tool_turn", ttft_s=1.9, decode=60.0, finish="length",
                error="finish_reason:length", correct=False),
    ]
    g = cr.build_group(tmp_path / "c1-32768-t1.0.jsonl", records)
    assert g["t_turno_s"] == round(1.9 + 512 / 56.0, 2)
    assert g["truncated"] == 1 and g["failed"] == 0 and g["correct"] == 3
    assert g["decode_range"] == [55.0, 60.0]
    assert not g["refused"]


def test_build_group_accepts_uncensored_candidate(tmp_path):
    records = [
        _record("cold", ttft_s=37.0, hit=0.0),
        _record("identical", ttft_s=0.1, decode=56.0, hit=1.0),
        _record("tool_turn", ttft_s=1.9, decode=55.0),
    ]
    g = cr.build_group(tmp_path / "u1-32768-t1.0-b.jsonl", records)
    assert g["cand"] == "u1" and g["stage"] == "B"


def test_build_group_marks_http_refusal(tmp_path):
    records = [_record(s, decode=0.0, hit=None, finish=None, error="http_507: Insufficient Storage",
                       correct=False, ctx=262144)
               for s in ("cold", "identical", "tool_turn")]
    g = cr.build_group(tmp_path / "c4-262144-t1.0.jsonl", records)
    assert g["refused"] and g["error_kinds"] == ["http_507"]
    assert g["t_turno_s"] is None and g["scenarios_served"] == []


def test_mark_canonical_prefers_stage_c_over_probe_and_a():
    groups = [
        {"cand": "c1", "context": 524288, "stage": "probe", "mode": "canonical", "canonical": False},
        {"cand": "c1", "context": 524288, "stage": "C", "mode": "canonical", "canonical": False},
        {"cand": "c3", "context": 262144, "stage": "A", "mode": "canonical", "canonical": False},
        {"cand": "c3", "context": 262144, "stage": "C", "mode": "canonical", "canonical": False},
    ]
    cr.mark_canonical(groups)
    assert [g["canonical"] for g in groups] == [False, True, False, True]


def test_mark_canonical_prefers_stage_b():
    groups = [
        {"cand": "c1", "context": 32768, "stage": "A", "mode": "canonical", "canonical": False},
        {"cand": "c1", "context": 32768, "stage": "B", "mode": "canonical", "canonical": False},
        {"cand": "c1", "context": 32768, "stage": "diag", "mode": "diag", "canonical": False},
    ]
    cr.mark_canonical(groups)
    assert [g["canonical"] for g in groups] == [False, True, False]


def test_campaign_data_matches_summary_verdict():
    data = cr.build(cr.RESULTS)
    assert _canon(data, "c1", 32768)["t_turno_s"] == 11.03
    assert _canon(data, "c1", 131072)["t_turno_s"] == 12.35
    assert _canon(data, "c3", 32768)["t_turno_s"] == 13.48
    assert _canon(data, "c3", 131072)["t_turno_s"] == 15.03
    c4 = _canon(data, "c4", 131072)
    assert c4["refused"] and "http_errors" in c4["gates_failed"]
    assert _canon(data, "c1", 524288)["stage"] == "C"
    assert ro.gate_passers(data) == ["c1", "c2", "c3"]


def test_renderers_fill_every_placeholder(tmp_path):
    data = cr.build(cr.RESULTS)
    overview = ro.render(data)
    perf = rpl.render(data)
    for page in (overview, perf):
        for marker in ("__DATA__", "__TILES__", "__PAYLOAD__", "/*__CSS__*/", "__DENSE_CSS__", "__PERF_CSS__"):
            assert marker not in page
    assert "12.35" in overview and "Verdict: c1 mlx-serve 26.9.2" in overview
    payload = rpl.build_payload(data)
    assert payload["points"]["c4"]["524288"]["status"] == rpl.ABSENT[("c4", 524288)]
    assert set(payload["hitmap"]["c4"]["131072"].values()) == {"x"}
    embedded = json.loads(overview.split('type="application/json">', 1)[1].split("</script>", 1)[0])
    # the overview embeds only the charted candidates; u1 (chart:False) is rendered
    # in its own Stage U section instead of the shared charts.
    chart_ids = {c["id"] for c in data["candidates"] if c.get("chart", True)}
    assert len(embedded["groups"]) == len([g for g in data["groups"] if g["cand"] in chart_ids])
    assert "u1" not in {g["cand"] for g in embedded["groups"]}
    assert "Refusal probe" in overview and "Responsiveness: c1 vs u1" in overview
    assert "Refusal on harmful prompts" in overview and "higher is safer" in overview


def test_stage_u_harmful_refusal_summary():
    data = cr.build(cr.RESULTS)
    refh = data["stage_u"]["refusal_harmful"]
    assert refh["categories"] == cr.HARMFUL_REFUSAL_CATEGORIES
    # the harmful summary must not leak the legitimate probe's categories
    assert set(refh["c1"]["by_category"]) == set(cr.HARMFUL_REFUSAL_CATEGORIES)
    # the measured safety delta the verdict rests on: c1 keeps some refusals,
    # the abliterated u1 refuses none.
    assert refh["c1"]["total"]["n"] == 24 and refh["u1"]["total"]["n"] == 24
    assert refh["c1"]["total"]["refused"] == 7
    assert refh["u1"]["total"]["refused"] == 0


def test_harmful_results_store_no_response_text():
    # A compliant preview would be the start of harmful content; the harmful
    # arm must persist the verdict only.
    for arm in ("c1", "u1"):
        path = cr.RESULTS / f"refusal-harmful-{arm}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                assert "preview" not in json.loads(line)
