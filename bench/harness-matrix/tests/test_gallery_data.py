"""Tests for the gallery data generator (stdlib unittest)."""
import json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "svgbench"))
import gallery_data as gd  # noqa: E402

SCORES = {
    "artifacts": [
        {"harness": "opencode", "model": "qwen3.8-flash-next", "artifact": "logs/opencode/qwen3.8-flash-next/dolphin-hula-hoop-fish-v2.svg",
         "question_index": 7, "animated": False, "slug": "dolphin-hula-hoop-fish-v2", "score": 1.0, "met": 7, "total": 7,
         "requirements": [{"text": "grey dolphin", "met": True, "note": ""}]},
        {"harness": "claude", "model": "claude-opus-5", "artifact": "logs/claude/claude-opus-5/dolphin-animated.svg",
         "question_index": 7, "animated": True, "slug": "dolphin-animated", "score": 0.5, "met": 1, "total": 2,
         "requirements": [{"text": "grey dolphin", "met": True, "note": ""}, {"text": "splash", "met": False, "note": "no splash"}]},
        {"harness": "opencode", "model": "qwen3.8-27b-8bit", "artifact": "logs/opencode/qwen3.8-27b-8bit/dolphin.svg",
         "question_index": 7, "animated": False, "slug": "dolphin", "score": 0.5, "met": 1, "total": 2,
         "requirements": [{"text": "grey dolphin", "met": True, "note": ""}, {"text": "splash", "met": False, "note": "x"}]},
    ],
    "unscored": [
        {"harness": "opencode", "model": "gpt-5.6-terra", "artifact": "logs/opencode/gpt-5.6-terra/dawn-beach-v3.svg",
         "question_index": None, "animated": True, "slug": "dawn-beach-v3", "reason": "prompt is not an SVGBench question"},
    ],
}


class TestBuildItems(unittest.TestCase):
    def setUp(self):
        self.items = gd.build_items(SCORES)

    def test_take_and_base_from_slug(self):
        by = {i["slug"]: i for i in self.items}
        self.assertEqual((by["dolphin-hula-hoop-fish-v2"]["take"], by["dolphin-hula-hoop-fish-v2"]["base"]), ("v2", "dolphin-hula-hoop-fish"))
        self.assertEqual((by["dolphin-animated"]["take"], by["dolphin-animated"]["base"]), ("animated", "dolphin"))
        self.assertEqual((by["dolphin"]["take"], by["dolphin"]["base"]), ("v1", "dolphin"))
        self.assertEqual((by["dawn-beach-v3"]["take"], by["dawn-beach-v3"]["base"]), ("v3", "dawn-beach"))

    def test_arm_and_prompt_label(self):
        by = {i["slug"]: i for i in self.items}
        self.assertEqual(by["dolphin-animated"]["arm"], "control")
        self.assertEqual(by["dolphin"]["arm"], "local")
        self.assertEqual(by["dolphin"]["prompt"], "Dolphin")
        self.assertEqual(by["dawn-beach-v3"]["prompt"], "Dawn on the beach")

    def test_unscored_item_has_no_score_and_a_reason(self):
        u = [i for i in self.items if i["q"] is None][0]
        self.assertIsNone(u["score"]); self.assertIsNone(u["verdict"]); self.assertEqual(u["reqs"], [])
        self.assertEqual(u["reason"], "prompt is not an SVGBench question")

    def test_scored_item_carries_reqs_and_verdict_path(self):
        s = [i for i in self.items if i["slug"] == "dolphin-animated"][0]
        self.assertEqual(s["reqs"][1], {"t": "splash", "m": False, "n": "no splash"})
        self.assertEqual(s["verdict"], "results/svgbench/verdicts/claude/claude-opus-5/dolphin-animated.json")

    def test_order_is_stable(self):
        keys = [(i["harness"], i["model"], i["q"] if i["q"] is not None else 999, i["base"], gd.TAKE_RANK[i["take"]]) for i in self.items]
        self.assertEqual(keys, sorted(keys))


class TestWriteBlock(unittest.TestCase):
    def test_replaces_between_markers_only(self):
        html = "<script>\nvar DATA = {};\n/* GALLERY:begin */\nvar GALLERY = [];\n/* GALLERY:end */\nvar L = 1;\n</script>"
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(html); path = f.name
        gd.write_block(path, [{"slug": "a"}])
        out = open(path).read()
        self.assertIn('var GALLERY = [{"slug": "a"}];', out)
        self.assertIn("var DATA = {};", out); self.assertIn("var L = 1;", out)
        self.assertEqual(out.count("GALLERY:begin"), 1)

    def test_missing_markers_raises(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write("<script>var DATA = {};</script>"); path = f.name
        with self.assertRaises(gd.MarkerError):
            gd.write_block(path, [])


if __name__ == "__main__":
    unittest.main()
