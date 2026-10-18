import json
from pathlib import Path

import pytest

import render_report as R

REAL_RESULTS = Path(__file__).resolve().parents[1] / "results"
REF = {32768: 7.9, 131072: 8.6, 262144: 11.1}


def _rec(scenario, ttft_s, decode, correct=True):
    return {"scenario": scenario, "finish_reason": "stop", "error": None, "ttft_ms": ttft_s * 1000,
            "decode_tps": decode, "cache_hit_ratio": 0.99, "correct": correct, "concurrency": 2}


def _stream(results, arm, ctx, tag, k, ratio, decode=512.0, correct=True):
    """Write one stream whose T_turno / ref is `ratio` (reply of 512 tokens at `decode` tok/s)."""
    ttft = ratio * REF[ctx] - 512 / decode
    recs = [_rec(s, ttft, decode, correct) for s in ("identical", "append", "tool_turn")]
    path = results / f"{arm}-{ctx}-{tag}-s{k}.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def _aux(results, arm, ctx, tag, totals):
    rows = [{"kind": "title", "ttft_s": t, "total_s": t, "status": 200, "error": None} for t in totals]
    (results / f"{arm}-{ctx}-{tag}-aux.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _cfg(data, code, ctx):
    return next(c for c in data["configs"] if c["code"] == code and c["ctx"] == ctx)


def test_collect_worst_stream_decides(tmp_path):
    _stream(tmp_path, "w1c2", 32768, "e1", 1, 1.1)
    _stream(tmp_path, "w1c2", 32768, "e1", 2, 1.9)
    c = _cfg(R.collect(tmp_path), "w1c2", 32768)
    assert c["worst_ratio"] == pytest.approx(1.9, abs=0.02)
    assert c["worst_stream"] == "s2"
    assert c["result"] == "warning"


@pytest.mark.parametrize("ratio,expected", [(1.4, "pass"), (1.9, "warning"), (2.1, "fail")])
def test_collect_result_bands(tmp_path, ratio, expected):
    _stream(tmp_path, "w1c1", 32768, "e1", 1, ratio)
    assert _cfg(R.collect(tmp_path), "w1c1", 32768)["result"] == expected


def test_collect_missing_config_is_na(tmp_path):
    c = _cfg(R.collect(tmp_path), "w1c4", 128 * 1024)
    assert c["worst_ratio"] is None and c["result"] == "n/a"
    assert c["decode_per_session"] is None and c["wired_peak"] is None


def test_collect_decode_total(tmp_path):
    _stream(tmp_path, "w1c2", 32768, "e1", 1, 1.1, decode=80.0)
    _stream(tmp_path, "w1c2", 32768, "e1", 2, 1.2, decode=40.0)
    c = _cfg(R.collect(tmp_path), "w1c2", 32768)
    assert c["n"] == 2
    assert c["decode_per_session"] == pytest.approx(60.0)
    assert c["decode_total"] == pytest.approx(2 * 60.0)


def test_collect_aux_and_refused_and_needles(tmp_path):
    _stream(tmp_path, "w1c1a", 32768, "e1", 1, 1.0, correct=False)
    _aux(tmp_path, "w1c1a", 32768, "e1", [1.0, 2.0, 70.0, 90.0])
    c = _cfg(R.collect(tmp_path), "w1c1a", 32768)
    assert c["aux"] is True and c["aux_over_60"] == 2 and c["aux_p50"] == pytest.approx(36.0)
    assert c["needles_ok"] is False and c["needles"] == "0/3"
    assert c["refused"] == 0


def test_collect_asymmetric_arm_uses_all_contexts(tmp_path):
    _stream(tmp_path, "w1c2L", 262144, "e1d", 1, 1.0)
    _stream(tmp_path, "w1c2L", 32768, "e1d", 2, 1.96)
    c = _cfg(R.collect(tmp_path), "w1c2L", 262144)
    assert c["worst_ratio"] == pytest.approx(1.96, abs=0.02) and c["worst_stream"] == "s2"


def _cc(results, name, wall):
    (results / f"cc-{name}.json").write_text(json.dumps(
        {"wall_s": wall, "task": name[-1], "is_error": False, "task_done": True, "num_turns": 5}))


def test_collect_claude_code_means(tmp_path):
    for rep, (a, b) in enumerate([(70.0, 60.0), (80.0, 64.0)], start=1):
        _cc(tmp_path, f"cc1r{rep}-a", a)
        _cc(tmp_path, f"cc1r{rep}-b", b)
    for rep, (a, b) in enumerate([(100.0, 140.0), (150.0, 120.0), (110.0, 160.0)], start=1):
        _cc(tmp_path, f"cc2r{rep}-a", a)
        _cc(tmp_path, f"cc2r{rep}-b", b)
    cc = R.collect(tmp_path)["claude_code"]
    assert cc["tasks"]["a"]["alone_mean"] == pytest.approx(75.0)
    assert cc["tasks"]["b"]["alone_mean"] == pytest.approx(62.0)
    assert cc["tasks"]["a"]["together_mean"] == pytest.approx(120.0)
    assert cc["tasks"]["a"]["together_reps"] == [100.0, 150.0, 110.0]
    assert cc["serial_sum"] == pytest.approx(137.0)
    assert cc["pair_wall"] == pytest.approx((140 + 150 + 160) / 3)


def test_collect_static_fields(tmp_path):
    (tmp_path / "etapa1-verdict.env").write_text("N_APPROVED=2\nNOTE=a=b\n")
    d = R.collect(tmp_path)
    assert d["refs"] == {32768: 7.9, 131072: 8.6, 262144: 11.1, "262144_measured": 10.3}
    assert d["verdicts"]["etapa1"] == {"N_APPROVED": "2", "NOTE": "a=b"}
    assert d["verdicts"]["etapa1b"] == {}
    assert d["by_n"]["ratio"] == {} or isinstance(d["by_n"]["ratio"], dict)
    assert len(d["configs"]) == 8 * 2 + 2 + 5


def test_collect_real_matches_summary():
    d = R.collect(REAL_RESULTS)
    assert _cfg(d, "w1c2a", 32768)["worst_ratio"] == pytest.approx(1.76, abs=0.01)
    assert _cfg(d, "w1c2a", 131072)["worst_ratio"] == pytest.approx(1.94, abs=0.01)
    assert _cfg(d, "w1c3a", 32768)["worst_ratio"] == pytest.approx(2.37, abs=0.01)
    assert _cfg(d, "w1c3a", 131072)["worst_ratio"] == pytest.approx(2.36, abs=0.01)
    assert _cfg(d, "w1c4a", 131072)["worst_ratio"] == pytest.approx(3.85, abs=0.01)
    assert _cfg(d, "w1c2m4", 262144)["worst_ratio"] == pytest.approx(1.68, abs=0.01)
    assert d["claude_code"]["pair_wall"] == pytest.approx(147.6, abs=0.1)
    assert d["claude_code"]["serial_sum"] == pytest.approx(137.6, abs=0.1)
    assert _cfg(d, "w1c2a", 131072)["wired_peak"] == pytest.approx(113.5)
    assert d["by_n"]["ratio"][131072][4] == pytest.approx(3.85, abs=0.01)


# ---- SVG builders ----

GROUPS = [
    {"label": "32k", "values": {"A": 1.2, "B": 2.4}},
    {"label": "128k", "values": {"A": 1.6, "B": None}},
]


def _opening_tag(svg):
    return svg[: svg.index(">") + 1]


def test_grouped_bars_one_rect_per_value_and_viewbox():
    svg = R.svg_grouped_bars(GROUPS, ["A", "B"], 3.0)
    assert svg.startswith("<svg")
    assert svg.count("<rect") == 3
    tag = _opening_tag(svg)
    assert "viewBox=" in tag and "width=" not in tag and "height=" not in tag


def test_grouped_bars_none_is_na_without_rect():
    svg = R.svg_grouped_bars(GROUPS, ["A", "B"], 3.0)
    assert svg.count(">n/a</text>") == 1
    only_none = R.svg_grouped_bars([{"label": "x", "values": {"A": None}}], ["A"], 3.0)
    assert "<rect" not in only_none and ">n/a</text>" in only_none


def test_grouped_bars_bands_are_lines():
    svg = R.svg_grouped_bars(GROUPS, ["A", "B"], 3.0, bands=[(1.5, "1.5x"), (2.0, "2.0x")])
    assert svg.count('<line class="band"') == 2
    assert "1.5x" in svg and "2.0x" in svg


def test_grouped_bars_escapes_labels():
    svg = R.svg_grouped_bars([{"label": "<b>", "values": {"A": 1.0}}], ["A"], 2.0)
    assert "<b>" not in svg and "&lt;b&gt;" in svg


ROWS = [
    {"label": "r1", "p50": 5.0, "p95": 12.0, "max": 20.0},
    {"label": "r2", "p50": None, "p95": None, "max": None},
]


def test_dots_circles_and_60s_reference():
    svg = R.svg_dots(ROWS)
    assert svg.startswith("<svg")
    assert svg.count('<circle class="p50"') == 1 and svg.count('<circle class="p95"') == 1
    assert svg.count('<line class="band"') == 1 and "60 s" in svg
    tag = _opening_tag(svg)
    assert "viewBox=" in tag and "width=" not in tag


def test_dots_none_is_na_without_circle():
    svg = R.svg_dots([{"label": "r", "p50": None, "p95": None, "max": None}])
    assert "<circle" not in svg and ">n/a</text>" in svg


PAIRS = [
    {"label": "p1", "a": 10.0, "b": 20.0, "a_label": "A", "b_label": "B"},
    {"label": "p2", "a": 5.0, "b": None, "a_label": "A", "b_label": "B"},
]


def test_paired_bars_rects_and_none():
    svg = R.svg_paired_bars(PAIRS)
    assert svg.startswith("<svg")
    assert svg.count('<rect class="a"') == 2 and svg.count('<rect class="b"') == 1
    assert svg.count(">n/a</text>") == 1
    tag = _opening_tag(svg)
    assert "viewBox=" in tag and "width=" not in tag


# ---- review fixes: partial None, clamping, contract ----

def _rect_heights(svg):
    import re
    return [float(m) for m in re.findall(r'<rect[^>]* height="([\d.]+)"', svg)]


def test_grouped_bars_clamps_over_ymax_zero_and_negative():
    svg = R.svg_grouped_bars([{"label": "g", "values": {"A": 9.0, "B": 0.0, "C": -2.0}}],
                             ["A", "B", "C"], 3.0)
    plot_h = 320 - 20 - 40
    assert _rect_heights(svg) == [float(plot_h), 0.0, 0.0]


def test_paired_bars_zero_and_negative_have_zero_height():
    svg = R.svg_paired_bars([{"label": "p", "a": 0.0, "b": -1.0, "a_label": "A", "b_label": "B"},
                             {"label": "q", "a": 5.0, "b": 2.0, "a_label": "A", "b_label": "B"}])
    h = _rect_heights(svg)
    assert h[:2] == [0.0, 0.0] and h[2] == 300 - 24 - 40


def test_dots_partial_none_has_distinct_label_and_other_circle():
    svg = R.svg_dots([{"label": "r", "p50": 5.0, "p95": None, "max": None},
                      {"label": "s", "p50": None, "p95": 9.0, "max": None}])
    assert ">p95 n/a</text>" in svg and ">p50 n/a</text>" in svg
    assert svg.count('<circle class="p50"') == 1 and svg.count('<circle class="p95"') == 1


def test_svg_contract_markers_in_all_builders():
    for svg in (R.svg_grouped_bars(GROUPS, ["A", "B"], 3.0), R.svg_dots(ROWS), R.svg_paired_bars(PAIRS)):
        assert 'role="img"' in svg and 'aria-label="' in svg
        assert 'preserveAspectRatio="xMidYMid meet"' in svg
        assert "var(--s" in svg and "currentColor" in svg
    g = R.svg_grouped_bars(GROUPS, ["A", "B"], 3.0)
    assert g.count("<title>") == 3 and "32k · A: 1.2" in g
    assert 'class="value"' in g and ">1.2</text>" in g
    assert ">60 s</text>" in R.svg_dots(ROWS)
    assert R.svg_paired_bars(PAIRS).count("<title>") == 3
