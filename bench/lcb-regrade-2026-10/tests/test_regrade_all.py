import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import regrade_all  # noqa: E402
from test_lcb_regrade import ANNOTATED, FUNCTIONAL_Q  # noqa: E402


def test_read_rows_skips_lines_without_question_id(tmp_path):
    f = tmp_path / "run.jsonl"
    f.write_text("\n".join([json.dumps({"lcb_question_id": "q1"}), "3", json.dumps({"summary": 1}), ""]))
    assert [r["lcb_question_id"] for r in regrade_all.read_rows(f)] == ["q1"]


def test_grade_file_looks_up_by_question_id_and_keeps_truncation():
    rows = [
        {"lcb_question_id": "q1", "raw_response": ANNOTATED, "correct": False, "finish_reason": "stop"},
        {"lcb_question_id": "q1", "raw_response": ANNOTATED, "correct": False, "finish_reason": "length"},
        {"lcb_question_id": "unknown", "raw_response": ANNOTATED, "correct": False},
    ]
    verdicts = regrade_all.grade_file(rows, {"q1": FUNCTIONAL_Q}, regrade_all.lcb_regrade.regrade)
    assert [(v["regraded"], v["reason"]) for v in verdicts] == [
        (True, "pass"), (False, "truncated"), (False, "missing_question")]
