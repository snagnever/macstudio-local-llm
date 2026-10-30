#!/usr/bin/env python3
"""SVG chart builders for the concurrency report page: pure functions that return one <svg> string.

Colors come only from the page's CSS tokens (var(--s1), var(--s2), var(--good), var(--warn-s), var(--crit),
var(--surface), currentColor), so the page theme styles every chart. A missing value draws a hatched
rectangle (fill="url(#hatch)", a <pattern> the page defines once) and the text "n/m". Every mark with a value
carries a <title> for the native tooltip. The band fills follow render_report.EXP_BANDS / EXP_BANDS_HIGH.
"""
from __future__ import annotations

import html
from typing import Any, Optional, Sequence

# Layout shared by the horizontal-bar forms: label column, plot width, row pitch.
W = 560
LEFT = 110.0
RIGHT_PAD = 70.0
PLOT_W = W - LEFT - RIGHT_PAD
ROW_H = 26.0
TOP = 26.0
BAR_H = 14.0
AXIS_X = LEFT + PLOT_W / 2  # zero axis of the diverging chart
# (good up to, acceptable up to) for lower-is-better metrics; (good from, acceptable from) for tps.
EXP_BANDS = {"ttft": (2.0, 5.0), "first_prompt": (30.0, 60.0), "side": (5.0, 60.0)}
EXP_BANDS_HIGH = {"tps": (60.0, 30.0)}
BAND_FILL = {"good": "var(--good)", "ok": "var(--warn-s)", "poor": "var(--crit)"}


def _fmt(v: float) -> str:
    return f"{v:.1f}"


def _scale(v: float, vmax: float, size: float) -> float:
    """Map v in [0, vmax] to [0, size]; values above vmax or below 0 are clamped."""
    return 0.0 if vmax <= 0 else max(0.0, min(v, vmax)) / vmax * size


def _svg(w: int, h: int, label: str, body: list[str]) -> str:
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{html.escape(label, quote=True)}" xmlns="http://www.w3.org/2000/svg">'
            + "".join(body) + "</svg>")


def _text(x: float, y: float, s: str, cls: str = "", anchor: str = "middle") -> str:
    c = f' class="{cls}"' if cls else ""
    return (f'<text{c} x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="13" '
            f'fill="currentColor">{html.escape(s)}</text>')


def _baseline(left: float, right: float, y: float) -> str:
    return f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="currentColor" opacity="0.4"/>'


def _title(s: str) -> str:
    return _text(0, 14, s, "ttl", "start")


def _tip(s: str) -> str:
    return f"<title>{html.escape(s)}</title>"


def _nm(x: float, y: float) -> list[str]:
    """The not-measured mark: a hatched bar and the text n/m."""
    return [f'<rect class="nm" x="{x:.1f}" y="{y:.1f}" width="60" height="{BAR_H}" rx="2" fill="url(#hatch)" '
            f'stroke="currentColor" opacity="0.6"/>', _text(x + 66, y + 11, "n/m", "na", "start")]


def _band_fills(metric: Optional[str], vmax: float, top: float, height: float) -> list[str]:
    """Background strips for the experience bands, in left-to-right order."""
    if metric is None:
        return []
    if metric in EXP_BANDS_HIGH:
        good, ok = EXP_BANDS_HIGH[metric]
        edges = [(0.0, ok, "poor"), (ok, good, "ok"), (good, vmax, "good")]
    else:
        good, ok = EXP_BANDS[metric]
        edges = [(0.0, good, "good"), (good, ok, "ok"), (ok, vmax, "poor")]
    out = []
    for lo, hi, kind in edges:
        x0, x1 = LEFT + _scale(lo, vmax, PLOT_W), LEFT + _scale(min(hi, vmax), vmax, PLOT_W)
        if x1 > x0:
            out.append(f'<rect class="band {kind}" x="{x0:.1f}" y="{top:.1f}" width="{x1 - x0:.1f}" '
                       f'height="{height:.1f}" fill="{BAND_FILL[kind]}" opacity="0.12"/>')
    return out


