import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from enrich_telemetry import enrich_records, summarize_telemetry


class EnrichTelemetryTests(unittest.TestCase):
    def test_summary_uses_first_sample_and_session_peaks(self):
        samples = [
            {
                "ram_gb": 40.0,
                "swap_gb": 0.25,
                "gpu_pct": 10.0,
                "power_w": 20.0,
                "gpu_temp_c": 44.0,
            },
            {
                "ram_gb": 61.5,
                "swap_gb": 0.50,
                "gpu_pct": 92.0,
                "power_w": 78.0,
                "gpu_temp_c": 53.0,
            },
            {
                "ram_gb": 58.0,
                "swap_gb": 0.40,
                "gpu_pct": 70.0,
                "power_w": 60.0,
                "gpu_temp_c": 51.0,
            },
        ]

        summary = summarize_telemetry(samples)

        self.assertEqual(summary["ram_peak_gb"], 61.5)
        self.assertEqual(summary["swap_delta_gb"], 0.25)
        self.assertEqual(summary["gpu_temp_start_c"], 44.0)
        self.assertEqual(summary["gpu_temp_peak_c"], 53.0)
        self.assertEqual(summary["gpu_util_peak_pct"], 92.0)
        self.assertEqual(summary["power_peak_w"], 78.0)

    def test_enrichment_only_changes_matching_session_records(self):
        records = [
            {"session_id": "wanted", "ram_peak_gb": None},
            {"session_id": "other", "ram_peak_gb": None},
        ]
        summary = {
            "ram_peak_gb": 60.0,
            "swap_delta_gb": 0.0,
            "gpu_temp_start_c": 42.0,
            "gpu_temp_peak_c": 49.0,
            "gpu_util_peak_pct": 90.0,
            "power_peak_w": 70.0,
            "telemetry_samples": 3,
        }

        changed = enrich_records(records, "wanted", summary)

        self.assertEqual(changed, 1)
        self.assertEqual(records[0]["ram_peak_gb"], 60.0)
        self.assertIsNone(records[1]["ram_peak_gb"])


if __name__ == "__main__":
    unittest.main()
