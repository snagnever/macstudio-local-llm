import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize import (
    evaluate_ane,
    evaluate_arms,
    evaluate_specprefill,
    gate_record,
    omlx_mtp_gate,
    specprefill_selection,
)


def passing_record(arm="C", scenario="append"):
    return {
        "runtime": "mlx-serve",
        "model_id": "ddalcu/Qwen3.8-27B-MLX-Serve-8bit",
        "arm": arm,
        "context_target": 32768,
        "scenario": scenario,
        "cache_enabled": True,
        "cache_hit_ratio": 0.96,
        "swap_delta_gb": 0.1,
        "ram_peak_gb": 55.0,
        "correct": True,
        "error": None,
    }


def pair_record(arm, context, ttft_ms, **overrides):
    record = passing_record(arm=arm, scenario="cold")
    record.update(
        {
            "context_target": context,
            "model_revision": "target-revision",
            "runtime_revision": "v0.6.3rc2",
            "quant": "awq5",
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "repetition_penalty": 1.0,
            "reasoning_effort": "xhigh",
            "max_tokens": 1024,
            "prompt_tokens": 16000,
            "content_class": "audit_retrieval",
            "prompt_identity": f"audit-{context}",
            "fixture_token_hash": "fixture-v1",
            "concurrency": 1,
            "warmup_id": "warmup-v1",
            "ttft_ms": ttft_ms,
            "e2e_ms": ttft_ms + 20,
            "needle_verdicts": {"10": True, "50": True, "90": True},
            "static_prefix_correct": True,
            "specprefill_enabled": arm in {"M", "N"},
            "ane_prefill_enabled": arm == "O",
            "ane_compiled_mlp_layers": 2 if arm == "O" else None,
            "ane_compiled_gdn_layers": 1 if arm == "O" else None,
            "ane_executed_operations": 3 if arm == "O" else None,
        }
    )
    record.update(overrides)
    return record


