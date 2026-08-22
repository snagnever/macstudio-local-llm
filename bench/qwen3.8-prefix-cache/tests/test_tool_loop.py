import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tool_loop import (
    TOOLS,
    append_tool_exchange,
    build_tools,
    parse_tool_arguments,
    _tool_payload,
    _final_payload,
)


class ToolLoopTests(unittest.TestCase):
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
