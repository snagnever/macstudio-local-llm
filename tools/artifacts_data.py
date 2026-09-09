#!/usr/bin/env python3
"""Build the data block of reports/artifacts.html from the three campaigns' results.

Usage (from the repository root):
    python3 tools/artifacts_data.py            # rewrite the block in place
    python3 tools/artifacts_data.py --check    # exit 1 when the block is stale

Sources (existing results only; nothing here re-runs a benchmark or edits a score):
    bench/harness-matrix/results/svgbench/scores.json   -> drawings
    bench/agent-build-off/results/arms.json             -> game
    bench/layout-skill-bench/results/arms.json          -> skills

The block sits between `/* DATA:begin */` and `/* DATA:end */` inside the page's
<script>. Everything else in the file is untouched. Same contract as
bench/harness-matrix/scripts/svgbench/gallery_data.py.

Asset paths are written the way reports/harness-matrix-svgbench.html writes
them: `../bench/<campaign>/...`, which resolves from `file://.../reports/` and
is rewritten to `bench/<campaign>/...` by the publish workflow's sed rule.
Demo links are site-only (`demos/...`); they 404 when the page is opened
locally, which is why their labels say so.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCORES = os.path.join(ROOT, "bench", "harness-matrix", "results", "svgbench", "scores.json")
GAME_ARMS = os.path.join(ROOT, "bench", "agent-build-off", "results", "arms.json")
SKILL_ARMS = os.path.join(ROOT, "bench", "layout-skill-bench", "results", "arms.json")
HTML = os.path.join(ROOT, "reports", "artifacts.html")

BEGIN, END = "/* DATA:begin */", "/* DATA:end */"

# --- kept byte-identical to bench/harness-matrix/scripts/svgbench/gallery_data.py ---
PROMPT_LABEL = {0: "Cow plowing", 4: "Rubber ducky", 5: "Picnic on clouds", 6: "Stunt car",
                7: "Dolphin", 12: "Fruit stall", 13: "Treasure barrel"}
TAKE_RANK = {"v1": 0, "v2": 1, "v3": 2, "animated": 3}
_SUFFIX = re.compile(r"-(v1|v2|v3|animated)$")


def split_slug(slug):
    m = _SUFFIX.search(slug)
    if not m:
        return slug, "v1"
    return slug[: m.start()], m.group(1)
# --- end of the shared helpers ---

TAKE_LABEL = {"v1": "take 1", "v2": "take 2", "v3": "take 3", "animated": "animated take"}

# Contestant colours, from the design, and the page's legend reads them as who
# ran the artifact. Drawings and layout arms colour by model family; the
# build-off arms carry their own colour in arms.json and it already agrees.
MODEL_COLOR = (
    ("qwen", "#2a9d8f"),
    ("claude", "#e76f51"),
    ("fable", "#e76f51"),
    ("gpt-5.6-terra", "#5c6f8a"),
    ("codex", "#f4a261"),
)
FALLBACK_COLOR = "#4a4e49"

HARNESS_LABEL = {"opencode": "opencode", "claude": "Claude Code", "codex": "Codex"}

SVG_PREFIX = "../bench/harness-matrix/"
HARNESS_ROOT = os.path.join(ROOT, "bench", "harness-matrix")
PARTICIPANTS = os.path.join(HARNESS_ROOT, "results", "svgbench", "participants.json")
GAME_SHOTS = "../bench/agent-build-off/results/shots/"
GAME_CLIPS = "../bench/agent-build-off/results/clips/"
SKILL_SHOTS = "../bench/layout-skill-bench/results/shots/"

GAME_METRICS = [("wallMinutes", "Wall time", " min"), ("tokensOutput", "Output tokens", ""),
                ("sourceLines", "Source lines", ""), ("defectsFound", "Defects found", "")]
SKILL_METRICS = [("wallMinutes", "Wall time", " min"), ("tokensOutput", "Output tokens", "")]

ITERATIONS = [1, 2, 3, 4, 5]


class MarkerError(RuntimeError):
    """The HTML has no single DATA:begin/DATA:end pair."""


def color_for(model):
    m = model.lower()
    for needle, color in MODEL_COLOR:
        if needle in m:
            return color
    return FALLBACK_COLOR


def metric_text(value, unit=""):
    """A metric the campaign did not collect renders as an em dash, never as 0."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return ("yes" if value else "no") + unit
    if float(value) == int(value):
        return "{:,}".format(int(value)) + unit
    return "{:,.1f}".format(float(value)) + unit


