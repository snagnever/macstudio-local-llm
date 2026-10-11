#!/usr/bin/env python3
"""Render the public guide reports/qwen38-flashnext-m4max-guide.html.

One page for readers outside this repo (Reddit): the best way to run Qwen3.8-Flash-Next on an
M4 Max 128 GB, from 8K to 512K. It joins the October runtime data (overview + perf-lines) and the
Swift 1.5 A/B, and it uses plain names instead of the campaign codes (arms, T_turn, gates, bands).

    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_m4max_guide.py          # the page, card and post HTML
    python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_m4max_guide.py --png    # also the PNGs (Chrome)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
REPO = CAMPAIGN.parents[1]
REPORTS_JSON = REPO / "bench" / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
SWIFT_JSON = REPO / "bench" / "swift15-flashnext-2026-10" / "results" / "page-data.json"
OUT = REPO / "reports" / "qwen38-flashnext-m4max-guide.html"
# The link-preview card (og:image). The HTML is the source; --png renders it with headless Chrome.
CARD_HTML = REPO / "reports" / "assets" / "qwen38-flashnext-m4max-guide-card.html"
CARD_PNG = CARD_HTML.with_suffix(".png")
# The post image: a taller static poster with the main charts, for the Reddit image post.
POST_HTML = REPO / "reports" / "assets" / "qwen38-flashnext-m4max-guide-post.html"
POST_PNG = POST_HTML.with_suffix(".png")
POST_W, POST_H = 1400, 1400
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

CTX = [8192, 32768, 131072, 262144, 524288]

# Plain names for the four October arms. The color slot and the marker shape follow the stack on every chart.
STACKS = [
    {"id": "n2", "name": "mlx-serve 26.10.1", "short": "mlx-serve", "cv": "--s1", "marker": "circle",
     "about": "MLX server by ddalcu",
     "quant": "ddalcu iQ-MLX 4.7 bpw", "model": "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw",
     "repo": "https://github.com/ddalcu/mlx-serve", "disk": "107 GB",
     "cache": "RAM (16 GB) + disk (100 GB)", "spec": "MTP + n-gram lookup",
     "max": "512K (YaRN 2.0 + 4-bit KV cache)", "max_ctx": 524288},
    {"id": "o1", "name": "oMLX 0.7.0", "short": "oMLX", "cv": "--s2", "marker": "square",
     "about": "MLX server by Jundot",
     "quant": "Jundot oQ4e-mtp (5.97 bpw)", "model": "Jundot/Qwen3.8-Flash-Next-oQ4e-mtp",
     "repo": "https://github.com/jundot/omlx", "disk": "132 GB",
     "cache": "paged, spills over to SSD", "spec": "MTP",
     "max": "262K (no YaRN support)", "max_ctx": 262144},
    {"id": "m1", "name": "MTPLX 2.12.2", "short": "MTPLX", "cv": "--s3", "marker": "triangle",
     "about": "MLX server by Youssofal, ships its own quant packs",
     "quant": "MTPLX Optimized-Speed (5.43 bpw)", "model": "Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed",
     "repo": "https://github.com/youssofal/MTPLX", "disk": "120 GB",
     "cache": "session bank in RAM + SSD", "spec": "MTP (depth 3)",
     "max": "128K, only with --memory-limit max", "max_ctx": 131072},
    {"id": "d1", "name": "ds4 (antirez, build 0aaea5a)", "short": "ds4", "cv": "--s4", "marker": "diamond",
     "about": "antirez's inference engine, Metal backend, GGUF weights",
     "quant": "antirez Q4 GGUF", "model": "antirez/qwen3.8-flash-next-gguf",
     "repo": "https://github.com/antirez/ds4", "disk": "177 GB",
     "cache": "on disk (100 GB)", "spec": "MTP (1 draft token)",
     "max": "512K (YaRN 2.0)", "max_ctx": 524288},
]
STACK = {s["id"]: s for s in STACKS}

# Sizes a stack does not serve: the page shows the reason instead of a number.
MISSING = {
    ("o1", 524288): "no YaRN: oMLX stops at the native 262K",
    ("m1", 262144): "refused: the MTPLX memory plan fits at most 237,568 tokens on 128 GB",
    ("m1", 524288): "not run: MTPLX already refuses 256K",
}
CONFIG_LABEL = {
    "memory limit max": "--memory-limit max",
    "YaRN 2.0 + KV 4-bit": "YaRN 2.0 + 4-bit KV cache",
    "YaRN 2.0": "YaRN 2.0",
}
QUALITY_SUITES = [("humaneval", "HumanEval (164)"), ("jdhodges", "Tool calls A (40)"), ("veerman", "Tool calls B (12)")]
SWIFT_SUITES = [("gpqa", "GPQA-Diamond (50)"), ("livecodebench", "LiveCodeBench v6 (50)"), ("humaneval", "HumanEval (164)")]


def canonical(data: dict) -> dict:
    return {(g["cand"], g["context"]): g for g in data["groups"] if g["canonical"]}


def point(g: dict) -> dict:
    reuse = g["hit"]["tool_turn"]
    return {
        "turn": g["t_turno_s"], "resume": g["ttft_s"]["tool_turn"], "append": g["ttft_s"]["append"],
        "cold": g["cold_ttft_s"], "edit": g["ttft_s"]["middle_mutation"],
        "decode": g["decode_tps"], "prefill": g["prefill_tps"], "wired": g["wired_peak_gb"],
        "swap": g["swap_delta_gb"], "reuse": reuse, "reuse_edit": g["hit"]["middle_mutation"],
        "reread": round((1 - reuse) * g["context"]), "reps": g["reps"],
        "hits": {sc: (g["hit"][sc] if sc in g["scenarios_served"] else None) for sc in g["scenarios_run"]},
        "config": CONFIG_LABEL.get(g.get("config") or "", ""),
    }


def quality_rows(data: dict, swift: dict) -> list[dict]:
    # mlx-serve: the 2026-10-11 run with explicit reasoning (Swift A/B, vendor sampling). The 2026-10-07 run
    # did not think, so it is left out. oMLX and MTPLX: the 2026-10-09 runs.
    q = swift["quality"]["t1"]["n2"]
    he = swift["humaneval_regrade"]["n2-t1"]
    rows = [{"id": "n2", "date": "2026-10-11", "humaneval": [he["with_imports"], he["n"]],
             "jdhodges": [q["jdhodges"]["passed"], q["jdhodges"]["n"]],
             "veerman": [q["veerman"]["passed"], q["veerman"]["n"]]}]
    legacy = {r["arm"]: r for r in data["quality"]["rows"]}
    for sid, arm in (("o1", "o1"), ("m1", "m1x")):
        r = legacy[arm]
        rows.append({"id": sid, "date": r["date"], "humaneval": [r["humaneval_imports"], r["humaneval_n"]],
                     "jdhodges": [r["jdhodges"], r["jdhodges_n"]], "veerman": [r["veerman"], r["veerman_n"]]})
    return rows


def swift_rows(swift: dict) -> list[dict]:
    rows = []
    for key, label in SWIFT_SUITES:
        arms = swift["time"]["t1"][key]["arms"]
        row = {"key": key, "label": label}
        for arm in ("n2", "w1"):
            passed = arms[arm]["passed"]
            if key == "humaneval":
                passed = swift["humaneval_regrade"][f"{arm}-t1"]["with_imports"]
            row[arm] = {"median": arms[arm]["median_s"], "passed": passed, "n": arms[arm]["n"]}
        rows.append(row)
    return rows


def build_payload(data: dict, swift: dict) -> dict:
    canon = canonical(data)
    points: dict = {}
    for s in STACKS:
        sid = s["id"]
        points[sid] = {}
        for ctx in CTX:
            g = canon.get((sid, ctx))
            if g is not None and not g["refused"]:
                points[sid][str(ctx)] = point(g)
            elif (sid, ctx) in MISSING:
                points[sid][str(ctx)] = {"reason": MISSING[(sid, ctx)]}
    stacks = [{k: s[k] for k in ("id", "name", "short", "cv", "marker", "max_ctx")} for s in STACKS]
    return {"ctx": CTX, "stacks": stacks, "points": points, "quality": quality_rows(data, swift),
            "quality_suites": QUALITY_SUITES, "swift": swift_rows(swift),
            "generated_at": data["generated_at"]}


def _pt(data: dict, sid: str, ctx: int) -> dict:
    return point(canonical(data)[(sid, ctx)])


def _k(n: float) -> str:
    return f"{n / 1000:.0f}K" if n >= 1000 else f"{n:.0f}"


def facts(data: dict, swift: dict) -> dict:
    """Numbers the prose quotes. Every value comes from the data, so the text cannot drift from the charts."""
    p = {(sid, ctx): _pt(data, sid, ctx) for (sid, ctx), g in canonical(data).items() if not g["refused"]}
    f: dict = {}
    for ctx, tag in zip(CTX, ("8", "32", "128", "256", "512")):
        f[f"mlx_turn_{tag}"] = f'{p[("n2", ctx)]["turn"]:.1f}'
        f[f"mlx_resume_{tag}"] = f'{p[("n2", ctx)]["resume"]:.1f}'
        f[f"ds4_turn_{tag}"] = f'{p[("d1", ctx)]["turn"]:.1f}'
    n512, n128, d512 = p[("n2", 524288)], p[("n2", 131072)], p[("d1", 524288)]
    f["omlx_turn_128"] = f'{p[("o1", 131072)]["turn"]:.1f}'
    f["omlx_turn_256"] = f'{p[("o1", 262144)]["turn"]:.1f}'
    f["mtplx_turn_32"] = f'{p[("m1", 32768)]["turn"]:.1f}'
    f["mtplx_turn_128"] = f'{p[("m1", 131072)]["turn"]:.1f}'
    f["mtplx_decode_128"] = f'{p[("m1", 131072)]["decode"]:.0f}'
    f["mtplx_prefill_128"] = f'{p[("m1", 131072)]["prefill"]:.0f}'
    f["mtplx_resume_128"] = f'{p[("m1", 131072)]["resume"]:.1f}'
    f["mlx_decode_128"] = f'{n128["decode"]:.0f}'
    f["mlx_prefill_128"] = f'{n128["prefill"]:.0f}'
    f["mlx_decode_512"] = f'{n512["decode"]:.0f}'
    f["mlx_cold_128_min"] = f'{n128["cold"] / 60:.0f}'
    f["mlx_cold_512_min"] = f'{n512["cold"] / 60:.0f}'
    f["mlx_edit_512_min"] = f'{n512["edit"] / 60:.0f}'
    f["cold_ratio_512"] = f'{round(n512["cold"] / n512["resume"], -1):.0f}'
    f["mlx_reuse_512"] = f'{n512["reuse"] * 100:.1f}'
    f["mlx_reread_512"] = _k(n512["reread"])
    f["ds4_reuse_512"] = f'{d512["reuse"] * 100:.1f}'
    f["ds4_reread_512"] = _k(d512["reread"])
    f["ds4_resume_512"] = f'{d512["resume"]:.0f}'
    f["ds4_resume_128"] = f'{p[("d1", 131072)]["resume"]:.1f}'
    f["ds4_decode_lo"] = f'{min(p[("d1", c)]["decode"] for c in CTX):.0f}'
    f["ds4_decode_hi"] = f'{max(p[("d1", c)]["decode"] for c in CTX):.0f}'
    f["pct_tokens_512"] = f"{0.01 * 524288:,.0f}"
    f["sec_per_pct_512"] = f'{0.01 * 524288 / n512["prefill"]:.0f}'
    wired = [p[("n2", c)]["wired"] for c in CTX[1:]]
    f["mlx_wired_min"], f["mlx_wired_max"] = f"{min(wired):.0f}", f"{max(wired):.0f}"
    f["prefill_hi"] = f'{max(v["prefill"] for v in p.values()):.0f}'
    f["gap_tokens_512"] = f'{round((d512["reread"] - n512["reread"]), -3):,.0f}'
    f["mlx_wired_128"] = f'{n128["wired"]:.0f}'
    others = [p[(sid, 131072)]["wired"] for sid in ("o1", "m1", "d1")]
    f["others_wired_128_lo"], f["others_wired_128_hi"] = f"{min(others):.0f}", f"{max(others):.0f}"
    sw = {r["key"]: r for r in swift_rows(swift)}
    f["swift_gpqa_x"] = f'{sw["gpqa"]["n2"]["median"] / sw["gpqa"]["w1"]["median"]:.1f}'
    f["swift_lcb_x"] = f'{sw["livecodebench"]["n2"]["median"] / sw["livecodebench"]["w1"]["median"]:.1f}'
    return f


def stacks_table() -> str:
    rows = "".join(
        f'<tr><td><span class="sw" style="background:var({s["cv"]})"></span><a href="{s["repo"]}" '
        f'target="_blank" rel="noopener">{s["name"]}</a><br><small class="about">{s["about"]}</small></td>'
        f'<td><a href="https://huggingface.co/{s["model"]}" target="_blank" rel="noopener">{s["quant"]}</a></td>'
        f'<td>{s["disk"]}</td><td>{s["cache"]}</td><td>{s["spec"]}</td><td>{s["max"]}</td></tr>'
        for s in STACKS)
    head = "".join(f"<th>{h}</th>" for h in ("Server", "Weights (quant)", "Disk", "Prefix cache lives in",
                                               "Speculative decoding", "Largest context on 128 GB"))
    return f'<table class="txt"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'


def rig_strip(data: dict) -> str:
    keep = {"Chip", "GPU", "Unified memory", "macOS"}
    # The macOS build number is noise for a reader outside this repo.
    return "".join(f'<span class="chip"><span class="lab">{r["lab"]}</span> {r["val"].split(" (")[0]}</span>'
                   for r in data["rig"] if r["lab"] in keep)


def render(data: dict, swift: dict) -> str:
    f = facts(data, swift)
    body = BODY.format_map(f)
    html = TEMPLATE.replace("/*__CSS__*/", CSS).replace("__BODY__", body)
    html = html.replace("__STACKS_TABLE__", stacks_table()).replace("__RIG__", rig_strip(data))
    html = html.replace("__COMMANDS__", COMMANDS).replace("__JS__", JS)
    payload = json.dumps(build_payload(data, swift), ensure_ascii=False).replace("</", "<\\/")
    return html.replace("__PAYLOAD__", payload)


COMMANDS = r"""<div class="cmd">
      <p class="cmd-lab">Up to 256K (native context)</p>
