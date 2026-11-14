import re
import shutil
import sys

import pytest

from conftest import HERE, SCRIPTS

sys.path.insert(0, str(SCRIPTS))
import render_speed_report as rs  # noqa: E402

REPO = HERE.parents[1]
PAGE = REPO / "reports/qwen38-flashnext-uncensored-speed.html"
CTX = {"32K": 32768, "128K": 131072, "256K": 262144}


@pytest.fixture(scope="module")
def data():
    return rs.collect()


@pytest.fixture(scope="module")
def page(data):
    return rs.render(data, generated="2026-11-14")


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_collect_matches_the_stage_report(data):
    md = (HERE / "results/etapa2-um-stream.md").read_text()
    rows = ratios = 0
    for line in md.splitlines():
        m = re.match(r"\| `(\w+)` \| (\d+K) \| ([\d.]+) s \| ([\d.]+) s \| ([\d.]+) s \| [\d.]+ / ([\d.]+) \| ([\d.]+) "
                     r"\| (\d+) \| ([\d.]+) GB \|", line)
        if m:
            got = data["pooled"][(m.group(1), CTX[m.group(2)])]
            assert (got["t_turn_s"], got["cold_ttft_s"], got["warm_ttft_s"]) == tuple(float(m.group(i)) for i in (3, 4, 5))
            assert round(got["hit"], 2) == float(m.group(6)) and got["decode_tps"] == float(m.group(7))
            assert abs(got["prefill_tps"] - int(m.group(8))) <= 0.5 and got["wired_gb"] == float(m.group(9))
            rows += 1
        m = re.match(r"\| `(\w+)` \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| \*\*", line)
        if m:
            assert [data["pooled"][(m.group(1), c)]["ratio"] for c in CTX.values()] == [float(m.group(i)) for i in (2, 3, 4)]
            ratios += 1
    assert (rows, ratios) == (12, 3)


def test_collect_keeps_two_boots_per_pack_and_context(data):
    assert len(data["boots"]) == 12 and all(len(b) == 2 for b in data["boots"].values())
    assert sorted(b["decode_tps"] for b in data["boots"][("z3h", 131072)]) == [110.5, 116.3]


def test_collect_refuses_a_missing_boot(tmp_path):
    for f in (HERE / "results").glob("*-t1.0-s[0-9]*.jsonl"):
        shutil.copy(f, tmp_path)
    next(tmp_path.glob("z4h-131072-*.jsonl")).unlink()
    with pytest.raises(ValueError, match="z4h"):
        rs.collect(results=tmp_path)


def test_page_states_the_answer_and_its_numbers(data, page):
    t = text_of(page)
    assert rs.TITLE in t and "0% to 5% slower per agent turn" in t
    k, z = data["pooled"][("k2h", 131072)], data["pooled"][("z4h", 131072)]
    assert f"{z['t_turn_s']} s" in t and f"{k['t_turn_s']} s" in t and "1.051×" in t


def test_page_discloses_the_quantization_confound_and_the_noise(page):
    t = text_of(page)
    assert "IQ3_S" in t and "did not run the standard pack at IQ3_S" in t
    assert "two boots" in t.lower() and "up to 10%" in t and "cannot tell the packs apart" in t


def test_page_is_self_contained_without_private_data(page):
    assert "<script" not in page and "<link" not in page and "http://" not in page
    assert not re.search(r"/Users/|vitor@|MBPro", page)


def test_every_chart_has_a_data_table(page):
    figures = page.count('<figure class="chart"')
    assert figures >= 4 and page.count("<svg") == figures and page.count('<details class="tbl"') == figures


def test_page_uses_public_pack_names_outside_the_method_section(page):
    body = text_of(page.split('id="method"')[0])
    assert not re.search(r"\b(z[0-4]h?|k2h?)\b", body) and "Heretic v2" in body and "SC117" in body


def test_speed_axis_has_round_ticks(page):
    svg = page.split('id="turn"')[1].split("</svg>")[0]
    assert ">1×<" in svg and ">1.02×<" in svg and ">1.06×<" in svg


def test_published_page_is_the_current_render(data):
    strip = lambda s: re.sub(r'<span id="generated">[^<]*</span>', "", s)  # noqa: E731
    assert strip(PAGE.read_text()) == strip(rs.render(data))


def test_index_and_readme_list_the_page():
    index = (REPO / "reports/index.html").read_text()
    flash = index.split('id="flashnext"')[1].split('<section class="block"')[0]
    assert 'href="qwen38-flashnext-uncensored-speed.html"' in flash
    assert "qwen38-flashnext-uncensored-speed.html" in (REPO / "reports/README.md").read_text()


# ---- review fixes

def section(page, sid):
    return text_of(page.split(f'id="{sid}"')[1].split("<section")[0])


def test_ratio_from_unrounded_times_is_kept_beside_the_rule_ratio(data):
    z4, z2 = data["pooled"][("z4h", 131072)], data["pooled"][("z2h", 131072)]
    assert (z4["ratio"], z4["ratio_raw"], z2["ratio_raw"]) == (1.051, 1.049, 1.051)


def test_turn_section_says_the_verdict_depends_on_rounding(page):
    t = section(page, "turn")
    assert "1.049×" in t and "depends on rounding" in t
    assert "passs" not in t and "SC117 IQ3_S passes" in t and "Heretic v2 fails" in t


def test_decode_section_states_what_the_data_supports(page):
    t = section(page, "decode")
    assert "median of 3 requests" in t and "8 of the 12 pairs" in t and "Across the three sizes" in t
    assert "At a single context size I cannot tell the packs apart" in t


def test_hero_tile_agrees_with_the_warm_start_table(data, page):
    t = text_of(page)
    assert "1.53 to 1.56 s" in t and "99.6%" in t


def test_page_discloses_the_truncated_answer(page):
    assert "119 of 120" in text_of(page)


def test_method_gives_the_real_queue_order(page):
    assert "two middle slots at 128K" in section(page, "method")