def _axis(y: float, vmax: float, unit: str, metric: Optional[str]) -> list[str]:
    ticks = {0.0, vmax}
    if metric in EXP_BANDS:
        ticks |= set(EXP_BANDS[metric])
    elif metric in EXP_BANDS_HIGH:
        ticks |= set(EXP_BANDS_HIGH[metric])
    out = [_baseline(LEFT, LEFT + PLOT_W, y)]
    for t in sorted(v for v in ticks if v <= vmax):
        x = LEFT + _scale(t, vmax, PLOT_W)
        label = f"{t:g}" + (f" {unit}" if t == vmax else "")
        out.append(_text(x, y + 14, label, "tick", "end" if t == vmax else "middle"))
    return out


def _fmt_unit(v: float, unit: str) -> str:
    return f"{_fmt(v)} {unit}".strip()


def svg_band_bars(title: str, rows: Sequence[dict[str, Any]], vmax: float, unit: str,
                  metric: Optional[str]) -> str:
    """Horizontal bars, one per row, over the band strips of `metric`. A row with lo/hi draws a range bar."""
    h = TOP + len(rows) * ROW_H + 24
    body = [_title(title)] + _band_fills(metric, vmax, TOP - 6, len(rows) * ROW_H)
    for i, r in enumerate(rows):
        y = TOP + i * ROW_H
        body.append(_text(LEFT - 8, y + 11, r["label"], "lbl", "end"))
        fill = f"var(--{r['series']})"
        if r.get("value") is not None:
            w = _scale(r["value"], vmax, PLOT_W)
            tip = f"{r['label']}: {_fmt_unit(r['value'], unit)}"
            body.append(f'<rect class="bar" x="{LEFT:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BAR_H}" rx="2" '
                        f'fill="{fill}">{_tip(tip)}</rect>')
            body.append(_text(LEFT + w + 6, y + 11, _fmt_unit(r["value"], unit) + (f" {r['note']}" if r.get("note") else ""),
                              "value", "start"))
        elif r.get("lo") is not None and r.get("hi") is not None:
            x0, x1 = LEFT + _scale(r["lo"], vmax, PLOT_W), LEFT + _scale(r["hi"], vmax, PLOT_W)
            label = f"{r['lo']:g}–{r['hi']:g} {unit}".strip()
            tip = _tip(f"{r['label']}: {label}")
            body.append(f'<rect class="bar" x="{x0:.1f}" y="{y:.1f}" width="{max(x1 - x0, 2):.1f}" height="{BAR_H}" '
                        f'rx="2" fill="{fill}">{tip}</rect>')
            body.append(_text(x1 + 6, y + 11, label, "value", "start"))
        else:
            body += _nm(LEFT, y)
    body += _axis(TOP + len(rows) * ROW_H - 4, vmax, unit, metric)
    return _svg(W, int(h), title, body)


