import json
import re
import sys
from pathlib import Path

import pytest

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "scripts"))
import render_page as R  # noqa: E402

REAL_RESULTS = CAMPAIGN / "results"
REAL_REPORTS = CAMPAIGN.parent / "engine-updates-2026-10" / "results" / "reports-2026-10.json"


def b2(idx, ok, s, fin="stop", comp=100, rc=10, **extra):
    return {"dataset_idx": idx, "lcb_question_id": None, "correct": ok, "elapsed_s": s,
            "finish_reason": fin, "completion_tokens": comp, "reasoning_chars": rc, **extra}


def tool(cid, ok, t1, t2=None, multi=False):
    return {"case_id": cid, "score_pass": ok, "turn_1_elapsed_s": t1, "turn_2_elapsed_s": t2,
            "multi_turn": multi, "turn_1_finish_reason": "tool_calls", "completion_tokens": 40}


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def speed_entry(t):
    return {"cold_ttft_s": 30.0, "warm_ttft_s": {"identical": 0.2, "append": 1.8, "tool_turn": 1.8},
            "hit": {"identical": 1.0, "append": 0.96, "tool_turn": 0.96}, "prefill_tps": 790.0,
            "decode_tps": 80.0, "t_turno_s": t, "correctness": "ok", "wired_peak_gb": 96.0,
            "swap_delta_gb": 0, "mtp_acceptance": 0.8, "errors": 0, "n": 13, "gates_failed": [], "warnings": []}


def group(arm, cand, ctx, canonical, t):
    return {"arm": arm, "cand": cand, "context": ctx, "canonical": canonical, "mode": "canonical",
            "t_turno_s": t, "cold_ttft_s": 40.0, "ttft_s": {"tool_turn": 2.4}, "hit": {"tool_turn": 0.96},
            "decode_tps": 66.0, "prefill_tps": 550.0, "mtp_acceptance": None, "wired_peak_gb": 91.0,
            "campaign": "engine-updates-2026-10", "gates_failed": []}


@pytest.fixture
def fake(tmp_path):
    res = tmp_path / "results"
    for prof in ("t1", "t0"):
        write_jsonl(res / "ab" / prof / "n2" / "gpqa.jsonl",
                    [b2(1, True, 60.0), b2(2, False, 100.0, fin="length"), b2(3, True, 20.0)])
        write_jsonl(res / "ab" / prof / "w1" / "gpqa.jsonl",
                    [b2(1, True, 20.0), b2(2, True, 30.0), b2(3, False, 10.0)])
        write_jsonl(res / "ab" / prof / "n2" / "jdhodges.jsonl",
                    [tool("a", True, 2.0), tool("b", True, 3.0, 5.0, True), tool("c", False, 4.0)])
        write_jsonl(res / "ab" / prof / "w1" / "jdhodges.jsonl",
                    [tool("a", True, 1.0), tool("b", True, 2.0, 7.0, True), tool("c", True, 3.0)])
    # w1 has no IF run in t0: the suite must show as missing, not disappear.
    write_jsonl(res / "ab" / "t1" / "n2" / "if.jsonl", [{"id": "if01", "passed": True, "elapsed_s": 2.0,
                                                         "finish_reason": "stop", "completion_tokens": 30}])
    write_jsonl(res / "ab" / "t1" / "w1" / "if.jsonl", [{"id": "if01", "passed": False, "elapsed_s": 1.0,
                                                         "finish_reason": "stop", "completion_tokens": 30}])
    write_jsonl(res / "ab" / "t0" / "n2" / "if.jsonl", [{"id": "if01", "passed": True, "elapsed_s": 2.0,
                                                         "finish_reason": "stop", "completion_tokens": 30}])
    (res / "humaneval-regrade.json").write_text(json.dumps(
        {"n2-t1": {"n": 164, "strict": 144, "with_imports": 158}}), encoding="utf-8")
    (res / "tturno-summary.json").write_text(json.dumps(
        {"n2@32768": speed_entry(8.1), "w1@32768": speed_entry(7.9),
         "n2@131072": speed_entry(8.9), "w1@131072": speed_entry(8.6)}), encoding="utf-8")
    rep = tmp_path / "reports.json"
    rep.write_text(json.dumps({"rig": [{"lab": "Chip", "val": "Apple M4 Max"}], "groups": [
        group("o1", "o1", 32768, True, 10.06), group("m1p", "m1", 32768, True, 8.84),
        group("m1x", "m1", 131072, True, 15.1), group("m1s", "m1", 131072, False, None),
        group("n2", "n2", 32768, True, 8.23),
    ]}), encoding="utf-8")
    return res, rep


