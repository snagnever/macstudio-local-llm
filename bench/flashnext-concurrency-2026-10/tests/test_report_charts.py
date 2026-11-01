import re

import report_charts as C

ROWS = [{"label": "Splash", "series": "s1", "value": 0.8}, {"label": "mlx", "series": "s2", "value": None}]


def _opening_tag(svg):
    return svg[: svg.index(">") + 1]


def _line_x(svg):
    m = re.search(r'<line class="dumbbell" x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)"', svg)
    return float(m.group(1)), float(m.group(2))


def test_band_bars_rect_per_value_and_hatch_for_none():
    svg = C.svg_band_bars("Reply starts", ROWS, 6, "s", "ttft")
    assert svg.count('fill="var(--s1)"') == 1 and 'url(#hatch)' in svg and ">n/m</text>" in svg
    assert svg.count("<title>") == 1 and "Splash: 0.8 s" in svg
    assert "var(--good)" in svg and "var(--warn-s)" in svg and "var(--crit)" in svg


def test_band_bars_without_metric_has_no_band_fills():
    svg = C.svg_band_bars("Cold read", ROWS, 200, "s", None)
    assert "var(--good)" not in svg and "var(--crit)" not in svg and svg.count('fill="var(--s1)"') == 1


def test_band_bars_tps_bands_are_reversed():
    svg = C.svg_band_bars("Generation", ROWS, 160, "tok/s", "tps")
    good = svg.index("var(--good)")
    crit = svg.index("var(--crit)")
    assert crit < good  # poor sits at the left (low speed), good at the right


def test_band_bars_range_bar_uses_lo_hi():
    rows = [{"label": "Splash", "series": "s1", "value": None, "lo": 100.0, "hi": 150.0}]
    svg = C.svg_band_bars("Generation", rows, 200, "tok/s", None)
    m = re.search(r'<rect class="bar" x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', svg)
    x, w = float(m.group(1)), float(m.group(2))
    assert abs(w / (x - C.LEFT) - 0.5) < 0.02 and "100–150 tok/s" in svg  # (150-100)/100 = 0.5


def test_dumbbell_pair_faster_than_alone_has_positive_width():
    svg = C.svg_dumbbell("t", [{"label": "x", "alone": 3.0, "pair": 1.0}], 5, "s", "ttft", "s1")
    x1, x2 = _line_x(svg)
    assert x2 > x1 and svg.count("<circle") == 2 and svg.count("<title>") == 2


def test_dumbbell_none_side_draws_one_circle_and_nm():
    svg = C.svg_dumbbell("t", [{"label": "x", "alone": 1.0, "pair": None}], 5, "s", "ttft", "s1")
    assert svg.count("<circle") == 1 and ">n/m</text>" in svg and '<line class="dumbbell"' not in svg


def test_diverging_negative_left_of_axis_and_none_hatched():
    rows = [{"label": "Splash", "series": "s1", "pct": 0.24}, {"label": "old", "series": "s2", "pct": -0.07},
            {"label": "mlx", "series": "s2", "pct": None}]
    svg = C.svg_diverging("Time saved", rows, 0.5)
    rects = re.findall(r'<rect class="bar" x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', svg)
    assert len(rects) == 2
    pos_x, neg_x = float(rects[0][0]), float(rects[1][0])
    assert pos_x >= C.AXIS_X - 0.01 and neg_x < C.AXIS_X
    assert 'url(#hatch)' in svg and "+24%" in svg and "−7%" in svg


def test_lines_legacy_points_are_hollow_and_missing_point_breaks_line():
    series = [{"key": "s1", "label": "Splash", "points": {1: {"y": 6.1, "legacy": False}, 2: {"y": 15.4, "legacy": False},
                                                          3: {"y": None, "legacy": False}, 4: {"y": 28.0, "legacy": False}}},
              {"key": "s2", "label": "mlx", "points": {1: {"y": 9.0, "legacy": False}, 2: {"y": 15.6, "legacy": False},
                                                       3: {"y": 20.3, "legacy": True}, 4: {"y": 33.1, "legacy": True}}}]
    svg = C.svg_lines("Turn time", series, [1, 2, 3, 4], 35, "s")
    assert svg.count('fill="var(--surface)"') == 2  # the two legacy points are hollow
    assert svg.count("<polyline") == 2  # s1 stops at the missing point (its lone 4th point draws no line) + s2
    assert svg.count("<circle") == 7 and svg.count("<title>") == 7


def test_timeline_names_both_servers():
    svg = C.svg_timeline(("Splash 1.5.0", "mlx-serve 26.10.3"))
    assert "Splash 1.5.0" in svg and "mlx-serve 26.10.3" in svg and "Session A" in svg


def test_table_view_escapes():
    html = C.table_view(["a", "b"], [["<x>", "1"]])
    assert html.startswith('<details class="tbl">') and "&lt;x&gt;" in html and "<table>" in html


def test_svg_contract_all_builders():
    svgs = [C.svg_band_bars("t", ROWS, 6, "s", "ttft"),
            C.svg_dumbbell("t", [{"label": "x", "alone": 1.0, "pair": 2.0}], 5, "s", "ttft", "s1"),
            C.svg_diverging("t", [{"label": "x", "series": "s1", "pct": 0.1}], 0.5),
            C.svg_lines("t", [{"key": "s1", "label": "x", "points": {1: {"y": 1.0, "legacy": False}}}], [1], 2, "s"),
            C.svg_timeline(("A", "B"))]
    for svg in svgs:
        tag = _opening_tag(svg)
        assert 'role="img"' in tag and 'aria-label="' in tag and "viewBox=" in tag and "width=" not in tag
        assert not re.search(r'#[0-9a-fA-F]{3,6}\b', svg.replace("url(#hatch)", ""))  # colors only via tokens
