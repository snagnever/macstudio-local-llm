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
import statistics
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


WARM = ("identical", "append", "tool_turn")


def _raw(rows: list[dict]) -> dict:
    """The medians of summarize_driver without its rounding to 0.1: turn time, generation speed, warm first token."""
    decode = statistics.median(r["decode_tps"] for r in rows if r["scenario"] in WARM)
    warm = statistics.median(r["ttft_ms"] / 1000 for r in rows if r["scenario"] == "tool_turn")
    return {"t_turn_raw": warm + 512 / decode, "decode_raw": decode, "warm_raw": warm}


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
            boots[key].append({**_row(_summary(rows)[key]), **_raw(rows)})
            records += rows
    short = [f"{a}@{CTXS[c]}: {len(b)}" for (a, c), b in boots.items() if len(b) != BOOTS]
    if short:
        raise ValueError(f"each pack needs {BOOTS} boots per context; found {', '.join(short)}")
    pooled = {k: {**_row(s), **_raw([r for r in records if (r["arm"], int(r["context_target"])) == k])}
              for k, s in _summary(records).items() if k in boots}
    for (arm, ctx), row in pooled.items():
        if round(row["t_turn_raw"], 1) != row["t_turn_s"]:
            raise ValueError(f"unrounded turn time of {arm}@{CTXS[ctx]} does not match summarize_driver")
        row["ratio"] = round(row["t_turn_s"] / pooled[("k2h", ctx)]["t_turn_s"], 3)       # the rule as coded
        row["ratio_raw"] = round(row["t_turn_raw"] / pooled[("k2h", ctx)]["t_turn_raw"], 3)
    gap = {k: 100 * (max(x["decode_raw"] for x in b) / min(x["decode_raw"] for x in b) - 1) for k, b in boots.items()}
    spread = {a: round(max(gap[(a, c)] for c in CTXS), 1) for a in ARMS}
    mean6 = {a: statistics.mean(x["decode_raw"] for c in CTXS for x in boots[(a, c)]) for a in ARMS}
    return {"pooled": pooled, "boots": boots, "decode_spread_pct": spread,
            "pairs_under_4": sum(g < 4 for g in gap.values()), "pairs": len(gap),
            "decode_mean_pct": {a: round(100 * (mean6[a] / mean6["k2h"] - 1), 1) for a in ARMS if a != "k2h"},
            "below_standard": {a: sum(pooled[(a, c)]["decode_raw"] < pooled[("k2h", c)]["decode_raw"] for c in CTXS)
                               for a in ARMS if a != "k2h"},
            "requests": len(records), "correct": sum(bool(r.get("correct")) for r in records),
            "truncated": [(r["arm"], int(r["context_target"])) for r in records
                          if not r.get("correct") and r.get("finish_reason") == "length"],
            "verdict": {a: "pass" if all(pooled[(a, c)]["ratio"] <= LIMIT for c in CTXS) else "fail"
                        for a in ARMS if a != "k2h"}}


def _headline(d: dict) -> dict:
    p = d["pooled"]
    unc = [a for a in ARMS if a != "k2h"]
    ratios = [p[(a, c)]["ratio_raw"] for a in unc for c in CTXS]
    decode = [p[(a, c)]["decode_raw"] / p[("k2h", c)]["decode_raw"] for a in unc for c in CTXS]
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
        ("Cache and warm start", "same", "warm first token in "
         f"{min(p[(a, 131072)]['warm_raw'] for a in ARMS):.2f} to {max(p[(a, 131072)]['warm_raw'] for a in ARMS):.2f} s at 128K"),
    ]
    return (f'<header><p class="eyebrow">Local LLM · Mac Studio M4 Max 128 GB · November 2026</p><h1>{rr._e(TITLE)}</h1>'
            f'<p class="sub">{rr._e(SUBTITLE)}</p></header>'
            f'<p class="lead"><b>At most a few percent: {h["turn"]}, close to the noise of this test.</b> I measured '
            "three uncensored packs of Qwen3.8 Flash-Next against the standard pack, on the same server, at 32K, 128K "
            "and 256K of context. On average the uncensored packs write tokens a few percent slower. Reading the "
            "prompt and reusing the cache are the same within about 1%. Two starts of the server with one pack differ "
            f"by up to {h['noise']:.0f}%, so at a single context size the packs cannot be told apart.</p>"
            '<div class="tiles">' + "".join(
                f'<div class="tile"><p class="t-lab">{rr._e(lab)}</p><p class="t-big">{big}</p>'
                f'<p class="t-sub">{rr._e(sub)}</p></div>' for lab, big, sub in tiles) + "</div>"
            '<nav class="toc" aria-label="Sections"><a href="#packs">The packs</a><a href="#turn">Agent turn</a>'
            '<a href="#decode">Generation</a><a href="#cold">Cold prompt</a><a href="#memory">Memory</a>'
            '<a href="#same">What stays the same</a><a href="#limits">Limits</a><a href="#method">Method</a></nav>')