class SummaryTests(unittest.TestCase):
    def test_specprefill_passes_only_after_twenty_percent_ttft_gain_at_both_contexts(self):
        """Relaxing the 20% pairwise TTFT gate must fail this fixture."""
        records = [
            pair_record("L", 16384, 100), pair_record("M", 16384, 80),
            pair_record("L", 32768, 120), pair_record("M", 32768, 90),
            {**pair_record("M", 65536, 1), "record_type": "verdict", "turns_requested": 20},
        ]

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "PASS")
        self.assertEqual(result["M"]["advance_to_65k"], True)

    def test_specprefill_rejects_mismatched_or_missing_pairing_controls(self):
        """Different builds, prompts, or absent controls must never form a pair."""
        for field, value in (
            ("runtime_revision", "v0.6.4"),
            ("model_id", "other-model"),
            ("scenario", "append"),
            ("max_tokens", 512),
            ("prompt_identity", "other-prompt"),
            ("warmup_id", None),
        ):
            with self.subTest(field=field):
                records = [
                    pair_record("L", 16384, 100), pair_record("M", 16384, 70, **{field: value}),
                    pair_record("L", 32768, 100), pair_record("M", 32768, 70),
                    {**pair_record("M", 65536, 1), "record_type": "verdict", "turns_requested": 20},
                ]
                result = evaluate_specprefill(records)
                self.assertEqual(result["M"]["status"], "FAIL")

    def test_specprefill_requires_all_needles_static_prefix_and_real_tool_verdict(self):
        """Missing Gate 6 evidence is not a passing substitute for measurement."""
        records = [
            pair_record("L", 16384, 100), pair_record("M", 16384, 70),
            pair_record("L", 32768, 100), pair_record("M", 32768, 70),
        ]
        for record in records:
            if record["arm"] == "M":
                record.pop("needle_verdicts")
                record.pop("static_prefix_correct")

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "FAIL")
        self.assertIn("needle_evidence", result["M"]["failures"])
        self.assertIn("static_prefix", result["M"]["failures"])
        self.assertIn("tool_loop", result["M"]["failures"])

    def test_only_one_machine_readable_specprefill_winner_can_advance(self):
        """65K orchestration must consume one selected profile, never an implicit tie."""
        records = [
            pair_record("L", 16384, 100), pair_record("M", 16384, 70), pair_record("N", 16384, 75),
            pair_record("L", 32768, 100), pair_record("M", 32768, 70), pair_record("N", 32768, 75),
            {**pair_record("M", 65536, 1), "record_type": "verdict", "turns_requested": 20},
            {**pair_record("N", 65536, 1), "record_type": "verdict", "turns_requested": 20},
        ]

        selection = specprefill_selection(evaluate_specprefill(records))

        self.assertEqual(selection["winner"]["arm"], "M")
        self.assertEqual(sum(profile["advance_to_65k"] for profile in selection["profiles"].values()), 1)

    def test_specprefill_selection_does_not_promote_a_profile_without_both_contexts(self):
        """A 16K-only improvement cannot leak into the 65K selection file."""
        records = [
            pair_record("L", 16384, 100), pair_record("M", 16384, 70),
            {**pair_record("M", 65536, 1), "record_type": "verdict", "turns_requested": 20},
        ]

        selection = specprefill_selection(evaluate_specprefill(records))

        self.assertIsNone(selection["winner"])

    def test_mtp_gate_requires_isolated_l_evidence(self):
        """SpecPrefill must not run before the L MTP profile records a clean gate."""
        self.assertFalse(omlx_mtp_gate([])["passed"])
        record = pair_record("L", 32768, 100, mtp_enabled=True, specprefill_enabled=False)
        self.assertTrue(omlx_mtp_gate([record])["passed"])

    def test_specprefill_fails_when_needle_or_tool_loop_fails(self):
        """Ignoring functional failures would incorrectly promote SpecPrefill."""
        records = [
            pair_record("L", 16384, 100),
            pair_record("M", 16384, 70, needle_verdicts={"10": False, "50": True, "90": True}),
            pair_record("L", 32768, 100),
            pair_record("M", 32768, 70, static_prefix_correct=False),
            {**pair_record("M", 65536, 1), "record_type": "verdict", "turns_requested": 20, "correct": False},
        ]

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "FAIL")
        self.assertIn("needle_evidence", result["M"]["failures"])
        self.assertIn("tool_loop", result["M"]["failures"])

    def test_null_stability_telemetry_fails_closed_without_raising(self):
        """Absent macmon data must be a verdict failure, never a TypeError or zero."""
        record = pair_record("M", 16384, 70, ram_peak_gb=None, swap_delta_gb=None)

        self.assertIn("ram_peak_gb_unavailable", gate_record(record))
        self.assertIn("swap_delta_gb_unavailable", gate_record(record))

    def test_ane_passes_at_five_percent_ttft_gain_with_confirmed_operations(self):
        """ANE must be both faster and observed executing operations."""
        records = [
            pair_record("J", 16384, 100), pair_record("O", 16384, 95),
            pair_record("J", 32768, 100), pair_record("O", 32768, 90),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "PASS")

    def test_ane_accepts_one_context_gain_but_scopes_execution_to_that_context(self):
        """Gate 7 needs one compatible 5% gain, not two, with local O evidence."""
        records = [
            pair_record("J", 16384, 100, specprefill_enabled=False),
            pair_record("O", 16384, 95, specprefill_enabled=False),
            pair_record("J", 32768, 100, specprefill_enabled=False),
            pair_record("O", 32768, 105, specprefill_enabled=False, ane_executed_operations=0),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "PASS")

    def test_ane_requires_enabled_o_and_disabled_specprefill_on_both_arms(self):
        """Activation evidence outside the valid J/O comparison cannot prove ANE."""
        records = [
            pair_record("J", 16384, 100, specprefill_enabled=True),
            pair_record("O", 16384, 90, ane_prefill_enabled=False),
            pair_record("J", 32768, 100), pair_record("O", 32768, 90),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "FAIL")
        self.assertIn("confounded_specprefill", result["O"]["failures"])
        self.assertIn("ane_not_enabled", result["O"]["failures"])

    def test_ane_is_inconclusive_without_executed_operations(self):
        """Compiled but unused ANE paths cannot establish an acceleration result."""
        records = [
            pair_record("J", 16384, 100),
            pair_record("O", 16384, 90, ane_compiled_mlp_layers=0, ane_compiled_gdn_layers=0, ane_executed_operations=0),
            pair_record("J", 32768, 100),
            pair_record("O", 32768, 90, ane_compiled_mlp_layers=0, ane_compiled_gdn_layers=0, ane_executed_operations=0),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "INCONCLUSIVE")

    def test_ane_is_inconclusive_when_layers_compile_but_execute_zero_operations(self):
        """Compilation without observed execution cannot satisfy the ANE gate."""
        records = [
            pair_record("J", 16384, 100),
            pair_record("O", 16384, 90, ane_executed_operations=0),
            pair_record("J", 32768, 100),
            pair_record("O", 32768, 90, ane_executed_operations=0),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "INCONCLUSIVE")
    def test_good_append_record_passes(self):
        self.assertEqual(gate_record(passing_record()), [])

    def test_bad_tool_record_lists_every_independent_failure(self):
        record = passing_record(scenario="tool_turn")
        record.update(
            {
                "cache_hit_ratio": 0.5,
                "swap_delta_gb": 1.0,
                "ram_peak_gb": 90.0,
                "correct": False,
                "error": "HTTP 500",
            }
        )

        failures = gate_record(record)

        self.assertEqual(
            failures,
            [
                "cache_hit_ratio",
                "swap_delta_gb",
                "ram_peak_gb",
                "correct",
                "error",
            ],
        )

    def test_cache_disabled_control_does_not_fail_for_expected_miss(self):
        record = passing_record(arm="A", scenario="identical")
        record.update({"cache_enabled": False, "cache_hit_ratio": 0.0})

        self.assertEqual(gate_record(record), [])

    def test_middle_mutation_rejects_reuse_far_past_halfway_boundary(self):
        record = passing_record(scenario="middle_mutation")
        record["cache_hit_ratio"] = 0.90

        self.assertEqual(gate_record(record), ["middle_mutation_reuse"])

    def test_evaluation_keeps_all_passing_production_arms(self):
        mlx = passing_record(arm="C")
        gguf = passing_record(arm="F")
        gguf.update(
            {
                "runtime": "llama.cpp",
                "model_id": "unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL",
            }
        )
        failed = passing_record(arm="G")
        failed.update(
            {
                "runtime": "llama.cpp",
                "model_id": "unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL",
                "correct": False,
            }
        )

        evaluations = evaluate_arms([mlx, gguf, failed])

        self.assertTrue(evaluations["C"]["passed"])
        self.assertTrue(evaluations["F"]["passed"])
        self.assertFalse(evaluations["G"]["passed"])
        self.assertEqual(evaluations["G"]["failures"], ["correct"])


if __name__ == "__main__":
    unittest.main()