def svg_dumbbell(title: str, rows: Sequence[dict[str, Any]], vmax: float, unit: str, metric: Optional[str],
                 series: str) -> str:
    """Alone → pair per row: a light circle (alone) and a full circle (pair) joined by a line."""
    h = TOP + len(rows) * ROW_H + 24
    body = [_title(title)] + _band_fills(metric, vmax, TOP - 6, len(rows) * ROW_H)
    for i, r in enumerate(rows):
        y = TOP + i * ROW_H + BAR_H / 2
        body.append(_text(LEFT - 8, y + 4, r["label"], "lbl", "end"))
        alone, pair = r.get("alone"), r.get("pair")
        xa = LEFT + _scale(alone, vmax, PLOT_W) if alone is not None else None
        xp = LEFT + _scale(pair, vmax, PLOT_W) if pair is not None else None
        if xa is not None and xp is not None:
            body.append(f'<line class="dumbbell" x1="{min(xa, xp):.1f}" y1="{y:.1f}" x2="{max(xa, xp):.1f}" '
                        f'y2="{y:.1f}" stroke="var(--{series})" stroke-width="2"/>')
        for x, v, kind, fill in ((xa, alone, "alone", f"var(--{series}l)"), (xp, pair, "pair", f"var(--{series})")):
            if x is None:
                continue
            tip = _tip(f"{r['label']}, {kind}: {_fmt_unit(v, unit)}")
            body.append(f'<circle class="{kind}" cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{fill}" '
                        f'stroke="var(--surface)" stroke-width="2">{tip}</circle>')
            anchor = "end" if (kind == "alone") == (xa is not None and xp is not None and xa <= xp) else "start"
            body.append(_text(x + (-8 if anchor == "end" else 8), y - 8, _fmt(v), "value", anchor))
        if xa is None or xp is None:
            body += _nm((xa if xa is not None else xp if xp is not None else LEFT) + 10, y - BAR_H / 2)
    body += _axis(TOP + len(rows) * ROW_H - 4, vmax, unit, metric)
    return _svg(W, int(h), title, body)


def svg_diverging(title: str, rows: Sequence[dict[str, Any]], vmax_pct: float) -> str:
    """Signed percentages around a central zero axis; positive to the right."""
    h = TOP + len(rows) * ROW_H + 30
    half = PLOT_W / 2
    body = [_title(title), f'<line x1="{AXIS_X:.1f}" y1="{TOP - 6:.1f}" x2="{AXIS_X:.1f}" '
                           f'y2="{TOP + len(rows) * ROW_H - 4:.1f}" stroke="currentColor" opacity="0.4"/>']
    for i, r in enumerate(rows):
        y = TOP + i * ROW_H
        body.append(_text(LEFT - 8, y + 11, r["label"], "lbl", "end"))
        pct = r.get("pct")
        if pct is None:
            body += _nm(AXIS_X - 30, y)
            continue
        w = _scale(abs(pct), vmax_pct, half)
        x = AXIS_X if pct >= 0 else AXIS_X - w
        sign = "+" if pct >= 0 else "−"
        label = f"{sign}{abs(pct) * 100:.0f}%"
        tip = _tip(f"{r['label']}: {label}")
        series = r["series"]
        body.append(f'<rect class="bar" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BAR_H}" rx="2" '
                    f'fill="var(--{series})">{tip}</rect>')
        if pct >= 0:
            body.append(_text(AXIS_X + w + 6, y + 11, label, "value", "start"))
        else:
            body.append(_text(AXIS_X - w - 6, y + 11, label, "value", "end"))
    body.append(_text(AXIS_X, TOP + len(rows) * ROW_H + 14, "0 = same time as one task after the other", "tick"))
    return _svg(W, int(h), title, body)


