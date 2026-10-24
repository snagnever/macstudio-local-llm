import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tool_loop import (
    TOOLS,
    append_tool_exchange,
    build_tools,
    parse_tool_arguments,
    _metrics_snapshot,
    _tool_payload,
    _final_payload,
    build_parser,
    sampling_controls_from_args,
    sampling_record_fields,
)
import tool_loop


class ToolLoopTests(unittest.TestCase):
    def test_missing_optional_metrics_endpoint_returns_empty_snapshot(self):
        error = HTTPError("http://example.test/metrics", 404, "Not Found", {}, None)
        with patch("tool_loop.urlopen", side_effect=error):
            self.assertEqual(
                _metrics_snapshot("http://example.test/metrics", runtime="oMLX"),
                {},
            )

    def test_api_model_can_differ_from_the_recorded_artifact(self):
        """MTPLX serves an alias while results must retain the pinned HF id."""
        args = build_parser().parse_args(
            [
                "--base-url", "http://127.0.0.1:8000/v1",
                "--model", "Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed",
                "--api-model", "mtplx",
                "--runtime", "MTPLX",
                "--runtime-revision", "v2.9.1/bd44215",
                "--model-revision", "123db8bc",
                "--arm", "V",
                "--session-id", "session",
                "--output", "/tmp/tool-loop.jsonl",
            ]
        )

        self.assertEqual(args.model, "Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed")
        self.assertEqual(args.api_model, "mtplx")
    def test_dspark_metrics_snapshot_reads_the_official_json_shape(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return (
                    b'{"model":"target","mode":"dflash","requests":1,'
                    b'"mean_accept_len":3.5,"mean_decode_tokens_per_sec":42.0,'
                    b'"prefix_cache":{"enabled":true},"auto_cap":{"cap":7},'
                    b'"rounds":{"accepted":8,"drafted":10,"steps":3}}'
                )

        with patch("tool_loop.urlopen", return_value=Response()):
            metrics = _metrics_snapshot(
                "http://127.0.0.1:8484/metrics", runtime="mlx-dspark"
            )

        self.assertEqual(metrics["mlx_dspark.mean_accept_len"], 3.5)
        self.assertEqual(metrics["mlx_dspark.rounds.accepted"], 8)

    def test_mtplx_metrics_snapshot_reads_the_latest_request(self):
        """MTPLX tool turns expose JSON rather than Prometheus metrics."""
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b'{"latest":{"drafted_tokens":18,"accepted_drafts":11}}'

        with patch("tool_loop.urlopen", return_value=Response()):
            metrics = _metrics_snapshot(
                "http://127.0.0.1:8000/metrics", runtime="MTPLX"
            )

        self.assertEqual(metrics["mtplx.drafted_tokens"], 18)
        self.assertEqual(metrics["mtplx.accepted_tokens"], 11)

    def test_tool_payload_carries_the_exact_specprefill_profile(self):
        """Tool-loop evidence must be collected with the profile under test."""
        payload = _tool_payload(
            "model", [{"role": "user", "content": "probe"}],
            specprefill=True, specprefill_keep_pct=0.40, specprefill_threshold=8192,
        )

        self.assertTrue(payload["specprefill"])
        self.assertEqual(payload["specprefill_keep_pct"], 0.40)
        self.assertEqual(payload["specprefill_threshold"], 8192)

    def test_final_payload_keeps_the_tool_loop_profile(self):
        """The verdict request must not silently switch sampling or SpecPrefill."""
        payload = _final_payload(
            "model", [{"role": "user", "content": "probe"}],
            specprefill=True, specprefill_keep_pct=0.40, specprefill_threshold=8192,
        )

        self.assertEqual(payload["temperature"], 0)
        self.assertTrue(payload["specprefill"])
        # The final prompt must demand the full verbatim identifiers so the grader,
        # which matches the complete marker strings, tests what it intends to test.
        final_message = payload["messages"][-1]["content"].lower()
        self.assertIn("verbatim", final_message)
        self.assertIn("abbreviate", final_message)

    def test_tool_payload_accepts_the_official_vendor_sampling(self):
        """A performance stage must not inherit the diagnostic temperature."""
        controls = {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "repetition_penalty": 1.0,
            "reasoning_effort": "xhigh",
        }

        payload = _tool_payload(
            "mtplx",
            [{"role": "user", "content": "probe"}],
            sampling_controls=controls,
        )

        self.assertEqual(payload["temperature"], 1.0)
        self.assertEqual(payload["top_p"], 0.95)
        self.assertEqual(payload["top_k"], 20)

    def test_tool_loop_records_the_sampling_profile_it_sends(self):
        controls = {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "repetition_penalty": 1.0,
            "reasoning_effort": "xhigh",
        }

        self.assertEqual(sampling_record_fields(controls), controls)

    def test_frequency_penalty_flag_reaches_the_request(self):
        """mlx-serve #912: a client frequency_penalty of 1 broke tool calls on 26.10.2."""
        base = ["--base-url", "u", "--model", "m", "--runtime", "r", "--runtime-revision", "v",
                "--model-revision", "w", "--arm", "a", "--session-id", "s", "--output", "o.jsonl"]
        default = sampling_controls_from_args(build_parser().parse_args(base))
        self.assertEqual(default["frequency_penalty"], 0.0)

        controls = sampling_controls_from_args(build_parser().parse_args(base + ["--frequency-penalty", "1"]))
        payload = _tool_payload("m", [{"role": "user", "content": "probe"}], sampling_controls=controls)
        self.assertEqual(payload["frequency_penalty"], 1.0)
        self.assertEqual(sampling_record_fields(controls)["frequency_penalty"], 1.0)

    def test_tool_loop_max_tokens_reaches_payload(self):
        """Splash stack-updates Task 10: turn-1 failures were finish_reason length at 512 tokens."""
        base = ["--base-url", "u", "--model", "m", "--runtime", "r", "--runtime-revision", "v",
                "--model-revision", "w", "--arm", "a", "--session-id", "s", "--output", "o.jsonl"]
        self.assertEqual(build_parser().parse_args(base).max_tokens, 512)
        args = build_parser().parse_args(base + ["--max-tokens", "2048"])
        payload = _tool_payload("m", [{"role": "user", "content": "probe"}],
                                sampling_controls=sampling_controls_from_args(args), max_tokens=args.max_tokens)
        self.assertEqual(payload["max_tokens"], 2048)
        self.assertEqual(_tool_payload("m", [])["max_tokens"], 512)

    def test_failed_turn_records_finish_reason_and_dumps_the_message(self):
        """Splash k2a answered turn 1 without a tool call: keep the reply to see why."""
        reply = {"role": "assistant", "content": "", "reasoning_content": "thinking..."}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "results" / "probe.jsonl"
            argv = ["tool_loop.py", "--base-url", "u", "--model", "m", "--runtime", "r",
                    "--runtime-revision", "v", "--model-revision", "w", "--arm", "a",
                    "--session-id", "s1", "--output", str(out), "--turns", "4"]
            with patch.object(sys, "argv", argv), \
                    patch.object(tool_loop, "_chat_once",
                                 return_value=(reply, {"completion_tokens": 512}, "length")):
                tool_loop.main()
            turn = json.loads(out.read_text().splitlines()[0])
            self.assertFalse(turn["correct"])
            self.assertEqual(turn["finish_reason"], "length")
            self.assertEqual(turn["completion_tokens"], 512)
            dump = json.loads((Path(tmp) / "logs" / "tool-loop" / "s1-turn1-fail.json").read_text())
            self.assertEqual(dump["finish_reason"], "length")
            self.assertEqual(dump["message"], reply)

    def test_build_tools_returns_fresh_stably_ordered_schemas(self):
        first = build_tools()
        first[0]["function"]["name"] = "mutated"

        second = build_tools()

        self.assertEqual(
            [tool["function"]["name"] for tool in second],
            [
                "read_fixture",
                "search_fixture",
                "run_fixture_test",
                "record_result",
            ],
        )
        self.assertEqual(TOOLS[0]["function"]["name"], "read_fixture")

    def test_exchange_preserves_reasoning_and_matches_tool_call_id(self):
        messages = [{"role": "user", "content": "start"}]
        call = {
            "role": "assistant",
            "content": "",
            "reasoning_content": "inspect fixture",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "read_fixture",
                        "arguments": '{"path":"audit.txt"}',
                    },
                }
            ],
        }

        updated = append_tool_exchange(messages, call, "fixture-value")

        self.assertEqual(updated[-2]["reasoning_content"], "inspect fixture")
        self.assertEqual(updated[-1]["tool_call_id"], "call_1")
        self.assertEqual(messages, [{"role": "user", "content": "start"}])

    def test_tool_arguments_require_valid_json_and_required_fields(self):
        self.assertEqual(
            parse_tool_arguments("read_fixture", '{"path":"audit.txt"}'),
            {"path": "audit.txt"},
        )

        with self.assertRaisesRegex(ValueError, "valid JSON object"):
            parse_tool_arguments("read_fixture", "not-json")
        with self.assertRaisesRegex(ValueError, "requires: path"):
            parse_tool_arguments("read_fixture", "{}")
        with self.assertRaisesRegex(ValueError, "unexpected arguments"):
            parse_tool_arguments(
                "read_fixture", '{"path":"audit.txt","extra":true}'
            )


if __name__ == "__main__":
    unittest.main()
