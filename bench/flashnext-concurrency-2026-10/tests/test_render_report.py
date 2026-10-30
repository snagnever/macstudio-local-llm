import html
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


@pytest.mark.parametrize("ratio,expected", [(1.4, "pass"), (1.9, "warning"), (2.0, "warning"), (2.1, "fail")])
def test_collect_result_bands(tmp_path, ratio, expected):
    _stream(tmp_path, "w1c1", 32768, "e1", 1, ratio)
    assert _cfg(R.collect(tmp_path), "w1c1", 32768)["result"] == expected


def test_result_band_boundaries_are_inclusive():
    # Exactly 1.5 passes and exactly 2.0 is a warning (the stream helper cannot hit 1.5 exactly: turn times are
    # rounded to 0.1 s), so the boundary is asserted on the classifier itself.
    assert R._result(1.5) == "pass" and R._result(2.0) == "warning"
    assert R._result(1.5000001) == "warning" and R._result(2.0000001) == "fail"


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
    assert len(d["configs"]) == 8 * 2 - 1 + 2 + 5


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


# ---- render() and main() ----

import re

# The page body (new sections) and the appendix (the 26.10.1 campaign sections, kept as they were).
SECTION_IDS = ["verdict", "one", "two", "worst", "many", "long", "recommend", "coverage", "appendix",
               "hero", "how-it-works", "glossary", "sessions", "throughput", "side-requests", "max-concurrent",
               "long-context", "claude-code", "pds", "learned", "upstream", "refusals", "not-measured",
               "reproduce", "terms"]
INSIDER = re.compile(r"\b(w1c\w*|w1zc\w*|k2c\w*|kcc\w*|T_turno|braço|aux|needle|needles|stream|streams|rig|"
                     r"daily driver|etapa)\b", re.IGNORECASE)


@pytest.fixture(scope="module")
def real_html():
    return R.render(R.collect(REAL_RESULTS))


def _payload(page):
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S)
    assert m, "data payload missing"
    return m.group(1)


def _public_body(page):
    body = re.sub(r"<footer\b.*?</footer>", "", page, flags=re.S)
    body = re.sub(r"<details\b.*?</details>", "", body, flags=re.S)
    body = re.sub(r'<script id="data" type="application/json">.*?</script>', "", body, flags=re.S)
    # "stream" is allowed only inside <code> (server messages and flags)
    return re.sub(r"<code\b.*?</code>", lambda m: re.sub(r"\bstreams?\b", "", m.group(0), flags=re.I),
                  body, flags=re.S)


def test_render_sections_present(real_html):
    for sid in SECTION_IDS:
        assert f'id="{sid}"' in real_html, sid
    assert real_html.lstrip().lower().startswith("<!doctype html>")
    assert '<html lang="en"' in real_html
    assert "<title>Can one Mac Studio serve Claude Code?</title>" in real_html


def test_render_illustrations_replace_anchors(real_html):
    assert "ILLUSTRATION_" not in real_html
    how = real_html[real_html.index('id="how-it-works"'):real_html.index('id="glossary"')]
    assert how.count(R.ILLUSTRATION_TIMELINE) == 1
    thr = real_html[real_html.index('id="throughput"'):real_html.index('id="side-requests"')]
    assert thr.count(R.ILLUSTRATION_BATCH) == 1
    assert real_html.count(R.ILLUSTRATION_TIMELINE) == 1 and real_html.count(R.ILLUSTRATION_BATCH) == 1