def _packs(d: dict) -> str:
    rows = [["Standard", "ukisai Swift 1.5", "IQ4_XS (about 4 bits per weight)", "no", "the reference"],
            ["Heretic v2", "jackjusko, the IQ4_XS-plus file, with 24 indexer tensors recast by me from F16 to BF16 "
             "(same values) because the server refused the original file", "IQ4_XS (about 4 bits per weight)", "yes",
             "same quantization level as the standard pack; recipe and imatrix differ"],
            ["Huihui v2", "huihui-ai abliterated v2", "GSQ-RCO IQ3_S (about 3 bits per weight)", "yes",
             "a smaller quantization, from another quantizer"],
            ["SC117", "SC117 abliterated", "GSQ-RCO IQ3_S (about 3 bits per weight)", "yes",
             "a smaller quantization, from another quantizer"]]
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
    points = {(f"{CTXS[c]} context", SHORT[a]): [p[(a, c)]["ratio_raw"]] for a in unc for c in CTXS}
    svg = sc.dot_plot(rows_lbl, [(SHORT[a], COLOUR[a]) for a in unc], points, 0.98, 1.06, "×", LIMIT,
                      "Agent turn time of three uncensored packs, relative to the standard pack",
                      f"All three uncensored packs take {h['turn_range'].replace('×', '')} times the turn time of the standard pack.",
                      ref_label="my limit, 1.05×")
    trows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['t_turn_raw']:.2f} s", f"{p[(a, c)]['ratio_raw']:.3f}×",
              f"{p[(a, c)]['ratio']:.3f}×"] for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "1.00× is the standard pack. Each dot is computed from the requests of 2 server boots.",
                     ["pack", "context", "agent turn", "ratio", "ratio from times rounded to 0.1 s (the rule)"],
                     trows, _legend(unc))
    k, z = p[("k2h", 131072)], p[("z4h", 131072)]
    verdict = ", ".join(f"{SHORT[a]} {v}es" if v == "pass" else f"{SHORT[a]} {v}s" for a, v in d["verdict"].items())
    z2 = p[("z2h", 131072)]
    body = (f"<p><b>{h['turn'][0].upper() + h['turn'][1:]}.</b> An agent turn here is a computed figure: the measured "
            "time to the first token of a follow-up tool request (96% to 100% of the prompt already in the cache), "
            "plus the time to write 512 tokens at the measured generation speed. At 128K that is "
            f"{k['t_turn_s']} s on the standard pack and {z['t_turn_s']} s on Heretic v2.</p>" + fig
            + f"<p>My rule, set before the run, was “at most 5% slower at every context size”: {verdict}. The rule "
            f"divides turn times rounded to 0.1 s: Heretic v2 and Huihui v2 land at {z['ratio']:.3f}× at 128K and fail "
            f"by 0.001. From the unrounded times Heretic v2 is {z['ratio_raw']:.3f}× and Huihui v2 {z2['ratio_raw']:.3f}×. "
            "The verdict depends on rounding, so I do not read it as a difference.</p>")
    return rr._section("turn", "Agent turn time", h["turn"][0].upper() + h["turn"][1:], body)


