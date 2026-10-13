#!/usr/bin/env python3
"""Render reports/qwen38-27b-stacks.html: the dense Qwen3.8-27B stacks measured in
bench/qwen38-27b-next-steps-2026-10 against the two Flash-Next daily drivers (A: w1, B: n2).
usage: render_27b_page.py [--results DIR] [--out HTML] [--json-out JSON] [--no-w1]
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "bench/qwen38-flashnext-daily-driver-2026-09/scripts"))
sys.path.insert(0, str(ROOT / "bench/swift15-flashnext-2026-10/scripts"))
from summarize_driver import summarize  # noqa: E402
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
    ("r27m", "mlx-serve 26.10.2 MTP head only (--no-drafter)", "mlx-serve 26.10.2", "ddalcu 8bit", "7775059e", 11234, "P3"),
    ("o27sw", "oMLX Swift 1.5 oQ4e", "oMLX 0.7.1.dev1", "scottlowry Swift-1.5 oQ4e-mtp", "881dc191", 8000, "P4"),
    ("l27", "llama.cpp b11569 draft-mtp", "llama.cpp b11569", "ggml-org Q8_0 + mtp", "71bc7b62", 8080, "P6"),
    ("l27n", "llama.cpp b11569 no spec", "llama.cpp b11569", "ggml-org Q8_0", "71bc7b62", 8080, "P6"),
]
ARM_IDS = [a[0] for a in ARMS]
FILE_RE = re.compile(r"^(?P<arm>[a-z0-9]+)-(?P<ctx>\d+)-t1\.0-p(?P<phase>\d)(?P<eff>[xm])\.jsonl$")
EFFORT = {"x": "xhigh", "m": "medium"}
EFFORTS = ("xhigh", "medium")
SUITES = summarize_ab.SUITES
SUITE_LABEL = {"humaneval": "HumanEval", "gpqa": "GPQA-Diamond", "livecodebench": "LiveCodeBench",
               "jdhodges": "Tool calling (jdhodges)", "veerman": "Tool calling (Veerman)", "if": "Instruction following"}
BANDS = (32768, 131072)
DRIVER_RATIO = 1.25
SKIP_HIT_ARMS = {"k27", "l27", "l27n"}  # runtimes that may not report cached_tokens (phases.sh)
W1_SUMMARY = ROOT / "bench/swift15-flashnext-2026-10/results/tturno-summary.json"
W1_AB = ROOT / "bench/swift15-flashnext-2026-10/results/ab/t1/w1"
N2_AB = ROOT / "bench/swift15-flashnext-2026-10/results/ab/t1/n2"
# Both drivers ran the Swift 1.5 battery at xhigh (ab-battery.sh, AB_EFFORT default).
W1_NAME = "Driver A: Flash-Next Swift 1.5 (w1, xhigh)"
N2_NAME = "Driver B: Flash-Next ddalcu iQ (n2, xhigh)"
SPEED_KEYS = ("t_turno_s", "warm_ttft_tool_s", "cold_ttft_s", "decode_tps", "hit_tool", "mtp_acceptance",
              "wired_peak_gb", "gates_failed")
CAMPAIGN_URL = "https://github.com/snagnever/macstudio-local-llm/tree/main/bench/qwen38-27b-next-steps-2026-10"


# ---------------------------------------------------------------- data

def load_w1_summary() -> dict:
    return json.loads(W1_SUMMARY.read_text(encoding="utf-8")) if W1_SUMMARY.exists() else {}


def load_w1_ab() -> dict | None:
    return summarize_ab.load_arm(W1_AB) if W1_AB.exists() else None


def load_n2_ab() -> dict | None:
    return summarize_ab.load_arm(N2_AB) if N2_AB.exists() else None


def _jsonl(f: Path) -> list[dict]:
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _speed_row(row: dict) -> dict:
    warm, hit = row.get("warm_ttft_s") or {}, row.get("hit") or {}
    return {"t_turno_s": row.get("t_turno_s"), "warm_ttft_tool_s": warm.get("tool_turn"),
            "cold_ttft_s": row.get("cold_ttft_s"), "decode_tps": row.get("decode_tps"),
            "hit_tool": hit.get("tool_turn"), "mtp_acceptance": row.get("mtp_acceptance"),
            "wired_peak_gb": row.get("wired_peak_gb"), "gates_failed": row.get("gates_failed")}


def _speed(results: Path) -> dict:
    """One file = one arm × ctx × effort; the effort comes from the file tag (p<N>x / p<N>m)."""
    out: dict[str, dict] = {}
    for f in sorted(results.glob("*-t1.0-p?[xm].jsonl")):
        m = FILE_RE.match(f.name)
        if not m:
            continue
        for (arm, ctx), row in summarize(_jsonl(f)).items():
            out.setdefault(str(ctx), {})[f"{arm}-{EFFORT[m['eff']]}"] = _speed_row(row)
    return out


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


def _driver(summary: dict, arm: str) -> dict:
    return {str(c): _speed_row(summary.get(f"{arm}@{c}", {})) for c in BANDS}


def _driver_quality(ab) -> dict:
    return {s: summarize_ab.suite_stats(ab[s]) for s in SUITES if s in ab} if ab else {}


def build_payload(results: Path, w1_summary: dict, w1_ab, n2_ab=None) -> dict:
    results = Path(results)
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "arms": [dict(zip(("id", "name", "runtime", "pack", "rev", "port", "phase"), a)) for a in ARMS],
            "speed": _speed(results),
            "w1": _driver(w1_summary, "w1"),
            "n2": _driver(w1_summary, "n2"),
            "quality": _quality(results),
            "w1_quality": _driver_quality(w1_ab),
            "n2_quality": _driver_quality(n2_ab),
            "empty": _empty(results),
            "loops": _loops(results),
            "gates": _gates(results)}


# ---------------------------------------------------------------- html helpers

NA = '<span class="na">—</span>'
NOT_MEASURED = '<p class="empty">not measured</p>'


def E(v) -> str:
    return _html.escape("" if v is None else str(v), quote=True)


def ND(v, fmt="{}", unit="") -> str:
    if v is None:
        return NA
    return E(fmt.format(v)) + (f'<span class="u">{E(unit)}</span>' if unit else "")


def _ctx_lab(ctx) -> str:
    return f"{int(ctx) // 1024}K"


def _order(labels) -> list[str]:
    """Arm-table order, xhigh before medium; unknown labels last, alphabetically."""
    def key(lab):
        arm, _, eff = lab.rpartition("-")
        if eff not in EFFORTS:
            arm, eff = lab, ""
        return (ARM_IDS.index(arm) if arm in ARM_IDS else len(ARM_IDS), arm,
                EFFORTS.index(eff) if eff in EFFORTS else 2, lab)
    return sorted(labels, key=key)


def _color(label: str) -> str:
    if label == N2_NAME:
        return "--ref-b"
    if label == W1_NAME or label.startswith("w1"):
        return "--s2"
    return "--s4" if label.endswith("-medium") else "--s1"


def _lab(label: str) -> str:
    return f'<span class="arm-lab"><span class="sw" style="background:var({_color(label)})"></span>{E(label)}</span>'


def _gates_text(label: str, failed) -> str:
    if failed is None:
        return ""
    arm = label.rpartition("-")[0]
    if arm in SKIP_HIT_ARMS:
        failed = [f"{g} (n/a)" if g.startswith("hit_") else g for g in failed]
    return ", ".join(failed) if failed else "pass"


def _hbars(rows: list, fmt: str, unit: str, refs: list | None = None) -> str:
    """Horizontal bars on one zero-based scale. rows: [(label, value, note)]; refs: [(value, cls, text)]."""
    refs = [r for r in (refs or []) if r[0] is not None]
    vals = [v for _, v, _ in rows if v is not None] + [r[0] for r in refs]
    mx = (max(vals) if vals else 1) * 1.04 or 1
    marks = "".join(f'<span class="refline {cls}" style="left:{100.0 * v / mx:.1f}%" title="{E(t)}"></span>'
                    for v, cls, t in refs)
    out = ""
    for label, v, note in rows:
        if v is None:
            out += (f'<div class="bline">{_lab(label)}<span class="btrack">{marks}</span>'
                    f'<span class="bv">{NA}</span></div>')
            continue
        txt = fmt.format(v) + unit
        tip = f"{label} · {txt}" + (f" · {note}" if note else "")
        out += (f'<div class="bline">{_lab(label)}<span class="btrack"><span class="bfill" '
                f'style="width:{100.0 * v / mx:.1f}%;background:var({_color(label)})" title="{E(tip)}"></span>{marks}'
                f'</span><span class="bv">{E(txt)}{f" <span class=u>{E(note)}</span>" if note else ""}</span></div>')
    return f'<div class="bars">{out}</div>'


def _chart(title: str, note: str, body: str) -> str:
    return (f'<figure class="card-chart"><p class="c-head">{E(title)}</p>'
            f'{f"<p class=c-note>{note}</p>" if note else ""}{body}</figure>')


def _ctxs(p: dict) -> list[str]:
    """The two driver bands first, then any other band measured (llama.cpp runs 64K)."""
    return [str(c) for c in BANDS] + sorted(set(p["speed"]) - {str(c) for c in BANDS}, key=int)


def _bar_note(label: str, failed) -> str:
    """Failed gates only, without the hit gates that do not apply to runtimes lacking cached-token counts."""
    arm = label.rpartition("-")[0]
    shown = [g for g in failed or [] if not (arm in SKIP_HIT_ARMS and g.startswith("hit_"))]
    return "fails " + ", ".join(shown) if shown else ""


# ---------------------------------------------------------------- sections

def _html_tturno(p: dict) -> str:
    cards = ""
    for ctx in _ctxs(p):
        rows = p["speed"].get(ctx, {})
        w1v = (p["w1"].get(ctx) or {}).get("t_turno_s")
        n2v = (p["n2"].get(ctx) or {}).get("t_turno_s")
        refs, keys = [], []
        if w1v is not None:  # the 1.25 x limit and the verdict use driver A only
            lim = round(DRIVER_RATIO * w1v, 1)
            refs += [(w1v, "w1", f"Driver A (w1): {w1v:.1f} s"), (lim, "lim", f"1.25 × w1: {lim:.1f} s")]
            keys += [f'<span class="refkey w1"></span>Driver A (Swift 1.5, w1) {w1v:.1f} s',
                     f'<span class="refkey lim"></span>1.25 × w1 = {lim:.1f} s']
        if n2v is not None:
            refs.append((n2v, "n2", f"Driver B (n2): {n2v:.1f} s"))
            keys.append(f'<span class="refkey n2"></span>Driver B (ddalcu iQ, n2) {n2v:.1f} s')
        if keys:
            note = " · ".join(keys)
        elif int(ctx) in BANDS:
            note = "Flash-Next driver references (w1, n2): not measured"
        else:
            note = "No Flash-Next reference at this band."
        if rows:
            body = _hbars([(lab, rows[lab]["t_turno_s"], _bar_note(lab, rows[lab]["gates_failed"]))
                           for lab in _order(rows)], "{:.1f}", " s", refs)
        else:
            body = NOT_MEASURED
        cards += _chart(f"{_ctx_lab(ctx)} context", note, body)
    return ('<section class="block" id="tturno"><h2 class="sec">Agent turn (T_turno) · 32K / 128K</h2>'
            '<p class="s-note">T_turno = time to first token of a warm turn that carries a tool result, plus 512 '
            'generated tokens at the warm decode rate. Median of 3 repetitions per arm and effort; shorter is better. '
            'The driver verdict reopens only for an arm at or under 1.25 × w1 (driver A) on both bands with every gate passing. '
            f'Bar notes list failed gates; hit gates are left out for runtimes that do not report cached tokens '
            f'(Splash, llama.cpp).</p>'
            f'<div class="cgrid">{cards}</div></section>')


def _html_ttft(p: dict) -> str:
    out = ""
    for ctx in _ctxs(p):
        rows = p["speed"].get(ctx, {})
        body = ""
        items = [(lab, rows[lab]) for lab in _order(rows)]
        for name, key in ((W1_NAME, "w1"), (N2_NAME, "n2")):
            d = p[key].get(ctx)
            if d and any(d.get(k) is not None for k in SPEED_KEYS):
                items.append((name, d))
        for lab, r in items:
            body += (f'<tr><td>{_lab(lab)}</td><td>{ND(r.get("t_turno_s"), "{:.1f}")}</td>'
                     f'<td>{ND(r.get("warm_ttft_tool_s"), "{:.2f}")}</td><td>{ND(r.get("cold_ttft_s"), "{:.1f}")}</td>'
                     f'<td>{ND(r.get("decode_tps"), "{:.1f}")}</td><td>{ND(r.get("hit_tool"), "{:.3f}")}</td>'
                     f'<td>{ND(r.get("mtp_acceptance"), "{:.3f}")}</td><td>{ND(r.get("wired_peak_gb"), "{:.1f}")}</td>'
                     f'<td class="nm">{E(_gates_text(lab, r.get("gates_failed"))) or NA}</td></tr>')
        if not body:
            body = '<tr><td colspan="9" class="nm"><span class="na">not measured</span></td></tr>'
        out += (f'<p class="c-head mt">{_ctx_lab(ctx)} context</p><div class="tbl-scroll"><table class="speedt">'
                '<thead><tr><th>Arm · effort</th><th>T_turno s</th><th>Warm TTFT (tool) s</th><th>Cold TTFT s</th>'
                '<th>Decode tok/s</th><th>Hit (tool)</th><th>MTP acc.</th><th>Wired peak GB</th>'
                f'<th class="nm">Gates</th></tr></thead><tbody>{body}</tbody></table></div>')
    return ('<section class="block" id="ttft"><h2 class="sec">Warm TTFT and decode</h2>'
            '<p class="s-note">Medians per arm and effort. Warm TTFT is the tool-result turn with the prefix cache '
            'warm; cold TTFT is the first request on an empty cache; hit is the cached share of the prompt on the '
            'tool turn. Tables scroll sideways on narrow screens.</p>'
            f'{out}</section>')


def _quality_rows(p: dict) -> list[tuple[str, dict]]:
    rows = [(lab, p["quality"][lab]) for lab in _order(p["quality"])]
    for name, key in ((W1_NAME, "w1_quality"), (N2_NAME, "n2_quality")):
        if p.get(key):
            rows.append((name, p[key]))
    return rows


def _suites(p: dict) -> list[str]:
    present = {s for _, st in _quality_rows(p) for s in st}
    return [s for s in SUITES if s in present]


def _per_suite(p: dict, key: str, fmt: str, unit: str) -> str:
    rows = _quality_rows(p)
    if not p["quality"]:
        return NOT_MEASURED + (_per_suite_cards(rows, _suites(p), key, fmt, unit) if rows else "")
    return _per_suite_cards(rows, _suites(p), key, fmt, unit)


def _per_suite_cards(rows, suites, key, fmt, unit) -> str:
    cards = ""
    for s in suites:
        bars = [(lab, (st.get(s) or {}).get(key), None) for lab, st in rows]
        cards += _chart(SUITE_LABEL.get(s, s), "", _hbars(bars, fmt, unit))
    return f'<div class="cgrid">{cards}</div>' if cards else ""


def _html_time(p: dict) -> str:
    return ('<section class="block" id="time"><h2 class="sec">Time per task</h2>'
            '<p class="s-note">Median seconds to the final answer per suite, one question at a time, vendor sampling '
            '(profile t1) at 131072 context. Labels are arm-effort; the Flash-Next driver rows (A and B) come from the '
            'Swift 1.5 campaign and ran at xhigh effort. Shorter is better.</p>'
            f'{_per_suite(p, "median_s", "{:.1f}", " s")}</section>')


def _html_tokens(p: dict) -> str:
    return ('<section class="block" id="tokens"><h2 class="sec">Tokens per answer (median)</h2>'
            '<p class="s-note">Median completion tokens per answer: thinking plus the visible answer.</p>'
            f'{_per_suite(p, "median_completion", "{:,.0f}", "")}</section>')


def _frac(d: dict | None, num: str, den: str) -> str:
    return NA if not d else f'{E(d[num])}<span class="u">/{E(d[den])}</span>'


def _html_accuracy(p: dict) -> str:
    rows = _quality_rows(p)
    suites = _suites(p)
    if not rows:
        table = NOT_MEASURED
    else:
        head = "".join(f"<th>{E(SUITE_LABEL.get(s, s))}</th>" for s in suites)
        body = ""
        for lab, st in rows:
            cells = ""
            for s in suites:
                x = st.get(s)
                if not x:
                    cells += f"<td>{NA}</td>"
                    continue
                tr = f' <span class="u">{x["truncated"]} trunc.</span>' if x.get("truncated") else ""
                cells += f'<td>{E(x["passed"])}/{E(x["n"])}{tr}</td>'
            emp = p["empty"].get(lab)
            loops = p["loops"].get(lab)
            cells += f"<td>{_frac(emp, 'empty', 'stop_records')}</td><td>{_frac(loops, 'degenerate', 'total')}</td>"
            body += f"<tr><td>{_lab(lab)}</td>{cells}</tr>"
        table = (f'<div class="tbl-scroll"><table class="qual"><thead><tr><th>Arm · effort</th>{head}'
                 f'<th>Empty answers</th><th>Loops</th></tr></thead><tbody>{body}</tbody></table></div>')
    think = [(k.split(":", 1)[1], v) for k, v in p["empty"].items() if k.startswith("think:")]
    think_html = ""
    if think:
        lis = "".join(f'<li><code>{E(k)}</code>: {v["empty"]} empty of {v["stop_records"]} finished turns</li>'
                      for k, v in think)
        think_html = f'<p class="s-note mt">Thinking-turn probe, empty final answers:</p><ul class="s-note">{lis}</ul>'
    return ('<section class="block" id="accuracy"><h2 class="sec">Accuracy</h2>'
            '<p class="s-note">Passed / questions per suite; a truncated answer never counts as passed. Empty answers '
            'are stop-finished records with no visible content; loops are degenerate outputs in the loop sweep.</p>'
            f'{table}{think_html}</section>')


GATE_DOC = {
    "P1_PASS": "Splash (k27): T_turno ≤ 0.75 × s27r at 128K and gates",
    "P2_PASS": "oMLX refit packs: T_turno ≤ s27r",
    "P3_PASS": "mlx-serve 26.10.2: T_turno ≤ s27r",
    "P4_PASS": "Swift 1.5 27B (o27sw): T_turno ≤ 1.03 × o27q4",
    "P6_PASS": "llama.cpp draft-mtp: T_turno ≤ s27r at 32K",
    "P5_GO": "Driver gate: fastest arm within 1.25 × w1 on both bands (0 = none)",
    "CAMPAIGN_DONE": "Campaign finished (UTC)",
}


def _html_gates(p: dict) -> str:
    g = p["gates"]
    if not g:
        body = NOT_MEASURED
    else:
        rows = ""
        for k, v in g.items():
            cls = "pass" if v in ("1", "pass") else "fail" if v in ("0", "fail") else ""
            doc = GATE_DOC.get(k) or (f"Best arm of {k.split('_')[0]}" if k.endswith("_BEST") else "")
            rows += (f'<tr><td><code>{E(k)}</code></td><td><span class="stchip {cls}">{E(v)}</span></td>'
                     f'<td class="nm">{E(doc)}</td></tr>')
        body = (f'<div class="tbl-scroll"><table class="cfg"><thead><tr><th>Gate</th><th>Value</th>'
                f'<th>Meaning</th></tr></thead><tbody>{rows}</tbody></table></div>')
    return ('<section class="block" id="gates"><h2 class="sec">Gates and verdicts</h2>'
            '<p class="s-note">Raw rows of <code>results/gates.env</code>, written by the unattended campaign runner '
            'and the driver gate.</p>' + body + '</section>')


def _ref_times(p: dict, key: str) -> str:
    """A driver's T_turno at 32K / 128K, read from the payload."""
    v = [(p[key].get(str(c)) or {}).get("t_turno_s") for c in BANDS]
    return " / ".join(f"{x:.1f}" for x in v) + " s" if all(x is not None for x in v) else "not measured"


