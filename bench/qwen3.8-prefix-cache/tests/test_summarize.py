import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize import evaluate_ane, evaluate_arms, evaluate_specprefill, gate_record


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
            "temperature": 0,
            "max_tokens": 1024,
            "ttft_ms": ttft_ms,
            "e2e_ms": ttft_ms + 20,
            "needle_correct": True,
            "tool_loop_correct": True,
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
        ]

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "PASS")
        self.assertEqual(result["M"]["advance_to_65k"], True)

    def test_specprefill_fails_when_needle_or_tool_loop_fails(self):
        """Ignoring functional failures would incorrectly promote SpecPrefill."""
        records = [
            pair_record("L", 16384, 100),
            pair_record("M", 16384, 70, needle_correct=False),
            pair_record("L", 32768, 100),
            pair_record("M", 32768, 70, tool_loop_correct=False),
        ]

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "FAIL")
        self.assertIn("needle", result["M"]["failures"])
        self.assertIn("tool_loop", result["M"]["failures"])

    def test_ane_passes_at_five_percent_ttft_gain_with_confirmed_operations(self):
        """ANE must be both faster and observed executing operations."""
        records = [
            pair_record("J", 16384, 100), pair_record("O", 16384, 95),
            pair_record("J", 32768, 100), pair_record("O", 32768, 90),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "PASS")

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
