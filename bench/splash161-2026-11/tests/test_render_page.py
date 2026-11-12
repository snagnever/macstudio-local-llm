"""Tests of render_page.py: the public Splash 1.6.1 vs 1.5.0 page.

The page restates the stage reports (results/etapa*.md). Two headline numbers are recomputed here from the
committed JSONL: the Task 7 probe ratio and the Task 5 largest gaps."""
import json
import re
import statistics
from pathlib import Path

import pytest
from conftest import HERE, load

RESULTS = HERE / "results"
REPO = HERE.parents[1]


def rows(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture(scope="module")
def rp():
    return load("render_page")


@pytest.fixture(scope="module")
def page(rp):
    return rp.render(rp.collect(), generated="2026-11-12")


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.split('<script id="data"')[0]))


def test_every_question_passes_and_the_launcher_switches(rp, page):
    d = rp.collect()
    assert [d["verdicts"][str(n)]["result"] for n in range(1, 8)] == ["pass"] * 7
    t = text_of(page)
    assert "Switches to 1.6.1" in t and "PLE auto" in t


def test_two_256k_sessions_match_the_stage_report(page):
    # results/etapa3-concorrencia.md: worst stream 16.07 s on 1.5.0, 16.63 s auto, 16.03 s off; 1.6.0 was +65%.
    t = text_of(page)
    assert "16.07 s" in t and "16.63 s" in t and "16.03 s" in t
    assert "+3.5%" in t and "+65%" in t


def test_soak_probe_ratio_recomputed_from_jsonl(rp):
    recs = rows(RESULTS / "soak-h161.jsonl")
    probe = lambda label: statistics.median(r["decode_tok_s"] for r in recs
                                             if r.get("kind") == "probe" and r["label"] == label)
    ratio = probe("pair43") / probe("pre")
    assert round(ratio, 2) == rp.collect()["task7"]["ratio"] == 1.09


def test_memory_limit_gaps_recomputed_from_jsonl(rp):
    def max_gap(run):
        return max(g for r in rows(RESULTS / f"churn-{run}.jsonl") for g in (r.get("gaps_s") or []))
    t5 = rp.collect()["task5"]
    assert round(max(max_gap("150-r1"), max_gap("150-r2")), 1) == t5["old_max_gap_s"]
    assert round(max(max_gap("161-r1"), max_gap("161-r2")), 1) == t5["new_max_gap_s"]


def test_page_is_self_contained_and_links_the_sources(page):
    assert page.startswith("<!doctype html>")
    assert "<script src=" not in page
    assert "bench/splash161-2026-11/results" in page and "bench/splash161-2026-11/plan.md" in page
    assert 'href="qwen38-flashnext-splash160.html"' in page


def test_index_has_a_card_for_the_page():
    index = (REPO / "reports" / "index.html").read_text(encoding="utf-8")
    assert 'href="qwen38-flashnext-splash161.html"' in index
    assert '<span class="path">qwen38-flashnext-splash161.html</span>' in index