<pre><code>mlx-serve --model ~/models/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw \
  --serve --host 127.0.0.1 --port 11234 \
  --ctx-size 262144 --mtp --ssm-checkpoint-max 16 \
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64</code></pre>
    </div>
    <div class="cmd">
      <p class="cmd-lab">512K (YaRN 2.0 + 4-bit KV cache)</p>
<pre><code>mlx-serve --model ~/models/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw \
  --serve --host 127.0.0.1 --port 11234 \
  --ctx-size 524288 --mtp --ssm-checkpoint-max 16 \
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64 \
  --kv-quant 4 --kv-attn-mode fused \
  --config-overrides '{"text_config":{"rope_parameters":{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":262144},"max_position_embeddings":524288}}'</code></pre>
    </div>"""

# Page copy. format_map() fills the {fact} fields from facts(); keep literal braces out of this string.
BODY = r"""
<header class="top">
  <div>
    <p class="eyebrow">Benchmark · Apple M4 Max 128 GB · October 2026</p>
    <h1>The best way to run Qwen3.8-Flash-Next on an M4 Max 128 GB</h1>
    <p class="sub">Four local inference servers, the same model, contexts from 8K to 512K tokens. I measured what
    you wait for in a real agent session, not only tokens per second.</p>
    <div class="chips">__RIG__<span class="chip"><span class="lab">Measured</span> 2026-10-07 to 2026-10-11</span></div>
    <p class="tldr"><b>Result:</b> mlx-serve 26.10.1 with the ddalcu iQ-MLX 4.7 bpw quant. {mlx_turn_128} s per agent turn at
    128K, {mlx_turn_512} s at 512K, {mlx_resume_512} s to start the next reply at 512K from the cache.
    <a href="#conclusion">Conclusion</a> · <a href="#run">commands</a>.</p>
  </div>
  <button class="theme" id="themeBtn" type="button">theme: auto</button>
</header>

<section class="premises" aria-label="Assumptions">
  <div class="pm"><p class="kicker">Goal</p><p>Find the best stack to run Qwen3.8-Flash-Next as a daily driver on one
  Mac Studio (M4 Max, 128 GB). The model is a 125B mixture-of-experts with 6B active parameters and a native context of
  262K tokens, so it fits in 128 GB at 4 to 6 bits per weight and decodes fast.</p></div>
  <div class="pm"><p class="kicker">Weights</p><p>Each stack runs the pack its runtime's author publishes for it, in the
  runtime's own format: the current ddalcu pack for mlx-serve, the only oMLX pack for Flash-Next, the pack MTPLX
  recommends for 128 GB Macs, and the larger of the two ds4 GGUFs, chosen for quality parity. The files are as close to
  each other as the formats allow (4.7 to 5.97 bits per weight), but they are not identical. The quality check in
  <a href="#quality">section 11</a> shows the three servers I checked within a few cases of each other; ds4 was not checked.</p></div>
  <div class="pm"><p class="kicker">Precision</p><p>A personal test for my own daily use and curiosity, not a lab
  benchmark. I aimed for accurate numbers without letting the runs take days: one machine, one test prompt, 1 to 3
  runs per point. Small differences can be run-to-run variation.</p></div>
</section>

<details class="toc">
  <summary>Table of contents</summary>
  <ol id="tocList"></ol>
</details>

<section class="block" id="stacks">
  <h2 class="sec">1 · The four stacks: each server runs its own weight file</h2>
  <p class="s-note">Each server needs its own weight format, so every stack below is a <b>server + quant</b> pair with a
  different file (4.7 to 5.97 bits per weight). The results compare these stacks, not the servers alone. Same base
  model, same test prompt, same sampling: temperature 1.0, top_p 0.95, top_k 20, reasoning effort xhigh, max 4,096
  output tokens. All four use speculative decoding with the model's MTP head and a prefix cache. They differ in where
  the cache lives and in how they handle the memory limit.</p>
  <p class="s-note">Why these four: in October 2026 they were the servers that ran Flash-Next on Apple Silicon with MTP
  and a prefix cache, each on its newest release. I did not measure llama.cpp, LM Studio or mlx-vlm in this round.
  mlx-dspark 0.20.3 ran at 32K only and behind these four, so it is not on the page.</p>
  <div class="tbl-scroll">__STACKS_TABLE__</div>
</section>

<section class="block" id="glance">
  <h2 class="sec">2 · At a glance: mlx-serve leads every speed metric</h2>
  <p class="s-note">Five speed metrics and the largest context, one panel each. Pick a context size: mlx-serve has the
  best value in every panel at every size I tested.</p>
  <div class="ctl"><span class="ctl-lab">Context size</span><div class="seg" data-seg="glance"></div></div>
  <div class="legend" data-legend></div>
  <div class="glance" id="chGlance"></div>
  <p class="foot-note">The trade-off is memory: mlx-serve locks {mlx_wired_128} GB at 128K, against {others_wired_128_lo}–{others_wired_128_hi} GB
  for the other servers (<a href="#limits">memory chart</a>). No server used swap.</p>
</section>

<section class="block" id="turn">
  <h2 class="sec">3 · Agent turn time: mlx-serve is the fastest at every context size</h2>
  <p class="s-note"><b>Agent turn time</b> = the wait from sending a tool result to the end of a 512-token reply:
  TTFT (time to first token) + 512 ÷ decode speed. A coding agent pays this at every step. Lower is better.</p>
  <div class="legend" data-legend></div>
  <div class="panel big"><div id="chTurn"></div><p class="gaps" id="gapsTurn"></p></div>
  <div class="tbl-scroll"><table id="tblTurn"></table></div>
  <ul class="reads">
    <li><b>mlx-serve stays almost flat:</b> {mlx_turn_8} s at 8K, {mlx_turn_128} s at 128K, {mlx_turn_512} s at 512K.</li>
    <li><b>oMLX</b> is second at 128K and 256K ({omlx_turn_128} and {omlx_turn_256} s). <b>MTPLX</b> is close at 32K
    ({mtplx_turn_32} s), but needs a flag to reach 128K and refuses 256K.</li>
    <li><b>ds4</b> serves every size up to 512K, but its turn grows from {ds4_turn_32} s at 32K to {ds4_turn_512} s at 512K.</li>
  </ul>
</section>

<section class="block" id="cache">
  <h2 class="sec">4 · The first message is slow on every server. The next one is what you feel.</h2>
  <p class="s-note">In an agent session, every step sends the whole conversation again: system prompt, files, earlier
  replies and tool results, plus a small new part at the end. A server with a <b>prefix cache</b> keeps the already
  processed part and prefills only the new tokens. Without a cache hit, the step prefills the whole prompt again.</p>
  <div class="explain">
    <svg viewBox="0 0 720 196" role="img" aria-label="How the prefix cache works: first message, next turn, edit in the middle">
      <g class="ex-row">
        <text x="0" y="30" class="ex-lab">First message</text>
        <rect x="150" y="14" width="440" height="26" rx="4" class="ex-read"/>
        <text x="370" y="32" class="ex-in">whole prompt prefilled from scratch</text>
        <text x="600" y="32" class="ex-val">{mlx_cold_512_min} min</text>
      </g>
      <g class="ex-row">
        <text x="0" y="94" class="ex-lab">Next turn</text>
        <rect x="150" y="78" width="426" height="26" rx="4" class="ex-hit"/>
        <rect x="578" y="78" width="12" height="26" rx="3" class="ex-read"/>
        <text x="363" y="96" class="ex-in hit">cache hit</text>
        <text x="600" y="96" class="ex-val">{mlx_resume_512} s</text>
        <text x="584" y="124" class="ex-note">new tokens</text>
      </g>
      <g class="ex-row">
        <text x="0" y="166" class="ex-lab">Edit in the middle</text>
        <rect x="150" y="150" width="218" height="26" rx="4" class="ex-hit"/>
        <rect x="370" y="150" width="220" height="26" rx="4" class="ex-read"/>
        <line x1="369" y1="142" x2="369" y2="184" class="ex-cut"/>
        <text x="259" y="168" class="ex-in hit">cache hit</text>
        <text x="480" y="168" class="ex-in">prefilled again after the edit</text>
        <text x="600" y="168" class="ex-val">{mlx_edit_512_min} min</text>
      </g>
    </svg>
    <p class="ex-cap">mlx-serve at 512K. The bar lengths are schematic; the times are measured.</p>
  </div>
  <div class="callout"><span class="c-big">{mlx_cold_512_min} min → {mlx_resume_512} s</span>
  <span class="c-txt">At 512K, mlx-serve needs {mlx_cold_512_min} minutes to prefill the full prompt the first time. With a
  cache hit, the next reply starts after {mlx_resume_512} s, about {cold_ratio_512}× faster. No server prefilled
  faster than {prefill_hi} tokens/s on this machine, so the first message is slow everywhere. The cache makes the
  difference.</span></div>
  <div class="ctl"><span class="ctl-lab">Context size</span><div class="seg" data-seg="wait"></div></div>
  <div class="panel big"><div id="chWait"></div>
    <div class="shape-key"><span><i class="k-cold"></i>first message (cold prefill)</span><span><i class="k-edit"></i>edit in the middle of the history</span><span><i class="k-next"></i>next turn (cache hit)</span></div>
  </div>
  <div class="tbl-scroll"><table id="tblWait"></table></div>
</section>

<section class="block" id="reuse">
  <h2 class="sec">5 · At long context, a 95% cache hit is not enough</h2>
  <p class="s-note">All four servers have a high cache hit rate on the next turn. At 512K the part that misses can still
  be a lot of tokens. ds4 hits {ds4_reuse_512}% and prefills about {ds4_reread_512} tokens again, so its next reply
  starts after {ds4_resume_512} s. mlx-serve hits {mlx_reuse_512}%, prefills about {mlx_reread_512} tokens and starts
  after {mlx_resume_512} s.</p>
  <div class="ctl"><span class="ctl-lab">Context size</span><div class="seg" data-seg="reread"></div></div>
  <div class="panel big"><div id="chReread"></div></div>
  <div class="callout small"><span class="c-big">1% ≈ {sec_per_pct_512} s</span><span class="c-txt">Rule of thumb at 512K:
  each 1% of cache miss is about {pct_tokens_512} tokens, or about {sec_per_pct_512} s of extra wait
  on this machine.</span></div>
  <div class="grid2">
    <div class="panel"><div class="p-head"><span class="p-title">TTFT on the next turn (cache hit)</span><span class="p-unit">s · lower is better</span></div><div id="chResume"></div>
    <p class="p-interp">mlx-serve stays under 4 s up to 512K. ds4 grows from {ds4_resume_128} s at 128K to {ds4_resume_512} s at 512K.</p></div>
    <div class="panel"><div class="p-head"><span class="p-title">Cache hit rate on the next turn</span><span class="p-unit">% · higher is better</span></div><div id="chReuse"></div>
    <p class="p-interp">The lines look close, but at 512K the gap between {ds4_reuse_512}% and {mlx_reuse_512}% is about {gap_tokens_512} tokens.</p></div>
  </div>
</section>

<section class="block" id="scenarios">
  <h2 class="sec">6 · Cache hit by scenario</h2>
  <p class="s-note">Share of the prompt the server took from the cache, per scenario. <b>First message</b> is 0% by
  design. <b>Edit in the middle</b> can reuse at most the part before the edit, about half. The two scenarios an agent
  repeats all day are <b>user adds a message</b> and <b>next turn</b>: above 90% is good.</p>
  <div class="ctl"><span class="ctl-lab">Context size</span><div class="seg" data-seg="hits"></div></div>
  <div class="tbl-scroll"><table id="tblHits" class="heat"></table></div>
</section>

