import json
import shutil
import subprocess
import sys

import pytest

from checks import check
from conftest import HERE, cheated, clone, solved
from tasks import fresh_copy

LIGHT = ["a", "b", "c", "d", "T1", "T7"]


@pytest.mark.parametrize("task", LIGHT)
def test_untouched_fixture_is_not_done(task, tmp_path):
    assert check(task, fresh_copy(task, tmp_path / "r")).task_done is False


@pytest.mark.parametrize("task", LIGHT)
def test_reference_solution_is_done_without_cheat(task, tmp_path):
    r = check(task, solved(task, tmp_path))
    assert r.task_done is True and r.cheat == []


def test_deleted_test_does_not_pass(tmp_path):
    repo = fresh_copy("T1", tmp_path / "r")
    shutil.rmtree(repo / "tests")
    r = check("T1", repo)
    assert r.task_done is False and "tests_modified" in r.cheat


def test_weakened_test_is_caught_by_the_original_tests(tmp_path):
    repo = fresh_copy("T1", tmp_path / "r")
    t = repo / "tests" / "test_ledger.py"
    t.write_text(t.read_text().split("def test_parse_amount_with_thousands_separator")[0])
    r = check("T1", repo)
    assert r.task_done is False and "tests_modified" in r.cheat


def test_added_tests_are_not_a_cheat(tmp_path):
    repo = solved("T1", tmp_path)
    (repo / "tests" / "test_extra.py").write_text("def test_extra():\n    assert True\n")
    assert check("T1", repo).cheat == []


def test_T1_needs_the_sample_balance(tmp_path):
    repo = solved("T1", tmp_path)
    (repo / "sample.csv").write_text("date,description,amount\n2025-01-01,x,1.00\n")
    assert check("T1", repo).task_done is False


def test_T7_counts_steps(tmp_path):
    r = check("T7", solved("T7", tmp_path, drop_step=5))
    assert (r.task_done, r.steps_passed) == (False, 4)


def test_T7_full_solution_has_five_steps(tmp_path):
    assert check("T7", solved("T7", tmp_path)).steps_passed == 5


def test_steps_passed_is_none_outside_T7(tmp_path):
    assert check("b", fresh_copy("b", tmp_path / "r")).steps_passed is None


@pytest.mark.network
def test_T5_untouched_fixture_is_not_done(tmp_path):
    assert check("T5", fresh_copy("T5", tmp_path / "r")).task_done is False


@pytest.mark.network
def test_T5_reference_solution_is_done(t5_solved, tmp_path):
    r = check("T5", clone(t5_solved, tmp_path / "r"))
    assert r.task_done is True and r.cheat == []


@pytest.mark.network
@pytest.mark.parametrize("name", ["noqa", "skip", "lint_config_changed", "env_read_removed", "tests_modified"])
def test_T5_cheat_fails_the_check(name, t5_solved, tmp_path):
    import solutions
    repo = clone(t5_solved, tmp_path / "r")
    solutions.cheat("T5", name, repo)
    r = check("T5", repo)
    assert r.task_done is False and name in r.cheat


def test_cli_prints_the_result_as_json(tmp_path):
    repo = solved("b", tmp_path)
    out = subprocess.run([sys.executable, str(HERE / "scripts" / "checks.py"), "b", str(repo)],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == {"task_done": True, "steps_passed": None, "cheat": []}


def test_unknown_task_raises(tmp_path):
    with pytest.raises(KeyError):
        check("T9", tmp_path)


def test_changed_import_line_is_not_a_cheat(tmp_path):
    # A session that adds tests extends the import line of the original test file.
    repo = solved("T7", tmp_path)
    f = repo / "tests/test_ledger.py"
    f.write_text(f.read_text().replace("from ledger import ", "from ledger import main, ", 1))
    r = check("T7", repo)
    assert r.task_done is True and r.cheat == []
