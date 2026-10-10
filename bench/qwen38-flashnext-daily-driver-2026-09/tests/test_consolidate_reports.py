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


# Perfil 2026-10: séries n2, o1, MTPLX (m1*), d1 e c1 de referência, lidas de três campanhas.
def _write(dirpath, name, records):
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def _rep_set(reps, stamp, ctx=32768, rev="v", tool_ttft=1.0, error=None):
    out = []
    for rep in range(1, reps + 1):
        for s in ("cold", "identical", "append", "tool_turn"):
            r = _record(s, ttft_s=(30.0 if s == "cold" else tool_ttft), hit=(0.0 if s == "cold" else 0.95), ctx=ctx)
            r.update(run_id=f"{stamp}-x-{ctx}-{s}-r{rep}", runtime_revision=rev)
            if error:
                r.update(error=error, decode_tps=0.0, cache_hit_ratio=None, finish_reason=None, correct=False)
            out.append(r)
    return out


def _dirs(tmp_path):
    sept, eng, upd = tmp_path / "sept", tmp_path / "eng", tmp_path / "upd"
    _write(sept, "c1-32768-t1.0-b.jsonl", _rep_set(3, "20260901T000000Z"))
    _write(eng, "n2-32768-t1.0-fn.jsonl", _rep_set(3, "20261007T000000Z", tool_ttft=2.0))
    _write(upd, "n2-32768-t1.0-ab.jsonl", _rep_set(3, "20261006T000000Z", tool_ttft=3.0))
    _write(eng, "n2-8192-t1.0-smoke.jsonl", _rep_set(1, "20261007T000000Z", ctx=8192, tool_ttft=9.0))
    _write(eng, "n2-8192-t1.0-pg.jsonl", _rep_set(3, "20261009T000000Z", ctx=8192, tool_ttft=0.5))
    _write(eng, "o1-32768-t1.0-fn.jsonl", _rep_set(3, "20261007T000000Z"))
    _write(eng, "m1-32768-t1.0-fn.jsonl", _rep_set(3, "20261007T000000Z", rev="v2.12.2", tool_ttft=46.0))
    _write(eng, "m1p-32768-t1.0-fx.jsonl", _rep_set(3, "20261008T000000Z", rev="v2.12.2-prime64", tool_ttft=2.4))
    _write(eng, "m1q-131072-t1.0-pg.jsonl", _rep_set(3, "20261009T000000Z", ctx=131072, rev="v2.12.2-kvq8"))
    _write(eng, "m1v-131072-t1.0-pg.jsonl",
           _rep_set(3, "20261009T000000Z", ctx=131072, rev="v2.12.2-vendor", error="http_507: Insufficient Storage"))
    _write(eng, "d1-8192-t1.0-pg.jsonl", _rep_set(3, "20261009T000000Z", ctx=8192))
    _write(eng, "d1-262144-t1.0-pg.jsonl",
           _rep_set(1, "20261009T000000Z", ctx=262144, error="http_500: PrefillDoesNotFit"))
    return sept, eng, upd


def test_profile_2026_10_reads_both_campaigns(tmp_path):
    data = cr.build_2026_10(*_dirs(tmp_path))
    assert data["profile"] == "2026-10"
    assert {c["id"] for c in data["candidates"]} == {"n2", "o1", "m1", "d1", "c1"}
    assert {g["cand"] for g in data["groups"] if g["canonical"]} == {"n2", "o1", "m1", "d1", "c1"}


def test_profile_2026_10_picks_most_reps(tmp_path):
    data = cr.build_2026_10(*_dirs(tmp_path))
    g32 = _canon(data, "n2", 32768)
    assert g32["file"] == "n2-32768-t1.0-fn.jsonl"  # empate em 3 reps: vale o mais recente
    g8 = _canon(data, "n2", 8192)
    assert g8["file"] == "n2-8192-t1.0-pg.jsonl" and g8["reps"] == 3


def test_refused_band_stays_as_refused_point(tmp_path):
    data = cr.build_2026_10(*_dirs(tmp_path))
    g = _canon(data, "d1", 262144)
    assert g["refused"] and g["error_kinds"] == ["http_500"]
    p = rpl.point(g)
    assert p["status"].startswith("refused")


def test_mtplx_point_carries_config_label(tmp_path):
    data = cr.build_2026_10(*_dirs(tmp_path))
    g128 = _canon(data, "m1", 131072)
    assert g128["arm"] == "m1q" and g128["config"] == "KV q8"  # m1v recusou; o m1q serviu
    g32 = _canon(data, "m1", 32768)
    assert g32["arm"] == "m1p" and g32["config"] == "prime 64"  # o m1 do fn usou o prime de 1 token


