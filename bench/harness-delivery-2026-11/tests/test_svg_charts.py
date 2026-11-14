import re

import pytest

import svg_charts as sc


@pytest.fixture(scope="module")
def charts():
    return {
        "heatmap": sc.heatmap(["pi", "dsh"], ["a", "b"], {("pi", "a"): 4, ("pi", "b"): 0, ("dsh", "a"): 2, ("dsh", "b"): 3},
                              4, "t", "d"),
        "paired": sc.paired_bars(["a", "b"], [("k", "--pack-a"), ("z", "--pack-b")],
                                 {("a", "k"): 8, ("a", "z"): 5, ("b", "k"): 7, ("b", "z"): 8}, 8, "t", "d"),
        "stacked": sc.stacked_bars(["x", "y"], [("r", "--refused"), ("e", "--empty"), ("c", "--complied")],
                                   {("x", "r"): 96, ("x", "e"): 1, ("x", "c"): 3, ("y", "r"): 0, ("y", "e"): 6, ("y", "c"): 94},
                                   "t", "d"),
        "dots": sc.dot_plot(["32K", "128K"], [("z", "--pack-b")], {("32K", "z"): [1.017], ("128K", "z"): [1.051]},
                            1.0, 1.1, "×", 1.05, "t", "d"),
        "matrix": sc.matrix_diagram([("harnesses", ["a", "b", "c", "d"]), ("tasks", ["1", "2"])], "t", "d"),
    }


def test_every_chart_is_one_svg_with_title_and_desc(charts):
    for svg in charts.values():
        assert svg.count("<svg") == 1 and "<title>" in svg and "<desc>" in svg and 'role="img"' in svg


def test_charts_use_only_theme_colors(charts):
    for svg in charts.values():
        assert not re.search(r'(fill|stroke)="(?!var\(|none|currentColor)', svg)


def test_heatmap_writes_each_value_once():
    svg = sc.heatmap(["pi"], ["a", "b"], {("pi", "a"): 4, ("pi", "b"): 0}, 4, "t", "d")
    assert svg.count(">4<") == 1 and svg.count(">0<") == 1


def test_stacked_bars_sum_to_full_width(charts):
    widths = [float(w) for w in re.findall(r'<rect class="part" [^>]*width="([\d.]+)"', charts["stacked"])]
    full = float(re.search(r'data-plot-width="([\d.]+)"', charts["stacked"]).group(1))
    assert len(widths) == 6 and abs(sum(widths[:3]) - full) < 0.5 and abs(sum(widths[3:]) - full) < 0.5


def test_dot_plot_draws_the_reference_line(charts):
    assert 'class="ref"' in charts["dots"] and charts["dots"].count("<circle") == 2


def test_matrix_diagram_shows_the_product(charts):
    assert ">8<" in charts["matrix"] or "= 8" in charts["matrix"]


def test_long_labels_are_cut_with_an_ellipsis():
    svg = sc.paired_bars(["x" * 60], [("s", "--pack-a")], {("x" * 60, "s"): 1}, 1, "t", "d")
    assert "x" * 60 not in svg and "…" in svg


def test_text_is_escaped():
    assert "<b>" not in sc.heatmap(["<b>"], ["a"], {("<b>", "a"): 1}, 4, "a & b", "d")
