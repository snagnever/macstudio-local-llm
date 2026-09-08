"""Tests for the artifact-gallery data generator (stdlib unittest).

pytest is not installed on this rig's python3, and the sibling suite
(bench/harness-matrix/tests/) is stdlib unittest too, so this follows it:

    python3 tools/tests/test_artifacts_data.py
"""
import json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import artifacts_data as ad  # noqa: E402


JUDGE = "claude-opus-5"


def _art(harness, model, slug, q, score, met, total, animated=False, judge=JUDGE):
    return {
        "harness": harness, "model": model,
        "artifact": "logs/%s/%s/%s.svg" % (harness, model, slug),
        "question_index": q, "animated": animated, "slug": slug,
        "judge": {"kind": "claude-vision", "model": judge, "date": "2026-09-07"},
        "prompt": "Write `svg` code to draw an image of a cow plowing a field.",
        "score": score, "met": met, "total": total,
        "requirements": [{"text": "a cow", "met": True, "note": ""},
                         {"text": "a plough", "met": bool(met > 1), "note": "no plough"}],
    }


SCORES = {
    "generated_at": "2026-09-07T18:44:20",
    "questions": [
        {"question_index": 0, "prompt": "Write `svg` code to draw an image of a cow plowing a field.",
         "n_requirements": 2, "requirements": ["a cow", "a plough"]},
        {"question_index": 7, "prompt": "Write `svg` code for an image of a dolphin.",
         "n_requirements": 2, "requirements": ["a dolphin", "a hoop"]},
    ],
    "artifacts": [
        # qwen on q0: v2 and v3 tie at 0.5 -> v2 wins (lower TAKE_RANK); v1 is worse.
        _art("opencode", "qwen3.8-flash-next", "cow-plowing-v1", 0, 0.0, 0, 2),
        _art("opencode", "qwen3.8-flash-next", "cow-plowing-v3", 0, 0.5, 1, 2),
        _art("opencode", "qwen3.8-flash-next", "cow-plowing-v2", 0, 0.5, 1, 2),
        # claude on q0: single take.
        _art("claude", "claude-opus-5", "cow-plowing", 0, 1.0, 2, 2),
        # terra on q7 only.
        _art("opencode", "gpt-5.6-terra", "dolphin-animated", 7, 0.5, 1, 2, animated=True),
    ],
    "unscored": [
        {"harness": "opencode", "model": "gpt-5.6-terra",
         "artifact": "logs/opencode/gpt-5.6-terra/dawn-beach-animated.svg",
         "question_index": None, "animated": True, "slug": "dawn-beach-animated",
         "reason": "prompt is not an SVGBench question"},
    ],
}

GAME = {
    "arms": [
        {"id": "opencode-qwen38", "harness": "opencode", "model": "qwen3.8-flash-next",
         "hosted": False, "label": "opencode + Qwen3.8 Flash Next (local)", "color": "#2a9d8f"},
        {"id": "codex-astra", "harness": "codex", "model": "gpt-6-astra",
         "hosted": True, "label": "Codex + gpt-6-astra (multi-model)", "color": "#f4a261"},
    ],
    "results": [
        {"arm": "opencode-qwen38", "metric": "wallMinutes", "value": 90, "note": "first files written"},
        {"arm": "opencode-qwen38", "metric": "tokensOutput", "value": 112802},
        {"arm": "opencode-qwen38", "metric": "sourceLines", "value": 1170, "note": "src/ TypeScript + CSS"},
        {"arm": "opencode-qwen38", "metric": "defectsFound", "value": 8},
        {"arm": "codex-astra", "metric": "wallMinutes", "value": 67},
        {"arm": "codex-astra", "metric": "tokensOutput", "value": 98882},
        {"arm": "codex-astra", "metric": "sourceLines", "value": 1435},
        {"arm": "codex-astra", "metric": "defectsFound", "value": None,
         "note": "this arm's STATS.md has no “defects found” section"},
    ],
}

