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

    def test_questions_in_reading_order_dolphin_then_cow(self):
        # 7 and 0 lead in that order whatever their fields look like
        self.assertEqual([q["q"] for q in self.d["questions"]], [7, 0])

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
        # dolphin now leads the reading order, so it is questions[0]
        t = [t for q in self.d["questions"] for t in q["takes"]
             if t["slug"] == "dolphin-animated"][0]
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
        # hue by family, tone by model inside it
        self.assertEqual(by["opencode/qwen3.8-flash-next"]["color"], ad.FAMILY_RAMP["qwen"][1])
        self.assertEqual(by["claude/claude-opus-5"]["color"], ad.FAMILY_RAMP["claude"][1])
        self.assertEqual(by["opencode/gpt-5.6-terra"]["color"], ad.FAMILY_RAMP["gpt"][1])
        self.assertIs(by["claude/claude-opus-5"]["hosted"], True)
        self.assertIs(by["opencode/qwen3.8-flash-next"]["hosted"], False)

    def test_pair_records_its_question_indexes(self):
        by = {p["key"]: p for p in self.d["pairs"]}
        self.assertEqual(by["opencode/gpt-5.6-terra"]["qs"], [7])
        self.assertEqual(by["opencode/qwen3.8-flash-next"]["n"], 3)


class TestQuestionOrder(unittest.TestCase):
    """Reading order: dolphin, cow, then the questions with the most pairs."""

    def _order(self, extra):
        scores = json.loads(json.dumps(SCORES))
        scores["questions"] += [
            {"question_index": 4, "prompt": "a duck", "n_requirements": 2, "requirements": []},
            {"question_index": 6, "prompt": "a car", "n_requirements": 2, "requirements": []},
            {"question_index": 13, "prompt": "a barrel", "n_requirements": 2, "requirements": []},
        ]
        scores["artifacts"] = scores["artifacts"] + extra
        return [q["q"] for q in ad.build_drawings(scores)["questions"]]

    def test_lead_questions_come_first_even_with_the_smallest_field(self):
        # q4 gets three pairs, more than either lead question, and still follows them
        extra = [_art("opencode", m, "rubber-ducky", 4, 0.5, 1, 2)
                 for m in ("qwen3.8-flash-next", "gpt-5.6-terra", "qwen3.8-27b-8bit")]
        self.assertEqual(self._order(extra)[:2], [7, 0])

    def test_the_rest_run_widest_field_first(self):
        extra = [_art("opencode", m, "rubber-ducky", 4, 0.5, 1, 2)
                 for m in ("qwen3.8-flash-next", "gpt-5.6-terra", "qwen3.8-27b-8bit")]
        extra += [_art("opencode", "gpt-5.6-terra", "stunt-car", 6, 0.5, 1, 2)]
        self.assertEqual(self._order(extra), [7, 0, 4, 6])

    def test_equal_fields_fall_back_to_the_question_index(self):
        extra = [_art("opencode", "gpt-5.6-terra", "stunt-car", 6, 0.5, 1, 2),
                 _art("opencode", "gpt-5.6-terra", "treasure-barrel", 13, 0.5, 1, 2)]
        self.assertEqual(self._order(extra), [7, 0, 6, 13])


