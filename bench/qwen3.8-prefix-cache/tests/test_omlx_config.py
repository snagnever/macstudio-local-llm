import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
CONFIG = Path(__file__).resolve().parents[1] / "config" / "omlx-arms.json"
sys.path.insert(0, str(SCRIPTS))

from omlx_config import load_arm, validate_arm, write_omlx_state


class OmlxConfigTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.model_root = self.root / "models"
        self.model_root.mkdir()
        self.target_dirs = {
            "I": self.model_root
            / "ddalcu-Qwen3.8-27B-MLX-Serve-8bit-011e38296b3d2aa99245ed49a700459c4ac246b6",
            "J": self.model_root
            / "True2456-Qwen3.8-27B-AWQ-5.0bpw-dc699a76ddcbef44c188a8aee2ccc79ccc339a04",
            "T": self.model_root
            / "Jundot-Qwen3.8-27B-oQ8e-mtp-c99e5aad8a478f71c10b9a3dde6709158b690da6",
            "U": self.model_root
            / "Jundot-Qwen3.8-27B-oQ8e-fp16-mtp-4761782b9455f335292f4d6cb0c89570dff27a11",
        }
        for target_dir in self.target_dirs.values():
            target_dir.mkdir()
        self.draft_2b = self.root / "draft-2b"
        self.draft_08b = self.root / "draft-08b"
        self.draft_2b.mkdir()
        self.draft_08b.mkdir()
        self.ane_profile = self.root / "ane-profile.json"
        self.ane_profile.write_text(
            json.dumps({"qwen35_ane_prefill_sequence_length": 8192}) + "\n",
            encoding="utf-8",
        )
        self.model_paths = {
            "model_root": self.model_root,
            "draft-2b": self.draft_2b,
            "draft-08b": self.draft_08b,
            "ane_profile": self.ane_profile,
        }

    def tearDown(self):
        self.tempdir.cleanup()

    def test_arm_profiles_map_runtime_features(self):
        expected = {
            "I": ("mlx8", False, False, False, False, None, None),
            "J": ("awq5", False, False, False, False, None, None),
            "K": ("awq5", True, False, False, False, None, None),
            "L": ("awq5", True, True, False, False, None, None),
            "M": ("awq5", True, True, True, False, "draft-2b", 0.40),
            "N": ("awq5", True, True, True, False, "draft-08b", 0.50),
            "O": ("awq5", False, False, False, True, None, None),
            "T": ("oq8e", True, True, False, False, None, None),
            "U": ("oq8e-fp16", True, True, False, False, None, None),
        }
        for arm, wanted in expected.items():
            with self.subTest(arm=arm):
                profile = load_arm(CONFIG, arm)
                settings = profile["model_settings"]
                self.assertEqual(profile["model"]["key"], wanted[0])
                self.assertEqual(profile["cache_enabled"], wanted[1])
                self.assertEqual(settings["mtp_enabled"], wanted[2])
                self.assertEqual(settings["specprefill_enabled"], wanted[3])
                self.assertEqual(settings["qwen35_ane_prefill_enabled"], wanted[4])
                self.assertEqual(profile.get("draft_key"), wanted[5])
                self.assertEqual(settings.get("specprefill_keep_pct"), wanted[6])
                if arm in {"M", "N"}:
                    self.assertEqual(settings["specprefill_threshold"], 8192)

    def test_write_state_uses_versioned_envelopes_and_one_model_entry(self):
        for arm in (*"IJKLMNO", "T", "U"):
            with self.subTest(arm=arm):
                profile = load_arm(CONFIG, arm)
                base_path = self.root / arm
                validate_arm(profile, self.model_paths)
                write_omlx_state(base_path, profile, self.model_paths)

                global_state = json.loads((base_path / "settings.json").read_text())
                model_state = json.loads(
                    (base_path / "model_settings.json").read_text()
                )
                self.assertEqual(global_state["version"], "1.0")
                self.assertEqual(global_state["server"]["port"], 8000)
                self.assertEqual(
                    global_state["model"]["model_dirs"],
                    [str(self.model_paths["model_root"])],
                )
                self.assertEqual(global_state["cache"]["enabled"], profile["cache_enabled"])
                self.assertEqual(model_state["version"], 1)
                self.assertEqual(len(model_state["models"]), 1)
                expected_dir = self.target_dirs.get(arm, self.target_dirs["J"])
                self.assertEqual(set(model_state["models"]), {expected_dir.name})

    def test_unknown_arm_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown arm"):
            load_arm(CONFIG, "Z")

    def test_specprefill_arms_require_their_local_draft(self):
        for arm, key in (("M", "draft-2b"), ("N", "draft-08b")):
            with self.subTest(arm=arm):
                paths = dict(self.model_paths)
                paths.pop(key)
                with self.assertRaisesRegex(ValueError, key):
                    validate_arm(load_arm(CONFIG, arm), paths)

    def test_ane_arm_requires_a_recorded_tuner_profile(self):
        paths = dict(self.model_paths)
        paths.pop("ane_profile")
        with self.assertRaisesRegex(ValueError, "tuner profile"):
            validate_arm(load_arm(CONFIG, "O"), paths)

    def test_ane_arm_only_enables_ane_prefill_technique(self):
        profile = load_arm(CONFIG, "O")
        settings = profile["model_settings"]
        self.assertTrue(settings["qwen35_ane_prefill_enabled"])
        self.assertFalse(settings["specprefill_enabled"])
        self.assertFalse(settings["mtp_enabled"])
        self.assertNotIn("specprefill_draft_model", settings)

    def test_ane_arm_keeps_ane_enabled_when_tuner_profile_has_a_stale_toggle(self):
        self.ane_profile.write_text(
            json.dumps({"qwen35_ane_prefill_enabled": False}) + "\n",
            encoding="utf-8",
        )
        base_path = self.root / "ane"
        write_omlx_state(base_path, load_arm(CONFIG, "O"), self.model_paths)
        model_state = json.loads((base_path / "model_settings.json").read_text())
        settings = next(iter(model_state["models"].values()))
        self.assertTrue(settings["qwen35_ane_prefill_enabled"])

    def test_state_rejects_a_missing_expected_target_directory_before_writing(self):
        missing_root = self.root / "missing-target-root"
        missing_root.mkdir()
        paths = dict(self.model_paths, model_root=missing_root)
        base_path = self.root / "state"
        with self.assertRaisesRegex(ValueError, "target model directory"):
            write_omlx_state(base_path, load_arm(CONFIG, "J"), paths)
        self.assertFalse(base_path.exists())

    def test_ane_tuner_profile_rejects_unknown_keys_and_invalid_values(self):
        invalid_profiles = (
            {"qwen35_ane_prefill_typo": True},
            {"qwen35_ane_prefill_sequence_length": 1025},
            {"qwen35_ane_prefill_fraction": "0.53"},
            {"qwen35_ane_prefill_cpu_threads": True},
        )
        for data in invalid_profiles:
            with self.subTest(data=data):
                self.ane_profile.write_text(json.dumps(data) + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    validate_arm(load_arm(CONFIG, "O"), self.model_paths)


if __name__ == "__main__":
    unittest.main()