SKILLS = {
    "arms": [
        {"id": "design-skill", "harness": "opencode", "model": "qwen3.8-flash-next", "hosted": False,
         "label": "opencode + Qwen3.8 Flash Next + frontend-design", "color": "#2a9d8f",
         "skillConfig": "frontend-design", "form": "Five static HTML directories"},
        {"id": "taste-skill", "harness": "opencode", "model": "qwen3.8-flash-next", "hosted": False,
         "label": "opencode + Qwen3.8 Flash Next + design-taste-frontend", "color": "#e76f51",
         "skillConfig": "design-taste-frontend", "form": "Vite + React"},
        {"id": "taste2", "harness": "opencode", "model": "qwen3.8-flash-next", "hosted": False,
         "label": "opencode + Qwen3.8 Flash Next + high-end-visual-design", "color": "#f4a261",
         "skillConfig": "high-end-visual-design", "form": "Five static HTML pages"},
    ],
    "results": [
        {"arm": "design-skill", "metric": "wallMinutes", "value": 12.4},
        {"arm": "design-skill", "metric": "tokensOutput", "value": 37742},
        {"arm": "taste-skill", "metric": "wallMinutes", "value": 24.7},
        {"arm": "taste-skill", "metric": "tokensOutput", "value": None},
        {"arm": "taste2", "metric": "wallMinutes", "value": 38.0},
        {"arm": "taste2", "metric": "tokensOutput", "value": 89922},
    ],
}


class TestSlugHelpers(unittest.TestCase):
    """Behaviour must stay identical to gallery_data.py."""

    def test_split_slug_matches_gallery_data(self):
        self.assertEqual(ad.split_slug("cow-plowing-v2"), ("cow-plowing", "v2"))
        self.assertEqual(ad.split_slug("dolphin-animated"), ("dolphin", "animated"))
        self.assertEqual(ad.split_slug("dolphin"), ("dolphin", "v1"))

    def test_take_rank_order(self):
        self.assertEqual([ad.TAKE_RANK[t] for t in ("v1", "v2", "v3", "animated")], [0, 1, 2, 3])

    def test_prompt_label(self):
        self.assertEqual(ad.PROMPT_LABEL[0], "Cow plowing")
        self.assertEqual(ad.PROMPT_LABEL[7], "Dolphin")


class TestDrawings(unittest.TestCase):
    def setUp(self):
        self.d = ad.build_drawings(SCORES)
        self.q0 = [q for q in self.d["questions"] if q["q"] == 0][0]

    def test_questions_in_question_index_order(self):
        self.assertEqual([q["q"] for q in self.d["questions"]], [0, 7])

    def test_question_carries_label_and_verbatim_prompt(self):
        self.assertEqual(self.q0["label"], "Cow plowing")
        self.assertEqual(self.q0["prompt"], "Write `svg` code to draw an image of a cow plowing a field.")

    def test_unscored_artifacts_are_dropped(self):
        slugs = [t["slug"] for q in self.d["questions"] for t in q["takes"]]
        self.assertNotIn("dawn-beach-animated", slugs)

    def test_best_take_breaks_a_tie_by_take_rank(self):
        best = [t for t in self.q0["takes"]
                if t["pair"] == "opencode/qwen3.8-flash-next" and t["best"]]
        self.assertEqual([t["slug"] for t in best], ["cow-plowing-v2"])

    def test_exactly_one_best_take_per_pair_per_question(self):
        for q in self.d["questions"]:
            seen = {}
            for t in q["takes"]:
                if t["best"]:
                    seen[t["pair"]] = seen.get(t["pair"], 0) + 1
            for pair, n in seen.items():
                self.assertEqual(n, 1, "%s on q%s" % (pair, q["q"]))

    def test_takes_ordered_by_pair_then_take_rank(self):
        keys = [(t["pair"], ad.TAKE_RANK[t["take"]]) for t in self.q0["takes"]]
        self.assertEqual(keys, sorted(keys))

    def test_take_carries_site_relative_file_and_flags(self):
        t = [t for t in self.d["questions"][1]["takes"] if t["slug"] == "dolphin-animated"][0]
        self.assertEqual(t["file"], "../bench/harness-matrix/logs/opencode/gpt-5.6-terra/dolphin-animated.svg")
        self.assertTrue(t["animated"])
        self.assertEqual(t["take"], "animated")
        self.assertEqual((t["met"], t["total"]), (1, 2))

    def test_requirements_use_the_compact_t_m_n_shape(self):
        t = self.q0["takes"][0]
        self.assertEqual(sorted(t["reqs"][0].keys()), ["m", "n", "t"])
        self.assertIs(t["reqs"][0]["m"], True)

    def test_pairs_carry_label_colour_and_hosting(self):
        by = {p["key"]: p for p in self.d["pairs"]}
        self.assertEqual(by["opencode/qwen3.8-flash-next"]["color"], "#2a9d8f")
        self.assertEqual(by["claude/claude-opus-5"]["color"], "#e76f51")
        self.assertEqual(by["opencode/gpt-5.6-terra"]["color"], "#5c6f8a")
        self.assertIs(by["claude/claude-opus-5"]["hosted"], True)
        self.assertIs(by["opencode/qwen3.8-flash-next"]["hosted"], False)

    def test_pair_records_its_question_indexes(self):
        by = {p["key"]: p for p in self.d["pairs"]}
        self.assertEqual(by["opencode/gpt-5.6-terra"]["qs"], [7])
        self.assertEqual(by["opencode/qwen3.8-flash-next"]["n"], 3)