def _html_sub(p: dict) -> str:
    return ('Nine ways to serve the dense 27B (mlx-dspark, Splash, oMLX refit packs, mlx-serve 26.10.2, the Swift 1.5 '
            '27B and llama.cpp) measured with the same agent-turn probe and battery as the two Qwen3.8-Flash-Next '
            f'daily drivers: A, Swift 1.5 (w1, T_turno {_ref_times(p, "w1")}) and B, ddalcu iQ (n2, T_turno '
            f'{_ref_times(p, "n2")}), both on mlx-serve 26.10.1 at 32K / 128K context.')


def _html_setup(p: dict) -> str:
    rows = "".join(f'<tr><td class="code">{E(a["id"])}</td><td>{E(a["name"])}</td><td>{E(a["runtime"])}</td>'
                   f'<td>{E(a["pack"])}</td><td><code>{E(a["rev"])}</code></td><td>{E(a["port"])}</td>'
                   f'<td>{E(a["phase"])}</td></tr>' for a in p["arms"])
    return ('<section class="block" id="setup"><h2 class="sec">Setup and how to reproduce</h2>'
            '<p class="s-note">Apple M4 Max, 128 GB. Every arm serves the dense Qwen3.8-27B; speed phases run each '
            'arm at xhigh and medium effort (file tags <code>p&lt;N&gt;x</code> / <code>p&lt;N&gt;m</code>), '
            '3 repetitions, bands 32K then 128K (llama.cpp: 32K and 64K). The two Flash-Next references come '
            'from <code>bench/swift15-flashnext-2026-10</code>, both on mlx-serve 26.10.1 at xhigh effort: driver A '
            f'(w1, Swift 1.5 MLX-4.7bpw) with T_turno {_ref_times(p, "w1")} and driver B (n2, ddalcu iQ-MLX-4.7bpw) '
            f'with T_turno {_ref_times(p, "n2")} at 32K / 128K. The 1.25 × limit and the driver verdict use driver A '
            'only.</p>'
            '<div class="tbl-scroll"><table class="cfg arms"><thead><tr><th>Arm</th><th>Stack</th><th>Runtime</th>'
            f'<th>Pack</th><th>Revision</th><th>Port</th><th>Phase</th></tr></thead><tbody>{rows}</tbody></table></div>'
            '<p class="s-note mt">Run the campaign on the rig with '
            '<code>bash bench/qwen38-27b-next-steps-2026-10/scripts/run-campaign.sh</code>, then render this page with '
            '<code>python3 bench/qwen38-27b-next-steps-2026-10/scripts/render_27b_page.py</code>. '
            f'Scripts and per-request results: <a href="{CAMPAIGN_URL}">github.com/snagnever/macstudio-local-llm</a>.</p>'
            '</section>')


