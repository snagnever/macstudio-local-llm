#!/usr/bin/env python3
"""Collect the flashnext-concurrency results into the payload of the public report page.

collect() reads results/ (per-arm JSONL through summarize_parallel.summarize, the Claude Code pair runs
cc-*.json and the two stage verdict .env files) and returns a plain dict; render code consumes that dict.

    python3 bench/flashnext-concurrency-2026-10/scripts/render_report.py   # prints the payload as JSON
"""
from __future__ import annotations

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


def main() -> int:
    print(json.dumps(collect(RESULTS), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
