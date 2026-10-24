#!/usr/bin/env python3
"""Long-context quality probe: 8 questions over one haystack of synthetic log lines.

The haystack plants 16 ledger records ("ledger: <ACCOUNT> moved <n> units to <ACCOUNT>") at even depths from 5%
to 95%. The questions are 3 direct lookups, 3 sums over one account's records and 2 two-hop chains. Every
question shares the same prefix, so only the first one pays the cold prefill. Answers are integers or account
names and are scored exactly. One JSON line per question, then one "verdict" line with the accuracy.

    python3 longctx_probe.py --base-url http://127.0.0.1:8585/v1 --model ID --context 524288 --output out.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CHARS_PER_TOKEN = 3.6
OUTPUT_ROOM = 8192
FILL = 0.9
ACCOUNTS = ("ORION", "VEGA", "LYRA", "ALTAIR", "DENEB", "RIGEL", "SIRIUS", "CAPELLA", "POLLUX", "CASTOR",
            "SPICA", "ANTARES", "ARCTURUS", "BETELGEUSE", "ALDEBARAN", "REGULUS", "FOMALHAUT", "MIRA",
            "ACHERNAR", "CANOPUS", "PROCYON", "HADAR", "MIMOSA", "ATRIA", "SHAULA", "ELNATH", "MIRFAK",
            "ALNITAK", "BELLATRIX", "SAIPH", "MINTAKA", "ALHENA")
RECORD_RE = re.compile(r"ledger: ([A-Z]+) moved (\d+) units to ([A-Z]+)")
INSTRUCTION = ("\n\nAnswer from the ledger records in the log above. "
               "End your reply with one line of the form 'ANSWER: <value>'.")
SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 20}


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def parse_records(text: str) -> list[tuple[str, int, str]]:
    return [(a, int(n), b) for a, n, b in RECORD_RE.findall(text)]


def _records_and_questions(rng: random.Random) -> tuple[list[tuple[str, int, str]], list[dict]]:
    names = rng.sample(ACCOUNTS, 22)
    amount = lambda: rng.randint(100, 9999)
    records, questions = [], []
    for i in range(3):  # lookups: one record each, a unique (source, target) pair
        a, b, n = names[2 * i], names[2 * i + 1], amount()
        records.append((a, n, b))
        questions.append({"kind": "lookup", "answer": n,
                          "question": f"How many units did account {a} move to account {b}?"})
    for i in range(3):  # sums: two records from the same source
        a = names[6 + i]
        ns = [amount(), amount()]
        records += [(a, ns[0], names[9 + i]), (a, ns[1], names[12 + i])]
        questions.append({"kind": "sum", "account": a, "answer": sum(ns),
                          "question": f"What is the total number of units account {a} moved, over all its records?"})
    for i in range(2):  # two hops: x sends once to y, y sends once onward
        x, y, z = names[15 + 3 * i], names[16 + 3 * i], names[17 + 3 * i]
        m = amount()
        records += [(x, amount(), y), (y, m, z)]
        questions.append({"kind": "hop", "answer": m,
                          "question": f"Account {x} moved units to exactly one account. "
                                      f"How many units did that account move onward?"})
    for _ in range(3):  # distractors between targets only, so no question's source gains a record
        b1, b2 = rng.sample(names[9:15], 2)
        records.append((b1, amount(), b2))
    rng.shuffle(records)
    for i, q in enumerate(questions):
        q["id"] = f"q{i + 1:02d}"
    return records, questions


def build_case(context: int, seed: int = 0, fill: float = FILL) -> tuple[str, list[dict]]:
    rng = random.Random(seed)
    records, questions = _records_and_questions(rng)
    target_tokens = min(int(fill * context), context - OUTPUT_ROOM - 512)
    target_chars = int(target_tokens * CHARS_PER_TOKEN)
    header = "Service log of the billing cluster. Ledger records are mixed with routine lines.\n\n"
    depths = [0.05 + 0.9 * i / (len(records) - 1) for i in range(len(records))]
    lines, size, placed, t = [], len(header), 0, 0
    while size < target_chars:
        if placed < len(records) and size >= depths[placed] * target_chars:
            a, n, b = records[placed]
            line = f"[t+{t:07d}] ledger: {a} moved {n} units to {b}\n"
            placed += 1
        else:
            line = (f"[t+{t:07d}] svc-{rng.randint(1, 64):02d} heartbeat ok latency={rng.randint(2, 900)}ms "
                    f"queue={rng.randint(0, 4000)} region={rng.choice(('eu', 'us', 'ap', 'sa'))}\n")
        lines.append(line)
        size += len(line)
        t += 1
    while placed < len(records):  # a tiny context can end before the last depth
        a, n, b = records[placed]
        lines.append(f"[t+{t:07d}] ledger: {a} moved {n} units to {b}\n")
        placed += 1
        t += 1
    return header + "".join(lines), questions


def score(text: str, answer: int | str) -> bool:
    tail = text.rsplit("ANSWER:", 1)[1] if "ANSWER:" in text else text
    if isinstance(answer, int):
        nums = re.findall(r"\d[\d,]*", tail)
        return bool(nums) and int(nums[-1].replace(",", "")) == answer
    return re.search(rf"\b{re.escape(answer)}\b", tail, re.IGNORECASE) is not None


def _chat(base_url: str, payload: dict, timeout: int) -> dict:
    req = Request(f"{base_url.rstrip('/')}/chat/completions", data=json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--context", type=int, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--arm", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--reasoning-effort", default="xhigh")
    ap.add_argument("--timeout", type=int, default=7200)
    args = ap.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    fill = FILL
    prefix, questions = build_case(args.context, args.seed, fill)
    results = []
    with args.output.open("a", encoding="utf-8") as out:
        for q in questions:
            payload = {"model": args.model, "max_tokens": args.max_tokens, "reasoning_effort": args.reasoning_effort,
                       "messages": [{"role": "user", "content": prefix + q["question"] + INSTRUCTION}], **SAMPLING}
            started = time.perf_counter()
            body, error = {}, None
            for _ in range(3):  # the 3.6 chars/token estimate can overshoot: shrink 10% on a context refusal
                try:
                    body = _chat(args.base_url, payload, args.timeout)
                    break
                except HTTPError as e:
                    error = f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}"
                    if e.code != 400 or q is not questions[0]:
                        break
                    fill *= 0.9
                    prefix, questions = build_case(args.context, args.seed, fill)
                    q = questions[0]
                    payload["messages"][0]["content"] = prefix + q["question"] + INSTRUCTION
                except Exception as e:  # noqa: BLE001 - the record keeps the error
                    error = f"{type(e).__name__}: {e}"
                    break
            msg = ((body.get("choices") or [{}])[0].get("message") or {}) if body else {}
            content = msg.get("content") or ""
            usage = body.get("usage") or {}
            ok = bool(body) and score(content, q["answer"])
            rec = {"record_type": "longctx", "arm": args.arm, "context": args.context, "seed": args.seed,
                   "fill": round(fill, 4), "id": q["id"], "kind": q["kind"], "answer": q["answer"], "correct": ok,
                   "prompt_tokens": usage.get("prompt_tokens"),
                   "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                   "completion_tokens": usage.get("completion_tokens"),
                   "finish_reason": ((body.get("choices") or [{}])[0].get("finish_reason")) if body else None,
                   "elapsed_s": round(time.perf_counter() - started, 2), "content_tail": content[-300:],
                   "error": error if not body else None}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            results.append(rec)
        acc = sum(r["correct"] for r in results) / len(results)
        out.write(json.dumps({"record_type": "verdict", "arm": args.arm, "context": args.context, "seed": args.seed,
                              "accuracy": round(acc, 3), "n": len(results),
                              "by_kind": {k: sum(r["correct"] for r in results if r["kind"] == k)
                                          for k in ("lookup", "sum", "hop")},
                              "prompt_tokens": results[0]["prompt_tokens"], "fill": round(fill, 4)}) + "\n")
    print(f"longctx {args.arm} @{args.context}: accuracy {acc:.2f} ({sum(r['correct'] for r in results)}/{len(results)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