class TestLastTake(unittest.TestCase):
    """"Last take" is the drawing a pair ended on, an animated one preferred."""

    def _takes(self, arts, q=0):
        scores = json.loads(json.dumps(SCORES))
        scores["artifacts"] = arts
        d = ad.build_drawings(scores)
        return [t for qq in d["questions"] if qq["q"] == q for t in qq["takes"]]

    def test_an_animated_take_wins_over_a_later_still_one(self):
        takes = self._takes([
            _art("opencode", "qwen3.8-flash-next", "cow-plowing-animated", 0, 0.1, 0, 2, animated=True),
            _art("opencode", "qwen3.8-flash-next", "cow-plowing-v3", 0, 0.9, 1, 2),
        ])
        last = [t for t in takes if t["last"]]
        self.assertEqual([t["slug"] for t in last], ["cow-plowing-animated"])

    def test_without_an_animated_take_the_highest_rank_wins(self):
        takes = self._takes([
            _art("opencode", "qwen3.8-flash-next", "cow-plowing-v1", 0, 0.9, 1, 2),
            _art("opencode", "qwen3.8-flash-next", "cow-plowing-v3", 0, 0.1, 0, 2),
        ])
        self.assertEqual([t["slug"] for t in takes if t["last"]], ["cow-plowing-v3"])

    def test_last_and_best_are_independent_flags(self):
        takes = self._takes([
            _art("opencode", "qwen3.8-flash-next", "cow-plowing-v1", 0, 0.9, 1, 2),
            _art("opencode", "qwen3.8-flash-next", "cow-plowing-v3", 0, 0.1, 0, 2),
        ])
        self.assertEqual([t["slug"] for t in takes if t["best"]], ["cow-plowing-v1"])
        self.assertEqual([t["slug"] for t in takes if t["last"]], ["cow-plowing-v3"])

    def test_exactly_one_last_take_per_pair_per_question(self):
        d = ad.build_drawings(SCORES)
        for q in d["questions"]:
            seen = {}
            for t in q["takes"]:
                seen[t["pair"]] = seen.get(t["pair"], 0) + (1 if t["last"] else 0)
            for pair, n in seen.items():
                self.assertEqual(n, 1, "%s on q%s" % (pair, q["q"]))


class TestAspect(unittest.TestCase):
    """A frame takes its drawing's own ratio, so nothing is letterboxed."""

    def _write(self, body):
        fh = tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False)
        fh.write(body)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_viewbox_gives_the_ratio(self):
        p = self._write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500"></svg>')
        self.assertAlmostEqual(ad.aspect_of(p), 1.6)

    def test_viewbox_wins_over_width_and_height(self):
        p = self._write('<svg width="100" height="100" viewBox="0 0 1200 800"></svg>')
        self.assertAlmostEqual(ad.aspect_of(p), 1.5)

    def test_width_and_height_are_the_fallback(self):
        p = self._write('<svg xmlns="http://www.w3.org/2000/svg" width="900px" height="600px"></svg>')
        self.assertAlmostEqual(ad.aspect_of(p), 1.5)

    def test_a_file_with_neither_falls_back_to_four_thirds(self):
        p = self._write("<svg></svg>")
        self.assertAlmostEqual(ad.aspect_of(p), 4 / 3)

    def test_a_missing_file_falls_back_rather_than_raising(self):
        self.assertAlmostEqual(ad.aspect_of("/no/such/drawing.svg"), 4 / 3)

    def test_a_zero_sized_viewbox_falls_back(self):
        p = self._write('<svg viewBox="0 0 0 0"></svg>')
        self.assertAlmostEqual(ad.aspect_of(p), 4 / 3)


class TestTakeRank(unittest.TestCase):
    """The page reads a take chain first to last, so every take carries the
    order it was made in and never re-derives the rule in JavaScript."""

    def setUp(self):
        self.d = ad.build_drawings(SCORES)

    def test_every_take_carries_its_rank(self):
        for q in self.d["questions"]:
            for t in q["takes"]:
                self.assertEqual(t["rank"], ad.TAKE_RANK[t["take"]])

    def test_rank_sorts_a_chain_first_to_last(self):
        takes = [t for q in self.d["questions"] for t in q["takes"]]
        chain = [t for t in takes if t["pair"] == "opencode/qwen3.8-flash-next"]
        chain.sort(key=lambda t: t["rank"])
        self.assertEqual([t["take"] for t in chain][:1], ["v1"])
        self.assertGreaterEqual(chain[-1]["rank"], chain[0]["rank"])


class TestHosted(unittest.TestCase):
    """Who served the model is transcribed per pair, not guessed from the harness."""

    def test_a_recorded_pair_wins_over_the_harness_rule(self):
        # an OpenAI model run through opencode is still served by OpenAI
        self.assertTrue(ad._hosted({"hosted": True}, "opencode"))
        self.assertFalse(ad._hosted({"hosted": False}, "claude"))

    def test_without_a_record_claude_code_is_the_hosted_control_arm(self):
        self.assertTrue(ad._hosted(None, "claude"))
        self.assertFalse(ad._hosted(None, "opencode"))
        self.assertFalse(ad._hosted({}, "opencode"))

    def test_the_participants_file_marks_every_pair(self):
        cfgs = ad._participants()
        self.assertTrue(cfgs, "participants.json should load")
        for key, c in cfgs.items():
            self.assertIn("hosted", c, key)
        self.assertTrue(cfgs["opencode/gpt-5.6-terra"]["hosted"])
        self.assertFalse(cfgs["opencode/qwen3.8-flash-next"]["hosted"])


