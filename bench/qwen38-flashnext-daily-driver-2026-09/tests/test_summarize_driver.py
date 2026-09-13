import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_driver import summarize, apply_gates, apply_warnings, t_turno, main  # noqa: E402


def rec(cand, ctx, scen, ttft_s, decode, hit, correct=True, fin="stop", rep=1, wired=100.0, swap=0.1, error=None):
    return {"arm": cand, "context_target": ctx, "scenario": scen, "repeat": rep, "ttft_ms": ttft_s * 1000,
            "decode_tps": decode, "prompt_tps": 700.0, "cache_hit_ratio": hit, "correct": correct,
            "finish_reason": fin, "ram_peak_gb": wired, "swap_delta_gb": swap, "mtp_acceptance": 0.8,
            "error": error}


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
    assert apply_gates(row, 32768) == ["hit_append<0.90"]


def test_wired_is_warning_not_gate():
    rs = [rec("c1", 131072, "cold", 37.0, 66.0, 0.0), rec("c1", 131072, "tool_turn", 2.0, 60.0, 0.96, wired=106.35),
          rec("c1", 131072, "append", 1.9, 64.0, 0.96, wired=106.35), rec("c1", 131072, "identical", 0.1, 65.0, 1.0, wired=106.35, swap=0.0)]
    s = summarize(rs)[("c1", 131072)]
    assert s["gates_failed"] == []
    assert s["warnings"] == ["wired>102"]


def test_swap_still_gates():
    rs = [rec("c1", 32768, "cold", 37.0, 66.0, 0.0), rec("c1", 32768, "tool_turn", 2.0, 60.0, 0.96, swap=0.8),
          rec("c1", 32768, "append", 1.9, 64.0, 0.96), rec("c1", 32768, "identical", 0.1, 65.0, 1.0)]
    s = summarize(rs)[("c1", 32768)]
    assert "swap>0.5" in s["gates_failed"]


def test_hit_gate_uses_unrounded_values():
    # 0.86 rounds to 0.9 at 1 decimal, which would wrongly pass a >=0.90
    # gate under the old rounding-before-gating behaviour.
    rs = [rec("c1", 32768, "cold", 37.0, 66.0, 0.0), rec("c1", 32768, "tool_turn", 2.0, 60.0, 0.96),
          rec("c1", 32768, "append", 1.9, 64.0, 0.86), rec("c1", 32768, "identical", 0.1, 65.0, 1.0)]
    s = summarize(rs)[("c1", 32768)]
    assert s["hit"]["append"] == 0.86
    assert "hit_append<0.90" in s["gates_failed"]


def test_hit_keeps_three_decimals():
    rs = [rec("c1", 32768, "cold", 37.0, 66.0, 0.0), rec("c1", 32768, "tool_turn", 2.0, 60.0, 0.9622),
          rec("c1", 32768, "append", 1.9, 64.0, 0.96), rec("c1", 32768, "identical", 0.1, 65.0, 1.0)]
    s = summarize(rs)[("c1", 32768)]
    assert s["hit"]["tool_turn"] == 0.962


def test_truncation_is_not_http_error():
    rs = [rec("c1", 32768, "cold", 37.0, 66.0, 0.0), rec("c1", 32768, "tool_turn", 2.0, 60.0, 0.96),
          rec("c1", 32768, "append", 1.9, 64.0, 0.96), rec("c1", 32768, "identical", 0.1, 65.0, 1.0)]
    trunc = rec("c1", 32768, "middle_mutation", 2.5, 62.0, 0.95, correct=False, fin="length",
                error="finish_reason:length")
    rs.append(trunc)
    s = summarize(rs)[("c1", 32768)]
    assert s["errors"] == 0
    assert s["correctness"] == "truncado"
    assert "http_errors" not in s["gates_failed"]


def test_default_glob_selects_etapa_a_only(tmp_path):
    # Etapa A: the one file the default glob must pick up.
    a_rec = rec("c1", 32768, "cold", 37.0, 66.0, 0.96)
    (tmp_path / "c1-32768-t1.0.jsonl").write_text(json.dumps(a_rec) + "\n", encoding="utf-8")
    # Etapa B: same band, would inflate n if the default glob matched it too.
    b_rec = rec("c1", 32768, "cold", 1.0, 1.0, 1.0)
    (tmp_path / "c1-32768-t1.0-b.jsonl").write_text(
        "\n".join(json.dumps(b_rec) for _ in range(4)) + "\n", encoding="utf-8"
    )
    # 512K probe: a different band/suffix entirely, must not show up at all.
    probe_rec = rec("c1", 524288, "cold", 5.0, 5.0, 1.0)
    (tmp_path / "c1-524288-t1.0-yarn2.jsonl").write_text(json.dumps(probe_rec) + "\n", encoding="utf-8")

    out_path = tmp_path / "summary.json"
    rc = main(["--results-dir", str(tmp_path), "--out", str(out_path)])
    assert rc == 0
    summary = json.loads(out_path.read_text(encoding="utf-8"))
    assert summary["c1@32768"]["n"] == 1  # only the Etapa A file's single record
    assert "c1@524288" not in summary
