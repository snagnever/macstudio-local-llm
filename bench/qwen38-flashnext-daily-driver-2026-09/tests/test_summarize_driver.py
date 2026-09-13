import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_driver import summarize, apply_gates, t_turno  # noqa: E402


def rec(cand, ctx, scen, ttft_s, decode, hit, correct=True, fin="stop", rep=1, wired=100.0, swap=0.1):
    return {"arm": cand, "context_target": ctx, "scenario": scen, "repeat": rep, "ttft_ms": ttft_s * 1000,
            "decode_tps": decode, "prompt_tps": 700.0, "cache_hit_ratio": hit, "correct": correct,
            "finish_reason": fin, "ram_peak_gb": wired, "swap_delta_gb": swap, "mtp_acceptance": 0.8}


def test_t_turno_formula():
    assert t_turno(2.0, 64.0) == 10.0  # 2.0 + 512/64


def test_summarize_medians_and_correctness():
    rs = [rec("c1", 32768, "cold", 37.0, 66.0, 0.0), rec("c1", 32768, "tool_turn", 2.0, 60.0, 0.96),
          rec("c1", 32768, "tool_turn", 2.2, 68.0, 0.96, rep=2), rec("c1", 32768, "append", 1.9, 64.0, 0.96),
          rec("c1", 32768, "identical", 0.1, 65.0, 1.0, correct=False, fin="length")]
    s = summarize(rs)[("c1", 32768)]
    assert s["cold_ttft_s"] == 37.0
    assert s["warm_ttft_s"]["tool_turn"] == 2.1
    assert s["decode_tps"] == 64.5  # mediana dos cenarios quentes (60, 68, 64, 65)
    assert s["t_turno_s"] == round(2.1 + 512 / 64.5, 1)
    assert s["correctness"] == "truncado"


def test_gates():
    row = {"hit": {"append": 0.85, "tool_turn": 0.96}, "correctness": "ok", "wired_peak_gb": 104.0, "swap_delta_gb": 0.1, "errors": 0}
    assert apply_gates(row, 32768) == ["hit_append<0.90", "wired>102"]
