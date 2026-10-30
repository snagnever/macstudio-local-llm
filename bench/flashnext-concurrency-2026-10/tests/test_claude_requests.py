import pytest

from claude_requests import main, max_concurrent, parse_splash_log, read_requests, summarize_requests

LOG = """19:02:07 Started · input 19,296 · cached 0 · effort xhigh · thinking on
19:02:32 Done · input 19,296 · cached 0 · output 112 · tools 23·d2a9ad50 · TTFT 23.7s · 133.8 tok/s · 4.8 tok/cycle
19:02:32 Started · input 19,622 · cached 19,264 · effort xhigh · thinking on
19:02:34 Done · input 19,622 · cached 19,264 · deduplicated 128 · output 204 · tools 23·d2a9ad50 · TTFT 0.6s · 161.3 tok/s · 4.1 tok/cycle
"""


def test_parse_splash_log_pairs_started_and_done():
    reqs = parse_splash_log(LOG)
    assert [r["input_tokens"] for r in reqs] == [19296, 19622]
    assert reqs[0] == {"t_start_s": 0.0, "ttft_s": 23.7, "t_end_s": 25.0, "input_tokens": 19296, "cached_tokens": 0,
                       "output_tokens": 112, "tps": 133.8, "status": 200, "stream": None}
    assert reqs[1]["t_start_s"] == 25.0 and reqs[1]["cached_tokens"] == 19264


def test_parse_splash_log_ignores_orphans():
    orphan_done = LOG.splitlines()[1] + "\n"
    orphan_start = LOG.splitlines()[0] + "\n"
    assert parse_splash_log(orphan_done) == [] and parse_splash_log(orphan_start) == []


def test_parse_splash_log_wraps_midnight():
    text = LOG.replace("19:02:07", "23:59:50").replace("19:02:32", "00:00:10").replace("19:02:34", "00:00:12")
    assert parse_splash_log(text)[0]["t_end_s"] == 20.0


def test_max_concurrent_counts_overlap():
    reqs = [dict(t_start_s=0, t_end_s=10), dict(t_start_s=5, t_end_s=15), dict(t_start_s=15, t_end_s=20)]
    assert max_concurrent(reqs) == 2


def test_summarize_requests_warm_and_cold():
    s = summarize_requests(parse_splash_log(LOG))
    assert s["n"] == 2 and s["max_concurrent"] == 1
    assert s["first_prompt_ttft_s"] == 23.7 and s["new_tokens_p50"] == pytest.approx(9827)
    assert s["warm"] == {"n": 1, "ttft_p50": 0.6, "ttft_p90": 0.6, "tps_p50": 161.3, "tps_min": 161.3, "tps_max": 161.3}


def test_summarize_requests_without_warm_is_none():
    s = summarize_requests(parse_splash_log("\n".join(LOG.splitlines()[:2]) + "\n"))
    assert s["warm"] is None and s["first_prompt_ttft_s"] == 23.7


def test_main_writes_jsonl(tmp_path):
    log = tmp_path / "boot.log"
    log.write_text(LOG)
    out = tmp_path / "req.jsonl"
    assert main(["--splash-log", str(log), "--out", str(out)]) == 0
    assert len(read_requests(out)) == 2