def svg_lines(title: str, series: Sequence[dict[str, Any]], xs: Sequence[int], ymax: float, unit: str) -> str:
    """One line per series over the integer xs (sessions). A legacy point is hollow; a missing point breaks the line."""
    left, plot_w, plot_h, top = 50.0, 390.0, 160.0, 26.0
    base = top + plot_h
    body = [_title(title), _baseline(left, left + plot_w, base)]
    for frac in (0.25, 0.5, 0.75, 1.0):
        y = base - frac * plot_h
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="currentColor" opacity="0.12"/>')
        body.append(_text(left - 6, y + 4, f"{frac * ymax:g}", "tick", "end"))
    step = plot_w / max(len(xs) - 1, 1)
    xpos = {x: left + i * step for i, x in enumerate(xs)}
    for s in series:
        color = f"var(--{s['key']})"
        run: list[str] = []
        runs: list[list[str]] = []
        for x in xs:
            p = s["points"].get(x) or {}
            if p.get("y") is None:
                if len(run) > 1:
                    runs.append(run)
                run = []
                continue
            run.append(f"{xpos[x]:.1f},{base - _scale(p['y'], ymax, plot_h):.1f}")
        if len(run) > 1:
            runs.append(run)
        for pts in runs:
            body.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>')
        last_x = None
        for x in xs:
            p = s["points"].get(x) or {}
            if p.get("y") is None:
                continue
            cy = base - _scale(p["y"], ymax, plot_h)
            fill = "var(--surface)" if p.get("legacy") else color
            tip = _tip(f"{s['label']}, {x}: {_fmt_unit(p['y'], unit)}")
            body.append(f'<circle cx="{xpos[x]:.1f}" cy="{cy:.1f}" r="4.5" fill="{fill}" stroke="{color}" '
                        f'stroke-width="2">{tip}</circle>')
            last_x = x
        if last_x is not None:
            p = s["points"][last_x]
            body.append(_text(xpos[last_x] + 8, base - _scale(p["y"], ymax, plot_h) + 4,
                              f"{s['label']} {_fmt(p['y'])}", "value", "start"))
    for x in xs:
        body.append(_text(xpos[x], base + 16, str(x), "tick"))
    body.append(_text(left + plot_w / 2, base + 32, "sessions (a subagent counts as one more)", "tick"))
    return _svg(W, int(base + 40), title, body)


def svg_timeline(server_labels: tuple[str, str]) -> str:
    """Schematic: session B sends a big prompt while A is mid-turn; the side call on each server."""
    a, b = server_labels
    body = [_title("Session B sends a big prompt while A is mid-turn (schematic)")]

    def box(x: float, y: float, w: float, label: str, fill: str, text_fill: str = "currentColor") -> list[str]:
        return [f'<rect x="{x}" y="{y}" width="{w}" height="{BAR_H}" rx="2" fill="{fill}"/>',
                f'<text x="{x + w / 2:.1f}" y="{y + 11}" text-anchor="middle" font-size="11" fill="{text_fill}">'
                f'{html.escape(label)}</text>']

    body.append(_text(LEFT - 8, 41, "Session A", "lbl", "end"))
    body += box(LEFT, 30, 60, "reply", "var(--s1)", "var(--surface)")
    body += box(LEFT + 60, 30, 130, "waits for B's read", "var(--grid)")
    body += box(LEFT + 190, 30, 60, "reply", "var(--s1)", "var(--surface)")
    body.append(_text(LEFT - 8, 69, "Session B", "lbl", "end"))
    body += box(LEFT + 60, 58, 130, "reads the prompt (prefill)", "var(--s1l)")
    body += box(LEFT + 190, 58, 60, "reply", "var(--s1)", "var(--surface)")
    body.append(_text(LEFT - 8, 97, "Side call", "lbl", "end"))
    body.append(f'<polygon points="{LEFT + 110},86 {LEFT + 106},80 {LEFT + 114},80" fill="currentColor"/>')
    body += box(LEFT + 110, 86, 12, "", "var(--s1)")
    body.append(_text(LEFT + 128, 97, f"{a}: answered in seconds", "tick", "start"))
    body.append(f'<rect x="{LEFT + 110}" y="106" width="80" height="{BAR_H}" rx="2" fill="url(#hatch)" stroke="var(--s2)"/>')
    body += box(LEFT + 190, 106, 12, "", "var(--s2)")
    body.append(_text(LEFT + 208, 117, f"{b}: waits for the whole read (minutes)", "tick", "start"))
    body.append(_baseline(LEFT, W - 10, 132))
    body.append(_text(LEFT, 146, "time →", "tick", "start"))
    return _svg(W, 152, "Timeline of two sessions when one reads a big prompt", body)


def table_view(head: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """The chart's data as a collapsed table (the accessible, copyable view)."""
    th = "".join(f"<th>{html.escape(str(h))}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<details class="tbl"><summary>Table view</summary><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></details>'
