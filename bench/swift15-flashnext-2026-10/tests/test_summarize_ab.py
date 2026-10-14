import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import summarize_ab as S  # noqa: E402


def b2(idx, ok, s, fin="stop", comp=100, rc=0):
    return {"dataset_idx": idx, "lcb_question_id": None, "correct": ok, "elapsed_s": s,
            "finish_reason": fin, "completion_tokens": comp, "reasoning_chars": rc}


def test_view_bench2_truncation_is_failure_and_flagged():
    v = S.view("gpqa", b2(7, False, 12.5, fin="length"))
    assert v == {"id": "7", "passed": False, "elapsed_s": 12.5, "completion_tokens": 100,
                 "reasoning_chars": 0, "truncated": True}


def test_view_accepts_string_booleans_and_numbers():
    v = S.view("humaneval", {"dataset_idx": "3", "correct": "True", "elapsed_s": "2.5",
                             "finish_reason": "stop", "completion_tokens": "163"})
    assert v["passed"] is True and v["elapsed_s"] == 2.5 and v["completion_tokens"] == 163


def test_view_tool_suite_sums_both_turns():
    v = S.view("jdhodges", {"case_id": "c1", "score_pass": True, "turn_1_elapsed_s": 1.0,
                            "turn_2_elapsed_s": 2.0, "turn_1_finish_reason": "tool_calls", "completion_tokens": 50})
    assert v["elapsed_s"] == 3.0 and v["passed"] is True and v["truncated"] is False


def test_view_lcb_uses_question_id():
    v = S.view("livecodebench", {"dataset_idx": 1, "lcb_question_id": "abc123", "correct": True,
                                 "elapsed_s": 1, "finish_reason": "stop"})
    assert v["id"] == "abc123"


def test_suite_stats():
    st = S.suite_stats([S.view("gpqa", b2(1, True, 10)), S.view("gpqa", b2(2, False, 30, fin="length")),
                        S.view("gpqa", b2(3, True, 20))])
    assert st["n"] == 3 and st["passed"] == 2 and st["truncated"] == 1
    assert st["total_s"] == 60.0 and st["median_s"] == 20.0


def _arm(tmp_path, arm, suites):
    d = tmp_path / arm
    d.mkdir()
    for suite, recs in suites.items():
        (d / f"{suite}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    return S.load_arm(d)


def test_mismatched_question_sets_are_refused(tmp_path):
    base = _arm(tmp_path, "n2", {"gpqa": [b2(1, True, 10)]})
    cand = _arm(tmp_path, "w1", {"gpqa": [b2(2, True, 10)]})
    with pytest.raises(ValueError, match="gpqa"):
        S.compare(base, cand)


def test_gates(tmp_path):
    base = _arm(tmp_path, "n2", {"gpqa": [b2(i, True, 100) for i in range(10)],
                                 "livecodebench": [b2(i, True, 100) for i in range(10)]})
    cand = _arm(tmp_path, "w1", {"gpqa": [b2(i, i > 2, 70) for i in range(10)],
                                 "livecodebench": [b2(i, True, 90) for i in range(10)]})
    stats = S.compare(base, cand)
    g = S.gates(stats["base"], stats["cand"])
    assert g["G1:gpqa"] is True            # 7 >= 10 - 3
    assert g["G1:livecodebench"] is True
    assert g["G2:gpqa"] is True            # 70 <= 0.8 * 100
    assert g["G2:livecodebench"] is False  # 90 > 80


def test_view_truncated_if_record_is_failure():
    v = S.view("if", {"id": "if02", "passed": True, "elapsed_s": 1, "finish_reason": "length"})
    assert v["passed"] is False and v["truncated"] is True


def test_reasoning_not_recorded_renders_nd():
    # Os registros de tool-calling não gravam reasoning_chars: a tabela não pode mostrar 0 como medido.
    views = [S.view("jdhodges", {"case_id": f"c{i}", "score_pass": True, "turn_1_elapsed_s": 1.0,
                                 "turn_1_finish_reason": "tool_calls", "completion_tokens": 50}) for i in range(3)]
    st = S.suite_stats(views)
    assert st["median_reasoning_chars"] is None
    md = S.render({"base": {"jdhodges": st}, "cand": {"jdhodges": st}}, {}, "n2", "w1")
    assert "| jdhodges | reasoning mediano (chars) | n/d | n/d |" in md


def _lcb_row(qid, ok, fin="stop"):
    return {"dataset_idx": 0, "lcb_question_id": qid, "correct": ok, "elapsed_s": 1.0,
            "finish_reason": fin, "completion_tokens": 10}


def test_load_arm_applies_lcb_regrade(tmp_path, monkeypatch):
    arm = tmp_path / "bench" / "c" / "results" / "ab" / "t1" / "w1"
    arm.mkdir(parents=True)
    rows = [_lcb_row("q1", False), _lcb_row("q2", True), _lcb_row("q3", False, fin="length")]
    (arm / "livecodebench.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    verdicts = tmp_path / "verdicts.json"
    verdicts.write_text(json.dumps({"bench/c/results/ab/t1/w1/livecodebench.jsonl": [
        {"lcb_question_id": "q1", "regraded": True}, {"lcb_question_id": "q2", "regraded": True},
        {"lcb_question_id": "q3", "regraded": False}]}))
    monkeypatch.setattr(S, "REPO", tmp_path)
    monkeypatch.setattr(S, "LCB_REGRADE", verdicts)
    views = S.load_arm(arm)["livecodebench"]
    assert [v["passed"] for v in views] == [True, True, False]


def test_load_arm_without_lcb_regrade_keeps_original(tmp_path, monkeypatch):
    arm = tmp_path / "w1"
    arm.mkdir()
    (arm / "livecodebench.jsonl").write_text(json.dumps(_lcb_row("q1", False)))
    monkeypatch.setattr(S, "LCB_REGRADE", tmp_path / "missing.json")
    assert S.load_arm(arm)["livecodebench"][0]["passed"] is False
