import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from enrich_telemetry import (
    enrich_records,
    enrich_request_evidence,
    summarize_telemetry,
)
from metrics import parse_ane_runtime_evidence, parse_omlx_mtp_request_evidence


class EnrichTelemetryTests(unittest.TestCase):
    def test_omlx_mtp_parser_ignores_warmup_and_control_requests(self):
        runtime_log = "\n".join(
            [
                "MTP[0] finish=length tokens=64 cycles=26 tok/cycle=2.46 accept=38/51 (74.5%) depth[d1=20/23]",
                "Chat completion: model=x, 64 tokens in 4.56s (41.9 tok/s), prompt: 578, finish_reason=length, max_tokens=64, request_max_tokens=64",
                "MTP[1] finish=stop tokens=289 cycles=112 tok/cycle=2.58 accept=176/213 (82.6%) depth[d1=99/109]",
                "Chat completion: model=x, 288 tokens in 135.65s (42.0 tok/s), prompt: 29289, finish_reason=stop, max_tokens=2048, request_max_tokens=2048",
                "MTP[2] finish=length tokens=2 cycles=1 tok/cycle=2.00 accept=1/1 (100.0%) depth[d1=1/1]",
                "Chat completion: model=x, 1 tokens in 3.28s (2540.8 tok/s), prompt: 29289, finish_reason=length, max_tokens=1, request_max_tokens=1",
                "MTP[3] finish=stop tokens=100 cycles=40 tok/cycle=2.50 accept=61/75 (81.3%) depth[d1=40/40]",
                "Chat completion: model=x, 99 tokens in 6.00s (40.0 tok/s), prompt: 29289, finish_reason=stop, max_tokens=2048, request_max_tokens=2048",
            ]
        )

        evidence = parse_omlx_mtp_request_evidence(runtime_log)

        self.assertEqual(len(evidence), 2)
        self.assertEqual(evidence[0]["accepted_tokens"], 176)
        self.assertEqual(evidence[0]["drafted_tokens"], 213)
        self.assertAlmostEqual(evidence[0]["mtp_acceptance"], 176 / 213)
        self.assertEqual(evidence[0]["verification_steps"], 112)
        self.assertEqual(evidence[0]["accept_length"], 2.58)
        self.assertEqual(evidence[1]["accepted_tokens"], 61)

    def test_request_evidence_binds_in_order_without_overwriting_server_values(self):
        records = [
            {
                "session_id": "wanted",
                "arm": "L",
                "context_target": 32768,
                "accepted_tokens": None,
            },
            {
                "session_id": "wanted",
                "arm": "L",
                "context_target": 32768,
                "accepted_tokens": 99,
            },
            {"session_id": "other", "arm": "L", "context_target": 32768},
        ]
        evidence = [
            {"accepted_tokens": 10, "mtp_acceptance": 0.5},
            {"accepted_tokens": 20, "mtp_acceptance": 0.75},
        ]

        changed = enrich_request_evidence(
            records, "wanted", evidence, "L", 32768
        )

        self.assertEqual(changed, 2)
        self.assertEqual(records[0]["accepted_tokens"], 10)
        self.assertEqual(records[0]["mtp_acceptance"], 0.5)
        self.assertEqual(records[1]["accepted_tokens"], 99)
        self.assertEqual(records[1]["mtp_acceptance"], 0.75)
        self.assertNotIn("mtp_acceptance", records[2])

    def test_request_evidence_rejects_ambiguous_cardinality(self):
        records = [
            {"session_id": "wanted", "arm": "L", "context_target": 32768},
            {"session_id": "wanted", "arm": "L", "context_target": 32768},
        ]

        with self.assertRaisesRegex(ValueError, "request evidence count"):
            enrich_request_evidence(
                records,
                "wanted",
                [{"mtp_acceptance": 0.5}],
                "L",
                32768,
            )

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
