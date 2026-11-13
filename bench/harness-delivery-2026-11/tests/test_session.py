import json
import os

import pytest

from conftest import HERE
from harness import Target
from run_session import FIELDS, main, record_path, run

T = Target("127.0.0.1", 9, "m:IQ4_XS")


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.fixture
def fake(monkeypatch):
    def set_mode(mode, task="b"):
        monkeypatch.setenv("FAKE_MODE", mode)
        monkeypatch.setenv("FAKE_TASK", task)
    monkeypatch.setenv("HARNESS_BIN_PI", str(HERE / "tests/fake_harness.py"))
    monkeypatch.setenv("HARNESS_PASS_ENV", "FAKE_MODE,FAKE_TASK")
    monkeypatch.setenv("HARNESS_SANDBOX_READ", str(HERE / "tests"))  # the fake harness lives there
    set_mode("solve")
    return set_mode


def test_solved_session_records_done(fake, tmp_path):
    fake("solve", "T1")
    r = run("pi", "T1", "k2", 1, T, tmp_path / "res", tmp_path / "logs")
    assert (r["task_done"], r["timeout"], r["claimed_done"], r["exit"]) == (True, False, True, 0)
    assert json.loads(record_path(tmp_path / "res", "k2", "pi", "T1", 1).read_text()) == r


def test_record_has_exactly_the_spec_fields(fake, tmp_path):
    r = run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert set(r) == FIELDS == {
        "harness", "harness_version", "pack", "task", "rep", "model_id", "task_done", "steps_passed", "cheat",
        "wall_s", "exit", "timeout", "claimed_done", "turns", "input_tokens", "output_tokens"}
    assert (r["harness"], r["pack"], r["task"], r["rep"], r["model_id"]) == ("pi", "k2", "b", 1, "m:IQ4_XS")
    assert r["harness_version"] == "fake 1.0" and r["wall_s"] >= 0 and r["turns"] is None


def test_timeout_kills_process_group(fake, tmp_path):
    fake("hang_with_child")
    r = run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l", limit_s=2)
    assert (r["timeout"], r["task_done"], r["claimed_done"]) == (True, False, False)
    assert r["wall_s"] < 20
    assert not pid_alive(int((tmp_path / "l/work/k2-pi-b-r1/child.pid").read_text()))


def test_claims_done_without_work(fake, tmp_path):
    fake("exit0_no_work")
    r = run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert (r["claimed_done"], r["task_done"]) == (True, False)


def test_crash_is_not_a_claim(fake, tmp_path):
    fake("crash")
    r = run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert (r["exit"], r["claimed_done"], r["task_done"], r["timeout"]) == (3, False, False, False)


def test_record_holds_no_session_text(fake, tmp_path):
    run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert "SECRET-TRANSCRIPT" not in "".join(p.read_text() for p in (tmp_path / "r").rglob("*.json"))
    assert "SECRET-TRANSCRIPT" in (tmp_path / "l/sessions/k2-pi-b-r1.log").read_text()


def test_default_limit_comes_from_the_task(fake, tmp_path, monkeypatch):
    seen = {}
    import run_session
    real = run_session._execute
    monkeypatch.setattr(run_session, "_execute", lambda cmd, log, limit: seen.update(limit=limit) or real(cmd, log, limit))
    run("pi", "T7", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert seen["limit"] == 1800


def test_rerun_starts_from_a_fresh_copy(fake, tmp_path):
    run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    fake("exit0_no_work")
    assert run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")["task_done"] is False


def test_cli_writes_the_record(fake, tmp_path, capsys):
    rc = main(["--harness", "pi", "--task", "b", "--pack", "k2", "--rep", "2", "--host", "127.0.0.1", "--port", "9",
               "--model", "m", "--out", str(tmp_path / "r"), "--logs", str(tmp_path / "l")])
    assert rc == 0 and record_path(tmp_path / "r", "k2", "pi", "b", 2).is_file()
    assert json.loads(capsys.readouterr().out)["task_done"] is True


def test_check_runs_inside_the_sandbox(fake, tmp_path, monkeypatch):
    """A repository that tries to write outside its copy during the check does not succeed."""
    import run_session
    seen = []
    real = run_session.harness.sandboxed
    monkeypatch.setattr(run_session.harness, "sandboxed", lambda cmd, **kw: seen.append(cmd.argv) or real(cmd, **kw))
    run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert len(seen) == 2 and any("checks.py" in a for a in seen[1])
