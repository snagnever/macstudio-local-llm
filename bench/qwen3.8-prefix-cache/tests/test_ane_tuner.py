import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ane_tuner import profile_from_snapshot


class AneTunerTests(unittest.TestCase):
    def test_translates_completed_hardware_recommendation_to_omlx_profile(self):
        snapshot = {
            "status": "completed",
            "recommendation": {
                "enabled": True,
                "mlp_fraction": 0.53,
                "gdn_enabled": True,
                "gdn_fraction": 0.45,
                "cpu_enabled": True,
                "cpu_fraction": 0.10,
                "cpu_down_fraction": 0.20,
                "cpu_gdn_fraction": 0.05,
                "cpu_threads": 8,
                "cpu_shared_resource": True,
                "processing_tps": 123.4,
                "speedup_percent": 8.5,
                "sequence_length": 2048,
            },
        }

        profile = profile_from_snapshot(snapshot)

        self.assertEqual(
            profile,
            {
                "qwen35_ane_prefill_enabled": True,
                "qwen35_ane_prefill_sequence_length": 2048,
                "qwen35_ane_prefill_fraction": 0.53,
                "qwen35_ane_prefill_gdn": True,
                "qwen35_ane_prefill_gdn_fraction": 0.45,
                "qwen35_ane_prefill_cpu_enabled": True,
                "qwen35_ane_prefill_cpu_fraction": 0.10,
                "qwen35_ane_prefill_cpu_down_fraction": 0.20,
                "qwen35_ane_prefill_cpu_gdn_fraction": 0.05,
                "qwen35_ane_prefill_cpu_threads": 8,
                "qwen35_ane_prefill_cpu_shared_resource": True,
            },
        )

    def test_rejects_gpu_only_or_incomplete_recommendation(self):
        with self.assertRaisesRegex(ValueError, "GPU-only"):
            profile_from_snapshot(
                {
                    "status": "completed",
                    "recommendation": {
                        "enabled": False,
                        "sequence_length": 2048,
                    },
                }
            )
        with self.assertRaisesRegex(ValueError, "not completed"):
            profile_from_snapshot({"status": "running", "recommendation": None})


if __name__ == "__main__":
    unittest.main()