def _cfg(config):
    """One participant row: who ran it, on what, at what thinking level.

    Every value comes from a results file. A level that file does not state
    stays None and the page prints "not recorded" — this campaign set records
    a reasoning effort for exactly one pair.
    """
    config = config or {}
    harness = config.get("harness") or ""
    if config.get("harnessVersion"):
        harness += " " + config["harnessVersion"]
    return {
        "harness": harness,
        "model": config.get("modelId") or "",
        "runtime": config.get("runtime") or "",
        "effort": config.get("effort") or "",
        "source": config.get("source") or "",
    }


def _extreme(arms, key, want_max, label, why=""):
    """The arm at one end of a metric, with the caveat its results file attaches.

    Returns None when no arm reports the metric, so a summary never invents a
    winner out of missing data.
    """
    rows = []
    for a in arms:
        m = next((x for x in a["metrics"] if x["key"] == key), None)
        if m and m.get("value") is not None:
            rows.append((a, m))
    if not rows:
        return None
    a, m = (max if want_max else min)(rows, key=lambda r: r[1]["value"])
    return {"label": label, "who": a.get("skillConfig") or a["label"],
            "value": m["text"], "note": m.get("note") or "", "why": why}


# ---------------------------------------------------------------- drawings

_VIEWBOX = re.compile(r'viewBox\s*=\s*"\s*([-\d.eE]+)[,\s]+([-\d.eE]+)[,\s]+([-\d.eE]+)[,\s]+([-\d.eE]+)\s*"')
_WH = re.compile(r'\b(width|height)\s*=\s*"\s*([\d.]+)\s*(?:px)?\s*"')
DEFAULT_ASPECT = 4 / 3


