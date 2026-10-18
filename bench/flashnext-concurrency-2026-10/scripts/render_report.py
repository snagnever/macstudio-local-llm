#!/usr/bin/env python3
"""Collect the flashnext-concurrency results and render the public report page.

collect() reads results/ (per-arm JSONL through summarize_parallel.summarize, the Claude Code pair runs
cc-*.json and the two stage verdict .env files) and returns a plain dict; render() turns that dict into the
self-contained HTML page (inline SVG charts, payload embedded as JSON); main() writes the page and the payload.

    python3 bench/flashnext-concurrency-2026-10/scripts/render_report.py \\
        [--results-dir DIR] [--out-html reports/qwen38-flashnext-concurrency.html] [--out-json results/report-data.json]
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Optional, Sequence, Union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_parallel import summarize  # noqa: E402

CAMPAIGN = Path(__file__).resolve().parents[1]
RESULTS = CAMPAIGN / "results"
REPO = CAMPAIGN.parents[1]

RIG = "Mac Studio M4 Max 128 GB"
MODEL = "Dankpaws Swift 1.5 Qwen3.8 Flash-Next MLX 4.7 bpw"
SERVER = "mlx-serve 26.10.1"
DATES = ["2026-10-17", "2026-10-18"]
REFS: dict[Any, float] = {32768: 7.9, 131072: 8.6, 262144: 11.1, "262144_measured": 10.3}

RATIO_PASS = 1.5
RATIO_FAIL = 2.0
STALL_S = 60.0

# Wired peak memory in GB, keyed by (arm, ctx, tag). Server logs are gitignored, so summarize() cannot derive
# it; the values come from the "wired peak" column of the stage reports (the table repeats one value per
# stream, so one value per arm x ctx): results/etapa1-sintetica.md (tag e1), results/etapa1b-256k.md
# (tags e1b and e1d) and results/etapa1c-extras.md (tag e1c). The prefill-decode-share arms (ap3, ap5) have
# no wired-peak column in etapa1c-extras.md, so they are absent and report None.
WIRED_PEAK_GB: dict[tuple[str, Union[int, str], str], float] = {
    ("w1c1", 32768, "e1"): 96.0, ("w1c1a", 32768, "e1"): 96.9, ("w1c2", 32768, "e1"): 100.7,
    ("w1c2a", 32768, "e1"): 99.9, ("w1c1x2", 32768, "e1"): 100.1, ("w1c3a", 32768, "e1"): 101.4,
    ("w1c4", 32768, "e1"): 103.6, ("w1c4a", 32768, "e1"): 104.3,
    ("w1c1", 131072, "e1"): 110.5, ("w1c2", 131072, "e1"): 112.6, ("w1c2a", 131072, "e1"): 113.5,
    ("w1c1x2", 131072, "e1"): 113.5, ("w1c3a", 131072, "e1"): 114.7, ("w1c4", 131072, "e1"): 116.0,
    ("w1c4a", 131072, "e1"): 115.9,
    ("w1c1", 262144, "e1c"): 113.9, ("w1c2L", 262144, "e1d"): 115.0, ("w1c2m4", 262144, "e1b"): 113.3,
    ("w1c2q8", 262144, "e1b"): 113.7, ("w1c2m4q8", 262144, "e1d"): 107.7,
}

# code -> (public name, number of sessions). The ctx suffix is added for the arms whose name does not already
# carry the configuration (w1c1, w1c1a, w1c2, w1c2a, w1c1x2 at 32K/128K, and w1c1 at 256K).
PUBLIC = {
    "w1c1": ("1 session", 1), "w1c1a": ("1 session + side requests", 1), "w1c2": ("2 sessions", 2),
    "w1c2a": ("2 sessions + side requests", 2), "w1c1x2": ("2 sessions, --max-concurrent 1", 2),
    "w1c3a": ("3 sessions + side requests", 3), "w1c4": ("4 sessions", 4),
    "w1c4a": ("4 sessions + side requests", 4),
    "w1c2ap3": ("2 sessions + side requests, prefill-decode-share 0.3", 2),
    "w1c2ap5": ("2 sessions + side requests, prefill-decode-share 0.5", 2),
    "w1c2L": ("256K + 32K sessions, 16 GB prompt cache", 2),
    "w1c2m4": ("2 × 256K, 4 GB prompt cache", 2), "w1c2q8": ("2 × 256K, 8-bit KV cache", 2),
    "w1c2m4q8": ("2 × 256K, 4 GB cache + 8-bit KV", 2),
}
CTX_SUFFIX = {"w1c1", "w1c1a", "w1c2", "w1c2a", "w1c1x2", "w1c2ap3", "w1c2ap5"}
CTX_LABEL = {32768: "32K", 131072: "128K", 262144: "256K"}
BASE = ("w1c1", "w1c1a", "w1c2", "w1c2a", "w1c1x2", "w1c3a", "w1c4", "w1c4a")

# (code, ctx key, tag, context argument for summarize)
CONFIGS: list[tuple[str, int, str, Union[int, str]]] = (
    [(c, ctx, "e1", ctx) for ctx in (32768, 131072) for c in BASE]
    + [("w1c2ap3", 131072, "e1", 131072), ("w1c2ap5", 131072, "e1", 131072),
       ("w1c1", 262144, "e1c", 262144), ("w1c2L", 262144, "e1d", "all"),
       ("w1c2m4", 262144, "e1b", 262144), ("w1c2q8", 262144, "e1b", 262144),
       ("w1c2m4q8", 262144, "e1d", 262144)]
)
# Chart arms: n sessions with side requests (128K has no w1c1a run, so n=1 is w1c1; 256K: the solo control and the 4 GB cache pair).
CHART_ARMS = {32768: {1: "w1c1a", 2: "w1c2a", 3: "w1c3a", 4: "w1c4a"},
              131072: {1: "w1c1", 2: "w1c2a", 3: "w1c3a", 4: "w1c4a"},
              262144: {1: "w1c1", 2: "w1c2m4"}}


def _public_name(code: str, ctx: int) -> str:
    name = PUBLIC[code][0]
    return f"{name}, {CTX_LABEL[ctx]}" if code in CTX_SUFFIX else name


def _result(worst: Optional[float]) -> str:
    if worst is None:
        return "n/a"
    if worst <= RATIO_PASS:
        return "pass"
    return "warning" if worst <= RATIO_FAIL else "fail"


def _aux_over_60(results_dir: Path, code: str, tag: str, context: Union[int, str], ctx: int) -> int:
    name = f"{code}-{ctx}-{tag}-aux.jsonl"
    path = results_dir / name
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            t = r.get("ttft_s") if r.get("ttft_s") is not None else r.get("total_s")
            if (t or 0) > STALL_S:
                n += 1
    return n


def _config(results_dir: Path, code: str, ctx: int, tag: str, context: Union[int, str]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "code": code, "public_name": _public_name(code, ctx), "n": PUBLIC[code][1], "ctx": ctx, "aux": False,
        "tag": tag, "worst_ratio": None, "worst_stream": None, "decode_per_session": None,
        "decode_total": None, "aux_p50": None, "aux_p95": None, "aux_over_60": 0, "refused": 0,
        "needles": None, "needles_ok": None, "wired_peak": None, "result": "n/a",
    }
    s = summarize(results_dir, code, context, tag)
    streams = s["streams"]
    if not streams:
        return entry
    entry["n"] = len(streams)
    entry["wired_peak"] = WIRED_PEAK_GB.get((code, ctx, tag))
    ratios = [(st["ratio"], st["stream"]) for st in streams if st["ratio"] is not None]
    if ratios:
        entry["worst_ratio"], entry["worst_stream"] = max(ratios)
    decodes = [st["decode_tps"] for st in streams if st["decode_tps"] is not None]
    if decodes:
        entry["decode_per_session"] = statistics.mean(decodes)
        entry["decode_total"] = len(streams) * entry["decode_per_session"]
    aux = s["aux"]
    if aux is not None:
        entry.update(aux=True, aux_p50=aux["p50"], aux_p95=aux["p95"],
                     aux_over_60=_aux_over_60(results_dir, code, tag, context, ctx))
    entry["refused"] = sum(st["http_errors"] for st in streams) + (aux["errors"] if aux else 0)
    good = sum(int(st["needles"].split("/")[0]) for st in streams)
    total = sum(int(st["needles"].split("/")[1]) for st in streams)
    entry["needles"] = f"{good}/{total}"
    entry["needles_ok"] = not any(st["needles_failed"] for st in streams)
    entry["result"] = _result(entry["worst_ratio"])
    return entry


def _read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def _claude_code(results_dir: Path) -> dict[str, Any]:
    def wall(name: str) -> Optional[float]:
        p = results_dir / f"cc-{name}.json"
        return json.loads(p.read_text(encoding="utf-8"))["wall_s"] if p.exists() else None

    def reps(kind: str) -> list[int]:
        return sorted(int(p.name.split("r")[1].split("-")[0]) for p in results_dir.glob(f"cc-{kind}r*-a.json"))

    tasks: dict[str, Any] = {}
    for t in ("a", "b"):
        alone = [w for w in (wall(f"cc1r{r}-{t}") for r in reps("cc1")) if w is not None]
        together = [w for w in (wall(f"cc2r{r}-{t}") for r in reps("cc2")) if w is not None]
        tasks[t] = {"alone_mean": statistics.mean(alone) if alone else None,
                    "together_mean": statistics.mean(together) if together else None,
                    "together_reps": together}
    pairs = []
    for r in reps("cc2"):
        a, b = wall(f"cc2r{r}-a"), wall(f"cc2r{r}-b")
        if a is not None and b is not None:
            pairs.append(max(a, b))
    means = [tasks[t]["alone_mean"] for t in ("a", "b")]
    return {"tasks": tasks, "serial_sum": sum(means) if None not in means else None,
            "pair_wall": statistics.mean(pairs) if pairs else None}


def collect(results_dir: Path) -> dict[str, Any]:
    results_dir = Path(results_dir)
    configs = [_config(results_dir, code, ctx, tag, context) for code, ctx, tag, context in CONFIGS]
    by_code = {(c["code"], c["ctx"]): c for c in configs}
    by_n: dict[str, dict[int, dict[int, float]]] = {"ratio": {}, "decode": {}}
    for ctx, arms in CHART_ARMS.items():
        for n, code in arms.items():
            c = by_code[(code, ctx)]
            if c["worst_ratio"] is not None:
                by_n["ratio"].setdefault(ctx, {})[n] = c["worst_ratio"]
            if c["decode_per_session"] is not None:
                by_n["decode"].setdefault(ctx, {})[n] = c["decode_per_session"]
    return {
        "rig": RIG, "model": MODEL, "server": SERVER, "dates": list(DATES), "configs": configs, "by_n": by_n,
        "claude_code": _claude_code(results_dir),
        "verdicts": {"etapa1": _read_env(results_dir / "etapa1-verdict.env"),
                     "etapa1b": _read_env(results_dir / "etapa1b-verdict.env")},
        "refs": dict(REFS),
    }


# ---- SVG chart builders (pure; colors via CSS variables --s1..--s4 so the page CSS themes them) ----

def _fmt(v: float) -> str:
    return f"{v:.1f}"


def _scale(v: float, vmax: float, size: float) -> float:
    """Map v in [0, vmax] to [0, size]; values above vmax or below 0 are clamped."""
    return 0.0 if vmax <= 0 else max(0.0, min(v, vmax)) / vmax * size


def _nice(v: float) -> float:
    """Round up to 1, 2, 2.5, 5 or 10 times a power of ten."""
    if v <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * mag:
            return m * mag
    return 10 * mag


def _svg(w: int, h: int, label: str, body: list[str]) -> str:
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{html.escape(label, quote=True)}" xmlns="http://www.w3.org/2000/svg">'
            + "".join(body) + "</svg>")


def _text(x: float, y: float, s: str, cls: str = "", anchor: str = "middle") -> str:
    c = f' class="{cls}"' if cls else ""
    return (f'<text{c} x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="11" '
            f'fill="currentColor">{html.escape(s)}</text>')


def _baseline(left: float, right: float, y: float) -> str:
    return f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="currentColor" opacity="0.4"/>'


def _bar(x: float, bw: float, base_y: float, plot_h: float, value: Optional[float], vmax: float,
         fill: str, tip: str, cls: str) -> list[str]:
    """One bar with its <title> and value text, or an "n/a" placeholder when value is None."""
    if value is None:
        return [_text(x + bw / 2, base_y - 4, "n/a", "na")]
    bh = _scale(value, vmax, plot_h)
    return [f'<rect class="{cls}" x="{x:.1f}" y="{base_y - bh:.1f}" width="{bw * 0.9:.1f}" '
            f'height="{bh:.1f}" fill="{fill}"><title>{html.escape(tip)}</title></rect>',
            _text(x + bw * 0.45, base_y - bh - 3, _fmt(value), "value")]


def svg_grouped_bars(groups: list[dict], series: list[str], ymax: float,
                     bands: Sequence[tuple[float, str]] = ()) -> str:
    w, h, left, top, bottom = 640, 320, 40, 20, 40
    plot_h, slot = h - top - bottom, (w - left - 10) / max(len(groups), 1)
    bw = slot * 0.8 / max(len(series), 1)
    base_y = top + plot_h
    body = [_baseline(left, w - 10, base_y)]
    for value, text in bands:
        y = base_y - _scale(value, ymax, plot_h)
        body.append(f'<line class="band" x1="{left}" y1="{y:.1f}" x2="{w - 10}" y2="{y:.1f}" '
                    f'stroke="currentColor" stroke-dasharray="4 3" opacity="0.6"/>')
        body.append(_text(left - 4, y + 4, text, anchor="end"))
    for gi, g in enumerate(groups):
        x0 = left + gi * slot + slot * 0.1
        body.append(_text(left + gi * slot + slot / 2, h - bottom + 16, g["label"]))
        for si, name in enumerate(series):
            v = g["values"].get(name)
            tip = f'{g["label"]} · {name}: {_fmt(v) if v is not None else "n/a"}'
            body += _bar(x0 + si * bw, bw, base_y, plot_h, v, ymax, f"var(--s{si % 4 + 1})", tip, f"s{si + 1}")
    return _svg(w, h, f'Grouped bars: {", ".join(series)} by {", ".join(g["label"] for g in groups)}', body)


def svg_dots(rows: list[dict]) -> str:
    w, left, right, row_h, top = 640, 110, 20, 32, 24
    h = top + row_h * len(rows) + 28
    xmax = _nice(max([60.0] + [r[k] for r in rows for k in ("p50", "p95", "max") if r.get(k) is not None]))

    def x_of(v: float) -> float:
        return left + _scale(v, xmax, w - left - right)

    x60 = x_of(60)
    body = [f'<line class="band" x1="{x60:.1f}" y1="{top - 8}" x2="{x60:.1f}" y2="{h - 24}" '
            f'stroke="currentColor" stroke-dasharray="4 3" opacity="0.6"/>',
            _text(x60, h - 10, "60 s")]
    for i, r in enumerate(rows):
        y = top + i * row_h + row_h / 2
        body.append(_text(left - 8, y + 4, r["label"], anchor="end"))
        body.append(f'<line class="track" x1="{left}" y1="{y:.1f}" x2="{w - right}" y2="{y:.1f}" '
                    f'stroke="currentColor" opacity="0.15"/>')
        p50, p95 = r.get("p50"), r.get("p95")
        if p50 is None and p95 is None:
            body.append(_text(left + 6, y + 4, "n/a", "na", "start"))
            continue
        if p50 is not None and p95 is not None:
            body.append(f'<line class="span" x1="{x_of(p50):.1f}" y1="{y:.1f}" x2="{x_of(p95):.1f}" y2="{y:.1f}" '
                        f'stroke="var(--s2)" stroke-width="2"/>')
        for cls, v, color in (("p50", p50, "var(--s1)"), ("p95", p95, "var(--s2)")):
            if v is None:
                # Label sits above the track, clear of the remaining dot's circle (r=5).
                other = p95 if cls == "p50" else p50
                body.append(_text(x_of(other), y - 9, f"{cls} n/a", "na"))
            else:
                body.append(f'<circle class="{cls}" cx="{x_of(v):.1f}" cy="{y:.1f}" r="5" fill="{color}">'
                            f'<title>{html.escape(r["label"])} · {cls}: {_fmt(v)} s</title></circle>')
    return _svg(w, h, f'p50 and p95 per line: {", ".join(r["label"] for r in rows)}', body)


def svg_paired_bars(pairs: list[dict]) -> str:
    w, h, left, top, bottom = 640, 300, 20, 24, 40
    plot_h, slot = h - top - bottom, (w - left - 10) / max(len(pairs), 1)
    vmax = _nice(max([0.0] + [p[k] for p in pairs for k in ("a", "b") if p.get(k) is not None]))
    bw = slot * 0.35
    base_y = top + plot_h
    body = [_baseline(left, w - 10, base_y)]
    for i, p in enumerate(pairs):
        x0 = left + i * slot + slot * 0.1
        body.append(_text(left + i * slot + slot / 2, h - bottom + 16, p["label"]))
        for j, (k, name) in enumerate((("a", p.get("a_label", "a")), ("b", p.get("b_label", "b")))):
            v = p.get(k)
            tip = p["label"] + f' · {name}: {_fmt(v) if v is not None else "n/a"}'
            body += _bar(x0 + j * bw, bw, base_y, plot_h, v, vmax, f"var(--s{j + 1})", tip, k)
    return _svg(w, h, f'Paired bars: {", ".join(p["label"] for p in pairs)}', body)


# ---- RENDER ----
# render(data) turns the collect() dict into the public page. Every measured number on the page is formatted
# here from `data`; the few facts collect() cannot derive (cold-start timings and server log lines are not in
# results/) live in TEXT_FACTS with their source and travel in the payload too.

TITLE = "Flash-Next: how many agent sessions fit on one server?"
H1 = "How many agent sessions fit on one local Flash-Next server?"
GITHUB = "https://github.com/snagnever/macstudio-local-llm"
RUNBOOK_URL = f"{GITHUB}/blob/main/bench/flashnext-concurrency-2026-10/plan.md"
RESULTS_URL = f"{GITHUB}/tree/main/bench/flashnext-concurrency-2026-10/results"
UPSTREAM = "https://github.com/ddalcu/mlx-serve"
DROWZEYS_URL = ("https://github.com/drowzeys/"
                "keys-Independent-Bench-MLX-Serve-26.9.7-dev-Qwen3.8-Flash-Next-4bit-8bit-mixed")

TEXT_FACTS: dict[str, Any] = {
    # Cold prefill of a full prompt, one session alone: ~165 s at 128K (etapa1-sintetica.md, stall section) and
    # 350.8 s at 256K (docs/models/qwen3.8-flash-next.md, 2026-10-14 table).
    "cold_prefill_s": {"131072": 165, "262144": 350},
    # Median cold first-token time at 128K, both sessions pooled (etapa1c-extras.md, second table).
    "cold_ttft_median_s": {"w1c2a": 168, "w1c1x2": 169, "w1c2ap3": 319, "w1c2ap5": 327},
    "claude_code_version": "2.1.292",  # etapa2-claude-code.md
    "drowzeys_short_prompt_gain": 1.4,  # summary.md, Notas
}

# Exact server message (etapa1-sintetica.md, N = 4 section; same text quoted in summary.md).
REFUSAL_QUOTE = ("prompt 125549 tokens needs ~6266MB at prefill chunk 512 (the narrowest width tried), "
                 "~5968MB available + ~13863MB the hot cache can give back (~17420MB resident, ~3556MB of it "
                 "pinned by this request's own prefix) — refused before prefill")
BOOT_LOG = "Concurrency: --max-concurrent=1, batched decode on"

# 256K configurations: (code, chart label, prompt cache in RAM, KV cache precision, sessions). Inputs, not results.
LONG_CTX = [("w1c2L", "16 GB cache", "16 GB", "full", "one 256K + one 32K"),
            ("w1c2m4", "4 GB cache", "4 GB", "full", "two 256K"),
            ("w1c2q8", "8-bit KV", "16 GB", "8-bit", "two 256K"),
            ("w1c2m4q8", "4 GB + 8-bit KV", "4 GB", "8-bit", "two 256K")]

# Side-request chart rows: (code, ctx, label).
SIDE_ROWS = [("w1c1a", 32768, "1 session, 32K"), ("w1c2a", 32768, "2 sessions, 32K"),
             ("w1c1x2", 32768, "2 (limit 1), 32K"), ("w1c3a", 32768, "3 sessions, 32K"),
             ("w1c4a", 32768, "4 sessions, 32K"), ("w1c2a", 131072, "2 sessions, 128K"),
             ("w1c1x2", 131072, "2 (limit 1), 128K"), ("w1c3a", 131072, "3 sessions, 128K"),
             ("w1c4a", 131072, "4 sessions, 128K"), ("w1c2L", 262144, "256K + 32K"),
             ("w1c2m4", 262144, "2×256K, 4 GB"), ("w1c2q8", 262144, "2×256K, 8-bit"),
             ("w1c2m4q8", 262144, "2×256K, 4GB+8bit")]

UPSTREAM_ROWS = [
    (f"{UPSTREAM}/pull/568", "PR #568", "PR", "merged, in 26.10.1",
     "Adds <code>--prefill-decode-share</code>: generation keeps a share of the time while another request "
     "reads its prompt; the waiting request gets its first token later by the same amount. Tested here at 0.3 "
     "and 0.5."),
    (f"{UPSTREAM}/pull/884", "PR #884", "PR", "merged 2026-10-17, not in a release",
     "Lets small requests in at prefill chunk boundaries, which is the fix for side requests stuck behind a "
     "long prompt. It excludes the <code>qwen4_exp</code> architecture (Flash-Next)."),
    (f"{UPSTREAM}/issues/528", "issue #528", "issue", "closed by PR #621",
     "Requests refused after the prompt cache was restored from the SSD: the restored part was billed "
     "again at admission. The closest match to the refusals seen here."),
    (f"{UPSTREAM}/pull/621", "PR #621", "PR", "merged, in 26.10.1",
     "The fix for #528: a restore from the SSD is credited, so a warm turn is not billed as a cold one. It "
     "is in the version tested here, so the refusals below are a different or remaining case."),
    (f"{UPSTREAM}/issues/567", "issue #567", "issue", "closed",
     "Batched generation is not batch-invariant: a request’s output can change with the request it shares "
     "a batch with."),
    (DROWZEYS_URL, "independent benchmark", "external benchmark", "external",
     "Same model on mlx-serve: about {gain}× total throughput with short prompts, and less than one "
     "session alone from 32K up."),
]

TERMS = [("arm (<code>braço</code>), e.g. <code>w1c2a</code>", "test configuration (short code in parentheses)"),
         ("<code>stream</code>", "session (one simulated agent session)"),
         ("<code>aux</code> (aux generator)", "short side request (a 1-second permission check)"),
         ("<code>T_turno</code>", "turn time"),
         ("ratio ÷ <code>w1</code>", "slowdown"),
         ("needles", "recall check"),
         ("daily driver", "the everyday server setup"),
         ("rig", "the test machine"),
         ("etapa 1 / 1b / 1c / 2", "sections named by subject"),
         ("gate / verdict", "pass rule / result"),
         ("wired peak", "peak memory held by the server"),
         ("hot cache / prefix cache", "prompt cache")]

RESULT_TEXT = {"pass": "pass", "warning": "pass with a warning", "fail": "fail", "n/a": "n/a"}


def _e(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _num(v: Optional[float], fmt: str = "{:.1f}", unit: str = "") -> str:
    return "n/a" if v is None else fmt.format(v) + unit


def _x(v: Optional[float]) -> str:
    return _num(v, "{:.2f}", "×")


def _sec(v: Optional[float]) -> str:
    return _num(v, "{:.1f}", " s")


def _find(data: dict, code: str, ctx: int) -> Optional[dict]:
    return next((c for c in data["configs"] if c["code"] == code and c["ctx"] == ctx), None)


def _get(c: Optional[dict], key: str) -> Any:
    return None if c is None else c.get(key)


def _by_n(data: dict, kind: str, ctx: int, n: int) -> Optional[float]:
    table = data.get("by_n", {}).get(kind, {})
    row = table.get(ctx, table.get(str(ctx), {}))
    return row.get(n, row.get(str(n)))


def _has_data(c: Optional[dict]) -> bool:
    return c is not None and c.get("needles") is not None


def _verdict(c: Optional[dict]) -> str:
    """The page result: the pass rule on the worst slowdown, then fail on any refusal or recall miss."""
    if not _has_data(c) or c["result"] == "n/a":
        return "n/a"
    if c["refused"] or c["needles_ok"] is False:
        return "fail"
    return c["result"]


def _ctx_label(c: dict) -> str:
    if c["code"] == "w1c2L" or c["ctx"] == "all":
        return "256K + 32K"
    return CTX_LABEL.get(c["ctx"], str(c["ctx"]))


def _recall(c: Optional[dict]) -> str:
    if not _has_data(c):
        return "n/a"
    return c["needles"] + ("" if c["needles_ok"] else " (miss)")


def _span(vals: list[Optional[float]], fmt) -> str:
    v = [x for x in vals if x is not None]
    if not v:
        return "n/a"
    lo, hi = fmt(min(v)), fmt(max(v))
    return lo if lo == hi else f"{lo}–{hi}"


def _legend(items: list[tuple[str, str]]) -> str:
    return ('<div class="legend">' + "".join(
        f'<span class="chip"><span class="sw" style="background:{c}"></span>{_e(t)}</span>' for c, t in items)
        + "</div>")


def _table(head: list[str], rows: list[list[str]], cls: str = "", row_attrs: Optional[list[str]] = None) -> str:
    """head and rows are HTML fragments (already escaped)."""
    attrs = row_attrs or [""] * len(rows)
    c = f' class="{cls}"' if cls else ""
    return (f'<div class="tbl-scroll"><table{c}><thead><tr>' + "".join(f"<th>{h}</th>" for h in head)
            + "</tr></thead><tbody>"
            + "".join(f"<tr{a}>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>" for a, r in zip(attrs, rows))
            + "</tbody></table></div>")


def _section(sid: str, title: str, body: str, cls: str = "block") -> str:
    return f'<section class="{cls}" id="{sid}"><h2 class="sec">{title}</h2>{body}</section>'


def _panel(chart: str, caption: str = "") -> str:
    cap = f'<p class="p-interp">{caption}</p>' if caption else ""
    return f'<div class="panel"><div class="chart">{chart}</div>{cap}</div>'


# ---- sections ----

def _hero(data: dict) -> str:
    n_max = 0
    for n in range(1, 5):
        vals = [_by_n(data, "ratio", ctx, n) for ctx in (32768, 131072)]
        if None in vals or max(vals) > RATIO_FAIL:
            break
        n_max = n
    two = [_get(_find(data, "w1c2a", ctx), "worst_ratio") for ctx in (32768, 131072)]
    two = [v for v in two if v is not None]
    cc = data["claude_code"]
    serial, pair = cc.get("serial_sum"), cc.get("pair_wall")
    saved = None if serial is None or pair is None else max(0.0, serial - pair)
    later = None if serial is None or pair is None else (pair / serial - 1) * 100
    dates = " and ".join(data["dates"])
    tiles = [
        ("Maximum that passes", f"{n_max} sessions" if n_max else "n/a",
         f"Two sessions pass the rule with a warning: worst slowdown {_x(two[0] if two else None)} at 32K "
         f"and {_x(two[1] if len(two) > 1 else None)} at 128K. Three and four sessions fail."),
        ("Each session", f"~{round(statistics.mean(two)):.0f}× slower" if two else "n/a",
         "When two sessions share the server, each one generates at about half its speed alone."),
        ("Time saved", f"{saved:.0f} s saved" if saved is not None else "n/a",
         f"Two real Claude Code sessions together finished in {_sec(pair)} on average; the same two tasks "
         f"one after the other took {_sec(serial)}. Together is {_num(later, '{:.0f}', '%')} later."),
    ]
    tiles_html = "".join(f'<div class="tile"><p class="t-lab">{_e(a)}</p><p class="t-big">{_e(b)}</p>'
                         f'<p class="t-sub">{_e(c)}</p></div>' for a, b, c in tiles)
    lead = (f"We ran several agent sessions at once against one local server: the {_e(data['model'])} model "
            f"on {_e(data['server'])}, on the test machine ({_e(data['rig'])}), on {_e(dates)}. "
            "Two sessions work and stay within the pass rule, but each runs at about half its speed alone, so "
            "two tasks run together finish no sooner than the same tasks one after the other.")
    return (f'<section class="hero" id="hero"><p class="hero-lead">{lead}</p>'
            f'<div class="tiles">{tiles_html}</div></section>')


def _how(data: dict) -> str:
    refs = data["refs"]
    body = (
        '<div class="two-col"><div class="illus"><!-- ILLUSTRATION_TIMELINE --></div><div>'
        '<p class="s-note">Each <b>session</b> replays a coding agent’s conversation at a fixed context size. '
        'It starts cold: the server reads the whole prompt once (<b>prefill</b>, reading the prompt before the '
        'first token). Then come warm turns that add a tool result to a prompt the server already holds in its '
        '<b>prompt cache</b> and ask for a 512-token reply (<b>decode</b>, generating the reply token by '
        'token).</p>'
        '<p class="s-note">The <b>turn time</b> is the time from sending a tool result to receiving the full '
        'reply. The <b>slowdown</b> is a session’s turn time divided by the same session alone: '
        f'{_sec(refs.get(32768))} at 32K, {_sec(refs.get(131072))} at 128K and {_sec(refs.get(262144))} at '
        '256K.</p>'
        '<p class="s-note">A <b>test configuration</b> is a number of sessions × a context size × with or '
        'without <b>short side requests</b>: one-second permission checks, like an agent asking “may I run '
        'this?”, sent while the sessions work. Each configuration ran 3 times unless noted.</p>'
        f'<p class="s-note"><b>Pass rule:</b> worst slowdown ≤ {RATIO_PASS:.1f}× passes; '
        f'{RATIO_PASS:.1f}–{RATIO_FAIL:.1f}× passes with a warning; above {RATIO_FAIL:.1f}× fails. The slowest '
        'session decides. A configuration also fails if the server refuses a request or the model misses a '
        '<b>recall check</b> (a fact planted in the prompt that the reply must find).</p>'
        '</div></div>')
    return _section("how-it-works", "How the test works", body)


def _glossary() -> str:
    terms = [("Session", "One simulated agent working through its conversation."),
             ("Turn time", "Seconds from sending a tool result to receiving the full reply."),
             ("Slowdown", "Turn time ÷ the same session’s turn time when it runs alone."),
             ("Context size", "How long the conversation is: 32K, 128K or 256K tokens."),
             ("Prefill", "The server reading the prompt before it writes the first token."),
             ("Decode", "The server writing the reply, one token at a time.")]
    dl = "".join(f"<div><dt>{_e(t)}</dt><dd>{_e(d)}</dd></div>" for t, d in terms)
    return _section("glossary", "Six words used below", f'<dl class="gloss">{dl}</dl>', "block card")


def _sessions(data: dict) -> str:
    groups = [{"label": f"{n} session{'s' if n > 1 else ''}",
               "values": {"32K": _by_n(data, "ratio", 32768, n), "128K": _by_n(data, "ratio", 131072, n)}}
              for n in range(1, 5)]
    chart = svg_grouped_bars(groups, ["32K", "128K"], 4.5, bands=[(1.5, "pass"), (2.0, "fail above")])
    plain = {(code, ctx): _x(_get(_find(data, code, ctx), "worst_ratio"))
             for code in ("w1c2", "w1c4") for ctx in (32768, 131072)}
    note = (f"Worst slowdown per configuration, with short side requests running. One session at 128K is the "
            f"session alone. Without side requests: 2 sessions {plain[('w1c2', 32768)]} at 32K and "
            f"{plain[('w1c2', 131072)]} at 128K; 4 sessions {plain[('w1c4', 32768)]} and "
            f"{plain[('w1c4', 131072)]}.")
    body = (f'<p class="s-note">Bars below the {RATIO_PASS:.1f}× line pass; between the lines pass with a warning; '
            f'above {RATIO_FAIL:.1f}× fail.</p>'
            + _legend([("var(--s1)", "32K"), ("var(--s2)", "128K")]) + _panel(chart, _e(note)))
    return _section("sessions", "More sessions, slower turns", body)


def _throughput(data: dict) -> str:
    groups = [{"label": f"{n} session{'s' if n > 1 else ''}",
               "values": {"32K": _by_n(data, "decode", 32768, n), "128K": _by_n(data, "decode", 131072, n)}}
              for n in range(1, 5)]
    vals = [v for g in groups for v in g["values"].values() if v is not None]
    chart = svg_grouped_bars(groups, ["32K", "128K"], _nice(max(vals) * 1.1) if vals else 100.0)
    rows, gains = [], {}
    for n in range(1, 5):
        r = [str(n)]
        for ctx in (32768, 131072):
            per = _by_n(data, "decode", ctx, n)
            r += [_num(per), _num(None if per is None else per * n)]
        rows.append(r)
    for ctx in (32768, 131072):
        alone = _by_n(data, "decode", ctx, 1)
        totals = [_by_n(data, "decode", ctx, n) for n in range(2, 5)]
        totals = [t * n for t, n in zip(totals, range(2, 5)) if t is not None]
        gains[ctx] = (max(totals) / alone) if totals and alone else None
    table = _table(["Sessions", "32K per session", "32K total", "128K per session", "128K total"], rows)
    gain = TEXT_FACTS["drowzeys_short_prompt_gain"]
    body = (
        '<div class="illus"><!-- ILLUSTRATION_BATCH --></div>'
        '<p class="s-note">The server already batches the sessions’ generation: it writes one token for each '
        'session in the same step. On this model that step gets slower as sessions are added, so the total '
        'barely grows. Going from 1 to 4 sessions, the best total is '
        f'{_num(gains[32768], "{:.2f}", "×")} the speed of one session alone at 32K and '
        f'{_num(gains[131072], "{:.2f}", "×")} at 128K, while each session slows down by more.</p>'
        + _legend([("var(--s1)", "32K"), ("var(--s2)", "128K")])
        + _panel(chart, "Generation speed per session, tokens per second (average over the sessions in the run).")
        + table
        + '<p class="s-note">In the 2-session runs the first session started before the second and ran some '
        'turns alone, which lifts the 2-session average. An '
        f'<a href="{DROWZEYS_URL}">independent benchmark</a> of the same model shows the same pattern: about '
        f'{gain}× total throughput with short prompts and less than one session alone from 32K up.</p>')
    return _section("throughput", "Why two sessions do not add up", body)


def _side_requests(data: dict) -> str:
    rows, table = [], []
    for code, ctx, label in SIDE_ROWS:
        c = _find(data, code, ctx)
        rows.append({"label": label, "p50": _get(c, "aux_p50"), "p95": _get(c, "aux_p95"), "max": None})
        table.append([_e(label), _sec(_get(c, "aux_p50")), _sec(_get(c, "aux_p95")),
                      str(c["aux_over_60"]) if _has_data(c) else "n/a"])
    cold = TEXT_FACTS["cold_prefill_s"]
    long_p95 = [_get(_find(data, code, ctx), "aux_p95") for code, ctx, _ in SIDE_ROWS if ctx != 32768]
    short_p95 = [_get(_find(data, code, ctx), "aux_p95") for code, ctx, _ in SIDE_ROWS if ctx == 32768]
    body = (
        '<p class="s-note">A side request takes about a second when the server is free. When it arrives while '
        'another session is reading a long prompt, it waits for that read to finish: a cold 128K prompt takes '
        f'about {cold["131072"]} s to read and a 256K one about {cold["262144"]} s. At 32K the slowest '
        f'side requests (95th percentile) took {_span(short_p95, _sec)}; at 128K and 256K, '
        f'{_span(long_p95, _sec)}.</p>'
        + _legend([("var(--s1)", "median (p50)"), ("var(--s2)", "95th percentile (p95)")])
        + _panel(svg_dots(rows), "Side-request response time, seconds. The dashed line marks 60 s. "
                 "“limit 1” runs the two sessions with <code>--max-concurrent 1</code>: the wait is the same, "
                 "so the flag does not cause it.")
        + _table(["Configuration", "p50", "p95", "Over 60 s"], table)
        + f'<p class="s-note">Upstream, <a href="{UPSTREAM}/pull/884">PR #884</a> lets small requests in '
        'between prefill chunks, but it excludes this model’s architecture and is not in a release yet.</p>')
    return _section("side-requests", "Short side requests wait for long prompts", body)


def _max_concurrent(data: dict) -> str:
    cols = [(ctx, code) for ctx in (32768, 131072) for code in ("w1c1x2", "w1c2a")]
    cfg = {k: _find(data, k[1], k[0]) for k in cols}
    head = ["Two sessions + side requests"] + [
        f"{CTX_LABEL[ctx]}, <code>--max-concurrent {1 if code == 'w1c1x2' else 2}</code>" for ctx, code in cols]
    metrics = [("Worst slowdown", lambda c: _x(_get(c, "worst_ratio"))),
               ("Generation per session, tokens/s", lambda c: _num(_get(c, "decode_per_session"))),
               ("Side-request p95", lambda c: _sec(_get(c, "aux_p95"))),
               ("Side requests over 60 s", lambda c: str(c["aux_over_60"]) if _has_data(c) else "n/a"),
               ("Peak memory held by the server", lambda c: _num(_get(c, "wired_peak"), unit=" GB"))]
    rows = [[m] + [f(cfg[k]) for k in cols] for m, f in metrics]
    body = (
        '<p class="s-note"><code>--max-concurrent</code> sets how many requests the server runs at once. On '
        f'{_e(data["server"])} the default is 1, yet the boot log already says <code>{_e(BOOT_LOG)}</code>: '
        'two sessions share generation either way. The flag is not a queue, and setting it to 2 changes '
        'nothing measurable. At 128K the side-request p95 is higher with the flag at 2 because of a single very '
        'slow request; the count of side requests over 60 s is close in both runs.</p>'
        + _table(head, rows, "cmp"))
    return _section("max-concurrent", "Does <code>--max-concurrent</code> matter?", body)


def _long_context(data: dict) -> str:
    refs = data["refs"]
    groups, rows = [], []
    for code, label, cache, kv, sessions in LONG_CTX:
        c = _find(data, code, 262144)
        mark = ("†" if _get(c, "refused") else "") + ("‡" if _get(c, "needles_ok") is False else "")
        groups.append({"label": label + (" " + mark if mark else ""),
                       "values": {"worst slowdown": _get(c, "worst_ratio")}})
        rows.append([_e(sessions), cache, kv, _num(_get(c, "wired_peak"), unit=" GB"),
                     (str(c["refused"]) if _has_data(c) else "n/a"), _recall(c), _x(_get(c, "worst_ratio")),
                     RESULT_TEXT[_verdict(c)]])
    m4 = _get(_find(data, "w1c2m4", 262144), "worst_ratio")
    m4_measured = None if m4 is None else m4 * refs[262144] / refs["262144_measured"]
    table = _table(["Sessions", "Prompt cache in RAM", "KV cache", "Peak memory", "Refused", "Recall",
                    "Worst slowdown", "Result"], rows)
    body = (
        '<p class="s-note">Two 256K sessions fit only when the prompt cache kept in RAM is cut from 16 GB to '
        f'4 GB. That configuration passes with a warning: worst slowdown {_x(m4)} against the '
        f'{_sec(refs[262144])} reference, or {_x(m4_measured)} against the {_sec(refs["262144_measured"])} we '
        'measured for one 256K session alone over 3 runs. With the 4 GB cache, warm turns lose about a second '
        'restoring the cache from the SSD.</p>'
        + _legend([("var(--s1)", "worst slowdown")])
        + _panel(svg_grouped_bars(groups, ["worst slowdown"], 2.5, bands=[(1.5, "pass"), (2.0, "fail above")]),
                 "† the server refused a request &nbsp; ‡ the model missed a recall check. In the 256K + 32K "
                 "configuration the slowest session is the 32K one.")
        + table)
    return _section("long-context", "256K: two long sessions", body)


def _claude_code_section(data: dict) -> str:
    cc = data["claude_code"]
    tasks = cc.get("tasks", {})
    names = {"a": "Task A: add a CLI flag", "b": "Task B: fix two bash bugs"}
    pairs = [{"label": names[t], "a": tasks.get(t, {}).get("alone_mean"),
              "b": tasks.get(t, {}).get("together_mean"), "a_label": "alone", "b_label": "together"}
             for t in ("a", "b")]
    per = [r / tasks[t]["alone_mean"] for t in tasks if tasks[t].get("alone_mean")
           for r in tasks[t].get("together_reps", [])]
    serial, pair = cc.get("serial_sum"), cc.get("pair_wall")
    later = None if serial is None or pair is None else (pair / serial - 1) * 100
    body = (
        f'<p class="s-note">Two real Claude Code {TEXT_FACTS["claude_code_version"]} sessions '
        '(<code>claude -p</code>) shared the everyday server setup (128K context, default '
        '<code>--max-concurrent 1</code>), each on a fixed coding task with the same model as both main and '
        'fast model. Every task was done, with no errors and no refusals. Each session took '
        f'{_span(per, _x)} its time alone, above the {RATIO_PASS:.1f}× rule.</p>'
        + _legend([("var(--s1)", "alone (mean)"), ("var(--s2)", "together (mean)")])
        + _panel(svg_paired_bars(pairs), "Wall time per task, seconds.")
        + f'<p class="s-note"><b>Functional pass, time fail.</b> The pair finished in {_sec(pair)} on average; '
        f'the two tasks one after the other take {_sec(serial)}. Running them together finishes '
        f'{_num(later, "{:.0f}", "%")} later.</p>')
    return _section("claude-code", "Two real Claude Code sessions", body)


def _pds(data: dict) -> str:
    cold = TEXT_FACTS["cold_ttft_median_s"]
    spec = [("w1c2a", "off (default), <code>--max-concurrent 2</code>"),
            ("w1c1x2", "off (default), <code>--max-concurrent 1</code>"),
            ("w1c2ap3", "<code>--prefill-decode-share 0.3</code>"),
            ("w1c2ap5", "<code>--prefill-decode-share 0.5</code>")]
    rows = []
    for code, label in spec:
        c = _find(data, code, 131072)
        rows.append([label, _x(_get(c, "worst_ratio")),
                     str(c["aux_over_60"]) if _has_data(c) else "n/a", _sec(_get(c, "aux_p95")),
                     _num(cold.get(code), "{:.0f}", " s")])
    body = (
        '<p class="s-note"><code>--prefill-decode-share</code> makes generation keep a share of the time while '
        'another request reads its prompt. We tried it at 128K to clear the side-request wait. It did not: as '
        'many side requests waited over 60 s as without it, and the cold first token took about twice as '
        'long. <b>Not adopted.</b></p>'
        + _table(["Setting (two sessions + side requests, 128K)", "Worst slowdown", "Side requests over 60 s",
                  "Side-request p95", "Cold first token (median)"], rows))
    return _section("pds", "<code>--prefill-decode-share</code> 0.3 and 0.5", body)


def _learned(data: dict) -> str:
    def r(code, ctx):
        return _x(_get(_find(data, code, ctx), "worst_ratio"))
    cc = data["claude_code"]
    long_p95 = [_get(_find(data, code, ctx), "aux_p95") for code, ctx, _ in SIDE_ROWS if ctx != 32768]
    items = [
        f"{_e(data['server'])} already batches generation for this model at the default "
        "<code>--max-concurrent 1</code>; the flag is not a queue.",
        f"Two sessions is the most that passes: {r('w1c2a', 32768)} at 32K and {r('w1c2a', 131072)} at 128K. "
        f"Three fail ({r('w1c3a', 32768)} / {r('w1c3a', 131072)}), four fail ({r('w1c4a', 32768)} / "
        f"{r('w1c4a', 131072)} with side requests, {r('w1c4', 32768)} / {r('w1c4', 131072)} without).",
        "Total generation speed barely grows with more sessions, so two sessions together are not faster: "
        f"two real Claude Code tasks took {_sec(cc.get('pair_wall'))} together against "
        f"{_sec(cc.get('serial_sum'))} one after the other.",
        "A short request that arrives while another session reads a long prompt waits for it "
        f"(p95 {_span(long_p95, _sec)} at 128K and 256K); neither <code>--max-concurrent</code> nor "
        "<code>--prefill-decode-share</code> removes the wait.",
        "Two 256K sessions fit only with a 4 GB prompt cache in RAM; with 16 GB or an 8-bit KV cache the "
        "server refused requests or the model missed a recall check.",
        "The everyday server setup stays as it was. The launcher gained a <code>256k</code> profile for two "
        "long sessions.",
    ]
    return _section("learned", "What we learned", "<ol class=\"learned\">" + "".join(
        f"<li>{i}</li>" for i in items) + "</ol>")


def _upstream() -> str:
    rows = [[f'<a href="{url}">{_e(name)}</a>', _e(kind), _e(state),
             what.format(gain=TEXT_FACTS["drowzeys_short_prompt_gain"])]
            for url, name, kind, state, what in UPSTREAM_ROWS]
    body = (_table(["Link", "Type", "State", "How it relates"], rows, "wide")
            + '<p class="s-note"><i>We have not opened an issue about the admission refusals below, and their '
            'cause is not confirmed.</i></p>')
    return _section("upstream", "Related upstream work", body)


def _refusals(data: dict) -> str:
    names = [_e(c["public_name"]) + ("" if _ctx_label(c).split()[0] in c["public_name"] else f", {_ctx_label(c)}")
             for c in data["configs"] if c.get("refused")]
    body = (
        '<p class="s-note">Some requests were refused before the server started reading them'
        + (": " + "; ".join(names) + "." if names else ".")
        + ' One of the server’s messages, verbatim:</p>'
        f'<blockquote><code>{_e(REFUSAL_QUOTE)}</code></blockquote>'
        '<p class="s-note">Read literally, the message lists more memory available plus memory the prompt cache '
        'can give back than the request needs, even after leaving out the part pinned by the request’s own '
        'prefix. It looks like an admission accounting problem in this server version, similar to '
        f'<a href="{UPSTREAM}/issues/528">issue #528</a>, whose fix is already in this version. '
        '<b>Cause not confirmed.</b></p>')
    return _section("refusals", "Admission refusals", body, "block card")


def _not_measured() -> str:
    items = ["The iQ-MLX 4.7 bpw build of the same model with two sessions.",
             "512K with two sessions (the 512K launcher profile forces one request at a time).",
             "mlx-serve 26.10.2, which changes batching at long context and the SSD cache, and PR #884 in a "
             "future release.",
             "More than four sessions. Three sessions ran only with side requests.",
             "A real queue in the client (a lock that sends one request at a time): this server version has no "
             "switch to turn batching off.",
             "An interactive Claude Code pair with real permission prompts and titles."]
    return _section("not-measured", "Not measured",
                    "<ul>" + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>")


def _reproduce(data: dict) -> str:
    rows, attrs = [], []
    for c in data["configs"]:
        has = _has_data(c)
        rows.append([_e(c["code"]), _e(c["public_name"]), str(c["n"]), _ctx_label(c),
                     ("yes" if c["aux"] else "no") if has else "n/a", _x(c["worst_ratio"]),
                     str(c["refused"]) if has else "n/a", _recall(c), _num(c["wired_peak"], unit=" GB"),
                     RESULT_TEXT[_verdict(c)]])
        attrs.append(f' data-config="{_e(c["code"])}-{_e(c["ctx"])}"')
    cmd = ("tools/scripts/serve-flashnext-daily-driver.sh        # everyday setup: 128K, 16 GB prompt cache\n"
           "tools/scripts/serve-flashnext-daily-driver.sh 256k   # two long sessions: 256K, 4 GB prompt cache\n\n"
           "# the 256k profile runs:\n"
           "mlx-serve --model \"$MODEL\" --serve --host 0.0.0.0 --port 11234 --metrics --mtp \\\n"
           "  --ssm-checkpoint-max 16 --prefix-cache-mem 4GB --prefix-cache-disk 100GB \\\n"
           "  --prefix-cache-entries 64 --ctx-size 262144 --max-concurrent 2")
    body = (
        '<p class="s-note">Server commands, from the repository root (<code>$MODEL</code> is the model '
        'directory):</p>'
        f'<pre><code>{_e(cmd)}</code></pre>'
        f'<p class="s-note">Runbook: <a href="{RUNBOOK_URL}">plan.md</a>. Raw results and stage reports: '
        f'<a href="{RESULTS_URL}">results/</a>. The data behind this page is embedded in it as JSON '
        '(<code>#data</code>).</p>'
        '<details><summary>All test configurations</summary>'
        '<p class="s-note">Result applies the pass rule to the worst slowdown (session, ÷ the session alone), '
        'then fails any configuration with a refused request or a recall miss. Recall counts only answered '
        'requests. 256K slowdowns use the 11.1 s reference.</p>'
        + _table(["Code", "Configuration", "Sessions", "Context", "Side requests", "Worst slowdown", "Refused",
                  "Recall", "Peak memory", "Result"], rows, "all", attrs)
        + "</details>")
    return _section("reproduce", "Reproduce and data", body)


def _footer(generated: str) -> str:
    rows = [[a, _e(b)] for a, b in TERMS]
    return ('<footer id="terms"><h2 class="sec">Terms in the repository</h2>'
            '<p class="s-note">The repository’s runbook and stage reports use internal names. This page uses '
            'the public names on the right.</p>'
            + _table(["Internal", "On this page"], rows, "wide")
            + f'<p class="s-note">Generated on {_e(generated)}. Runbook: <a href="{RUNBOOK_URL}">plan.md</a>. '
            f'Results: <a href="{RESULTS_URL}">results/</a>.</p></footer>')


CSS = """
:root{
  color-scheme: light;
  --plane:#f9f9f7; --surface:#fcfcfb; --surface-2:#f3f2ee;
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,0.10);
  --accent:#2a78d6; --warn:#b06a00; --warn-bg:#fbf1dd;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
  --mono:"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
    --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
    --accent:#3987e5; --warn:#e0a63a; --warn-bg:#2a2312;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
  --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
  --accent:#3987e5; --warn:#e0a63a; --warn-bg:#2a2312;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--plane); color:var(--ink); font-family:var(--sans); line-height:1.5; -webkit-font-smoothing:antialiased}