class TestSelfJudged(unittest.TestCase):
    """The judge drew some of what it judged; the page marks those drawings."""

    def setUp(self):
        self.d = ad.build_drawings(SCORES)

    def test_judge_block_names_the_judge_and_counts_its_own_drawings(self):
        self.assertEqual(self.d["judge"], {"model": JUDGE, "selfJudged": 1})

    def test_only_the_judges_own_takes_are_marked(self):
        marked = [t["slug"] for q in self.d["questions"] for t in q["takes"] if t["selfJudged"]]
        self.assertEqual(marked, ["cow-plowing"])

    def test_pair_carries_the_mark_too(self):
        by = {p["key"]: p for p in self.d["pairs"]}
        self.assertIs(by["claude/claude-opus-5"]["selfJudged"], True)
        self.assertIs(by["opencode/qwen3.8-flash-next"]["selfJudged"], False)

    def test_more_than_one_judge_leaves_the_model_blank_but_still_counts(self):
        mixed = json.loads(json.dumps(SCORES))
        mixed["artifacts"][0]["judge"]["model"] = "gpt-5.6-terra"
        d = ad.build_drawings(mixed)
        self.assertEqual(d["judge"]["model"], "")
        self.assertEqual(d["judge"]["selfJudged"], 1)

    def test_an_artifact_with_no_judge_is_not_self_judged(self):
        none = json.loads(json.dumps(SCORES))
        for a in none["artifacts"]:
            a.pop("judge")
        d = ad.build_drawings(none)
        self.assertEqual(d["judge"], {"model": "", "selfJudged": 0})
        self.assertFalse(any(t["selfJudged"] for q in d["questions"] for t in q["takes"]))


class TestMetricText(unittest.TestCase):
    def test_none_renders_as_an_em_dash_never_zero(self):
        self.assertEqual(ad.metric_text(None), "—")
        self.assertEqual(ad.metric_text(None, " min"), "—")

    def test_zero_is_still_zero(self):
        self.assertEqual(ad.metric_text(0), "0")

    def test_thousands_separator_and_units(self):
        self.assertEqual(ad.metric_text(112802), "112,802")
        self.assertEqual(ad.metric_text(90, " min"), "90 min")
        self.assertEqual(ad.metric_text(682.33, " min"), "682.3 min")
        self.assertEqual(ad.metric_text(38.0, " min"), "38 min")


class TestGame(unittest.TestCase):
    def setUp(self):
        self.g = ad.build_game(GAME)

    def test_arm_shot_and_demo_paths(self):
        a = self.g["arms"][0]
        self.assertEqual(a["shot"], "../bench/agent-build-off/results/shots/opencode-qwen38.webp")
        self.assertEqual(a["demo"], "demos/build-off/opencode-qwen38/")

    def test_metric_order_is_the_four_the_design_names(self):
        a = self.g["arms"][0]
        self.assertEqual([m["key"] for m in a["metrics"]],
                         ["wallMinutes", "tokensOutput", "sourceLines", "defectsFound"])

    def test_missing_metric_is_an_em_dash_with_its_note(self):
        astra = [a for a in self.g["arms"] if a["id"] == "codex-astra"][0]
        d = [m for m in astra["metrics"] if m["key"] == "defectsFound"][0]
        self.assertEqual(d["text"], "—")
        self.assertIsNone(d["value"])
        self.assertIn("no “defects found” section", d["note"])

    def test_arm_keeps_identity_and_colour(self):
        a = self.g["arms"][0]
        self.assertEqual(a["color"], "#2a9d8f")
        self.assertIs(a["hosted"], False)
        self.assertEqual(a["label"], "opencode + Qwen3.8 Flash Next (local)")

    def test_brief_is_carried_through(self):
        g = ad.build_game(dict(GAME, brief="build a 3D runner"))
        self.assertEqual(g["brief"], "build a 3D runner")


