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
