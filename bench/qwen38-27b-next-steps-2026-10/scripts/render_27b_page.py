#!/usr/bin/env python3
"""Render reports/qwen38-27b-stacks.html, the public page for the dense Qwen3.8-27B servers measured in
bench/qwen38-27b-next-steps-2026-10, against the two Qwen3.8-Flash-Next references (w1, n2).
Also writes the link-preview card, the Reddit post image (HTML; PNG with --png) and results/reddit-post.md.
usage: render_27b_page.py [--results DIR] [--out HTML] [--json-out JSON] [--card HTML] [--post HTML]
                          [--reddit-out MD] [--png] [--no-w1]
Every number on the page comes from the results; internal codes (arm ids, gates) only appear in the closed
"Raw data and reproduction" appendix.
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import statistics
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "bench/qwen38-flashnext-daily-driver-2026-09/scripts"))
sys.path.insert(0, str(ROOT / "bench/swift15-flashnext-2026-10/scripts"))
from summarize_driver import summarize, _is_served  # noqa: E402
from render_perf_lines import CSS as PERF_CSS, EXTRA_CSS as PERF_EXTRA_CSS  # noqa: E402
import summarize_ab  # noqa: E402
from empty_answers import is_empty  # noqa: E402

ARMS = [  # id, name, runtime, pack, rev, port, phase
    ("s27r", "mlx-dspark 0.20.3 + DFlash2", "mlx-dspark 0.20.3", "mlx-community 8bit", "815b83c0", 8484, "P0"),
    # KV int8: Splash 1.3.1 `serve --help` states "--kv-format {int8,bf16} ... (default: int8)"; the launcher passes no flag.
    ("k27", "Splash 1.3.1 + DFlash2, KV int8", "Splash 1.3.1",
     "mlx-community 8bit (Hub cache) + local DFlash2 draft", "815b83c0", 8585, "P1"),
    ("o27q8", "oMLX oQ8e refit", "oMLX 0.7.1.dev1", "Jundot oQ8e-mtp", "6c76ddfb", 8000, "P2"),
    ("o27q4", "oMLX oQ4e refit", "oMLX 0.7.1.dev1", "Jundot oQ4e-mtp", "49c1d603", 8000, "P2"),
    ("r27d", "mlx-serve 26.10.2 DFlash2 drafter only (--no-mtp)", "mlx-serve 26.10.2", "ddalcu 8bit", "7775059e", 11234, "P3"),
    ("r27m", "mlx-serve 26.10.2 MTP head only (--no-drafter)", "mlx-serve 26.10.2", "ddalcu 8bit", "7775059e", 11234, "P8"),
    ("w27d", "mlx-serve 26.10.2 Swift 1.5, DFlash2 drafter only (--no-mtp)", "mlx-serve 26.10.2",
     "scottlowry Swift-1.5 oQ4e-mtp", "881dc191", 11234, "P7"),
    ("w27m", "mlx-serve 26.10.2 Swift 1.5, MTP head only (--no-drafter)", "mlx-serve 26.10.2",
     "scottlowry Swift-1.5 oQ4e-mtp", "881dc191", 11234, "P8"),
    ("o27sw", "oMLX Swift 1.5 oQ4e", "oMLX 0.7.1.dev1", "scottlowry Swift-1.5 oQ4e-mtp", "881dc191", 8000, "P4"),
    ("l27", "llama.cpp b11569 draft-mtp", "llama.cpp b11569", "ggml-org Q8_0 + mtp", "71bc7b62", 8080, "P6"),
    ("l27n", "llama.cpp b11569 no spec", "llama.cpp b11569", "ggml-org Q8_0", "71bc7b62", 8080, "P6"),
]
ARM_IDS = [a[0] for a in ARMS]
# Public names: the page body never shows the internal codes.
PUBLIC = {
    "s27r": "mlx-dspark 0.20.3 + DFlash2 (baseline)",
    "k27": "Splash 1.3.1 + DFlash2",
    "r27d": "mlx-serve 26.10.2 + DFlash2",
    "o27q8": "oMLX 0.7.1 · oQ8e refit, 8-bit",
    "o27q4": "oMLX 0.7.1 · oQ4e refit, 4-bit",
    "o27sw": "oMLX 0.7.1 · Swift 1.5, 4-bit",
    "w27d": "mlx-serve 26.10.2 · Swift 1.5 + DFlash2",
    "r27m": "mlx-serve 26.10.2 · MTP head only",
    "w27m": "mlx-serve 26.10.2 · Swift 1.5, MTP only",
    "l27": "llama.cpp b11569 · Q8_0 + MTP draft",
    "l27n": "llama.cpp b11569 · Q8_0, no speculation",
}
SHORT = {"s27r": "mlx-dspark (baseline)", "k27": "Splash", "r27d": "mlx-serve"}
WEIGHTS = {  # Hugging Face ID of the target weights per measured setup (revisions come from ARMS)
    "s27r": "mlx-community/Qwen3.8-27B-8bit", "k27": "mlx-community/Qwen3.8-27B-8bit",
    "r27d": "ddalcu/Qwen3.8-27B-MLX-Serve-8bit",
}
COLOR = {"s27r": "--s1", "k27": "--s2", "r27d": "--s5", "w1": "--s3", "n2": "--ref-b"}
BASELINE = "s27r"
FILE_RE = re.compile(r"^(?P<arm>[a-z0-9]+)-(?P<ctx>\d+)-t1\.0-p(?P<phase>\d)(?P<eff>[xm])\.jsonl$")
EFFORT = {"x": "xhigh", "m": "medium"}
EFFORTS = ("xhigh", "medium")
SUITES = summarize_ab.SUITES
BANDS = (32768, 131072)
DRIVER_RATIO = 1.25
REPLY_TOKENS = 512
W1_SUMMARY = ROOT / "bench/swift15-flashnext-2026-10/results/tturno-summary.json"
W1_JSONL = ROOT / "bench/swift15-flashnext-2026-10/results"  # <ref>-<ctx>-t1.0-fn.jsonl, for the prefill column
W1_AB = ROOT / "bench/swift15-flashnext-2026-10/results/ab/t1/w1"
N2_AB = ROOT / "bench/swift15-flashnext-2026-10/results/ab/t1/n2"
# Both Flash-Next references ran at xhigh on mlx-serve 26.10.1 (swift15-flashnext-2026-10).
W1_NAME = "Qwen3.8-Flash-Next · Swift 1.5 quant (our daily model)"
N2_NAME = "Qwen3.8-Flash-Next · ddalcu iQ quant"
REF_NAMES = {"w1": W1_NAME, "n2": N2_NAME}
REF_RUNTIME = "mlx-serve 26.10.1"
SPEED_KEYS = ("t_turno_s", "warm_ttft_tool_s", "cold_ttft_s", "prefill_tps", "decode_tps", "hit_tool",
              "mtp_acceptance", "wired_peak_gb", "gates_failed")
REPO_URL = "https://github.com/snagnever/macstudio-local-llm"
CAMPAIGN_URL = f"{REPO_URL}/tree/main/bench/qwen38-27b-next-steps-2026-10"
SITE = "https://snagnever.github.io/macstudio-local-llm"
PAGE_URL = f"{SITE}/qwen38-27b-stacks.html"
CARD_URL = f"{SITE}/assets/qwen38-27b-stacks-card.png"
CARD_HTML = ROOT / "reports/assets/qwen38-27b-stacks-card.html"
POST_HTML = ROOT / "reports/assets/qwen38-27b-stacks-post.html"
POST_W, POST_H = 1400, 2080
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
RUN_CANDIDATE = ROOT / "bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh"
SPLASH_FLAGS = ROOT / "bench/qwen3.8-prefix-cache/config/splash-flags.env"
STATE_KEY = "qwen38-27b-stacks:v1"


# ---------------------------------------------------------------- data

def load_w1_summary() -> dict:
    return json.loads(W1_SUMMARY.read_text(encoding="utf-8")) if W1_SUMMARY.exists() else {}


def load_w1_ab() -> dict | None:
    return summarize_ab.load_arm(W1_AB) if W1_AB.exists() else None


def load_n2_ab() -> dict | None:
    return summarize_ab.load_arm(N2_AB) if N2_AB.exists() else None


def _jsonl(f: Path) -> list[dict]:
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _prefill(records: list[dict]) -> dict:
    """Prefill = prompt tokens of the cold request ÷ cold TTFT, median over the served cold records."""
    cold = [r for r in records if r.get("scenario") == "cold" and _is_served(r)
            and r.get("prompt_tokens") and r.get("ttft_ms")]
    if not cold:
        return {"prefill_tps": None, "cold_prompt_tokens": None}
    return {"prefill_tps": round(statistics.median(r["prompt_tokens"] / (r["ttft_ms"] / 1000) for r in cold), 1),
            "cold_prompt_tokens": round(statistics.median(r["prompt_tokens"] for r in cold))}


def _speed_row(row: dict, extra: dict | None = None) -> dict:
    warm, hit = row.get("warm_ttft_s") or {}, row.get("hit") or {}
    out = {"t_turno_s": row.get("t_turno_s"), "warm_ttft_tool_s": warm.get("tool_turn"),
           "cold_ttft_s": row.get("cold_ttft_s"), "decode_tps": row.get("decode_tps"),
           "hit_tool": hit.get("tool_turn"), "mtp_acceptance": row.get("mtp_acceptance"),
           "wired_peak_gb": row.get("wired_peak_gb"), "gates_failed": row.get("gates_failed"),
           "prefill_tps": None, "cold_prompt_tokens": None, "reps": None}
    out.update(extra or {})
    return out


def _reps(records: list[dict]) -> int | None:
    n = sum(1 for r in records if r.get("scenario") == "tool_turn")
    return n or None


def _speed(results: Path) -> dict:
    """One file = one arm × ctx × effort; the effort comes from the file tag (p<N>x / p<N>m)."""
    out: dict[str, dict] = {}
    for f in sorted(results.glob("*-t1.0-p?[xm].jsonl")):
        m = FILE_RE.match(f.name)
        if not m:
            continue
        recs = _jsonl(f)
        for (arm, ctx), row in summarize(recs).items():
            mine = [r for r in recs if r.get("arm") == arm and int(r["context_target"]) == ctx]
            extra = dict(_prefill(mine), reps=_reps(mine))
            out.setdefault(str(ctx), {})[f"{arm}-{EFFORT[m['eff']]}"] = _speed_row(row, extra)
    return out


def _smoke(results: Path) -> dict:
    """8K smokes: warm decode as summarize_driver defines it (median of identical, append, tool_turn)."""
    out = {}
    for f in sorted(results.glob("*-8192-t1.0-smoke.jsonl")):
        recs = _jsonl(f)
        for (arm, _ctx), row in summarize(recs).items():
            effs = sorted({r.get("reasoning_effort") for r in recs if r.get("reasoning_effort")})
            out[arm] = {"decode_tps": row.get("decode_tps"), "t_turno_s": row.get("t_turno_s"),
                        "effort": effs[0] if len(effs) == 1 else None, "reps": _reps(recs)}
    return out


def _think(results: Path) -> dict:
    """Thinking-turn probe at 128K: tool turns that resend the previous reasoning vs drop it."""
    out = {}
    d = results / "think"
    for f in sorted(d.glob("*.jsonl")) if d.exists() else []:
        recs = _jsonl(f)
        arm, _, eff = f.stem.rpartition("-")
        row = {"arm": arm, "effort": eff}
        for mode in ("resend", "drop"):
            tool = [r for r in recs if r.get("mode") == mode and r.get("scenario") == "tool_turn"]
            ok = [r["ttft_ms"] / 1000 for r in tool if not r.get("error") and r.get("ttft_ms") is not None]
            row[mode] = {"n": len(tool), "errors": sum(1 for r in tool if r.get("error")),
                         "http400": sum(1 for r in tool if "400" in str(r.get("error") or "")),
                         "ttft_s_median": round(statistics.median(ok), 1) if ok else None,
                         "ttft_s_min": round(min(ok), 1) if ok else None,
                         "ttft_s_max": round(max(ok), 1) if ok else None}
        out[f.stem] = row
    return out


def _sampling(results: Path) -> dict:
    for f in sorted(results.glob("*-t1.0-p?[xm].jsonl")):
        for r in _jsonl(f):
            if r.get("temperature") is not None:
                return {k: r.get(k) for k in ("temperature", "top_p", "top_k")}
    return {}


def _quality(results: Path) -> dict:
    root = results / "q/t1"
    out = {}
    for d in sorted(p for p in root.glob("*") if p.is_dir()) if root.exists() else []:
        arm = summarize_ab.load_arm(d)
        stats = {s: summarize_ab.suite_stats(arm[s]) for s in SUITES if s in arm}
        if stats:
            out[d.name] = stats
    return out


def _empty(results: Path) -> dict:
    """Empty final answers per battery label (q/t1/<label>/*.jsonl) and per thinking probe (think/<arm>-<eff>)."""
    out = {}
    groups = {}
    root = results / "q/t1"
    for d in sorted(p for p in root.glob("*") if p.is_dir()) if root.exists() else []:
        groups[d.name] = sorted(d.glob("*.jsonl"))
    think = results / "think"
    for f in sorted(think.glob("*.jsonl")) if think.exists() else []:
        groups[f"think:{f.stem}"] = [f]
    for label, files in groups.items():
        empty = stops = 0
        for f in files:
            for r in _jsonl(f):
                if r.get("finish_reason") == "stop":
                    stops += 1
                    empty += is_empty(r)
        out[label] = {"empty": empty, "stop_records": stops}
    return out


def _loops(results: Path) -> dict:
    out = {}
    d = results / "loops"
    for f in sorted(d.glob("*.jsonl")) if d.exists() else []:
        ok = [r for r in _jsonl(f) if "error" not in r]
        label = f.stem[2:] if f.stem.startswith("q-") else f.stem
        out[label] = {"degenerate": sum(1 for r in ok if r.get("degenerate")), "total": len(ok)}
    return out


def _gates(results: Path) -> dict:
    g = results / "gates.env"
    if not g.exists():
        return {}
    return dict(l.split("=", 1) for l in g.read_text(encoding="utf-8").splitlines() if "=" in l)


def _macos(results: Path) -> str | None:
    f = results / "etapa0-preflight.md"
    m = re.search(r"^macOS (\S+)", f.read_text(encoding="utf-8"), re.M) if f.exists() else None
    return m.group(1) if m else None


def _driver(summary: dict, arm: str, jsonl_dir: Path | None = None) -> dict:
    out = {}
    for c in BANDS:
        extra = {}
        f = jsonl_dir / f"{arm}-{c}-t1.0-fn.jsonl" if jsonl_dir else None
        if f is not None and f.exists() and summary.get(f"{arm}@{c}"):
            recs = _jsonl(f)
            extra = dict(_prefill(recs), reps=_reps(recs))
        out[str(c)] = _speed_row(summary.get(f"{arm}@{c}", {}), extra)
    return out


def _driver_quality(ab) -> dict:
    return {s: summarize_ab.suite_stats(ab[s]) for s in SUITES if s in ab} if ab else {}


def _t(p: dict, label: str, ctx) -> float | None:
    return ((p["speed"].get(str(ctx)) or {}).get(label) or {}).get("t_turno_s")


def _ref_t(p: dict, ref: str, ctx) -> float | None:
    return ((p.get(ref) or {}).get(str(ctx)) or {}).get("t_turno_s")


def _setups(p: dict) -> list[str]:
    """Setups with speed results, in ARMS order (unknown ids last)."""
    ids = {lab.rpartition("-")[0] for rows in p["speed"].values() for lab in rows}
    return sorted(ids, key=lambda i: (ARM_IDS.index(i) if i in ARM_IDS else len(ARM_IDS), i))


def _xhigh(p: dict, i: str, key: str) -> list:
    return [((p["speed"].get(str(c)) or {}).get(f"{i}-xhigh") or {}).get(key) for c in BANDS]


def funnel(p: dict) -> list[dict]:
    """The selection funnel, from the payload: candidates → 8K smoke → full test → fastest setup.
    Each stage: count, the ids that reach it, and entries (id, class keep / ref / cut / fail, speeds)."""
    ids = [a["id"] for a in p["arms"]]
    smoke = [i for i in ids if i in p.get("smoke", {})]
    full = [i for i in _setups(p) if all(any(lab.rpartition("-")[0] == i for lab in p["speed"].get(str(c), {}))
                                         for c in BANDS)]
    base_t = _xhigh(p, BASELINE, "t_turno_s")
    faster = []
    for i in full:
        if i == BASELINE:
            continue
        t = _xhigh(p, i, "t_turno_s")
        if None not in t + base_t and all(a < b for a, b in zip(t, base_t)):
            faster.append(i)
    fastest = min(faster, key=lambda i: _xhigh(p, i, "t_turno_s")[-1]) if faster else None

    def speeds(i):
        t = _xhigh(p, i, "t_turno_s")
        r = [a / b if a is not None and b else None for a, b in zip(t, base_t)] if i != BASELINE else None
        return {"t_turno_s": t, "decode_tps": _xhigh(p, i, "decode_tps"), "ratios": r}

    full_entries = []
    for i in full:
        cls = "ref" if i == BASELINE else "keep" if i == fastest else "fail"
        full_entries.append(dict({"id": i, "cls": cls}, **speeds(i)))
    fams = []
    for a in p["arms"]:
        fam = a["runtime"].split()[0]
        if fam not in fams:
            fams.append(fam)
    return [
        {"stage": "candidates", "count": len(ids), "ids": ids, "runtimes": fams,
         "entries": [{"id": i, "cls": "cut"} for i in ids if i not in smoke and i not in full]},
        {"stage": "smoke", "count": len(smoke), "ids": smoke, "skipped": [i for i in full if i not in smoke],
         "entries": [{"id": i, "cls": "keep" if i in full else "cut", "decode_tps": p["smoke"][i]["decode_tps"]}
                     for i in smoke]},
        {"stage": "full", "count": len(full), "ids": full, "entries": full_entries},
        {"stage": "fastest", "count": 1 if fastest else 0, "ids": [fastest] if fastest else [],
         "entries": [dict({"id": fastest, "cls": "keep"}, **speeds(fastest))] if fastest else []},
    ]


def build_payload(results: Path, w1_summary: dict, w1_ab, n2_ab=None, ref_jsonl: Path | None = None) -> dict:
    results = Path(results)
    p = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "arms": [dict(zip(("id", "name", "runtime", "pack", "rev", "port", "phase"), a), public=PUBLIC[a[0]])
                  for a in ARMS],
         "speed": _speed(results),
         "w1": _driver(w1_summary, "w1", ref_jsonl),
         "n2": _driver(w1_summary, "n2", ref_jsonl),
         "smoke": _smoke(results),
         "think": _think(results),
         "sampling": _sampling(results),
         "macos": _macos(results),
         "quality": _quality(results),
         "w1_quality": _driver_quality(w1_ab),
         "n2_quality": _driver_quality(n2_ab),
         "empty": _empty(results),
         "loops": _loops(results),
         "gates": _gates(results)}
    p["funnel"] = funnel(p)
    return p


def splash_command() -> dict | None:
    """The Splash 1.3.1 launch of the k27 setup, read from run-candidate.sh (k27 block) and splash-flags.env."""
    if not (RUN_CANDIDATE.exists() and SPLASH_FLAGS.exists()):
        return None
    rc = RUN_CANDIDATE.read_text(encoding="utf-8")
    block = re.search(r"^\s*k27\)(.*?);;", rc, re.S | re.M)
    if not block:
        return None
    b = block.group(1)
    env = dict(re.findall(r'(SPLASH_MODEL|SPLASH_REVISION|SPLASH_DRAFTER|QWEN38_SPLASH_PORT)="?([^"\s]+)"?', b))
    var = env.get("SPLASH_DRAFTER", "").lstrip("$")
    dm = re.search(rf'^{var}="([^"]+)"', rc, re.M) if var else None
    root = re.search(r'^MODEL_ROOT="([^"]+)"', rc, re.M)
    draft = dm.group(1) if dm else ""
    if root:
        draft = draft.replace("$MODEL_ROOT", root.group(1))
    draft = draft.replace("$HOME", "~")
    fl = dict(re.findall(r'^(\w+)="([^"]*)"', SPLASH_FLAGS.read_text(encoding="utf-8"), re.M))
    dname = draft.rstrip("/").rsplit("/", 1)[-1]
    drepo = re.match(r"^(?P<owner>[^-]+)--(?P<repo>.+)-(?P<rev>[0-9a-f]{40})$", dname)
    return {"bin": fl.get("SPLASH_BIN", "").replace("$HOME", "~"), "model": env.get("SPLASH_MODEL"),
            "revision": env.get("SPLASH_REVISION"), "port": env.get("QWEN38_SPLASH_PORT"),
            "draft_dir": draft, "draft_repo": f"{drepo['owner']}/{drepo['repo']}" if drepo else None,
            "draft_rev": drepo["rev"] if drepo else None, "extra": fl.get("SPLASH_EXTRA_ARGS", ""),
            "flags": fl}


# ---------------------------------------------------------------- html helpers

NA = '<span class="na">—</span>'


def E(v) -> str:
    return _html.escape("" if v is None else str(v), quote=True)


def ND(v, fmt="{}", unit="") -> str:
    if v is None:
        return NA
    return E(fmt.format(v)) + (f'<span class="u">{E(unit)}</span>' if unit else "")


def _ctx_lab(ctx) -> str:
    return f"{int(ctx) // 1024}K"


def _fmt_s(v) -> str:
    return "not measured" if v is None else f"{v:.1f} s"


def _name(i: str) -> str:
    return PUBLIC.get(i) or REF_NAMES.get(i) or i


def _ratio(a, b):
    return a / b if a is not None and b else None


def facts(p: dict) -> dict | None:
    """Headline numbers for the TL;DR, the card and the post; None when the needed results are missing."""
    big = "131072"
    k = {e: _t(p, f"k27-{e}", big) for e in EFFORTS}
    base = _t(p, f"{BASELINE}-xhigh", big)
    w1 = _ref_t(p, "w1", big)
    if None in (k["xhigh"], k["medium"], base, w1):
        return None
    return {"k_x": k["xhigh"], "k_m": k["medium"], "base": base, "w1": w1,
            "vs_base": k["xhigh"] / base, "vs_w1_x": k["xhigh"] / w1, "vs_w1_m": k["medium"] / w1,
            "vs_w1_round": round(k["xhigh"] / w1)}


# ---------------------------------------------------------------- sections

AGENT_TURN_DEF = ("time to the first token of a turn that carries a tool result, plus "
                  f"{REPLY_TOKENS} generated tokens")
EFFORT_SENTENCE = ("Thinking effort is the <code>reasoning_effort</code> value sent with each request. More effort means "
                   "more reasoning tokens and lower draft acceptance, so a lower decode speed.")
QUALITY_LINE = "Quality and per-task time were not measured for the 27B."


def _html_tldr(p: dict) -> str:
    f = facts(p)
    sp = _smoke_split(p)
    cut = sp["never"] + sp["smoked"]
    names = "".join(f'<li>{E(_name(e["id"]))}{" (8K smoke only)" if e in sp["smoked"] else ""}</li>' for e in cut)
    not_measured = ('<aside class="nm-box"><p class="nm-h">What we did not measure</p><ul>'
                    '<li><b>Quality of the 27B.</b> No coding, reasoning or tool-calling accuracy run on any setup.</li>'
                    '<li><b>Time per real task.</b> Only a synthetic agent turn, not an end-to-end job.</li>'
                    f'<li><b>{len(cut)} of the {len(ARMS)} candidate setups</b> never got the full 32K / 128K test '
                    f'({len(sp["never"])} never ran; {len(sp["smoked"])} ran only the 8K smoke):'
                    f'<ul class="nm-sub">{names}</ul></li></ul></aside>')
    if f is None:
        body = ('<p class="tl-line">The headline numbers (the fastest setup at 128K, the baseline and the Flash-Next '
                'reference) were not measured.</p>')
    else:
        body = (
            f'<p class="tl-line"><b>Fastest setup: Splash 1.3.1 + DFlash2</b> (8-bit weights). Its <dfn>agent turn time</dfn> '
            f'({AGENT_TURN_DEF}) at 128K context is <b>{f["k_x"]:.1f} s</b> at thinking effort xhigh and '
            f'<b>{f["k_m"]:.1f} s</b> at thinking effort medium.</p>'
            f'<p class="tl-line">That is <b>{f["vs_base"]:.2f}×</b> the baseline, {E(PUBLIC[BASELINE].replace(" (baseline)", ""))} '
            f'with the same weights and draft ({f["base"]:.1f} s at xhigh; same effort on both sides).</p>'
            f'<p class="tl-line">It is still <b>~{f["vs_w1_round"]}×</b> Qwen3.8-Flash-Next, the model we use daily '
            f'({f["w1"]:.1f} s at 128K; {f["vs_w1_x"]:.2f}× at xhigh, {f["vs_w1_m"]:.2f}× at medium): '
            '<b>for agent loops, Flash-Next is still faster.</b></p>')
    return (f'<section class="block tldr-wrap" id="tldr"><div class="tldr"><p class="tl-h">TL;DR</p>{body}</div>'
            f'{not_measured}</section>')


GLOSSARY = [
    ("TTFT", "time to first token: seconds from sending a request until the first token comes back."),
    ("Cold vs warm", "cold is the first request on an empty cache, so the server reads the whole prompt; warm is a "
                     "later request that reuses the cached start of the conversation."),
    ("Prefill (prompt processing)", "reading the prompt before the first token; here prompt tokens ÷ cold TTFT."),
    ("Decode (token generation)", "how fast the reply comes out, in tokens per second; the median over the warm requests."),
    ("Prefix cache and hit rate", "the server keeps the work done on the previous prompt; the hit rate is the share of "
                                  "the new prompt served from that cache."),
    ("Context 32K / 128K", "the test conversation fills a 32K (32,768-token) or 128K (131,072-token) context window."),
    ("Draft model (DFlash2) and speculative decoding", "a small draft model proposes several tokens and the 27B checks "
                                                       "them in one pass; accepted tokens come almost free."),
    ("MTP", "multi-token prediction: extra heads inside the model propose the next tokens, with no separate draft."),
    ("Thinking effort", "the reasoning_effort value of the request (xhigh or medium); more effort means more reasoning "
                        "tokens and lower draft acceptance, so lower decode."),
]


def _html_glossary() -> str:
    items = "".join(f"<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>" for k, v in GLOSSARY)
    return ('<section class="block" id="glossary"><h2 class="sec">Glossary</h2>'
            f'<dl class="gloss">{items}</dl></section>')


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width, break_on_hyphens=False, break_long_words=False) or [""]


FN_W = 360  # SVG units; at 375 px the figure is ~329 px wide, so 13.5-unit text stays above 12 px


def _pair(v, fmt) -> str:
    return " / ".join("—" if x is None else fmt.format(x) for x in v)


def _fn_notes(e: dict) -> list[str]:
    if e.get("decode_tps") is not None and "t_turno_s" not in e:
        return [f'decode {e["decode_tps"]:.1f} tok/s at 8K']
    if "t_turno_s" not in e:
        return []
    notes = [f'{_pair(e["t_turno_s"], "{:.1f}")} s per agent turn',
             f'decode {_pair(e["decode_tps"], "{:.1f}")} tok/s']
    if e.get("ratios") and None not in e["ratios"]:
        notes.append(f'{_pair(e["ratios"], "{:.2f}×")} the baseline')
    elif e["cls"] == "ref":
        notes.append("the reference for the other two")
    return notes


def funnel_svg(p: dict) -> str:
    """The funnel as inline SVG (no library). Bars scale with the count; each setup line carries class
    keep / ref / cut / fail and its speeds from the payload."""
    st = p["funnel"]
    W = FN_W
    n0 = max(st[0]["count"], 1)
    out, y = [], 4
    smoke = p.get("smoke", {})
    fastest = st[-1]["ids"][0] if st[-1]["ids"] else None
    labels = {
        "candidates": "candidate setups",
        "smoke": "8K smoke test (decode)",
        "full": "full speed test at 32K and 128K",
        "fastest": f"fastest: {_name(fastest)}" if fastest else "faster than the baseline: none",
    }
    heads = {"candidates": "never ran, cut by choice:", "smoke": "decode at 8K, thinking effort medium:",
             "full": "agent turn time at 32K / 128K, xhigh:", "fastest": ""}
    for k, s in enumerate(st):
        cnt = s["count"]
        w = max(48.0, (W - 24) * cnt / n0)
        x = (W - w) / 2
        cls, ncls = ("fn-bar", "fn-n") if cnt else ("fn-zero", "fn-n0")
        out.append(f'<rect class="{cls}" x="{x:.1f}" y="{y}" width="{w:.1f}" height="32" rx="6"/>'
                   f'<text class="{ncls}" x="{W / 2}" y="{y + 22}" text-anchor="middle">{cnt}</text>')
        y += 32 + 21
        for line in _wrap(labels[s["stage"]], 36):
            out.append(f'<text class="fn-lab" x="{W / 2}" y="{y}" text-anchor="middle">{E(line)}</text>')
            y += 20
        det = []
        if s["stage"] == "candidates":
            det = [f'{len(s["runtimes"])} runtimes: {", ".join(s["runtimes"])}']
        elif s["stage"] == "smoke":
            if s.get("skipped") == [BASELINE]:
                det.append("the baseline skips it: it is the reference")
            elif s.get("skipped"):
                det.append("skipped: " + ", ".join(_name(i) for i in s["skipped"]))
        for d in det:
            for line in _wrap(d, 44):
                out.append(f'<text class="fn-det" x="{W / 2}" y="{y}" text-anchor="middle">{E(line)}</text>')
                y += 18
        ents = s["entries"]
        if ents:
            y += 6
            if heads[s["stage"]]:
                out.append(f'<text class="fn-grp" x="10" y="{y}">{E(heads[s["stage"]])}</text>')
                y += 19
        for e in ents:
            notes = _fn_notes(e)
            lines = _wrap(_name(e["id"]), 40)
            out.append(f'<rect class="fn-sw {e["cls"]}" x="12" y="{y - 11}" width="12" height="12" rx="2"/>')
            for line in lines:
                out.append(f'<text class="fn-name {e["cls"]}" x="32" y="{y}">{E(line)}</text>')
                y += 18
            for n in notes:
                for line in _wrap(n, 44):
                    out.append(f'<text class="fn-note" x="32" y="{y}">{E(line)}</text>')
                    y += 17
            y += 4
        if k < len(st) - 1:
            y += 4
            out.append(f'<path class="fn-arrow" d="M{W / 2 - 8} {y} L{W / 2} {y + 9} L{W / 2 + 8} {y}"/>')
            y += 18
    h = y + 2
    return (f'<svg class="funnel" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" '
            f'aria-labelledby="fn-title"><title id="fn-title">Selection funnel: '
            f'{" → ".join(str(s["count"]) for s in st)} setups</title>{"".join(out)}</svg>')


def _smoke_split(p: dict) -> dict:
    """Setups that ran the 8K smoke but not the full test, and which of them decoded slower than every setup
    that went on."""
    st = {s["stage"]: s for s in p["funnel"]}
    sm = st["smoke"]["entries"]
    kept = [e["decode_tps"] for e in sm if e["cls"] == "keep" and e["decode_tps"] is not None]
    cut = [e for e in sm if e["cls"] == "cut"]
    floor = min(kept) if kept else None
    slow = [e for e in cut if floor is not None and e["decode_tps"] is not None and e["decode_tps"] < floor]
    return {"never": st["candidates"]["entries"], "smoked": cut, "slow": slow, "floor": floor}


def _funnel_legend(p: dict) -> str:
    effs = {v.get("effort") for v in p.get("smoke", {}).values()}
    eff = next(iter(effs)) if len(effs) == 1 and None not in effs else None
    reps = {v.get("reps") for v in p.get("smoke", {}).values()}
    run = "one run" if reps == {1} else "median of the runs"
    sp = _smoke_split(p)
    smoked = ""
    if sp["smoked"]:
        smoked = (f' {len(sp["smoked"])} of them ran the 8K smoke first and were not taken further after it'
                  + (f'; {len(sp["slow"])} of those decoded slower than every setup that went on '
                     f'(under {sp["floor"]:.1f} tok/s)' if sp["slow"] else "") + '.')
    return ('<p class="fn-legend"><span><span class="fn-key keep"></span>kept</span>'
            '<span><span class="fn-key ref"></span>reference (baseline)</span>'
            '<span><span class="fn-key cut"></span>cut by scope (not measured)</span>'
            '<span><span class="fn-key fail"></span>failed a measurement</span></p>'
            '<p class="c-note">Grey means the setup never got the full 32K / 128K test.'
            f'{smoked} Smoke decode = the median of the identical, append and tool-turn requests at 8K '
            f'(the same warm-decode definition as every decode number on this page){f", thinking effort {eff}" if eff else ""}, '
            f'{run}. Agent turn times in the funnel are at thinking effort xhigh, the only effort the baseline has '
            'at 128K; failed = slower than the baseline.</p>')


def _funnel_heading(p: dict) -> str:
    st = p["funnel"]
    end = st[-1]["ids"]
    return (f'How {st[0]["count"]} candidate setups came down to '
            f'{SHORT.get(end[0], _name(end[0])) if end else "none faster than the baseline"}')


def _html_funnel(p: dict) -> str:
    sp = _smoke_split(p)
    n_never, n_smoked = len(sp["never"]), len(sp["smoked"])
    return ('<section class="block" id="funnel"><h2 class="sec">'
            f'{E(_funnel_heading(p))}</h2>'
            '<p class="s-note">Each step keeps the setups that can still be the fastest way to run the dense 27B. '
            f'{n_never} setups never ran: they were cut by choice to save rig time. '
            + (f'{n_smoked} ran the 8K smoke and were not taken further after it, so their smoke decode is all we '
               'have for them. ' if n_smoked else '')
            + 'The comparison with Flash-Next is in the TL;DR and the chart below.</p>'
            f'<div class="fn-wrap"><figure class="fn-fig">{funnel_svg(p)}</figure>'
            f'<div class="fn-side">{_funnel_legend(p)}</div></div></section>')


def _rows_for(p: dict, ctx: str) -> list[dict]:
    """Chart and table rows for one context: every measured setup × effort (missing ones kept as not measured),
    then the Flash-Next references."""
    rows = []
    for i in _setups(p):
        for eff in EFFORTS:
            d = (p["speed"].get(ctx) or {}).get(f"{i}-{eff}")
            if d is None and not any(f"{i}-{eff}" in (p["speed"].get(str(c)) or {}) for c in BANDS) \
                    and i != BASELINE:
                continue  # a setup that never ran this effort at any context
            rows.append({"id": i, "name": _name(i), "effort": eff, "data": d, "ref": False, "color": COLOR.get(i, "--s4")})
    for ref in ("w1", "n2"):
        d = (p.get(ref) or {}).get(ctx)
        if d and d.get("t_turno_s") is not None:
            rows.append({"id": ref, "name": REF_NAMES[ref], "effort": "xhigh", "data": d, "ref": True,
                         "color": COLOR[ref]})
    return rows


DEFAULT_EFFORTS = {"xhigh": True, "medium": False}  # medium shows only when the reader ticks it


def _off(r: dict) -> str:
    return "" if r["ref"] or DEFAULT_EFFORTS.get(r["effort"], True) else " off"


def _attrs(r: dict) -> str:
    return ' data-ref="flashnext"' if r["ref"] else f' data-effort="{r["effort"]}"'


def _tip(r: dict, ctx: str) -> str:
    d = r["data"]
    gen = REPLY_TOKENS / d["decode_tps"] if d.get("decode_tps") else None
    parts = [f'{r["name"]} · thinking effort: {r["effort"]} · {_ctx_lab(ctx)}',
             f'agent turn time {_fmt_s(d.get("t_turno_s"))}',
             f'warm TTFT (tool turn) {_fmt_s(d.get("warm_ttft_tool_s"))}',
             f'{REPLY_TOKENS} tokens {_fmt_s(gen)}' if gen is not None else f"{REPLY_TOKENS} tokens: not measured",
             f'decode {d["decode_tps"]:.1f} tok/s' if d.get("decode_tps") is not None else "decode: not measured",
             f'cold TTFT {_fmt_s(d.get("cold_ttft_s"))}',
             f'peak memory {d["wired_peak_gb"]:.1f} GB' if d.get("wired_peak_gb") is not None else "peak memory: not measured"]
    return " · ".join(parts)


def _bars(p: dict, ctx: str) -> str:
    rows = _rows_for(p, ctx)
    tot = [r["data"]["t_turno_s"] for r in rows if r["data"] and r["data"].get("t_turno_s") is not None]
    mx = (max(tot) if tot else 1) * 1.02
    out = ""
    for r in rows:
        d = r["data"]
        eff = f'<span class="eff">{"reference · " if r["ref"] else ""}effort: {r["effort"]}</span>'
        lab = (f'<span class="sb-lab"><span class="sw" style="background:var({r["color"]})"></span>'
               f'<span class="sb-txt"><span class="sb-name">{E(r["name"])}</span> {eff}</span></span>')
        if not d or d.get("t_turno_s") is None or not d.get("decode_tps") or d.get("warm_ttft_tool_s") is None:
            out += (f'<div class="sbar nm{_off(r)}"{_attrs(r)} title="{E(r["name"])} · thinking effort: {r["effort"]} · '
                    f'{_ctx_lab(ctx)}: not measured">{lab}<span class="sb-track"><span class="sb-nm">not measured'
                    f'</span></span><span class="sb-val na">—</span></div>')
            continue
        ttft, gen = d["warm_ttft_tool_s"], REPLY_TOKENS / d["decode_tps"]
        tip = _tip(r, ctx)
        out += (f'<div class="sbar{_off(r)}"{_attrs(r)} title="{E(tip)}" role="img" aria-label="{E(tip)}">{lab}'
                f'<span class="sb-track"><span class="seg ttft" style="width:{100 * ttft / mx:.2f}%;'
                f'background:var({r["color"]})"></span><span class="seg gen" style="width:{100 * gen / mx:.2f}%;'
                f'background:var({r["color"]})"></span></span>'
                f'<span class="sb-val">{d["t_turno_s"]:.1f} s</span></div>')
    if not rows:
        out = '<p class="empty">not measured</p>'
    return (f'<div class="sbars">{out}</div>'
            '<p class="sb-key"><span><span class="k ttft"></span>warm TTFT of the tool-result turn</span>'
            f'<span><span class="k gen"></span>{REPLY_TOKENS} tokens at the median decode speed</span>'
            '<span>hover a bar for decode, TTFT and memory; the table below has the same numbers</span></p>')


def _table(p: dict, ctx: str) -> str:
    body = ""
    for r in _rows_for(p, ctx):
        d = r["data"]
        lab = (f'<span class="sb-lab"><span class="sw" style="background:var({r["color"]})"></span>'
               f'<span class="sb-name">{E(r["name"])}</span></span>')
        effcell = f'{E(r["effort"])}{" (reference)" if r["ref"] else ""}'
        if not d or all(d.get(k) is None for k in SPEED_KEYS):
            body += (f'<tr{_attrs(r)}{' class="off"' if _off(r) else ""}><td>{lab}</td><td class="tx">{effcell}</td>'
                     f'<td colspan="8" class="tx"><span class="na">not measured</span></td></tr>')
            continue
        acc = ND(d.get("mtp_acceptance"), "{:.2f}")
        body += (f'<tr{_attrs(r)}{' class="off"' if _off(r) else ""}><td>{lab}</td><td class="tx">{effcell}</td>'
                 f'<td><b>{ND(d.get("t_turno_s"), "{:.1f}")}</b></td><td>{ND(d.get("warm_ttft_tool_s"), "{:.1f}")}</td>'
                 f'<td>{ND(d.get("cold_ttft_s"), "{:.1f}")}</td><td>{ND(d.get("prefill_tps"), "{:,.0f}")}</td>'
                 f'<td>{ND(d.get("decode_tps"), "{:.1f}")}</td><td>{ND(d.get("hit_tool"), "{:.2f}")}</td>'
                 f'<td>{acc}</td><td>{ND(d.get("wired_peak_gb"), "{:.1f}")}</td></tr>')
    if not body:
        body = '<tr><td colspan="10" class="tx"><span class="na">not measured</span></td></tr>'
    return ('<div class="tbl-scroll"><table class="speedt"><thead><tr><th>Setup</th><th class="tx">Thinking effort</th>'
            '<th>Agent turn time (s)</th><th>Warm TTFT, tool turn (s)</th><th>Cold TTFT (s)</th><th>Prefill (tok/s)</th>'
            '<th>Decode (tok/s)</th><th>Cache hit, tool turn</th><th>Draft / MTP acceptance</th><th>Peak memory (GB)</th>'
            f'</tr></thead><tbody>{body}</tbody></table></div>')


def _ctxs(p: dict) -> list[str]:
    return [str(c) for c in BANDS] + sorted(set(p["speed"]) - {str(c) for c in BANDS}, key=int)


def _html_results(p: dict) -> str:
    ctxs = _ctxs(p)
    default = "131072" if "131072" in ctxs else ctxs[0]
    tabs = "".join(f'<button type="button" role="tab" class="tab" data-ctx="{c}" '
                   f'aria-selected="{"true" if c == default else "false"}">{_ctx_lab(c)} context</button>' for c in ctxs)
    effs = "".join(f'<label class="chk"><input type="checkbox" data-effort-toggle="{e}"'
                   f'{" checked" if DEFAULT_EFFORTS.get(e, True) else ""}> {e}</label>' for e in EFFORTS)
    controls = (f'<div class="controls" role="group" aria-label="Chart controls">'
                f'<div class="ctl"><span class="ctl-h">Context</span><div class="tabs" role="tablist">{tabs}</div></div>'
                f'<div class="ctl"><span class="ctl-h">Thinking effort</span>{effs}</div>'
                '<div class="ctl"><label class="chk"><input type="checkbox" data-ref-toggle checked> '
                'show Flash-Next reference</label></div></div>')
    panels = ""
    for c in ctxs:
        cls = "" if c == default else " tab-off"
        panels += (f'<div class="ctx-panel{cls}" data-ctx-panel="{c}"><h3 class="c-head">{_ctx_lab(c)} context · '
                   'agent turn time, shorter is better</h3>'
                   f'{_bars(p, c)}{_table(p, c)}</div>')
    reps = sorted({d.get("reps") for rows in p["speed"].values() for d in rows.values() if d.get("reps")})
    rep_txt = f"median of {reps[0]} repetitions" if len(reps) == 1 else "median of the repetitions"
    return ('<section class="block" id="results"><h2 class="sec">Agent turn time at 32K and 128K</h2>'
            f'<p class="s-note">Each bar is one agent turn: {AGENT_TURN_DEF}, {rep_txt}. {EFFORT_SENTENCE} '
            'Only thinking effort xhigh shows by default; tick medium to add those rows. '
            'The Flash-Next rows are the reference we compare against (thinking effort xhigh, on '
            f'{REF_RUNTIME}).</p>{controls}{panels}'
            '<p class="s-note mt"><b>Peak memory (GB)</b> is the highest wired memory of the whole machine sampled '
            'during the run (model weights, KV cache and anything else the system pinned), not the server process '
            'alone. <b>Prefill</b> is prompt tokens of the cold request ÷ cold TTFT, read from the per-request results. '
            'The harness reads an acceptance rate only from mlx-serve (draft) and the Flash-Next references (MTP); '
            'the other cells are empty.</p>'
            f'<p class="quality-line">{QUALITY_LINE}</p></section>')


def _think_facts(p: dict) -> dict:
    k = [v for v in p.get("think", {}).values() if v["arm"] == "k27"]
    r = [v for v in p.get("think", {}).values() if v["arm"] == "r27d"]
    drop = [v["drop"]["ttft_s_median"] for v in k if v["drop"]["ttft_s_median"] is not None]
    rr = [x for v in r for m in ("resend", "drop") for x in (v[m]["ttft_s_min"], v[m]["ttft_s_max"]) if x is not None]
    return {"resend_400": sum(v["resend"]["http400"] for v in k), "resend_n": sum(v["resend"]["n"] for v in k),
            "efforts": sorted({v["effort"] for v in k}),
            "drop_err": sum(v["drop"]["errors"] for v in k), "drop_n": sum(v["drop"]["n"] for v in k),
            "drop_ttft": round(statistics.median(drop), 1) if drop else None,
            "r_min": min(rr) if rr else None, "r_max": max(rr) if rr else None,
            "r_per_mode": max((v[m]["n"] for v in r for m in ("resend", "drop")), default=None)}


def _html_run(p: dict) -> str:
    cmd = splash_command()
    t = _think_facts(p)
    s = p.get("sampling") or {}
    if cmd:
        rev, drev = cmd["revision"] or "", cmd["draft_rev"] or ""
        fl = cmd["flags"]
        draft_dl = (f'DRAFT_DIR="$HOME/models/Qwen3.8-27B-DFlash2"   # any absolute directory you choose\n'
                    f'hf download {cmd["draft_repo"]} --revision {drev} --local-dir "$DRAFT_DIR"\n'
                    if cmd["draft_repo"] and drev else
                    '# draft model: not found in the campaign launcher; set DRAFT_DIR to a local DFlash2 directory\n')
        shell = (
            f'# once: fill the Hugging Face cache (Splash wants a Hub ID for the target and --offline reads the cache)\n'
            f'hf download {cmd["model"]} --revision {rev}\n'
            f'{draft_dl}\n'
            f'# serve (Splash 1.3.1)\n'
            f'splash {fl.get("SPLASH_SERVE_SUBCMD", "serve")} {fl.get("SPLASH_FLAG_MODEL", "--model")} {cmd["model"]} '
            f'{fl.get("SPLASH_FLAG_HOST", "--host")} 0.0.0.0 {fl.get("SPLASH_FLAG_PORT", "--port")} {cmd["port"]} \\\n'
            f'  {fl.get("SPLASH_FLAG_CTX", "--max-context")} 131072 \\\n'
            f'  {fl.get("SPLASH_FLAG_REVISION", "--revision")} {rev} \\\n'
            f'  {fl.get("SPLASH_FLAG_DRAFTER", "--draft-model")} "$DRAFT_DIR" \\\n'
            f'  {cmd["extra"]}')
        ids = (f'<li>Target: <code>{E(cmd["model"])}</code> @ <code>{E(rev[:8])}</code> '
               f'(full revision <code>{E(rev)}</code>).</li>'
               + (f'<li>Draft: <code>{E(cmd["draft_repo"])}</code> @ <code>{E(drev[:8])}</code> '
                  f'(full revision <code>{E(drev)}</code>), passed as a local directory.</li>'
                  if cmd["draft_repo"] and drev else '<li>Draft: —</li>'))
    else:
        shell, ids = "# launcher files not found", ""
    samp = (f'temperature {s["temperature"]}, top_p {s["top_p"]}, top_k {s["top_k"]}' if s else "not recorded")
    body = {"model": cmd["model"] if cmd else "", "messages": [{"role": "user", "content": "..."}],
            "reasoning_effort": "medium", **({k: s[k] for k in ("temperature", "top_p", "top_k")} if s else {})}
    req = ("curl -s http://localhost:" + (cmd["port"] if cmd else "8585") + "/v1/chat/completions \\\n"
           "  -H 'Content-Type: application/json' \\\n  -d '" + json.dumps(body) + "'")
    if t["resend_n"]:
        warn = (f'<div class="warnbox"><p><b>Do not resend the reasoning.</b> At 128K, Splash 1.3.1 returned '
                f'<b>HTTP 400</b> on every tool turn that sent the previous <code>reasoning_content</code> back '
                f'({t["resend_400"]} of {t["resend_n"]}, thinking effort {" and ".join(t["efforts"])}). '
                + (f'Without it, {t["drop_n"] - t["drop_err"]} of {t["drop_n"]} worked'
                   + (f', with a TTFT of {t["drop_ttft"]:.1f} s. ' if t["drop_ttft"] is not None else '. ')
                   if t["drop_n"] else '') +
                'Configure your client to drop <code>reasoning_content</code> from earlier assistant messages.</p></div>')
    else:
        warn = '<p class="s-note">The thinking-turn probe was not run.</p>'
    return ('<section class="block" id="run"><h2 class="sec">Run it yourself</h2>'
            '<p class="s-note">The exact Splash 1.3.1 launch of the fastest setup, rebuilt from the campaign launcher. '
            'KV cache: int8, the Splash 1.3.1 default (<code>--kv-format</code>, not passed). '
            '<code>--idle-release off</code> keeps the model loaded; <code>--language-only</code> skips the vision '
            'tower.</p>'
            f'<ul class="s-note">{ids}<li>Sampling (the vendor settings, sent with every request): {E(samp)}.</li>'
            '<li>Thinking effort: send <code>reasoning_effort</code> at the top level of the request body; '
            'medium gave the shorter turns here.</li></ul>'
            f'<pre class="cmd"><code>{E(shell)}</code></pre>'
            f'<pre class="cmd"><code>{E(req)}</code></pre>{warn}</section>')


def _html_hw(p: dict) -> str:
    measured = [a for a in p["arms"] if a["id"] in _setups(p)]
    runtimes = ", ".join(dict.fromkeys(a["runtime"] for a in measured))
    weights = "".join(f'<li>{E(a["public"])}: <code>{E(WEIGHTS.get(a["id"], a["pack"]))}</code> @ '
                      f'<code>{E(a["rev"])}</code></li>' for a in measured)
    reps = sorted({d.get("reps") for rows in p["speed"].values() for d in rows.values() if d.get("reps")})
    macos = p.get("macos")
    return ('<section class="block" id="hw"><h2 class="sec">Hardware and software</h2><ul class="s-note">'
            '<li>Apple M4 Max, 128 GB unified memory, one machine.</li>'
            f'<li>macOS {E(macos) if macos else "version not recorded"}.</li>'
            f'<li>27B servers: {E(runtimes or "none measured")}. Flash-Next references: {E(REF_RUNTIME)}.</li>'
            f'{weights}'
            f'<li>{reps[0] if len(reps) == 1 else "Several"} repetitions per setup, thinking effort and context; '
            'every number is the median.</li></ul></section>')


def _html_limits(p: dict) -> str:
    sp = p["speed"]
    gain = []
    for c in BANDS:
        k = ((sp.get(str(c)) or {}).get("k27-xhigh") or {}).get("prefill_tps")
        b = ((sp.get(str(c)) or {}).get(f"{BASELINE}-xhigh") or {}).get("prefill_tps")
        gain.append(f"+{100 * (k / b - 1):.0f}% at {_ctx_lab(c)}" if k and b else None)
    gain_li = (f'<li>Splash prefills faster than the baseline ({", ".join(gain)}, same weights). The vendor '
               'credits a GPU + Neural Engine (ANE) prefill split; our harness does not record whether the ANE ran, '
               'so that cause is the vendor\'s claim only.</li>') if None not in gain else ""
    t = _think_facts(p)
    r128 = ((sp.get("131072") or {}).get("r27d-xhigh") or {}).get("warm_ttft_tool_s")
    rn = t["r_per_mode"]
    per = "one request per mode" if rn == 1 else f"{rn} requests per mode" if rn else "few requests"
    mlx_li = (f'<li>mlx-serve 26.10.2: the tool-turn TTFT in the thinking-turn probe was {t["r_min"]:.0f}–'
              f'{t["r_max"]:.0f} s ({per}, resend and drop), against {r128:.1f} s in the cache probe at the same '
              '128K. We have no explanation.</li>') if t["r_min"] is not None and r128 is not None else ""
    reps = sorted({d.get("reps") for rows in sp.values() for d in rows.values() if d.get("reps")})
    return ('<section class="block" id="limits"><h2 class="sec">Limitations</h2><ul class="s-note">'
            '<li>One machine (M4 Max, 128 GB). Other Macs will differ.</li>'
            f'<li>{reps[0] if len(reps) == 1 else "A few"} repetitions per point; medians, no confidence intervals.</li>'
            '<li>The agent turn is a synthetic probe (a long document, a tool result, a reply), not a real task.</li>'
            '<li>Quality was not measured: a fast setup is not known to answer as well as the others.</li>'
            f'{gain_li}{mlx_li}</ul></section>')


# Setups cut from the campaign (user scope, 2026-10-13/14). Shown only in the appendix, with the codes.
NOT_RUN = {
    "o27q8": "oMLX with the oQ8e refit pack. Cut by scope B (stop after P1 unless Splash passes at 128K).",
    "o27q4": "oMLX with the oQ4e refit pack. Only the 8K smoke ran. Cut by scope B.",
    "o27sw": "Swift 1.5 on oMLX. Cut with the rest of P4.",
    "w27d": "Swift 1.5 on mlx-serve with the drafter: cancelled after r27d failed on the same runtime and drafter.",
    "r27m": "MTP head only on mlx-serve. Only the 8K smoke ran (slow decode). Cut.",
    "w27m": "Swift 1.5 MTP only on mlx-serve. Cut with r27m.",
    "l27": "llama.cpp draft-mtp. Only the 8K smoke ran (slow decode). Cut.",
    "l27n": "llama.cpp without speculation. Cut with l27.",
}

GATE_DOC = {
    "P1_PASS": "Splash (k27): T_turno ≤ 0.75 × s27r at 128K and gates",
    "P2_PASS": "oMLX refit packs: T_turno ≤ s27r",
    "P3_PASS": "mlx-serve 26.10.2: T_turno ≤ s27r",
    "P4_PASS": "Swift 1.5 27B (o27sw): T_turno ≤ 1.03 × o27q4",
    "P7_PASS": "w27d at or under 1.03 × r27d on both bands",
    "P8_PASS": "r27m or w27m at or under s27r on both bands",
    "P7_SMOKE": "8K smoke passed (reasoning, spec-stats mode, decode ≥ 60 tok/s)",
    "P8_SMOKE_w27m": "8K smoke passed (reasoning, spec-stats mode, decode ≥ 60 tok/s)",
    "P6_PASS": "llama.cpp draft-mtp: T_turno ≤ s27r at 32K",
    "P5_GO": "Driver gate: fastest arm within 1.25 × w1 on both bands (0 = none)",
    "CAMPAIGN_DONE": "Campaign finished (UTC)",
}


def _html_appendix(p: dict) -> str:
    rows = "".join(f'<tr><td class="code">{E(a["id"])}</td><td>{E(a["public"])}</td><td>{E(a["name"])}</td>'
                   f'<td>{E(a["runtime"])}</td><td>{E(a["pack"])}</td><td><code>{E(a["rev"])}</code></td>'
                   f'<td>{E(a["port"])}</td><td>{E(a["phase"])}</td></tr>' for a in p["arms"])
    rows += "".join(f'<tr><td class="code">{k}</td><td>{E(v)}</td><td>Flash-Next reference (xhigh)</td>'
                    f'<td>{E(REF_RUNTIME)}</td><td></td><td></td><td></td><td></td></tr>' for k, v in REF_NAMES.items())
    g = p["gates"]
    grows = "".join(
        f'<tr><td><code>{E(k)}</code></td><td>{E(v)}</td>'
        f'<td>{E(GATE_DOC.get(k) or (f"Best arm of {k.split(chr(95))[0]}" if k.endswith("_BEST") else ""))}</td></tr>'
        for k, v in g.items()) or '<tr><td colspan="3">not measured</td></tr>'
    smoke = "".join(f'<li><code>{E(i)}</code>: warm decode {v["decode_tps"]:.1f} tok/s, T_turno 8K '
                    f'{_fmt_s(v["t_turno_s"])}</li>' for i, v in p.get("smoke", {}).items()
                    if v.get("decode_tps") is not None)
    cut = "".join(f'<li><code>{E(i)}</code>: {E(why)}</li>' for i, why in NOT_RUN.items())
    think = "".join(f'<li><code>{E(k)}</code>: resend {v["resend"]["errors"]}/{v["resend"]["n"]} errors, '
                    f'drop {v["drop"]["errors"]}/{v["drop"]["n"]} errors, drop TTFT {_fmt_s(v["drop"]["ttft_s_median"])}'
                    '</li>' for k, v in p.get("think", {}).items())
    return ('<details class="block raw" id="raw"><summary>Raw data and reproduction</summary>'
            '<p class="s-note">Internal codes used in the campaign files. "T_turno" is the agent turn time; '
            '<code>p&lt;N&gt;x</code> / <code>p&lt;N&gt;m</code> file tags mark the phase and the effort (xhigh / medium).</p>'
            '<div class="tbl-scroll"><table class="cfg arms"><thead><tr><th>Code</th><th>Public name</th><th>Campaign name</th>'
            '<th>Runtime</th><th>Pack</th><th>Revision</th><th>Port</th><th>Phase</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            '<p class="s-note mt">Raw gates from <code>results/gates.env</code>:</p>'
            '<div class="tbl-scroll"><table class="cfg"><thead><tr><th>Gate</th><th>Value</th><th>Meaning</th></tr>'
            f'</thead><tbody>{grows}</tbody></table></div>'
            f'<p class="s-note mt">8K smokes (warm decode as in <code>summarize_driver.py</code>):</p><ul class="s-note">{smoke or "<li>none</li>"}</ul>'
            f'<p class="s-note mt">Setups not run (cut on 2026-10-13/14), by user scope:</p><ul class="s-note">{cut}</ul>'
            f'<p class="s-note mt">Thinking-turn probe at 128K:</p><ul class="s-note">{think or "<li>not run</li>"}</ul>'
            '<p class="s-note mt">Run the campaign on the rig with '
            '<code>bash bench/qwen38-27b-next-steps-2026-10/scripts/run-campaign.sh</code>, then render this page with '
            '<code>python3 bench/qwen38-27b-next-steps-2026-10/scripts/render_27b_page.py --png</code>. '
            f'Scripts and per-request results: <a href="{CAMPAIGN_URL}">{E(CAMPAIGN_URL.split("//")[1])}</a>.</p>'
            '</details>')


PAGE_CSS = r"""
:root{--ref-b:#7a4fd1; --cut:#a8a69d; --fail:#d0453b}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ref-b:#a78bf0; --cut:#6f6e68; --fail:#ef6b5f}}
:root[data-theme="dark"]{--ref-b:#a78bf0; --cut:#6f6e68; --fail:#ef6b5f}
.mt{margin-top:14px}
.u{color:var(--muted); font-size:0.9em; margin-left:2px}
a{color:var(--accent)}
.wrap{max-width:1100px}
h3.c-head{margin:16px 0 4px; font-size:0.95rem}
.c-note{margin:6px 0 0; font-size:0.8rem; color:var(--ink-2)}
.empty{color:var(--muted); font-size:0.88rem; margin:8px 0 0}
.s-note code, .c-note code, .warnbox code{font-family:var(--mono); font-size:0.9em; background:var(--surface-2); padding:1px 5px; border-radius:4px}
ul.s-note{padding-left:18px} ul.s-note li{margin:4px 0}
/* TL;DR */
.tldr-wrap{display:grid; grid-template-columns:minmax(0,1.7fr) minmax(0,1fr); gap:14px; align-items:start}
.tldr{background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--s2); border-radius:12px; padding:14px 18px}
.tl-h, .nm-h{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); margin:0 0 6px}
.tl-line{margin:6px 0; font-size:0.98rem; line-height:1.5}
.tl-line dfn{font-style:normal; font-weight:600}
.nm-box{background:var(--warn-bg); border:1px solid var(--border); border-radius:12px; padding:14px 18px; font-size:0.86rem; color:var(--ink-2)}
.nm-box ul{margin:0; padding-left:18px} .nm-box li{margin:5px 0} .nm-box b{color:var(--ink)}
/* glossary */
dl.gloss{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr)); gap:6px 22px; margin:8px 0 0}
dl.gloss div{font-size:0.86rem; color:var(--ink-2); line-height:1.4}
dl.gloss dt{display:inline; font-weight:700; color:var(--ink)} dl.gloss dt::after{content:": "}
dl.gloss dd{display:inline; margin:0}
/* funnel */
.fn-wrap{display:grid; grid-template-columns:minmax(0,480px) minmax(0,1fr); gap:20px; align-items:start}
.nm-sub{margin:4px 0 0; padding-left:16px} .nm-sub li{margin:2px 0}
figure.fn-fig{margin:0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px}
svg.funnel{width:100%; max-width:440px; height:auto; display:block; margin:0 auto; font-family:var(--sans)}
.fn-bar{fill:var(--accent)} .fn-zero{fill:none; stroke:var(--muted); stroke-dasharray:5 4; stroke-width:1.5}
.fn-n{fill:#fff; font-size:18px; font-weight:700} .fn-n0{fill:var(--ink-2); font-size:18px; font-weight:700}
.fn-lab{fill:var(--ink); font-size:16px; font-weight:700} .fn-det{fill:var(--ink-2); font-size:13.5px}
.fn-grp{fill:var(--muted); font-size:13.5px; font-style:italic}
.fn-name{fill:var(--ink); font-size:14.5px; font-weight:600} .fn-name.cut{fill:var(--ink-2); font-weight:400}
.fn-note{fill:var(--ink-2); font-size:13.5px}
.fn-sw.cut, .fn-key.cut{fill:var(--cut); background:var(--cut)} .fn-sw.fail, .fn-key.fail{fill:var(--fail); background:var(--fail)}
.fn-sw.keep, .fn-key.keep{fill:var(--accent); background:var(--accent)}
.fn-sw.ref{fill:var(--plane); stroke:var(--accent); stroke-width:2} .fn-key.ref{background:transparent; box-shadow:inset 0 0 0 2px var(--accent)}
.fn-arrow{fill:none; stroke:var(--muted); stroke-width:2}
.fn-legend{display:flex; flex-wrap:wrap; gap:8px 18px; margin:0; font-size:0.88rem; color:var(--ink)}
.fn-legend > span{display:inline-flex; align-items:center; gap:7px}
.fn-key{display:inline-block; width:13px; height:13px; border-radius:3px}
/* controls */
.controls{display:none; flex-wrap:wrap; gap:10px 22px; align-items:center; margin:6px 0 4px; padding:10px 14px;
  background:var(--surface); border:1px solid var(--border); border-radius:10px}
html.js .controls{display:flex}
.ctl{display:flex; align-items:center; gap:10px; flex-wrap:wrap}
.ctl-h{font-family:var(--mono); font-size:0.7rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--muted)}
.tabs{display:inline-flex; border:1px solid var(--border); border-radius:8px; overflow:hidden}
.tab{font:inherit; font-size:0.84rem; padding:5px 12px; border:0; background:var(--surface); color:var(--ink-2); cursor:pointer}
.tab[aria-selected="true"]{background:var(--accent); color:#fff}
.tab:focus-visible, .chk input:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
.chk{display:inline-flex; align-items:center; gap:5px; font-size:0.86rem; color:var(--ink); cursor:pointer}
html.js .tab-off{display:none}
.off{display:none!important}
/* stacked bars */
.ctx-panel{margin-top:6px}
.sbars{margin-top:8px; display:grid; gap:7px}
.sbar{display:grid; grid-template-columns:minmax(0,300px) minmax(0,1fr) 64px; gap:10px; align-items:center}
.sb-lab{display:flex; align-items:center; gap:7px; min-width:0; font-size:0.84rem; line-height:1.3}
.sb-lab .sw{width:10px; height:10px; border-radius:2px; flex:none}
.sb-txt{min-width:0}
.sb-txt .eff{white-space:nowrap}
.sb-name{font-weight:600; color:var(--ink)}
.eff{font-family:var(--mono); font-size:0.7rem; color:var(--muted)}
.sb-track{position:relative; display:flex; height:20px; background:var(--surface-2); border-radius:0 5px 5px 0; overflow:hidden}
.seg{display:block; height:100%} .seg.gen{opacity:0.45}
.sb-nm{font-size:0.78rem; color:var(--muted); align-self:center; padding-left:8px; font-style:italic}
.sb-val{font-family:var(--mono); font-size:0.84rem; text-align:right; color:var(--ink); font-weight:600}
.sb-key{display:flex; flex-wrap:wrap; gap:6px 18px; margin:10px 0 12px; font-size:0.78rem; color:var(--ink-2)}
.sb-key > span{display:inline-flex; align-items:center; gap:6px}
.sb-key .k{display:inline-block; width:18px; height:10px; border-radius:2px; background:var(--ink-2)}
.sb-key .k.gen{opacity:0.45}
table.speedt{min-width:980px}
table.speedt td:first-child{min-width:230px} table.speedt th{min-width:84px; vertical-align:bottom}
td.tx, th.tx{font-family:var(--sans); text-align:left; color:var(--ink-2)}
.quality-line{margin:14px 0 0; padding:10px 14px; border:1px dashed var(--baseline); border-radius:10px; font-size:0.9rem; color:var(--ink)}
/* run it */
pre.cmd{background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 14px; overflow-x:auto;
  font-family:var(--mono); font-size:0.8rem; line-height:1.5; margin:10px 0}
.warnbox{background:var(--warn-bg); border:1px solid var(--warn); border-radius:10px; padding:10px 14px; font-size:0.9rem; color:var(--ink)}
.warnbox p{margin:0}
/* appendix */
details.raw{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 16px}
details.raw summary{cursor:pointer; font-weight:700}
details.raw[open] summary{margin-bottom:10px}
table.cfg td, table.cfg th{text-align:left; font-family:var(--sans); font-size:0.82rem}
table.cfg code{font-family:var(--mono); font-size:0.9em}
td.code{font-family:var(--mono)!important; font-weight:700; color:var(--ink)}
table.arms{min-width:900px}
@media (max-width:860px){.tldr-wrap, .fn-wrap{grid-template-columns:minmax(0,1fr)}}
@media (max-width:620px){
  .wrap{padding:24px 16px 48px}
  .sbar{grid-template-columns:minmax(0,1fr) 56px; grid-template-areas:"lab lab" "track val"; gap:3px 8px}
  .sbar .sb-lab{grid-area:lab} .sbar .sb-track{grid-area:track} .sbar .sb-val{grid-area:val}
  h1{font-size:1.4rem}
  figure.fn-fig{padding:6px}
}
"""

JS = r"""
(function(){
  const root=document.documentElement; root.classList.add("js");
  const KEY="__KEY__";
  const DEF_EFF=__DEFEFF__;
  let st={effort:Object.assign({}, DEF_EFF), ctx:"__DEFAULT__", ref:true};
  try{ const s=JSON.parse(localStorage.getItem(KEY)||"null");
       if(s && typeof s==="object"){ st=Object.assign(st, s); st.effort=Object.assign({}, DEF_EFF, s.effort||{}); } }catch(e){}
  if(!document.querySelector('[data-ctx-panel="'+st.ctx+'"]')) st.ctx="__DEFAULT__";
  function save(){ try{ localStorage.setItem(KEY, JSON.stringify(st)); }catch(e){} }
  function apply(){
    document.querySelectorAll("[data-effort]").forEach(el=>el.classList.toggle("off", !st.effort[el.dataset.effort]));
    document.querySelectorAll("[data-ref]").forEach(el=>el.classList.toggle("off", !st.ref));
    document.querySelectorAll("[data-ctx-panel]").forEach(el=>el.classList.toggle("tab-off", el.dataset.ctxPanel!==st.ctx));
    document.querySelectorAll(".tab[data-ctx]").forEach(b=>b.setAttribute("aria-selected", String(b.dataset.ctx===st.ctx)));
    document.querySelectorAll("[data-effort-toggle]").forEach(c=>{ c.checked=!!st.effort[c.dataset.effortToggle]; });
    document.querySelectorAll("[data-ref-toggle]").forEach(c=>{ c.checked=st.ref; });
  }
  document.querySelectorAll(".tab[data-ctx]").forEach(b=>b.addEventListener("click", ()=>{ st.ctx=b.dataset.ctx; apply(); save(); }));
  document.querySelectorAll("[data-effort-toggle]").forEach(c=>c.addEventListener("change", ()=>{ st.effort[c.dataset.effortToggle]=c.checked; apply(); save(); }));
  document.querySelectorAll("[data-ref-toggle]").forEach(c=>c.addEventListener("change", ()=>{ st.ref=c.checked; apply(); save(); }));
  apply();
  const btn=document.getElementById("themeBtn");
  function applyLabel(){ btn.textContent="theme: "+(root.getAttribute("data-theme")||"auto"); }
  btn.addEventListener("click",()=>{
    const cur=root.getAttribute("data-theme");
    const next=cur==null?"light":cur==="light"?"dark":null;
    if(next) root.setAttribute("data-theme",next); else root.removeAttribute("data-theme");
    try{ next?localStorage.setItem("theme",next):localStorage.removeItem("theme"); }catch(e){}
    applyLabel();
  });
  try{ const saved=localStorage.getItem("theme"); if(saved) root.setAttribute("data-theme",saved); }catch(e){}
  applyLabel();
})();
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Qwen3.8-27B servers on an M4 Max</title>
<meta name="description" content="__DESC__">
<meta property="og:type" content="article">
<meta property="og:title" content="__OGTITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="__PAGEURL__">
<meta property="og:image" content="__CARDURL__">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
/*__CSS__*/
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Qwen3.8-27B dense · Apple M4 Max 128 GB · October 2026</p>
      <h1>Dense Qwen3.8-27B on an M4 Max: which server runs it fastest?</h1>
      <p class="sub">Three local servers measured with the same agent-turn test at 32K and 128K context, against
      Qwen3.8-Flash-Next, the model we use every day.</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>
__BODY__
  <footer id="foot">Generated <code>__GENERATED__</code> from the per-request results by
  <code>render_27b_page.py</code>. Source: <a href="__REPO__">__REPOTXT__</a>.</footer>
</div>
<script>
__JS__
</script>
</body>
</html>
"""


def _desc(p: dict) -> str:
    f = facts(p)
    if not f:
        return ("Agent turn time of the dense Qwen3.8-27B on three local servers on an Apple M4 Max 128 GB, "
                "against Qwen3.8-Flash-Next.")
    return (f"Splash 1.3.1 + DFlash2 runs the dense Qwen3.8-27B fastest on an M4 Max 128 GB: {f['k_x']:.1f} s per agent "
            f"turn at 128K (xhigh), {f['vs_base']:.2f}× the mlx-dspark baseline, still ~{f['vs_w1_round']}× "
            "Qwen3.8-Flash-Next.")


def _og_title(p: dict) -> str:
    f = facts(p)
    tail = f": Splash 1.3.1 is the fastest server, Flash-Next still ~{f['vs_w1_round']}× faster for agent loops" if f else ""
    return "Dense Qwen3.8-27B on an M4 Max 128 GB" + tail


def render_html(p: dict) -> str:
    body = (_html_tldr(p) + _html_glossary() + _html_funnel(p) + _html_results(p) + _html_run(p) + _html_hw(p)
            + _html_limits(p) + _html_appendix(p))
    ctxs = _ctxs(p)
    default = "131072" if "131072" in ctxs else ctxs[0]
    parts = {
        "/*__CSS__*/": PERF_CSS + PERF_EXTRA_CSS + PAGE_CSS,
        "__JS__": JS.replace("__KEY__", STATE_KEY).replace("__DEFAULT__", default)
                     .replace("__DEFEFF__", json.dumps(DEFAULT_EFFORTS)),
        "__BODY__": body, "__DESC__": E(_desc(p)), "__OGTITLE__": E(_og_title(p)),
        "__PAGEURL__": PAGE_URL, "__CARDURL__": CARD_URL, "__REPO__": REPO_URL,
        "__REPOTXT__": E(REPO_URL.split("//")[1]), "__GENERATED__": E(p.get("generated_at", "")),
    }
    html = TEMPLATE
    for k, v in parts.items():
        html = html.replace(k, v)
    return html


# ---------------------------------------------------------------- card, post image, Reddit post

CARD_FIXED = {"--s1": "#2a78d6", "--s2": "#eb6834", "--s5": "#e87ba4", "--s3": "#1baf7a", "--ref-b": "#7a4fd1"}


def render_card(p: dict) -> str:
    """1200×630 link-preview card: agent turn time at 128K per setup and effort, plus the three headline numbers."""
    f = facts(p)
    rows = [r for r in _rows_for(p, "131072") if r["data"] and r["data"].get("t_turno_s") is not None
            and r["id"] != "n2"]
    rows.sort(key=lambda r: r["data"]["t_turno_s"])
    top = max((r["data"]["t_turno_s"] for r in rows), default=1)
    bars = ""
    for i, r in enumerate(rows):
        y = 34 + i * 44
        w = 290 * r["data"]["t_turno_s"] / top
        name = "Flash-Next (daily model)" if r["ref"] else SHORT.get(r["id"], r["name"])
        bars += (f'<text x="0" y="{y + 19}" class="lab">{E(name)}<tspan class="eff"> {E(r["effort"])}</tspan></text>'
                 f'<rect x="300" y="{y}" width="{w:.0f}" height="26" rx="4" fill="{CARD_FIXED[r["color"]]}"/>'
                 f'<text x="{300 + w + 10:.0f}" y="{y + 19}" class="val">{r["data"]["t_turno_s"]:.1f} s</text>')
    h = 34 + len(rows) * 44
    tiles = ""
    if f:
        tiles = (f'<div class="tile"><span class="t-val">{f["k_x"]:.1f}<small> s</small> / {f["k_m"]:.1f}<small> s</small></span>'
                 '<span class="t-lab">Splash 1.3.1 agent turn at 128K, thinking effort xhigh / medium</span></div>'
                 f'<div class="tile"><span class="t-val">{f["vs_base"]:.2f}×</span><span class="t-lab">the mlx-dspark baseline '
                 '(same weights, same draft)</span></div>'
                 f'<div class="tile"><span class="t-val">~{f["vs_w1_round"]}×</span><span class="t-lab">Qwen3.8-Flash-Next: '
                 'still faster for agent loops</span></div>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Card</title>
<style>
html,body{{margin:0; width:1200px; height:630px; background:#fbfaf7; color:#15171b;
  font-family:-apple-system,"SF Pro Text","Inter",Helvetica,Arial,sans-serif}}
.card{{width:1200px; height:630px; padding:50px 60px; box-sizing:border-box}}
.eyebrow{{font-family:"SF Mono",Menlo,monospace; font-size:17px; letter-spacing:0.14em; text-transform:uppercase; color:#6b7280; margin:0 0 12px}}
h1{{font-size:46px; line-height:1.1; letter-spacing:-0.025em; margin:0}}
.row{{display:flex; gap:40px; margin-top:34px; align-items:flex-start}}
svg{{flex:none}}
.lab{{font-size:19px; font-weight:600; fill:#15171b}} .eff{{font-weight:400; fill:#6b7280; font-size:16px}}
.val{{font-family:"SF Mono",Menlo,monospace; font-size:18px; fill:#15171b}}
.axis{{font-size:16px; fill:#6b7280}}
.tiles{{display:grid; gap:12px; flex:1}}
.tile{{background:#f0eee8; border-radius:12px; padding:12px 18px}}
.t-val{{font-size:36px; font-weight:700; letter-spacing:-0.02em; display:block}}
.t-val small{{font-size:18px; font-weight:600; color:#444a55}}
.t-lab{{font-size:16px; color:#444a55; line-height:1.3}}
</style></head><body><div class="card">
<p class="eyebrow">Benchmark · Apple M4 Max 128 GB · October 2026</p>
<h1>Dense Qwen3.8-27B on an M4 Max: which local server runs it fastest?</h1>
<div class="row">
  <svg width="680" height="{h}" viewBox="0 0 680 {h}"><text x="0" y="18" class="axis">Agent turn time at 128K · seconds · shorter is better</text>{bars}</svg>
  <div class="tiles">{tiles}</div>
</div>
</div></body></html>
"""


POST_CSS = r"""
html,body{margin:0; width:__W__px; min-height:__H__px; background:var(--plane)}
.wrap{max-width:none; width:__W__px; padding:44px 52px; box-sizing:border-box}
.post-grid{display:grid; grid-template-columns:400px minmax(0,1fr); gap:28px; margin-top:22px; align-items:start}
.post-grid figure.fn-fig{padding:12px}
.post-foot{margin-top:18px; font-size:15px; color:var(--muted); display:flex; justify-content:space-between}
.tldr .tl-line{font-size:1.05rem}
h1{font-size:2.1rem}
.sbar{grid-template-columns:330px minmax(0,1fr) 64px}
"""


def render_post(p: dict) -> str:
    """The Reddit post image: TL;DR, the funnel and the main chart at 128K and 32K (static, light theme)."""
    charts = "".join(f'<h3 class="c-head">{_ctx_lab(c)} context · agent turn time, shorter is better</h3>{_bars(p, c)}'
                     for c in ("131072", "32768") if c in p["speed"])
    css = (PERF_CSS + PERF_EXTRA_CSS + PAGE_CSS + POST_CSS).replace("__W__", str(POST_W)).replace("__H__", str(POST_H))
    return f"""<!doctype html>
<html lang="en" data-theme="light"><head><meta charset="utf-8"><title>Post image</title>
<style>{css}</style></head><body><div class="wrap">
<header><div><p class="eyebrow">Benchmark · Apple M4 Max 128 GB · October 2026</p>
<h1>Dense Qwen3.8-27B on an M4 Max: which local server runs it fastest?</h1></div></header>
{_html_tldr(p)}
<div class="post-grid">
  <div><h2 class="sec">{E(_funnel_heading(p))}</h2>
  <figure class="fn-fig">{funnel_svg(p)}</figure>{_funnel_legend(p)}</div>
  <div><h2 class="sec">Agent turn time</h2><p class="s-note">{AGENT_TURN_DEF}. {EFFORT_SENTENCE}</p>{charts}
  <p class="quality-line">{QUALITY_LINE}</p></div>
</div>
<p class="post-foot"><span>Median of the repetitions · per-request results in the repo</span>
<span>{E(PAGE_URL.split("//")[1])}</span></p>
</div></body></html>
"""


def render_reddit(p: dict) -> str:
    f = facts(p)
    title = ("Dense Qwen3.8-27B on an M4 Max 128 GB: Splash 1.3.1 is the fastest of 3 servers, but Qwen3.8-Flash-Next "
             f"is still ~{f['vs_w1_round']}× faster for agent loops" if f else "Dense Qwen3.8-27B on an M4 Max 128 GB")
    lines = [f"# {title}", ""]
    if f:
        lines += ["**TL;DR**", "",
                  f"- Fastest setup: **Splash 1.3.1 + DFlash2** (8-bit weights). Agent turn time at 128K: "
                  f"**{f['k_x']:.1f} s** at thinking effort xhigh, **{f['k_m']:.1f} s** at medium.",
                  f"- **{f['vs_base']:.2f}×** the baseline (mlx-dspark 0.20.3 + DFlash2, same weights and draft, "
                  f"{f['base']:.1f} s at xhigh).",
                  f"- Still **~{f['vs_w1_round']}×** Qwen3.8-Flash-Next, our daily model ({f['w1']:.1f} s; "
                  f"{f['vs_w1_x']:.2f}× at xhigh, {f['vs_w1_m']:.2f}× at medium): for agent loops, Flash-Next is still faster.",
                  ""]
    lines += [f"Agent turn time = {AGENT_TURN_DEF}. Median of the repetitions on one machine; shorter is better.", "",
              "| Setup | Thinking effort | 32K | 128K |", "|---|---|---:|---:|"]
    for i in _setups(p):
        for eff in EFFORTS:
            v = [_t(p, f"{i}-{eff}", c) for c in BANDS]
            if all(x is None for x in v) and i != BASELINE:
                continue
            lines.append(f"| {_name(i)} | {eff} | {_fmt_s(v[0])} | {_fmt_s(v[1])} |")
    for ref in ("w1", "n2"):
        v = [_ref_t(p, ref, c) for c in BANDS]
        if any(x is not None for x in v):
            lines.append(f"| {REF_NAMES[ref]}, reference on {REF_RUNTIME} | xhigh | {_fmt_s(v[0])} | {_fmt_s(v[1])} |")
    t = _think_facts(p)
    lines += ["", f"Full page (selection funnel, every number, how to run it): {PAGE_URL}", ""]
    if t["resend_n"]:
        lines += [f"**If you run it on Splash 1.3.1:** do not resend `reasoning_content` in earlier assistant messages. "
                  f"At 128K every tool turn that did got HTTP 400 ({t['resend_400']}/{t['resend_n']})"
                  + (f"; without it {t['drop_n'] - t['drop_err']}/{t['drop_n']} worked"
                     + (f" (TTFT {t['drop_ttft']:.1f} s)" if t['drop_ttft'] is not None else "") if t['drop_n'] else "")
                  + ".", ""]
    st = p["funnel"]
    reps = sorted({d.get("reps") for rows in p["speed"].values() for d in rows.values() if d.get("reps")})
    rep = f"{reps[0]} repetitions per point (median)" if len(reps) == 1 else "few repetitions per point"
    lines += [f"**Limitations.** One M4 Max 128 GB; {rep}; a synthetic agent-turn probe, not a real "
              "task. Quality and per-task time were not measured for the 27B. "
              f"{len(_smoke_split(p)['never']) + len(_smoke_split(p)['smoked'])} of the {st[0]['count']} candidate setups "
              f"never got the full test ({len(_smoke_split(p)['never'])} never ran; "
              f"{len(_smoke_split(p)['smoked'])} ran only an 8K smoke). "
              "The Splash prefill gain over the baseline is attributed to the Neural Engine by the vendor only.", ""]
    return "\n".join(lines)


def write_png(page: Path, png: Path, size: tuple[int, int] = (1200, 630), scale: int = 1) -> bool:
    """Render a static page with headless Chrome. Returns False when Chrome is not installed."""
    import subprocess
    if not CHROME.is_file():
        return False
    subprocess.run([str(CHROME), "--headless=new", "--hide-scrollbars", f"--window-size={size[0]},{size[1]}",
                    f"--force-device-scale-factor={scale}", f"--screenshot={png}", page.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=C / "results")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/qwen38-27b-stacks.html")
    ap.add_argument("--json-out", type=Path, default=C / "results/page-data.json")
    ap.add_argument("--card", type=Path, default=CARD_HTML, help="the link-preview card HTML (og:image source)")
    ap.add_argument("--post", type=Path, default=POST_HTML, help="the Reddit post image HTML")
    ap.add_argument("--reddit-out", type=Path, default=C / "results/reddit-post.md")
    ap.add_argument("--png", action="store_true", help="also render the card and post PNGs with headless Chrome")
    ap.add_argument("--no-w1", action="store_true", help="leave out both Flash-Next references (w1, n2)")
    a = ap.parse_args(argv)
    p = build_payload(a.results, {} if a.no_w1 else load_w1_summary(), None if a.no_w1 else load_w1_ab(),
                      None if a.no_w1 else load_n2_ab(), None if a.no_w1 else W1_JSONL)
    a.json_out.write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    a.out.write_text(render_html(p), encoding="utf-8")
    print(f"wrote {a.out}")
    a.card.parent.mkdir(parents=True, exist_ok=True)
    a.card.write_text(render_card(p), encoding="utf-8")
    a.post.parent.mkdir(parents=True, exist_ok=True)
    a.post.write_text(render_post(p), encoding="utf-8")
    a.reddit_out.write_text(render_reddit(p), encoding="utf-8")
    print(f"wrote {a.card}, {a.post}, {a.reddit_out}")
    if a.png:
        for page, size, scale in ((a.card, (1200, 630), 1), (a.post, (POST_W, POST_H), 2)):
            png = page.with_suffix(".png")
            if write_png(page, png, size, scale):
                print(f"wrote {png}")
            else:
                print(f"Chrome not found at {CHROME}; {png} was not rendered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
