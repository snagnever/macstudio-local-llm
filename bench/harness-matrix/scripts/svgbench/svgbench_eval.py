#!/usr/bin/env python3
"""Score harness-matrix SVG artifacts against SVGBench requirements.

Stdlib only. Subcommands (run from the repo root or anywhere):

  manifest   discover logs/<harness>/<model>/**/*.svg, match each to an SVGBench
             question by filename slug, write results/svgbench/manifest.json
             (existing question_index overrides are kept)
  render     rasterize every manifest artifact with headless Chrome to
             logs/renders/<harness>/<model>/<slug>.png (same method as SVGBench)
  judge      optional: ask an OpenAI-compatible vision endpoint for per-requirement
             verdicts (SVGBENCH_JUDGE_URL / _MODEL / _KEY); writes verdict files
  score      merge verdict files into results/svgbench/scores.json

Verdict file: results/svgbench/verdicts/<harness>/<model>/<slug>.json
  {"artifact": ..., "question_index": N, "judge": {...},
   "requirements": [{"text": ..., "met": bool, "note": ...}, ...]}
The score of one artifact is met / total, the SVGBench metric.
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN = os.path.abspath(os.path.join(HERE, "..", ".."))
QUESTIONS_PATH = os.path.join(HERE, "questions.json")
QUESTIONS_META_PATH = os.path.join(HERE, "questions.meta.json")
MANIFEST_REL = "results/svgbench/manifest.json"
VERDICTS_REL = "results/svgbench/verdicts"
SCORES_REL = "results/svgbench/scores.json"
RENDERS_REL = "logs/renders"
CHROME = os.environ.get(
    "SVGBENCH_CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

SLUG_NOISE = {"animated", "anim", "final", "draft", "copy", "on", "of", "the", "a", "in", "at"}
STOP_WORDS = {"write", "svg", "code", "for", "an", "image", "of", "a", "the", "to", "draw",
              "and", "with", "on", "in", "at", "its", "out", "top", "screenshot"}


class StaleVerdict(Exception):
    """A verdict's requirement texts no longer match the pinned question."""


# ---------- matching ----------

def _prompt_words(prompt):
    return [w for w in re.findall(r"[a-z]+", prompt.lower()) if w not in STOP_WORDS]


def _slug_tokens(slug):
    toks = re.split(r"[-_]+", slug.lower())
    return [t for t in toks if t and t not in SLUG_NOISE and not re.fullmatch(r"v?\d+", t)]


def match_question(slug, questions):
    """Return the index of the single question whose prompt contains every slug token.

    A slug token matches a prompt word by prefix in either direction (plow/plowing,
    jump/jumping). Zero or several candidates -> None (off-benchmark or ambiguous).
    """
    toks = _slug_tokens(slug)
    if not toks:
        return None
    hits = []
    for i, q in enumerate(questions):
        words = _prompt_words(q["prompt"])
        if all(any(w.startswith(t) or t.startswith(w) for w in words if len(w) >= 3)
               for t in toks):
            hits.append(i)
    return hits[0] if len(hits) == 1 else None


# ---------- discovery ----------

def discover(campaign_root):
    """Return ([(harness, model, rel_svg_path)], [stray rel paths]) under logs/."""
    logs = os.path.join(campaign_root, "logs")
    found, strays = [], []
    for dirpath, dirnames, filenames in os.walk(logs):
        dirnames[:] = sorted(d for d in dirnames if d != "renders")
        for fn in sorted(filenames):
            if not fn.lower().endswith(".svg"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), campaign_root)
            parts = rel.split(os.sep)
            if len(parts) >= 4:  # logs/<harness>/<model>/.../x.svg
                found.append((parts[1], parts[2], rel))
            else:
                strays.append(rel)
    return sorted(found), sorted(strays)


def slug_of(rel_path):
    return os.path.splitext(os.path.basename(rel_path))[0]


def is_animated(svg_text):
    return bool(re.search(r"<animate|<set\b|animateTransform|animateMotion|@keyframes", svg_text))


