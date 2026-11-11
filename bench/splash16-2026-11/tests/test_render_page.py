"""Tests of render_page.py: the numbers of the public Splash 1.6.0 vs 1.5.0 page and its HTML.

The headline numbers are recomputed here from the committed JSONL, independently of render_page, and checked
against both the stage reports (results/etapa*.md) and collect()."""
import json
import re
import statistics
from pathlib import Path

import pytest
from conftest import HERE, load

RESULTS = HERE / "results"


def rows(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture(scope="module")
def rp():
    return load("render_page")


@pytest.fixture(scope="module")
def data(rp):
    return rp.collect()


@pytest.fixture(scope="module")
def page(rp, data):
    return rp.render(data, generated="2026-11-11")


# ---- collect(): shape ----

def test_collect_is_a_plain_json_dict(data):
    assert isinstance(data, dict)
    assert json.loads(json.dumps(data)) == data
    for key in ("rig", "weights", "dates", "verdicts", "task1", "task2", "task3", "task4", "claude_code",
                "task5", "task6", "task7"):
        assert key in data


def test_verdicts_follow_the_summary(data):
    v = data["verdicts"]
    assert v["4"]["result"] == "fail"
    assert v["5"]["result"] == "pass"
    assert v["3"]["skipped"] and v["6"]["skipped"]
    assert not any(v[str(n)]["skipped"] for n in (1, 2, 4, 5, 7))


# ---- headline numbers recomputed from JSONL ----

def _pairs(tag):
    n = 0
    while (RESULTS / f"cc-soak{tag}p{n + 1}-c.json").exists() and (RESULTS / f"cc-soak{tag}p{n + 1}-d.json").exists():
        n += 1
    return n


def test_task7_pair_counts_match_jsonl(data):
    assert (_pairs("g"), _pairs("f")) == (43, 38)  # etapa7-agente-4h.md
    assert data["task7"]["new"]["pairs"] == 43 and data["task7"]["old"]["pairs"] == 38


def test_task7_hourly_probe_matches_report(data):
    # etapa7-agente-4h.md, "Por hora": pairs per hour and the probe p50 per hour.
    new, old = data["task7"]["new"]["hours"], data["task7"]["old"]["hours"]
    assert [h["pairs"] for h in new] == [10, 11, 11, 10, 1]
    assert [h["pairs"] for h in old] == [9, 8, 10, 10, 1]
    assert [round(h["probe_p50"], 1) for h in new] == [100.1, 101.4, 99.8, 100.2, 90.3]
    assert [round(h["probe_p50"], 1) for h in old] == [100.6, 102.7, 102.4, 102.3, 97.8]


def test_task7_probe_ratio_and_denied(data):
    new, old = data["task7"]["new"], data["task7"]["old"]
    assert round(new["probe_pre"], 1) == 99.1 and round(old["probe_pre"], 1) == 101.6
    assert round(new["probe_end"] / new["probe_pre"], 2) == 0.91
    assert round(old["probe_end"] / old["probe_pre"], 2) == 0.96
    assert (new["denied_reservations"], old["denied_reservations"]) == (11203, 71422)
    assert (new["task_done"], old["task_done"]) == ("85/86", "75/76")


def _max_gap(run):
    return max(g for r in rows(RESULTS / f"churn-{run}.jsonl") if r["kind"] == "request" for g in r.get("gaps_s") or [])


def test_task5_max_gap_matches_jsonl(data):
    old = max(_max_gap("150-r1"), _max_gap("150-r2"))
    new = max(_max_gap("160-r1"), _max_gap("160-r2"))
    assert (round(old, 1), round(new, 1)) == (48.8, 2.5)  # etapa5-pressao.md
    by_run = {r["run"]: r for r in data["task5"]["runs"]}
    assert round(by_run["150-r2"]["max_gap_s"], 1) == 48.8
    assert round(by_run["160-r1"]["max_gap_s"], 1) == 2.5
    assert [by_run[k]["requests"] for k in ("150-r1", "160-r1", "160-r2", "150-r2")] == [167, 217, 217, 163]
    assert [by_run[k]["gaps_over_5s"] for k in ("150-r1", "160-r1", "160-r2", "150-r2")] == [6, 0, 0, 7]


def _t_turno(path):
    """Median client TTFT of tool_turn + 512 tokens at the median warm decode, served records only."""
    recs = [r for r in rows(path) if r.get("finish_reason") in ("stop", "length") and not
            (r.get("error") and not str(r["error"]).startswith("finish_reason:length"))]
    ttft = statistics.median(((r.get("client_ttft_ms") if r.get("client_ttft_ms") is not None else r["ttft_ms"])
                              / 1000) for r in recs if r["scenario"] == "tool_turn")
    decode = statistics.median(r["decode_tps"] for r in recs if r["scenario"] in ("identical", "append", "tool_turn"))
    return round(ttft + 512 / decode, 1)


def test_task4_worst_stream_matches_jsonl(data):
    control = max(_t_turno(RESULTS / "c150" / f"k2c2LL-262144-c1-s{k}.jsonl") for k in (1, 2))
    new = max(_t_turno(RESULTS / f"k2c2LL-262144-g1-s{k}.jsonl") for k in (1, 2))
    assert (control, new) == (14.8, 24.4)  # etapa4-concorrencia.md
    ll = data["task4"]["k2c2LL"]
    assert ll["control"]["worst_s"] == 14.8 and ll["new"]["worst_s"] == 24.4
    assert round((ll["new"]["worst_s"] / ll["control"]["worst_s"] - 1) * 100) == 65


def test_task4_two_sessions_and_reference(data):
    t4 = data["task4"]
    assert t4["k2c2a"]["131072"]["new"]["worst_s"] == 12.5
    assert t4["k2c2a"]["131072"]["ref"]["worst_s"] == 15.4
    assert t4["k2c2a"]["32768"]["new"]["worst_s"] == 11.4
    assert round(t4["k2c2LL"]["control"]["decode_sum"], 1) == 89.8
    assert round(t4["k2c2LL"]["new"]["decode_sum"], 1) == 86.5
    assert round(t4["k2c2LL"]["ref"]["decode_sum"], 1) == 201.3
    assert t4["side_over_60s"]["k2c2a-131072"] == 1


def test_task4_claim_wait_per_boot(data):
    cw = {b["arm"]: b for b in data["task4"]["claim_wait"]}
    assert round(cw["k2c2a 128K"]["max_s"], 1) == 30.3 and round(cw["k2c2a 128K"]["total_s"], 1) == 61.4
    assert round(cw["k2c2LL 256K"]["max_s"], 1) == 30.1 and round(cw["k2c2LL 256K"]["total_s"], 1) == 190.3
    assert cw["k2c1 32K"]["max_s"] == 0 and cw["k2c2a 32K"]["max_s"] == 0


def test_claude_code_sessions(data):
    cc = data["claude_code"]
    assert cc["pair"]["new"]["wall_s"] == pytest.approx(321.4)
    assert cc["pair"]["old"]["wall_s"] == pytest.approx(398.65)
    assert cc["subagents"]["new"]["wall_s"] == pytest.approx(724.4)
    assert round((1 - cc["pair"]["new"]["wall_s"] / cc["pair"]["old"]["wall_s"]) * 100) == 19
    assert round((1 - cc["subagents"]["new"]["wall_s"] / cc["subagents"]["old"]["wall_s"]) * 100) == 25
    assert cc["pair"]["new"]["tps_min"] < cc["pair"]["old"]["tps_min"]
    assert cc["subagents"]["new"]["tps_min"] < cc["subagents"]["old"]["tps_min"]


def test_task3_aging_ratios(data):
    runs = {r["run"]: r for r in data["task3"]["runs"]}
    assert round(runs["a-150-r1"]["ratio"], 2) == 1.00
    assert round(runs["a-160-r1"]["ratio"], 2) == 0.92
    assert runs["p-150-r1"]["ratio"] is None
    # etapa3-envelhecimento.md: p-150-r1 completed 4 of 6 rounds; round 5 was cut by the user.
    assert [runs[k]["rounds"] for k in ("a-150-r1", "a-160-r1", "p-160-r1", "p-150-r1")] == [6, 6, 6, 4]
    assert round(runs["a-150-r1"]["denied_reservations"] / runs["a-160-r1"]["denied_reservations"]) == 18


def test_task2_single_stream_ratios(data):
    ratios = {b["ctx"]: round(b["ratio"], 3) for b in data["task2"]["bands"]}
    assert ratios == {32768: 0.984, 131072: 1.0, 262144: 1.0}
    assert round(data["task2"]["one_million"]["ratio"], 3) == 1.031


def test_task6_quality_from_summarize_ab(data):
    s = {r["suite"]: r for r in data["task6"]["suites"]}
    assert (s["humaneval"]["base"], s["humaneval"]["cand"]) == (147, 144)
    assert (s["gpqa"]["base"], s["gpqa"]["cand"]) == (41, 44)
    assert all(r["g1"] for r in data["task6"]["suites"])


def test_task1_restart_and_proxy(data):
    t1 = data["task1"]
    assert t1["restart"]["first_200_s"] == 24.3
    assert t1["restart"]["pass"] is True
    assert t1["proxy"]["1.5.0"]["key_hits"] >= 1 and t1["proxy"]["1.6.0"]["key_hits"] == 0
    # C7: no release reused a reply token; the second turn cached only the first prompt.
    assert set(t1["c7"]["cached"]["1.5.0"]) == {320} and set(t1["c7"]["cached"]["1.6.0"]) == {320}


# ---- render() ----

def test_render_is_self_contained(page):
    assert page.startswith("<!doctype html>")
    assert not re.search(r"<script[^>]+src=", page)
    for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', page):
        assert url.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com",
                               "https://github.com/"))


