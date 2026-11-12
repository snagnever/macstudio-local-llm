import importlib.util
import sys

from conftest import HERE

CONC = HERE.parent / "flashnext-concurrency-2026-10" / "scripts"


def _cr():
    spec = importlib.util.spec_from_file_location("claude_requests", CONC / "claude_requests.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["claude_requests"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parse_splash_log_reads_161_lines():
    text = (HERE / "tests" / "fixtures" / "splash-161-log.txt").read_text()
    reqs = _cr().parse_splash_log(text)
    assert [r["input_tokens"] for r in reqs] == [19300, 19844, 20818]
    assert [r["cached_tokens"] for r in reqs] == [0, 19264, 19808]
    assert [r["output_tokens"] for r in reqs] == [140, 224, 534]
    assert [r["ttft_s"] for r in reqs] == [22.8, 0.9, 1.4]
    assert [r["tps"] for r in reqs] == [138.1, 173.0, 159.9]


def test_parse_splash_log_counts_match_proxy():
    # First rep of rc2 on 1.6.1 (tag h2): the server log against the request_log.py JSONL of the same pair.
    # The proxy also records one request with no input tokens (not a model turn), which the server does not log.
    fx = HERE / "tests" / "fixtures"
    cr = _cr()
    reqs = cr.parse_splash_log((fx / "rc2h2-splash-log.txt").read_text())
    proxy = [r for r in cr.read_requests(fx / "rc2h2-proxy.jsonl") if r["input_tokens"]]
    assert len(proxy) == 44
    assert len(reqs) == len(proxy)
    assert sorted(r["input_tokens"] for r in reqs) == sorted(r["input_tokens"] for r in proxy)
