import json
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from metrics import metric_delta, parse_macmon, parse_prometheus


class MetricsTests(unittest.TestCase):
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
                "gpu_temp": 48.25,
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