@pytest.mark.parametrize("name", ["ILLUSTRATION_TIMELINE", "ILLUSTRATION_BATCH"])
def test_illustration_svg_contract(name):
    svg = getattr(R, name)
    assert svg.startswith("<svg")
    assert 'role="img"' in svg and 'preserveAspectRatio="xMidYMid meet"' in svg
    assert re.search(r"<svg[^>]*\sviewBox=", svg)
    assert not re.search(r"<svg[^>]*\s(width|height)=", svg)
    m = re.search(r'aria-labelledby="([^"]+)"', svg)
    assert m and f'<title id="{m.group(1)}">' in svg
    assert svg.index("<title") < svg.index("<rect")
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b|rgb\(", svg)
    sizes = [float(x) for x in re.findall(r'font-size="([\d.]+)"', svg)]
    assert sizes and min(sizes) >= 11
    assert INSIDER.search(re.sub(r"<[^>]+>", " ", svg)) is None


def test_illustration_labels():
    for t in ("One session alone", "Two sessions together", "waits here", "prompt cache"):
        assert t in R.ILLUSTRATION_TIMELINE
    for t in ("1 session", "4 sessions", "Schematic", "measured totals are in the chart below"):
        assert t in R.ILLUSTRATION_BATCH
    assert not re.search(r"\d+ tok/s|× \d|About 80", R.ILLUSTRATION_BATCH)


def test_render_no_insider_terms(real_html):
    hits = sorted({m.group(0) for m in INSIDER.finditer(_public_body(real_html))})
    assert hits == []
    footer = re.search(r"<footer\b.*?</footer>", real_html, re.S).group(0)
    assert "w1c2a" in footer and "T_turno" in footer


def test_render_no_insider_terms_empty_results(tmp_path):
    hits = sorted({m.group(0) for m in INSIDER.finditer(_public_body(R.render(R.collect(tmp_path))))})
    assert hits == []


def test_render_no_placeholders(real_html):
    assert not re.search(r"__[A-Z_]+__", real_html)


def test_render_payload_escaped(tmp_path):
    data = R.collect(tmp_path)
    data["configs"][0]["public_name"] = "</script><b>x</b>"
    page = R.render(data)
    payload = _payload(page)
    assert "</" not in payload
    assert json.loads(payload)["configs"][0]["public_name"] == "</script><b>x</b>"
    assert "<b>x</b>" not in page.replace(payload, "")


def test_render_payload_is_collect_output(real_html):
    p = json.loads(_payload(real_html))
    assert len(p["configs"]) == 22 and p["claude_code"]["pair_wall"] == pytest.approx(147.6, abs=0.1)


def test_render_na_for_missing(tmp_path):
    page = R.render(R.collect(tmp_path))
    row = re.search(r'<tr data-config="w1c4-131072">(.*?)</tr>', page, re.S)
    assert row, "results table row for a missing configuration"
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row.group(1), re.S)
    assert cells[0] == "w1c4"
    assert cells.count("n/a") >= 4


def test_render_na_for_missing_in_real_data(real_html):
    assert 'data-config="w1c1a-131072"' not in real_html  # never ran at 128K
    row = re.search(r'<tr data-config="w1c2ap3-131072">(.*?)</tr>', real_html, re.S)
    assert row and "n/a" in row.group(1)


def test_render_numbers_match_summary(real_html):
    for s in ("1.76×", "1.94×", "2.37×", "2.36×", "2.84×", "3.85×", "1.68×", "1.81×", "147.6 s", "137.6 s"):
        assert s in real_html, s


def test_main_writes_files(tmp_path):
    out_html, out_json = tmp_path / "page" / "r.html", tmp_path / "r.json"
    rc = R.main(["--results-dir", str(REAL_RESULTS), "--out-html", str(out_html), "--out-json", str(out_json)])
    assert rc == 0
    page = out_html.read_text(encoding="utf-8")
    assert 'id="hero"' in page and "1.94×" in page
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["claude_code"]["serial_sum"] == pytest.approx(137.6, abs=0.1)


def test_main_defaults():
    p = R._parser().parse_args([])
    assert Path(p.results_dir) == R.RESULTS
    assert Path(p.out_html) == R.REPO / "reports" / "qwen38-flashnext-concurrency.html"
    assert Path(p.out_json) == R.RESULTS / "report-data.json"


# ---- review round 1: derived cold times, recall rule, band labels, hero labels ----

def test_collect_cold_ttft_median_over_served_records_of_all_streams(tmp_path):
    _stream(tmp_path, "w1c2a", 131072, "e1", 1, 1.1)
    _stream(tmp_path, "w1c2a", 131072, "e1", 2, 1.9)
    for k, ttfts in ((1, [100.0, 300.0]), (2, [200.0])):
        path = tmp_path / f"w1c2a-131072-e1-s{k}.jsonl"
        extra = [_rec("cold", t, 512.0) for t in ttfts]
        refused = dict(_rec("cold", 999.0, 512.0), error="HTTP 500: PrefillDoesNotFit", finish_reason=None)
        path.write_text(path.read_text() + "\n".join(json.dumps(r) for r in extra + [refused]) + "\n")
    c = _cfg(R.collect(tmp_path), "w1c2a", 131072)
    assert c["cold_ttft_s"] == pytest.approx(200.0)
    assert [s["session"] for s in c["needles_per_stream"]] == ["s1", "s2"]


