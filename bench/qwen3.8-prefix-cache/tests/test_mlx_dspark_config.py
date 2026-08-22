import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mlx_dspark_config import build_command, load_arm, validate_arm


CONFIG = Path(__file__).resolve().parents[1] / "config" / "mlx-dspark-arms.json"
TARGET_REVISION = "815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
DSPARK_REVISION = "85ef153be924f17ce4bf62726954eeaa4a73e854"
DFLASH_REVISION = "dedf8df68adfb1afeaf7b7480c0a0243108177b4"


class MlxDsparkConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.paths = {
            "target": root / f"mlx-community--Qwen3.8-27B-8bit-{TARGET_REVISION}",
            "dspark": root / f"RadixArk--Qwen3.8-27B-DSpark-{DSPARK_REVISION}",
            "dflash": root / f"incoai--Qwen3.8-27B-DFlash2-{DFLASH_REVISION}",
        }
        for path in self.paths.values():
            path.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_p_to_s_profiles_and_pinned_target(self):
        profiles = {arm: load_arm(CONFIG, arm) for arm in "PQRS"}

        self.assertEqual(profiles["P"]["mode"], "baseline")
        self.assertFalse(profiles["P"]["prefix_cache"])
        self.assertIsNone(profiles["P"]["drafter"])
        self.assertEqual(profiles["Q"]["mode"], "baseline")
        self.assertTrue(profiles["Q"]["prefix_cache"])
        self.assertEqual(profiles["R"]["mode"], "dspark")
        self.assertEqual(profiles["R"]["drafter"]["id"], "RadixArk/Qwen3.8-27B-DSpark")
        self.assertEqual(profiles["S"]["mode"], "dflash")
        self.assertEqual(profiles["S"]["drafter"]["id"], "incoai/Qwen3.8-27B-DFlash2")
        for profile in profiles.values():
            self.assertEqual(profile["target"]["id"], "mlx-community/Qwen3.8-27B-8bit")
            self.assertEqual(profile["target"]["revision"], TARGET_REVISION)
        self.assertEqual(profiles["R"]["max_draft"], "auto")
        self.assertEqual(profiles["S"]["max_draft"], "auto")

    def test_build_command_is_pinned_cache_safe_and_has_no_kv_bits(self):
        for arm in "PQRS":
            profile = load_arm(CONFIG, arm)
            validate_arm(profile, self.paths)
            command = build_command(profile, self.paths)
            self.assertEqual(command[:2], ["mlx-dspark", "serve"])
            self.assertIn("--host", command)
            self.assertEqual(command[command.index("--host") + 1], "0.0.0.0")
            self.assertEqual(command[command.index("--port") + 1], "8484")
            self.assertEqual(command[command.index("--context-window") + 1], "65536")
            self.assertEqual(command[command.index("--reasoning-effort") + 1], "xhigh")
            self.assertNotIn("--kv-bits", command)
            self.assertEqual(command[command.index("--max-batch") + 1], "1")
            self.assertFalse(any(value.isdigit() for value in command if value not in {"1", "8484", "65536"}))
        self.assertIn("--no-prefix-cache", build_command(load_arm(CONFIG, "P"), self.paths))
        self.assertNotIn("--no-prefix-cache", build_command(load_arm(CONFIG, "Q"), self.paths))
        for arm, key in (("R", "dspark"), ("S", "dflash")):
            command = build_command(load_arm(CONFIG, arm), self.paths)
            self.assertEqual(command[command.index("--mode") + 1], key)
            self.assertEqual(command[command.index("--max-draft") + 1], "auto")
            self.assertEqual(command[command.index("--drafter") + 1], str(self.paths[key]))

    def test_build_command_accepts_native_262k_context_override(self):
        profile = load_arm(CONFIG, "S")

        command = build_command(profile, self.paths, context_window=262144)

        self.assertEqual(command[command.index("--context-window") + 1], "262144")

    def test_build_command_rejects_context_outside_target_native_window(self):
        profile = load_arm(CONFIG, "S")

        for context_window in (0, -1, 262145):
            with self.subTest(context_window=context_window):
                with self.assertRaises(ValueError):
                    build_command(profile, self.paths, context_window=context_window)

    def test_rejects_unknown_arm_and_wrong_snapshot_directory(self):
        with self.assertRaises(ValueError):
            load_arm(CONFIG, "Z")
        profile = load_arm(CONFIG, "R")
        wrong = dict(self.paths)
        wrong["dspark"] = self.paths["dspark"].parent / "wrong-draft-directory"
        wrong["dspark"].mkdir()
        with self.assertRaises(ValueError):
            validate_arm(profile, wrong)


if __name__ == "__main__":
    unittest.main()