def test_quality_counts_per_profile_and_arm(fake):
    d = R.collect(*fake)
    q = d["quality"]["t1"]
    assert q["n2"]["gpqa"] == {"n": 3, "passed": 2, "missing": False}
    assert q["w1"]["gpqa"]["passed"] == 2


def test_missing_suite_is_marked_not_dropped(fake):
    d = R.collect(*fake)
    assert d["quality"]["t0"]["w1"]["if"] == {"n": 0, "passed": None, "missing": True}
    assert d["time"]["t0"]["if"]["arms"]["w1"]["missing"] is True
    assert d["time"]["t0"]["if"]["ratio"] is None


def test_time_stats_points_and_ratio(fake):
    t = R.collect(*fake)["time"]["t1"]["gpqa"]
    n2 = t["arms"]["n2"]
    assert n2["median_s"] == 60.0 and n2["total_s"] == 180.0 and n2["truncated"] == 1
    assert {"id": "2", "s": 100.0, "ok": False, "trunc": True, "tok": 100} in n2["points"]
    assert t["ratio"] == round(20.0 / 60.0, 2)


def test_tool_latency_turn2_only_multi_turn(fake):
    lat = R.collect(*fake)["tool_latency"]["t1"]["jdhodges"]
    assert lat["n2"]["turn1_median_s"] == 3.0
    assert lat["n2"]["turn2_median_s"] == 5.0 and lat["n2"]["turn2_n"] == 1
    assert lat["w1"]["passed"] == 3 and lat["w1"]["n"] == 3


def test_humaneval_regrade_passed_through(fake):
    assert R.collect(*fake)["humaneval_regrade"]["n2-t1"]["with_imports"] == 158


def test_speed_uses_same_session_arms_then_canonical_groups(fake):
    sp = R.collect(*fake)["speed"]
    rows32 = {r["arm"]: r for r in sp["32768"]}
    assert rows32["w1"]["t_turno_s"] == 7.9 and rows32["w1"]["source"] == "swift15-flashnext-2026-10"
    assert rows32["m1p"]["series"] == "m1" and rows32["m1p"]["ttft_tool_turn_s"] == 2.4
    # The n2 group from Etapa G does not become a second row: it is the drift reference.
    assert [r["arm"] for r in sp["32768"]].count("n2") == 1
    assert sp["drift"]["32768"] == 8.23
    arms128 = [r["arm"] for r in sp["131072"]]
    assert "m1x" in arms128 and "m1s" not in arms128


def test_series_without_group_in_band_is_listed_as_absent(fake):
    rows128 = {r["arm"]: r for r in R.collect(*fake)["speed"]["131072"]}
    assert rows128["o1"]["t_turno_s"] is None and rows128["o1"]["absent"]


@pytest.mark.skipif(not REAL_REPORTS.is_file(), reason="reports-2026-10.json not found")
def test_real_data_matches_summary_md():
    d = R.collect(REAL_RESULTS, REAL_REPORTS)
    hi = d["humaneval_regrade"]
    assert [hi[k]["with_imports"] for k in ("n2-t1", "w1-t1", "n2-t0", "w1-t0")] == [158, 158, 155, 157]
    assert [d["quality"][p][a]["gpqa"]["passed"] for p in ("t1", "t0") for a in ("n2", "w1")] == [45, 43, 39, 42]
    g = d["time"]["t1"]["gpqa"]["arms"]
    assert (g["n2"]["median_s"], g["w1"]["median_s"]) == (63.9, 22.3)
    assert d["time"]["t1"]["gpqa"]["ratio"] == 0.35
    rows = {r["arm"]: r for r in d["speed"]["131072"]}
    assert rows["w1"]["t_turno_s"] == 8.6 and rows["m1x"]["t_turno_s"] == 15.1


