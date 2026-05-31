"""Judge long-form degeneration outputs for COHERENCE with a separate model, so
non-XTC failures (repetition loops) and XTC failures (high-distinct word-salad) are
scored on ONE fair scale. Reads the saved generations; for each, asks the judge to
rate 1-5 + classify the failure mode. failure = score <= 2.

Run AFTER stopping the DeepSeek server and starting a judge server on JUDGE_BASE.
Env: IN (jsonl of generations), JUDGE_BASE, JUDGE_MODEL.
"""
import json, os, re, urllib.request
from collections import defaultdict

IN = os.environ.get("IN", ".bench-logs/degeneration-rates-longform.jsonl")
JUDGE_BASE = os.environ.get("JUDGE_BASE", "http://127.0.0.1:8766/v1")
JUDGE_MODEL = os.environ["JUDGE_MODEL"]
OUT = os.environ.get("JUDGE_OUT", ".bench-logs/longform-coherence-scores.jsonl")

PROMPTS = {
    "story_en": "Write a detailed 800-word short story about a lighthouse keeper who discovers a message in a bottle.",
    "list_en": "List and briefly explain 50 distinct tips for improving focus while working from home.",
}

RUBRIC = (
    "You are a strict evaluator of AI text quality. An assistant was given a PROMPT and produced a "
    "RESPONSE (its first ~1800 and last ~1800 characters are shown, joined by [...]).\n\n"
    "Rate the RESPONSE's COHERENCE on this scale:\n"
    "5 = fully coherent, on-task, readable throughout.\n"
    "4 = coherent and on-task; may be simply cut off at the end by a length limit (that is NOT a failure).\n"
    "3 = starts coherent then partially degrades.\n"
    "2 = largely degenerate: stuck repeating words/phrases, OR incoherent word-salad, with only some signal.\n"
    "1 = fully degenerate: locked in token/phrase repetition, or incoherent word-salad.\n\n"
    "Also classify the dominant failure mode: coherent | truncated_ok | repetition_loop | word_salad | off_task.\n"
    "A response that is coherent but merely cut off at the token limit is 'truncated_ok', NOT a failure.\n\n"
    'Respond with ONLY one line of JSON: {"score": <1-5 int>, "mode": "<one of the labels>"}'
)


def judge(prompt_text, response):
    head = response[:1800]
    tail = response[-1800:] if len(response) > 3600 else ""
    shown = head + ("\n[...]\n" + tail if tail else "")
    body = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": f"PROMPT:\n{prompt_text}\n\nRESPONSE:\n{shown}"},
        ],
        "max_tokens": 600, "temperature": 0.0, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(f"{JUDGE_BASE}/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    txt = msg.get("content") or msg.get("reasoning_content") or ""
    m = re.search(r'\{[^}]*"score"[^}]*\}', txt, re.DOTALL)
    if not m:
        return None, None, txt[:80]
    try:
        d = json.loads(m.group(0))
        return int(d["score"]), d.get("mode", "?"), ""
    except Exception:
        return None, None, txt[:80]


def main():
    recs = [json.loads(l) for l in open(IN) if '"error"' not in l]
    fout = open(OUT, "w")
    by = defaultdict(list)
    print(f"# judging {len(recs)} generations with {JUDGE_MODEL}\n")
    for d in recs:
        ptext = PROMPTS.get(d["prompt"], d["prompt"])
        score, mode, err = judge(ptext, d["content"] or "")
        rec = {"config": d["config"], "prompt": d["prompt"], "seed": d["seed"],
               "score": score, "mode": mode, "distinct": d["distinct"], "tokens": d["tokens"]}
        fout.write(json.dumps(rec) + "\n"); fout.flush()
        if score is None:
            print(f"  [parse-fail] {d['config']}/{d['prompt']} s{d['seed']}: {err}")
            continue
        by[(d["config"], d["prompt"])].append((score, mode))
    fout.close()

    print(f"\n{'config':20s} {'prompt':9s}  mean  fail(<=2)/n   modes")
    print("-" * 78)
    for k in sorted(by):
        sc = by[k]
        mean = sum(s for s, _ in sc) / len(sc)
        fails = sum(1 for s, _ in sc if s <= 2)
        modes = ",".join(sorted({m for _, m in sc}))
        print(f"{k[0]:20s} {k[1]:9s}  {mean:4.1f}  {fails:2d}/{len(sc):<2d}        {modes}")
    print(f"\n# per-generation scores -> {OUT}")


if __name__ == "__main__":
    main()