.wrap{max-width:1080px; margin:0 auto; padding:32px 16px 64px}
header{display:flex; flex-wrap:wrap; gap:16px 32px; align-items:flex-end; justify-content:space-between}
h1{font-size:1.7rem; font-weight:700; letter-spacing:-0.02em; margin:0; text-wrap:balance}
.eyebrow{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.14em; text-transform:uppercase; color:var(--muted); margin:0 0 6px}
button.theme{font-family:var(--mono); font-size:0.74rem; color:var(--ink-2); background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:7px 12px; cursor:pointer}
button.theme:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
a{color:var(--accent)}
code{font-family:var(--mono); font-size:0.88em; background:var(--surface-2); padding:1px 5px; border-radius:4px; overflow-wrap:anywhere}
h2.sec{font-size:1.1rem; margin:0 0 6px; letter-spacing:-0.01em}
.s-note{color:var(--ink-2); font-size:0.92rem; margin:0 0 12px; max-width:82ch}
.s-note b{color:var(--ink)}
section.block{margin-top:34px}
.card{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px}
.hero-lead{font-size:1.06rem; line-height:1.55; max-width:72ch; margin:18px 0 0; color:var(--ink)}
.tiles{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr)); gap:12px; margin-top:20px}
.tile{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px}
.tile .t-lab{font-family:var(--mono); font-size:0.68rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--muted); margin:0}
.tile .t-big{font-size:1.8rem; line-height:1.1; font-weight:700; margin:6px 0 4px; color:var(--ink); font-variant-numeric:tabular-nums}
.tile .t-sub{font-size:0.84rem; color:var(--ink-2); margin:0; line-height:1.4}
.two-col{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr)); gap:16px; align-items:start}
.illus:empty{display:none}
.gloss{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr)); gap:10px 18px; margin:0}
.gloss dt{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--accent)}
.gloss dd{margin:2px 0 0; font-size:0.88rem; color:var(--ink-2)}
.legend{display:flex; flex-wrap:wrap; gap:6px 18px; margin:10px 0 6px}
.chip{display:inline-flex; align-items:center; gap:7px; font-size:0.84rem; color:var(--ink-2)}
.chip .sw{width:12px; height:12px; border-radius:3px; flex:none}
.panel{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 14px 10px; margin:6px 0 12px}
.chart{color:var(--ink-2); padding-left:30px}
.chart svg{width:100%; max-width:760px; height:auto; display:block; margin:0 auto; overflow:visible; font-family:var(--mono)}
.chart rect.s1,.chart rect.a,.chart circle.p50{fill:var(--s1)}
.chart rect.s2,.chart rect.b,.chart circle.p95{fill:var(--s2)}
.chart line.span{stroke:var(--s2)}
.chart text.na{fill:var(--muted)}
.p-interp{font-size:0.82rem; color:var(--ink-2); margin:8px 2px 0; line-height:1.4; border-top:1px solid var(--border); padding-top:8px}
.tbl-scroll{overflow-x:auto; border:1px solid var(--border); border-radius:10px; background:var(--surface); margin:0 0 12px}
table{border-collapse:collapse; width:100%; font-size:0.84rem}
th,td{padding:7px 10px; text-align:right; font-variant-numeric:tabular-nums; font-family:var(--mono); vertical-align:top}
th{font-size:0.72rem; letter-spacing:0.04em; color:var(--muted); font-weight:500; border-bottom:1px solid var(--border); background:var(--surface)}
td:first-child,th:first-child{text-align:left}
tbody tr:hover{background:var(--surface-2)}
table.wide td,table.wide th{text-align:left; font-family:var(--sans)}
table.wide td:last-child{min-width:260px}
table.all{min-width:860px}
table.all td:nth-child(2){text-align:left; font-family:var(--sans)}
ol.learned{margin:0; padding-left:22px; display:grid; gap:8px; max-width:82ch}
ol.learned li{font-size:0.92rem; color:var(--ink-2)}
blockquote{margin:0 0 12px; padding:10px 14px; border-left:3px solid var(--warn); background:var(--warn-bg); border-radius:6px}
blockquote code{background:none; padding:0; font-size:0.82rem}
pre{background:var(--surface-2); border:1px solid var(--border); border-radius:10px; padding:12px 14px; overflow-x:auto; font-size:0.8rem}
pre code{background:none; padding:0; overflow-wrap:normal}
details{margin-top:8px}
summary{cursor:pointer; font-weight:600; margin:0 0 10px}
footer{margin-top:48px; padding-top:20px; border-top:1px solid var(--border)}
"""

THEME_JS = """
const root=document.documentElement, btn=document.getElementById("themeBtn");
function label(){ btn.textContent="theme: "+(root.getAttribute("data-theme")||"auto"); }
btn.addEventListener("click",()=>{
  const cur=root.getAttribute("data-theme"), next=cur==null?"light":cur==="light"?"dark":null;
  if(next) root.setAttribute("data-theme",next); else root.removeAttribute("data-theme");
  try{ next?localStorage.setItem("theme",next):localStorage.removeItem("theme"); }catch(e){}
  label();
});
try{ const saved=localStorage.getItem("theme"); if(saved) root.setAttribute("data-theme",saved); }catch(e){}
label();
"""


def _payload(data: dict) -> dict:
    return dict(data, text_facts=TEXT_FACTS)


def render(data: dict, generated: Optional[str] = None) -> str:
    generated = generated or datetime.date.today().isoformat()
    payload = json.dumps(_payload(data), ensure_ascii=False).replace("</", "<\\/")
    eyebrow = " · ".join(["Qwen3.8 Flash-Next", data["server"], data["rig"], " to ".join(data["dates"])])
    desc = ("Two agent sessions is the most one local Flash-Next server handles within the pass rule; each runs "
            "about 2× slower and the pair saves no time.")
    parts = [
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n',
        f"<title>{_e(TITLE)}</title>\n",
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        f'<meta name="description" content="{_e(desc)}">\n',
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700'
        '&display=swap">\n',
        f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n",
        f'<header><div><p class="eyebrow">{_e(eyebrow)}</p><h1>{_e(H1)}</h1></div>'
        '<button class="theme" id="themeBtn" type="button">theme: auto</button></header>\n',
        _hero(data), _how(data), _glossary(), _sessions(data), _throughput(data), _side_requests(data),
        _max_concurrent(data), _long_context(data), _claude_code_section(data), _pds(data), _learned(data),
        _upstream(), _refusals(data), _not_measured(), _reproduce(data), "\n", _footer(generated),
        "\n</div>\n",
        f'<script id="data" type="application/json">{payload}</script>\n',
        f"<script>{THEME_JS}</script>\n</body>\n</html>\n",
    ]
    return "".join(parts)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render the public Flash-Next concurrency report page.")
    p.add_argument("--results-dir", default=str(RESULTS))
    p.add_argument("--out-html", default=str(REPO / "reports" / "qwen38-flashnext-concurrency.html"))
    p.add_argument("--out-json", default=str(RESULTS / "report-data.json"))
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    data = collect(Path(args.results_dir))
    out_html, out_json = Path(args.out_html), Path(args.out_json)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render(data), encoding="utf-8")
    out_json.write_text(json.dumps(_payload(data), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
