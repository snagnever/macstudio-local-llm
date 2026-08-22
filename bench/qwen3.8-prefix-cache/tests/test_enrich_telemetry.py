import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from enrich_telemetry import enrich_records, summarize_telemetry
from metrics import parse_ane_runtime_evidence


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

    def test_enrichment_binds_a_production_ane_log_to_the_known_run_scope(self):
        records = [
            {"session_id": "wanted", "arm": "O", "context_target": 16384},
            {"session_id": "other", "arm": "O", "context_target": 16384},
        ]
        evidence = parse_ane_runtime_evidence(
            "Eagerly compiled 64 MLP and 0 GDN procedures into 2 instance-pinned ANE programs (sequence_length=8192)\n"
            "[benchmark-ane-profile] category=mlp operations=126 configured_layers=64",
            "O", "wanted", 16384,
        )

        enrich_records(records, "wanted", {"ram_peak_gb": 60.0}, evidence, "O", 16384)

        self.assertEqual(records[0]["ane_runtime_log_compiled_programs"], 2)
        self.assertEqual(records[0]["ane_runtime_log_executed_operations"], 126)
        self.assertNotIn("ane_runtime_log_compiled_programs", records[1])

    def test_enrichment_does_not_stamp_positive_ane_evidence_from_ambiguous_log(self):
        """A scoped record keeps unavailable evidence when the log is ambiguous."""
        records = [{"session_id": "wanted", "arm": "O", "context_target": 16384}]
        evidence = parse_ane_runtime_evidence(
            "Eagerly compiled 64 MLP and 0 GDN procedures into 2 instance-pinned ANE programs (sequence_length=8192)\n"
            "[benchmark-ane-profile] category=mlp operations=126 configured_layers=64\n"
            "[benchmark-ane-profile] category=mlp operations=127 configured_layers=64",
            "O", "wanted", 16384,
        )

        enrich_records(records, "wanted", {"ram_peak_gb": 60.0}, evidence, "O", 16384)

        self.assertIsNone(records[0]["ane_runtime_log_compiled_programs"])
        self.assertIsNone(records[0]["ane_runtime_log_executed_operations"])


if __name__ == "__main__":
    unittest.main()
