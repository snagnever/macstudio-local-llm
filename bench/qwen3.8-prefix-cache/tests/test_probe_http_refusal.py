"""A memory-guard refusal (MTPLX 507, mlx-serve 400, ...) must become a
JSONL record, not a crash that leaves the campaign's 256K band with a
0-byte output file. Covers the _stream_chat_checked/_error_record/
_run_scenario_repeat plumbing directly, plus one end-to-end main() run."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError, URLError


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cache_probe
from cache_probe import (
    RequestFailure,
    _error_record,
    _messages_for_scenario,
    _priming_messages,
    _prompt_identity,
    _run_scenario_repeat,
    _static_prefix_hash,
    _stream_chat_checked,
)
from fixtures import PromptFixture
from sse_client import StreamResult


def _mtplx_507() -> HTTPError:
    return HTTPError(
        "http://example.test/v1/chat/completions",
        507,
        "Insufficient Storage",
        {},
        io.BytesIO(b'{"error":"prompt exceeds machine fit 114688"}'),
    )


def _fixture() -> PromptFixture:
    return PromptFixture(
        text="fixture body",
        token_ids=[1, 2, 3],
        needles=("XENON-7592-FALCON", "ARGON-1844-EMBER", "NEON-6301-ORBIT"),
        question="Return the keys.",
    )


def _args(**overrides) -> SimpleNamespace:
    base = dict(
        base_url="http://example.test/v1",
        arm="FX",
        context=131072,
        session_id="session",
        runtime="MTPLX",
        runtime_revision="v2.11.2",
        model="Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed",
        model_revision="target",
        cache_enabled=True,
        mtp_enabled=True,
        specprefill=None,
        specprefill_keep_pct=None,
        specprefill_threshold=None,
        ane_prefill_enabled=False,
        metrics_url=None,
        machine_url=None,
        mlx_dspark_metrics_url=None,
        drafter_id=None,
        drafter_revision=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class StreamChatCheckedTests(unittest.TestCase):
    def test_http_error_becomes_a_non_fatal_request_failure_with_body(self):
        with patch.object(cache_probe, "stream_chat", side_effect=_mtplx_507()):
            with self.assertRaises(RequestFailure) as raised:
                _stream_chat_checked("http://example.test/v1", {})

        failure = raised.exception
        self.assertFalse(failure.fatal)
        self.assertTrue(failure.message.startswith("http_507"))
        self.assertIn("machine fit", failure.message)
        self.assertGreaterEqual(failure.elapsed_ms, 0.0)

    def test_connection_refused_becomes_a_fatal_request_failure(self):
        with patch.object(
            cache_probe, "stream_chat",
            side_effect=URLError("[Errno 61] Connection refused"),
        ):
            with self.assertRaises(RequestFailure) as raised:
                _stream_chat_checked("http://example.test/v1", {})

        failure = raised.exception
        self.assertTrue(failure.fatal)
        self.assertTrue(failure.message.startswith("connection:"))


class ErrorRecordTests(unittest.TestCase):
    def test_error_record_matches_the_failed_request_field_contract(self):
        failure = RequestFailure("http_507: Insufficient Storage: prompt exceeds machine fit 114688", elapsed_ms=42.0, fatal=False)
        args = _args()

        record = _error_record(
            args, "cold", 1, failure, ("XENON", "ARGON", "NEON"), "fixturehash", 0, 0, 0,
            error_stage="measured",
        )

        self.assertEqual(record["run_id"].split("-", 1)[1], "FX-131072-cold-r1")
        self.assertEqual(record["arm"], "FX")
        self.assertEqual(record["runtime"], "MTPLX")
        self.assertEqual(record["runtime_revision"], "v2.11.2")
        self.assertEqual(record["model_id"], args.model)
        self.assertEqual(record["context_target"], 131072)
        self.assertEqual(record["scenario"], "cold")
        self.assertEqual(record["repeat"], 1)
        self.assertTrue(record["error"].startswith("http_507"))
        self.assertIn("machine fit", record["error"])
        self.assertEqual(record["error_stage"], "measured")
        self.assertFalse(record["correct"])
        self.assertIsNone(record["finish_reason"])
        self.assertEqual(record["completion_tokens"], 0)
        self.assertEqual(record["decode_tps"], 0.0)
        self.assertIsNone(record["cache_hit_ratio"])
        self.assertEqual(record["ttft_ms"], 42.0)
        self.assertEqual(record["e2e_ms"], 42.0)
        self.assertEqual(record["temperature"], cache_probe.SAMPLING_CONTROLS["temperature"])

    def test_error_record_requires_an_explicit_error_stage(self):
        """error_stage is keyword-only and has no default -- every call site
        (warmup/prime/measured) must say which request failed."""
        failure = RequestFailure("connection: refused", elapsed_ms=1.0, fatal=True)
        args = _args()

        with self.assertRaises(TypeError):
            _error_record(
                args, "cold", 1, failure, ("XENON",), "fixturehash", 0, 0, 0,
            )


class RunScenarioRepeatTests(unittest.TestCase):
    def test_http_507_refusal_becomes_a_record_and_does_not_stop_the_loop(self):
        """The MTPLX memory guard's real refusal shape must land as data."""
        args = _args()
        with patch.object(cache_probe, "stream_chat", side_effect=_mtplx_507()):
            record, stop = _run_scenario_repeat(
                args, "model-id", "cold", 1, _fixture(), "mutated", "suffix",
                [1, 2], 0, 0, "fixturehash", lambda text: [], cache_probe.SAMPLING_CONTROLS,
            )

        self.assertFalse(stop)
        self.assertEqual(record["scenario"], "cold")
        self.assertTrue(record["error"].startswith("http_507"))
        self.assertIn("machine fit", record["error"])
        # cold has no priming step, so its only request is the measured one.
        self.assertEqual(record["error_stage"], "measured")
        self.assertFalse(record["correct"])
        self.assertIsNone(record["finish_reason"])
        self.assertEqual(record["completion_tokens"], 0)
        self.assertEqual(record["decode_tps"], 0.0)
        self.assertIsNone(record["cache_hit_ratio"])

    def test_connection_refused_is_fatal_and_stops_the_loop(self):
        args = _args()
        with patch.object(
            cache_probe, "stream_chat",
            side_effect=URLError("[Errno 61] Connection refused"),
        ):
            record, stop = _run_scenario_repeat(
                args, "model-id", "cold", 1, _fixture(), "mutated", "suffix",
                [1, 2], 0, 0, "fixturehash", lambda text: [], cache_probe.SAMPLING_CONTROLS,
            )

        self.assertTrue(stop)
        self.assertTrue(record["error"].startswith("connection:"))
        self.assertEqual(record["error_stage"], "measured")

    def test_a_refusal_on_one_scenario_does_not_block_the_next(self):
        """A refused `cold` must not hide whether `tool_turn` is also refused."""
        success = StreamResult(
            text="XENON-7592-FALCON ARGON-1844-EMBER NEON-6301-ORBIT",
            reasoning_text="", finish_reason="stop", ttft_ms=1.0, e2e_ms=2.0,
            usage={"prompt_tokens": 10, "completion_tokens": 3}, raw_chunks=1,
        )
        args = _args()

        with patch.object(cache_probe, "stream_chat", side_effect=_mtplx_507()):
            cold_record, cold_stop = _run_scenario_repeat(
                args, "model-id", "cold", 1, _fixture(), "mutated", "suffix",
                [1, 2], 0, 0, "fixturehash", lambda text: [], cache_probe.SAMPLING_CONTROLS,
            )
        self.assertFalse(cold_stop)
        self.assertTrue(cold_record["error"].startswith("http_507"))
        self.assertEqual(cold_record["error_stage"], "measured")

        with patch.object(cache_probe, "stream_chat", return_value=success):
            tool_record, tool_stop = _run_scenario_repeat(
                args, "model-id", "tool_turn", 1, _fixture(), "mutated", "suffix",
                [1, 2], 0, 0, "fixturehash", lambda text: [1, 2, 3], cache_probe.SAMPLING_CONTROLS,
            )

        self.assertFalse(tool_stop)
        self.assertIsNone(tool_record["error"])
        self.assertIsNone(tool_record["error_stage"])
        self.assertTrue(tool_record["correct"])