class TestFamilyColour(unittest.TestCase):
    """Hue by model family, tone by stack inside it."""

    def test_family_of_maps_every_model_in_the_campaigns(self):
        self.assertEqual(ad.family_of("qwen3.8-flash-next"), "qwen")
        self.assertEqual(ad.family_of("claude-opus-5"), "claude")
        self.assertEqual(ad.family_of("fable-5-1"), "claude")
        self.assertEqual(ad.family_of("gpt-5.6-terra"), "gpt")
        self.assertEqual(ad.family_of("gpt-6-astra"), "gpt")

    def test_an_unknown_model_still_gets_a_colour(self):
        self.assertIn(ad.color_for("something-new"), ad.FAMILY_RAMP["gpt"])

    def test_two_stacks_of_one_model_share_the_hue_and_differ_by_tone(self):
        plain = ad.color_for("qwen3.8-flash-next", "opencode-qwen38")
        powered = ad.color_for("qwen3.8-flash-next", "opencode-qwen38-superpowers")
        self.assertNotEqual(plain, powered)
        self.assertIn(plain, ad.FAMILY_RAMP["qwen"])
        self.assertIn(powered, ad.FAMILY_RAMP["qwen"])

    def test_an_unknown_variant_falls_back_to_the_models_own_tone(self):
        self.assertEqual(ad.color_for("claude-opus-5", "no-such-arm"),
                         ad.color_for("claude-opus-5"))

    def test_families_legend_is_one_row_per_family(self):
        fams = ad.build_families()
        self.assertEqual([f["key"] for f in fams], ["qwen", "claude", "gpt"])
        for f in fams:
            self.assertEqual(f["color"], ad.FAMILY_RAMP[f["key"]][1])
            self.assertTrue(f["label"])


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
        self.assertEqual(a["color"], ad.FAMILY_RAMP["qwen"][1])
        self.assertIs(a["hosted"], False)
        self.assertEqual(a["label"], "opencode + Qwen3.8 Flash Next (local)")

    def test_clip_is_empty_when_no_loop_was_recorded(self):
        # the fixture arms have no file under results/clips, so the page falls
        # back to the still rather than requesting a missing video
        for a in self.g["arms"]:
            if not os.path.exists(os.path.join(
                    ad.ROOT, "bench", "agent-build-off", "results", "clips", a["id"] + ".mp4")):
                self.assertEqual(a["clip"], "")

    def test_a_recorded_clip_is_a_site_relative_mp4_path(self):
        for a in self.g["arms"]:
            if a["clip"]:
                self.assertTrue(a["clip"].startswith("../bench/agent-build-off/results/clips/"))
                self.assertTrue(a["clip"].endswith(".mp4"))

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

    def test_three_skill_arms_are_three_tones_of_one_family(self):
        """All three arms are the same local model, so they share the Qwen hue
        and take one tone each: one family at a glance, still told apart."""
        got = [a["color"] for a in self.s["arms"]]
        self.assertEqual(got, list(ad.FAMILY_RAMP["qwen"]))
        self.assertEqual(len(set(got)), 3)

    def test_game_colour_is_the_family_ramp_not_the_arms_series_colour(self):
        """arms.json carries its own series colours for the other reports; this
        page paints the family ramp so two arms of one model read as one hue."""
        g = ad.build_game(GAME)
        self.assertEqual([a["color"] for a in g["arms"]],
                         [ad.FAMILY_RAMP["qwen"][1], ad.FAMILY_RAMP["gpt"][1]])


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
        self.assertEqual(sorted(data.keys()),
                         ["drawings", "families", "game", "generated_at", "skills"])
        self.assertTrue(data["generated_at"])

    def test_serialises_without_surrogates_or_nan(self):
        json.dumps(ad.build_all(SCORES, GAME, SKILLS), ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