<section class="block" id="speed">
  <h2 class="sec">7 · Tokens per second is not the whole story</h2>
  <p class="s-note">At 128K, MTPLX decodes almost as fast as mlx-serve ({mtplx_decode_128} vs {mlx_decode_128}
  tokens/s). Its agent turn still takes {mtplx_turn_128} s against {mlx_turn_128} s: its TTFT on the next turn is
  {mtplx_resume_128} s, and its prefill runs at {mtplx_prefill_128} tokens/s against {mlx_prefill_128}. Compare
  servers on turn time and cache behavior, not on decode speed alone.</p>
  <div class="ctl"><span class="ctl-lab">Context size</span><div class="seg" data-seg="scatter"></div></div>
  <div class="panel big"><div class="p-head"><span class="p-title">Decode speed vs agent turn time</span><span class="p-unit">best = bottom right</span></div><div id="chScatter"></div></div>
  <div class="grid2">
    <div class="panel"><div class="p-head"><span class="p-title">Decode speed</span><span class="p-unit">tokens/s · higher is better</span></div><div id="chDecode"></div>
    <p class="p-interp">mlx-serve: {mlx_decode_128} tokens/s at 128K, {mlx_decode_512} at 512K. ds4 stays at {ds4_decode_lo}–{ds4_decode_hi} tokens/s.</p></div>
    <div class="panel"><div class="p-head"><span class="p-title">Prefill speed (cold prompt)</span><span class="p-unit">tokens/s · higher is better</span></div><div id="chPrefill"></div>
    <p class="p-interp">MTPLX drops to {mtplx_prefill_128} tokens/s at 128K. The others stay almost flat.</p></div>
  </div>
</section>

<section class="block" id="limits">
  <h2 class="sec">8 · What each server can serve on 128 GB</h2>
  <p class="s-note">The model's native context is 262,144 tokens. 512K uses YaRN 2.0, a context extension that
  oMLX does not support. A cell shows the agent turn time, or why that size did not run.</p>
  <div class="tbl-scroll"><table id="tblSupport"></table></div>
  <ol class="fn" id="fnSupport"></ol>
  <div class="panel big" style="margin-top:14px"><div class="p-head"><span class="p-title">Peak memory locked by the server</span><span class="p-unit">GB · of 128 GB</span></div><div id="chMem"></div>
  <p class="p-interp">No server used swap. mlx-serve locks the KV and prefix cache in memory on purpose: {mlx_wired_min}–{mlx_wired_max} GB
  from 32K to 512K. Close other large apps before a long session.</p></div>
</section>

<section class="verdict" id="conclusion" aria-labelledby="v-title">
  <div class="v-main">
    <p class="kicker">Conclusion</p>
    <h2 id="v-title">Use <b>mlx-serve 26.10.1</b> with the <b>ddalcu iQ-MLX 4.7 bpw</b> quant.</h2>
    <p>It had the shortest agent turn at every context size I tested, from 8K to 512K. It is the only server
    that kept a turn under 15 s at 512K. The runner-up is <b>oMLX 0.7.0</b> ({omlx_turn_128} s at 128K), but it stops
    at 256K. <a href="#run">Commands below.</a></p>
  </div>
  <div class="tiles">
    <div class="tile"><span class="t-val">{mlx_turn_128}<small> s</small></span><span class="t-lab">per agent turn at 128K context</span></div>
    <div class="tile"><span class="t-val">{mlx_turn_512}<small> s</small></span><span class="t-lab">per agent turn at 512K context</span></div>
    <div class="tile"><span class="t-val">{mlx_resume_512}<small> s</small></span><span class="t-lab">to start the next reply at 512K, from cache (first message: {mlx_cold_512_min} min)</span></div>
    <div class="tile"><span class="t-val">{mlx_wired_max}<small> GB</small></span><span class="t-lab">peak memory at 512K, no swap</span></div>
  </div>
</section>

<section class="block" id="run">
  <h2 class="sec">9 · Run it yourself</h2>
  <p class="s-note">Download <a href="https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw" target="_blank" rel="noopener">ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw</a>
  (107 GB) and <a href="https://github.com/ddalcu/mlx-serve" target="_blank" rel="noopener">mlx-serve 26.10.1</a>. These are the
  flags I measured. The server exposes OpenAI and Anthropic compatible endpoints. The data, the prompt generator and
  the scripts behind this page are in the <a href="https://github.com/snagnever/macstudio-local-llm" target="_blank" rel="noopener">repository</a>.</p>
  <div class="cmds">__COMMANDS__</div>
  <ul class="reads">
    <li>The prefix cache flags matter. In my September test (mlx-serve 26.9.1), the default 2 GB cache could not hold a
    128K session, and every turn read the whole prompt again.</li>
    <li>For 512K, use the 4-bit KV cache. With 8-bit, some long prompts were refused because they did not fit in memory.</li>
  </ul>
</section>

<section class="block" id="tips">
  <h2 class="sec">10 · Tips for daily use</h2>
  <ul class="tips">
    <li><b>Keep the start of the prompt stable.</b> System prompt, tool list and project rules come first. A change
    there invalidates the cache for everything after it.</li>
    <li><b>Add, do not edit.</b> At 512K, an edit in the middle of the history costs {mlx_edit_512_min} min on mlx-serve. A new
    message at the end costs seconds.</li>
    <li><b>Plan for the first load.</b> Prefilling a cold 128K prompt takes about {mlx_cold_128_min} min, 512K about
    {mlx_cold_512_min} min. Load once, then keep working in the same session.</li>
    <li><b>Leave memory headroom.</b> mlx-serve locks {mlx_wired_min}–{mlx_wired_max} GB from 32K to 512K.</li>
    <li><b>Use the context you need.</b> The turn grows from {mlx_turn_128} s at 128K to {mlx_turn_512} s at 512K, and 512K
    needs the 4-bit KV cache.</li>
  </ul>
</section>

<section class="block" id="quality">
  <h2 class="sec">11 · Quality sanity check</h2>
  <p class="s-note">Does a server or quant break the model? Not in these runs: the three servers I checked are within
  a few cases of each other. One run per server, on different dates, with a small sample. Read it as a sanity check,
  not as a ranking. ds4 was not checked.</p>
  <div class="panel big"><div id="chQuality"></div></div>
  <p class="foot-note">HumanEval with the prompt's import lines added before the answer. Tool calls A = jdhodges tool-call
  test; tool calls B = Veerman tool-call test. mlx-serve: 2026-10-11 run with reasoning effort xhigh; oMLX and MTPLX
  (with --memory-limit max): 2026-10-09 runs.</p>
</section>

<section class="block" id="swift">
  <h2 class="sec">12 · Bonus: Swift 1.5, a fine-tune on the same stack</h2>
  <p class="s-note">Swift 1.5 is a community fine-tune of Qwen3.8-Flash-Next that thinks less before it answers. I ran
  it on the same mlx-serve setup. It scored the same as the base quant within the noise of these samples, and it reached
  the final answer {swift_gpqa_x}× faster on GPQA and {swift_lcb_x}× faster on LiveCodeBench. Its agent turn time is the
  same, because prefill and the cache do not change. I now use it every day.</p>
  <div class="panel big"><div class="p-head"><span class="p-title">Median time to the final answer</span><span class="p-unit">s per question · lower is better</span></div><div id="chSwift"></div></div>
  <p class="foot-note">Vendor sampling, reasoning effort xhigh, one run per model. Base: ddalcu iQ-MLX 4.7 bpw. Swift 1.5:
  <a href="https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw" target="_blank" rel="noopener">Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw</a>.
  The two packs also have different n-gram tables, so the comparison is between the packs, not only the fine-tune.</p>
</section>

<section class="block" id="method">
  <h2 class="sec">13 · How I measured</h2>
  <dl class="method">
    <dt>Test prompt</dt><dd>A long audit document filled to the target size, with three facts hidden at 10%, 50% and
    90% of the text. A reply is correct when it finds all three.</dd>
    <dt>Scenarios</dt><dd><b>First message</b>: the full prompt, no cache (cold prefill). <b>Next turn</b>: the same prompt plus a tool
    result at the end. <b>User adds a message</b>: the same prompt plus a new user message. <b>Edit in the middle</b>:
    the prompt changes halfway, so only the first half can be a cache hit.</dd>
    <dt>Agent turn time</dt><dd>TTFT on the next turn + 512 ÷ median decode speed. It is the wait
    for one agent step with a 512-token reply.</dd>
    <dt>Runs</dt><dd>One to three runs per point; the "Runs" column of the last table gives the number. A point with
    three runs shows the median.</dd>
    <dt>Speculative decoding (MTP)</dt><dd>The model has a small extra head that drafts the next tokens; the server
    checks them in one pass. Output stays the same, decode gets faster.</dd>
    <dt>YaRN</dt><dd>A method that stretches the model's position encoding beyond its native 262K tokens.</dd>
    <dt>Harness</dt><dd>A script sends each scenario to the server's HTTP API and reads the timings from the stream.
    No coding agent sits in the loop.</dd>
    <dt>Data and scripts</dt><dd>The raw results, the prompt generator and this page's script are in the
    <a href="https://github.com/snagnever/macstudio-local-llm" target="_blank" rel="noopener">repository</a>
    (<code>bench/engine-updates-2026-10</code> and <code>bench/swift15-flashnext-2026-10</code>).</dd>
  </dl>
  <h3>What this page does not measure</h3>
  <ul class="reads">
    <li><b>Agent reliability over many turns.</b> Speed, cache and memory only. Test your own agent workload before
    you choose.</li>
    <li><b>Other chips.</b> Numbers from an M5 Max or an M3 Ultra do not transfer to this M4 Max, and the reverse is
    also true.</li>
    <li><b>Power draw and fan noise.</b></li>
    <li><b>Several requests at once.</b> Every run sent one request at a time.</li>
    <li><b>The quality of ds4.</b> Only the three MLX servers went through the sanity check in <a href="#quality">section 11</a>.</li>
  </ul>
  <h3>Setup notes</h3>
  <ul class="reads">
    <li><b>MTPLX.</b> The default config plans only a 65,536-token window on this machine and refuses 128K;
    128K needs <code>--memory-limit max</code>. Short requests without history skip its session cache, so the test
    sends a 64-token warm-up first.</li>
  </ul>
</section>

<section class="block" id="data">
  <h2 class="sec">14 · All values</h2>
  <p class="s-note">One row per server and context size. Times in seconds (TTFT = time to first token). Decode and
  prefill in tokens/s, memory in GB.</p>
  <div class="tbl-scroll"><table id="tblAll"></table></div>
</section>
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Qwen3.8-Flash-Next on M4 Max</title>
<meta name="description" content="Four local servers for Qwen3.8-Flash-Next on an Apple M4 Max 128 GB, from 8K to 512K context: agent turn time, prefix cache, memory.">
<meta property="og:type" content="article">
<meta property="og:title" content="Qwen3.8-Flash-Next on an M4 Max 128 GB: four local servers, 8K to 512K context">
<meta property="og:description" content="Agent turn time, prefix cache hit and memory for mlx-serve, oMLX, MTPLX and ds4. Cache hit matters more than tokens per second.">
<meta property="og:url" content="https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-m4max-guide.html">
<meta property="og:image" content="https://snagnever.github.io/macstudio-local-llm/assets/qwen38-flashnext-m4max-guide-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<style>/*__CSS__*/</style>
</head>
<body>
<div class="wrap">
__BODY__
<footer class="foot" id="foot"></footer>
</div>
<div id="tip" class="tip" role="tooltip"></div>
<script>
const P = __PAYLOAD__;
__JS__
</script>
</body>
</html>
"""

CSS = r"""
:root{
  color-scheme: light;
  --plane:#f9f9f7; --surface:#fcfcfb; --surface-2:#f3f2ee;
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --baseline:#c3c2b7; --border:rgba(11,11,11,0.10);
  --accent:#2a78d6; --accent-soft:rgba(42,120,214,0.16);
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4;
  --mono:"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
    --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
    --accent:#3987e5; --accent-soft:rgba(57,135,229,0.22);
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232321;
  --ink:#ffffff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --baseline:#383835; --border:rgba(255,255,255,0.10);
  --accent:#3987e5; --accent-soft:rgba(57,135,229,0.22);
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--plane); color:var(--ink); font-family:var(--sans); line-height:1.5; -webkit-font-smoothing:antialiased}
a{color:var(--accent)}
code{font-family:var(--mono); font-size:0.88em; background:var(--surface-2); padding:1px 5px; border-radius:4px}
.wrap{max-width:1080px; margin:0 auto; padding:32px 16px 64px}
header.top{display:flex; gap:20px; align-items:flex-start; justify-content:space-between}
h1{font-size:2rem; line-height:1.15; letter-spacing:-0.025em; margin:0; text-wrap:balance; max-width:22ch}
.sub{color:var(--ink-2); max-width:62ch; margin:10px 0 0; font-size:1.02rem}
.eyebrow{font-family:var(--mono); font-size:0.72rem; letter-spacing:0.14em; text-transform:uppercase; color:var(--muted); margin:0 0 8px}
.chips{display:flex; flex-wrap:wrap; gap:6px 8px; margin-top:16px}
.tldr{margin:16px 0 0; padding:10px 14px; border-left:3px solid var(--accent); background:var(--surface); border-radius:0 8px 8px 0; font-size:0.95rem; max-width:72ch}
.tldr a{color:var(--accent)}
.about{display:block; color:var(--muted); font-weight:400; font-size:0.78rem; margin-top:2px; padding-left:18px}
.block h3{font-size:1rem; margin:20px 0 6px; letter-spacing:-0.01em}
.chip{font-family:var(--mono); font-size:0.74rem; background:var(--surface); border:1px solid var(--border); border-radius:999px; padding:3px 10px; color:var(--ink)}
.chip .lab{color:var(--muted)}
button.theme{flex:none; font-family:var(--mono); font-size:0.74rem; color:var(--ink-2); background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:7px 12px; cursor:pointer}
button.theme:focus-visible,.seg button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