def test_collect_adds_rate_split_and_time_per_correct(fake):
    res, rep = fake
    write_jsonl(res / "ab" / "t1" / "n2" / "gpqa.jsonl",
                [b2(1, True, 60.0, tok_s=70.0, reasoning_tokens=900, visible_tokens=4),
                 b2(2, False, 100.0, fin="length", tok_s=74.0, reasoning_tokens=5000, visible_tokens=4),
                 b2(3, True, 20.0, tok_s=72.0, reasoning_tokens=300, visible_tokens=6)])
    a = R.collect(res, rep)["time"]["t1"]["gpqa"]["arms"]["n2"]
    assert a["median_tok_s"] == 72.0
    assert (a["median_reasoning_tokens"], a["median_visible_tokens"]) == (900, 4)
    assert a["sec_per_correct"] == 90.0 and a["total_completion"] == 300
    assert a["points"][0]["tok"] == 100


def test_collect_counts_questions_the_candidate_finished_first(fake):
    t = R.collect(*fake)["time"]
    assert t["t1"]["gpqa"]["paired"] == {"n": 3, "faster": 3}
    assert t["t0"]["if"]["paired"] is None  # w1 has no IF in t0


def test_collect_splits_livecodebench_by_difficulty(fake):
    res, rep = fake
    rows = [dict(b2(1, True, 5.0), lcb_question_id="a", lcb_difficulty="easy"),
            dict(b2(2, False, 300.0, fin="length"), lcb_question_id="b", lcb_difficulty="hard"),
            dict(b2(3, True, 100.0), lcb_question_id="c", lcb_difficulty="hard")]
    write_jsonl(res / "ab" / "t1" / "n2" / "livecodebench.jsonl", rows)
    diff = R.collect(res, rep)["lcb_difficulty"]["t1"]["n2"]
    assert diff["easy"] == {"n": 1, "median_s": 5.0, "passed": 1}
    assert diff["hard"] == {"n": 2, "median_s": 200.0, "passed": 1}  # the truncated answer does not count


# ---- render() and main() ----

SECTIONS = ("tldr", "profile-switch", "time-per-task", "why", "accuracy", "detail", "short-tasks", "agent-turn",
            "numbers", "setup", "limits")


def _section(html, sid):
    return re.search(rf'id="{sid}".*?</section>', html, re.S).group(0)


def _visible_text(html):
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<title>.*?</title>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def test_render_has_every_section(fake):
    html = R.render(R.collect(*fake))
    for sid in SECTIONS:
        assert f'id="{sid}"' in html, sid


def test_render_profile_switch_shows_t1_hides_t0(fake):
    html = R.render(R.collect(*fake))
    assert 'data-set-profile="t1"' in html and 'data-set-profile="t0"' in html
    assert '<html lang="en" data-profile="t1">' in html
    assert 'class="prof prof-t0"' in html and 'class="prof prof-t1"' in html


def test_render_leaves_no_placeholder(fake):
    assert not re.search(r"__[A-Z_]+__", R.render(R.collect(*fake)))


def test_render_marks_missing_suite_nd(fake):
    html = R.render(R.collect(*fake))
    rows = re.findall(r'<tr data-suite="if">.*?</tr>', html, re.S)
    assert any("n/d" in r for r in rows)


def test_render_escapes_text(fake):
    d = R.collect(*fake)
    d["stacks"]["n2"]["weights"] = "<b>x</b>"
    html = R.render(d)
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "<b>x</b>" not in html


def test_render_strip_plot_has_one_mark_per_question(fake):
    html = R.render(R.collect(*fake))
    panel = re.search(r'<figure class="strip" data-profile="t1" data-suite="gpqa">.*?</figure>', html, re.S).group(0)
    assert panel.count('class="dot n2') == 3 and panel.count('class="dot w1') == 3
    assert len(re.findall(r'class="dot [^"]*\btrunc\b', panel)) == 1  # question 2 of n2 hit max_tokens
    assert "Swift 1.5 faster on 3 of 3" in panel


def test_render_uses_model_names_not_internal_vocabulary(fake):
    text = _visible_text(R.render(R.collect(*fake)))
    for word in ("n2", "w1", "G1", "G2", "G3", "gate", "promot", "daily driver", "rollback", "campaign", "T_turn",
                 "bench2", "runbook"):
        assert not re.search(rf"\b{re.escape(word)}", text, re.I), word
    assert "iQ-MLX" in text and "Swift 1.5" in text


