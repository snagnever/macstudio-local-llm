import csv
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location("export_tbench", HERE / "scripts" / "export_tbench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _trial(job, name, reward, exc=None, running=False):
    d = job / f"{name}__abc123"
    d.mkdir(parents=True)
    if running:
        return
    phase = lambda a, b: {"started_at": f"2026-10-28T10:{a:02d}:00", "finished_at": f"2026-10-28T10:{b:02d}:00"}
    (d / "result.json").write_text(json.dumps({
        "task_name": name, "started_at": "2026-10-28T10:00:00", "finished_at": "2026-10-28T10:20:00",
        "environment_setup": phase(0, 1), "agent_setup": phase(1, 2), "agent_execution": phase(2, 17),
        "verifier": phase(17, 20),
        "verifier_result": {"rewards": {"reward": reward}} if reward is not None else None,
        "exception_info": {"exception_type": exc} if exc else None,
        "agent_result": {"n_input_tokens": 1000, "n_cache_tokens": 800, "n_output_tokens": 50,
                         "metadata": {"n_episodes": 3, "api_request_times_msec": [100.0, 300.0, 200.0]}},
    }))


def test_rows_carry_reward_timeout_phase_minutes_and_tokens(tmp_path):
    job = tmp_path / "tb21-x"
    _trial(job, "fix-git", 1.0)
    _trial(job, "dna-assembly", 0.0, exc="AgentTimeoutError")
    _trial(job, "still-going", None, running=True)
    rows = _mod().rows(job)
    assert [r["task"] for r in rows] == ["dna-assembly", "fix-git"]
    fix = rows[1]
    assert fix["reward"] == 1.0 and fix["timeout"] == 0 and fix["error"] == ""
    assert (fix["total_min"], fix["agent_min"], fix["verifier_min"], fix["env_min"]) == (20.0, 15.0, 3.0, 1.0)
    assert (fix["input_tokens"], fix["cache_tokens"], fix["output_tokens"]) == (1000, 800, 50)
    assert fix["episodes"] == 3 and fix["requests"] == 3 and fix["median_request_s"] == 0.2
    dna = rows[0]
    assert dna["reward"] == 0.0 and dna["timeout"] == 1 and dna["error"] == "AgentTimeoutError"


def test_main_writes_a_csv_per_arm(tmp_path):
    runs = tmp_path / "runs"
    _trial(runs / "tb21-k2a", "fix-git", 1.0)
    out = tmp_path / "results"
    _mod().main(["k2a", "--runs", str(runs), "--out", str(out)])
    with open(out / "tbench21-k2a-tasks.csv") as f:
        got = list(csv.DictReader(f))
    assert got[0]["task"] == "fix-git" and got[0]["output_tokens"] == "50"
