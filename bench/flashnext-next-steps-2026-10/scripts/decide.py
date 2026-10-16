#!/usr/bin/env python3
"""Campaign table and decision for T_turno arms, on top of summarize_driver.py.

Reads the cache_probe JSONL files that match the globs, groups them by (arm, context) with
summarize_driver.summarize (same medians, same T_turno, same gates), and prints:

  1. the fixed table of the campaign:
     braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles
     (warm TTFT = median TTFT of tool_turn; hit = append / tool_turn; needles = correct/records, with the
     records truncated at max_tokens and the wrong answers in parentheses: a truncation is not a needle failure)
  2. a memory line per row (minimum free memory from mem-sampler);
  3. with --base and --cand, the ratio T_turno(cand) / T_turno(base) per context and a verdict line:
       --mode le      pass when ratio <= --threshold at every context (adoption 0.97, condition 1.03, ple 0.95)
       --mode parity  pass when |ratio - 1| <= --threshold at every context (weights rule 0.03)
     The verdict also needs: every gate of summarize_driver passing for the candidate at every context, and,
     for mlx-serve arms, at least one "[spec-stats]" line in the boot log of the run (logs/<run>-boot.log).
     The last line is "VERDICT: pass" or "VERDICT: fail (<reasons>)".
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "bench" / "qwen38-flashnext-daily-driver-2026-09" / "scripts"))
from summarize_driver import summarize  # noqa: E402

HEADER = ("| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ "
          "| HTTP errs | needles |")


def load(results_dir: Path, globs: list[str]) -> tuple[list[dict], dict[tuple, set]]:
    records, runs = [], {}
    for g in globs:
        for f in sorted(glob.glob(str(results_dir / g))):
            for line in Path(f).read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    records.append(r)
                    runs.setdefault((r["arm"], int(r["context_target"])), set()).add(Path(f).stem)
    return records, runs


def fmt(v, digits=1, unit=""):
    return "—" if v is None else f"{v:.{digits}f}{unit}"


def spec_stats_ok(logs_dir: Path, runs: set) -> bool:
    for stem in runs:
        boot = logs_dir / f"{stem}-boot.log"
        if boot.is_file() and "[spec-stats]" in boot.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def table(records: list[dict], runs: dict) -> tuple[str, dict]:
    summary = summarize(records)
    needles, free_min, runtime = {}, {}, {}
    for r in records:
        key = (r["arm"], int(r["context_target"]))
        ok, n, t, w = needles.get(key, (0, 0, 0, 0))
        trunc = not r.get("correct") and r.get("finish_reason") == "length"
        wrong = not r.get("correct") and not trunc
        needles[key] = (ok + (1 if r.get("correct") else 0), n + 1, t + (1 if trunc else 0), w + (1 if wrong else 0))
        if r.get("mem_free_min_gb") is not None:
            free_min[key] = min(free_min.get(key, 1e9), r["mem_free_min_gb"])
        runtime[key] = r.get("runtime")
    lines = [HEADER, "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|"]
    for (arm, ctx), s in sorted(summary.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        h = s["hit"]
        hit = "/".join("—" if h.get(k) is None else f"{h[k]:.2f}" for k in ("append", "tool_turn"))
        ok, n, t, w = needles[(arm, ctx)]
        notes = ", ".join(x for x in (f"{t} trunc" if t else "", f"{w} erro" if w else "") if x)
        lines.append(f"| {arm} | {ctx // 1024}K | {fmt(s['t_turno_s'], 1, ' s')} | {fmt(s['cold_ttft_s'], 1, ' s')} | "
                     f"{fmt(s['warm_ttft_s'].get('tool_turn'), 2, ' s')} | {hit} | {fmt(s['decode_tps'])} | "
                     f"{fmt(s['mtp_acceptance'], 3)} | {fmt(s['wired_peak_gb'], 1, ' GB')} | "
                     f"{fmt(s['swap_delta_gb'], 2, ' GB')} | {s['errors']} | {ok}/{n}{f' ({notes})' if notes else ''} |")
    lines.append("")
    for key in sorted(summary, key=lambda k: (k[1], k[0])):
        s = summary[key]
        lines.append(f"- {key[0]} @ {key[1] // 1024}K: livre mínimo {fmt(free_min.get(key), 2, ' GB')}; "
                     f"gates {', '.join(s['gates_failed']) or 'passa'}; alertas {', '.join(s.get('warnings') or []) or '—'}")
    return "\n".join(lines), {"summary": summary, "runtime": runtime}


def decide(summary: dict, runtime: dict, runs: dict, logs_dir: Path, base: str, cand: str,
           ctxs: list[int], mode: str, threshold: float,
           skip: frozenset | set = frozenset()) -> tuple[str, bool]:
    lines = ["", f"| razão `T_turno({cand}) / T_turno({base})` | " + " | ".join(f"{c // 1024}K" for c in ctxs) + " |",
             "|---|" + "---:|" * len(ctxs)]
    reasons, ratios = [], []
    for c in ctxs:
        b, k = summary.get((base, c)), summary.get((cand, c))
        if not b or not k or not b["t_turno_s"] or not k["t_turno_s"]:
            ratios.append(None); reasons.append(f"sem T_turno @{c // 1024}K"); continue
        r = k["t_turno_s"] / b["t_turno_s"]
        ratios.append(r)
        if (mode == "le" and r > threshold) or (mode == "parity" and abs(r - 1) > threshold):
            reasons.append(f"razão {r:.3f} @{c // 1024}K")
        kf = [g for g in k["gates_failed"] if g.split("<")[0] not in skip]
        bf = [g for g in b["gates_failed"] if g.split("<")[0] not in skip]
        if kf:
            reasons.append(f"gates {cand}@{c // 1024}K: {','.join(kf)}")
        if bf:
            reasons.append(f"gates {base}@{c // 1024}K: {','.join(bf)}")
        if runtime.get((cand, c)) == "mlx-serve" and not spec_stats_ok(logs_dir, runs.get((cand, c), set())):
            reasons.append(f"sem [spec-stats] {cand}@{c // 1024}K")
    lines.append(f"| {cand} | " + " | ".join("—" if r is None else f"{r:.3f}" for r in ratios) + " |")
    rule = f"≤ {threshold}" if mode == "le" else f"|r−1| ≤ {threshold}"
    lines.append("")
    lines.append(f"Regra: {rule} em {', '.join(f'{c // 1024}K' for c in ctxs)}, gates do candidato e da base, `[spec-stats]`"
                 + (f", ignorando {', '.join(sorted(skip))}." if skip else "."))
    ok = not reasons
    lines.append("VERDICT: pass" if ok else f"VERDICT: fail ({'; '.join(reasons)})")
    return "\n".join(lines), ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    camp = Path(__file__).resolve().parents[1]
    ap.add_argument("--results-dir", type=Path, default=camp / "results")
    ap.add_argument("--logs-dir", type=Path, default=camp / "logs")
    ap.add_argument("--glob", action="append", required=True, help="relative to --results-dir; repeat")
    ap.add_argument("--base")
    ap.add_argument("--cand")
    ap.add_argument("--ctx", default="32768,131072")
    ap.add_argument("--mode", choices=("le", "parity"), default="le")
    ap.add_argument("--threshold", type=float, help="default 0.97 with --mode le, 0.03 with --mode parity")
    ap.add_argument("--skip-gates", default="", help="comma list of gate names to ignore, e.g. hit_append,hit_tool_turn")
    ap.add_argument("--title", default="")
    ap.add_argument("--out-md", type=Path, help="also write the output to this markdown file")
    a = ap.parse_args(argv)
    if a.threshold is None:
        a.threshold = 0.03 if a.mode == "parity" else 0.97
    records, runs = load(a.results_dir, a.glob)
    if not records:
        print(f"decide: no records for {a.glob} in {a.results_dir}", file=sys.stderr)
        return 66
    text, data = table(records, runs)
    out = ([f"## {a.title}", ""] if a.title else []) + [text]
    ok = True
    if a.base and a.cand:
        verdict, ok = decide(data["summary"], data["runtime"], runs, a.logs_dir, a.base, a.cand,
                             [int(c) for c in a.ctx.split(",")], a.mode, a.threshold,
                             set(filter(None, a.skip_gates.split(","))))
        out.append(verdict)
    doc = "\n".join(out) + "\n"
    print(doc, end="")
    if a.out_md:
        a.out_md.parent.mkdir(parents=True, exist_ok=True)
        with a.out_md.open("a", encoding="utf-8") as fh:
            fh.write(doc + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
