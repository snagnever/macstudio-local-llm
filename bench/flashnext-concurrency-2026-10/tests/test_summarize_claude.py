import json

import pytest

from summarize_claude import main, summarize_claude

COLD = {"t_start_s": 0.0, "ttft_s": 23.7, "t_end_s": 25.0, "input_tokens": 19296, "cached_tokens": 0,
        "output_tokens": 112, "tps": 133.8, "status": 200, "stream": None}
WARM = {"t_start_s": 25.0, "ttft_s": 0.6, "t_end_s": 27.0, "input_tokens": 19622, "cached_tokens": 19264,
        "output_tokens": 204, "tps": 161.3, "status": 200, "stream": None}


def _cc(results, name, wall, task, turns, **extra):
    data = {"wall_s": wall, "task": task, "num_turns": turns, "is_error": False, "task_done": True}
    data.update(extra)
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


# ---- fix pass after the whole-branch review ----

def test_rep_number_parses_when_prefix_contains_r(tmp_path):
    for r in (1, 2):
        _cc(tmp_path, f"rc1r{r}-c", 400.0, "c", 30)
        _cc(tmp_path, f"rc1r{r}-d", 380.0, "d", 28)
        _cc(tmp_path, f"rc2r{r}-c", 600.0, "c", 30)
        _cc(tmp_path, f"rc2r{r}-d", 590.0, "d", 28)
    p = summarize_claude(tmp_path, "rc")["profiles"]["realistic"]
    assert p["pair_wall_s"] == 600.0 and p["time_saved"] == pytest.approx(1 - 600 / 780)


def test_pair_request_files_per_session_share_one_clock(tmp_path):
    # One file per session of the same rep (the proxy layout): counted once, on a shared clock.
    a = [dict(COLD, t_start_s=0.0, t_end_s=25.0), dict(WARM, t_start_s=25.0, t_end_s=27.0)]
    b = [dict(COLD, t_start_s=1.0, t_end_s=30.0), dict(WARM, t_start_s=30.0, t_end_s=32.0)]
    _req(tmp_path, "rc2r1-c", a)
    _req(tmp_path, "rc2r1-d", b)
    _req(tmp_path, "rc2r2-c", a)
    _req(tmp_path, "rc2r2-d", b)
    r = summarize_claude(tmp_path, "rc")["requests"]["pair"]
    assert r["n"] == 8 and r["max_concurrent"] == 2


def test_timed_out_session_is_an_error_not_a_mean(tmp_path):
    _cc(tmp_path, "kcc1r1-a", 40.0, "a", 10)
    (tmp_path / "cc-kcc1r2-a.json").write_text(json.dumps(
        {"parse_error": True, "wall_s": 1800.0, "task": "a", "sessions": 1, "exit": 143, "task_done": False}))
    p = summarize_claude(tmp_path, "kcc")["profiles"]["small"]
    assert p["alone_s"]["a"] == 40.0 and p["errors"] == 1 and p["task_done"] is False


# ---- campaign B: variants (rc2s = subagents, rc2d = decode-share) ----

def test_variant_files_are_not_counted_in_the_main_pair(tmp_path):
    _cc(tmp_path, "rc2r1-c", 300, "c", 25)
    _cc(tmp_path, "rc2r1-d", 280, "d", 22)
    _cc(tmp_path, "rc2sr1-c", 400, "c", 25)
    _cc(tmp_path, "rc2sr1-d", 390, "d", 22)
    _req(tmp_path, "rc2r1-c", [COLD, WARM])
    _req(tmp_path, "rc2sr1-c", [COLD, WARM, WARM])
    s = summarize_claude(tmp_path, "rc")
    assert s["profiles"]["realistic"]["pair_wall_s"] == 300 and "subagents" not in s
    assert s["profiles"]["realistic"]["pair_s"] == {"c": 300, "d": 280}
    assert s["requests"]["pair"]["n"] == 2


def test_variants_get_their_own_key_with_serial_from_the_main_alone(tmp_path):
    _cc(tmp_path, "rc1r1-c", 200, "c", 25)
    _cc(tmp_path, "rc1r1-d", 200, "d", 22)
    _cc(tmp_path, "rc2sr1-c", 300, "c", 25, parallel_agent_calls=3, subagents_spawned=6)
    _cc(tmp_path, "rc2sr1-d", 380, "d", 22, parallel_agent_calls=3, subagents_spawned=6)
    _req(tmp_path, "rc2sr1-c", [COLD, WARM, WARM, WARM])
    _req(tmp_path, "rc2sr1-d", [COLD, WARM, WARM, WARM])
    s = summarize_claude(tmp_path, "rc", variants={"s": "subagents", "d": "decode_share"})
    sub = s["subagents"]
    assert sub["profile"]["pair_wall_s"] == 380 and sub["profile"]["serial_sum_s"] == 400
    assert abs(sub["profile"]["time_saved"] - (1 - 380 / 400)) < 1e-9
    assert sub["profile"]["pair_s"] == {"c": 300, "d": 380} and sub["profile"]["errors"] == 0
    assert sub["parallel_agent_calls"] == 6 and sub["subagents_spawned"] == 12 and sub["requests"]["n"] == 8
    assert "decode_share" not in s  # no rc2d files in this dir


def test_rep_regex_with_variant_letter():
    from summarize_claude import _rep
    assert _rep("cc-rc2sr3-c.json", "rc", "2", "s") == "3" and _rep("cc-rc2sr3-c.json", "rc", "2") is None
    assert _rep("req-rc2sr3-d.jsonl", "rc", "2", "s") == "3" and _rep("cc-rc2r3-c.json", "rc", "2", "s") is None


def test_main_variants_flag(tmp_path):
    _cc(tmp_path, "rc1r1-c", 200, "c", 25)
    _cc(tmp_path, "rc1r1-d", 200, "d", 22)
    _cc(tmp_path, "rc2dr1-c", 300, "c", 25)
    _cc(tmp_path, "rc2dr1-d", 380, "d", 22)
    out = tmp_path / "claude-summary-splash.json"
    assert main(["--results-dir", str(tmp_path), "--prefix", "rc", "--out", str(out),
                 "--variants", "s=subagents,d=decode_share"]) == 0
    data = json.loads(out.read_text())
    assert data["decode_share"]["profile"]["pair_wall_s"] == 380 and "subagents" not in data