details.toc{margin-top:14px; background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:10px 14px}
details.toc summary{cursor:pointer; font-size:0.88rem; font-weight:600; color:var(--ink); list-style-position:inside}
details.toc summary:focus-visible{outline:2px solid var(--accent); outline-offset:2px; border-radius:4px}
details.toc ol{list-style:none; margin:10px 0 2px; padding:0; columns:2 260px; column-gap:24px}
details.toc li{break-inside:avoid; padding:3px 0}
details.toc a{color:var(--ink-2); text-decoration:none; font-size:0.86rem; display:flex; gap:8px}
details.toc a:hover{color:var(--accent)}
.toc-n{font-family:var(--mono); font-size:0.78rem; color:var(--muted); min-width:1.6em; text-align:right}
.premises{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px; margin-top:24px}
.pm{background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 14px}
.pm .kicker{margin-bottom:4px}
.pm p:last-child{margin:0; font-size:0.86rem; color:var(--ink-2); line-height:1.45}
.verdict{margin-top:44px; background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--s1); border-radius:12px; padding:20px; display:grid; gap:18px}
.kicker{font-family:var(--mono); font-size:0.7rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--accent); margin:0 0 6px}
.verdict h2{font-size:1.35rem; line-height:1.3; margin:0 0 8px; letter-spacing:-0.015em; font-weight:600}
.verdict h2 b{font-weight:750}
.verdict p{margin:0; color:var(--ink-2); max-width:72ch}
.tiles{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px}
@media (min-width:880px){.tiles{grid-template-columns:repeat(4,minmax(0,1fr))}}
.tile{background:var(--surface-2); border-radius:10px; padding:12px 14px; display:flex; flex-direction:column; gap:2px}
.t-val{font-size:1.9rem; font-weight:700; letter-spacing:-0.02em; font-variant-numeric:tabular-nums}
.t-val small{font-size:0.9rem; font-weight:600; color:var(--ink-2)}
.t-lab{font-size:0.84rem; color:var(--ink-2); line-height:1.35}

section.block{margin-top:44px}
h2.sec{font-size:1.25rem; margin:0 0 6px; letter-spacing:-0.015em; text-wrap:balance}
.s-note{color:var(--ink-2); font-size:0.95rem; margin:0 0 14px; max-width:78ch}
.reads,.tips{margin:14px 0 0; padding-left:18px; color:var(--ink-2); font-size:0.92rem; display:grid; gap:6px; max-width:80ch}
.reads b,.tips b{color:var(--ink)}
.tips li{padding-left:2px}
.foot-note{color:var(--muted); font-size:0.8rem; margin:10px 0 0; max-width:86ch}

.legend{display:flex; flex-wrap:wrap; gap:8px 18px; margin:6px 0 10px}
.lg{display:inline-flex; align-items:center; gap:7px; font-size:0.86rem; color:var(--ink-2)}
.lg svg{flex:none}
.panel{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 14px 10px; position:relative}
.panel.big{margin-bottom:14px}
.p-head{display:flex; justify-content:space-between; align-items:baseline; gap:10px; flex-wrap:wrap; margin:0 2px 4px}
.p-title{font-size:0.98rem; font-weight:700; letter-spacing:-0.01em}
.p-unit{font-family:var(--mono); font-size:0.72rem; color:var(--muted)}
.p-interp{font-size:0.84rem; color:var(--ink-2); margin:6px 2px 2px}
.gaps{font-size:0.8rem; color:var(--muted); margin:4px 2px 0}
.grid2{display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; margin-top:14px}
svg.chart{width:100%; height:auto; display:block; overflow:visible}
svg.chart text{font-family:var(--sans)}
.ax{font-size:11px; fill:var(--muted); font-family:var(--mono) !important}
.ax-t{font-size:11px; fill:var(--muted)}
.gl{stroke:var(--grid); stroke-width:1}
.bl{stroke:var(--baseline); stroke-width:1}
.dl{font-size:12px; font-weight:600; fill:var(--ink)}
.dv{font-size:11.5px; fill:var(--ink-2); font-family:var(--mono) !important}
.rowlab{font-size:12.5px; font-weight:600; fill:var(--ink)}
.miss{font-size:12px; fill:var(--muted); font-style:italic}
.ref{stroke:var(--muted); stroke-width:1; stroke-dasharray:4 4}
.reflab{font-size:10.5px; fill:var(--muted)}
.ch{stroke:var(--baseline); stroke-width:1; opacity:0; pointer-events:none}

.ctl{display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:6px 0 10px}
.ctl-lab{font-size:0.8rem; color:var(--muted)}
.seg{display:inline-flex; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:2px}
.seg button{font-family:var(--mono); font-size:0.78rem; border:0; background:transparent; color:var(--ink-2); padding:5px 11px; border-radius:6px; cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--surface-2); color:var(--ink); font-weight:700}

.explain{background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:14px}
.explain svg{width:100%; height:auto; display:block}
.ex-lab{font-size:13px; font-weight:600; fill:var(--ink)}
.ex-read{fill:var(--muted); opacity:0.55}
.ex-hit{fill:var(--accent-soft); stroke:var(--accent); stroke-width:1}
.ex-in{font-size:12px; fill:var(--ink); text-anchor:middle}
.ex-in.hit{fill:var(--accent)}
.ex-val{font-size:14px; font-weight:700; fill:var(--ink); font-family:var(--mono)}
.ex-note{font-size:11px; fill:var(--muted); text-anchor:middle}
.ex-cut{stroke:var(--ink); stroke-width:2; stroke-dasharray:3 3}
.ex-cap{font-size:0.78rem; color:var(--muted); margin:6px 0 0}
.callout{display:flex; gap:16px; align-items:center; flex-wrap:wrap; background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 18px; margin:0 0 16px}
.callout.small{margin-top:4px}
.c-big{font-size:1.7rem; font-weight:750; letter-spacing:-0.02em; font-variant-numeric:tabular-nums; white-space:nowrap}
.callout.small .c-big{font-size:1.3rem}
.c-txt{flex:1 1 320px; color:var(--ink-2); font-size:0.92rem}
.shape-key{display:flex; flex-wrap:wrap; gap:6px 18px; font-size:0.8rem; color:var(--ink-2); margin:6px 2px 2px}
.shape-key i{display:inline-block; width:11px; height:11px; margin-right:6px; vertical-align:-1px}
.k-cold{border:2px solid var(--muted); border-radius:2px}
.k-edit{border:2px solid var(--ink-2); transform:rotate(45deg) scale(0.85)}
.k-next{background:var(--ink); border-radius:50%}

.tbl-scroll{overflow-x:auto; border:1px solid var(--border); border-radius:10px; background:var(--surface)}
table{border-collapse:collapse; width:100%; font-size:0.85rem}
th,td{padding:8px 11px; text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap}
th{font-size:0.72rem; letter-spacing:0.03em; color:var(--muted); font-weight:500; border-bottom:1px solid var(--border); background:var(--surface)}
td{font-family:var(--mono); font-size:0.82rem}
td:first-child,th:first-child{text-align:left; font-family:var(--sans)}
tbody tr+tr td{border-top:1px solid var(--border)}
td .sw,.txt .sw{display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:8px; vertical-align:0}
td.best{font-weight:700; color:var(--ink)}
td .x{color:var(--muted); font-size:0.9em; margin-left:6px}
td.na{color:var(--muted); font-family:var(--sans); font-style:italic; white-space:normal; text-align:left; font-size:0.8rem; min-width:140px; max-width:200px}
td .cfg{display:block; color:var(--muted); font-size:0.85em}
td.ok{color:var(--ink)}
td.no{color:var(--muted)}
td sup{font-size:0.7em; color:var(--accent); margin-left:2px}
ol.fn{margin:8px 0 0; padding-left:22px; color:var(--muted); font-size:0.8rem; display:grid; gap:2px}
table.heat td.hc{text-align:center; font-weight:600}
table.heat th{text-align:center; white-space:normal; min-width:84px}
table.heat th:first-child{text-align:left}
.glance .p-head{flex-direction:column; gap:0}
.p-desc{font-size:0.8rem; color:var(--ink-2); line-height:1.4; margin:2px 2px 8px; min-height:4.2em}
.glance{display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:12px}
td.stk{font-weight:600}
table.txt td,table.txt th{text-align:left; white-space:normal; font-family:var(--sans); vertical-align:top}
table.txt td{font-size:0.84rem; line-height:1.4}
table.txt td:first-child{white-space:nowrap; font-weight:600}
table.txt a{color:var(--ink); text-decoration-color:var(--baseline)}
#tblAll{min-width:900px}
#tblAll .cfg{display:block; color:var(--muted); font-size:0.72rem; white-space:nowrap}

.cmds{display:grid; grid-template-columns:minmax(0,1fr); gap:12px}
.cmd{min-width:0; background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 14px}
.cmd-lab{font-size:0.8rem; font-weight:600; margin:0 0 6px}
.cmd pre{margin:0; overflow-x:auto; font-family:var(--mono); font-size:0.78rem; line-height:1.55; color:var(--ink)}
.cmd code{background:none; padding:0}
dl.method{display:grid; grid-template-columns:minmax(140px,200px) 1fr; gap:8px 18px; margin:0; font-size:0.9rem; max-width:90ch}
dl.method dt{font-weight:600}
dl.method dd{margin:0; color:var(--ink-2)}

.tip{position:fixed; pointer-events:none; opacity:0; z-index:10; background:var(--surface); color:var(--ink); border:1px solid var(--border);
  border-radius:8px; padding:8px 10px; font-size:0.78rem; box-shadow:0 6px 24px rgba(0,0,0,0.14); max-width:320px; transition:opacity .08s}
.tip .t-h{font-weight:700; margin-bottom:4px}
.tip .t-r{display:flex; gap:10px; justify-content:space-between; align-items:baseline}
.tip .t-r span:last-child{font-family:var(--mono)}
.tip .t-k{display:inline-flex; align-items:center; gap:6px}
.tip .t-k i{width:9px; height:9px; border-radius:2px; display:inline-block}
.foot{margin-top:48px; padding-top:16px; border-top:1px solid var(--border); color:var(--muted); font-size:0.8rem}
.foot a{color:var(--ink-2)}

@media (max-width:640px){
  h1{font-size:1.55rem}
  header.top{display:block; position:relative}
  header.top .eyebrow{padding-right:112px}
  button.theme{position:absolute; top:0; right:0; padding:5px 9px; font-size:0.7rem}
  dl.method{grid-template-columns:1fr; gap:2px}
  dl.method dd{margin-bottom:8px}
  .t-val{font-size:1.6rem}
}
"""

JS = r"""
const CTX = P.ctx, STACKS = P.stacks, PTS = P.points;
const NS = "http://www.w3.org/2000/svg";
const ctxLab = c => (c/1024) + "K";
const pt = (sid, c) => (PTS[sid] || {})[String(c)];
const val = (sid, c, k) => { const d = pt(sid, c); return d && d[k] != null ? d[k] : null; };
const col = s => `var(${s.cv})`;
const tip = document.getElementById("tip");
const esc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");

function fmtS(v){
  if (v == null) return "—";
  if (v < 10) return v.toFixed(1) + " s";
  if (v < 120) return v.toFixed(0) + " s";
  return (v/60).toFixed(1) + " min";
}
function fmtTok(n){ return n >= 1000 ? (n/1000).toFixed(n >= 10000 ? 0 : 1) + "K" : String(n); }
// Tick count that keeps round steps for the axis tops niceMax() returns (1, 2, 2.5, 5 × 10^k).
function tickCount(span){
  const n = span / Math.pow(10, Math.floor(Math.log10(span) + 1e-9));
  return Math.abs(n - 2) < 1e-6 ? 4 : 5;
}
function niceMax(v){
  const p = Math.pow(10, Math.floor(Math.log10(v))); const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
}
// Marker shapes give a second channel besides color (palette is below the CVD target for all pairs).
function marker(shape, x, y, r, fill, extra){
  const ring = `stroke:var(--surface);stroke-width:2;fill:${fill}`;
  const a = extra || "";
  if (shape === "square") return `<rect x="${x-r*0.9}" y="${y-r*0.9}" width="${r*1.8}" height="${r*1.8}" rx="1.5" style="${ring}" ${a}/>`;
  if (shape === "triangle") return `<path d="M${x},${y-r*1.15} L${x+r*1.05},${y+r*0.8} L${x-r*1.05},${y+r*0.8} Z" style="${ring}" ${a}/>`;
  if (shape === "diamond") return `<path d="M${x},${y-r*1.2} L${x+r*1.1},${y} L${x},${y+r*1.2} L${x-r*1.1},${y} Z" style="${ring}" ${a}/>`;
  return `<circle cx="${x}" cy="${y}" r="${r}" style="${ring}" ${a}/>`;
}
function swatch(s){ return `<svg width="26" height="12" aria-hidden="true"><line x1="1" y1="6" x2="25" y2="6" style="stroke:${col(s)};stroke-width:2"/>${marker(s.marker,13,6,4.2,col(s))}</svg>`; }