def test_collect_cold_ttft_none_without_cold_records(tmp_path):
    _stream(tmp_path, "w1c1", 32768, "e1", 1, 1.0)
    c = _cfg(R.collect(tmp_path), "w1c1", 32768)
    assert c["cold_ttft_s"] is None and c["needles_per_stream"] == [{"session": "s1", "needles": "3/3", "ok": True}]
    assert _cfg(R.collect(tmp_path), "w1c4", 131072)["needles_per_stream"] == []


def test_collect_real_cold_ttft():
    d = R.collect(REAL_RESULTS)
    assert _cfg(d, "w1c1", 131072)["cold_ttft_s"] == pytest.approx(165.6, abs=1.0)
    assert _cfg(d, "w1c1", 262144)["cold_ttft_s"] == pytest.approx(350.8, abs=1.0)
    assert _cfg(d, "w1c2ap5", 131072)["cold_ttft_s"] == pytest.approx(327, abs=3)


def test_text_facts_only_non_derivable():
    assert set(R.TEXT_FACTS) == {"claude_code_version", "drowzeys_short_prompt_gain"}


def test_render_cold_times_come_from_data(real_html):
    side = real_html[real_html.index('id="side-requests"'):real_html.index('id="max-concurrent"')]
    assert "about 166 s" in side and "about 351 s" in side


def test_render_long_context_recall_rule_and_per_session(real_html):
    lc = real_html[real_html.index('id="long-context"'):real_html.index('id="claude-code"')]
    assert "2 of 13" in lc and "8-bit" in lc
    assert "session 1: 11/13" in lc and "session 2: 13/13" in lc
    assert "24/26" not in lc


def test_render_band_labels(real_html):
    for s in ("pass ≤ 1.5", "fail &gt; 2.0", "warning"):
        assert s in real_html[real_html.index('id="sessions"'):real_html.index('id="throughput"')], s


def test_render_hero_labels_by_context(tmp_path):
    _stream(tmp_path, "w1c2a", 131072, "e1", 1, 1.1)
    _stream(tmp_path, "w1c2a", 131072, "e1", 2, 1.94)
    hero = R.render(R.collect(tmp_path))
    hero = hero[hero.index('id="hero"'):hero.index('id="how-it-works"')]
    assert "n/a at 32K and 1.94× at 128K" in hero


def test_illustration_labels_fit_their_boxes():
    for svg in (R.ILLUSTRATION_TIMELINE, R.ILLUSTRATION_BATCH):
        rects, checked = [], 0
        for m in re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"'
                             r'|<text x="([\d.]+)" y="([\d.]+)" text-anchor="middle"[^>]*>([^<]*)</text>', svg):
            if m.group(1):
                x, y, w, h = (float(m.group(i)) for i in range(1, 5))
                assert x >= 0 and x + w <= 760, "box leaves the viewBox"
                rects.append((x, y, w, h))
                continue
            tx, ty, label = float(m.group(5)), float(m.group(6)), html.unescape(m.group(7))
            box = [r for r in rects if abs(r[0] + r[2] / 2 - tx) < 0.6 and r[1] <= ty <= r[1] + r[3]]
            if not box:
                continue  # free-standing label (caption, "waits here")
            checked += 1
            assert len(label) * 6.6 <= box[-1][2] - 4, label
        assert svg is R.ILLUSTRATION_BATCH or checked >= 10


def test_chart_css_uses_sans_and_tabular_nums(real_html):
    rule = re.search(r"\.chart svg\{([^}]*)\}", real_html).group(1)
    assert "font-family:var(--sans)" in rule and "var(--mono)" not in rule
    assert "font-variant-numeric:tabular-nums" in rule


def test_chart_text_is_13_units():
    svgs = [R.svg_grouped_bars(GROUPS, ["A", "B"], 3.0, bands=[(1.5, "pass")]), R.svg_paired_bars(PAIRS),
            R.svg_dots([{"label": "x", "p50": 1.0, "p95": 2.0}])]
    for svg in svgs:
        assert set(re.findall(r'font-size="([\d.]+)"', svg)) == {"13"}


