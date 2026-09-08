# SVGBench Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a filterable gallery of all 89 harness-matrix SVGs, each with its SVGBench score, to `reports/harness-matrix-svgbench.html`.

**Architecture:** A Python generator reads `scores.json` and writes a `var GALLERY = [...]` block between two markers in the dashboard. The page's inline JavaScript renders the gallery section from that block, reusing the dashboard's CSS tokens and lightbox. No new page, no new dependency, no build step beyond the generator.

**Tech Stack:** Python 3 stdlib (generator + unittest), vanilla HTML/CSS/JS in the dashboard.

**Spec:** `docs/superpowers/specs/2026-09-07-agent-comparison-site-design.md` §"The gallery is deleted and the scoring dashboard is the single SVG page" (lines 478-492). This plan keeps that decision: the gallery lives inside the scoring page. The old gallery (`git show ad039ad:bench/harness-matrix/harness-matrix-svgs.html`) is the inspiration for controls and badges.

## Global Constraints

- All site copy is in English.
- `reports/` holds self-contained dashboards; source data stays in `bench/` (AGENTS.md).
- `scores.json` is generated; never edit it by hand. The gallery reads it, never writes it.
- Every displayed figure carries its `n` or its `met/total`.
- Relative asset paths use the existing `L = "../bench/harness-matrix/"` prefix.
- No new fonts, no CDN scripts. Palette tokens: `--rig` teal for local arms, `--ctl` raspberry for controls.
- Run `python3 tests/test_svgbench_eval.py` and the new test after any script change (from `bench/harness-matrix/`).

## What the old gallery had, and what changes

| Old gallery | This gallery |
|---|---|
| Group by prompt / harness / model | Same three; each group header also shows the group's mean score with its `n` |
| Takes segment: all / first / last / animated | Same, plus **"best"** (the highest-scoring take per set; ties show all tied takes) |
| Selects: harness, model, prompt, each with counts | Same, prompt select lists `Q<id> · <label>` and includes "Dawn on the beach (unscored)" |
| Checkbox "complete sets only" | Replaced by **"scored only"** checkbox (hides the 5 dawn-beach SVGs) and a **minimum score** select (any / ≥ 0.5 / ≥ 0.75 / perfect) |
| Badges: take, matrix run, in verdict, unattributed | Badges: **take**, **score chip `met/total`** (filled when perfect, dashed when unscored), **best of set**, **†self-judged** on claude-opus-5 tiles, **animated** flag on the image |
| Status line + active-filter chips with × + Reset | Same, plus the filter state is written to `location.hash` so a filtered view can be linked |
| Lightbox with prev/next | Same lightbox as the dashboard, extended with prev/next and the per-requirement checklist from the verdict (✓/✗ + note) |
| Hand-written data array | Generated from `scores.json` |

---

### Task 1: Gallery data generator

**Files:**
- Create: `bench/harness-matrix/scripts/svgbench/gallery_data.py`
- Create: `bench/harness-matrix/tests/test_gallery_data.py`
- Modify: `reports/harness-matrix-svgbench.html:405` (add the two markers after the `var DATA = {...};` line)

**Interfaces:**
- Consumes: `results/svgbench/scores.json` (`artifacts[]` with `harness, model, artifact, question_index, animated, slug, score, met, total, requirements[{text,met,note}]`; `unscored[]` with `harness, model, artifact, slug, reason`).
- Produces: `build_items(scores: dict) -> list[dict]` and `write_block(html_path, items)`. Each item:

