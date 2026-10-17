import json
import stat

import pytest

from conftest import SCRIPTS, clean_env, run

SCENARIOS = (("cold", 3), ("identical", 3), ("append", 3), ("middle_mutation", 1), ("tool_turn", 3))


def approx_tokens(messages):
    return sum(len(m["content"]) for m in messages) // 4


def write_fixture_streams(tmp_path, arm, ctx, tag, tturno, hit, overlap, needles=None, ttft_tool=2.0):
    """One JSONL per stream in the cache_probe record shape: 13 records, a target T_turno, hit on
    append/tool_turn, and wall clocks that overlap across streams (overlap > 0) or run back to back."""
    for k, target in enumerate(tturno, start=1):
        decode = 512 / (target - ttft_tool)
        good = int(needles[k - 1].split("/")[0]) if needles else 13
        offset = 0.0 if overlap[k - 1] > 0 else 10_000.0 * (k - 1)
        recs, i = [], 0
        for scenario, reps in SCENARIOS:
            for rep in range(1, reps + 1):
                start = offset + 100.0 * i
                recs.append({
                    "arm": arm, "context_target": ctx, "scenario": scenario, "repeat": rep,
                    "session_id": f"{arm}-{tag}-s{k}", "concurrency": len(tturno),
                    "ttft_ms": (ttft_tool if scenario == "tool_turn" else 1.5) * 1000,
                    "decode_tps": decode, "prompt_tps": 900.0,
                    "cache_hit_ratio": hit[k - 1] if scenario in ("append", "tool_turn", "identical") else 0.0,
                    "finish_reason": "stop", "error": None, "correct": i < good,
                    "wall_start": start, "wall_end": start + 50.0,
                })
                i += 1
        (tmp_path / f"{arm}-{ctx}-{tag}-s{k}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))


def test_run_parallel_probes_dry_run_lists_streams():
    out = run("bash", SCRIPTS / "run-parallel-probes.sh", "--dry-run", "--streams", "2", "--aux", "--context", "32768",
              "--repeat", "3", "--arm", "w1c2a", "--tag", "e1", "--out", "/tmp/x").stdout
    assert out.count("cache_probe.py") == 2
    assert "--content-class audit_retrieval" in out and "--content-class code" in out
    assert "--session-id w1c2a-e1-s1" in out and "--session-id w1c2a-e1-s2" in out
    assert "--concurrency 2" in out and "--scenario-repeats middle_mutation=1" in out
    assert "aux_load.py" in out and "w1c2a-32768-e1-aux.jsonl" in out


def test_run_parallel_probes_contexts_per_stream():
    out = run("bash", SCRIPTS / "run-parallel-probes.sh", "--dry-run", "--streams", "2", "--contexts", "262144,32768",
              "--repeat", "3", "--arm", "w1c2L", "--tag", "e1b", "--out", "/tmp/x").stdout
    assert "--context 262144" in out and "--context 32768" in out
    assert "w1c2L-262144-e1b-s1.jsonl" in out and "w1c2L-32768-e1b-s2.jsonl" in out


def test_run_parallel_probes_salts_streams_three_and_four():
    out = run("bash", SCRIPTS / "run-parallel-probes.sh", "--dry-run", "--streams", "4", "--context", "32768",
              "--repeat", "3", "--arm", "w1c4", "--tag", "e1", "--out", "/tmp/x").stdout
    lines = [l for l in out.splitlines() if "cache_probe.py" in l]
    assert len(lines) == 4
    assert "--prompt-salt" not in lines[0] and "--prompt-salt" not in lines[1]
    assert "--prompt-salt s3" in lines[2] and "--content-class audit_retrieval" in lines[2]
    assert "--prompt-salt s4" in lines[3] and "--content-class code" in lines[3]


def test_run_parallel_probes_rejects_contexts_count_mismatch():
    bad = run("bash", SCRIPTS / "run-parallel-probes.sh", "--dry-run", "--streams", "2", "--contexts", "262144",
              "--repeat", "3", "--arm", "w1c2L", "--tag", "e1b", "--out", "/tmp/x", check=False)
    assert bad.returncode == 64 and "--contexts" in bad.stderr


def test_run_parallel_probes_fails_when_a_stream_fails(tmp_path):
    fake = tmp_path / "fakepy"
    fake.write_text('#!/bin/bash\ncase "$*" in *aux_load.py*) exit 0 ;; *-s2" "*) exit 3 ;; *) exit 0 ;; esac\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = clean_env({"PARALLEL_PYTHON": str(fake), "BASE_URL": "http://127.0.0.1:1/v1", "MODEL_ID": "m"})
    res = run("bash", SCRIPTS / "run-parallel-probes.sh", "--streams", "2", "--aux", "--context", "32768",
              "--repeat", "1", "--arm", "w1c2a", "--tag", "t", "--out", tmp_path, env=env, check=False)
    assert res.returncode != 0
    assert not list(tmp_path.glob("*.running"))


def test_aux_load_prompts_and_record_shape():
    from aux_load import build_request, record
    for kind in ("permission", "title"):
        req = build_request(kind, model="m")
        assert req["max_tokens"] == 64 and req["chat_template_kwargs"] == {"enable_thinking": False}
        assert req["stream"] is True and req["model"] == "m"
        assert 200 <= approx_tokens(req["messages"]) <= 400
    r = record("title", t_start=1.0, ttft_s=0.4, total_s=0.9, status=200, error=None)
    assert set(r) == {"kind", "t_start", "ttft_s", "total_s", "status", "error"}


def test_aux_load_stops_when_duration_file_is_gone(tmp_path):
    out = tmp_path / "aux.jsonl"
    res = run("python3", SCRIPTS / "aux_load.py", "--base-url", "http://127.0.0.1:1/v1", "--model", "m",
              "--period", "20", "--duration-file", tmp_path / "missing", "--output", out)
    assert res.returncode == 0 and (not out.exists() or out.read_text() == "")


def test_summarize_parallel_gates_and_verdict(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2", ctx=32768, tag="e1",
                          tturno=[9.0, 11.0], hit=[0.97, 0.96], overlap=[0.8, 0.8])
    s = summarize(tmp_path, "w1c2", 32768, "e1", ref_32k=7.9, ref_128k=8.6)
    assert s["verdict"] == "pass" and max(r["ratio"] for r in s["streams"]) == pytest.approx(11.0 / 7.9)
    assert all(r["overlap"] > 0 for r in s["streams"])


def test_summarize_parallel_fails_without_overlap(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2", ctx=32768, tag="e1", tturno=[8.0, 15.9], hit=[0.97, 0.97],
                          overlap=[0.0, 0.0])
    s = summarize(tmp_path, "w1c2", 32768, "e1")
    assert s["verdict"].startswith("fail") and "no overlap" in s["verdict"]


def test_summarize_parallel_single_stream_needs_no_overlap(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c1", ctx=32768, tag="e1", tturno=[7.9], hit=[0.99], overlap=[0.0])
    assert summarize(tmp_path, "w1c1", 32768, "e1")["verdict"] == "pass"


def test_summarize_parallel_ref_256k_and_kv_quant_needles(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2q8", ctx=262144, tag="e1b", tturno=[15.0, 16.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7], needles=["12/13", "13/13"])
    s = summarize(tmp_path, "w1c2q8", 262144, "e1b", ref_256k=11.1)
    assert s["verdict"].startswith("fail") and "needles" in s["verdict"]   # kv-quant arm needs 13/13


def test_summarize_parallel_256k_accepts_11_of_13_without_kv_quant(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2m4", ctx=262144, tag="e1b", tturno=[15.0, 16.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7], needles=["11/13", "13/13"])
    s = summarize(tmp_path, "w1c2m4", 262144, "e1b", ref_256k=11.1)
    assert s["verdict"] == "pass" and s["streams"][0]["needles"] == "11/13"


def test_summarize_parallel_warning_band(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2", ctx=131072, tag="e1", tturno=[13.5, 14.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7])
    assert summarize(tmp_path, "w1c2", 131072, "e1")["verdict"] == "pass-with-warning"   # 14.0/8.6 = 1.63


def test_summarize_parallel_fails_on_ratio_above_two(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2", ctx=32768, tag="e1", tturno=[9.0, 16.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7])
    s = summarize(tmp_path, "w1c2", 32768, "e1")
    assert s["verdict"].startswith("fail") and "ratio" in s["verdict"]


def test_summarize_parallel_fails_on_low_hit(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2", ctx=32768, tag="e1", tturno=[9.0, 9.0], hit=[0.99, 0.93],
                          overlap=[0.7, 0.7])
    s = summarize(tmp_path, "w1c2", 32768, "e1")
    assert s["verdict"].startswith("fail") and "hit" in s["verdict"]


def test_summarize_parallel_counts_aux_errors_and_stalls(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2a", ctx=32768, tag="e1", tturno=[9.0, 9.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7])
    aux = [{"kind": "permission", "t_start": 1.0, "ttft_s": 0.3, "total_s": 0.8, "status": 200, "error": None},
           {"kind": "title", "t_start": 21.0, "ttft_s": 0.4, "total_s": 0.9, "status": 500, "error": "http_500"},
           {"kind": "permission", "t_start": 41.0, "ttft_s": 61.0, "total_s": 61.5, "status": 200, "error": None}]
    (tmp_path / "w1c2a-32768-e1-aux.jsonl").write_text("".join(json.dumps(a) + "\n" for a in aux))
    s = summarize(tmp_path, "w1c2a", 32768, "e1")
    assert s["aux"]["errors"] == 1 and s["aux"]["n"] == 3
    assert s["verdict"].startswith("fail") and "http errors" in s["verdict"] and "stall" in s["verdict"]


def test_summarize_parallel_reads_memory_sampler(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2", ctx=131072, tag="e1", tturno=[9.0, 9.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7])
    logs = tmp_path / "logs"
    logs.mkdir()
    mem = [{"t": 1, "free_gb": 20.0, "wired_gb": 90.0, "swap_used_gb": 1.0},
           {"t": 2, "free_gb": 0.3, "wired_gb": 112.5, "swap_used_gb": 1.2}]
    (logs / "w1c2-131072-t1.0-e1-mem.jsonl").write_text("".join(json.dumps(m) + "\n" for m in mem))
    s = summarize(tmp_path, "w1c2", 131072, "e1", logs_dir=logs)
    assert s["memory"] == {"wired_peak_gb": 112.5, "free_min_gb": 0.3, "swap_delta_gb": pytest.approx(0.2)}
    assert s["verdict"].startswith("fail") and "free" in s["verdict"]


def test_summarize_parallel_context_all_uses_ref_per_stream(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2L", ctx=262144, tag="e1b", tturno=[13.0], hit=[0.99], overlap=[0.7])
    other = tmp_path / "w1c2L-262144-e1b-s1.jsonl"
    write_fixture_streams(tmp_path, arm="w1c2L", ctx=32768, tag="e1b", tturno=[9.0, 9.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7])
    (tmp_path / "w1c2L-32768-e1b-s1.jsonl").unlink()
    assert other.exists()
    s = summarize(tmp_path, "w1c2L", "all", "e1b", ref_256k=11.1)
    ratios = {r["context"]: r["ratio"] for r in s["streams"]}
    assert ratios[262144] == pytest.approx(13.0 / 11.1) and ratios[32768] == pytest.approx(9.0 / 7.9)


def test_summarize_parallel_cli_prints_table_and_verdict(tmp_path):
    write_fixture_streams(tmp_path, arm="w1c2", ctx=32768, tag="e1", tturno=[9.0, 11.0], hit=[0.97, 0.96],
                          overlap=[0.8, 0.8])
    out = run("python3", SCRIPTS / "summarize_parallel.py", "--results-dir", tmp_path, "--arm", "w1c2",
              "--context", "32768", "--tag", "e1", "--markdown").stdout
    assert out.splitlines()[0].startswith("| braço | contexto | stream | T_turno | razão ÷ w1 |")
    assert "VERDICT: pass" in out


def _set_ttft(path, scenario, seconds):
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    for r in rows:
        if r["scenario"] == scenario:
            r["ttft_ms"] = seconds * 1000
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_summarize_parallel_stall_ignores_prefill_bound_middle_mutation(tmp_path):
    from summarize_parallel import summarize
    write_fixture_streams(tmp_path, arm="w1c2", ctx=131072, tag="e1", tturno=[9.0, 9.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7])
    _set_ttft(tmp_path / "w1c2-131072-e1-s1.jsonl", "middle_mutation", 92.0)
    assert summarize(tmp_path, "w1c2", 131072, "e1")["verdict"] == "pass"
    _set_ttft(tmp_path / "w1c2-131072-e1-s2.jsonl", "append", 61.0)
    assert "stall" in summarize(tmp_path, "w1c2", 131072, "e1")["verdict"]