def test_dots_row_labels_fit_left_gutter():
    svg = R.svg_dots([{"label": "2 (limit 1), 128K", "p50": 1.0, "p95": 2.0}])
    x = float(re.search(r'<text x="([\d.]+)" y="[\d.]+" text-anchor="end"', svg).group(1))
    assert x - len("2 (limit 1), 128K") * 7.2 >= 0  # 13-unit sans, about 7 units per character


def test_render_wording_fixes(real_html):
    hero = real_html[real_html.index('id="hero"'):real_html.index('id="how-it-works"')]
    assert "each turn takes about twice as long" in hero and "about half its speed" not in hero
    assert "barely grows" not in real_html and "the same pattern" not in real_html
    assert "at most 1.44×" in real_html and "1.26×" in real_html
    assert "at least 11 of every 13 answered checks (85%) per session at 256K" in real_html
    assert "Refused / HTTP errors (client)" in real_html and "server log can count more refusals" in real_html
    cc = real_html[real_html.index('id="claude-code"'):real_html.index('id="pds"')] if 'id="pds"' in real_html else real_html
    assert "2 repetitions per task" in cc and "“together” has 3" in cc


def test_public_names_carry_context_for_all_arms():
    for code in ("w1c3a", "w1c4", "w1c4a"):
        assert R._public_name(code, 32768).endswith(", 32K")


def test_splash_absent_renders_no_section(tmp_path):
    assert R.collect_splash(tmp_path) is None
    assert 'id="splash"' not in R.render(R.collect(tmp_path, tmp_path))


@pytest.mark.skipif(not any(R.SPLASH_RESULTS.glob("k2c1-*-e1-s1.jsonl")), reason="no Splash results")
def test_splash_section_real_data():
    page = R.render(R.collect(REAL_RESULTS, R.SPLASH_RESULTS))
    sec = re.search(r'<section class="block card" id="splash">.*?</section>', page, re.S).group(0)
    assert "partial" not in sec and "pending" not in sec and "n/a" not in sec.split("<details")[0].split("<ol")[1]
    assert "Two Claude Code sessions" in sec and "sooner than the two tasks" in sec
    assert "Four sessions at 128K" in sec and "--state-format bf16" in sec and "not run" not in sec
    assert '<a href="#splash">' in page
    assert sorted({m.group(0) for m in INSIDER.finditer(_public_body(page))}) == []
    assert not re.search(r"\bk2c\w*", _public_body(page))


# ---- scenario payload, experience bands and Terminal-Bench status (Task 3 of the 2026-10-30 plan) ----

SPLASH_RESULTS = R.SPLASH_RESULTS
HAS_SPLASH = any(SPLASH_RESULTS.glob("k2c1-*-e1-s1.jsonl"))
FAKE_MLX_SUMMARY = {
    "prefix": "rm", "profiles": {
        "small": {"tasks": ["a", "b"], "alone_s": {"a": 50.0, "b": 48.0}, "pair_s": {"a": 70.0, "b": 72.0},
                  "pair_wall_s": 73.0, "serial_sum_s": 98.0, "time_saved": 0.255, "turns": {"a": 10, "b": 6},
                  "task_done": True, "errors": 0},
        "realistic": {"tasks": ["c", "d"], "alone_s": {"c": 400.0, "d": 380.0}, "pair_s": {"c": 600.0, "d": 590.0},
                      "pair_wall_s": 610.0, "serial_sum_s": 780.0, "time_saved": 0.218, "turns": {"c": 30, "d": 28},
                      "task_done": True, "errors": 0}},
    "requests": {
        "alone": {"n": 40, "max_concurrent": 1, "first_prompt_ttft_s": 30.0, "new_tokens_p50": 600,
                  "warm": {"n": 38, "ttft_p50": 1.5, "ttft_p90": 2.5, "tps_p50": 80.0, "tps_min": 60.0, "tps_max": 90.0}},
        "pair": {"n": 80, "max_concurrent": 2, "first_prompt_ttft_s": 40.0, "new_tokens_p50": 600,
                 "warm": {"n": 76, "ttft_p50": 3.1, "ttft_p90": 6.0, "tps_p50": 50.0, "tps_min": 30.0, "tps_max": 85.0}}}}