function showTip(ev, html){
  tip.innerHTML = html; tip.style.opacity = 1;
  let tx = ev.clientX + 14, ty = ev.clientY - 10;
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  if (tx + tw > window.innerWidth - 8) tx = ev.clientX - tw - 14;
  if (ty + th > window.innerHeight - 8) ty = window.innerHeight - th - 8;
  if (ty < 8) ty = 8;
  tip.style.left = tx + "px"; tip.style.top = ty + "px";
}
function hideTip(){ tip.style.opacity = 0; }
function tipRow(s, txt){ return `<div class="t-r"><span class="t-k"><i style="background:${col(s)}"></i>${esc(s.short)}</span><span>${txt}</span></div>`; }
function bindHover(el, fn){
  el.addEventListener("mousemove", fn);
  el.addEventListener("mouseleave", hideTip);
  el.addEventListener("touchstart", e => { if (e.touches[0]) fn(e.touches[0]); }, {passive:true});
  el.addEventListener("touchend", hideTip);
}
function mkSvg(W, H, label){
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("class", "chart");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", label);
  return svg;
}

function buildLegends(){
  document.querySelectorAll("[data-legend]").forEach(el => {
    el.innerHTML = STACKS.map(s => `<span class="lg">${swatch(s)}${esc(s.name)}</span>`).join("");
  });
}

// Line chart by context: one line per stack, categorical x axis, direct end labels, crosshair tooltip.
function lineChart(host, o){
  const W = o.big ? 760 : 380, H = o.big ? 330 : 236;
  const ML = 46, MR = o.big ? 92 : 70, MT = 14, MB = 30;
  const x0 = ML, x1 = W - MR, y0 = H - MB, y1 = MT;
  const ctx = o.ctx || CTX;
  const xAt = i => x0 + (x1 - x0) * (i / (ctx.length - 1));
  let vmax = o.ref ? o.ref.v : 0, vmin = Infinity;
  STACKS.forEach(s => ctx.forEach(c => { const v = val(s.id, c, o.key); if (v != null){ vmax = Math.max(vmax, v); vmin = Math.min(vmin, v); } }));
  const lo = o.min != null ? o.min : 0;
  const top = o.max != null ? o.max : niceMax(vmax * 1.06);
  // o.clip: values above the axis top sit on the top edge with their value, so one outlier does not flatten the rest.
  const yAt = v => y0 - (y0 - y1) * ((Math.min(v, top) - lo) / (top - lo));
  const svg = mkSvg(W, H, o.label);
  let g = "";
  const nt = o.ticks || tickCount(top - lo);
  for (let t = 0; t <= nt; t++){
    const v = lo + (top - lo) * t / nt, y = yAt(v);
    g += `<line x1="${x0}" x2="${x1}" y1="${y}" y2="${y}" class="${t ? "gl" : "bl"}"/>`;
    g += `<text x="${x0 - 8}" y="${y + 4}" text-anchor="end" class="ax">${o.tick ? o.tick(v) : v}</text>`;
  }
  if (o.ref){ const ry = yAt(o.ref.v); g += `<line x1="${x0}" x2="${x1}" y1="${ry}" y2="${ry}" class="ref"/><text x="${x0 + 4}" y="${ry - 5}" class="reflab">${o.ref.lab}</text>`; }
  ctx.forEach((c, i) => { g += `<text x="${xAt(i)}" y="${H - 9}" text-anchor="middle" class="ax">${ctxLab(c)}</text>`; });
  const ends = [];
  STACKS.forEach(s => {
    const pts = [];
    ctx.forEach((c, i) => { const v = val(s.id, c, o.key); if (v != null) pts.push([xAt(i), yAt(v), i, v > top ? v : null]); });
    for (let k = 1; k < pts.length; k++) if (pts[k][2] === pts[k-1][2] + 1)
      g += `<line x1="${pts[k-1][0]}" y1="${pts[k-1][1]}" x2="${pts[k][0]}" y2="${pts[k][1]}" style="stroke:${col(s)};stroke-width:2;stroke-linecap:round${pts[k][3] ? ";stroke-dasharray:4 4" : ""}"/>`;
    pts.forEach(p => {
      g += marker(s.marker, p[0], p[1], o.big ? 5 : 4.2, col(s));
      if (p[3]) g += `<text x="${p[0]}" y="${p[1] + 22}" text-anchor="middle" class="dv">↑ ${o.fmt(p[3])}</text>`;
    });
    if (pts.length){ const last = pts[pts.length - 1]; ends.push({x: last[0], y: last[1], s}); }
  });
  ends.sort((a, b) => a.y - b.y);
  for (let k = 1; k < ends.length; k++) if (ends[k].y - ends[k-1].y < 14) ends[k].y = ends[k-1].y + 14;
  ends.forEach(e => { g += `<text x="${e.x + 10}" y="${e.y + 4}" class="dl">${esc(e.s.short)}</text>`; });
  g += `<line class="ch" x1="0" x2="0" y1="${y1}" y2="${y0}"/>`;
  g += `<rect x="${x0 - 20}" y="${y1}" width="${x1 - x0 + 40}" height="${y0 - y1}" fill="transparent"/>`;
  svg.innerHTML = g;
  host.innerHTML = ""; host.appendChild(svg);
  const ch = svg.querySelector(".ch");
  bindHover(svg, ev => {
    const r = svg.getBoundingClientRect();
    const mx = (ev.clientX - r.left) / r.width * W;
    const i = Math.max(0, Math.min(ctx.length - 1, Math.round((mx - x0) / ((x1 - x0) / (ctx.length - 1)))));
    const c = ctx[i];
    ch.setAttribute("x1", xAt(i)); ch.setAttribute("x2", xAt(i)); ch.style.opacity = 1;
    let h = `<div class="t-h">${ctxLab(c)} context · ${esc(o.title)}</div>`;
    STACKS.forEach(s => {
      const d = pt(s.id, c);
      let txt = "no data";
      if (d && d.reason) txt = esc(d.reason);
      else if (d && d[o.key] != null) txt = o.fmt(d[o.key]) + (d.config ? " · " + esc(d.config) : "");
      h += tipRow(s, txt);
    });
    showTip(ev, h);
  });
  svg.addEventListener("mouseleave", () => { ch.style.opacity = 0; });
}

function gapsNote(el){
  const items = [];
  STACKS.forEach(s => CTX.forEach(c => { const d = pt(s.id, c); if (d && d.reason) items.push(`<b>${esc(s.short)} ${ctxLab(c)}</b>: ${esc(d.reason)}`); }));
  el.innerHTML = "Missing points · " + items.join(" · ");
}

// Turn-time table: best value per context in bold, the others with the ratio to the best.
function turnTable(){
  const t = document.getElementById("tblTurn");
  let h = "<thead><tr><th>Server</th>" + CTX.map(c => `<th>${ctxLab(c)}</th>`).join("") + "</tr></thead><tbody>";
  const best = {}; CTX.forEach(c => { const vs = STACKS.map(s => val(s.id, c, "turn")).filter(v => v != null); best[c] = Math.min(...vs); });
  STACKS.forEach(s => {
    h += `<tr><td class="stk"><span class="sw" style="background:${col(s)}"></span>${esc(s.name)}</td>`;
    CTX.forEach(c => {
      const d = pt(s.id, c);
      if (!d) { h += `<td class="na">—</td>`; return; }
      if (d.reason) { h += `<td class="na">${esc(d.reason.split(":")[0])}</td>`; return; }
      const r = d.turn / best[c];
      h += r < 1.005 ? `<td class="best">${d.turn.toFixed(1)} s</td>` : `<td>${d.turn.toFixed(1)} s<span class="x">${r.toFixed(2)}×</span></td>`;
    });
    h += "</tr>";
  });
  t.innerHTML = h + "</tbody>";
}

function segControl(name, options, initial, onChange){
  const el = document.querySelector(`[data-seg="${name}"]`);
  el.innerHTML = options.map(c => `<button type="button" data-v="${c}" aria-pressed="${c === initial}">${ctxLab(c)}</button>`).join("");
  el.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    el.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
    onChange(Number(b.dataset.v));
  });
  onChange(initial);
}

// Log-scale dot plot: per server, first message vs edit in the middle vs next turn, for one context size.
function waitChart(c){
  const host = document.getElementById("chWait");
  const W = 760, rowH = 54, MT = 14, MB = 34, ML = 112, MR = 30;
  const H = MT + rowH * STACKS.length + MB, x0 = ML, x1 = W - MR, y0 = H - MB;
  const lmin = Math.log10(0.5), lmax = Math.log10(1200);
  const xAt = v => x0 + (x1 - x0) * ((Math.log10(Math.max(v, 0.5)) - lmin) / (lmax - lmin));
  const svg = mkSvg(W, H, `Wait per scenario at ${ctxLab(c)} context, log scale`);
  let g = "";
  [[1, "1 s"], [10, "10 s"], [60, "1 min"], [600, "10 min"]].forEach(([v, lab]) => {
    g += `<line x1="${xAt(v)}" x2="${xAt(v)}" y1="${MT}" y2="${y0}" class="gl"/><text x="${xAt(v)}" y="${H - 12}" text-anchor="middle" class="ax">${lab}</text>`;
  });
  g += `<line x1="${x0}" x2="${x1}" y1="${y0}" y2="${y0}" class="bl"/>`;
  STACKS.forEach((s, i) => {
    const y = MT + rowH * i + rowH / 2;
    g += `<text x="0" y="${y + 4}" class="rowlab">${esc(s.short)}</text>`;
    const d = pt(s.id, c);
    if (!d || d.reason){ g += `<text x="${x0}" y="${y + 4}" class="miss">${esc(d ? d.reason : "no data")}</text>`; return; }
    const vs = [d.cold, d.edit, d.resume].filter(v => v != null);
    g += `<line x1="${xAt(Math.min(...vs))}" x2="${xAt(Math.max(...vs))}" y1="${y}" y2="${y}" style="stroke:var(--baseline);stroke-width:2"/>`;
    const hit = `data-s="${s.id}"`;
    if (d.cold != null) g += `<rect x="${xAt(d.cold) - 6}" y="${y - 6}" width="12" height="12" rx="2" style="fill:var(--surface);stroke:var(--muted);stroke-width:2" ${hit}/>`;
    if (d.edit != null) g += `<path d="M${xAt(d.edit)},${y - 7.5} L${xAt(d.edit) + 7.5},${y} L${xAt(d.edit)},${y + 7.5} L${xAt(d.edit) - 7.5},${y} Z" style="fill:var(--surface);stroke:var(--ink-2);stroke-width:2" ${hit}/>`;
    g += marker("circle", xAt(d.resume), y, 7, col(s), hit);
    g += `<text x="${xAt(d.resume)}" y="${y - 12}" text-anchor="middle" class="dv">${fmtS(d.resume)}</text>`;
    if (d.cold != null) g += `<text x="${xAt(d.cold)}" y="${y - 12}" text-anchor="middle" class="dv">${fmtS(d.cold)}</text>`;
    g += `<rect x="0" y="${y - rowH/2}" width="${W}" height="${rowH}" fill="transparent" ${hit}/>`;
  });
  svg.innerHTML = g; host.innerHTML = ""; host.appendChild(svg);
  bindHover(svg, ev => {
    const t = ev.target && ev.target.getAttribute ? ev.target.getAttribute("data-s") : null;
    if (!t){ hideTip(); return; }
    const s = STACKS.find(x => x.id === t), d = pt(t, c);
    showTip(ev, `<div class="t-h">${esc(s.name)} · ${ctxLab(c)}</div>` +
      `<div class="t-r"><span>TTFT · first message (cold)</span><span>${fmtS(d.cold)}</span></div>` +
      `<div class="t-r"><span>TTFT · edit in the middle</span><span>${fmtS(d.edit)}</span></div>` +
      `<div class="t-r"><span>TTFT · next turn (cache hit)</span><span>${fmtS(d.resume)}</span></div>` +
      `<div class="t-r"><span>Cache hit rate</span><span>${(d.reuse*100).toFixed(1)}%</span></div>`);
  });
  waitTable(c);
}
function waitTable(c){
  const t = document.getElementById("tblWait");
  let h = `<thead><tr><th>Server · ${ctxLab(c)}</th><th>Cold TTFT</th><th>TTFT · next turn</th><th>TTFT · added message</th><th>TTFT · edit in middle</th><th>Cache hit</th><th>Cold ÷ next turn</th></tr></thead><tbody>`;
  STACKS.forEach(s => {
    const d = pt(s.id, c);
    h += `<tr><td class="stk"><span class="sw" style="background:${col(s)}"></span>${esc(s.name)}</td>`;
    if (!d || d.reason){ h += `<td class="na" colspan="6">${esc(d ? d.reason : "no data")}</td></tr>`; return; }
    h += `<td>${fmtS(d.cold)}</td><td>${fmtS(d.resume)}</td><td>${fmtS(d.append)}</td><td>${fmtS(d.edit)}</td><td>${(d.reuse*100).toFixed(1)}%</td><td>${(d.cold/d.resume).toFixed(0)}×</td></tr>`;
  });
  t.innerHTML = h + "</tbody>";
}

