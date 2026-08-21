import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cache_probe import (
    cache_hit_ratio,
    cached_tokens_from_usage,
    fixture_token_target,
    _payload,
    mtp_acceptance_from_snapshots,
    scenario_messages,
    token_ids_from_response,
)


class CacheProbeTests(unittest.TestCase):
    def test_fixture_target_reserves_template_and_generation_headroom(self):
        self.assertEqual(fixture_token_target(8192), 7168)
        self.assertEqual(fixture_token_target(32768), 31744)

    def test_diagnostic_payload_keeps_vendor_reasoning_effort(self):
        payload = _payload("model", [{"role": "user", "content": "probe"}])

        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["reasoning_effort"], "xhigh")
        self.assertEqual(payload["max_tokens"], 512)

    def test_cache_ratio_is_bounded_and_handles_empty_prompt(self):
        self.assertEqual(cache_hit_ratio(900, 1000), 0.9)
        self.assertEqual(cache_hit_ratio(1200, 1000), 1.0)
        self.assertEqual(cache_hit_ratio(-10, 1000), 0.0)
        self.assertEqual(cache_hit_ratio(10, 0), 0.0)

    def test_append_keeps_existing_messages_unchanged(self):
        base = [{"role": "user", "content": "base"}]

        updated = scenario_messages("append", base, "suffix")

        self.assertEqual(updated[:1], base)
        self.assertEqual(updated[-1], {"role": "user", "content": "suffix"})
        self.assertEqual(base, [{"role": "user", "content": "base"}])

    def test_tool_turn_appends_matching_call_and_result_ids(self):
        updated = scenario_messages(
            "tool_turn", [{"role": "user", "content": "base"}], "value"
        )

        call_id = updated[-2]["tool_calls"][0]["id"]
        self.assertEqual(updated[-1]["tool_call_id"], call_id)
        self.assertEqual(updated[-1]["content"], "value")

    def test_cached_tokens_uses_openai_prompt_details(self):
        usage = {"prompt_tokens_details": {"cached_tokens": 31744}}

        self.assertEqual(cached_tokens_from_usage(usage), 31744)
        self.assertEqual(cached_tokens_from_usage({}), 0)

    def test_tokenizer_response_rejects_non_integer_tokens(self):
        self.assertEqual(token_ids_from_response({"tokens": [1, 2, 3]}), [1, 2, 3])

        with self.assertRaisesRegex(ValueError, "integer token IDs"):
            token_ids_from_response({"tokens": [1, "2", 3]})

    def test_mtp_acceptance_uses_request_delta_not_process_lifetime_totals(self):
        before = {
            "qwen_draft_tokens_accepted_total": 100.0,
            "qwen_draft_tokens_generated_total": 200.0,
        }
        after = {
            "qwen_draft_tokens_accepted_total": 112.0,
            "qwen_draft_tokens_generated_total": 220.0,
        }

        self.assertEqual(mtp_acceptance_from_snapshots(before, after), 0.6)


if __name__ == "__main__":
    unittest.main()
