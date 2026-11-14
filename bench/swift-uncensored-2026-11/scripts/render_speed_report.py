#!/usr/bin/env python3
"""Render the public page that compares the speed of three uncensored Flash-Next packs with the standard pack.

usage: render_speed_report.py [--out reports/qwen38-flashnext-uncensored-speed.html]

Reads the 24 cache_probe files results/<arm>-<context>-t1.0-s<N>.jsonl (2 boots per pack and context) and
groups them with summarize_driver.summarize, the same code that made etapa2-um-stream.md.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import io
import json
import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
REPO = CAMPAIGN.parents[1]
RESULTS = CAMPAIGN / "results"
OUT = REPO / "reports/qwen38-flashnext-uncensored-speed.html"
sys.path.insert(0, str(REPO / "bench/flashnext-next-steps-2026-10/scripts"))
sys.path.insert(0, str(REPO / "bench/harness-delivery-2026-11/scripts"))

import decide  # noqa: E402
import render_report as rr  # noqa: E402  (page CSS, table and figure helpers, pack names)
import svg_charts as sc  # noqa: E402

TITLE = "Do uncensored weights cost speed?"
SUBTITLE = "Three uncensored Qwen3.8 Flash-Next packs against the standard pack on a Mac Studio M4 Max"
GLOB = "*-t1.0-s[0-9]*.jsonl"
ARMS = ("k2h", "z4h", "z2h", "z3h")
CTXS = {32768: "32K", 131072: "128K", 262144: "256K"}
BOOTS = 2
LIMIT = 1.05
COLOUR = {"k2h": "--s1", "z4h": "--pack-b", "z2h": "--s3", "z3h": "--s4"}
SHORT = rr.ARM_SHORT
FULL = rr.ARM_PACK
SWIFT_URL = rr.SWIFT_URL
DELIVERY_PAGE = "qwen38-flashnext-harness-delivery.html"


def _summary(records: list[dict]) -> dict:
    with contextlib.redirect_stderr(io.StringIO()):   # the "mixes session_id" notice: two boots per group is the design
        return decide.summarize(records)


def _row(s: dict) -> dict:
    return {"t_turn_s": s["t_turno_s"], "decode_tps": s["decode_tps"], "cold_ttft_s": s["cold_ttft_s"],
            "warm_ttft_s": s["warm_ttft_s"]["tool_turn"], "hit": s["hit"]["tool_turn"],
            "prefill_tps": s["prefill_tps"], "wired_gb": round(s["wired_peak_gb"], 1), "errors": s["errors"]}


def collect(results: Path = RESULTS) -> dict:
    """Every number of the page. Raises ValueError unless each pack has 2 boots at each context."""
    results = Path(results)
    by_file = {f.stem: [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
               for f in sorted(results.glob(GLOB))}
    boots: dict[tuple, list[dict]] = {(a, c): [] for a in ARMS for c in CTXS}
    records = []
    for rows in by_file.values():
        key = (rows[0]["arm"], int(rows[0]["context_target"]))
        if key in boots:
            boots[key].append(_row(_summary(rows)[key]))
            records += rows
    short = [f"{a}@{CTXS[c]}: {len(b)}" for (a, c), b in boots.items() if len(b) != BOOTS]
    if short:
        raise ValueError(f"each pack needs {BOOTS} boots per context; found {', '.join(short)}")
    pooled = {k: _row(s) for k, s in _summary(records).items() if k in boots}
    for (arm, ctx), row in pooled.items():
        row["ratio"] = round(row["t_turn_s"] / pooled[("k2h", ctx)]["t_turn_s"], 3)
    spread = {a: max(round(100 * (max(x["decode_tps"] for x in boots[(a, c)]) / min(x["decode_tps"] for x in boots[(a, c)]) - 1), 1)
                     for c in CTXS) for a in ARMS}
    return {"pooled": pooled, "boots": boots, "decode_spread_pct": spread,
            "verdict": {a: "pass" if all(pooled[(a, c)]["ratio"] <= LIMIT for c in CTXS) else "fail"
                        for a in ARMS if a != "k2h"}}


def _headline(d: dict) -> dict:
    p = d["pooled"]
    unc = [a for a in ARMS if a != "k2h"]
    ratios = [p[(a, c)]["ratio"] for a in unc for c in CTXS]
    decode = [p[(a, c)]["decode_tps"] / p[("k2h", c)]["decode_tps"] for a in unc for c in CTXS]
    cold = [p[(a, c)]["cold_ttft_s"] / p[("k2h", c)]["cold_ttft_s"] for a in unc for c in CTXS]
    return {"turn": f"{round((min(ratios) - 1) * 100)}% to {round((max(ratios) - 1) * 100)}% slower per agent turn",
            "turn_range": f"{min(ratios):.2f}× to {max(ratios):.2f}×",
            "decode": f"{round((1 - max(decode)) * 100)}% to {round((1 - min(decode)) * 100)}%",
            "cold": f"{(max(cold) - 1) * 100:.1f}%",
            "noise": max(d["decode_spread_pct"].values())}


def _hero(d: dict) -> str:
    h, p = _headline(d), d["pooled"]
    tiles = [
        ("Agent turn", h["turn_range"], "the turn time of the standard pack, over 3 packs and 3 context sizes"),
        ("Token generation", f"{h['decode']} <small>lower</small>", "tokens per second while the model writes"),
        ("Reading a cold prompt", f"+{h['cold']} <small>at most</small>", "time to the first token with an empty cache"),
        ("Cache and warm start", "same", f"warm first token in {p[('k2h', 131072)]['warm_ttft_s']:.1f} s on every pack at 128K"),
    ]
    return (f'<header><p class="eyebrow">Local LLM · Mac Studio M4 Max 128 GB · November 2026</p><h1>{rr._e(TITLE)}</h1>'
            f'<p class="sub">{rr._e(SUBTITLE)}</p></header>'
            f'<p class="lead"><b>Not measurably: {h["turn"]}, inside the noise.</b> I measured three uncensored packs of '
            "Qwen3.8 Flash-Next against the standard pack, on the same server, at 32K, 128K and 256K of context. On "
            "average the uncensored packs write tokens a few percent slower. Everything else, from reading the prompt "
            "to reusing the cache, is the same. But two boots of one pack differ by up to "
            f"{h['noise']:.0f}%, which is more than the gap between the packs.</p>"
            '<div class="tiles">' + "".join(
                f'<div class="tile"><p class="t-lab">{rr._e(lab)}</p><p class="t-big">{big}</p>'
                f'<p class="t-sub">{rr._e(sub)}</p></div>' for lab, big, sub in tiles) + "</div>"
            '<nav class="toc" aria-label="Sections"><a href="#packs">The packs</a><a href="#turn">Agent turn</a>'
            '<a href="#decode">Generation</a><a href="#cold">Cold prompt</a><a href="#memory">Memory</a>'
            '<a href="#same">What stays the same</a><a href="#limits">Limits</a><a href="#method">Method</a></nav>')


def _packs(d: dict) -> str:
    rows = [["Standard", "ukisai Swift 1.5", "IQ4_XS (4-bit)", "no", "the reference"],
            ["Heretic v2", "jackjusko, indexer tensors recast by me from F16 to BF16", "IQ4_XS (4-bit)", "yes",
             "same quantization level as the standard pack; recipe and imatrix differ"],
            ["Huihui v2", "huihui-ai abliterated v2, GSQ-RCO", "IQ3_S (3-bit)", "yes", "one quantization step smaller"],
            ["SC117", "SC117 GSQ-RCO abliterated", "IQ3_S (3-bit)", "yes", "one quantization step smaller"]]
    body = ("<p>An uncensored (or “abliterated”) pack is the same model with the refusal behaviour edited out of the "
            "weights. A “pack” here is one set of GGUF weight files. All four run on the same server, Splash 1.6.1, with "
            "the same settings.</p>" + rr._table(["name on this page", "source", "quantization", "uncensored", "note"], rows, "text")
            + '<div class="callout"><p>Only Heretic v2 is a like-for-like comparison with the standard pack. The other '
            "two are also a smaller quantization, and I did not run the standard pack at IQ3_S, so for those two this "
            "page cannot separate the uncensoring from the quantization.</p></div>")
    return rr._section("packs", "What I compared", "One standard pack, three uncensored packs", body)


def _legend(arms) -> str:
    return rr._legend([(SHORT[a], COLOUR[a]) for a in arms])


def _turn(d: dict) -> str:
    h, p = _headline(d), d["pooled"]
    unc = [a for a in ARMS if a != "k2h"]
    rows_lbl = [f"{c} context" for c in CTXS.values()]
    points = {(f"{CTXS[c]} context", SHORT[a]): [p[(a, c)]["ratio"]] for a in unc for c in CTXS}
    svg = sc.dot_plot(rows_lbl, [(SHORT[a], COLOUR[a]) for a in unc], points, 0.98, 1.06, "×", LIMIT,
                      "Agent turn time of three uncensored packs, relative to the standard pack",
                      "All three uncensored packs take 1.00 to 1.05 times the turn time of the standard pack.",
                      ref_label="my limit, 1.05×")
    trows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['t_turn_s']} s", f"{p[(a, c)]['ratio']:.3f}×"] for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "1.00× is the standard pack. Each dot pools 2 server boots.",
                     ["pack", "context", "agent turn", "ratio"], trows, _legend(unc))
    k, z = p[("k2h", 131072)], p[("z4h", 131072)]
    verdict = ", ".join(f"{SHORT[a]} {v}s" for a, v in d["verdict"].items())
    body = (f"<p><b>{h['turn'][0].upper() + h['turn'][1:]}.</b> An agent turn here is a follow-up request with the "
            "prompt already in the cache: the time to the first token, plus 512 output tokens at the measured "
            f"generation speed. At 128K that is {k['t_turn_s']} s on the standard pack and {z['t_turn_s']} s on Heretic v2 "
            f"({z['ratio']:.3f}×).</p>" + fig
            + f"<p>My rule, set before the run, was “at most 5% slower at every context size”: {verdict}. Heretic v2 and "
            "Huihui v2 miss it by 0.001 at 128K. I do not read that as a real difference: the two boots of one pack "
            "differ by more than that. See the next section.</p>")
    return rr._section("turn", "Agent turn time", h["turn"][0].upper() + h["turn"][1:], body)


def _decode(d: dict) -> str:
    h, p, b = _headline(d), d["pooled"], d["boots"]
    rows_lbl = [f"{c} context" for c in CTXS.values()]
    points = {(f"{CTXS[c]} context", SHORT[a]): [x["decode_tps"] for x in b[(a, c)]] for a in ARMS for c in CTXS}
    svg = sc.dot_plot(rows_lbl, [(SHORT[a], COLOUR[a]) for a in ARMS], points, 100.0, 120.0, "", None,
                      "Generation speed in tokens per second, one dot per server boot",
                      "The dots of the four packs overlap at every context size; two boots of one pack differ as much as two packs do.")
    trows = [[SHORT[a], CTXS[c]] + [f"{x['decode_tps']}" for x in b[(a, c)]] + [f"{p[(a, c)]['decode_tps']}"]
             for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "Tokens per second; one dot per server boot, the tick is the middle of the two. The axis starts at 100.",
                     ["pack", "context", "boot 1", "boot 2", "pooled"], trows, _legend(ARMS))
    spread = ", ".join(f"{SHORT[a]} {v:.1f}%" for a, v in d["decode_spread_pct"].items())
    body = (f"<p><b>The uncensored packs generate {h['decode']} fewer tokens per second.</b> This is where the turn time "
            "goes: the model writes a little slower.</p>" + fig
            + f"<p>Each pack ran in two boots per context. The largest gap between the two boots of one pack: {spread}. "
            f"So the same pack can move by up to {h['noise']:.0f}% from one boot to the next, more than the gap between "
            "the packs. With two boots I cannot tell the packs apart. The data rules out a large slowdown, and no "
            "more than that.</p>")
    return rr._section("decode", "Token generation", "A few percent fewer tokens per second, inside the noise", body)


def _cold(d: dict) -> str:
    h, p = _headline(d), d["pooled"]
    groups = [f"{c} context" for c in CTXS.values()]
    series = [(SHORT[a], COLOUR[a]) for a in ARMS]
    values = {(f"{CTXS[c]} context", SHORT[a]): p[(a, c)]["cold_ttft_s"] for a in ARMS for c in CTXS}
    svg = sc.paired_bars(groups, series, values, max(values.values()),
                         "Seconds to the first token with an empty cache, per context size and pack",
                         "The four packs take the same time to read a prompt: 33 seconds at 32K, 161 at 128K, 338 at 256K.")
    trows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['cold_ttft_s']} s", f"{p[(a, c)]['prefill_tps']:.0f}",
              f"{p[(a, c)]['cold_ttft_s'] / p[('k2h', c)]['cold_ttft_s']:.3f}×"] for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "Seconds to the first token when the whole prompt is new. Shorter is better.",
                     ["pack", "context", "cold first token", "prompt tokens/s", "ratio"], trows, _legend(ARMS))
    body = (f"<p><b>No real difference: at most {h['cold']} slower.</b> Reading a full prompt for the first time is the "
            "slow part of a local model, and it does not depend on the pack. It depends on the context size.</p>" + fig)
    return rr._section("cold", "Reading a cold prompt", "The same wait on every pack", body)


def _memory(d: dict) -> str:
    p = d["pooled"]
    groups = [f"{c} context" for c in CTXS.values()]
    series = [(SHORT[a], COLOUR[a]) for a in ARMS]
    values = {(f"{CTXS[c]} context", SHORT[a]): p[(a, c)]["wired_gb"] for a in ARMS for c in CTXS}
    svg = sc.paired_bars(groups, series, values, 128.0, "Peak memory locked by the server, in GB of 128 GB",
                         "The two IQ3_S packs use about 13 GB less than the standard pack; Heretic v2 uses about 2 GB more.")
    trows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['wired_gb']} GB",
              f"{p[(a, c)]['wired_gb'] - p[('k2h', c)]['wired_gb']:+.1f} GB"] for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "Peak memory of the server; the bar is full at 128 GB.",
                     ["pack", "context", "peak memory", "against standard"], trows, _legend(ARMS))
    k, z4, z2 = (p[(a, 131072)]["wired_gb"] for a in ("k2h", "z4h", "z2h"))
    body = (f"<p><b>Memory follows the quantization, not the uncensoring.</b> At 128K Heretic v2 peaks {z4 - k:.0f} GB "
            f"above the standard pack. The two IQ3_S packs peak {k - z2:.0f} GB below it, because they are a smaller "
            "quantization.</p>" + fig)
    return rr._section("memory", "Memory", "Smaller quantization, less memory", body)


def _same(d: dict) -> str:
    p = d["pooled"]
    rows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['warm_ttft_s']:.1f} s", f"{100 * p[(a, c)]['hit']:.0f}%", p[(a, c)]["errors"]]
            for a in ARMS for c in CTXS]
    body = ("<p>Three things do not change with the pack: the time to the first token on a warm cache, the share of "
            "the prompt the cache reuses, and the error count.</p>"
            + rr._table(["pack", "context", "warm first token", "prompt reused from cache", "HTTP errors"], rows)
            + "<p class=\"note\">In real coding sessions I also measured no slowdown: on 7 small tasks the Heretic v2 pack "
            f'took 0.78× to 0.99× the session time of the standard pack. See <a href="{DELIVERY_PAGE}">Four coding '
            "harnesses, one local model</a>.</p>")
    return rr._section("same", "What stays the same", "Cache reuse and warm start", body)


def _limits(d: dict) -> str:
    items = [
        f"<b>Two boots per pack and context.</b> A difference under about {_headline(d)['noise']:.0f}% is inside the "
        "boot-to-boot spread.",
        "<b>Quantization is mixed in.</b> Two of the three uncensored packs are IQ3_S; the standard pack is IQ4_XS. "
        "I did not run the standard pack at IQ3_S.",
        "<b>Heretic v2 is not the file as published.</b> The server refused it; I recast 24 indexer tensors from F16 "
        "to BF16.",
        "<b>One machine, one server.</b> Mac Studio M4 Max 128 GB and Splash 1.6.1. Another runtime may behave differently.",
        "<b>One stream.</b> No concurrent requests.",
        "<b>Speed only.</b> This page does not measure answer quality.",
    ]
    return rr._section("limits", "Limits", "What this does not show", "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")


def _method(d: dict) -> str:
    setup = [
        ["Machine", "Mac Studio M4 Max, 128 GB"],
        ["Server", "Splash 1.6.1, temperature 1.0, reasoning effort xhigh, one stream"],
        ["Run", "2026-11-13 and 14: 24 server boots, 4 packs × 3 context sizes × 2 boots, 5 scenarios per boot; the "
                "standard pack runs first and last at each context size"],
        ["Labels in the data", " · ".join(f"{a}: {FULL[a]}" for a in ARMS)],
        ["Agent turn", "warm first-token time of a tool turn + 512 tokens ÷ warm generation speed (T_turno in the data)"],
        ["Cold first token", "time to the first token when no part of the prompt is in the cache"],
        ["Terms", "Splash: the local model server · GGUF: the weight file format · IQ4_XS, IQ3_S: 4-bit and 3-bit "
                  "quantization levels · imatrix: calibration data used when quantizing"],
    ]
    links = [("Campaign plan and scripts", SWIFT_URL),
             ("Stage report with every measure", f"{SWIFT_URL}/results/etapa2-um-stream.md"),
             ("The 24 result files", f"{SWIFT_URL}/results")]
    body = (rr._table(["item", "value"], setup, "text") + "<p>Everything is in the repository:</p><ul>"
            + "".join(f'<li><a href="{rr._e(u)}">{rr._e(t)}</a></li>' for t, u in links) + "</ul>")
    return rr._section("method", "Method and data", "How to check this", body)


def render(data: dict, generated: str | None = None) -> str:
    generated = generated or datetime.date.today().isoformat()
    h = _headline(data)
    desc = (f"Three uncensored Qwen3.8 Flash-Next packs against the standard pack on a Mac Studio M4 Max: {h['turn']}, "
            "the same cold start and cache reuse, measured at 32K, 128K and 256K.")
    e = rr._e
    head = "".join([
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n', f"<title>{e(TITLE)}</title>\n",
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        f'<meta name="description" content="{e(desc)}">\n',
        f'<meta property="og:title" content="{e(TITLE)}">\n<meta property="og:description" content="{e(desc)}">\n',
        f'<meta property="og:type" content="article">\n<meta property="og:url" content="{e(rr.SITE + OUT.name)}">\n',
        f"<style>{rr.CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n",
    ])
    sections = [_hero(data), _packs(data), _turn(data), _decode(data), _cold(data), _memory(data), _same(data),
                _limits(data), _method(data)]
    footer = (f'<footer>Generated <span id="generated">{e(generated)}</span> by <code>render_speed_report.py</code> from '
              f'the tracked results. <a href="{rr.SITE}">All reports</a></footer>')
    return head + "\n".join(sections) + "\n" + footer + "\n</div>\n</body>\n</html>\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    a.out.write_text(render(collect()))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
