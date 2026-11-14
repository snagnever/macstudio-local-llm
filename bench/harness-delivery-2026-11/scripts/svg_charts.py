"""Static SVG charts for the public report. Each function returns one <svg> string.

Every colour is a CSS variable of the page (var(--name)), so the charts follow the light and dark themes.
"""
from __future__ import annotations

import html
import statistics

W = 720
LABEL_MAX = 28
ROW = 34


def _e(text) -> str:
    return html.escape(str(text), quote=True)


def _cut(label: str, limit: int = LABEL_MAX) -> str:
    label = str(label)
    return label if len(label) <= limit else label[:limit - 1].rstrip() + "…"


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _svg(height: float, title: str, desc: str, body: list[str], extra: str = "") -> str:
    return (f'<svg viewBox="0 0 {W} {_num(height)}" role="img" xmlns="http://www.w3.org/2000/svg"{extra}>'
            f"<title>{_e(title)}</title><desc>{_e(desc)}</desc>" + "".join(body) + "</svg>")


def _text(x: float, y: float, text, cls: str = "lbl", anchor: str = "start", fill: str = "var(--ink-2)") -> str:
    return (f'<text x="{_num(x)}" y="{_num(y)}" class="{cls}" text-anchor="{anchor}" fill="{fill}" '
            f'font-size="13">{_e(text)}</text>')


def heatmap(rows: list[str], cols: list[str], values: dict, vmax: int, title: str, desc: str,
            col_groups: list[tuple[str, int]] | None = None) -> str:
    """One cell per (row, col) with the value written in it. Five colour levels, --heat-0 to --heat-4.
    col_groups: optional (label, number of columns) headers above the column labels."""
    left, top = 150, 54 if col_groups else 30
    cw, ch = (W - left - 10) / len(cols), 40
    body = []
    if col_groups:
        x = left
        for label, n in col_groups:
            body.append(_text(x + n * cw / 2, 16, label, "ttl", "middle", "var(--ink)"))
            body.append(f'<line x1="{_num(x + 4)}" y1="24" x2="{_num(x + n * cw - 4)}" y2="24" stroke="var(--baseline)"/>')
            x += n * cw
    for j, c in enumerate(cols):
        body.append(_text(left + j * cw + cw / 2, top - 10, _cut(c, 10), "tick", "middle"))
    for i, r in enumerate(rows):
        y = top + i * ch
        body.append(_text(left - 12, y + ch / 2 + 5, _cut(r, 18), "lbl", "end", "var(--ink)"))
        for j, c in enumerate(cols):
            v = values[(r, c)]
            level = round(4 * v / vmax) if vmax else 0
            body.append(f'<rect x="{_num(left + j * cw + 2)}" y="{_num(y + 2)}" width="{_num(cw - 4)}" '
                        f'height="{ch - 4}" rx="5" fill="var(--heat-{level})"/>')
            ink = "var(--heat-ink-hi)" if level >= 3 else "var(--ink)"
            body.append(_text(left + j * cw + cw / 2, y + ch / 2 + 5, v, "value", "middle", ink))
    return _svg(top + len(rows) * ch + 6, title, desc, body)


def paired_bars(groups: list[str], series: list[tuple[str, str]], values: dict, vmax: float, title: str,
                desc: str) -> str:
    """Horizontal bars, one group per row and one bar per series. series: (label, colour variable)."""
    left, right, bh = 210, 46, 13
    plot = W - left - right
    gh = len(series) * (bh + 3) + 14
    body = []
    for i, g in enumerate(groups):
        y0 = 8 + i * gh
        body.append(_text(left - 12, y0 + gh / 2 - 2, _cut(g), "lbl", "end", "var(--ink)"))
        for k, (label, colour) in enumerate(series):
            v = values[(g, label)]
            y = y0 + k * (bh + 3)
            body.append(f'<rect x="{left}" y="{_num(y)}" width="{_num(plot)}" height="{bh}" rx="3" fill="var(--track)"/>')
            body.append(f'<rect x="{left}" y="{_num(y)}" width="{_num(plot * v / vmax if vmax else 0)}" height="{bh}" '
                        f'rx="3" fill="var({colour})"/>')
            body.append(_text(left + plot + 8, y + bh - 2, _num(v), "value", "start", "var(--ink)"))
    return _svg(8 + len(groups) * gh, title, desc, body)


