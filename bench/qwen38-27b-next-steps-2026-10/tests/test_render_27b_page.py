import json, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
sys.path.insert(0, str(C / "scripts"))
import render_27b_page as rp  # noqa: E402


def _speed_rows(arm, ctx, tag, t_ttft_ms, dec):
    base = {"arm": arm, "context_target": ctx, "finish_reason": "stop", "error": None, "correct": True,
            "decode_tps": dec, "ttft_ms": t_ttft_ms, "cache_hit_ratio": 0.99, "swap_delta_gb": 0.0,
            "session_id": f"{arm}-{ctx}-{tag}", "runtime": "x", "ram_peak_gb": 40.0}
    return [dict(base, scenario=s) for s in ("cold", "identical", "append", "tool_turn")]


def _write_speed(d, arm, tag, ttft, dec, ctxs=(32768, 131072)):
    for ctx in ctxs:
        (d / f"{arm}-{ctx}-t1.0-{tag}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in _speed_rows(arm, ctx, tag, ttft, dec)) + "\n")


@pytest.fixture
def results(tmp_path):
    for arm, tag, ttft, dec in (("s27r", "p0x", 9700, 32.0), ("k27", "p1x", 2500, 60.0), ("k27", "p1m", 2400, 61.0)):
        _write_speed(tmp_path, arm, tag, ttft, dec)
    q = tmp_path / "q/t1/o27q4-medium"; q.mkdir(parents=True)
    (q / "gpqa.jsonl").write_text("\n".join(json.dumps({"question_num": i, "correct": i % 2 == 0, "finish_reason": "stop",
                                                        "elapsed_s": 20.0 + i, "completion_tokens": 1500, "reasoning_chars": 4000})
                                            for i in range(4)) + "\n")
    (tmp_path / "gates.env").write_text("P1_PASS=1\nP1_BEST=k27\nP5_GO=0\n")
    return tmp_path


def test_payload_has_speed_per_effort_and_quality(results):
    p = rp.build_payload(results, w1_summary={"w1@32768": {"t_turno_s": 7.9}, "w1@131072": {"t_turno_s": 8.6}}, w1_ab=None)
    s = p["speed"]["131072"]
    assert set(s) == {"s27r-xhigh", "k27-xhigh", "k27-medium"}
    assert s["s27r-xhigh"]["t_turno_s"] == 25.7
    assert s["k27-medium"]["t_turno_s"] == round(2.4 + 512 / 61.0, 1)
    assert p["w1"]["131072"]["t_turno_s"] == 8.6
    assert p["quality"]["o27q4-medium"]["gpqa"]["passed"] == 2
    assert p["quality"]["o27q4-medium"]["gpqa"]["median_s"] == 21.5
    assert p["gates"]["P1_BEST"] == "k27"


def test_html_mentions_every_arm_and_both_bands(results, tmp_path):
    out = tmp_path / "page.html"
    rp.main(["--results", str(results), "--out", str(out), "--json-out", str(tmp_path / "pd.json"), "--no-w1"])
    html = out.read_text()
    for needle in ("s27r", "k27", "32K", "128K", "T_turno", "Time per task", "Tokens per answer", "Flash-Next"):
        assert needle in html
    assert "<script src=\"http" not in html  # self-contained, like the other reports


@pytest.mark.skipif(not (C / "results/gates.env").exists(), reason="campaign results not committed yet")
def test_real_data_renders_and_matches_decision_tables():
    p = rp.build_payload(C / "results", w1_summary=rp.load_w1_summary(), w1_ab=rp.load_w1_ab())
    assert "s27r-xhigh" in p["speed"]["131072"]
    assert p["w1"]["32768"]["t_turno_s"] == 7.9


# --- extra coverage: arms table, missing data, medium-only arm, w1 reference, loops/empty ---

def test_arms_table_ids_and_updated_meanings():
    ids = [a[0] for a in rp.ARMS]
    assert ids == ["s27r", "k27", "o27q8", "o27q4", "r27d", "r27m", "o27sw", "l27", "l27n"]
    arms = {a[0]: a for a in rp.ARMS}
    assert arms["r27d"][1] == "mlx-serve 26.10.2 DFlash2 drafter only (--no-mtp)"
    assert arms["r27m"][1] == "mlx-serve 26.10.2 MTP head only (--no-drafter)"
    assert arms["k27"][2] == "Splash 1.3.1"


def test_html_lists_every_arm_id_and_section(results, tmp_path):
    p = rp.build_payload(results, w1_summary={}, w1_ab=None)
    html = rp.render_html(p)
    for a in rp.ARMS:
        assert f">{a[0]}<" in html
    for sec in ("Agent turn (T_turno) · 32K / 128K", "Warm TTFT and decode", "Time per task",
                "Tokens per answer (median)", "Accuracy", "Gates and verdicts", "Setup and how to reproduce"):
        assert sec in html
    assert "P1_BEST" in html and "k27" in html


def test_empty_results_dir_renders_without_data(tmp_path):
    p = rp.build_payload(tmp_path, w1_summary={}, w1_ab=None)
    assert p["speed"] == {} and p["quality"] == {} and p["gates"] == {}
    assert p["w1"]["32768"]["t_turno_s"] is None
    html = rp.render_html(p)
    assert "not measured" in html
    assert "Flash-Next" in html and "32K" in html and "128K" in html


def test_missing_quality_data_says_not_measured(results):
    import shutil
    shutil.rmtree(results / "q")
    p = rp.build_payload(results, w1_summary={}, w1_ab=None)
    assert p["quality"] == {}
    html = rp.render_html(p)
    i = html.index("Time per task")
    assert "not measured" in html[i:i + 4000]


def test_medium_only_arm_and_unmatched_files_ignored(results):
    _write_speed(results, "o27sw", "p4m", 3000, 40.0)
    (results / "o27sw-131072-t1.0-thinkx.jsonl").write_text("{}\n")  # not a speed file
    p = rp.build_payload(results, w1_summary={}, w1_ab=None)
    assert "o27sw-medium" in p["speed"]["131072"]
    assert "o27sw-xhigh" not in p["speed"]["131072"]
    assert p["speed"]["32768"]["o27sw-medium"]["t_turno_s"] == round(3.0 + 512 / 40.0, 1)
    assert "o27sw-medium" in rp.render_html(p)


def test_w1_reference_lines_when_present(results):
    w1 = {"w1@32768": {"t_turno_s": 7.9, "decode_tps": 84.6, "warm_ttft_s": {"tool_turn": 1.8}},
          "w1@131072": {"t_turno_s": 8.6}}
    p = rp.build_payload(results, w1_summary=w1, w1_ab=None)
    assert p["w1"]["32768"]["decode_tps"] == 84.6
    assert p["w1"]["32768"]["warm_ttft_tool_s"] == 1.8
    html = rp.render_html(p)
    assert "7.9" in html and "8.6" in html
    assert "9.9" in html and "10.8" in html  # 1.25 × w1 at 32K and 128K
    assert 'class="refline w1"' in html and 'class="refline lim"' in html


def test_w1_quality_marked_xhigh(results, tmp_path):
    w1 = tmp_path / "w1"; w1.mkdir()
    (w1 / "gpqa.jsonl").write_text("\n".join(json.dumps({"dataset_idx": i, "correct": True, "finish_reason": "stop",
                                                         "elapsed_s": 10.0, "completion_tokens": 800,
                                                         "reasoning_chars": 2000}) for i in range(3)) + "\n")
    import summarize_ab
    p = rp.build_payload(results, w1_summary={}, w1_ab=summarize_ab.load_arm(w1))
    assert p["w1_quality"]["gpqa"]["median_s"] == 10.0
    html = rp.render_html(p)
    i = html.index("Time per task")
    assert rp.W1_NAME in html[i:]


def test_loops_and_empty_answers(results):
    (results / "loops").mkdir()
    (results / "loops/q-o27q4-medium.jsonl").write_text("\n".join(json.dumps(r) for r in (
        {"prompt": "a", "degenerate": True}, {"prompt": "a", "degenerate": False},
        {"prompt": "b", "degenerate": False}, {"prompt": "b", "error": "boom"})) + "\n")
    q = results / "q/t1/o27q4-medium"
    (q / "if.jsonl").write_text("\n".join(json.dumps(r) for r in (
        {"id": "1", "passed": True, "finish_reason": "stop", "elapsed_s": 3.0, "raw_response": ""},
        {"id": "2", "passed": True, "finish_reason": "stop", "elapsed_s": 3.0, "raw_response": "ok"})) + "\n")
    p = rp.build_payload(results, w1_summary={}, w1_ab=None)
    assert p["loops"]["o27q4-medium"] == {"degenerate": 1, "total": 3}
    assert p["empty"]["o27q4-medium"]["empty"] == 1
    rp.render_html(p)


def test_payload_json_written(results, tmp_path):
    out, pj = tmp_path / "x.html", tmp_path / "x.json"
    assert rp.main(["--results", str(results), "--out", str(out), "--json-out", str(pj), "--no-w1"]) == 0
    d = json.loads(pj.read_text())
    assert set(d) >= {"generated_at", "arms", "speed", "w1", "quality", "empty", "loops", "gates"}
    assert d["arms"][0] == {"id": "s27r", "name": d["arms"][0]["name"], "runtime": "mlx-dspark 0.20.3",
                            "pack": "mlx-community 8bit", "rev": "815b83c0", "port": 8484, "phase": "P0"}


# --- driver B (n2) beside driver A (w1) ---

DRIVERS = {"w1@32768": {"t_turno_s": 7.9, "decode_tps": 84.6}, "w1@131072": {"t_turno_s": 8.6},
           "n2@32768": {"t_turno_s": 8.1, "decode_tps": 82.3, "warm_ttft_s": {"tool_turn": 1.8}},
           "n2@131072": {"t_turno_s": 8.9}}


def _ab_dir(tmp_path, name, secs):
    d = tmp_path / name; d.mkdir()
    (d / "gpqa.jsonl").write_text("\n".join(json.dumps({"dataset_idx": i, "correct": True, "finish_reason": "stop",
                                                        "elapsed_s": secs, "completion_tokens": 800,
                                                        "reasoning_chars": 2000}) for i in range(3)) + "\n")
    import summarize_ab
    return summarize_ab.load_arm(d)


def test_payload_has_n2_at_both_bands(results):
    p = rp.build_payload(results, w1_summary=DRIVERS, w1_ab=None)
    assert p["n2"]["32768"]["t_turno_s"] == 8.1
    assert p["n2"]["131072"]["t_turno_s"] == 8.9
    assert p["n2"]["32768"]["warm_ttft_tool_s"] == 1.8
    assert p["n2_quality"] == {}
    assert p["w1"]["32768"]["t_turno_s"] == 7.9


def test_payload_n2_quality_from_n2_ab(results, tmp_path):
    p = rp.build_payload(results, w1_summary={}, w1_ab=_ab_dir(tmp_path, "w1", 10.0), n2_ab=_ab_dir(tmp_path, "n2", 12.0))
    assert p["w1_quality"]["gpqa"]["median_s"] == 10.0
    assert p["n2_quality"]["gpqa"]["median_s"] == 12.0


def test_driver_b_line_and_rows_in_html(results, tmp_path):
    p = rp.build_payload(results, w1_summary=DRIVERS, w1_ab=_ab_dir(tmp_path, "w1", 10.0), n2_ab=_ab_dir(tmp_path, "n2", 12.0))
    html = rp.render_html(p)
    assert 'class="refline n2"' in html and 'class="refkey n2"' in html
    assert "8.1 s" in html and "8.9 s" in html
    assert rp.W1_NAME == "Driver A: Flash-Next Swift 1.5 (w1, xhigh)"
    assert rp.N2_NAME == "Driver B: Flash-Next ddalcu iQ (n2, xhigh)"
    for name in (rp.W1_NAME, rp.N2_NAME):
        assert html.count(name) >= 4  # speed tables (2+), accuracy, time, tokens
    t = html[html.index('id="ttft"'):html.index('id="time"')]
    assert t.index(rp.W1_NAME) < t.index(rp.N2_NAME)
    q = html[html.index('id="accuracy"'):]
    assert q.index(rp.W1_NAME) < q.index(rp.N2_NAME)
    assert "--ref-b" in html


def test_verdict_and_limit_stay_on_w1(results):
    p = rp.build_payload(results, w1_summary=DRIVERS, w1_ab=None)
    html = rp.render_html(p)
    assert "9.9" in html and "10.8" in html  # 1.25 x w1
    assert "10.1 s" not in html and "11.1 s" not in html  # 1.25 x n2 is not drawn
    assert "1.25 × n2" not in html
    assert 'title="1.25 × w1: 9.9 s"' in html and 'title="1.25 × w1: 10.8 s"' in html
    assert "1.25 × w1" in html


def test_no_w1_drops_both_drivers(results, tmp_path):
    out, pj = tmp_path / "p.html", tmp_path / "p.json"
    rp.main(["--results", str(results), "--out", str(out), "--json-out", str(pj), "--no-w1"])
    d = json.loads(pj.read_text())
    assert d["w1"]["32768"]["t_turno_s"] is None and d["n2"]["32768"]["t_turno_s"] is None
    assert d["w1_quality"] == {} and d["n2_quality"] == {}
    html = out.read_text()
    assert 'class="refline n2"' not in html and 'class="refline w1"' not in html
    body = html[html.index("</style>"):]
    assert rp.N2_NAME not in body and rp.W1_NAME not in body