@pytest.mark.parametrize("metric,value,expected", [
    ("ttft", 2.0, "good"), ("ttft", 2.01, "ok"), ("ttft", 5.0, "ok"), ("ttft", 5.01, "poor"),
    ("tps", 60.0, "good"), ("tps", 59.9, "ok"), ("tps", 29.9, "poor"), ("tps", 30.0, "ok"),
    ("first_prompt", 30.0, "good"), ("side", 60.0, "ok"), ("side", 61.0, "poor"), ("ttft", None, None)])
def test_band_boundaries(metric, value, expected):
    assert R.band(metric, value) == expected


def test_read_tbench_status_missing_and_bad(tmp_path):
    assert R.read_tbench_status(tmp_path / "none.json") is None
    (tmp_path / "bad.json").write_text("{")
    assert R.read_tbench_status(tmp_path / "bad.json") is None
    (tmp_path / "ok.json").write_text(json.dumps({"server": "mlx-serve 26.10.3", "done": 51, "total": 89}))
    assert R.read_tbench_status(tmp_path / "ok.json")["done"] == 51


def test_servers_and_recommended():
    assert [s["key"] for s in R.SERVERS] == ["splash", "mlx"] and R.RECOMMENDED == "splash"
    assert R.LEGACY["key"] == "legacy"


@pytest.mark.skipif(not HAS_SPLASH, reason="no Splash results")
def test_collect_scenarios_real_splash_and_legacy():
    data = R.collect(REAL_RESULTS, SPLASH_RESULTS, claude_dirs={"splash": SPLASH_RESULTS, "legacy": REAL_RESULTS},
                     tbench_status=Path("/none"))
    sc = data["scenarios"]
    two = sc["two_sessions"]["splash"]
    assert two["ttft_pair_p50"] == pytest.approx(1.9, abs=0.1) and two["ttft_alone_p50"] == pytest.approx(0.8, abs=0.1)
    assert two["max_concurrent"] == 2 and two["time_saved"] == pytest.approx(0.24, abs=0.01)
    assert two["tasks"]["small"]["a"]["alone_s"] == pytest.approx(41.0, abs=0.1)
    assert sc["one_session"]["splash"]["warm_ttft_source"] == "claude"
    assert sc["one_session"]["mlx"]["warm_ttft_source"] == "synthetic"
    assert sc["one_session"]["splash"]["first_prompt_s"] == pytest.approx(23.7, abs=0.1)
    assert sc["one_session"]["mlx"]["first_prompt_s"] is None
    assert sc["by_n"]["mlx"][4]["legacy"] is True and sc["by_n"]["splash"][4]["legacy"] is False
    assert sc["by_n"]["splash"][4]["turn_s"] == pytest.approx(28.0, abs=0.1)
    assert sc["by_n"]["mlx"][2]["turn_s"] == pytest.approx(15.6, abs=0.1)
    assert sc["two_sessions"]["mlx"]["ttft_pair_p50"] is None
    assert sc["worst_case"]["splash"]["best_setting"]["turn_s"] == pytest.approx(10.8, abs=0.1)
    assert sc["worst_case"]["mlx"]["best_setting"] is None
    assert sc["long_256k"]["splash"]["turn_s"] == pytest.approx(12.1, abs=0.1)
    assert sc["long_256k"]["mlx"]["turn_s"] == pytest.approx(18.6, abs=0.3) and sc["long_256k"]["mlx"]["legacy"] is True
    assert sc["verdict"]["one"]["word"] == "Yes" and sc["verdict"]["two"]["word"].startswith("Yes")
    assert sc["verdict"]["many"]["word"] == "No"
    assert data["servers"] == R.SERVERS and data["recommended"] == "splash" and data["tbench"] is None


def test_collect_scenarios_without_splash_is_all_missing(tmp_path):
    sc = R.collect(REAL_RESULTS, None, claude_dirs={"legacy": REAL_RESULTS}, tbench_status=tmp_path / "none")["scenarios"]
    assert all(row["cells"]["splash"] == "missing" for row in sc["coverage"])
    assert sc["verdict"]["one"]["word"] is None
    assert sc["two_sessions"]["splash"]["ttft_pair_p50"] is None


