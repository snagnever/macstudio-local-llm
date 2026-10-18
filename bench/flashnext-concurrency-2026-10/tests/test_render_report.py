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


# ---- render() and main() ----

import re

SECTION_IDS = ["hero", "how-it-works", "glossary", "sessions", "throughput", "side-requests", "max-concurrent",
               "long-context", "claude-code", "pds", "learned", "upstream", "refusals", "not-measured",
               "reproduce", "terms"]
INSIDER = re.compile(r"\b(w1c\w*|T_turno|braço|aux|needle|needles|stream|streams|rig|daily driver|etapa)\b",
                     re.IGNORECASE)


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
    assert "<title>Flash-Next: how many agent sessions fit on one server?</title>" in real_html


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
    for t in ("1 session: 80 tok/s", "4 sessions: 4 × 20", "shared, not multiplied", "about"):
        assert t in R.ILLUSTRATION_BATCH


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
    assert len(p["configs"]) == 23 and p["claude_code"]["pair_wall"] == pytest.approx(147.6, abs=0.1)


def test_render_na_for_missing(tmp_path):
    page = R.render(R.collect(tmp_path))
    row = re.search(r'<tr data-config="w1c4-131072">(.*?)</tr>', page, re.S)
    assert row, "results table row for a missing configuration"
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row.group(1), re.S)
    assert cells[0] == "w1c4"
    assert cells.count("n/a") >= 4


def test_render_na_for_missing_in_real_data(real_html):
    row = re.search(r'<tr data-config="w1c1a-131072">(.*?)</tr>', real_html, re.S)
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
