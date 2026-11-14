from tasks import TASKS, fresh_copy, prompt


def test_registry_has_seven_tasks_with_spec_limits():
    assert {k: t.limit_s for k, t in TASKS.items()} == {
        "a": 900, "b": 900, "c": 900, "d": 900, "T1": 900, "T5": 1200, "T7": 1800}


def test_hard_tasks_are_the_three_new_ones():
    assert {k for k, t in TASKS.items() if t.hard} == {"T1", "T5", "T7"}


def test_prompt_of_T1_is_the_text_block_only():
    p = prompt("T1")
    assert p.startswith("The test suite in this project is failing.")
    assert "Verificação" not in p and "```" not in p


def test_prompt_of_a_is_the_whole_task_file():
    assert prompt("a").startswith("This repository is a small Python package, `inventory`")


def test_fresh_copy_leaves_caches_behind(tmp_path):
    repo = fresh_copy("T5", tmp_path / "r")
    assert (repo / "Makefile").is_file()
    assert not list(repo.rglob(".ruff_cache")) and not list(repo.rglob(".pytest_cache"))