def aspect_of(svg_path):
    """The drawing's own width/height, so its frame matches the artwork exactly.

    A frame in a fixed ratio letterboxes every SVG that does not share it. Reads
    the viewBox first, falls back to width/height, and to 4:3 when neither
    parses. Only the file's head is read; the viewBox is in the root element.
    """
    try:
        with open(svg_path, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
    except OSError:
        return DEFAULT_ASPECT
    m = _VIEWBOX.search(head)
    if m:
        w, h = float(m.group(3)), float(m.group(4))
        if w > 0 and h > 0:
            return w / h
    dims = {k: float(v) for k, v in _WH.findall(head)}
    if dims.get("width", 0) > 0 and dims.get("height", 0) > 0:
        return dims["width"] / dims["height"]
    return DEFAULT_ASPECT


def judge_of(artifact):
    """The model that wrote this artifact's verdict, or "" when none is recorded."""
    j = artifact.get("judge") or {}
    return j.get("model") or ""


def build_drawings(scores):
    prompts = {q["question_index"]: q["prompt"] for q in scores.get("questions", [])}
    pairs = {}
    by_q = {}
    for a in scores["artifacts"]:
        q = a.get("question_index")
        if q is None:
            continue
        key = "%s/%s" % (a["harness"], a["model"])
        base, take = split_slug(a["slug"])
        p = pairs.setdefault(key, {
            "key": key, "harness": a["harness"], "model": a["model"],
            "label": a["model"], "harnessLabel": HARNESS_LABEL.get(a["harness"], a["harness"]),
            "color": color_for(a["model"]), "hosted": a["harness"] == "claude",
            "n": 0, "qs": [], "selfJudged": False,
        })
        p["n"] += 1
        if q not in p["qs"]:
            p["qs"].append(q)
        self_judged = judge_of(a) == a["model"]
        p["selfJudged"] = p["selfJudged"] or self_judged
        by_q.setdefault(q, []).append({
            "pair": key, "model": a["model"],
            "harnessLabel": HARNESS_LABEL.get(a["harness"], a["harness"]),
            "color": p["color"], "hosted": p["hosted"],
            "slug": a["slug"], "base": base, "take": take,
            "takeLabel": TAKE_LABEL[take],
            "file": SVG_PREFIX + a["artifact"],
            "aspect": round(aspect_of(os.path.join(HARNESS_ROOT, a["artifact"])), 4),
            "animated": bool(a.get("animated")),
            "selfJudged": self_judged,
            "score": a["score"], "met": a["met"], "total": a["total"],
            "reqs": [{"t": r["text"], "m": bool(r["met"]), "n": r.get("note", "")}
                     for r in a["requirements"]],
            "best": False, "last": False,
        })

    # Reading order, not question-bank order: the two drawings every pair
    # attempted lead, then the questions with the most models to compare.
    LEAD = [7, 0]

    def question_order(q):
        if q in LEAD:
            return (0, LEAD.index(q), 0)
        return (1, -len({t["pair"] for t in by_q[q]}), q)

    questions = []
    for q in sorted(by_q, key=question_order):
        takes = by_q[q]
        takes.sort(key=lambda t: (t["pair"], TAKE_RANK[t["take"]]))
        for key in {t["pair"] for t in takes}:
            mine = [t for t in takes if t["pair"] == key]
            best = min(mine, key=lambda t: (-t["score"], TAKE_RANK[t["take"]]))
            best["best"] = True
            # the take the pair ended on, and an animated one wins over a still:
            # TAKE_RANK already ends at "animated", so the highest rank is it
            last = max(mine, key=lambda t: (t["animated"], TAKE_RANK[t["take"]]))
            last["last"] = True
        questions.append({
            "q": q,
            "label": PROMPT_LABEL.get(q, "Question %d" % q),
            "prompt": prompts.get(q, ""),
            "takes": takes,
        })

    for p in pairs.values():
        p["qs"].sort()

    # Who wrote the verdicts, and how many of them are on its own drawings. The
    # page says this next to the scores; harness-matrix-svgbench.html says it too.
    judges = {judge_of(a) for a in scores["artifacts"] if a.get("question_index") is not None}
    judges.discard("")

    # Who ran each pair, and the mean it scored. The means cover different
    # question sets, which the summary says rather than hiding.
    cfgs = {}
    try:
        with open(PARTICIPANTS, "r", encoding="utf-8") as fh:
            cfgs = {c["key"]: c for c in json.load(fh)["pairs"]}
    except (OSError, ValueError, KeyError):
        cfgs = {}
    means = {"%s/%s" % (p["harness"], p["model"]): p for p in scores.get("pairs", [])}
    roster = []
    for p in sorted(pairs.values(), key=lambda p: (p["hosted"], p["key"])):
        m = means.get(p["key"], {})
        row = dict(_cfg(cfgs.get(p["key"])))
        row.update({
            "key": p["key"], "label": p["model"], "color": p["color"],
            "hosted": p["hosted"], "n": m.get("artifacts_scored"),
            "mean": round(m["mean_score"], 3) if m.get("mean_score") is not None else None,
            "selfJudged": p["selfJudged"],
        })
        roster.append(row)

    scored = [r for r in roster if r["mean"] is not None]
    summary, summary_note = [], ""
    if len(scored) > 1:
        def row(r, label):
            return {"label": label, "who": r["label"], "value": "%.3f" % r["mean"],
                    "note": "over %d drawing%s" % (r["n"], "" if r["n"] == 1 else "s"),
                    "why": ("it judged its own drawings" if r["selfJudged"] else "")}
        summary = [row(max(scored, key=lambda r: r["mean"]), "Highest mean"),
                   row(min(scored, key=lambda r: r["mean"]), "Lowest mean")]
        # The means are not a ranking and the page must not let them read as one:
        # each pair attempted a different set of questions, and the counts run
        # from one drawing to twenty-eight.
        ns = sorted(r["n"] for r in scored)
        summary_note = (
            "These two are the ends of the scale, not a ranking. Each pair attempted a "
            "different set of questions, and the counts behind the means run from %d "
            "drawing to %d, so a high mean over a handful is not a better model than a "
            "lower mean over many." % (ns[0], ns[-1])
        )

    return {
        "questions": questions,
        "pairs": sorted(pairs.values(), key=lambda p: (p["hosted"], p["key"])),
        "roster": roster,
        "summary": summary,
        "summaryNote": summary_note,
        "judge": {
            "model": sorted(judges)[0] if len(judges) == 1 else "",
            "selfJudged": sum(1 for q in questions for t in q["takes"] if t["selfJudged"]),
        },
    }


# ------------------------------------------------------------- arms shared

def _metrics(results, arm_id, defs):
    rows = {r["metric"]: r for r in results if r["arm"] == arm_id}
    out = []
    for key, label, unit in defs:
        r = rows.get(key, {})
        value = r.get("value")
        out.append({"key": key, "label": label, "value": value,
                    "text": metric_text(value, unit), "note": r.get("note") or ""})
    return out


def build_game(arms):
    out = []
    for a in arms["arms"]:
        out.append({
            "id": a["id"], "label": a["label"], "harness": a["harness"], "model": a["model"],
            "hosted": bool(a["hosted"]), "color": a.get("color", FALLBACK_COLOR),
            "shot": GAME_SHOTS + a["id"] + ".webp",
            # A 60 fps loop of the start screen, when one was recorded. The page
            # plays it over the still and falls back to the still without it.
            "clip": (GAME_CLIPS + a["id"] + ".mp4"
                     if os.path.exists(os.path.join(ROOT, "bench", "agent-build-off",
                                                    "results", "clips", a["id"] + ".mp4"))
                     else ""),
            "demo": "demos/build-off/%s/" % a["id"],
            "note": a.get("multiModelNote") or "",
            "metrics": _metrics(arms["results"], a["id"], GAME_METRICS),
        })
        out[-1].update(_cfg(a.get("config")))
    # No quality score exists for this campaign, so the summary names the ends
    # of each measured run instead of declaring a winner.
    summary = [x for x in (
        _extreme(out, "wallMinutes", False, "Shortest run"),
        _extreme(out, "wallMinutes", True, "Longest run"),
        _extreme(out, "tokensOutput", True, "Most output tokens"),
        _extreme(out, "sourceLines", True, "Most source shipped"),
        _extreme(out, "defectsFound", True, "Most defects caught in its own work"),
    ) if x]
    return {"brief": arms.get("brief", ""), "arms": out, "summary": summary}


# Per-arm page URL rule, copied verbatim from reports/layout-skill-bench.html.
def page_for(arm_id, n):
    if arm_id == "design-skill":
        return "demos/layout/design-skill/%s/" % n
    if arm_id == "taste-skill":
        return "demos/layout/taste-skill/%s" % n
    return "demos/layout/taste2/%s.html" % n              # taste2


def build_skills(arms):
    out = []
    for a in arms["arms"]:
        out.append({
            "id": a["id"], "label": a["label"], "skillConfig": a["skillConfig"],
            "harness": a["harness"], "model": a["model"], "hosted": bool(a["hosted"]),
            # The colour line on this page means who ran it, so it comes from the
            # model, not from the arm's own series colour. All three skill arms are
            # the same local model, so all three share the Qwen colour; the skill
            # name is the cell title and tells the arms apart.
            "color": color_for(a["model"]), "form": a.get("form", ""),
            "shots": [{"n": n, "src": "%s%s-%d.webp" % (SKILL_SHOTS, a["id"], n),
                       "page": page_for(a["id"], n)} for n in ITERATIONS],
            "metrics": _metrics(arms["results"], a["id"], SKILL_METRICS),
        })
        out[-1].update(_cfg(a.get("config")))
    # This campaign scored nothing: it varied one skill and kept everything else
    # fixed, so the summary reports cost, and says the quality call is the eye's.
    summary = [x for x in (
        _extreme(out, "wallMinutes", False, "Fastest session"),
        _extreme(out, "wallMinutes", True, "Longest session"),
        _extreme(out, "tokensOutput", True, "Most output tokens"),
    ) if x]
    return {"brief": arms.get("brief", ""), "arms": out, "summary": summary}


# ------------------------------------------------------------------ block

def build_all(scores, game, skills):
    return {
        "generated_at": datetime.date.today().isoformat(),
        "drawings": build_drawings(scores),
        "game": build_game(game),
        "skills": build_skills(skills),
    }


def render_block(data):
    return "%s\nvar DATA = %s;\n%s" % (
        BEGIN, json.dumps(data, ensure_ascii=False, separators=(", ", ": "), allow_nan=False), END)


def write_block(html_path, data):
    with open(html_path, encoding="utf-8") as f:
        src = f.read()
    if src.count(BEGIN) != 1 or src.count(END) != 1:
        raise MarkerError("expected exactly one %s / %s pair in %s" % (BEGIN, END, html_path))
    head, rest = src.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    out = head + render_block(data) + tail
    if out != src:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(out)
    return out != src


def _same_but_for_the_date(block, src):
    """generated_at moves with the clock; the numbers are what staleness means."""
    strip = re.compile(r'"generated_at": "[^"]*"')
    m = re.search(re.escape(BEGIN) + r"(.*?)" + re.escape(END), src, re.S)
    if not m:
        return False
    return strip.sub("", block) == strip.sub("", BEGIN + m.group(1) + END)


def check_block(html_path, data):
    with open(html_path, encoding="utf-8") as f:
        src = f.read()
    return 0 if _same_but_for_the_date(render_block(data), src) else 1


def _load():
    with open(SCORES, encoding="utf-8") as f:
        scores = json.load(f)
    with open(GAME_ARMS, encoding="utf-8") as f:
        game = json.load(f)
    with open(SKILL_ARMS, encoding="utf-8") as f:
        skills = json.load(f)
    return build_all(scores, game, skills)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when the block differs from the results files")
    args = ap.parse_args(argv)
    data = _load()
    counts = (sum(len(q["takes"]) for q in data["drawings"]["questions"]),
              len(data["drawings"]["questions"]), len(data["game"]["arms"]),
              len(data["skills"]["arms"]))
    tally = "%d drawings over %d prompts, %d game arms, %d skill arms" % counts
    if args.check:
        stale = check_block(HTML, data)
        print("artifacts data block is %s (%s)" % ("STALE" if stale else "fresh", tally))
        return stale
    changed = write_block(HTML, data)
    print("artifacts data block %s: %s" % ("rewritten" if changed else "unchanged", tally))
    return 0


if __name__ == "__main__":
    sys.exit(main())