class PrimeRefusalIdentityTests(unittest.TestCase):
    def test_prime_refusal_carries_this_scenarios_identity_not_the_previous_ones(self):
        """Regression: previously, args.messages/static_prefix_hash were only
        assigned AFTER the prime succeeded, so a refused prime built its error
        record from the PREVIOUS scenario's leftovers on `args` (reproduced:
        an append prime-507 record carried cold's prompt_identity/
        static_prefix_hash). They must now be assigned before the prime is
        sent, and the measured request must never be sent when the prime is
        refused."""
        args = _args()
        fixture = _fixture()
        success = StreamResult(
            text="XENON-7592-FALCON ARGON-1844-EMBER NEON-6301-ORBIT",
            reasoning_text="", finish_reason="stop", ttft_ms=1.0, e2e_ms=2.0,
            usage={"prompt_tokens": 10, "completion_tokens": 3}, raw_chunks=1,
        )

        with patch.object(cache_probe, "stream_chat", return_value=success):
            cold_record, cold_stop = _run_scenario_repeat(
                args, "model-id", "cold", 1, fixture, "mutated", "suffix",
                [1, 2], 0, 0, "fixturehash", lambda text: [1], cache_probe.SAMPLING_CONTROLS,
            )
        self.assertFalse(cold_stop)
        self.assertIsNone(cold_record["error"])

        calls = {"n": 0}

        def refuse_everything(base_url, payload):
            calls["n"] += 1
            raise _mtplx_507()

        with patch.object(cache_probe, "stream_chat", side_effect=refuse_everything):
            append_record, append_stop = _run_scenario_repeat(
                args, "model-id", "append", 2, fixture, "mutated", "suffix",
                [1, 2], 0, 0, "fixturehash", lambda text: [1], cache_probe.SAMPLING_CONTROLS,
            )

        self.assertFalse(append_stop)
        self.assertEqual(calls["n"], 1, "the measured request must not be sent after a refused prime")
        self.assertEqual(append_record["scenario"], "append")
        self.assertEqual(append_record["error_stage"], "prime")

        # Must not be cold's leftover identity...
        self.assertNotEqual(append_record["prompt_identity"], cold_record["prompt_identity"])
        self.assertNotEqual(append_record["static_prefix_hash"], cold_record["static_prefix_hash"])
        # ...it must be exactly what a successful append prime would compute.
        expected_messages = _messages_for_scenario(
            "append", fixture.text, "mutated", "suffix", 2, fixture.question
        )
        expected_prime_messages = _priming_messages(fixture.text, 2, fixture.question)
        self.assertEqual(
            append_record["prompt_identity"], _prompt_identity(expected_messages)
        )
        self.assertEqual(
            append_record["static_prefix_hash"],
            _static_prefix_hash(expected_prime_messages),
        )


