#!/usr/bin/env python3
"""Collect the flashnext-concurrency results into the payload of the public report page.

collect() reads results/ (per-arm JSONL through summarize_parallel.summarize, the Claude Code pair runs
cc-*.json and the two stage verdict .env files) and returns a plain dict; render code consumes that dict.

    python3 bench/flashnext-concurrency-2026-10/scripts/render_report.py   # prints the payload as JSON
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any, Optional, Union

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


def main() -> int:
    print(json.dumps(collect(RESULTS), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
