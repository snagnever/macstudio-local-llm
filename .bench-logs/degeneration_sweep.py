"""Degeneration sampling sweep for DeepSeek-V4-Flash-2bit-DQ.

Tests whether the repetition/looping degeneration on long-form generation can be
*mitigated* by sampling knobs mlx-lm actually supports — focusing on the two we
NEVER tested before: XTC (xtc_probability/xtc_threshold) and presence_penalty.

Two-level success criteria (this is the whole point):
  LOOP-BROKEN  = generation terminates (finish=stop) with no repetition tail.
  QUALITY      = the non-looping text is *coherent* (a separate judgment — a
                 broken loop that emits different garbage is NOT a win). We capture
                 every full generation to JSONL so coherence can be read/graded.

Key mechanics (verified in mlx_lm source on this rig):
  - All knobs are per-REQUEST body params, so no server restarts between configs.
  - make_sampler SHORT-CIRCUITS to argmax when temperature==0 -> top_p/min_p/XTC/
    top_k are ALL bypassed. => XTC only does anything at temp>0. Penalties
    (repetition/presence/frequency) are logits_processors applied BEFORE the
    sampler, so they apply even at temp==0.
  - Sampler order is hard-coded: penalties -> top_p -> min_p -> XTC -> top_k ->
    categorical(temp). We can't reorder; note the default min_p->XTC is the
    community-recommended order already.
  - Server protects EOS + "\n" via xtc_special_tokens, so XTC won't suppress
    termination. xtc_threshold must be in [0, 0.5].

Usage:
  python degeneration_sweep.py screen    # fast triage: 1 prompt, few seeds, all configs
  python degeneration_sweep.py confirm    # survivors over all prompts x more seeds
Env overrides: BASE, MODEL, MAXTOK, SEEDS, OUT.
"""
import json, os, sys, time, urllib.request
from collections import Counter

BASE = os.environ.get("BASE", "http://127.0.0.1:8765/v1")
MODEL = os.environ.get(
    "MODEL", "/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
)
MAXTOK = int(os.environ.get("MAXTOK", "1500"))
CHAT_KWARGS = json.loads(os.environ["CHAT_KWARGS"]) if os.environ.get("CHAT_KWARGS") else None

# Prompts chosen to provoke long-form open-ended generation (where the loop appears).
PROMPTS = {
    # the known reliable trigger from the earlier sweep (short prompt -> long ramble)
    "exec_pt": "você executa código",
    # open-ended long-form English (story) — invites rambling
    "story_en": "Write a detailed 800-word short story about a lighthouse keeper "
                "who discovers a message in a bottle. Include vivid description.",
    # enumerated list — structurally invites repetition
    "list_en": "List and briefly explain 50 distinct, non-overlapping tips for "
               "improving focus while working from home. Number each one.",
    # --- normal, well-posed prompts: must stay COHERENT under any mitigation
    #     sampler (a knob that fixes loops but wrecks good answers is a bad rec) ---
    "qa_fact": "In two sentences, what is the capital of France and why is it significant?",
    "qa_explain": "Explain in 3-4 sentences how a hash map achieves average O(1) lookup.",
}
NORMAL_PROMPTS = {"qa_fact", "qa_explain"}  # judged on coherence, not loop%

