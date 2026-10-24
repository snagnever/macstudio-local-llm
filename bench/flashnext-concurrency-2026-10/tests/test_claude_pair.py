import json
import stat

from conftest import SCRIPTS, clean_env, run


def test_run_claude_pair_dry_run():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "2", "--tag", "e2").stdout
    assert out.count("claude -p") == 2 and "task-a.md" in out and "task-b.md" in out
    assert "CLAUDE_CODE_EFFORT_LEVEL=xhigh" in out and "ANTHROPIC_DEFAULT_HAIKU_MODEL=" in out
    assert "--output-format json" in out and "--strict-mcp-config" in out


def test_run_claude_pair_single_session_picks_task():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "1", "--task", "b", "--tag", "c1").stdout
    assert out.count("claude -p") == 1 and "task-b.md" in out and "task-a.md" not in out


def test_run_claude_pair_interactive_env_prints_exports_only():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--interactive-env").stdout
    assert "export ANTHROPIC_BASE_URL=http://127.0.0.1:11234" in out
    assert "export ANTHROPIC_SMALL_FAST_MODEL=" in out and "claude -p" not in out


def test_run_claude_pair_records_wall_time_and_task_check(tmp_path):
    fake = tmp_path / "claude"
    fake.write_text('#!/bin/bash\nsleep 1\necho \'{"type":"result","is_error":false,"num_turns":9,"duration_ms":1000}\'\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    out = tmp_path / "results"
    env = clean_env({"CLAUDE_BIN": str(fake), "CLAUDE_PAIR_WORK": str(tmp_path / "work"),
                     "MODEL_ID": "m", "BASE_URL": "http://127.0.0.1:1/v1"})
    res = run("bash", SCRIPTS / "run-claude-pair.sh", "--sessions", "2", "--tag", "t", "--out", out, env=env, check=False)
    a = json.loads((out / "cc-t-a.json").read_text())
    b = json.loads((out / "cc-t-b.json").read_text())
    assert a["num_turns"] == 9 and a["wall_s"] >= 1 and a["task"] == "a" and a["sessions"] == 2
    # the fake claude changed nothing: repo-a tests still pass but the json flag is missing; repo-b still has its bugs
    assert a["task_done"] is False and b["task_done"] is False
    assert res.returncode != 0