```python
{
  "harness": "opencode", "model": "qwen3.8-flash-next", "arm": "local",   # arm: "local" unless harness == "claude" -> "control"
  "q": 7,                       # question_index, or None for unscored
  "prompt": "Dolphin",          # PROMPT_LABEL[q], or "Dawn on the beach" when q is None
  "slug": "dolphin-hula-hoop-fish-v2",
  "base": "dolphin-hula-hoop-fish",   # slug minus the take suffix; the set key is harness/model/q/base
  "take": "v2",                 # "v1" | "v2" | "v3" | "animated"; a slug with no suffix is "v1"
  "file": "logs/opencode/qwen3.8-flash-next/dolphin-hula-hoop-fish-v2.svg",
  "animated": False,
  "score": 1.0, "met": 7, "total": 7,   # all None when unscored
  "reqs": [{"t": "<text>", "m": True, "n": ""}],   # [] when unscored
  "verdict": "results/svgbench/verdicts/opencode/qwen3.8-flash-next/dolphin-hula-hoop-fish-v2.json",  # None when unscored
  "reason": None                # unscored reason string, else None
}
```

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd bench/harness-matrix && python3 tests/test_gallery_data.py`
Expected: `ModuleNotFoundError: No module named 'gallery_data'`

- [ ] **Step 3: Write the generator**

```python
#!/usr/bin/env python3
"""Build the gallery block of reports/harness-matrix-svgbench.html from scores.json.

Usage (from bench/harness-matrix/):
    python3 scripts/svgbench/gallery_data.py            # rewrite the block in place
    python3 scripts/svgbench/gallery_data.py --check    # exit 1 when the block is stale

The block sits between `/* GALLERY:begin */` and `/* GALLERY:end */` inside the
dashboard's <script>. Everything else in the file is untouched.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))            # bench/harness-matrix
SCORES = os.path.join(ROOT, "results", "svgbench", "scores.json")
HTML = os.path.abspath(os.path.join(ROOT, "..", "..", "reports", "harness-matrix-svgbench.html"))

PROMPT_LABEL = {0: "Cow plowing", 4: "Rubber ducky", 5: "Picnic on clouds", 6: "Stunt car",
                7: "Dolphin", 12: "Fruit stall", 13: "Treasure barrel"}
UNSCORED_LABEL = {"dawn-beach": "Dawn on the beach"}
TAKE_RANK = {"v1": 0, "v2": 1, "v3": 2, "animated": 3}
_SUFFIX = re.compile(r"-(v1|v2|v3|animated)$")
BEGIN, END = "/* GALLERY:begin */", "/* GALLERY:end */"


class MarkerError(RuntimeError):
    """The HTML has no single GALLERY:begin/GALLERY:end pair."""


def split_slug(slug):
    m = _SUFFIX.search(slug)
    if not m:
        return slug, "v1"
    return slug[: m.start()], m.group(1)


def _item(a, scored):
    base, take = split_slug(a["slug"])
    q = a.get("question_index")
    return {
        "harness": a["harness"], "model": a["model"],
        "arm": "control" if a["harness"] == "claude" else "local",
        "q": q,
        "prompt": PROMPT_LABEL.get(q) if q is not None else UNSCORED_LABEL.get(base, base),
        "slug": a["slug"], "base": base, "take": take,
        "file": a["artifact"], "animated": bool(a.get("animated")),
        "score": a["score"] if scored else None,
        "met": a["met"] if scored else None,
        "total": a["total"] if scored else None,
        "reqs": [{"t": r["text"], "m": bool(r["met"]), "n": r.get("note", "")} for r in a["requirements"]] if scored else [],
        "verdict": "results/svgbench/verdicts/%s/%s/%s.json" % (a["harness"], a["model"], a["slug"]) if scored else None,
        "reason": None if scored else a.get("reason"),
    }


def build_items(scores):
    items = [_item(a, True) for a in scores["artifacts"]] + [_item(a, False) for a in scores.get("unscored", [])]
    items.sort(key=lambda i: (i["harness"], i["model"], i["q"] if i["q"] is not None else 999, i["base"], TAKE_RANK[i["take"]]))
    return items


def render_block(items):
    return "%s\nvar GALLERY = %s;\n%s" % (BEGIN, json.dumps(items, ensure_ascii=False, separators=(", ", ": ")), END)


def write_block(html_path, items):
    src = open(html_path, encoding="utf-8").read()
    if src.count(BEGIN) != 1 or src.count(END) != 1:
        raise MarkerError("expected exactly one %s / %s pair in %s" % (BEGIN, END, html_path))
    head, rest = src.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    out = head + render_block(items) + tail
    if out != src:
        open(html_path, "w", encoding="utf-8").write(out)
    return out != src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 when the block differs from scores.json")
    args = ap.parse_args(argv)
    items = build_items(json.load(open(SCORES, encoding="utf-8")))
    if args.check:
        src = open(HTML, encoding="utf-8").read()
        stale = render_block(items) not in src
        print("gallery block is %s (%d items)" % ("STALE" if stale else "fresh", len(items)))
        return 1 if stale else 0
    changed = write_block(HTML, items)
    print("gallery block %s: %d items" % ("rewritten" if changed else "unchanged", len(items)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Add the markers to the dashboard**

In `reports/harness-matrix-svgbench.html`, directly after the line that starts with `var DATA = {` (line 405, one long line ending in `};`), insert:

```js
/* GALLERY:begin */
var GALLERY = [];
/* GALLERY:end */
```

- [ ] **Step 5: Run the tests and the generator**

Run: `cd bench/harness-matrix && python3 tests/test_gallery_data.py && python3 tests/test_svgbench_eval.py && python3 scripts/svgbench/gallery_data.py && python3 scripts/svgbench/gallery_data.py --check`
Expected: both test files pass; `gallery block rewritten: 89 items`; `gallery block is fresh (89 items)`.

- [ ] **Step 6: Commit**

```bash
git add bench/harness-matrix/scripts/svgbench/gallery_data.py bench/harness-matrix/tests/test_gallery_data.py reports/harness-matrix-svgbench.html
git commit -m "bench(svgbench): generate the gallery data block from scores.json"
```

---

### Task 2: Gallery section markup and styles

**Files:**
- Modify: `reports/harness-matrix-svgbench.html` — nav (line ~254), a new `<section id="gallery">` inserted before `<section id="loose"` (line 361), CSS before the `/* ---------- loose ends ---------- */` comment (line ~199).

**Interfaces:**
- Produces element ids used by Task 3: `groupSeg`, `takeSeg`, `harnessFilter`, `modelFilter`, `promptFilter`, `minScore`, `scoredOnly`, `resetFilters`, `galleryStatus`, `galleryTiles`.

- [ ] **Step 1: Add the nav link**

After `<a href="#questions">By question</a>` add `<a href="#gallery">Gallery</a>`.

- [ ] **Step 2: Insert the section**

```html
  <section id="gallery" aria-labelledby="gallery-h">
    <h2 id="gallery-h">Gallery</h2>
    <p class="sec-note">Every SVG in the logs tree, 89 in all, with its score. Each harness × model set is laid out as v1, v2, v3, animated; a dashed slot marks a take that was never made. Scores are requirements met over total, from the same verdicts as the board. The five dawn-beach drawings have no question and carry no score.</p>
    <div class="controls" aria-label="Gallery controls">
      <div class="control-row">
        <div class="field">Group by
          <div class="seg" id="groupSeg" role="group" aria-label="Group by">
            <button type="button" data-v="prompt" aria-pressed="true">Prompt</button>
            <button type="button" data-v="harness" aria-pressed="false">Harness</button>
            <button type="button" data-v="model" aria-pressed="false">Model</button>
          </div>
        </div>
        <div class="field">Takes
          <div class="seg" id="takeSeg" role="group" aria-label="Takes">
            <button type="button" data-v="all" aria-pressed="true">All</button>
            <button type="button" data-v="first" aria-pressed="false">First</button>
            <button type="button" data-v="last" aria-pressed="false">Last</button>
            <button type="button" data-v="best" aria-pressed="false">Best</button>
            <button type="button" data-v="animated" aria-pressed="false">Animated</button>
          </div>
        </div>
      </div>
      <div class="control-row">
        <label for="harnessFilter">Harness <select id="harnessFilter"><option value="all">All harnesses</option></select></label>
        <label for="modelFilter">Model <select id="modelFilter"><option value="all">All models</option></select></label>
        <label for="promptFilter">Prompt <select id="promptFilter"><option value="all">All prompts</option></select></label>
        <label for="minScore">Minimum score
          <select id="minScore">
            <option value="0">Any</option>
            <option value="0.5">≥ 0.500</option>
            <option value="0.75">≥ 0.750</option>
            <option value="1">Perfect only</option>
          </select>
        </label>
        <label class="check" for="scoredOnly"><input type="checkbox" id="scoredOnly"> Scored only</label>
        <button class="reset" id="resetFilters" type="button" disabled>Reset</button>
      </div>
    </div>
    <div class="gallery-status" id="galleryStatus" aria-live="polite"></div>
    <div class="prompt-groups" id="galleryTiles"></div>
  </section>
```

- [ ] **Step 3: Add the styles**

```css
  /* ---------- gallery ---------- */
  .controls { border: 1px solid var(--line); border-top: 3px solid var(--ink); background: var(--paper); padding: 12px 16px 14px; margin-bottom: 14px; }
  .control-row { display: flex; flex-wrap: wrap; gap: 12px 22px; align-items: end; }
  .control-row + .control-row { margin-top: 12px; }
  .control-row label, .control-row .field { display: grid; gap: 4px; font-size: 12.5px; font-weight: 650; color: var(--ink-soft); }
  .control-row select { font: 14px/1.3 var(--f); padding: 5px 8px; border: 1px solid var(--ink); background: var(--board); color: var(--ink); }
  .control-row .check { grid-auto-flow: column; align-items: center; gap: 7px; padding-bottom: 6px; }
  .seg { display: inline-flex; border: 1px solid var(--ink); }
  .seg button { font: 13px/1 var(--f); font-weight: 650; padding: 7px 11px; border: 0; background: var(--paper); color: var(--ink); cursor: pointer; }
  .seg button + button { border-left: 1px solid var(--ink); }
  .seg button[aria-pressed="true"] { background: var(--ink); color: var(--paper); }
  .reset { font: 13px var(--f); font-weight: 650; padding: 7px 12px; border: 1px solid var(--ink); background: var(--paper); cursor: pointer; align-self: end; }
  .reset:disabled { opacity: 0.45; cursor: default; }
  .gallery-status { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; font-size: 13px; color: var(--ink-soft); margin: 0 0 18px; }
  .fchip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border: 1px solid var(--ink-soft); font: 12px var(--f); font-weight: 650; color: var(--ink); background: var(--paper); cursor: pointer; }
  .fchip::after { content: "\00d7"; font-weight: 800; color: var(--ink-soft); }
  .prompt-group > h3 { margin: 30px 0 3px; font-size: 15px; font-weight: 700; border-bottom: 2px solid var(--ink); padding-bottom: 7px; font-variation-settings: "wdth" 105; }
  .prompt-group > h3 small { float: right; font-weight: 450; color: var(--ink-soft); }
  .comparison-set { margin: 14px 0 22px; }
  .comparison-set h4 { margin: 0 0 8px; font-size: 13.5px; font-weight: 700; }
  .comparison-set h4 .count { font-weight: 450; color: var(--ink-soft); margin-left: 6px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
  .tiles.slots { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .tile { margin: 0; background: var(--paper); border: 1px solid var(--line); position: relative; }
  .tile::before { content: ""; position: absolute; top: -1px; left: -1px; width: 11px; height: 11px; border-top: 3px solid var(--arm, var(--ink)); border-left: 3px solid var(--arm, var(--ink)); pointer-events: none; }
  .tile.local { --arm: var(--rig); }
  .tile.control { --arm: var(--ctl); }
  .tile > button { display: block; width: 100%; padding: 0; margin: 0; border: 0; background: var(--matte); cursor: zoom-in; position: relative; aspect-ratio: 4 / 3; }
  .tile > button img { display: block; width: 100%; height: 100%; object-fit: contain; }
  .tile figcaption { padding: 8px 10px 10px; border-top: 1px solid var(--line); font-size: 12.5px; }
  .tile .subj { margin: 0 0 2px; font-weight: 700; font-size: 13px; }
  .tile .who { margin: 0 0 6px; color: var(--ink-soft); }
  .badges { display: flex; flex-wrap: wrap; gap: 4px; margin: 0; }
  .badge { display: inline-block; font-size: 11.5px; font-weight: 650; padding: 1px 7px; border: 1px solid var(--ink-soft); color: var(--ink-soft); }
  .badge.take { border-color: var(--ink); color: var(--ink); font-weight: 750; }
  .badge.score { border-color: var(--ink); color: var(--ink); }
  .badge.score.perfect { background: var(--ink); color: var(--paper); }
  .badge.score.none { border-style: dashed; }
  .badge.best { border-color: var(--rig); color: var(--rig); }
  .badge.self { border-color: var(--ctl); color: var(--ctl); }
  .empty-slot { margin: 0; border: 1px dashed var(--line); color: var(--ink-soft); font-size: 12px; display: grid; place-items: center; min-height: 120px; }
  .gallery-empty { padding: 30px 0; color: var(--ink-soft); }
  @media (max-width: 860px) { .tiles.slots { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 620px) { .control-row label, .control-row .field, .control-row select { width: 100%; } }
```

- [ ] **Step 4: Check the page still renders**

Run: `cd bench/harness-matrix && python3 scripts/svgbench/gallery_data.py --check` (still fresh), then open the page over `preview_start` name `repo-static` at `http://localhost:8765/reports/harness-matrix-svgbench.html#gallery`. Expected: the controls render, the tiles area is empty, no console errors.

- [ ] **Step 5: Commit**

```bash
git add reports/harness-matrix-svgbench.html
git commit -m "docs(reports): add the gallery section markup and styles"
```

---

### Task 3: Gallery rendering, filters, and hash state

**Files:**
- Modify: `reports/harness-matrix-svgbench.html` — add a `/* ---------------- gallery ---------------- */` block in the `<script>` before `/* ---------------- lightbox ---------------- */`.

**Interfaces:**
- Consumes: `GALLERY` (Task 1 shape), `L`, `VD`, `DATA.self_judge`, `HARNESS_LABEL`, `el`, `esc`, `plural`, `openLb(src, alt, title)` from the existing script.
- Produces: `renderGallery()`; `GALLERY_FLAT` (the ordered list of visible items, consumed by Task 4's prev/next); `tileFigure(item, index)`.

- [ ] **Step 1: Add the derived fields and the state**

```js
/* ---------------- gallery ---------------- */
var TAKE_SLOTS = ["v1", "v2", "v3", "animated"];
var TAKE_LABEL = { v1: "take 1", v2: "take 2", v3: "take 3", animated: "animated" };
var MODEL_RANK = ["claude-opus-5", "qwen3.8-flash-next", "qwen3.8-27b-8bit", "gpt-5.6-terra", "fable-5-1", "claude-opus-4-8"];
GALLERY.forEach(function (x) {
  x.setKey = x.harness + "/" + x.model + "/" + (x.q == null ? "u" : x.q) + "/" + x.base;
  x.harnessLabel = HARNESS_LABEL[x.harness] || x.harness;
  x.promptLabel = x.q == null ? x.prompt + " (unscored)" : "Q" + x.q + " · " + x.prompt;
});
(function markSets() {
  var sets = {};
  GALLERY.forEach(function (x) { (sets[x.setKey] = sets[x.setKey] || []).push(x); });
  Object.keys(sets).forEach(function (k) {
    var items = sets[k];
    var statics = items.filter(function (x) { return x.take !== "animated"; });
    var best = Math.max.apply(null, items.map(function (x) { return x.score == null ? -1 : x.score; }));
    items.forEach(function (x) {
      x.isFirst = x === (statics[0] || items[0]);
      x.isLast = x === (statics[statics.length - 1] || items[items.length - 1]);
      x.isBest = x.score != null && x.score === best && items.length > 1;
    });
  });
})();

var gState = { group: "prompt", takes: "all" };
var groupSeg = document.getElementById("groupSeg"), takeSeg = document.getElementById("takeSeg");
var harnessFilter = document.getElementById("harnessFilter"), modelFilter = document.getElementById("modelFilter");
var promptFilter = document.getElementById("promptFilter"), minScore = document.getElementById("minScore");
var scoredOnly = document.getElementById("scoredOnly"), resetFilters = document.getElementById("resetFilters");
var galleryStatus = document.getElementById("galleryStatus"), galleryTiles = document.getElementById("galleryTiles");
var GALLERY_FLAT = [];

function uniq(list) { return list.filter(function (v, i, all) { return all.indexOf(v) === i; }); }
function fillSelect(select, values, labelOf, matchOf) {
  values.forEach(function (v) {
    var count = GALLERY.filter(function (x) { return matchOf(x, v); }).length;
    var o = el("option", null, esc(labelOf(v)) + " (" + count + ")"); o.value = v; select.appendChild(o);
  });
}
fillSelect(harnessFilter, uniq(GALLERY.map(function (x) { return x.harness; })), function (h) { return HARNESS_LABEL[h] || h; }, function (x, v) { return x.harness === v; });
fillSelect(modelFilter, uniq(GALLERY.map(function (x) { return x.model; })).sort(function (a, b) { return MODEL_RANK.indexOf(a) - MODEL_RANK.indexOf(b); }), function (m) { return m; }, function (x, v) { return x.model === v; });
fillSelect(promptFilter, uniq(GALLERY.map(function (x) { return x.promptLabel; })), function (p) { return p; }, function (x, v) { return x.promptLabel === v; });
```

- [ ] **Step 2: Add the filter predicate and the render**

```js
function takePass(x) {
  if (gState.takes === "first") return x.isFirst;
  if (gState.takes === "last") return x.isLast;
  if (gState.takes === "best") return x.isBest || x.score == null && x.isLast;
  if (gState.takes === "animated") return x.take === "animated";
  return true;
}
function galleryShown() {
  var min = parseFloat(minScore.value);
  return GALLERY.filter(function (x) {
    return (harnessFilter.value === "all" || x.harness === harnessFilter.value) &&
      (modelFilter.value === "all" || x.model === modelFilter.value) &&
      (promptFilter.value === "all" || x.promptLabel === promptFilter.value) &&
      (!scoredOnly.checked || x.score != null) &&
      (min === 0 || (x.score != null && x.score >= min)) &&
      takePass(x);
  });
}
function groupValue(x) { return gState.group === "prompt" ? x.promptLabel : gState.group === "harness" ? x.harnessLabel : x.model; }
function setTitle(x) {
  if (gState.group === "prompt") return x.harnessLabel + " × " + x.model + " · " + x.base;
  if (gState.group === "harness") return x.model + " · " + x.promptLabel + " · " + x.base;
  return x.harnessLabel + " · " + x.promptLabel + " · " + x.base;
}

function renderGallery() {
  var shown = galleryShown(), useSlots = gState.takes === "all";
  galleryTiles.replaceChildren(); GALLERY_FLAT = [];
  renderGalleryStatus(shown);
  if (!shown.length) { galleryTiles.appendChild(el("p", "gallery-empty", "No SVGs match these filters.")); return; }
  var groups = uniq(shown.map(groupValue));
  groups.forEach(function (g) {
    var items = shown.filter(function (x) { return groupValue(x) === g; });
    var scored = items.filter(function (x) { return x.score != null; });
    var mean = scored.length ? (scored.reduce(function (t, x) { return t + x.score; }, 0) / scored.length).toFixed(3) : "—";
    var sec = el("section", "prompt-group");
    sec.appendChild(el("h3", null, esc(g) + "<small>" + plural(items.length, "SVG") + " · mean " + mean + " (n=" + scored.length + ")</small>"));
    uniq(items.map(function (x) { return x.setKey; })).forEach(function (key) {
      var setItems = items.filter(function (x) { return x.setKey === key; });
      var set = el("div", "comparison-set");
      set.appendChild(el("h4", null, esc(setTitle(setItems[0])) + '<span class="count">· ' + plural(setItems.length, "SVG") + "</span>"));
      var grid = el("div", "tiles" + (useSlots ? " slots" : ""));
      if (useSlots) {
        TAKE_SLOTS.forEach(function (slot) {
          var hits = setItems.filter(function (x) { return x.take === slot; });
          if (!hits.length) { grid.appendChild(el("p", "empty-slot", "no " + TAKE_LABEL[slot])); return; }
          hits.forEach(function (x) { grid.appendChild(tileFigure(x)); });
        });
      } else {
        setItems.forEach(function (x) { grid.appendChild(tileFigure(x)); });
      }
      set.appendChild(grid); sec.appendChild(set);
    });
    galleryTiles.appendChild(sec);
  });
}

function tileFigure(x) {
  var index = GALLERY_FLAT.length; GALLERY_FLAT.push(x);
  var fig = el("figure", "tile " + x.arm);
  var src = L + x.file;
  var alt = x.prompt + ", " + x.harnessLabel + " × " + x.model + ", " + TAKE_LABEL[x.take] + (x.score == null ? ", unscored" : ", " + x.met + " of " + x.total + " requirements met");
  var btn = el("button"); btn.type = "button"; btn.setAttribute("aria-label", "Open " + x.slug + " full size");
  var img = el("img"); img.src = src; img.alt = alt; img.loading = "lazy"; btn.appendChild(img);
  if (x.animated) btn.appendChild(el("span", "anim-flag", "animated"));
  btn.addEventListener("click", function () { openGalleryLb(index); });
  fig.appendChild(btn);
  var cap = el("figcaption");
  cap.appendChild(el("p", "subj", esc(x.prompt) + " · " + esc(x.slug)));
  cap.appendChild(el("p", "who", esc(x.harnessLabel + " · " + x.model)));
  var b = '<span class="badge take">' + TAKE_LABEL[x.take] + "</span>";
  b += x.score == null ? '<span class="badge score none" title="' + esc(x.reason || "") + '">unscored</span>'
     : '<span class="badge score' + (x.score === 1 ? " perfect" : "") + '">' + x.met + "/" + x.total + "</span>";
  if (x.isBest) b += '<span class="badge best">best of set</span>';
  if (x.harness + "/" + x.model === DATA.self_judge) b += '<span class="badge self" title="judged by the model that drew it">† self-judged</span>';
  cap.appendChild(el("p", "badges", b));
  fig.appendChild(cap);
  return fig;
}
```

- [ ] **Step 3: Add the status line, chips, reset, and hash state**

```js
function renderGalleryStatus(shown) {
  galleryStatus.replaceChildren();
  var takesText = { all: "takes in order v1, v2, v3, animated", first: "first take of each set", last: "last static take of each set", best: "best-scoring take of each set (ties shown)", animated: "animated takes only" }[gState.takes];
  galleryStatus.appendChild(el("span", null, plural(shown.length, "SVG") + " of " + GALLERY.length + " · grouped by " + gState.group + " · " + takesText));
  var chips = [];
  if (harnessFilter.value !== "all") chips.push({ text: HARNESS_LABEL[harnessFilter.value] || harnessFilter.value, clear: function () { harnessFilter.value = "all"; } });
  if (modelFilter.value !== "all") chips.push({ text: modelFilter.value, clear: function () { modelFilter.value = "all"; } });
  if (promptFilter.value !== "all") chips.push({ text: promptFilter.value, clear: function () { promptFilter.value = "all"; } });
  if (minScore.value !== "0") chips.push({ text: "score " + minScore.options[minScore.selectedIndex].text, clear: function () { minScore.value = "0"; } });
  if (scoredOnly.checked) chips.push({ text: "scored only", clear: function () { scoredOnly.checked = false; } });
  if (gState.takes !== "all") chips.push({ text: "takes: " + gState.takes, clear: function () { setSeg(takeSeg, "all"); gState.takes = "all"; } });
  chips.forEach(function (c) {
    var chip = el("button", "fchip", esc(c.text)); chip.type = "button"; chip.setAttribute("aria-label", "Clear filter " + c.text);
    chip.addEventListener("click", function () { c.clear(); update(); });
    galleryStatus.appendChild(chip);
  });
  resetFilters.disabled = chips.length === 0 && gState.group === "prompt";
}
function setSeg(seg, v) {
  seg.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === v)); });
}
function writeHash() {
  var p = [];
  if (gState.group !== "prompt") p.push("g=" + gState.group);
  if (gState.takes !== "all") p.push("t=" + gState.takes);
  if (harnessFilter.value !== "all") p.push("h=" + encodeURIComponent(harnessFilter.value));
  if (modelFilter.value !== "all") p.push("m=" + encodeURIComponent(modelFilter.value));
  if (promptFilter.value !== "all") p.push("p=" + encodeURIComponent(promptFilter.value));
  if (minScore.value !== "0") p.push("s=" + minScore.value);
  if (scoredOnly.checked) p.push("scored=1");
  history.replaceState(null, "", p.length ? "#gallery?" + p.join("&") : location.pathname + location.search + (location.hash.indexOf("#gallery") === 0 ? "#gallery" : location.hash));
}
function readHash() {
  var h = location.hash;
  if (h.indexOf("#gallery?") !== 0) return;
  h.slice(9).split("&").forEach(function (kv) {
    var k = kv.split("=")[0], v = decodeURIComponent(kv.split("=").slice(1).join("="));
    if (k === "g" && ["prompt", "harness", "model"].indexOf(v) >= 0) { gState.group = v; setSeg(groupSeg, v); }
    if (k === "t" && ["all", "first", "last", "best", "animated"].indexOf(v) >= 0) { gState.takes = v; setSeg(takeSeg, v); }
    if (k === "h") harnessFilter.value = v;
    if (k === "m") modelFilter.value = v;
    if (k === "p") promptFilter.value = v;
    if (k === "s") minScore.value = v;
    if (k === "scored") scoredOnly.checked = v === "1";
  });
}
function update() { writeHash(); renderGallery(); }
groupSeg.addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; gState.group = b.dataset.v; setSeg(groupSeg, b.dataset.v); update(); });
takeSeg.addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; gState.takes = b.dataset.v; setSeg(takeSeg, b.dataset.v); update(); });
[harnessFilter, modelFilter, promptFilter, minScore, scoredOnly].forEach(function (c) { c.addEventListener("change", update); });
resetFilters.addEventListener("click", function () {
  harnessFilter.value = modelFilter.value = promptFilter.value = "all"; minScore.value = "0"; scoredOnly.checked = false;
  gState = { group: "prompt", takes: "all" }; setSeg(groupSeg, "prompt"); setSeg(takeSeg, "all"); update();
});
readHash();
renderGallery();
```

Note: `openGalleryLb(index)` is defined in Task 4. Until then, define a one-line stub right above `renderGallery` so this task runs: `function openGalleryLb(i) { var x = GALLERY_FLAT[i]; openLb(L + x.file, x.slug, x.model + " · " + x.slug); }`. Task 4 replaces it.

- [ ] **Step 4: Verify in the browser**

Open `http://localhost:8765/reports/harness-matrix-svgbench.html#gallery` and run in `javascript_tool`:

```js
({tiles: document.querySelectorAll('#galleryTiles .tile').length, groups: document.querySelectorAll('#galleryTiles .prompt-group').length, empty: document.querySelectorAll('.empty-slot').length, errors: 0})
```

Expected: `tiles` is 89; `groups` is 8 (seven questions plus "Dawn on the beach (unscored)"). Then set `minScore` to `1` via `form_input` and confirm `tiles` drops to the count of perfect scores in `scores.json` (`python3 -c "import json;print(sum(1 for a in json.load(open('bench/harness-matrix/results/svgbench/scores.json'))['artifacts'] if a['score']==1))"`). Check `location.hash` reads `#gallery?s=1`. Reload the page with that hash and confirm the filter is applied. `read_console_messages` with `onlyErrors: true` returns nothing.

- [ ] **Step 5: Commit**

```bash
git add reports/harness-matrix-svgbench.html
git commit -m "docs(reports): render the SVG gallery with filters and linkable state"
```

---

### Task 4: Lightbox with prev/next and the requirement checklist

**Files:**
- Modify: `reports/harness-matrix-svgbench.html` — the `<dialog id="lb">` markup (line ~387), the `dialog#lb` CSS (line ~211), and the lightbox script block.

**Interfaces:**
- Consumes: `GALLERY_FLAT`, `openLb(src, alt, title)` (kept for the Q7 cards), `VD`, `L`.
- Produces: `openGalleryLb(index)` replacing the Task 3 stub.

- [ ] **Step 1: Extend the dialog markup**

Replace the dialog with:

```html
<dialog id="lb" aria-label="Artifact viewer">
  <div class="lb-head"><h3 id="lbTitle"></h3><span class="pos" id="lbPos"></span><button class="close" id="lbClose" aria-label="Close viewer">Close</button></div>
  <div class="lb-body">
    <button class="lb-nav prev" id="lbPrev" type="button" aria-label="Previous" hidden>&#8249;</button>
    <img id="lbImg" alt="">
    <button class="lb-nav next" id="lbNext" type="button" aria-label="Next" hidden>&#8250;</button>
  </div>
  <ul class="lb-reqs" id="lbReqs" hidden></ul>
  <div class="lb-foot">
    <span id="lbFile"></span>
    <a id="lbVerdict" href="#" hidden>verdict</a>
    <a class="right" id="lbRaw" href="#">Open raw file</a>
  </div>
</dialog>
```

- [ ] **Step 2: Add the styles**

```css
  .lb-head .pos { font-size: 13px; color: var(--ink-soft); }
  .lb-body { position: relative; }
  .lb-nav { position: absolute; top: 50%; transform: translateY(-50%); font: 28px/1 var(--f); width: 40px; height: 56px; border: 1px solid var(--ink); background: var(--paper); color: var(--ink); cursor: pointer; }
  .lb-nav.prev { left: 8px; } .lb-nav.next { right: 8px; }
  .lb-reqs { margin: 0; padding: 10px 16px; list-style: none; border-top: 1px solid var(--line); font-size: 13px; display: grid; gap: 4px; max-height: 32vh; overflow: auto; }
  .lb-reqs li { padding-left: 18px; position: relative; color: var(--ink-soft); }
  .lb-reqs li::before { position: absolute; left: 0; font-weight: 800; }
  .lb-reqs li.ok::before { content: "\2713"; color: var(--rig); }
  .lb-reqs li.ok { color: var(--ink); }
  .lb-reqs li.no::before { content: "\2717"; color: var(--ctl); }
  .lb-reqs li .why { display: block; font-size: 12px; }
```

- [ ] **Step 3: Replace the lightbox script**

Replace the block from `/* ---------------- lightbox ---------------- */` to the end of the script with:

```js
/* ---------------- lightbox ---------------- */
var lb = document.getElementById("lb"), lbImg = document.getElementById("lbImg"), lbTitle = document.getElementById("lbTitle"),
    lbFile = document.getElementById("lbFile"), lbRaw = document.getElementById("lbRaw"), lbPos = document.getElementById("lbPos"),
    lbPrev = document.getElementById("lbPrev"), lbNext = document.getElementById("lbNext"), lbReqs = document.getElementById("lbReqs"),
    lbVerdict = document.getElementById("lbVerdict");
var lbIndex = -1;

function openLb(src, alt, title) {
  lbIndex = -1;
  lbImg.src = src; lbImg.alt = alt; lbTitle.textContent = title;
  lbFile.textContent = src.replace(L + "logs/", ""); lbRaw.href = src;
  lbPos.textContent = ""; lbPrev.hidden = lbNext.hidden = true; lbReqs.hidden = true; lbVerdict.hidden = true;
  lb.showModal();
}
function openGalleryLb(i) {
  var x = GALLERY_FLAT[i]; if (!x) return;
  lbIndex = i;
  var src = L + x.file;
  lbImg.src = src; lbImg.alt = x.prompt + " · " + x.slug; lbTitle.textContent = x.model + " · " + x.slug;
  lbFile.textContent = x.file.replace("logs/", ""); lbRaw.href = src;
  lbPos.textContent = (i + 1) + " / " + GALLERY_FLAT.length + (x.score == null ? " · unscored" : " · " + x.met + "/" + x.total);
  lbPrev.hidden = i === 0; lbNext.hidden = i === GALLERY_FLAT.length - 1;
  lbReqs.replaceChildren();
  if (x.reqs.length) {
    x.reqs.forEach(function (r) {
      var li = el("li", r.m ? "ok" : "no", esc(r.t) + (r.m || !r.n ? "" : '<span class="why">' + esc(r.n) + "</span>"));
      lbReqs.appendChild(li);
    });
    lbReqs.hidden = false; lbVerdict.hidden = false; lbVerdict.href = L + x.verdict;
  } else { lbReqs.hidden = true; lbVerdict.hidden = true; }
  if (!lb.open) lb.showModal();
}
lbPrev.addEventListener("click", function () { openGalleryLb(lbIndex - 1); });
lbNext.addEventListener("click", function () { openGalleryLb(lbIndex + 1); });
lb.addEventListener("keydown", function (e) {
  if (lbIndex < 0) return;
  if (e.key === "ArrowLeft" && lbIndex > 0) openGalleryLb(lbIndex - 1);
  if (e.key === "ArrowRight" && lbIndex < GALLERY_FLAT.length - 1) openGalleryLb(lbIndex + 1);
});
document.getElementById("lbClose").addEventListener("click", function () { lb.close(); });
lb.addEventListener("click", function (e) { if (e.target === lb) lb.close(); });
```

Delete the Task 3 stub `function openGalleryLb(i) {...}`. The Q7 cards keep calling `openLb` and get no prev/next, as before.

- [ ] **Step 4: Verify in the browser**

Open the page at `#gallery`, click the first tile with `computer` (or call `openGalleryLb(0)` from `javascript_tool`), then read:

```js
({open: document.getElementById('lb').open, pos: document.getElementById('lbPos').textContent, reqs: document.querySelectorAll('#lbReqs li').length, fails: document.querySelectorAll('#lbReqs li.no').length, prevHidden: document.getElementById('lbPrev').hidden})
```

Expected: `open` true, `reqs` equals that artifact's `total`, `fails` equals `total - met`, `prevHidden` true. Call `openGalleryLb(1)` and confirm `pos` reads `2 / 89`. Press Escape; confirm `open` is false. Check `#h2hCols .proof button` still opens the dialog without the checklist.

- [ ] **Step 5: Commit**

```bash
git add reports/harness-matrix-svgbench.html
git commit -m "docs(reports): gallery lightbox with prev/next and the requirement checklist"
```

---

### Task 5: Wire the generator into the recipe and the docs

**Files:**
- Modify: `.claude/skills/svgbench-eval/SKILL.md` (recipe step 4)
- Modify: `bench/harness-matrix/plan.md` ("SVGBench scoring of the artifacts" bullets)
- Modify: `reports/README.md:11` (the dashboard row)
- Modify: `docs/superpowers/specs/2026-09-07-agent-comparison-site-design.md:485` (one sentence)

- [ ] **Step 1: Recipe**

In `SKILL.md` step 4, after the `score` sentence add: `Then `python3 scripts/svgbench/gallery_data.py` rewrites the gallery block of `reports/harness-matrix-svgbench.html`; `--check` reports whether it is stale.`

- [ ] **Step 2: Runbook**

In `plan.md`, add a bullet under "SVGBench scoring of the artifacts": `- Gallery: `scripts/svgbench/gallery_data.py` regenerates the `GALLERY` block in `reports/harness-matrix-svgbench.html` from `scores.json`. Run it after every `score`.`

- [ ] **Step 3: Reports index and spec**

`reports/README.md` row for `harness-matrix-svgbench.html`: append `, and a filterable gallery of all 89 SVGs with their scores` to the description. In the spec at line 485 replace `The gallery is deleted and the scoring dashboard is the single SVG page.` with `The standalone gallery is deleted; the scoring dashboard is the single SVG page and carries its own gallery section, generated from scores.json (plan: 2026-09-07-svgbench-gallery.md).`

- [ ] **Step 4: Final check and commit**

Run: `cd bench/harness-matrix && python3 tests/test_gallery_data.py && python3 tests/test_svgbench_eval.py && python3 scripts/svgbench/gallery_data.py --check`
Expected: all pass, `gallery block is fresh (89 items)`.

```bash
git add .claude/skills/svgbench-eval/SKILL.md bench/harness-matrix/plan.md reports/README.md docs/superpowers/specs/2026-09-07-agent-comparison-site-design.md
git commit -m "docs(svgbench): record the gallery generator in the recipe, runbook, and spec"
```

---

## Out of scope, deferred

- Generating the rest of `DATA` from `scores.json` (leaderboard, matrices, take series). Same marker pattern applies later.
- Copying `bench/harness-matrix/logs` and `results/svgbench` into the site build. The gallery uses the same `../bench/` paths as the Q7 cards, so it shares the existing publish gap noted in the site plan.
- Mobile screenshots: verify with `resize_window` preset `mobile` once the Browser pane is visible.
