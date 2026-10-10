import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "regrade_humaneval", Path(__file__).resolve().parents[1] / "scripts" / "regrade_humaneval.py")
rh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rh)

ROW = {
    "prompt": "from typing import List\n\n\ndef first(xs: List[int]) -> int:\n    \"\"\"First item.\"\"\"\n",
    "test": "def check(f):\n    assert f([3, 4]) == 3\n",
    "entry_point": "first",
}
NO_IMPORT = "def first(xs: List[int]) -> int:\n    return xs[0]\n"


def test_strict_grade_fails_without_typing_import():
    assert rh.passes(rh.extract_code(NO_IMPORT), ROW) is False


def test_prompt_imports_make_the_same_code_pass():
    assert rh.passes(rh.with_prompt_imports(ROW["prompt"], rh.extract_code(NO_IMPORT)), ROW) is True


def test_extract_code_reads_python_fence():
    assert rh.extract_code("text\n```python\nx = 1\n```\nmore") == "\nx = 1\n"
