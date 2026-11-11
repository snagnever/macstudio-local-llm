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
            cached = 42 + 1024 + 64
        return 200, {"choices": [{"message": {"content": "ok", "reasoning_content": "r"}, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 42, "completion_tokens": 1100,
                               "prompt_tokens_details": {"cached_tokens": cached}}}


TOOL_CALL = {"id": "call_9", "type": "function", "function": {"name": "record", "arguments": "{}"}}


def by_check(rows):
    return {r["check"]: r for r in rows}


def test_contract_writes_one_line_per_check(ac):
    rows = ac.run_checks(Server(), "m", "1.6.0")
    assert [r["check"] for r in rows] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert all(set(r) >= {"check", "expected", "observed", "pass"} for r in rows)
    json.dumps(rows)


def test_contract_passes_on_the_16_behavior(ac):
    rows = by_check(ac.run_checks(Server(), "m", "1.6.0"))
    assert all(r["pass"] is True for n, r in rows.items() if n != "C7")
    assert rows["C7"]["pass"] is None


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


def test_c7_keeps_the_prefix_of_the_first_turn(ac):
    calls = []
    server = Server()

    def spy(method, path, body=None):
        calls.append(body)
        code, out = server(method, path, body)
        if len(body["messages"]) == 1:
            out["choices"][0]["message"]["tool_calls"] = [TOOL_CALL]
        return code, out
    ac._c7(spy, "m", "1.6.0")
    first, second = calls
    assert second["messages"][1]["tool_calls"] == [TOOL_CALL]  # the model's own call: an added one departs from the reply
    assert second["reasoning_effort"] == first["reasoning_effort"]  # the effort is rendered near the start of the prompt
    assert second["messages"][1]["reasoning_content"] == "r"  # the reply keeps the tokens the budget cut
    # Qwen's templates drop the reasoning of a turn before the last user message, so the turn must continue by tool.
    assert second["messages"][-1]["role"] == "tool" and first["tools"] == second["tools"]
    assert second["messages"][1]["tool_calls"][0]["id"] == second["messages"][-1]["tool_call_id"]


def test_c7_needs_cached_tokens_past_the_cut(ac):
    def answer(cached):
        server = Server()

        def call(method, path, body=None):
            code, out = server(method, path, body)
            if len(body["messages"]) > 1:
                out["usage"]["prompt_tokens_details"]["cached_tokens"] = cached
            else:
                out["choices"][0]["message"]["tool_calls"] = [TOOL_CALL]
            return code, out
        return ac._c7(call, "m", "1.6.0")[1]
    prompt, budget = 42, ac.THINKING_BUDGET
    assert answer(prompt + budget + 1) is True
    assert answer(prompt + budget) is False


def test_restart_verdict_accepts_the_two_documented_503_codes(er):
    attempts = [{"t": 0, "status": 503, "code": "runtime_unavailable", "retry_after": "24"},
                {"t": 1, "status": 503, "code": "engine_recovering", "retry_after": "23"}, {"t": 24, "status": 200}]
    assert er.verdict(attempts, boot_s=30, context_before=32768, context_after=32768)["pass"] is True
    attempts[0]["code"] = "engine_failed"
    assert er.verdict(attempts, boot_s=30, context_before=32768, context_after=32768)["pass"] is False


def test_c7_without_a_tool_call_is_inconclusive_not_a_failure(ac):
    expected, ok, seen = ac._c7(Server(), "m", "1.6.0")
    assert ok is None and seen["inconclusive"] == "no tool call in the reply"


def _replies_with_tool_call_on_attempt(n, calls):
    server = Server()

    def call(method, path, body=None):
        code, out = server(method, path, body)
        calls.append(body)
        first_turns = [c for c in calls if len(c["messages"]) == 1]
        if len(body["messages"]) == 1 and len(first_turns) >= n:
            out["choices"][0]["message"]["tool_calls"] = [TOOL_CALL]
        return code, out
    return call


def test_c7_retries_the_first_turn_until_the_model_calls_the_tool(ac):
    calls = []
    _, _, seen = ac._c7(_replies_with_tool_call_on_attempt(3, calls), "m", "1.6.0")
    assert "inconclusive" not in seen and seen["attempts"] == 3


def test_c7_stays_inconclusive_after_the_last_attempt(ac):
    calls = []
    _, ok, seen = ac._c7(_replies_with_tool_call_on_attempt(99, calls), "m", "1.5.0")
    assert ok is None and seen["attempts"] == ac.TOOL_CALL_ATTEMPTS and "inconclusive" in seen


def test_c7b_control_has_no_thinking_budget_and_only_records(ac):
    calls = []
    expected, ok, seen = ac._c7b(_replies_with_tool_call_on_attempt(1, calls), "m", "1.6.0")
    assert expected is None and ok is None and "cached" in seen
    assert all("thinking_token_budget" not in c for c in calls)
    assert calls[0]["reasoning_effort"] == calls[1]["reasoning_effort"]


def test_main_runs_only_the_named_checks_for_each_rep(ac, tmp_path):
    rows = ac.run_checks(_replies_with_tool_call_on_attempt(1, []), "m", "1.6.0", only=["C7", "C7b"], reps=2)
    assert [r["check"] for r in rows] == ["C7", "C7b", "C7", "C7b"]
    assert [r["rep"] for r in rows] == [1, 1, 2, 2]


def test_c7_record_only_on_150_writes_pass_null(ac):
    calls = []
    _, ok, seen = ac._c7(_replies_with_tool_call_on_attempt(1, calls), "m", "1.5.0")
    assert ok is None and "cached" in seen