def _decode(d: dict) -> str:
    h, p, b = _headline(d), d["pooled"], d["boots"]
    rows_lbl = [f"{c} context" for c in CTXS.values()]
    points = {(f"{CTXS[c]} context", SHORT[a]): [x["decode_raw"] for x in b[(a, c)]] for a in ARMS for c in CTXS}
    svg = sc.dot_plot(rows_lbl, [(SHORT[a], COLOUR[a]) for a in ARMS], points, 100.0, 120.0, "", None,
                      "Generation speed in tokens per second, one dot per server boot",
                      "The dots of the four packs overlap at every context size; two starts of one pack can differ as much as two packs do.")
    trows = [[SHORT[a], CTXS[c]] + [f"{x['decode_tps']}" for x in b[(a, c)]] + [f"{p[(a, c)]['decode_tps']}"]
             for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "Tokens per second; one dot per server start (the median of its 3 warm requests), the tick is "
                     "the middle of the two. The headline numbers use the median of all 6 requests, in the table. "
                     "The axis starts at 100.",
                     ["pack", "context", "start 1", "start 2", "all 6 requests"], trows, _legend(ARMS))
    spread = ", ".join(f"{SHORT[a]} {v:.1f}%" for a, v in d["decode_spread_pct"].items())
    body = (f"<p><b>The uncensored packs generate {h['decode']} fewer tokens per second.</b> This is where the turn time "
            "goes: the model writes a little slower.</p>" + fig
            + "<p>Each pack ran in two boots per context size (a boot is one fresh start of the server). Each dot is "
            f"the median of 3 requests in one boot. The largest gap between the two boots of one pack: {spread}; "
            f"{d['pairs_under_4']} of the {d['pairs']} pairs differ by less than 4%, and the worst pair by up to "
            f"{h['noise']:.0f}%. I found no pattern by position in the queue.</p>"
            "<p>At a single context size I cannot tell the packs apart. Across the three sizes "
            + ", ".join(f"{SHORT[a]} is {abs(v):.1f}% {'slower' if v < 0 else 'faster'} (below the standard pack at "
                        f"{d['below_standard'][a]} of 3 sizes)" for a, v in d["decode_mean_pct"].items())
            + ", taking the mean of the 6 boots of each pack. That is weak evidence of a slowdown of a few percent for "
            "Heretic v2 and Huihui v2, and weaker still for SC117. The data rules out a slowdown above about 10%.</p>")
    return rr._section("decode", "Token generation", "A few percent fewer tokens per second, close to the noise", body)


def _cold(d: dict) -> str:
    h, p = _headline(d), d["pooled"]
    groups = [f"{c} context" for c in CTXS.values()]
    series = [(SHORT[a], COLOUR[a]) for a in ARMS]
    values = {(f"{CTXS[c]} context", SHORT[a]): p[(a, c)]["cold_ttft_s"] for a in ARMS for c in CTXS}
    svg = sc.paired_bars(groups, series, values, max(values.values()),
                         "Seconds to the first token with an empty cache, per context size and pack",
                         "The four packs take the same time to read a prompt, within about 1%: "
                         + ", ".join(f"{p[('k2h', c)]['cold_ttft_s']:.0f} to {max(p[(a, c)]['cold_ttft_s'] for a in ARMS):.0f} "
                                     f"seconds at {CTXS[c]}" for c in CTXS) + ".")
    trows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['cold_ttft_s']} s", f"{p[(a, c)]['prefill_tps']:.0f}",
              f"{p[(a, c)]['cold_ttft_s'] / p[('k2h', c)]['cold_ttft_s']:.3f}×"] for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "Seconds to the first token when the whole prompt is new. Shorter is better.",
                     ["pack", "context", "cold first token", "prompt tokens/s", "ratio"], trows, _legend(ARMS))
    body = (f"<p><b>No real difference: at most {h['cold']} slower.</b> Reading a full prompt for the first time is the "
            "slow part of a local model. The pack changes it by about 1%; the context size changes it tenfold.</p>" + fig)
    return rr._section("cold", "Reading a cold prompt", "The same wait on every pack", body)


def _memory(d: dict) -> str:
    p = d["pooled"]
    groups = [f"{c} context" for c in CTXS.values()]
    series = [(SHORT[a], COLOUR[a]) for a in ARMS]
    values = {(f"{CTXS[c]} context", SHORT[a]): p[(a, c)]["wired_gb"] for a in ARMS for c in CTXS}
    svg = sc.paired_bars(groups, series, values, 128.0, "Peak wired memory of the machine while the server ran, in GB of 128 GB",
                         "The two IQ3_S packs use about 13 GB less than the standard pack; Heretic v2 uses about 2 GB more.")
    trows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['wired_gb']} GB",
              f"{p[(a, c)]['wired_gb'] - p[('k2h', c)]['wired_gb']:+.1f} GB"] for a in ARMS for c in CTXS]
    fig = rr._figure(svg, "Peak wired memory of the whole machine while the server ran; the bar is full at 128 GB.",
                     ["pack", "context", "peak memory", "against standard"], trows, _legend(ARMS))
    k, z4, z2 = (p[(a, 131072)]["wired_gb"] for a in ("k2h", "z4h", "z2h"))
    body = (f"<p><b>Memory tracks the size of the weight files.</b> At 128K the two IQ3_S packs peak {k - z2:.0f} GB "
            f"below the standard pack: they are smaller files. Heretic v2 peaks {z4 - k:.0f} GB above it, at the same "
            "quantization level but with a different recipe; I did not isolate the cause.</p>" + fig)
    return rr._section("memory", "Memory", "Smaller files, less memory", body)