PAGE_CSS = r"""
.mt{margin-top:14px}
.u{color:var(--muted); font-size:0.9em; margin-left:2px}
a{color:var(--accent)}
.arm-lab{display:inline-flex; align-items:center; gap:6px; white-space:nowrap; font-weight:600; color:var(--ink); min-width:0}
.arm-lab .sw{width:10px; height:10px; border-radius:2px; flex:none}
td.nm, th.nm{font-family:var(--sans); text-align:left; color:var(--ink-2); font-size:0.84rem}
td.code{font-family:var(--mono); font-weight:700; color:var(--ink)}
table.cfg td, table.cfg th{text-align:left; font-family:var(--sans); font-size:0.84rem}
table.cfg td:first-child, table.cfg td:nth-child(2){white-space:nowrap}
table.cfg code, .s-note code, .c-note code{font-family:var(--mono); font-size:0.9em}
table.speedt{min-width:860px} table.speedt td.nm{min-width:200px; white-space:normal} table.qual{min-width:760px} table.arms{min-width:760px}
.cgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); gap:14px; margin-top:14px}
figure.card-chart{margin:0; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 14px; min-width:0}
.c-head{margin:0; font-weight:700; font-size:0.92rem}
.c-note{margin:3px 0 0; font-size:0.8rem; color:var(--muted)}
.empty{color:var(--muted); font-size:0.88rem; margin:8px 0 0}
.bars{margin-top:8px}
.bline{display:grid; grid-template-columns:150px minmax(0,1fr) minmax(64px,auto); gap:8px; align-items:center; margin:4px 0}
.bline .arm-lab{font-size:0.78rem; font-weight:500; white-space:normal; line-height:1.2; overflow-wrap:anywhere}
.btrack{position:relative; display:block; height:14px; background:var(--surface-2); border-radius:0 4px 4px 0}
.bfill{display:block; height:100%; border-radius:0 4px 4px 0; min-width:2px}
.bv{font-family:var(--mono); font-size:0.76rem; text-align:right; color:var(--ink); white-space:nowrap}
.bv .u{display:block; font-size:0.66rem; white-space:normal; max-width:150px; margin-left:auto}
.refline{position:absolute; top:-3px; bottom:-3px; width:0; border-left:2px solid var(--s2)}
.refline.lim{border-left:2px dashed var(--warn)}
.refkey{display:inline-block; width:12px; height:0; vertical-align:middle; margin-right:4px; border-top:2px solid var(--s2)}
.refkey.lim{border-top:2px dashed var(--warn)}
:root{--ref-b:#7a4fd1}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ref-b:#a78bf0}}
:root[data-theme="dark"]{--ref-b:#a78bf0}
.refline.n2{border-left:2px dotted var(--ref-b)}
.refkey.n2{border-top:2px dotted var(--ref-b)}
.stchip:empty::before{content:"—"}
ul.s-note{padding-left:18px}
@media (max-width:520px){.wrap{padding:24px 16px 48px} .bline{grid-template-columns:104px minmax(0,1fr) minmax(56px,auto)}
  .bv .u{max-width:96px}}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Qwen3.8-27B stacks</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Dense Qwen3.8-27B stacks on an Apple M4 Max 128 GB against the Qwen3.8-Flash-Next driver: agent-turn time (T_turno) at 32K and 128K, time and tokens per task, accuracy, gates.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
/*__CSS__*/
</style>
<div class="wrap">
  <header>
    <div>
      <p class="eyebrow">Qwen3.8-27B dense · Apple M4 Max 128 GB · October 2026</p>
      <h1>Qwen3.8-27B stacks vs the Flash-Next driver</h1>
      <p class="sub">__SUB__</p>
    </div>
    <button class="theme" id="themeBtn" type="button">theme: auto</button>
  </header>
__TTURNO__
__TTFT__
__TIME__
__TOKENS__
__ACCURACY__
__GATES__
__SETUP__
  <footer id="foot">Generated <code>__GENERATED__</code> by <code>render_27b_page.py</code>.</footer>
</div>
<script>
const root=document.documentElement, btn=document.getElementById("themeBtn");
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
</script>
"""


def render_html(p: dict) -> str:
    parts = {
        "/*__CSS__*/": PERF_CSS + PERF_EXTRA_CSS + PAGE_CSS,
        "__TTURNO__": _html_tturno(p), "__TTFT__": _html_ttft(p), "__TIME__": _html_time(p),
        "__TOKENS__": _html_tokens(p), "__ACCURACY__": _html_accuracy(p), "__GATES__": _html_gates(p),
        "__SUB__": _html_sub(p), "__SETUP__": _html_setup(p), "__GENERATED__": E(p.get("generated_at", "")),
    }
    html = TEMPLATE
    for k, v in parts.items():
        html = html.replace(k, v)
    return html


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=C / "results")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/qwen38-27b-stacks.html")
    ap.add_argument("--json-out", type=Path, default=C / "results/page-data.json")
    ap.add_argument("--no-w1", action="store_true", help="leave out both Flash-Next drivers (A: w1, B: n2)")
    a = ap.parse_args(argv)
    p = build_payload(a.results, {} if a.no_w1 else load_w1_summary(), None if a.no_w1 else load_w1_ab(),
                      None if a.no_w1 else load_n2_ab())
    a.json_out.write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    a.out.write_text(render_html(p), encoding="utf-8")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