class MainEndToEndRefusalTests(unittest.TestCase):
    def test_main_records_refusal_attempts_next_scenario_and_exits_3(self):
        """End-to-end: a 507 on `cold` must not crash main(), must still try
        `identical`, and must surface via a distinct non-zero exit code only
        after the JSONL is fully written."""
        class Tokenizer:
            def __call__(self, text):
                return list(range(len(text.split())))

        success = StreamResult(
            text="XENON-7592-FALCON ARGON-1844-EMBER NEON-6301-ORBIT",
            reasoning_text="", finish_reason="stop", ttft_ms=1.0, e2e_ms=2.0,
            usage={"prompt_tokens": 100, "completion_tokens": 5}, raw_chunks=1,
        )
        calls = {"n": 0}

        def fake_stream_chat(base_url, payload):
            calls["n"] += 1
            # call 1 = warmup; call 2 = cold's own measurement (cold has no
            # priming call), which is where the real MTPLX 507 was observed.
            if calls["n"] == 2:
                raise _mtplx_507()
            return success

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "refusal.jsonl"
            argv = [
                "cache_probe.py", "--base-url", "http://example.test/v1",
                "--model", "awq5", "--runtime", "MTPLX",
                "--runtime-revision", "v2.11.2", "--model-revision", "target",
                "--arm", "FX", "--session-id", "refusal-session", "--context", "8192",
                "--scenarios", "cold,identical", "--repeat", "1",
                "--output", str(output), "--tokenizer-path", "/models/awq5",
                "--api-model", "local-awq5-revision",
            ]
            with patch.object(cache_probe, "LocalTokenizer", return_value=Tokenizer()), \
                patch.object(cache_probe, "stream_chat", side_effect=fake_stream_chat), \
                patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(io.StringIO()):
                exit_code = cache_probe.main()

            records = [json.loads(line) for line in output.read_text().splitlines()]

        self.assertEqual(exit_code, 3)
        self.assertEqual(calls["n"], 4)  # warmup, cold, identical-prime, identical-main
        self.assertEqual(len(records), 2)
        cold, identical = records
        self.assertEqual(cold["scenario"], "cold")
        self.assertTrue(cold["error"].startswith("http_507"))
        self.assertIn("machine fit", cold["error"])
        self.assertEqual(cold["error_stage"], "measured")
        self.assertFalse(cold["correct"])
        self.assertEqual(identical["scenario"], "identical")
        self.assertIsNone(identical["error"])
        self.assertIsNone(identical["error_stage"])
        self.assertTrue(identical["correct"])

    def test_main_records_warmup_refusal_and_still_attempts_scenarios(self):
        """A warmup 507 must not crash main(): it must write a record (JSONL
        never left empty), tag it error_stage=warmup on the first requested
        scenario, and still attempt the real scenarios afterwards."""
        class Tokenizer:
            def __call__(self, text):
                return list(range(len(text.split())))

        success = StreamResult(
            text="XENON-7592-FALCON ARGON-1844-EMBER NEON-6301-ORBIT",
            reasoning_text="", finish_reason="stop", ttft_ms=1.0, e2e_ms=2.0,
            usage={"prompt_tokens": 100, "completion_tokens": 5}, raw_chunks=1,
        )
        calls = {"n": 0}

        def fake_stream_chat(base_url, payload):
            calls["n"] += 1
            if calls["n"] == 1:  # the warmup call
                raise _mtplx_507()
            return success

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "warmup-refusal.jsonl"
            argv = [
                "cache_probe.py", "--base-url", "http://example.test/v1",
                "--model", "awq5", "--runtime", "MTPLX",
                "--runtime-revision", "v2.11.2", "--model-revision", "target",
                "--arm", "FX", "--session-id", "warmup-refusal-session", "--context", "8192",
                "--scenarios", "cold,identical", "--repeat", "1",
                "--output", str(output), "--tokenizer-path", "/models/awq5",
                "--api-model", "local-awq5-revision",
            ]
            with patch.object(cache_probe, "LocalTokenizer", return_value=Tokenizer()), \
                patch.object(cache_probe, "stream_chat", side_effect=fake_stream_chat), \
                patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(io.StringIO()):
                exit_code = cache_probe.main()

            records = [json.loads(line) for line in output.read_text().splitlines()]

        self.assertEqual(exit_code, 3)
        self.assertTrue(records, "the JSONL must not be left empty")
        warmup, cold, identical = records
        self.assertEqual(warmup["error_stage"], "warmup")
        self.assertEqual(warmup["scenario"], "cold")  # first requested scenario
        self.assertTrue(warmup["error"].startswith("http_507"))
        self.assertIn("machine fit", warmup["error"])
        # scenarios still attempted after a non-fatal warmup refusal
        self.assertEqual(cold["scenario"], "cold")
        self.assertIsNone(cold["error"])
        self.assertIsNone(cold["error_stage"])
        self.assertEqual(identical["scenario"], "identical")
        self.assertIsNone(identical["error"])
        self.assertIsNone(identical["error_stage"])

    def test_main_stops_after_connection_refused_warmup(self):
        """A dead connection during warmup must still produce a record and
        must not attempt any scenario afterwards."""
        class Tokenizer:
            def __call__(self, text):
                return list(range(len(text.split())))

        calls = {"n": 0}

        def fake_stream_chat(base_url, payload):
            calls["n"] += 1
            raise URLError("[Errno 61] Connection refused")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "warmup-connection-refusal.jsonl"
            argv = [
                "cache_probe.py", "--base-url", "http://example.test/v1",
                "--model", "awq5", "--runtime", "MTPLX",
                "--runtime-revision", "v2.11.2", "--model-revision", "target",
                "--arm", "FX", "--session-id", "warmup-conn-session", "--context", "8192",
                "--scenarios", "cold,identical", "--repeat", "1",
                "--output", str(output), "--tokenizer-path", "/models/awq5",
                "--api-model", "local-awq5-revision",
            ]
            with patch.object(cache_probe, "LocalTokenizer", return_value=Tokenizer()), \
                patch.object(cache_probe, "stream_chat", side_effect=fake_stream_chat), \
                patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(io.StringIO()):
                exit_code = cache_probe.main()

            records = [json.loads(line) for line in output.read_text().splitlines()]

        self.assertEqual(exit_code, 3)
        self.assertEqual(calls["n"], 1)  # only the warmup was attempted
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["error_stage"], "warmup")
        self.assertTrue(records[0]["error"].startswith("connection:"))

    def test_main_stops_after_connection_refused(self):
        """A dead port must not be hammered with the remaining scenarios."""
        class Tokenizer:
            def __call__(self, text):
                return list(range(len(text.split())))

        calls = {"n": 0}

        def fake_stream_chat(base_url, payload):
            calls["n"] += 1
            if calls["n"] == 2:
                raise URLError("[Errno 61] Connection refused")
            return StreamResult(
                text="ok", reasoning_text="", finish_reason="stop",
                ttft_ms=1.0, e2e_ms=2.0, usage={}, raw_chunks=1,
            )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "refusal.jsonl"
            argv = [
                "cache_probe.py", "--base-url", "http://example.test/v1",
                "--model", "awq5", "--runtime", "MTPLX",
                "--runtime-revision", "v2.11.2", "--model-revision", "target",
                "--arm", "FX", "--session-id", "refusal-session", "--context", "8192",
                "--scenarios", "cold,identical", "--repeat", "1",
                "--output", str(output), "--tokenizer-path", "/models/awq5",
                "--api-model", "local-awq5-revision",
            ]
            with patch.object(cache_probe, "LocalTokenizer", return_value=Tokenizer()), \
                patch.object(cache_probe, "stream_chat", side_effect=fake_stream_chat), \
                patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(io.StringIO()):
                exit_code = cache_probe.main()

            records = [json.loads(line) for line in output.read_text().splitlines()]

        self.assertEqual(exit_code, 3)
        self.assertEqual(calls["n"], 2)  # warmup + cold; identical never attempted
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["error"].startswith("connection:"))
        self.assertEqual(records[0]["error_stage"], "measured")


if __name__ == "__main__":
    unittest.main()
