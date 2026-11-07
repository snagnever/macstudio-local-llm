import json
import subprocess
import sys

import pytest
from conftest import SCRIPTS, clean_env, load


@pytest.fixture(scope="module")
def sl():
    return load("serving_load")


@pytest.fixture(scope="module")
def su():
    return load("summarize_load")


def rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def test_aging_prompts_are_distinct_and_sized(sl):
    prompts = sl.build_aging_prompts(rounds=6, sessions=3, prompt_tokens=190960, seed=0, chars_per_token=3.6)
    flat = [p for r in prompts for p in r]
    assert len(flat) == 18
    for a in range(len(flat)):
        assert abs(len(flat[a]) / 3.6 - 190960) / 190960 < 0.02
        for b in range(a + 1, len(flat)):
            n = 0
            while n < 2000 and flat[a][n] == flat[b][n]:
                n += 1
            assert n < 1024, (a, b, n)


def test_aging_is_deterministic(sl):
    one = sl.build_aging_prompts(rounds=1, sessions=2, prompt_tokens=8000, seed=3, chars_per_token=3.6)
    two = sl.build_aging_prompts(rounds=1, sessions=2, prompt_tokens=8000, seed=3, chars_per_token=3.6)
    other = sl.build_aging_prompts(rounds=1, sessions=2, prompt_tokens=8000, seed=4, chars_per_token=3.6)
    assert one == two and one != other


def test_failed_request_is_recorded_and_the_run_continues(sl, fake_server, tmp_path):
    url, cls = fake_server(fail_on=(5,))
    out = tmp_path / "a.jsonl"
    # 1 warm-up + 3 "pre" probes come first, so request 5 is the first load request.
    rc = sl.main(["aging", "--base-url", url + "/v1", "--model", "m", "--status-url", url + "/status", "--out", str(out),
                  "--rounds", "2", "--sessions", "2", "--prompt-tokens", "500", "--idle-minutes", "0",
                  "--probe-reps", "3"])
    assert rc == 0
    reqs = [r for r in rows(out) if r["kind"] == "request"]
    assert len(reqs) == 4
    failed = [r for r in reqs if r["status"] == 500]
    assert len(failed) == 1 and "engine_failed" in failed[0]["error"]
    assert sum(r["status"] == 200 for r in reqs) == 3
    labels = {r["label"] for r in rows(out) if r["kind"] == "probe"}
    assert labels == {"pre", "round1", "round2", "fim", "ocioso"}


def test_request_uses_the_campaign_sampling(sl, fake_server, tmp_path):
    url, cls = fake_server()
    sl.main(["probe", "--base-url", url + "/v1", "--model", "m", "--out", str(tmp_path / "p.jsonl"), "--label", "x", "--reps", "1"])
    body = cls.bodies[0]
    assert (body["temperature"], body["top_p"], body["top_k"], body["frequency_penalty"]) == (1.0, 0.95, 20, 0)
    assert body["reasoning_effort"] == "xhigh" and body["stream"] is True and body["max_tokens"] == 512


def test_decode_uses_completion_tokens(sl):
    times = [10.0 + 0.1 * i for i in range(31)]  # 30 intervals over 3 s
    assert sl.decode_tok_s(300, times) == pytest.approx(100.0)
    assert sl.decode_tok_s(1, [10.0]) is None


def test_status_reader_accepts_schema8(sl):
    rec = sl.status_record({"schema_version": 8, "kv": {"pages_cache": 5}, "state": {}, "disk": {},
                            "memory_governor": {"denied_reservations": 0}, "metrics": {"ttft_parts_ms": {}},
                            "kv_spill": {"history_stream": {}}, "scheduler": {}}, t=1.5)
    assert rec["kind"] == "status" and rec["schema_version"] == 8 and rec["kv"]["pages_cache"] == 5
    assert rec["memory_governor"]["denied_reservations"] == 0 and rec["t"] == 1.5
    old = sl.status_record({"schema_version": 6, "kv": {}}, t=0)
    assert old["memory_governor"] is None and old["metrics"] is None


def test_churn_stops_on_time_and_grows_each_conversation(sl, fake_server, tmp_path):
    url, cls = fake_server()
    out = tmp_path / "c.jsonl"
    rc = sl.main(["churn", "--base-url", url + "/v1", "--model", "m", "--status-url", url + "/status", "--out", str(out),
                  "--minutes", "0.02", "--clients", "2", "--base-tokens", "200", "--step-tokens", "100",
                  "--max-tokens", "10", "--order", "1,0"])
    assert rc == 0
    reqs = [r for r in rows(out) if r["kind"] == "request"]
    assert {r["session"] for r in reqs} == {0, 1}
    sizes = [len(b["messages"]) for b in cls.bodies]
    assert max(sizes) >= 3  # user, assistant, user: the conversation grew past its first turn


def test_churn_resend_round_adds_no_new_text(sl):
    conv = sl.Conversation("hay", step_text=lambda n: f"more {n}")
    sent = {}
    for n in range(1, 6):
        sent[n] = [dict(m) for m in conv.messages]
        conv.advance(n, "reply")
    assert sent[4] == sent[3]  # every fourth round resends the conversation as it was
    assert len(sent[5]) > len(sent[4])
    assert all(s[-1]["role"] == "user" for s in sent.values())  # a final assistant message would be a prefill (400)


def test_verdict_thresholds(su):
    assert su.verdict(0.85) == "estavel"
    assert su.verdict(0.84) == "degradado"
    assert su.verdict(0.50) == "degradado"
    assert su.verdict(0.49) == "queda"


def _req(gaps, status=200):
    return {"kind": "request", "round": 1, "session": 0, "status": status, "gaps_s": gaps, "max_gap_s": max(gaps or [0]),
            "decode_tok_s": 50.0, "ttft_s": 1.0, "prompt_tokens": 1, "cached_tokens": 0, "error": None}


def test_stall_gate(su):
    assert su.stall([_req([1.0] * 200)]) == "pass"
    assert su.stall([_req([10.1])]) == "fail"
    assert su.stall([_req([0.1] * 98 + [5.1, 5.1])]) == "fail"
    assert su.stall([_req([], status=500)]) == "fail"


def test_summary_prints_verdict_from_pre_and_fim(su, tmp_path):
    p = tmp_path / "x.jsonl"
    recs = [{"kind": "probe", "label": "pre", "ttft_s": 0.1, "decode_tok_s": 100.0},
            {"kind": "probe", "label": "fim", "ttft_s": 0.1, "decode_tok_s": 40.0},
            _req([0.1]), {"kind": "status", "t": 1, "schema_version": 6, "kv": {"pages_cache": 1, "pages_free": 2},
                          "state": {}, "disk": {}, "memory_governor": None, "metrics": None}]
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    out = subprocess.run([sys.executable, str(SCRIPTS / "summarize_load.py"), str(p)], capture_output=True, text=True,
                         env=clean_env(), check=True).stdout
    assert "verdict=queda" in out and "stall=pass" in out and "| rodada |" in out


def test_proxy_capture_flags_key_headers(tmp_path):
    pc = load("proxy_capture")
    a = pc.record("GET http://127.0.0.1:8585/health HTTP/1.1", {"Authorization": "Bearer sekret"})
    b = pc.record("GET http://127.0.0.1:8585/status HTTP/1.1", {"x-api-key": "sekret"})
    c = pc.record("GET http://127.0.0.1:8585/health HTTP/1.1", {"Accept": "*/*"})
    assert a["has_key"] and b["has_key"] and not c["has_key"]
    assert "sekret" not in json.dumps([a, b, c])
