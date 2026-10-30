import json
import stat
import sys
import threading
from http.server import ThreadingHTTPServer

from conftest import SCRIPTS, clean_env, run


def test_run_claude_pair_dry_run():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "2", "--tag", "e2").stdout
    assert out.count("claude -p") == 2 and "task-a.md" in out and "task-b.md" in out
    assert "CLAUDE_CODE_EFFORT_LEVEL=xhigh" in out and "ANTHROPIC_DEFAULT_HAIKU_MODEL=" in out
    assert "--output-format stream-json --verbose" in out and "--strict-mcp-config" in out


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


# ---- campaign B: --pair, --task c|d, --subagents, --proxy, --max-turns ----

def test_pair_cd_with_subagents_and_proxy_dry_run():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "2", "--pair", "c,d",
              "--subagents", "--proxy", "8686", "--tag", "rc2sr1").stdout
    assert out.count("claude -p") == 2 and "task-c.md" in out and "task-d.md" in out and "task-a.md" not in out
    assert "subagents-preamble.md" in out and " Agent " in out and "--max-turns 60" in out
    assert "request_log.py --listen 8686 " in out and "--listen 8687 " in out
    assert "--upstream http://127.0.0.1:11234 " in out and "--stream rc2sr1-c" in out and "--out" in out
    assert "ANTHROPIC_BASE_URL=http://127.0.0.1:8686" in out and "ANTHROPIC_BASE_URL=http://127.0.0.1:8687" in out
    assert "--output-format stream-json --verbose" in out


def test_single_task_c_without_subagents_keeps_agent_out():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "1", "--task", "c", "--tag", "rc1r1").stdout
    assert out.count("claude -p") == 1 and " Agent " not in out and "--max-turns 60" in out and "request_log" not in out


def test_default_pair_is_ab_with_40_turns():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "2", "--tag", "x").stdout
    assert "task-a.md" in out and "task-b.md" in out and "--max-turns 40" in out


def test_explicit_max_turns_overrides_the_default():
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "1", "--task", "d", "--max-turns", "25",
              "--tag", "x").stdout
    assert "--max-turns 25" in out and "--max-turns 60" not in out


def _fake_claude(path, body):
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_stream_json_counts_parallel_agent_calls(tmp_path):
    fake = tmp_path / "claude"
    _fake_claude(fake, 'echo \'{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Agent","id":"1"},{"type":"tool_use","name":"Agent","id":"2"}]}}\'\n'
                       'echo \'{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","id":"3"}]}}\'\n'
                       'echo \'{"type":"result","is_error":false,"num_turns":4,"subagent_stats":{"spawned":2}}\'\n')
    out = tmp_path / "results"
    env = clean_env({"CLAUDE_BIN": str(fake), "CLAUDE_PAIR_WORK": str(tmp_path / "work"), "MODEL_ID": "m",
                     "BASE_URL": "http://127.0.0.1:1/v1"})
    run("bash", SCRIPTS / "run-claude-pair.sh", "--sessions", "1", "--task", "c", "--subagents", "--tag", "t", "--out", out,
        env=env, check=False)
    c = json.loads((out / "cc-t-c.json").read_text())
    assert c["parallel_agent_calls"] == 1 and c["subagents_spawned"] == 2 and c["subagents"] is True and c["num_turns"] == 4
    assert c["task_done"] is False  # the fake changed nothing in repo-c


def test_proxy_inside_the_pair_records_the_session_requests(tmp_path):
    sys.path.insert(0, str(SCRIPTS.parent / "tests"))
    from test_request_log import FakeUpstream
    up = ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    fake = tmp_path / "claude"
    _fake_claude(fake, 'curl -s -X POST "$ANTHROPIC_BASE_URL/v1/messages" -H "content-type: application/json" -d \'{}\' >/dev/null\n'
                       'echo \'{"type":"result","is_error":false,"num_turns":1}\'\n')
    out = tmp_path / "results"
    env = clean_env({"CLAUDE_BIN": str(fake), "CLAUDE_PAIR_WORK": str(tmp_path / "work"), "MODEL_ID": "m",
                     "BASE_URL": f"http://127.0.0.1:{up.server_port}/v1"})
    run("bash", SCRIPTS / "run-claude-pair.sh", "--sessions", "1", "--task", "a", "--proxy", "18686", "--tag", "t",
        "--out", out, env=env, check=False)
    up.shutdown()
    recs = [json.loads(line) for line in (out / "req-t-a.jsonl").read_text().splitlines()]
    assert len(recs) == 1 and recs[0]["stream"] == "t-a" and recs[0]["status"] == 200 and recs[0]["input_tokens"] == 19297
    assert json.loads((out / "cc-t-a.json").read_text())["subagents"] is False


def test_raw_dir_env_reaches_the_proxy_in_dry_run():
    env = clean_env({"CLAUDE_PAIR_RAW_DIR": "/tmp/raw-x"})
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "1", "--task", "a", "--proxy", "8686",
              "--tag", "t", env=env).stdout
    assert "--raw-dir /tmp/raw-x " in out
    out = run("bash", SCRIPTS / "run-claude-pair.sh", "--dry-run", "--sessions", "1", "--task", "a", "--proxy", "8686",
              "--tag", "t").stdout
    assert "--raw-dir" not in out
