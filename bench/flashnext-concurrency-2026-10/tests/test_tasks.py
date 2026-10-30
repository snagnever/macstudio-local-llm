"""Tasks c and d of campaign B: the checkers refuse the base repository and accept the reference solution."""
import shutil
import subprocess

from conftest import SCRIPTS, run

TASKS = SCRIPTS / "claude-tasks"


def _copy(tmp_path, t):
    repo = tmp_path / f"repo-{t}"
    shutil.copytree(TASKS / f"repo-{t}", repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def _apply(repo, patch):
    subprocess.run(["git", "apply", str(patch)], cwd=repo, check=True)


def test_check_c_is_false_on_the_base_repo_and_true_after_the_solution(tmp_path):
    repo = _copy(tmp_path, "c")
    assert run("bash", TASKS / "check-c.sh", repo).stdout.strip() == "false"
    _apply(repo, TASKS / "solutions/c.patch")
    assert run("bash", TASKS / "check-c.sh", repo).stdout.strip() == "true"


def test_check_d_is_false_on_the_base_repo_and_true_after_the_solution(tmp_path):
    repo = _copy(tmp_path, "d")
    assert run("bash", TASKS / "check-d.sh", repo).stdout.strip() == "false"
    _apply(repo, TASKS / "solutions/d.patch")
    assert run("bash", TASKS / "check-d.sh", repo).stdout.strip() == "true"


def test_base_repos_pass_their_own_suites():
    assert subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=TASKS / "repo-c",
                          capture_output=True).returncode == 0
    assert subprocess.run(["bash", "tests/run_tests.sh"], cwd=TASKS / "repo-d", capture_output=True).returncode == 0


def test_repos_meet_the_size_floor():
    big_c = [p for p in (TASKS / "repo-c").rglob("*") if p.is_file() and p.stat().st_size > 20_000]
    big_d = [p for p in (TASKS / "repo-d").rglob("*") if p.is_file() and p.stat().st_size > 20_000]
    assert len(big_c) >= 2 and len(big_d) >= 2  # ~5K tokens each
    assert sum(1 for _ in (TASKS / "repo-c").rglob("*.py")) >= 6
    assert sum(1 for _ in (TASKS / "repo-d").rglob("*.sh")) >= 6


def test_shell_scripts_parse_under_bash(tmp_path):
    scripts = list((TASKS / "repo-d").rglob("*.sh")) + [TASKS / "check-c.sh", TASKS / "check-d.sh"]
    assert len(scripts) >= 8
    for s in scripts:
        assert subprocess.run(["bash", "-n", str(s)], capture_output=True).returncode == 0, s


def test_subagents_preamble_asks_for_two_parallel_agent_calls():
    text = (TASKS / "subagents-preamble.md").read_text()
    assert "`Agent` tool twice in the same message" in text and "Explore" in text
