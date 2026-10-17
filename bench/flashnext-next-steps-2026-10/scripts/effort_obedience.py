#!/usr/bin/env python3
"""Does an arm follow reasoning_effort the way a base arm does? Paired per-question test on battery JSONL.

For each effort, each question (``dataset_idx``) gets the mean over rounds of log(reasoning_tokens) in each arm.
``shift(effort)`` is the mean over questions of (cand - base), with a bootstrap CI over questions. exp(shift) is
the factor of reasoning the candidate spends against the base at the same effort. ``medium`` renders the same
prompt in both arms of the effort-tail test, so its shift is an A/A test: it shows the noise of rounds and server
sessions. The candidate follows the effort when the CI of the shift at ``xhigh`` and at ``low`` lies within
+-``--margin`` (log units; 0.223 = a factor of 1.25). The output also prints, per arm, the low/xhigh and
medium/xhigh factors.

Layout: <root>/<arm>-<effort>-<round>/<suite>.jsonl, one root per arm (symlinks work).
usage: effort_obedience.py --base-root DIR --cand-root DIR [--base w1] [--cand w1t] [--rounds r1,r2]
                           [--suites gpqa,livecodebench] [--margin 0.223] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

EFFORTS = ("xhigh", "medium", "low")
BOOT = 4000
SEED = 7


def _tokens(row: dict) -> int | None:
    for key in ("reasoning_tokens", "completion_tokens"):
        v = row.get(key)
        if v not in (None, "", "None"):
            return int(float(v))
    return None


def load(root: Path, arm: str, effort: str, rounds: list[str], suites: list[str]) -> dict[str, float]:
    """Mean log(reasoning tokens) per question id ("<suite>:<dataset_idx>"), over the rounds that have it."""
    acc: dict[str, list[float]] = {}
    for r in rounds:
        for s in suites:
            path = root / f"{arm}-{effort}-{r}" / f"{s}.jsonl"
            if not path.exists():
                raise FileNotFoundError(path)
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                t = _tokens(row)
                if t is None or row.get("error") not in (None, "", "None"):
                    continue
                acc.setdefault(f"{s}:{row['dataset_idx']}", []).append(math.log(max(t, 1)))
    return {q: sum(v) / len(v) for q, v in acc.items()}


def mean_ci(diffs: list[float], level: float = 0.90) -> tuple[float, float, float]:
    rng = random.Random(SEED)
    n = len(diffs)
    means = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(BOOT))
    lo, hi = means[int((1 - level) / 2 * BOOT)], means[int((1 + level) / 2 * BOOT) - 1]
    return sum(diffs) / n, lo, hi


def paired(a: dict[str, float], b: dict[str, float]) -> list[float]:
    return [b[q] - a[q] for q in sorted(a.keys() & b.keys())]


def analyse(base_root: Path, cand_root: Path, base: str, cand: str, rounds: list[str], suites: list[str],
            margin: float) -> dict:
    data = {arm: {e: load(root, arm, e, rounds, suites) for e in EFFORTS}
            for arm, root in ((base, base_root), (cand, cand_root))}
    out: dict = {"base": base, "cand": cand, "rounds": rounds, "suites": suites, "margin": margin,
                 "shift": {}, "factor": {}}
    for e in EFFORTS:
        d = paired(data[base][e], data[cand][e])
        m, lo, hi = mean_ci(d)
        out["shift"][e] = {"n": len(d), "mean": m, "lo": lo, "hi": hi}
    for arm in (base, cand):
        out["factor"][arm] = {}
        for e in ("medium", "low"):
            m, lo, hi = mean_ci(paired(data[arm]["xhigh"], data[arm][e]))
            out["factor"][arm][e] = {"mean": math.exp(m), "lo": math.exp(lo), "hi": math.exp(hi)}
    out["follows"] = all(-margin <= out["shift"][e]["lo"] and out["shift"][e]["hi"] <= margin for e in ("xhigh", "low"))
    return out


def render(res: dict) -> str:
    b, c = res["base"], res["cand"]
    lines = [f"| effort | questões | reasoning `{c}` / `{b}` (IC 90%) | dentro de ×{math.exp(res['margin']):.2f}? |",
             "|---|---:|---|---|"]
    for e in EFFORTS:
        s = res["shift"][e]
        inside = -res["margin"] <= s["lo"] and s["hi"] <= res["margin"]
        tag = " (A/A)" if e == "medium" else ""
        lines.append(f"| {e}{tag} | {s['n']} | ×{math.exp(s['mean']):.2f} ({math.exp(s['lo']):.2f}–{math.exp(s['hi']):.2f}) "
                     f"| {'sim' if inside else 'não'} |")
    lines += ["", "| braço | medium / xhigh (IC 90%) | low / xhigh (IC 90%) |", "|---|---|---|"]
    for arm in (b, c):
        f = res["factor"][arm]
        lines.append(f"| {arm} | ×{f['medium']['mean']:.2f} ({f['medium']['lo']:.2f}–{f['medium']['hi']:.2f}) "
                     f"| ×{f['low']['mean']:.2f} ({f['low']['lo']:.2f}–{f['low']['hi']:.2f}) |")
    lines += ["", f"OBEDIENCE: {'pass' if res['follows'] else 'fail'} (xhigh e low dentro de ×{math.exp(-res['margin']):.2f}–"
              f"×{math.exp(res['margin']):.2f}; suítes {', '.join(res['suites'])}; rodadas {', '.join(res['rounds'])})"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-root", type=Path, required=True)
    ap.add_argument("--cand-root", type=Path, required=True)
    ap.add_argument("--base", default="w1")
    ap.add_argument("--cand", default="w1t")
    ap.add_argument("--rounds", default="r1,r2")
    ap.add_argument("--suites", default="gpqa,livecodebench")
    ap.add_argument("--margin", type=float, default=0.223, help="log units; 0.223 = factor 1.25")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    try:
        res = analyse(a.base_root, a.cand_root, a.base, a.cand, a.rounds.split(","), a.suites.split(","), a.margin)
    except FileNotFoundError as error:
        print(f"effort_obedience: missing {error}", file=sys.stderr)
        return 66
    print(render(res))
    if a.json:
        a.json.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    return 0 if res["follows"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