class TestSkills(unittest.TestCase):
    def setUp(self):
        self.s = ad.build_skills(SKILLS)

    def test_five_shots_per_arm_with_the_per_arm_page_url_rule(self):
        by = {a["id"]: a for a in self.s["arms"]}
        self.assertEqual([s["n"] for s in by["design-skill"]["shots"]], [1, 2, 3, 4, 5])
        self.assertEqual(by["design-skill"]["shots"][0]["src"],
                         "../bench/layout-skill-bench/results/shots/design-skill-1.webp")
        self.assertEqual(by["design-skill"]["shots"][2]["page"], "demos/layout/design-skill/3/")
        self.assertEqual(by["taste-skill"]["shots"][2]["page"], "demos/layout/taste-skill/3")
        self.assertEqual(by["taste2"]["shots"][2]["page"], "demos/layout/taste2/3.html")

    def test_metrics_are_wall_time_and_output_tokens(self):
        a = self.s["arms"][0]
        self.assertEqual([m["key"] for m in a["metrics"]], ["wallMinutes", "tokensOutput"])
        self.assertEqual(a["metrics"][0]["text"], "12.4 min")

    def test_missing_metric_is_an_em_dash(self):
        taste = [a for a in self.s["arms"] if a["id"] == "taste-skill"][0]
        self.assertEqual(taste["metrics"][1]["text"], "—")

    def test_skill_config_is_carried(self):
        self.assertEqual(self.s["arms"][0]["skillConfig"], "frontend-design")

    def test_colour_comes_from_the_model_not_the_arms_series_colour(self):
        """All three arms are the same local model, and the legend reads the
        colour as who ran it, so all three paint Qwen's colour."""
        self.assertEqual([a["color"] for a in self.s["arms"]], ["#2a9d8f"] * 3)

    def test_game_arms_keep_their_own_series_colour(self):
        g = ad.build_game(GAME)
        self.assertEqual([a["color"] for a in g["arms"]], ["#2a9d8f", "#f4a261"])


class TestBlock(unittest.TestCase):
    HTML = ("<script>\n/* DATA:begin */\nvar DATA = null;\n/* DATA:end */\nvar KEEP = 1;\n</script>")

    def _tmp(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
        f.write(body); f.close()
        return f.name

    def test_write_block_replaces_between_markers_only(self):
        path = self._tmp(self.HTML)
        self.assertTrue(ad.write_block(path, {"a": 1}))
        with open(path, encoding="utf-8") as f:
            out = f.read()
        self.assertIn('var DATA = {"a": 1};', out)
        self.assertIn("var KEEP = 1;", out)
        self.assertEqual(out.count("DATA:begin"), 1)

    def test_write_block_is_idempotent(self):
        path = self._tmp(self.HTML)
        self.assertTrue(ad.write_block(path, {"a": 1}))
        self.assertFalse(ad.write_block(path, {"a": 1}))

    def test_missing_markers_raises(self):
        path = self._tmp("<script>var DATA = null;</script>")
        with self.assertRaises(ad.MarkerError):
            ad.write_block(path, {})

    def test_check_exits_1_when_stale_and_0_when_fresh(self):
        path = self._tmp(self.HTML)
        data = ad.build_all(SCORES, GAME, SKILLS)
        self.assertEqual(ad.check_block(path, data), 1)
        ad.write_block(path, data)
        self.assertEqual(ad.check_block(path, data), 0)

    def test_check_goes_stale_when_a_source_number_changes(self):
        path = self._tmp(self.HTML)
        data = ad.build_all(SCORES, GAME, SKILLS)
        ad.write_block(path, data)
        self.assertEqual(ad.check_block(path, data), 0)
        game2 = json.loads(json.dumps(GAME))
        game2["results"][1]["value"] = 999
        self.assertEqual(ad.check_block(path, ad.build_all(SCORES, game2, SKILLS)), 1)


class TestBuildAll(unittest.TestCase):
    def test_top_level_shape(self):
        data = ad.build_all(SCORES, GAME, SKILLS)
        self.assertEqual(sorted(data.keys()), ["drawings", "game", "generated_at", "skills"])
        self.assertTrue(data["generated_at"])

    def test_serialises_without_surrogates_or_nan(self):
        json.dumps(ad.build_all(SCORES, GAME, SKILLS), ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
