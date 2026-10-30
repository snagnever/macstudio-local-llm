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


def test_prefill_turn_with_big_new_prompt_is_not_warm():
    # Session B's first prompt in a pair: the system prompt is cached, 3,245 tokens are new, TTFT 23.7 s.
    text = LOG + "19:03:00 Started · input 19,277 · cached 16,032 · effort xhigh · thinking on\n" \
                 "19:03:30 Done · input 19,277 · cached 16,032 · output 100 · tools 23·d2a9ad50 · TTFT 23.7s · 120.0 tok/s · 4.0 tok/cycle\n"
    s = summarize_requests(parse_splash_log(text))
    assert s["warm"]["n"] == 1 and s["warm"]["ttft_p90"] == 0.6
    assert s["first_prompt_ttft_s"] == 23.7 and s["prefill_turns"] == 2


# ---- campaign B: proxy records (cached_tokens / ttft_s may be null, status may be an error) ----

WARM = {"t_start_s": 25.0, "ttft_s": 0.6, "t_end_s": 27.0, "input_tokens": 19622, "cached_tokens": 19264,
        "output_tokens": 204, "tps": 161.3, "status": 200, "stream": None}


def test_null_cached_counts_as_prefill_only_when_ttft_is_long():
    reqs = [dict(WARM, t_start_s=0.0, ttft_s=12.0, t_end_s=15.0, cached_tokens=None),
            dict(WARM, t_start_s=20.0, ttft_s=1.5, t_end_s=22.0, cached_tokens=None)]
    s = summarize_requests(reqs)
    assert s["prefill_turns"] == 1 and s["warm"]["n"] == 1 and s["warm"]["ttft_p50"] == 1.5
    assert s["first_prompt_ttft_s"] == 12.0 and s["new_tokens_p50"] is None


def test_null_ttft_and_non_200_are_errors_not_samples():
    reqs = [dict(WARM, t_start_s=0.0, ttft_s=None, tps=None, t_end_s=1.0, status=529),
            dict(WARM, t_start_s=5.0, ttft_s=1.0, t_end_s=7.0)]
    s = summarize_requests(reqs)
    assert s["errors"] == 1 and s["warm"]["n"] == 1 and s["n"] == 2


def test_summarize_requests_has_zero_errors_by_default():
    assert summarize_requests(parse_splash_log(LOG))["errors"] == 0


def test_empty_200_responses_are_not_model_turns():
    # A 200 with no content delta and no tokens (a non-message endpoint behind the proxy) is neither a sample,
    # an error nor a request: it must not count in n or in max_concurrent.
    empty = {"t_start_s": 1.0, "ttft_s": None, "t_end_s": 1.01, "input_tokens": 0, "cached_tokens": None,
             "output_tokens": 0, "tps": None, "status": 200, "stream": None}
    s = summarize_requests([dict(WARM, t_start_s=0.0, t_end_s=3.0), empty])
    assert s["n"] == 1 and s["max_concurrent"] == 1 and s["errors"] == 0 and s["warm"]["n"] == 1