@pytest.mark.skipif(not HAS_SPLASH, reason="no Splash results")
def test_collect_scenarios_with_campaign_b_fixture(tmp_path):
    (tmp_path / "claude-summary.json").write_text(json.dumps(FAKE_MLX_SUMMARY))
    sc = R.collect(REAL_RESULTS, SPLASH_RESULTS, claude_dirs={"splash": SPLASH_RESULTS, "mlx": tmp_path},
                   tbench_status=Path("/none"))["scenarios"]
    assert sc["two_sessions"]["mlx"]["ttft_pair_p50"] == 3.1
    assert sc["one_session"]["mlx"]["warm_ttft_source"] == "claude" and sc["one_session"]["mlx"]["tps_hi"] == 90.0
    assert "realistic" in sc["one_session"]["mlx"]["tasks"]
    assert next(r for r in sc["coverage"] if r["scenario"] == "Two Claude Code sessions")["cells"]["mlx"] == "measured"


@pytest.mark.skipif(not HAS_SPLASH, reason="no Splash results")
def test_coverage_marks_running_tbench(tmp_path):
    (tmp_path / "tb.json").write_text(json.dumps({"server": "mlx-serve 26.10.3", "done": 51, "total": 89}))
    data = R.collect(REAL_RESULTS, SPLASH_RESULTS, claude_dirs={}, tbench_status=tmp_path / "tb.json")
    row = next(r for r in data["scenarios"]["coverage"] if r["scenario"].startswith("Agent quality"))
    assert row["cells"] == {"splash": "missing", "mlx": "running", "legacy": "missing"}
    assert data["tbench"]["done"] == 51


# ---- the page by use scenario (Task 5 of the 2026-10-30 plan) ----

@pytest.fixture(scope="module")
def full_html():
    dirs = {"splash": SPLASH_RESULTS, "legacy": REAL_RESULTS} if HAS_SPLASH else {"legacy": REAL_RESULTS}
    return R.render(R.collect(REAL_RESULTS, SPLASH_RESULTS if HAS_SPLASH else None, claude_dirs=dirs,
                              tbench_status=Path("/none")))


def _section_of(page, sid):
    return re.search(rf'<section id="{sid}".*?</section>', page, re.S).group(0)


def test_render_sections_in_order(full_html):
    ids = re.findall(r'<section id="([a-z]+)"', full_html)
    assert ids == ["verdict", "one", "two", "worst", "many", "long", "recommend", "coverage", "appendix"]


@pytest.mark.skipif(not HAS_SPLASH, reason="no Splash results")
def test_hero_words_and_numbers_from_payload(full_html):
    sc = json.loads(_payload(full_html))["scenarios"]
    hero = _section_of(full_html, "verdict")
    assert sc["verdict"]["one"]["word"] in hero and sc["verdict"]["two"]["word"] in hero
    assert f'{sc["two_sessions"]["splash"]["ttft_pair_p50"]:.1f} s' in hero
    assert "finishes 24% sooner" in hero


def test_every_chart_has_title_tooltips_and_table_view(full_html):
    body = full_html.split('<section id="appendix"')[0]
    n_svg = body.count('role="img"')
    assert n_svg >= 10
    assert body.count('class="tbl"') >= n_svg - 1  # the timeline schematic has no table
    assert body.count("<title>") >= 20
    assert body.count('class="legend"') >= 5


@pytest.mark.skipif(not HAS_SPLASH, reason="no Splash results")
def test_mlx_pair_cells_are_hatched_until_campaign_b(full_html):
    two = _section_of(full_html, "two")
    assert 'url(#hatch)' in two and ">n/m</text>" in two


def test_render_without_splash_or_claude(tmp_path):
    page = R.render(R.collect(REAL_RESULTS, None, claude_dirs={}, tbench_status=tmp_path / "none"))
    assert '<section id="coverage"' in page and page.count("○") >= 8 and "Traceback" not in page
    assert ">n/m<" in page


def test_render_body_has_no_insider_terms(full_html):
    body = full_html.split('<section id="appendix"')[0]
    assert sorted({m.group(0) for m in INSIDER.finditer(_public_body(body))}) == []


def test_legacy_only_in_appendix(full_html):
    body = full_html.split('<section id="appendix"')[0]
    body = re.sub(r"\([^)]*26\.10\.1[^)]*\)", "", body)  # a parenthesised marker beside a value is allowed
    assert "26.10.1" not in body


def test_hatch_pattern_defined_once(full_html):
    assert full_html.count('<pattern id="hatch"') == 1 and "--good:" in full_html and "--s1l:" in full_html