// Horizontal bars: tokens prefilled again on the next turn, labeled with reuse and the wait it causes.
function rereadChart(c){
  const host = document.getElementById("chReread");
  const W = 760, rowH = 44, MT = 8, MB = 30, ML = 112, MR = 250;
  const H = MT + rowH * STACKS.length + MB, x0 = ML, x1 = W - MR, y0 = H - MB;
  const vs = STACKS.map(s => val(s.id, c, "reread")).filter(v => v != null);
  const top = niceMax(Math.max(...vs) * 1.02);
  const xAt = v => x0 + (x1 - x0) * v / top;
  const svg = mkSvg(W, H, `Tokens prefilled again on the next turn at ${ctxLab(c)}`);
  let g = "";
  const nt = tickCount(top);
  for (let t = 0; t <= nt; t++){ const v = top * t / nt; g += `<line x1="${xAt(v)}" x2="${xAt(v)}" y1="${MT}" y2="${y0}" class="${t ? "gl" : "bl"}"/><text x="${xAt(v)}" y="${H - 10}" text-anchor="middle" class="ax">${fmtTok(Math.round(v))}</text>`; }
  STACKS.forEach((s, i) => {
    const y = MT + rowH * i + rowH / 2;
    g += `<text x="0" y="${y + 4}" class="rowlab">${esc(s.short)}</text>`;
    const d = pt(s.id, c);
    if (!d || d.reason){ g += `<text x="${x0 + 6}" y="${y + 4}" class="miss">${esc(d ? d.reason : "no data")}</text>`; return; }
    const w = Math.max(3, xAt(d.reread) - x0);
    g += `<path d="M${x0},${y - 9} h${w - 4} a4,4 0 0 1 4,4 v10 a4,4 0 0 1 -4,4 h${-(w - 4)} Z" style="fill:${col(s)}" data-s="${s.id}"/>`;
    g += `<text x="${x0 + w + 8}" y="${y + 4}" class="dv">${fmtTok(d.reread)} tokens · ${(d.reuse*100).toFixed(1)}% cache hit · TTFT ${fmtS(d.resume)}</text>`;
    g += `<rect x="0" y="${y - rowH/2}" width="${W}" height="${rowH}" fill="transparent" data-s="${s.id}"/>`;
  });
  svg.innerHTML = g; host.innerHTML = ""; host.appendChild(svg);
  bindHover(svg, ev => {
    const t = ev.target && ev.target.getAttribute ? ev.target.getAttribute("data-s") : null;
    if (!t){ hideTip(); return; }
    const s = STACKS.find(x => x.id === t), d = pt(t, c);
    showTip(ev, `<div class="t-h">${esc(s.name)} · ${ctxLab(c)}</div>` +
      `<div class="t-r"><span>Tokens prefilled again</span><span>${d.reread.toLocaleString("en-US")}</span></div>` +
      `<div class="t-r"><span>Cache hit rate</span><span>${(d.reuse*100).toFixed(1)}%</span></div>` +
      `<div class="t-r"><span>TTFT · next turn</span><span>${fmtS(d.resume)}</span></div>`);
  });
}

// Scatter: decode speed (x) vs agent turn time (y) at one context size, one point per server.
function scatterChart(c){
  const host = document.getElementById("chScatter");
  const W = 760, H = 320, ML = 50, MR = 30, MT = 14, MB = 40;
  const x0 = ML, x1 = W - MR, y0 = H - MB, y1 = MT;
  const xs = [], ys = [];
  STACKS.forEach(s => { const d = pt(s.id, c); if (d && !d.reason){ xs.push(d.decode); ys.push(d.turn); } });
  const xlo = Math.floor((Math.min(...xs) - 8) / 10) * 10, xhi = Math.ceil((Math.max(...xs) + 6) / 10) * 10;
  const ytop = niceMax(Math.max(...ys) * 1.15);
  const xAt = v => x0 + (x1 - x0) * (v - xlo) / (xhi - xlo), yAt = v => y0 - (y0 - y1) * v / ytop;
  const svg = mkSvg(W, H, `Decode speed vs agent turn time at ${ctxLab(c)}`);
  let g = "";
  const nt = tickCount(ytop);
  for (let t = 0; t <= nt; t++){ const v = ytop * t / nt; g += `<line x1="${x0}" x2="${x1}" y1="${yAt(v)}" y2="${yAt(v)}" class="${t ? "gl" : "bl"}"/><text x="${x0 - 8}" y="${yAt(v) + 4}" text-anchor="end" class="ax">${v.toFixed(0)}</text>`; }
  for (let v = xlo; v <= xhi; v += 10) g += `<text x="${xAt(v)}" y="${y0 + 18}" text-anchor="middle" class="ax">${v}</text>`;
  g += `<text x="${(x0 + x1) / 2}" y="${H - 4}" text-anchor="middle" class="ax-t">decode speed (tokens/s) →</text>`;
  g += `<text x="${x0 + 4}" y="${y1 + 10}" class="ax-t">↑ agent turn time (s)</text>`;
  STACKS.forEach(s => {
    const d = pt(s.id, c);
    if (!d || d.reason) return;
    const x = xAt(d.decode), y = yAt(d.turn);
    g += marker(s.marker, x, y, 7, col(s), `data-s="${s.id}"`);
    const left = x > x1 - 200;
    g += `<text x="${left ? x - 12 : x + 12}" y="${y + 4}" text-anchor="${left ? "end" : "start"}" class="dl">${esc(s.short)} <tspan class="dv">${d.turn.toFixed(1)} s · ${d.decode.toFixed(0)} tok/s</tspan></text>`;
    g += `<circle cx="${x}" cy="${y}" r="16" fill="transparent" data-s="${s.id}"/>`;
  });
  const miss = STACKS.filter(s => { const d = pt(s.id, c); return !d || d.reason; }).map(s => `${s.short}: ${(pt(s.id, c) || {}).reason || "no data"}`);
  if (miss.length) g += `<text x="${x1}" y="${y1 + 10}" text-anchor="end" class="miss">${esc(miss.join(" · "))}</text>`;
  svg.innerHTML = g; host.innerHTML = ""; host.appendChild(svg);
  bindHover(svg, ev => {
    const t = ev.target && ev.target.getAttribute ? ev.target.getAttribute("data-s") : null;
    if (!t){ hideTip(); return; }
    const s = STACKS.find(x => x.id === t), d = pt(t, c);
    showTip(ev, `<div class="t-h">${esc(s.name)} · ${ctxLab(c)}</div>` +
      `<div class="t-r"><span>Agent turn time</span><span>${d.turn.toFixed(1)} s</span></div>` +
      `<div class="t-r"><span>Decode speed</span><span>${d.decode.toFixed(1)} tok/s</span></div>` +
      `<div class="t-r"><span>TTFT · next turn</span><span>${fmtS(d.resume)}</span></div>` +
      `<div class="t-r"><span>Prefill speed</span><span>${d.prefill.toFixed(0)} tok/s</span></div>`);
  });
}

function supportTable(){
  // Cells stay short: the reason or the special config goes to a numbered note under the table.
  const t = document.getElementById("tblSupport"), notes = [];
  const note = txt => { notes.push(txt); return `<sup>${notes.length}</sup>`; };
  let h = "<thead><tr><th>Server</th>" + CTX.map(c => `<th>${ctxLab(c)}</th>`).join("") + "</tr></thead><tbody>";
  STACKS.forEach(s => {
    h += `<tr><td class="stk"><span class="sw" style="background:${col(s)}"></span>${esc(s.name)}</td>`;
    CTX.forEach(c => {
      const d = pt(s.id, c);
      if (!d) h += `<td class="no">—</td>`;
      else if (d.reason){
        const [head, ...rest] = d.reason.split(": ");
        h += `<td class="no">✕ ${esc(head)}${note(`${esc(s.short)} ${ctxLab(c)}: ${esc(rest.join(": "))}.`)}</td>`;
      }
      else h += `<td class="ok">✓ ${d.turn.toFixed(1)} s${d.config ? note(`${esc(s.short)} ${ctxLab(c)}: runs with ${esc(d.config)}.`) : ""}</td>`;
    });
    h += "</tr>";
  });
  t.innerHTML = h + "</tbody>";
  document.getElementById("fnSupport").innerHTML = notes.map(n => `<li>${n}</li>`).join("");
}

// Cache hit heatmap: one row per server, one column per scenario, cell shade = share served from cache.
const HIT_SCEN = [["cold", "First message"], ["identical", "Same prompt again"], ["append", "User adds a message"],
                  ["middle_mutation", "Edit in the middle"], ["tool_turn", "Next turn (tool result)"]];
function hitTable(c){
  const t = document.getElementById("tblHits");
  let h = `<thead><tr><th>Server · ${ctxLab(c)}</th>` + HIT_SCEN.map(x => `<th>${x[1]}</th>`).join("") + "</tr></thead><tbody>";
  STACKS.forEach(s => {
    const d = pt(s.id, c);
    h += `<tr><td class="stk"><span class="sw" style="background:${col(s)}"></span>${esc(s.name)}</td>`;
    if (!d || d.reason){ h += `<td class="no" colspan="${HIT_SCEN.length}">✕ ${esc(d ? d.reason : "no data")}</td></tr>`; return; }
    h += HIT_SCEN.map(([k]) => {
      const v = d.hits[k];
      if (v === undefined) return `<td class="no">—</td>`;
      if (v === null) return `<td class="no">✕</td>`;
      const a = (0.06 + v * 0.8).toFixed(3);
      return `<td class="hc" style="background:color-mix(in srgb, var(--accent) ${(a * 100).toFixed(0)}%, transparent);${v >= 0.55 ? "color:#fff" : ""}">${(v * 100).toFixed(v === 1 || v === 0 ? 0 : 1)}%</td>`;
    }).join("") + "</tr>";
  });
  t.innerHTML = h + "</tbody>";
}

// At-a-glance panels: one small horizontal bar chart per metric, the best server's value in bold.
const GLANCE = [
  {key: "turn", title: "Agent turn time", unit: "s", better: "low", fmt: v => v.toFixed(1) + " s",
   desc: "The wait for one agent step: from sending a tool result to the end of a 512-token reply (TTFT on the next turn + 512 ÷ decode speed)."},
  {key: "resume", title: "TTFT · next turn (cache hit)", unit: "s", better: "low", fmt: v => fmtS(v),
   desc: "Time to first token when the conversation continues: the server reuses the cached prompt and prefills only the new part."},
  {key: "cold", title: "TTFT · first message (cold)", unit: "s", better: "low", fmt: v => fmtS(v),
   desc: "Time to first token for a new conversation: the server prefills the whole prompt, with nothing in the cache."},
  {key: "decode", title: "Decode speed", unit: "tokens/s", better: "high", fmt: v => v.toFixed(1),
   desc: "How fast the server writes the reply, after the first token. This is the usual “tokens per second”."},
  {key: "prefill", title: "Prefill speed", unit: "tokens/s", better: "high", fmt: v => v.toFixed(0),
   desc: "How fast the server reads a prompt it has not seen before. It sets the cold TTFT."},
  {key: "max_ctx", title: "Largest context on 128 GB", unit: "tokens · any size", better: "high", fmt: v => ctxLab(v), static: true,
   desc: "The longest prompt the stack served on this machine. It does not change with the selector."},
];
function glance(c){
  const host = document.getElementById("chGlance"); host.innerHTML = "";
  GLANCE.forEach(m => {
    const get = s => m.static ? s.max_ctx : val(s.id, c, m.key);
    const vs = STACKS.map(get).filter(v => v != null);
    const best = m.better === "low" ? Math.min(...vs) : Math.max(...vs);
    const W = 360, rowH = 30, MT = 6, ML = 78, MR = 70;
    const H = MT + rowH * STACKS.length + 4, x0 = ML, x1 = W - MR;
    const top = Math.max(...vs) * 1.02;
    const panel = document.createElement("div"); panel.className = "panel";
    panel.innerHTML = `<div class="p-head"><span class="p-title">${m.title}</span><span class="p-unit">${m.unit} · ${m.better === "low" ? "shorter is better" : "longer is better"}</span></div>` +
      `<p class="p-desc">${m.desc}</p>`;
    const svg = mkSvg(W, H, `${m.title}${m.static ? "" : " at " + ctxLab(c)}`);
    let g = "";
    STACKS.forEach((s, i) => {
      const y = MT + rowH * i + rowH / 2, v = get(s);
      g += `<text x="0" y="${y + 4}" class="rowlab">${esc(s.short)}</text>`;
      if (v == null){ const d = pt(s.id, c); g += `<text x="${x0}" y="${y + 4}" class="miss">${esc(d && d.reason ? d.reason.split(": ")[0] : "no data")}</text>`; return; }
      const w = Math.max(3, (x1 - x0) * v / top), isBest = Math.abs(v - best) < 1e-9;
      g += `<path d="M${x0},${y - 7} h${w - 4} a4,4 0 0 1 4,4 v6 a4,4 0 0 1 -4,4 h${-(w - 4)} Z" style="fill:${col(s)}" data-s="${s.id}"/>`;
      g += `<text x="${x0 + w + 6}" y="${y + 4}" class="${isBest ? "dl" : "dv"}">${m.fmt(v)}${isBest ? " ★" : ""}</text>`;
      g += `<rect x="0" y="${y - rowH / 2}" width="${W}" height="${rowH}" fill="transparent" data-s="${s.id}"/>`;
    });
    svg.innerHTML = g; panel.appendChild(svg); host.appendChild(panel);
    bindHover(svg, ev => {
      const id = ev.target && ev.target.getAttribute ? ev.target.getAttribute("data-s") : null;
      if (!id){ hideTip(); return; }
      const s = STACKS.find(x => x.id === id), v = get(s), d = pt(id, c);
      const txt = v != null ? m.fmt(v) + (d && d.config && !m.static ? " · " + esc(d.config) : "") : esc(d && d.reason ? d.reason : "no data");
      showTip(ev, `<div class="t-h">${esc(m.title)}${m.static ? "" : " · " + ctxLab(c)}</div>` + tipRow(s, txt));
    });
  });
}