# Config groups. screen runs ALL; confirm runs only the survivors you set below.
CONFIGS = [
    # --- controls (reproduce prior results) ---
    ("ctrl_greedy_t0",        {"temperature": 0.0}),
    ("ctrl_t0.6",             {"temperature": 0.6}),
    # --- XTC: the big untested knob (needs temp>0) ---
    ("xtc_p0.5_th0.1",        {"temperature": 0.6, "xtc_probability": 0.5, "xtc_threshold": 0.1}),
    ("xtc_p0.5_th0.1_minp",   {"temperature": 0.6, "min_p": 0.02, "xtc_probability": 0.5, "xtc_threshold": 0.1}),
    ("xtc_p1.0_th0.1_minp",   {"temperature": 0.6, "min_p": 0.02, "xtc_probability": 1.0, "xtc_threshold": 0.1}),
    ("xtc_p0.5_th0.2_minp",   {"temperature": 0.6, "min_p": 0.02, "xtc_probability": 0.5, "xtc_threshold": 0.2}),
    # --- presence_penalty: untested (works at temp 0 AND temp>0) ---
    ("presence0.5",           {"temperature": 0.6, "presence_penalty": 0.5}),
    ("presence1.0",           {"temperature": 0.6, "presence_penalty": 1.0}),
    ("presence1.5",           {"temperature": 0.6, "presence_penalty": 1.5}),
    ("presence1.0_t0",        {"temperature": 0.0, "presence_penalty": 1.0}),
    # --- frequency_penalty higher (lightly tested before) ---
    ("frequency1.0",          {"temperature": 0.6, "frequency_penalty": 1.0}),
    ("frequency1.5_t0",       {"temperature": 0.0, "frequency_penalty": 1.5}),
    # --- reproduce the suspected NEGATIVE (rep penalty made it worse) ---
    ("rep1.3_ctx64",          {"temperature": 0.6, "repetition_penalty": 1.3, "repetition_context_size": 64}),
    # --- combos: kitchen-sink anti-loop ---
    ("combo_xtc_presence",    {"temperature": 0.7, "min_p": 0.02, "xtc_probability": 0.5, "xtc_threshold": 0.1, "presence_penalty": 1.0}),
    ("combo_xtc_freq",        {"temperature": 0.7, "min_p": 0.02, "xtc_probability": 0.5, "xtc_threshold": 0.1, "frequency_penalty": 0.8}),
    # --- ablations around the winner (combo_xtc_presence) to find the minimal recipe ---
    ("abl_noxtc",             {"temperature": 0.7, "min_p": 0.02, "presence_penalty": 1.0}),                                              # is XTC necessary?
    ("abl_nominp",            {"temperature": 0.7, "xtc_probability": 0.5, "xtc_threshold": 0.1, "presence_penalty": 1.0}),               # is min_p necessary?
    ("abl_presence0.5",       {"temperature": 0.7, "min_p": 0.02, "xtc_probability": 0.5, "xtc_threshold": 0.1, "presence_penalty": 0.5}),# weaker presence
    ("abl_temp0.6",           {"temperature": 0.6, "min_p": 0.02, "xtc_probability": 0.5, "xtc_threshold": 0.1, "presence_penalty": 1.0}),# temp sensitivity
    ("abl_xtc_th0.05",        {"temperature": 0.7, "min_p": 0.02, "xtc_probability": 0.5, "xtc_threshold": 0.05, "presence_penalty": 1.0}),# gentler XTC threshold
    ("abl_presence_only",     {"temperature": 0.7, "presence_penalty": 1.0}),                                                            # presence alone at temp0.7
]

# Edit after the screen phase: the config names that survived, for `confirm`.
SURVIVORS = os.environ.get("SURVIVORS", "").split(",") if os.environ.get("SURVIVORS") else []

DEFAULT_SEEDS = [0, 1, 2, 3, 4]


def degenerate(text, finish_reason):
    """Heuristic loop detector. Conservative: flags clear repetition or non-termination."""
    if finish_reason == "length":
        return True, "hit max_tokens (no EOS)"
    w = text.split()
    if len(w) < 30:
        return False, ""
    tail = w[-60:]
    c = Counter(tail)
    if c.most_common(1)[0][1] >= 15:
        return True, f"tail token x{c.most_common(1)[0][1]}"
    if len(set(tail)) <= 0.25 * len(tail):
        return True, f"tail distinct {len(set(tail))}/{len(tail)}"
    # consecutive 3-gram loop anywhere
    for n in range(len(w) - 12):
        g = tuple(w[n:n + 3])
        reps = 0
        k = n
        while k + 3 <= len(w) and tuple(w[k:k + 3]) == g:
            reps += 1
            k += 3
        if reps >= 5:
            return True, f"3-gram x{reps}: {' '.join(g)!r}"
    return False, ""


