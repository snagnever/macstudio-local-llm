"""Tests for the SVGBench evaluation driver (stdlib unittest, no network)."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "svgbench"))
import svgbench_eval as se  # noqa: E402

QUESTIONS = [
    {"prompt": "Write `svg` code to draw an image of a cow plowing a field.",
     "requirements": ["a", "b", "c"]},
    {"prompt": "Write `svg` code for an image of a rubber ducky floating on top of a soapy bathtub.",
     "requirements": ["a", "b"]},
    {"prompt": "Write `svg` code for an image of a dolphin jumping out of the water and through a hula hoop.",
     "requirements": ["a", "b", "c", "d"]},
    {"prompt": "Write `svg` code for an image of a child building a sandcastle at the beach.",
     "requirements": ["a"]},
]


class MatchQuestion(unittest.TestCase):
    def test_slug_tokens_all_found_in_one_prompt(self):
        self.assertEqual(se.match_question("cow-plowing", QUESTIONS), 0)
        self.assertEqual(se.match_question("rubber-ducky", QUESTIONS), 1)

    def test_variant_suffixes_are_ignored(self):
        self.assertEqual(se.match_question("cow-plowing-animated", QUESTIONS), 0)
        self.assertEqual(se.match_question("rubber-ducky-v2", QUESTIONS), 1)

    def test_prefix_match_on_prompt_words(self):
        self.assertEqual(se.match_question("dolphin-hoop-jump", QUESTIONS), 2)

    def test_partial_match_is_not_a_match(self):
        # "beach" is in a prompt, "dawn" is not: off-benchmark prompt.
        self.assertIsNone(se.match_question("dawn-beach", QUESTIONS))


class Discover(unittest.TestCase):
    def test_attributed_svgs_and_strays(self):
        with tempfile.TemporaryDirectory() as d:
            logs = os.path.join(d, "logs")
            os.makedirs(os.path.join(logs, "opencode", "modelA"))
            os.makedirs(os.path.join(logs, "claude", "modelB", "nested"))
            for p in ["opencode/modelA/cow-plowing.svg", "claude/modelB/nested/dolphin.svg",
                      "opencode/stray.svg", "opencode/modelA/trace.log"]:
                with open(os.path.join(logs, p), "w") as f:
                    f.write("<svg/>")
            found, strays = se.discover(d)
        self.assertEqual(
            found,
            [("claude", "modelB", "logs/claude/modelB/nested/dolphin.svg"),
             ("opencode", "modelA", "logs/opencode/modelA/cow-plowing.svg")])
        self.assertEqual(strays, ["logs/opencode/stray.svg"])


class SvgDimensions(unittest.TestCase):
    def test_width_height_attributes(self):
        self.assertEqual(se.svg_dimensions('<svg width="800" height="500" viewBox="0 0 1 1"/>'), (800, 500))

    def test_viewbox_when_width_is_percent(self):
        self.assertEqual(se.svg_dimensions('<svg width="100%" viewBox="0 0 1200 700"/>'), (1200, 700))

    def test_default_when_nothing_usable(self):
        self.assertEqual(se.svg_dimensions("<svg/>"), (800, 600))


class Scoring(unittest.TestCase):
    def verdict(self, met):
        return {"artifact": "logs/opencode/modelA/dolphin.svg", "question_index": 2,
                "judge": {"kind": "test"},
                "requirements": [{"text": t, "met": m} for t, m in zip("abcd", met)]}

    def test_score_is_fraction_of_requirements_met(self):
        self.assertEqual(se.score_verdict(self.verdict([True, True, False, False])), 0.5)

    def test_stale_verdict_requirements_are_rejected(self):
        v = self.verdict([True] * 4)
        v["requirements"][0]["text"] = "changed"
        with self.assertRaises(se.StaleVerdict):
            se.check_verdict(v, QUESTIONS)

    def test_build_scores_aggregates_per_pair(self):
        manifest = {"artifacts": [
            {"harness": "opencode", "model": "modelA", "artifact": "logs/opencode/modelA/dolphin.svg",
             "question_index": 2, "animated": False},
            {"harness": "opencode", "model": "modelA", "artifact": "logs/opencode/modelA/cow.svg",
             "question_index": 0, "animated": False},
            {"harness": "opencode", "model": "modelA", "artifact": "logs/opencode/modelA/dawn.svg",
             "question_index": None, "animated": True},
        ], "strays": ["logs/opencode/stray.svg"]}
        cow = {"artifact": "logs/opencode/modelA/cow.svg", "question_index": 0, "judge": {"kind": "test"},
               "requirements": [{"text": t, "met": m} for t, m in zip("abc", [True, False, False])]}
        out = se.build_scores(manifest, {"logs/opencode/modelA/dolphin.svg": self.verdict([True] * 4),
                                         "logs/opencode/modelA/cow.svg": cow}, QUESTIONS)
        pair = out["pairs"][0]
        self.assertEqual((pair["harness"], pair["model"]), ("opencode", "modelA"))
        self.assertEqual(pair["artifacts_scored"], 2)
        self.assertAlmostEqual(pair["mean_score"], (1.0 + 1 / 3) / 2)
        self.assertEqual(pair["by_question"], {"0": 1 / 3, "2": 1.0})
        self.assertEqual([a["artifact"] for a in out["unscored"]], ["logs/opencode/modelA/dawn.svg"])
        self.assertEqual(out["skipped"][0]["path"], "logs/opencode/stray.svg")

    def test_build_scores_reports_missing_verdict_as_unscored(self):
        manifest = {"artifacts": [{"harness": "h", "model": "m", "artifact": "logs/h/m/x.svg",
                                   "question_index": 0, "animated": False}], "strays": []}
        out = se.build_scores(manifest, {}, QUESTIONS)
        self.assertEqual(out["unscored"][0]["reason"], "no verdict file")
        self.assertEqual(out["pairs"], [])


if __name__ == "__main__":
    unittest.main()