def load_questions():
    with open(QUESTIONS_PATH) as f:
        return json.load(f)


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def cmd_manifest(args):
    questions = load_questions()
    path = os.path.join(CAMPAIGN, MANIFEST_REL)
    previous = {a["artifact"]: a for a in load_json(path, {}).get("artifacts", [])}
    found, strays = discover(CAMPAIGN)
    artifacts = []
    for harness, model, rel in found:
        with open(os.path.join(CAMPAIGN, rel)) as f:
            text = f.read()
        entry = {
            "harness": harness, "model": model, "artifact": rel, "slug": slug_of(rel),
            "question_index": match_question(slug_of(rel), questions),
            "animated": is_animated(text), "bytes": len(text.encode()),
        }
        old = previous.get(rel)
        if old and old.get("question_index_override") is not None:
            entry["question_index"] = old["question_index_override"]
            entry["question_index_override"] = old["question_index_override"]
        artifacts.append(entry)
    write_json(path, {"generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                      "artifacts": artifacts, "strays": strays})
    for a in artifacts:
        print(f"{a['artifact']:70} -> q{a['question_index']}"
              f"{' (animated)' if a['animated'] else ''}")
    for s in strays:
        print(f"STRAY (no harness/model dir, not scored): {s}")
    print(f"wrote {MANIFEST_REL}: {len(artifacts)} artifacts, {len(strays)} strays")


# ---------- rendering ----------

def _dim(v):
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(px)?\s*$", v or "")
    return int(float(m.group(1))) if m else None


def svg_dimensions(svg_text):
    """(width, height) the way SVGBench picks them: attributes, else viewBox, else 800x600."""
    try:
        root = ET.fromstring(svg_text.strip())
    except ET.ParseError:
        return (800, 600)
    w, h = _dim(root.get("width")), _dim(root.get("height"))
    if w and h:
        return (w, h)
    vb = (root.get("viewBox") or "").split()
    if len(vb) >= 4:
        try:
            return (max(int(float(vb[2])), 200), max(int(float(vb[3])), 200))
        except ValueError:
            pass
    return (800, 600)


def render_svg(svg_path, png_path, chrome=CHROME):
    with open(svg_path) as f:
        w, h = svg_dimensions(f.read())
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", f"--window-size={w},{h}",
           f"--screenshot={png_path}", "file://" + os.path.abspath(svg_path)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return (w, h)


def render_rel(entry):
    return f"{RENDERS_REL}/{entry['harness']}/{entry['model']}/{entry['slug']}.png"


def cmd_render(args):
    manifest = load_json(os.path.join(CAMPAIGN, MANIFEST_REL), None)
    if manifest is None:
        sys.exit("run `manifest` first")
    for entry in manifest["artifacts"]:
        if args.only and args.only not in entry["artifact"]:
            continue
        png = os.path.join(CAMPAIGN, render_rel(entry))
        w, h = render_svg(os.path.join(CAMPAIGN, entry["artifact"]), png)
        print(f"{entry['artifact']} -> {render_rel(entry)} ({w}x{h})")


# ---------- judging (optional LLM path) ----------

def verdict_rel(entry):
    return f"{VERDICTS_REL}/{entry['harness']}/{entry['model']}/{entry['slug']}.json"


JUDGE_PROMPT = """Examine the generated image. For each of the {n} requirements below, decide
strictly whether the image fulfils it. Respond with JSON only:
{{"requirements": [{{"index": 1, "met": true|false, "note": "<one short reason>"}}, ...]}}

Requirements:
{reqs}
"""


def llm_judge(png_path, requirements, url, model, key):
    with open(png_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    reqs = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(requirements))
    body = {"model": model, "temperature": 0,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": JUDGE_PROMPT.format(n=len(requirements), reqs=reqs)},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}]}
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        content = json.load(resp)["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", content, re.S)
    parsed = json.loads(m.group(0))["requirements"]
    by_idx = {int(p["index"]): p for p in parsed}
    return [{"text": r, "met": bool(by_idx[i + 1]["met"]), "note": by_idx[i + 1].get("note", "")}
            for i, r in enumerate(requirements)]


def cmd_judge(args):
    url = os.environ.get("SVGBENCH_JUDGE_URL")
    model = os.environ.get("SVGBENCH_JUDGE_MODEL")
    key = os.environ.get("SVGBENCH_JUDGE_KEY", "none")
    if not (url and model):
        sys.exit("set SVGBENCH_JUDGE_URL and SVGBENCH_JUDGE_MODEL (OpenAI-compatible vision endpoint)")
    questions = load_questions()
    manifest = load_json(os.path.join(CAMPAIGN, MANIFEST_REL), None)
    if manifest is None:
        sys.exit("run `manifest` first")
    for entry in manifest["artifacts"]:
        if entry["question_index"] is None or (args.only and args.only not in entry["artifact"]):
            continue
        out = os.path.join(CAMPAIGN, verdict_rel(entry))
        if os.path.exists(out) and not args.force:
            print(f"keep {verdict_rel(entry)}")
            continue
        png = os.path.join(CAMPAIGN, render_rel(entry))
        if not os.path.exists(png):
            sys.exit(f"missing render {render_rel(entry)}; run `render` first")
        reqs = questions[entry["question_index"]]["requirements"]
        verdict = {
            "artifact": entry["artifact"], "question_index": entry["question_index"],
            "render": render_rel(entry),
            "judge": {"kind": "llm", "model": model, "endpoint": url,
                      "date": dt.date.today().isoformat()},
            "requirements": llm_judge(png, reqs, url, model, key),
        }
        write_json(out, verdict)
        print(f"{entry['artifact']}: {score_verdict(verdict):.3f} -> {verdict_rel(entry)}")


# ---------- scoring ----------

def score_verdict(verdict):
    reqs = verdict["requirements"]
    return sum(1 for r in reqs if r["met"]) / len(reqs)


def check_verdict(verdict, questions):
    q = questions[verdict["question_index"]]
    texts = [r["text"] for r in verdict["requirements"]]
    if texts != q["requirements"]:
        raise StaleVerdict(f"{verdict['artifact']}: requirement texts differ from pinned "
                           f"question {verdict['question_index']}; re-judge it")


def build_scores(manifest, verdicts, questions, meta=None):
    """Assemble the display JSON from the manifest and {artifact: verdict}."""
    artifacts, unscored = [], []
    for entry in manifest["artifacts"]:
        base = {k: entry[k] for k in ("harness", "model", "artifact", "question_index", "animated")}
        base["slug"] = entry.get("slug", slug_of(entry["artifact"]))
        if entry["question_index"] is None:
            unscored.append({**base, "reason": "prompt is not an SVGBench question"})
            continue
        v = verdicts.get(entry["artifact"])
        if v is None:
            unscored.append({**base, "reason": "no verdict file"})
            continue
        check_verdict(v, questions)
        q = questions[entry["question_index"]]
        met = sum(1 for r in v["requirements"] if r["met"])
        artifacts.append({
            **base, "prompt": q["prompt"], "score": met / len(q["requirements"]),
            "met": met, "total": len(q["requirements"]), "judge": v.get("judge", {}),
            "render": v.get("render"), "requirements": v["requirements"],
        })

    pairs = {}
    for a in artifacts:
        p = pairs.setdefault((a["harness"], a["model"]), {
            "harness": a["harness"], "model": a["model"], "artifacts_scored": 0,
            "mean_score": 0.0, "by_question": {}})
        p["artifacts_scored"] += 1
        p["by_question"].setdefault(str(a["question_index"]), []).append(a["score"])
    pair_list = []
    for p in pairs.values():
        scores = [s for v in p["by_question"].values() for s in v]
        p["mean_score"] = sum(scores) / len(scores)
        p["by_question"] = {k: sum(v) / len(v) for k, v in sorted(p["by_question"].items(),
                                                                 key=lambda kv: int(kv[0]))}
        pair_list.append(p)
    pair_list.sort(key=lambda p: -p["mean_score"])

    q_idx = sorted({a["question_index"] for a in artifacts})
    question_list = [{
        "question_index": i, "prompt": questions[i]["prompt"],
        "n_requirements": len(questions[i]["requirements"]),
        "requirements": questions[i]["requirements"],
        "artifacts": [a["artifact"] for a in artifacts if a["question_index"] == i],
    } for i in q_idx]

    return {
        "benchmark": {
            "name": "SVGBench",
            "source": "https://github.com/johnbean393/SVGBench",
            "questions": meta or {},
            "scoring": "score = requirements met / requirements total, judged on the "
                       "Chrome-rendered PNG; pair mean_score = mean over scored artifacts",
            "comparability": "subset of the 105 questions; artifacts came from coding harnesses, "
                             "not the SVGBench direct-API run; judge differs from SVGBench's "
                             "gemini-2.5-flash. Not comparable to the upstream leaderboard.",
        },
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "pairs": pair_list,
        "artifacts": artifacts,
        "questions": question_list,
        "unscored": unscored,
        "skipped": [{"path": s, "reason": "no harness/model directory (see AGENTS.md)"}
                    for s in manifest.get("strays", [])],
    }


def cmd_score(args):
    questions = load_questions()
    manifest = load_json(os.path.join(CAMPAIGN, MANIFEST_REL), None)
    if manifest is None:
        sys.exit("run `manifest` first")
    verdicts = {}
    for entry in manifest["artifacts"]:
        p = os.path.join(CAMPAIGN, verdict_rel(entry))
        if os.path.exists(p):
            verdicts[entry["artifact"]] = load_json(p, None)
    out = build_scores(manifest, verdicts, questions, load_json(QUESTIONS_META_PATH, {}))
    write_json(os.path.join(CAMPAIGN, SCORES_REL), out)
    for p in out["pairs"]:
        print(f"{p['harness']:10} {p['model']:24} {p['mean_score']:.3f} "
              f"({p['artifacts_scored']} artifacts) {p['by_question']}")
    for u in out["unscored"]:
        print(f"unscored {u['artifact']}: {u['reason']}")
    print(f"wrote {SCORES_REL}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest").set_defaults(fn=cmd_manifest)
    r = sub.add_parser("render"); r.add_argument("--only", help="substring filter on artifact path")
    r.set_defaults(fn=cmd_render)
    j = sub.add_parser("judge"); j.add_argument("--only"); j.add_argument("--force", action="store_true")
    j.set_defaults(fn=cmd_judge)
    sub.add_parser("score").set_defaults(fn=cmd_score)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