def test_render_agent_turn_lists_only_the_two_packs(fake):
    sec = _section(R.render(R.collect(*fake)), "agent-turn")
    assert "oMLX" not in sec and "MTPLX" not in sec
    assert "within 4% of each other" in sec  # 8.6 / 8.9 = 0.966


def test_render_has_share_metadata(fake):
    html = R.render(R.collect(*fake))
    assert '<meta property="og:image" content="https://snagnever.github.io/macstudio-local-llm/' in html
    assert 'name="twitter:card" content="summary_large_image"' in html


def test_speed_words():
    assert R._speed_words(63.9 / 22.3) == "2.9× faster"
    assert R._speed_words(1 / 1.13) == "1.1× slower"
    assert R._speed_words(1.04) == "about the same"
    assert R._speed_words(None) == "n/d"


def test_main_writes_json_and_html(fake, tmp_path):
    res, rep = fake
    out, js = tmp_path / "page.html", tmp_path / "page.json"
    assert R.main(["--results", str(res), "--reports", str(rep), "--out", str(out), "--json-out", str(js)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert json.loads(js.read_text(encoding="utf-8"))["quality"]["t1"]["n2"]["gpqa"]["passed"] == 2


def test_main_data_reuses_json(fake, tmp_path):
    res, rep = fake
    js, out = tmp_path / "page.json", tmp_path / "page.html"
    js.write_text(json.dumps(R.collect(res, rep)), encoding="utf-8")
    assert R.main(["--data", str(js), "--out", str(out), "--json-out", ""]) == 0
    assert 'id="accuracy"' in out.read_text(encoding="utf-8")


@pytest.mark.skipif(not REAL_REPORTS.is_file(), reason="reports-2026-10.json not found")
def test_real_page_hero_states_the_headline_numbers():
    hero = _section(R.render(R.collect(REAL_RESULTS, REAL_REPORTS)), "tldr")
    assert "2.9× faster" in hero and "2.0× faster" in hero
    assert "−67%" in hero and "≤ 3" in hero
    assert "1.2× faster on GPQA-Diamond and 1.5× faster on LiveCodeBench" in hero  # greedy


@pytest.mark.skipif(not REAL_REPORTS.is_file(), reason="reports-2026-10.json not found")
def test_real_page_accuracy_uses_the_humaneval_grade_with_imports():
    sec = _section(R.render(R.collect(REAL_RESULTS, REAL_REPORTS)), "accuracy")
    row = re.search(r'<tr data-suite="humaneval">.*?</tr>', sec, re.S).group(0)
    assert [int(x) for x in re.findall(r">(\d+)<", row)][:2] == [158, 158]


def test_g2_uses_unrounded_medians(fake):
    res, rep = fake
    # Medians 10.04 and 8.04: rounded they give 0.80 (pass); unrounded, 8.04 > 0.8 × 10.04 (fail).
    write_jsonl(res / "ab" / "t1" / "n2" / "gpqa.jsonl", [b2(1, True, 10.04)])
    write_jsonl(res / "ab" / "t1" / "w1" / "gpqa.jsonl", [b2(1, True, 8.04)])
    assert R.collect(res, rep)["gates"]["g2"]["gpqa"]["t1"]["pass"] is False


def test_speed_table_follows_perf_lines_without_c1(fake):
    # The October perf-lines page dropped the September reference (c1); this page does the same.
    sp = R.collect(*fake)["speed"]
    assert all(r["series"] != "c1" for c in R.CONTEXTS for r in sp[c])


def test_limits_tool_token_range_comes_from_data(fake):
    # The tool-calling answers in the fixture have 40 tokens.
    assert "40 tokens per answer" in _section(R.render(R.collect(*fake)), "limits")


def test_index_card_qualifies_speedup_with_the_sampling():
    idx = (CAMPAIGN.parents[1] / "reports" / "index.html").read_text(encoding="utf-8")
    card = re.search(r'href="qwen38-flashnext-swift15.html">.*?</a>', idx, re.S).group(0)
    assert "recommended sampling" in card
