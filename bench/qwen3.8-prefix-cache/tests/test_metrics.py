import json
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from metrics import (
    metric_delta,
    normalize_server_measurements,
    parse_ane_runtime_evidence,
    parse_macmon,
    parse_prometheus,
)


class MetricsTests(unittest.TestCase):
    def test_server_measurements_preserve_observed_sparse_work_without_inference(self):
        """Replacing observed server telemetry with a prompt-length guess must fail."""
        observed = normalize_server_measurements(
            {
                "x_mlx_dspark": {
                    "prompt_work_mode": "sparse",
                    "machine_roofline_tps": 88.5,
                    "specprefill_selected_tokens": 123,
                }
            },
            {},
        )

        self.assertEqual(observed["prompt_work_mode"], "sparse")
        self.assertEqual(observed["machine_roofline_tps"], 88.5)
        self.assertEqual(observed["specprefill_selected_tokens"], 123)
        self.assertIsNone(observed["specprefill_scored_tokens"])

    def test_ane_metric_counters_use_a_per_request_delta(self):
        """A warmup's lifetime counter must not count as measured ANE work."""
        observed = normalize_server_measurements(
            {},
            {"ane_executed_operations_total": 100.0},
            {"ane_executed_operations_total": 102.0},
        )

        self.assertEqual(observed["ane_executed_operations"], 2.0)

    def test_ane_compiled_layer_gauge_keeps_a_stable_nonzero_state(self):
        """Compilation state is a gauge; only execution counters are delta values."""
        observed = normalize_server_measurements(
            {},
            {"ane_compiled_mlp_layers": 8.0, "ane_executed_operations_total": 3.0},
            {"ane_compiled_mlp_layers": 8.0, "ane_executed_operations_total": 5.0},
        )

        self.assertEqual(observed["ane_compiled_mlp_layers"], 8.0)
        self.assertEqual(observed["ane_executed_operations"], 2.0)

    def test_ane_runtime_log_evidence_requires_matching_arm_session_and_context(self):
        """Structured logs from another session cannot certify a measured O request."""
        source = "\n".join(
            [
                json.dumps(
                    {
                        "event": "ane_prefill",
                        "arm": "O",
                        "session_id": "measured-o",
                        "context_target": 16384,
                        "ane_compiled_mlp_layers": 2,
                        "ane_compiled_gdn_layers": 1,
                        "ane_executed_operations": 4,
                    }
                ),
                json.dumps(
                    {
                        "event": "ane_prefill",
                        "arm": "O",
                        "session_id": "warmup-o",
                        "context_target": 16384,
                        "ane_compiled_mlp_layers": 99,
                        "ane_executed_operations": 99,
                    }
                ),
            ]
        )

        evidence = parse_ane_runtime_evidence(source, "O", "measured-o", 16384)

        self.assertEqual(evidence["ane_runtime_log_compiled_programs"], 3)
        self.assertEqual(evidence["ane_runtime_log_executed_operations"], 4)
        self.assertEqual(evidence["ane_runtime_log_arm"], "O")
    def test_prometheus_parser_reads_labels_and_ignores_comments(self):
        source = (
            '# HELP prefix_cache_hits_total Cache hits\n'
            'prefix_cache_hits_total{model="qwen"} 3\n'
            "prefix_cache_tokens_total 8192\n"
        )

        parsed = parse_prometheus(source)

        self.assertEqual(parsed['prefix_cache_hits_total{model="qwen"}'], 3.0)
        self.assertEqual(parsed["prefix_cache_tokens_total"], 8192.0)

    def test_metric_delta_uses_zero_for_keys_missing_from_one_snapshot(self):
        before = {"hits": 4.0, "removed": 10.0}
        after = {"hits": 5.0, "tokens": 250.0}

        delta = metric_delta(before, after)

        self.assertEqual(
            delta,
            {"hits": 1.0, "removed": -10.0, "tokens": 250.0},
        )

    def test_macmon_parser_normalizes_memory_gpu_power_and_temperature(self):
        sample = json.dumps(
            {
                "memory": {"ram_usage": 64_000_000_000, "swap_usage": 500_000_000},
                "gpu_usage": ["GPU", 0.75],
                "all_power": 42.5,
                "temp": {"cpu_temp_avg": 44.0, "gpu_temp_avg": 48.25},
            }
        )

        parsed = parse_macmon(sample)

        self.assertEqual(parsed["ram_gb"], 64.0)
        self.assertEqual(parsed["swap_gb"], 0.5)
        self.assertEqual(parsed["gpu_pct"], 75.0)
        self.assertEqual(parsed["power_w"], 42.5)
        self.assertEqual(parsed["gpu_temp_c"], 48.25)


if __name__ == "__main__":
    unittest.main()