// Grouped horizontal bars (share of correct answers), one group per suite.
function groupedBars(host, groups, series, o){
  const W = 760, barH = 16, gap = 2, groupGap = 22, MT = 8, MB = 30, ML = 170, MR = 120;
  const gh = series.length * (barH + gap) - gap;
  const H = MT + groups.length * (gh + groupGap) - groupGap + MB, x0 = ML, x1 = W - MR, y0 = H - MB;
  const top = o.max || niceMax(Math.max(...groups.flatMap(gr => series.map(s => o.value(gr, s) || 0))) * 1.05);
  const xAt = v => x0 + (x1 - x0) * v / top;
  const svg = mkSvg(W, H, o.label);
  let g = "";
  const nt = tickCount(top);
  for (let t = 0; t <= nt; t++){ const v = top * t / nt; g += `<line x1="${xAt(v)}" x2="${xAt(v)}" y1="${MT}" y2="${y0}" class="${t ? "gl" : "bl"}"/><text x="${xAt(v)}" y="${H - 10}" text-anchor="middle" class="ax">${o.tick(v)}</text>`; }
  groups.forEach((gr, gi) => {
    const gy = MT + gi * (gh + groupGap);
    g += `<text x="0" y="${gy + gh / 2 + 4}" class="rowlab">${esc(gr.label)}</text>`;
    series.forEach((s, si) => {
      const v = o.value(gr, s); const y = gy + si * (barH + gap);
      if (v == null) return;
      const w = Math.max(3, xAt(v) - x0);
      g += `<path d="M${x0},${y} h${w - 4} a4,4 0 0 1 4,4 v${barH - 8} a4,4 0 0 1 -4,4 h${-(w - 4)} Z" style="fill:${s.color}" data-g="${gi}" data-i="${si}"/>`;
      g += `<text x="${x0 + w + 6}" y="${y + barH - 4}" class="dv">${o.label_of(gr, s)}</text>`;
      g += `<rect x="${x0}" y="${y}" width="${x1 - x0}" height="${barH}" fill="transparent" data-g="${gi}" data-i="${si}"/>`;
    });
  });
  svg.innerHTML = g; host.innerHTML = ""; host.appendChild(svg);
  bindHover(svg, ev => {
    const gi = ev.target && ev.target.getAttribute ? ev.target.getAttribute("data-g") : null;
    if (gi == null){ hideTip(); return; }
    const gr = groups[+gi];
    showTip(ev, `<div class="t-h">${esc(gr.label)}</div>` + series.map(s =>
      `<div class="t-r"><span class="t-k"><i style="background:${s.color}"></i>${esc(s.name)}</span><span>${o.label_of(gr, s)}</span></div>`).join(""));
  });
  const leg = document.createElement("div"); leg.className = "legend";
  leg.innerHTML = series.map(s => `<span class="lg"><svg width="14" height="12" aria-hidden="true"><rect x="1" y="1" width="12" height="10" rx="2" style="fill:${s.color}"/></svg>${esc(s.name)}</span>`).join("");
  host.prepend(leg);
}

function qualityChart(){
  const rows = Object.fromEntries(P.quality.map(r => [r.id, r]));
  const series = P.quality.map(r => { const s = STACKS.find(x => x.id === r.id); return {id: r.id, name: s.name, color: col(s)}; });
  const groups = P.quality_suites.map(([key, label]) => ({key, label}));
  groupedBars(document.getElementById("chQuality"), groups, series, {
    max: 100, label: "Share of correct answers per test and server", tick: v => v.toFixed(0) + "%",
    value: (gr, s) => { const q = rows[s.id][gr.key]; return 100 * q[0] / q[1]; },
    label_of: (gr, s) => { const q = rows[s.id][gr.key]; return `${q[0]}/${q[1]} · ${(100*q[0]/q[1]).toFixed(0)}%`; },
  });
}

function swiftChart(){
  const series = [{id: "n2", name: "Qwen3.8-Flash-Next (ddalcu iQ-MLX 4.7 bpw)", color: "var(--s1)"},
                  {id: "w1", name: "Swift 1.5 (same runtime and flags)", color: "var(--s5)"}];
  groupedBars(document.getElementById("chSwift"), P.swift, series, {
    label: "Median time to the final answer per suite", tick: v => v.toFixed(0) + " s",
    value: (gr, s) => gr[s.id].median,
    label_of: (gr, s) => `${gr[s.id].median.toFixed(1)} s · ${gr[s.id].passed}/${gr[s.id].n} correct`,
  });
}

function allTable(){
  const t = document.getElementById("tblAll");
  const cols = [["turn", "Agent turn", v => v.toFixed(1)], ["resume", "TTFT next turn", v => v.toFixed(2)],
    ["append", "TTFT added msg", v => v.toFixed(2)], ["cold", "Cold TTFT", v => v.toFixed(1)],
    ["edit", "TTFT edit", v => v.toFixed(1)], ["reuse", "Cache hit", v => (v*100).toFixed(1) + "%"],
    ["decode", "Decode", v => v.toFixed(1)], ["prefill", "Prefill", v => v.toFixed(0)],
    ["wired", "Peak memory", v => v.toFixed(1)], ["swap", "Swap", v => v.toFixed(1)], ["reps", "Runs", v => String(v)]];
  let h = "<thead><tr><th>Server</th><th>Context</th>" + cols.map(c => `<th>${c[1]}</th>`).join("") + "</tr></thead><tbody>";
  STACKS.forEach(s => CTX.forEach(c => {
    const d = pt(s.id, c); if (!d) return;
    h += `<tr><td class="stk"><span class="sw" style="background:${col(s)}"></span>${esc(s.short)}</td><td>${ctxLab(c)}${d.config ? `<span class="cfg">${esc(d.config)}</span>` : ""}</td>`;
    if (d.reason){ h += `<td class="na" colspan="${cols.length}">${esc(d.reason)}</td></tr>`; return; }
    h += cols.map(cl => d[cl[0]] == null ? `<td class="na">—</td>` : `<td>${cl[2](d[cl[0]])}</td>`).join("") + "</tr>";
  }));
  t.innerHTML = h + "</tbody>";
}

function buildFoot(){
  document.getElementById("foot").innerHTML =
    `Data: <code>bench/engine-updates-2026-10/results/reports-2026-10.json</code> and ` +
    `<code>bench/swift15-flashnext-2026-10/results/page-data.json</code>, generated at <code>${esc(P.generated_at)}</code>. ` +
    `Page: <code>render_m4max_guide.py</code>. Detailed pages: ` +
    `<a href="qwen38-flashnext-overview.html">campaign dashboard</a> · ` +
    `<a href="qwen38-flashnext-perf-lines.html">four runtimes from 8K to 512K</a> · ` +
    `<a href="qwen38-flashnext-swift15.html">Swift 1.5 A/B</a> · ` +
    `<a href="https://github.com/snagnever/macstudio-local-llm" target="_blank" rel="noopener">repository</a>.`;
}

// Table of contents from the section headings, in page order; the conclusion block has no number.
function buildToc(){
  const items = [...document.querySelectorAll("section.block[id] > h2.sec, #conclusion")].map(el => {
    const sec = el.closest("section");
    const label = sec.id === "conclusion" ? "Conclusion" : el.textContent.replace(/^\d+ · /, "");
    const num = sec.id === "conclusion" ? "→" : (el.textContent.match(/^(\d+) · /) || [, ""])[1];
    return `<li><a href="#${sec.id}"><span class="toc-n">${num}</span>${esc(label)}</a></li>`;
  });
  document.getElementById("tocList").innerHTML = items.join("");
}

function build(){
  buildToc();
  buildLegends();
  segControl("glance", [32768, 131072, 262144, 524288], 131072, glance);
  lineChart(document.getElementById("chTurn"), {key: "turn", title: "agent turn time", label: "Agent turn time by context size",
    big: true, max: 32, ticks: 4, fmt: v => v.toFixed(1) + " s", tick: v => v.toFixed(0) + " s"});
  gapsNote(document.getElementById("gapsTurn"));
  turnTable();
  segControl("wait", [32768, 131072, 262144, 524288], 131072, waitChart);
  segControl("reread", [131072, 262144, 524288], 131072, rereadChart);
  lineChart(document.getElementById("chResume"), {key: "resume", title: "TTFT on the next turn", label: "TTFT on the next turn by context",
    max: 10, fmt: v => fmtS(v), tick: v => v.toFixed(0)});
  lineChart(document.getElementById("chReuse"), {key: "reuse", title: "cache hit rate", label: "Cache hit rate on the next turn by context",
    ctx: [32768, 131072, 262144, 524288], min: 0.9, max: 1, fmt: v => (v*100).toFixed(1) + "%", tick: v => (v*100).toFixed(0) + "%"});
  segControl("hits", [8192, 32768, 131072, 262144, 524288], 131072, hitTable);
  segControl("scatter", [32768, 131072, 262144], 131072, scatterChart);
  lineChart(document.getElementById("chDecode"), {key: "decode", title: "decode speed", label: "Decode speed by context",
    fmt: v => v.toFixed(1) + " tok/s", tick: v => v.toFixed(0)});
  lineChart(document.getElementById("chPrefill"), {key: "prefill", title: "prefill speed", label: "Prefill speed by context",
    fmt: v => v.toFixed(0) + " tok/s", tick: v => v.toFixed(0)});
  supportTable();
  lineChart(document.getElementById("chMem"), {key: "wired", title: "peak memory", label: "Peak memory locked by the server by context",
    big: true, max: 128, ticks: 4, ref: {v: 128, lab: "128 GB total"}, fmt: v => v.toFixed(1) + " GB", tick: v => v.toFixed(0)});
  qualityChart(); swiftChart(); allTable(); buildFoot();
}
build();

document.addEventListener("click", e => {
  const a = e.target.closest('a[href^="#"]'); if (!a) return;
  const el = document.getElementById(a.getAttribute("href").slice(1)); if (!el) return;
  e.preventDefault(); el.scrollIntoView({behavior: "smooth", block: "start"});
  try { history.replaceState(null, "", a.getAttribute("href")); } catch (err) {}
});

const btn = document.getElementById("themeBtn");
function applyLabel(){ btn.textContent = "theme: " + (document.documentElement.getAttribute("data-theme") || "auto"); }
btn.addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur == null ? "light" : cur === "light" ? "dark" : null;
  if (next) document.documentElement.setAttribute("data-theme", next); else document.documentElement.removeAttribute("data-theme");
  try { next ? localStorage.setItem("theme", next) : localStorage.removeItem("theme"); } catch (e) {}
  applyLabel();
});
try { const saved = localStorage.getItem("theme"); if (saved) document.documentElement.setAttribute("data-theme", saved); } catch (e) {}
applyLabel();
"""


# The page's light palette (validated with the dataviz checks), fixed per stack.
CARD_COLORS = {"n2": "#2a78d6", "o1": "#eb6834", "m1": "#1baf7a", "d1": "#eda100"}
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


def render_card(data: dict, swift: dict) -> str:
    """A 1200x630 static card: the agent turn at 128K per stack and the three headline numbers."""
    f = facts(data, swift)
    p = {k: point(g) for k, g in canonical(data).items() if not g["refused"]}
    turns = [(s, p[(s["id"], 131072)]["turn"]) for s in STACKS]
    top = max(t for _, t in turns)
    bars = ""
    for i, (s, t) in enumerate(turns):
        y = 40 + i * 54
        w = 440 * t / top
        bars += (f'<text x="0" y="{y + 20}" class="lab">{s["short"]}</text>'
                 f'<rect x="130" y="{y}" width="{w:.0f}" height="30" rx="5" fill="{CARD_COLORS[s["id"]]}"/>'
                 f'<text x="{130 + w + 12:.0f}" y="{y + 21}" class="val">{t:.1f} s{" ★" if i == 0 else ""}</text>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Card</title>
<style>
html,body{{margin:0; width:1200px; height:630px; background:#fbfaf7; color:#15171b;
  font-family:-apple-system,"SF Pro Text","Inter",Helvetica,Arial,sans-serif}}
.card{{position:relative; width:1200px; height:630px; padding:56px 64px; box-sizing:border-box}}
.eyebrow{{font-family:"SF Mono",Menlo,monospace; font-size:17px; letter-spacing:0.14em; text-transform:uppercase; color:#6b7280; margin:0 0 14px}}
h1{{font-size:50px; line-height:1.1; letter-spacing:-0.025em; margin:0; max-width:1060px}}
.sub{{font-size:23px; color:#444a55; margin:16px 0 0}}
.row{{display:flex; gap:48px; margin-top:38px; align-items:flex-start}}
svg{{flex:none}}
.lab{{font-size:19px; font-weight:600; fill:#15171b}}
.val{{font-family:"SF Mono",Menlo,monospace; font-size:19px; fill:#15171b}}
.axis{{font-size:16px; fill:#6b7280}}
.tiles{{display:grid; grid-template-columns:1fr 1fr; gap:14px; flex:1}}
.tile{{background:#f0eee8; border-radius:12px; padding:14px 18px}}
.t-val{{font-size:40px; font-weight:700; letter-spacing:-0.02em; display:block}}
.t-val small{{font-size:19px; font-weight:600; color:#444a55}}
.t-lab{{font-size:16px; color:#444a55; line-height:1.3}}
</style></head><body><div class="card">
<p class="eyebrow">Benchmark · Apple M4 Max 128 GB · October 2026</p>
<h1>Qwen3.8-Flash-Next on an M4 Max: four local servers, 8K to 512K context</h1>
<p class="sub">Cache hit and the next turn matter more than tokens per second.</p>
<div class="row">
  <svg width="700" height="270" viewBox="0 0 700 270"><text x="0" y="18" class="axis">Agent turn time at 128K · seconds · shorter is better</text>{bars}</svg>
  <div class="tiles">
    <div class="tile"><span class="t-val">{f["mlx_turn_512"]}<small> s</small></span><span class="t-lab">per agent turn at 512K on mlx-serve</span></div>
    <div class="tile"><span class="t-val">{f["mlx_resume_512"]}<small> s</small></span><span class="t-lab">to start the next reply at 512K, from the cache</span></div>
    <div class="tile"><span class="t-val">{f["mlx_cold_512_min"]}<small> min</small></span><span class="t-lab">first message at 512K, nothing cached</span></div>
    <div class="tile"><span class="t-val">{f["mlx_wired_max"]}<small> GB</small></span><span class="t-lab">peak memory at 512K, no swap</span></div>
  </div>
</div>
</div></body></html>
"""


