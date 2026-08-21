import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize import evaluate_arms, gate_record


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


class SummaryTests(unittest.TestCase):
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