def distinct_ratio(text):
    w = text.split()
    return round(len(set(w)) / len(w), 3) if w else 0.0


def call(params, prompt, seed):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAXTOK, "stream": False}
    body.update(params)
    if CHAT_KWARGS:
        body["chat_template_kwargs"] = CHAT_KWARGS
    if params.get("temperature", 0.0) > 0 and seed is not None:
        body["seed"] = seed
    req = urllib.request.Request(f"{BASE}/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read())
    dt = time.time() - t0
    ch = d["choices"][0]
    content = ch["message"].get("content") or ""
    fr = ch.get("finish_reason")
    ct = d["usage"]["completion_tokens"]
    return content, fr, ct, dt


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "screen"
    seeds = [int(s) for s in os.environ["SEEDS"].split(",")] if os.environ.get("SEEDS") else \
        ([0, 1, 2] if phase == "screen" else DEFAULT_SEEDS)
    prompts = {"exec_pt": PROMPTS["exec_pt"]} if phase == "screen" else PROMPTS
    configs = CONFIGS if phase == "screen" else [c for c in CONFIGS if c[0] in SURVIVORS] or CONFIGS
    only = os.environ["ONLY"].split(",") if os.environ.get("ONLY") else None
    if only:
        configs = [c for c in CONFIGS if c[0] in only]
    if os.environ.get("PROMPTS_ONLY"):
        keep = os.environ["PROMPTS_ONLY"].split(",")
        prompts = {k: PROMPTS[k] for k in keep if k in PROMPTS}

    out = os.environ.get("OUT", f".bench-logs/degeneration-{phase}.jsonl")
    print(f"# phase={phase} configs={len(configs)} prompts={list(prompts)} seeds={seeds}", flush=True)
    print(f"# writing full generations to {out}\n", flush=True)
    print(f"{'config':22s} {'prompt':9s} loop%  clean/total  meanTok  meanTok/s", flush=True)

    fout = open(out, "w")
    for name, params in configs:
        for pkey, prompt in prompts.items():
            use_seeds = [None] if params.get("temperature", 0.0) == 0 else seeds
            results = []
            for sd in use_seeds:
                try:
                    content, fr, ct, dt = call(params, prompt, sd)
                    deg, why = degenerate(content, fr)
                    rec = {"config": name, "params": params, "prompt": pkey, "seed": sd,
                           "finish": fr, "tokens": ct, "secs": round(dt, 1),
                           "tok_s": round(ct / dt, 1) if dt else 0,
                           "distinct": distinct_ratio(content),
                           "degenerate": deg, "why": why, "content": content}
                    results.append(rec)
                    fout.write(json.dumps(rec) + "\n"); fout.flush()
                except Exception as e:
                    rec = {"config": name, "prompt": pkey, "seed": sd, "error": f"{type(e).__name__}: {e}"}
                    fout.write(json.dumps(rec) + "\n"); fout.flush()
                    print(f"  [ERROR] {name} {pkey} seed={sd}: {e}", flush=True)
            ok = [r for r in results if "error" not in r]
            if not ok:
                continue
            n_deg = sum(r["degenerate"] for r in ok)
            loop_pct = round(100 * n_deg / len(ok))
            mt = round(sum(r["tokens"] for r in ok) / len(ok))
            mts = round(sum(r["tok_s"] for r in ok) / len(ok), 1)
            clean = len(ok) - n_deg
            print(f"{name:22s} {pkey:9s} {loop_pct:4d}%  {clean:2d}/{len(ok):<2d}        {mt:5d}    {mts:6.1f}", flush=True)
        print("", flush=True)
    fout.close()
    print(f"\n# done. Read full text per config: jq -r 'select(.config==\"NAME\")|.content' {out}", flush=True)


if __name__ == "__main__":
    main()