def _marker(shape: str, x: float, y: float, color: str, r: float = 5) -> str:
    ring = f'stroke="#fcfcfb" stroke-width="2"'
    if shape == "square":
        return f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" fill="{color}" {ring}/>'
    if shape == "triangle":
        return (f'<polygon points="{x:.1f},{y - r - 1:.1f} {x + r + 1:.1f},{y + r:.1f} {x - r - 1:.1f},{y + r:.1f}" '
                f'fill="{color}" {ring}/>')
    if shape == "diamond":
        return (f'<polygon points="{x:.1f},{y - r - 1:.1f} {x + r + 1:.1f},{y:.1f} {x:.1f},{y + r + 1:.1f} '
                f'{x - r - 1:.1f},{y:.1f}" fill="{color}" {ring}/>')
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" {ring}/>'


def _nice_ticks(top: float, n: int = 4) -> list[float]:
    import math
    raw = top / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    return [i * step for i in range(int(math.ceil(top / step)) + 1)]


def _line_panel(points: dict, key: str, title: str, unit: str, fmt, w: int = 620, h: int = 340,
                clip: float | None = None, ticks: list[float] | None = None) -> str:
    """One static line chart: a series per stack over the context sizes, with end labels."""
    left, right, top, bottom = 58, 165, 54, 40
    x0, x1, y0, y1 = left, w - right, top, h - bottom
    vals = [points[(s["id"], c)][key] for s in STACKS for c in CTX if (s["id"], c) in points]
    vmax = max(vals)
    ymax = clip if clip and vmax > clip else vmax
    ticks = ticks or _nice_ticks(ymax)
    ymax = ticks[-1]
    xs = {c: x0 + i * (x1 - x0) / (len(CTX) - 1) for i, c in enumerate(CTX)}
    ys = lambda v: y1 - (min(v, ymax) / ymax) * (y1 - y0)
    out = [f'<text x="0" y="22" font-size="19" font-weight="700" fill="{INK}">{title}</text>',
           f'<text x="0" y="42" font-size="14" fill="{MUTED}" font-family="Menlo,monospace">{unit}</text>']
    for t in ticks:
        y = ys(t)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{GRID if t else BASE}"/>')
        out.append(f'<text x="{x0 - 8}" y="{y + 4:.1f}" font-size="13" text-anchor="end" fill="{MUTED}" '
                   f'font-family="Menlo,monospace">{t:g}</text>')
    for c in CTX:
        out.append(f'<text x="{xs[c]:.1f}" y="{y1 + 22}" font-size="13" text-anchor="middle" fill="{MUTED}" '
                   f'font-family="Menlo,monospace">{c // 1024}K</text>')
    labels = []
    for s in STACKS:
        pts = [(c, points[(s["id"], c)][key]) for c in CTX if (s["id"], c) in points]
        color = CARD_COLORS[s["id"]]
        coords = [(xs[c], ys(v)) for c, v in pts]
        for (xa, ya), (xb, yb), (_, vb) in zip(coords, coords[1:], pts[1:]):
            dash = ' stroke-dasharray="5 4"' if clip and vb > clip else ""
            out.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{color}" '
                       f'stroke-width="2.5"{dash}/>')
        for (x, y) in coords:
            out.append(_marker(s["marker"], x, y, color))
        cl, vl = pts[-1]
        txt = f"{s['short']} {('↑ ' if clip and vl > clip else '')}{fmt(vl)}"
        labels.append([ys(vl), xs[cl] + 12, txt, color])
    # Push end labels apart so they stay readable.
    labels.sort(key=lambda l: l[0])
    for i in range(1, len(labels)):
        if labels[i][0] - labels[i - 1][0] < 18:
            labels[i][0] = labels[i - 1][0] + 18
    for y, x, txt, color in labels:
        out.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="14" font-weight="600" fill="{INK}">{txt}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="-apple-system,Helvetica,Arial,sans-serif">{"".join(out)}</svg>'


def render_post(data: dict, swift: dict) -> str:
    """The Reddit post image: headline numbers, four line charts and the 512K cache-miss bars."""
    f = facts(data, swift)
    p = {k: point(g) for k, g in canonical(data).items() if not g["refused"]}
    legend = "".join(
        f'<span class="lg"><svg width="26" height="14">{_marker(s["marker"], 13, 7, CARD_COLORS[s["id"]], 5)}'
        f'<line x1="0" y1="7" x2="26" y2="7" stroke="{CARD_COLORS[s["id"]]}" stroke-width="2.5"/>'
        f'{_marker(s["marker"], 13, 7, CARD_COLORS[s["id"]], 5)}</svg>{s["name"]}</span>' for s in STACKS)
    panels = "".join(f'<div class="panel">{svg}</div>' for svg in (
        _line_panel(p, "turn", "Agent turn time", "seconds · TTFT on the next turn + a 512-token reply · shorter is better",
                    lambda v: f"{v:.1f} s", clip=32),
        _line_panel(p, "resume", "Time to first token on the next turn (cache hit)", "seconds · shorter is better",
                    lambda v: f"{v:.1f} s", clip=10),
        _line_panel(p, "decode", "Decode speed", "tokens/s · higher is better", lambda v: f"{v:.0f} tok/s"),
        _line_panel(p, "wired", "Peak memory locked by the server", "GB of 128 GB · no server used swap",
                    lambda v: f"{v:.0f} GB", ticks=[0, 32, 64, 96, 128]),
    ))
    # The 512K cache-miss bars: only the stacks that serve 512K.
    rows = [(s, p[(s["id"], 524288)]) for s in STACKS if (s["id"], 524288) in p]
    top = max(d["reread"] for _, d in rows)
    bars = ""
    for i, (s, d) in enumerate(rows):
        y, w = 14 + i * 50, 240 * d["reread"] / top
        bars += (f'<text x="0" y="{y + 20}" font-size="16" font-weight="600" fill="{INK}">{s["short"]}</text>'
                 f'<rect x="110" y="{y}" width="{max(w, 4):.0f}" height="30" rx="4" fill="{CARD_COLORS[s["id"]]}"/>'
                 f'<text x="{110 + max(w, 4) + 12:.0f}" y="{y + 21}" font-size="14" fill="{INK}" font-family="Menlo,monospace">'
                 f'{_k(d["reread"])} tokens prefilled again · {d["reuse"] * 100:.1f}% hit · next reply in {d["resume"]:.1f} s</text>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Post image</title>
<style>
html,body{{margin:0; width:{POST_W}px; height:{POST_H}px; background:#fbfaf7; color:{INK};
  font-family:-apple-system,"SF Pro Text","Inter",Helvetica,Arial,sans-serif}}
.wrap{{width:{POST_W}px; height:{POST_H}px; padding:52px 60px; box-sizing:border-box; display:flex; flex-direction:column; gap:22px}}
.eyebrow{{font-family:"SF Mono",Menlo,monospace; font-size:16px; letter-spacing:0.14em; text-transform:uppercase; color:{MUTED}; margin:0 0 10px}}
h1{{font-size:44px; line-height:1.1; letter-spacing:-0.025em; margin:0}}
.sub{{font-size:22px; color:{INK2}; margin:12px 0 0}}
.tiles{{display:grid; grid-template-columns:repeat(4,1fr); gap:14px}}
.tile{{background:#f0eee8; border-radius:12px; padding:14px 18px}}
.t-val{{font-size:38px; font-weight:700; letter-spacing:-0.02em; display:block; line-height:1.1}}
.t-val small{{font-size:18px; font-weight:600; color:{INK2}}}
.t-lab{{font-size:15px; color:{INK2}; line-height:1.3}}
.legend{{display:flex; gap:28px; font-size:16px; color:{INK2}}}
.lg{{display:inline-flex; align-items:center; gap:8px}}
.grid{{display:grid; grid-template-columns:1fr 1fr; gap:18px}}
.panel{{background:#fcfcfb; border:1px solid rgba(11,11,11,0.10); border-radius:12px; padding:14px 16px 8px}}
.panel svg{{display:block}}
.wide{{display:flex; gap:28px; align-items:center}}
.callout{{flex:none; width:300px}}
.c-big{{font-size:36px; font-weight:700; letter-spacing:-0.02em; display:block}}
.c-txt{{font-size:15px; color:{INK2}; line-height:1.35}}
.foot{{margin-top:auto; font-size:15px; color:{MUTED}; display:flex; justify-content:space-between}}
</style></head><body><div class="wrap">
<div>
  <p class="eyebrow">Benchmark · Apple M4 Max 128 GB · October 2026</p>
  <h1>Qwen3.8-Flash-Next on an M4 Max: four local servers, 8K to 512K context</h1>
  <p class="sub">What you wait for in an agent session: the next turn and the cache hit matter more than tokens per second.</p>
</div>
<div class="tiles">
  <div class="tile"><span class="t-val">{f["mlx_turn_128"]}<small> s</small></span><span class="t-lab">per agent turn at 128K on mlx-serve</span></div>
  <div class="tile"><span class="t-val">{f["mlx_turn_512"]}<small> s</small></span><span class="t-lab">per agent turn at 512K on mlx-serve</span></div>
  <div class="tile"><span class="t-val">{f["mlx_cold_512_min"]}<small> min</small> → {f["mlx_resume_512"]}<small> s</small></span><span class="t-lab">first message vs next reply at 512K, from the cache</span></div>
  <div class="tile"><span class="t-val">{f["mlx_wired_max"]}<small> GB</small></span><span class="t-lab">peak memory at 512K, no swap</span></div>
</div>
<div class="legend">{legend}</div>
<div class="grid">{panels}</div>
<div class="panel wide">
  <div class="callout"><span class="c-big">1% ≈ {f["sec_per_pct_512"]} s</span><span class="c-txt">At 512K, each 1% of cache miss is about
  {f["pct_tokens_512"]} tokens prefilled again, or about {f["sec_per_pct_512"]} s of extra wait. oMLX stops at 256K and MTPLX at 128K.</span></div>
  <svg width="940" height="{14 + len(rows) * 50}" font-family="-apple-system,Helvetica,Arial,sans-serif">{bars}</svg>
</div>
<p class="foot"><span>mlx-serve 26.10.1 · oMLX 0.7.0 · MTPLX 2.12.2 · ds4 (antirez) · each on its author's pack, 4.7 to 5.97 bpw</span>
<span>snagnever.github.io/macstudio-local-llm/qwen38-flashnext-m4max-guide.html</span></p>
</div></body></html>
"""


def write_png(page: Path, png: Path, size: tuple[int, int] = (1200, 630), scale: int = 1) -> bool:
    """Render a static page with headless Chrome. Returns False when Chrome is not installed."""
    import subprocess
    if not CHROME.is_file():
        return False
    subprocess.run([str(CHROME), "--headless=new", "--hide-scrollbars", f"--window-size={size[0]},{size[1]}",
                    f"--force-device-scale-factor={scale}", f"--screenshot={png}", page.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(REPORTS_JSON))
    ap.add_argument("--swift", default=str(SWIFT_JSON))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--card", default=str(CARD_HTML), help="the link-preview card HTML")
    ap.add_argument("--post", default=str(POST_HTML), help="the Reddit post image HTML")
    ap.add_argument("--png", action="store_true", help="also render the card and post PNGs with headless Chrome")
    a = ap.parse_args(argv)
    data = json.loads(Path(a.data).read_text(encoding="utf-8"))
    swift = json.loads(Path(a.swift).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.write_text(render(data, swift), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    card = Path(a.card)
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(render_card(data, swift), encoding="utf-8")
    print(f"wrote {card}")
    post = Path(a.post)
    post.write_text(render_post(data, swift), encoding="utf-8")
    print(f"wrote {post}")
    if a.png:
        for page, size, scale in ((card, (1200, 630), 1), (post, (POST_W, POST_H), 2)):
            png = page.with_suffix(".png")
            if write_png(page, png, size, scale):
                print(f"wrote {png} ({png.stat().st_size} bytes)")
            else:
                print(f"Chrome not found at {CHROME}; the PNG was not rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