def stacked_bars(rows: list[str], parts: list[tuple[str, str]], values: dict, title: str, desc: str) -> str:
    """Horizontal 100% bars. parts: (label, colour variable). A part wide enough shows its count."""
    left, bh = 250, 22
    plot = W - left - 10
    body = []
    for i, r in enumerate(rows):
        y = 6 + i * ROW
        total = sum(values[(r, p)] for p, _ in parts) or 1
        body.append(_text(left - 12, y + bh - 6, _cut(r, 34), "lbl", "end", "var(--ink)"))
        x = float(left)
        for p, colour in parts:
            w = plot * values[(r, p)] / total
            body.append(f'<rect class="part" x="{_num(x)}" y="{y}" width="{_num(w)}" height="{bh}" fill="var({colour})"/>')
            if w >= 26:
                body.append(_text(x + w / 2, y + bh - 6, values[(r, p)], "value", "middle", "var(--on-fill)"))
            x += w
    return _svg(6 + len(rows) * ROW, title, desc, body, f' data-plot-width="{_num(plot)}"')


def dot_plot(rows: list[str], series: list[tuple[str, str]], points: dict, xmin: float, xmax: float, unit: str,
             ref: float | None, title: str, desc: str, ref_label: str = "") -> str:
    """One dot per measurement, a tick at the median of each (row, series), a vertical line at ref."""
    left, right, top = 150, 60, 26
    plot = W - left - right
    sx = lambda v: left + plot * (min(max(v, xmin), xmax) - xmin) / (xmax - xmin)  # noqa: E731
    rh = max(ROW, 14 * len(series) + 12)
    height = top + len(rows) * rh + 26
    body = []
    for k in range(5):
        v = xmin + (xmax - xmin) * k / 4
        body.append(f'<line x1="{_num(sx(v))}" y1="{top}" x2="{_num(sx(v))}" y2="{_num(height - 24)}" stroke="var(--grid)"/>')
        body.append(_text(sx(v), height - 8, f"{_num(v)}{unit}", "tick", "middle"))
    if ref is not None:
        body.append(f'<line class="ref" x1="{_num(sx(ref))}" y1="{top - 8}" x2="{_num(sx(ref))}" y2="{_num(height - 24)}" '
                    'stroke="var(--crit)" stroke-dasharray="5 4" stroke-width="1.5"/>')
        if ref_label:
            body.append(_text(sx(ref), top - 12, ref_label, "tick", "middle", "var(--crit)"))
    for i, r in enumerate(rows):
        y0 = top + i * rh
        body.append(_text(left - 12, y0 + rh / 2 + 5, _cut(r, 18), "lbl", "end", "var(--ink)"))
        for k, (label, colour) in enumerate(series):
            vals = points.get((r, label), [])
            y = y0 + rh / 2 + (k - (len(series) - 1) / 2) * 14
            for v in vals:
                body.append(f'<circle cx="{_num(sx(v))}" cy="{_num(y)}" r="4.5" fill="var({colour})" fill-opacity="0.8"/>')
            if len(vals) > 1:
                m = sx(statistics.median(vals))
                body.append(f'<line x1="{_num(m)}" y1="{_num(y - 7)}" x2="{_num(m)}" y2="{_num(y + 7)}" '
                            f'stroke="var({colour})" stroke-width="2.5"/>')
    return _svg(height, title, desc, body)


def matrix_diagram(factors: list[tuple[str, list[str]]], title: str, desc: str) -> str:
    """The factors of the test matrix as columns of chips, and their product."""
    cw = (W - 110) / len(factors)
    rows = max(len(items) for _, items in factors)
    body, product = [], 1
    for i, (name, items) in enumerate(factors):
        product *= len(items)
        x = i * cw
        body.append(_text(x + (cw - 14) / 2, 16, f"{len(items)} {name}", "ttl", "middle", "var(--ink)"))
        for j, item in enumerate(items):
            y = 28 + j * 30
            body.append(f'<rect x="{_num(x)}" y="{y}" width="{_num(cw - 14)}" height="24" rx="6" fill="var(--surface-2)" '
                        'stroke="var(--baseline)"/>')
            body.append(_text(x + (cw - 14) / 2, y + 17, _cut(item, 20), "lbl", "middle", "var(--ink)"))
        if i < len(factors) - 1:
            body.append(_text(x + cw - 7, 16, "×", "ttl", "middle", "var(--muted)"))
    x = len(factors) * cw
    body.append(_text(x + 4, 16, "=", "ttl", "start", "var(--muted)"))
    body.append(f'<text x="{_num(x + 55)}" y="62" text-anchor="middle" fill="var(--ink)" font-size="34" '
                f'font-weight="700">{product}</text>')
    body.append(_text(x + 55, 82, "sessions", "tick", "middle"))
    return _svg(28 + rows * 30 + 6, title, desc, body)
