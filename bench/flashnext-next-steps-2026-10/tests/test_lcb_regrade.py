import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))

import lcb_regrade  # noqa: E402

ANNOTATED = """```python
class Solution:
    def total(self, nums: List[int]) -> int:
        return sum(nums)
```"""

FUNCTIONAL_Q = {
    "question_id": "q1",
    "testtype": "functional",
    "fn_name": "total",
    "starter_code": "class Solution:\n    def total(self, nums: List[int]) -> int:\n        ",
    "test_cases": [{"testtype": "functional", "input": "[1, 2, 3]", "output": "6"}],
}


@pytest.mark.skipif(sys.version_info >= (3, 14) or hasattr(lcb_regrade.bench2, "LCB_PRELUDE"),
                    reason="Python 3.14 defers annotations (PEP 649), or the submodule grader has the fix (2403125)")
def test_original_grader_fails_on_missing_typing_import():
    ok, _, reason = lcb_regrade.bench2.grade_livecodebench(FUNCTIONAL_Q, ANNOTATED)
    assert not ok and reason.startswith("fail_test0:rc=1")


@pytest.mark.skipif(not hasattr(lcb_regrade.bench2, "LCB_PRELUDE"), reason="submodule grader predates 2403125")
def test_bench2_at_2403125_matches_regrade():
    # The submodule fix (2403125) adds the same prelude and file runner, so both graders agree.
    assert lcb_regrade.bench2.grade_livecodebench(FUNCTIONAL_Q, ANNOTATED) == \
        lcb_regrade.regrade(FUNCTIONAL_Q, ANNOTATED)
    big = list(range(400_000))
    q = dict(FUNCTIONAL_Q, test_cases=[{"testtype": "functional", "input": json.dumps(big),
                                        "output": str(sum(big))}])
    ok, _, reason = lcb_regrade.bench2.grade_livecodebench(q, ANNOTATED)
    assert ok and reason == "pass", reason


def test_regrade_adds_the_livecodebench_import_prelude():
    ok, _, reason = lcb_regrade.regrade(FUNCTIONAL_Q, ANNOTATED)
    assert ok and reason == "pass", reason


def test_regrade_survives_inputs_larger_than_argmax():
    big = list(range(400_000))
    q = dict(FUNCTIONAL_Q, test_cases=[{"testtype": "functional", "input": json.dumps(big),
                                        "output": str(sum(big))}])
    ok, _, reason = lcb_regrade.regrade(q, ANNOTATED)
    assert ok and reason == "pass", reason


def test_regrade_keeps_wrong_answers_wrong():
    q = dict(FUNCTIONAL_Q, test_cases=[{"testtype": "functional", "input": "[1, 2, 3]", "output": "7"}])
    ok, _, reason = lcb_regrade.regrade(q, ANNOTATED)
    assert not ok and "mismatch" in reason


def test_regrade_stdin_with_prelude():
    q = {"question_id": "q2", "testtype": "stdin", "starter_code": "",
         "test_cases": [{"testtype": "stdin", "input": "3\n", "output": "6"}]}
    code = "```python\nn = int(input())\nprint(sum(accumulate([1] * n)))\n```"
    ok, _, reason = lcb_regrade.regrade(q, code)
    assert ok and reason == "pass", reason
