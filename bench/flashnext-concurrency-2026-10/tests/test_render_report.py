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
