import json

import pytest
from conftest import load


@pytest.fixture(scope="module")
def ac():
    return load("api_contract")


@pytest.fixture(scope="module")
def er():
    return load("engine_restart")


class Server:
    """A Splash stand-in: answers by path and records the calls. `stop_string_status` plays C1."""

    def __init__(self, schema=8, stop_string_status=400, cancelled=0):
        self.schema, self.stop_string_status, self.cancelled = schema, stop_string_status, cancelled
        self.requests = {"completed": 0, "cancelled": 0}

    def __call__(self, method, path, body=None):
        if path == "/status":
            out = {"schema_version": self.schema, "requests": dict(self.requests)}
            if self.schema == 8:
                out.update(memory_governor={}, metrics={"ttft_parts_ms": {}, "decode_gap_causes": {}}, kv_spill={"history_stream": {}},
                           memory_plan={"budget": {}})
            return 200, out
        if path == "/v1/messages":
            if isinstance(body.get("stop_sequences"), str):
                return self.stop_string_status, {"error": {"message": "stop_sequences must be an array"}}
            return 200, {"content": [], "usage": {}}
        if path == "/v1/chat/completions/count_tokens":
            return 200, {"input_tokens": 42}
        if len(str(body.get("stop"))) > 16384:
            return 400, {"error": {"message": "stop too long"}}
        if body.get("stop"):
            self.requests["cancelled" if self.cancelled else "completed"] += 1
        cached = 0
        if len(body["messages"]) > 1:
            cached = 42 + 1000
        return 200, {"choices": [{"message": {"content": "ok", "reasoning_content": "r"}, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 42, "completion_tokens": 1100,
                               "prompt_tokens_details": {"cached_tokens": cached}}}


def by_check(rows):
    return {r["check"]: r for r in rows}


def test_contract_writes_one_line_per_check(ac):
    rows = ac.run_checks(Server(), "m", "1.6.0")
    assert [r["check"] for r in rows] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert all(set(r) >= {"check", "expected", "observed", "pass"} for r in rows)
    json.dumps(rows)


def test_contract_passes_on_the_16_behavior(ac):
    assert all(r["pass"] for r in ac.run_checks(Server(), "m", "1.6.0"))


def test_contract_marks_unexpected_status_as_fail(ac):
    rows = by_check(ac.run_checks(Server(stop_string_status=200), "m", "1.6.0"))
    assert rows["C1"]["pass"] is False and rows["C2"]["pass"] is True


def test_contract_marks_stop_counted_as_cancelled_as_fail_on_16(ac):
    assert by_check(ac.run_checks(Server(cancelled=1), "m", "1.6.0"))["C5"]["pass"] is False


def test_contract_expects_the_15_behavior_on_15(ac):
    rows = by_check(ac.run_checks(Server(schema=6, stop_string_status=200, cancelled=1), "m", "1.5.0"))
    assert rows["C1"]["pass"] and rows["C5"]["pass"] and rows["C6"]["pass"]


def test_contract_keeps_going_when_a_call_raises(ac):
    def broken(method, path, body=None):
        raise OSError("connection reset")
    rows = ac.run_checks(broken, "m", "1.6.0")
    assert len(rows) == 7 and not any(r["pass"] for r in rows)
    assert "connection reset" in rows[0]["observed"]


def test_restart_verdict_requires_503_with_retry_after_then_200(er):
    good = [{"t": 1, "status": 503, "code": "engine_recovering", "retry_after": "20"}, {"t": 30, "status": 200}]
    assert er.verdict(good, boot_s=20, context_before=262144, context_after=262144)["pass"] is True
    no_header = [{"t": 1, "status": 503, "code": "engine_recovering", "retry_after": None}, {"t": 30, "status": 200}]
    assert er.verdict(no_header, boot_s=20, context_before=262144, context_after=262144)["pass"] is False
    late = [{"t": 1, "status": 503, "code": "engine_recovering", "retry_after": "20"}, {"t": 41, "status": 200}]
    assert er.verdict(late, boot_s=20, context_before=262144, context_after=262144)["pass"] is False
    never = [{"t": 1, "status": 503, "code": "engine_recovering", "retry_after": "20"}]
    assert er.verdict(never, boot_s=20, context_before=262144, context_after=None)["pass"] is False
    shrunk = good
    assert er.verdict(shrunk, boot_s=20, context_before=262144, context_after=131072)["pass"] is False
