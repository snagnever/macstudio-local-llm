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
        "prompt": PROMPT_LABEL.get(q, base) if q is not None else UNSCORED_LABEL.get(base, base),
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
    with open(html_path, encoding="utf-8") as f:
        src = f.read()
    if src.count(BEGIN) != 1 or src.count(END) != 1:
        raise MarkerError("expected exactly one %s / %s pair in %s" % (BEGIN, END, html_path))
    head, rest = src.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    out = head + render_block(items) + tail
    if out != src:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(out)
    return out != src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 when the block differs from scores.json")
    args = ap.parse_args(argv)
    with open(SCORES, encoding="utf-8") as f:
        items = build_items(json.load(f))
    if args.check:
        with open(HTML, encoding="utf-8") as f:
            src = f.read()
        stale = render_block(items) not in src
        print("gallery block is %s (%d items)" % ("STALE" if stale else "fresh", len(items)))
        return 1 if stale else 0
    changed = write_block(HTML, items)
    print("gallery block %s: %d items" % ("rewritten" if changed else "unchanged", len(items)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