def test_render_title_and_rig(page):
    assert "<title>Splash 1.6.0 vs 1.5.0</title>" in page
    assert "Mac Studio M4 Max 128 GB" in page
    assert "0142554" in page and "IQ4_XS" in page
    assert "2026-11-06" in page and "2026-11-08" in page


def test_render_has_the_sections(page):
    for sid in ("verdict", "questions", "claude-code", "not-measured", "api", "method"):
        assert f'id="{sid}"' in page
    for n in range(1, 8):
        assert f'id="task{n}"' in page


def test_render_marks_skipped_tasks(page):
    for n in (3, 6):
        block = page.split(f'id="task{n}"')[1].split("</section>")[0]
        assert "Skipped by the user" in block and "partial" in block


def test_render_has_three_charts(page):
    assert page.count('<svg viewBox=') >= 3
    for label in ("Worst-stream turn time", "Largest decode gap", "Short-probe decode per hour"):
        assert label in page


def test_render_theme_tokens(page):
    assert "prefers-color-scheme: dark" in page
    assert ':root:not([data-theme="light"])' in page and ':root[data-theme="dark"]' in page


def test_render_keeps_out_the_upstream_draft_and_secrets(page):
    assert "relato-upstream" not in page and "upstream draft" not in page.lower()
    assert not re.search(r"\bsk-[A-Za-z0-9]{8,}", page)
    assert "Bearer " not in page


def test_render_headline_numbers(page):
    for s in ("65%", "24.4 s", "14.8 s", "48.8 s", "2.5 s", "43", "38", "30.3 s"):
        assert s in page


def test_render_embeds_the_payload(page, data):
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S)
    assert m and json.loads(m.group(1)) == data


def test_render_size(page):
    assert len(page.encode("utf-8")) < 150_000


def test_main_writes_page_and_payload(rp, tmp_path):
    html_path, json_path = tmp_path / "page.html", tmp_path / "page-data.json"
    assert rp.main(["--out-html", str(html_path), "--out-json", str(json_path)]) == 0
    assert html_path.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert json.loads(json_path.read_text(encoding="utf-8"))["task7"]["new"]["pairs"] == 43
