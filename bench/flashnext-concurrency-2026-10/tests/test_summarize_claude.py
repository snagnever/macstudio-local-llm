import json

import pytest

from summarize_claude import main, summarize_claude

COLD = {"t_start_s": 0.0, "ttft_s": 23.7, "t_end_s": 25.0, "input_tokens": 19296, "cached_tokens": 0,
        "output_tokens": 112, "tps": 133.8, "status": 200, "stream": None}
WARM = {"t_start_s": 25.0, "ttft_s": 0.6, "t_end_s": 27.0, "input_tokens": 19622, "cached_tokens": 19264,
        "output_tokens": 204, "tps": 161.3, "status": 200, "stream": None}


def _cc(results, name, wall, task, turns):
    data = {"wall_s": wall, "task": task, "num_turns": turns, "is_error": False, "task_done": True}
    (results / f"cc-{name}.json").write_text(json.dumps(data))


def _req(results, name, reqs):
    (results / f"req-{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in reqs))


def test_summarize_claude_small_profile(tmp_path):
    for r, w in ((1, 40.0), (2, 42.0)):
        _cc(tmp_path, f"kcc1r{r}-a", w, "a", 10)
        _cc(tmp_path, f"kcc1r{r}-b", 40.0, "b", 6)
    for r in (1, 2, 3):
        _cc(tmp_path, f"kcc2r{r}-a", 60.0, "a", 10)
        _cc(tmp_path, f"kcc2r{r}-b", 50.0, "b", 6)
    s = summarize_claude(tmp_path, "kcc")
    p = s["profiles"]["small"]
    assert p["alone_s"] == {"a": 41.0, "b": 40.0} and p["pair_s"] == {"a": 60.0, "b": 50.0}
    assert p["pair_wall_s"] == 60.0 and p["serial_sum_s"] == 81.0
    assert p["time_saved"] == pytest.approx(0.259, abs=0.001)
    assert p["turns"] == {"a": 10, "b": 6} and p["task_done"] is True and p["errors"] == 0
    assert "realistic" not in s["profiles"] and s["requests"] == {"alone": None, "pair": None}


def test_summarize_claude_requests_split_alone_and_pair(tmp_path):
    _req(tmp_path, "kcc1r1-a", [COLD, WARM])
    _req(tmp_path, "kcc2r1", [COLD, WARM, WARM])
    s = summarize_claude(tmp_path, "kcc")
    assert s["requests"]["alone"]["n"] == 2 and s["requests"]["pair"]["n"] == 3
    assert s["prefix"] == "kcc" and s["profiles"] == {}


def test_requests_pooled_across_files_keep_per_file_concurrency(tmp_path):
    # Each file counts time from its own first request, so two runs must not look concurrent with each other.
    two = [COLD, dict(COLD, t_start_s=5.0, t_end_s=30.0)]
    _req(tmp_path, "kcc2r1", two)
    _req(tmp_path, "kcc2r2", two)
    assert summarize_claude(tmp_path, "kcc")["requests"]["pair"]["max_concurrent"] == 2


def test_main_writes_json_and_markdown(tmp_path, capsys):
    _cc(tmp_path, "kcc1r1-a", 40.0, "a", 10)
    _cc(tmp_path, "kcc1r1-b", 40.0, "b", 6)
    _cc(tmp_path, "kcc2r1-a", 60.0, "a", 10)
    _cc(tmp_path, "kcc2r1-b", 50.0, "b", 6)
    out = tmp_path / "claude-summary.json"
    assert main(["--results-dir", str(tmp_path), "--prefix", "kcc", "--out", str(out), "--markdown"]) == 0
    assert json.loads(out.read_text())["profiles"]["small"]["pair_wall_s"] == 60.0
    assert "time_saved" in capsys.readouterr().out