def _same(d: dict) -> str:
    p = d["pooled"]
    rows = [[SHORT[a], CTXS[c], f"{p[(a, c)]['warm_raw']:.2f} s", f"{100 * p[(a, c)]['hit']:.1f}%", p[(a, c)]["errors"]]
            for a in ARMS for c in CTXS]
    worst = max(p[(a, c)]["warm_raw"] - p[("k2h", c)]["warm_raw"] for a in ARMS for c in CTXS)
    cut = ", ".join(f"one {SHORT[a]} answer at {CTXS[c]}" for a, c in d["truncated"])
    body = ("<p>Three things barely change with the pack: the time to the first token on a warm cache (at most "
            f"{worst:.2f} s more), the share of the prompt the cache reuses, and the error count.</p>"
            + rr._table(["pack", "context", "warm first token", "prompt reused from cache", "HTTP errors"], rows)
            + f"<p>{d['correct']} of {d['requests']} requests returned the facts planted in the prompt. The exception: "
            f"{cut} used all 4096 output tokens and was cut off before answering.</p>"
            "<p class=\"note\">In real coding sessions I also measured no slowdown: on 7 small tasks the Heretic v2 pack "
            "took 0.78× to 0.99× the session time of the standard pack (median time of the sessions that passed; "
            f'Heretic v2 passed 51 of 56, the standard pack 54). See <a href="{DELIVERY_PAGE}">Four coding '
            "harnesses, one local model</a>.</p>")
    return rr._section("same", "What stays the same", "Cache reuse and warm start", body)


def _limits(d: dict) -> str:
    items = [
        "<b>Two boots per pack and context size, 3 warm requests per boot.</b> A difference under about 5% at one "
        f"context size is inside the boot-to-boot spread (worst pair: {_headline(d)['noise']:.0f}%).",
        "<b>Quantization is mixed in.</b> Two of the three uncensored packs are IQ3_S; the standard pack is IQ4_XS. "
        "I did not run the standard pack at IQ3_S.",
        "<b>Heretic v2 is not the file as published.</b> The server refused it; I recast 24 indexer tensors from F16 "
        "to BF16, two number formats that hold the same values here.",
        "<b>One machine, one server.</b> Mac Studio M4 Max 128 GB and Splash 1.6.1. Another runtime may behave differently.",
        "<b>One stream.</b> No concurrent requests.",
        "<b>Speed only.</b> This page does not measure answer quality.",
    ]
    return rr._section("limits", "Limits", "What this does not show", "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")


def _method(d: dict) -> str:
    setup = [
        ["Machine", "Mac Studio M4 Max, 128 GB"],
        ["Server", "Splash 1.6.1, temperature 1.0, reasoning effort xhigh, one stream"],
        ["Run", "2026-11-13 and 14: 24 server boots, 4 packs × 3 context sizes × 2 boots, 5 scenarios per boot. Mirrored "
                "order: the standard pack runs first and last at 32K and 256K, and in the two middle slots at 128K"],
        ["Labels in the data", " · ".join(f"{a}: {FULL[a]}" for a in ARMS)],
        ["Agent turn", "median first-token time of the tool-turn request + 512 tokens ÷ median generation speed of "
                       "the 3 warm requests (T_turno in the data). A tool turn is a follow-up request that appends a "
                       "tool result to a cached prompt"],
        ["Memory", "peak of the wired pages of the whole machine, sampled while the server ran"],
        ["Cold first token", "time to the first token when no part of the prompt is in the cache"],
        ["Terms", "Splash: the local model server · GGUF: the weight file format · IQ4_XS, IQ3_S: quantization "
                  "levels of about 4 and 3 bits per weight · GSQ-RCO: a quantizer · imatrix: calibration data used "
                  "when quantizing · context: the prompt size the server is set up for, in tokens"],
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
