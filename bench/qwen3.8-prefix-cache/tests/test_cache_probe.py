import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cache_probe import (
    cache_hit_ratio,
    code_result_verdict,
    cached_tokens_from_usage,
    fixture_token_target,
    _payload,
    _warmup_payload,
    _messages_for_scenario,
    _base_messages,
    _record,
    mtp_acceptance_from_snapshots,
    scenario_messages,
    result_correct,
    token_ids_from_response,
)
from fixtures import build_code_fixture
from sse_client import StreamResult


class CacheProbeTests(unittest.TestCase):
    def test_measurement_record_uses_schema_v3_and_has_speculation_fields(self):
        """Changing the v3 record contract must break this schema assertion."""
        args = SimpleNamespace(
            arm="M", context=16384, session_id="session", runtime="oMLX",
            runtime_revision="v0.6.3rc2", model="awq5", model_revision="target",
            cache_enabled=True, mtp_enabled=True, specprefill=True,
            specprefill_keep_pct=0.40, specprefill_threshold=8192,
            ane_prefill_enabled=False,
        )
        result = StreamResult(
            text="XENON", reasoning_text="", finish_reason="stop", ttft_ms=10.0,
            e2e_ms=20.0,
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 2,
                "x_mlx_dspark": {"prompt_work_mode": "sparse"},
            },
            raw_chunks=1,
        )

        record = _record(
            args, "cold", 1, result, "XENON", "fixture", {}, {}, 0, 0, 0
        )

        required = {
            "specprefill_enabled", "specprefill_draft_model",
            "specprefill_draft_revision", "specprefill_keep_pct",
            "specprefill_threshold", "specprefill_selected_tokens",
            "specprefill_scored_tokens", "specprefill_draft_ms",
            "specprefill_target_ms", "static_prefix_cached_tokens",
            "ane_prefill_enabled", "ane_prefill_tuned",
            "ane_compiled_mlp_layers", "ane_compiled_gdn_layers",
            "prompt_work_mode", "speculation_mode", "drafter_id",
            "drafter_revision", "draft_cap_policy", "draft_cap_resolved",
            "drafted_tokens", "accepted_tokens", "accept_length",
            "verification_steps", "decode_speedup_vs_baseline",
            "machine_roofline_tps", "decode_roofline_ratio",
        }
        self.assertEqual(record["schema_version"], 3)
        self.assertTrue(required.issubset(record))
        self.assertEqual(record["prompt_work_mode"], "sparse")
        self.assertIsNone(record["specprefill_selected_tokens"])
        self.assertEqual(record["runtime_revision"], "v0.6.3rc2")
        self.assertEqual(record["max_tokens"], 1024)
        self.assertEqual(record["concurrency"], 1)
        self.assertEqual(record["warmup_id"], "cache-probe-warmup-v1")
        self.assertTrue(record["prompt_identity"])
        self.assertIn("10", record["needle_verdicts"])

    def test_specprefill_request_options_are_sent_exactly(self):
        """Dropping a request override must make the runtime profile unobservable."""
        payload = _payload(
            "model", [{"role": "user", "content": "probe"}],
            specprefill=True, specprefill_keep_pct=0.40,
            specprefill_threshold=8192,
        )

        self.assertTrue(payload["specprefill"])
        self.assertEqual(payload["specprefill_keep_pct"], 0.40)
        self.assertEqual(payload["specprefill_threshold"], 8192)
    def test_warmup_is_bounded_but_keeps_xhigh(self):
        payload = _warmup_payload("model", "warmup fixture")

        self.assertEqual(payload["reasoning_effort"], "xhigh")
        self.assertEqual(payload["max_tokens"], 64)
        self.assertEqual(payload["messages"][-1]["content"], "warmup fixture")

    def test_cold_repeats_change_the_leading_system_prefix(self):
        first = _messages_for_scenario("cold", "fixture", "mutated", "suffix", 1)
        second = _messages_for_scenario("cold", "fixture", "mutated", "suffix", 2)

        self.assertNotEqual(first[0]["content"], second[0]["content"])
        self.assertEqual(first[1:], second[1:])

    def test_fixture_target_reserves_template_and_generation_headroom(self):
        self.assertEqual(fixture_token_target(8192), 5632)
        self.assertEqual(fixture_token_target(32768), 30208)

    def test_diagnostic_payload_keeps_vendor_reasoning_effort(self):
        payload = _payload("model", [{"role": "user", "content": "probe"}])

        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["reasoning_effort"], "xhigh")
        self.assertEqual(payload["max_tokens"], 1024)

    def test_correctness_requires_visible_non_truncated_answer(self):
        hidden_only = StreamResult(
            text="",
            reasoning_text="the key is XENON",
            finish_reason="length",
            ttft_ms=1.0,
            e2e_ms=2.0,
            usage={},
            raw_chunks=2,
        )
        visible = StreamResult(
            text="XENON",
            reasoning_text="checked",
            finish_reason="stop",
            ttft_ms=1.0,
            e2e_ms=2.0,
            usage={},
            raw_chunks=2,
        )

        self.assertFalse(result_correct(hidden_only, "XENON"))
        self.assertTrue(result_correct(visible, "XENON"))

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

    def test_code_workload_has_a_deterministic_prompt_and_verifiable_result(self):
        encode = lambda text: text.split()
        fixture = build_code_fixture(80, encode)
        messages = _base_messages(fixture.text, fixture.question)

        self.assertIn("def rolling_checksum", fixture.text)
        self.assertNotIn("CODE-RESULT", fixture.text)
        self.assertNotIn(str(fixture.expected_result), messages[-1]["content"])
        self.assertIn('"rolling_checksum"', messages[-1]["content"])
        self.assertEqual(fixture.needles, ())

    def test_code_result_requires_the_derived_structured_value_not_an_echo(self):
        """The MTP code gate must parse a result, not find a disclosed marker."""
        good = StreamResult(
            text='{"rolling_checksum": 32896}', reasoning_text="", finish_reason="stop",
            ttft_ms=1.0, e2e_ms=2.0, usage={}, raw_chunks=1,
        )
        echo = StreamResult(
            text="CODE-RESULT-32896", reasoning_text="", finish_reason="stop",
            ttft_ms=1.0, e2e_ms=2.0, usage={}, raw_chunks=1,
        )

        self.assertEqual(code_result_verdict(good, 32896), (True, 32896))
        self.assertEqual(code_result_verdict(echo, 32896), (False, None))


if __name__ == "__main__":
    unittest.main()