def test_default_profile_unchanged():
    committed = json.loads((CAMPAIGN / "results" / "reports.json").read_text(encoding="utf-8"))
    built = cr.build(CAMPAIGN / "results")
    committed.pop("generated_at"); built.pop("generated_at")
    assert built == committed


def test_render_2026_10_has_notes(tmp_path):
    html = rpl.render(cr.build_2026_10(*_dirs(tmp_path)))
    for text in ("Apple M4 Max", "mlx-serve 26.10.1", "oMLX 0.7.0", "MTPLX 2.12.2", "ds4",
                 "64-token prime", "speed, cache and memory only", "mlx-serve/issues/658"):
        assert text.lower() in html.lower(), text
    payload = json.loads(html.split("const P = ", 1)[1].split(";\n", 1)[0])
    assert [s["id"] for s in payload["series"]] == ["n2", "o1", "m1", "d1", "c1"]
    assert payload["points"]["m1"]["131072"]["config"] == "KV q8"
    assert "__" not in html.split("<script>", 1)[0].replace("__PAYLOAD__", "")


def test_render_default_keeps_september_text():
    data = json.loads((CAMPAIGN / "results" / "reports.json").read_text(encoding="utf-8"))
    html = rpl.render(data)
    assert "Four quant × runtime candidates" in html and "64-token prime" not in html


def test_render_panel_without_interp_prints_nothing():
    assert 'interp.innerHTML=p.interp||"";' in rpl.TEMPLATE


def test_m1xq_label_says_kv_q8_was_ignored(tmp_path):
    # O MTPLX 2.12.2 rebaixa --paged-kv-quantization q8 para off no Flash-Next (boot log do m1xq).
    sept, eng, upd = _dirs(tmp_path)
    _write(eng, "m1xq-262144-t1.0-pg.jsonl", _rep_set(1, "20261009T200000Z", ctx=262144, rev="v2.12.2-memmax-kvq8"))
    g = _canon(cr.build_2026_10(sept, eng, upd), "m1", 262144)
    assert g["arm"] == "m1xq" and g["config"] == "memory limit max (KV q8 ignored)"


def test_render_2026_10_marks_mtplx_512k_absent():
    assert rpl.ABSENT_2026_10[("m1", 524288)].startswith("not run")


def test_2026_10_has_takeaways_with_quality_line(tmp_path):
    sept, eng, upd = _dirs(tmp_path)
    tk = cr.build_2026_10(sept, eng, upd)["takeaways"]
    assert len(tk) >= 4 and all(len(t) == 2 for t in tk)
    assert any("HumanEval" in body for _, body in tk)


def test_2026_10_every_panel_has_interp():
    assert all(p.get("interp") for p in rpl.PAGE_2026_10["panels"].values())


def test_2026_10_tech_cards_name_measured_configs():
    cards = {c["name"]: c for c in rpl.TECH_2026_10}
    assert "69.7 GiB" in cards["ds4 (upstream)"]["configs"]
    assert "65,536" in cards["MTPLX 2.12.2"]["configs"]


def test_review_takeaways_rank_and_quality_wording(tmp_path):
    sept, eng, upd = _dirs(tmp_path)
    tk = dict(cr.build_2026_10(sept, eng, upd)["takeaways"])
    body = " ".join(tk.values())
    text = " ".join(tk) + " " + body
    assert "second at 128K and 256K" in text and "second up to 256K" not in text
    assert "no runtime beats n2" not in " ".join(tk).lower()
    assert "reasoning" in body and "±" in text


def test_review_mtplx_points_hide_mtp_counter():
    data = json.loads((Path(__file__).resolve().parents[2] / "engine-updates-2026-10" / "results"
                       / "reports-2026-10.json").read_text(encoding="utf-8"))
    pts = rpl.build_payload(data)["points"]["m1"]
    assert all(p.get("mtp") is None for p in pts.values())


def test_review_prefill_interp_marks_hypothesis():
    assert "not profiled" in rpl.PAGE_2026_10["panels"]["prefill"]["interp"]


def test_review_index_card_does_not_claim_measured_237k():
    html = (Path(__file__).resolve().parents[3] / "reports" / "index.html").read_text(encoding="utf-8")
    assert "stops at 237K" not in html and "refuses 256K" in html
