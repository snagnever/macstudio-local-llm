#!/usr/bin/env python3
"""Sonda de instruction-following no estilo IFEval: 20 prompts com instruções verificáveis por código.

Mede, por caso, se todas as instruções passaram (strict) e o tempo e os tokens da resposta. Não reproduz o
IFBench do card do Swift 1.5; é uma checagem de sanidade para o A/B n2 × w1."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


def split_reasoning(message: dict) -> tuple[str, str]:
    """(content, reasoning): mesma regra do bench2.split_reasoning."""
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    if "</think>" in content:
        head, _, tail = content.partition("</think>")
        reasoning += head.replace("<think>", "", 1)
        content = tail.lstrip()
    return content, reasoning


def _words(t: str) -> list[str]:
    return re.findall(r"\b\w+\b", t)


def _json_payload(t: str):
    t = t.strip()
    fence = re.match(r"^```(?:json)?\s*\n(.*)\n```$", t, re.S)
    try:
        return json.loads(fence.group(1) if fence else t)
    except (json.JSONDecodeError, TypeError):
        return None


def _json_keys(t: str, keys: list[str]) -> bool:
    d = _json_payload(t)
    return isinstance(d, dict) and all(k in d for k in keys)


def _json_array_len(t: str, n: int) -> bool:
    d = _json_payload(t)
    return isinstance(d, list) and len(d) == n


CHECKERS = {
    "all_lowercase": lambda t: t == t.lower() and any(c.isalpha() for c in t),
    "all_uppercase": lambda t: t == t.upper() and any(c.isalpha() for c in t),
    "no_commas": lambda t: "," not in t,
    "word_count_max": lambda t, n: len(_words(t)) < n,
    "word_count_min": lambda t, n: len(_words(t)) >= n,
    "bullet_count": lambda t, n: len(re.findall(r"^\s*[-*]\s+\S", t, re.M)) == n,
    "json_keys": _json_keys,
    "json_array_len": _json_array_len,
    "ends_with": lambda t, s: t.strip().endswith(s),
    "starts_with": lambda t, s: t.strip().startswith(s),
    "includes": lambda t, ws: all(w.lower() in t.lower() for w in ws),
    "excludes": lambda t, ws: not any(re.search(rf"\b{re.escape(w)}\b", t, re.I) for w in ws),
    "paragraphs_by_divider": lambda t, n: len([p for p in re.split(r"\n\s*\*\*\*\s*\n", t.strip()) if p.strip()]) == n,
    "has_title": lambda t: re.search(r"<<[^<>\n]+>>", t) is not None,
    "placeholder_min": lambda t, n: len(re.findall(r"\[[^\[\]\n]+\]", t)) >= n,
    "wrapped_in_quotes": lambda t: len(t.strip()) > 1 and t.strip()[0] == '"' and t.strip()[-1] == '"',
    "section_count": lambda t, n: len(re.findall(r"\bSECTION\s+\d+", t)) == n,
    "has_postscript": lambda t, s: re.search(rf"^\s*{re.escape(s)}", t, re.M) is not None,
}

CASES = [
    {"id": "if01", "prompt": "Write a haiku about rain. Use only lowercase letters.", "checks": [("all_lowercase",)]},
    {"id": "if02", "prompt": "Describe the water cycle in fewer than 50 words.", "checks": [("word_count_max", 50)]},
    {"id": "if03", "prompt": "List exactly 4 benefits of unit tests as a markdown bullet list, and nothing else.",
     "checks": [("bullet_count", 4)]},
    {"id": "if04", "prompt": "Explain what a hash map is without using any commas.", "checks": [("no_commas",)]},
    {"id": "if05", "prompt": "Return a JSON object with the keys \"name\" and \"age\" for a fictional person. "
                             "Output only the JSON.", "checks": [("json_keys", ["name", "age"])]},
    {"id": "if06", "prompt": "Write a short product description for a desk lamp. End your response with the exact "
                             "phrase \"Is there anything else I can help with?\"",
     "checks": [("ends_with", "Is there anything else I can help with?")]},
    {"id": "if07", "prompt": "Write one motivational sentence in ALL CAPITAL LETTERS.", "checks": [("all_uppercase",)]},
    {"id": "if08", "prompt": "Write a two-paragraph story about a cat. Separate the paragraphs with the markdown "
                             "divider ***.", "checks": [("paragraphs_by_divider", 2)]},
    {"id": "if09", "prompt": "Write a short poem about the sea. Give it a title wrapped in double angular brackets, "
                             "like <<title>>.", "checks": [("has_title",)]},
    {"id": "if10", "prompt": "Write a cover letter template with at least 3 placeholders in square brackets, such as "
                             "[name].", "checks": [("placeholder_min", 3)]},
    {"id": "if11", "prompt": "Explain recursion to a beginner in at least 120 words.", "checks": [("word_count_min", 120)]},
    {"id": "if12", "prompt": "Write a tweet about coffee that includes the keywords \"sunrise\" and \"ritual\".",
     "checks": [("includes", ["sunrise", "ritual"])]},
    {"id": "if13", "prompt": "Describe a forest without using the words \"tree\" or \"green\".",
     "checks": [("excludes", ["tree", "trees", "green"])]},
    {"id": "if14", "prompt": "Wrap your entire response in double quotation marks. Tell me one fact about Mars.",
     "checks": [("wrapped_in_quotes",)]},
    {"id": "if15", "prompt": "Write a weekend plan with exactly 3 sections. Mark the start of each section with "
                             "\"SECTION X\", where X is the section number.", "checks": [("section_count", 3)]},
    {"id": "if16", "prompt": "Start your answer with the word \"Absolutely\" and explain in two sentences why sleep "
                             "matters.", "checks": [("starts_with", "Absolutely")]},
    {"id": "if17", "prompt": "Name the three primary colors. Use only lowercase letters and no commas.",
     "checks": [("all_lowercase",), ("no_commas",)]},
    {"id": "if18", "prompt": "Write a limerick about a programmer. After it, add a postscript that starts with "
                             "\"P.S.\"", "checks": [("has_postscript", "P.S.")]},
    {"id": "if19", "prompt": "Summarize the plot of Romeo and Juliet in fewer than 40 words, and include the "
                             "keyword \"feud\".", "checks": [("word_count_max", 40), ("includes", ["feud"])]},
    {"id": "if20", "prompt": "Output a JSON array of exactly 5 prime numbers and nothing else.",
     "checks": [("json_array_len", 5)]},
]


def grade(case: dict, content: str) -> dict[str, bool]:
    return {name: bool(CHECKERS[name](content, *args)) for name, *args in case["checks"]}


def case_passed(checks: dict[str, bool], finish_reason: str | None, content: str) -> bool:
    """Todas as instruções certas numa resposta completa. Vazia, truncada ou com erro não conta: uma resposta
    vazia passaria em word_count_max, no_commas e excludes."""
    return all(checks.values()) and finish_reason not in ("length", "error") and bool(content.strip())


def build_body(model: str, prompt: str, effort: str | None, max_tokens: int, temperature: float,
               sampling: dict) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens, **sampling}
    if effort:
        body["reasoning_effort"] = effort
    return body


def select_cases(only: str | None) -> list[dict]:
    if not only:
        return CASES
    wanted = {x.strip() for x in only.split(",")}
    unknown = wanted - {c["id"] for c in CASES}
    if unknown:
        raise SystemExit(f"if_probe: casos desconhecidos: {sorted(unknown)}")
    return [c for c in CASES if c["id"] in wanted]


def chat(base_url: str, body: dict, timeout: int) -> dict:
    req = Request(f"{base_url}/chat/completions", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    elapsed = time.time() - t0
    choice = data["choices"][0]
    content, reasoning = split_reasoning(choice["message"])
    return {"content": content, "reasoning_chars": len(reasoning), "finish_reason": choice.get("finish_reason"),
            "completion_tokens": data.get("usage", {}).get("completion_tokens"), "elapsed_s": round(elapsed, 2)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--reasoning-effort", default="xhigh")
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--min-p", type=float, default=None)
    ap.add_argument("--presence-penalty", type=float, default=None)
    ap.add_argument("--repetition-penalty", type=float, default=None)
    ap.add_argument("--only", default=None, help="ids separados por vírgula (ex.: if07)")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    sampling = {k: v for k, v in {"top_p": a.top_p, "top_k": a.top_k, "min_p": a.min_p,
                                  "presence_penalty": a.presence_penalty,
                                  "repetition_penalty": a.repetition_penalty}.items() if v is not None}
    cases = select_cases(a.only)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    passed = total = 0
    with out.open("w", encoding="utf-8") as f:
        for rep in range(1, a.repeat + 1):
            for case in cases:
                body = build_body(a.model, case["prompt"], a.reasoning_effort, a.max_tokens, a.temperature, sampling)
                try:
                    r = chat(a.base_url, body, a.timeout)
                    checks = grade(case, r["content"])
                    err = None
                except OSError as e:  # URLError e timeouts: o caso conta como erro, a sonda segue
                    r = {"content": "", "reasoning_chars": 0, "finish_reason": "error", "completion_tokens": None,
                         "elapsed_s": None}
                    checks = {name: False for name, *_ in case["checks"]}
                    err = str(e)
                ok = case_passed(checks, r["finish_reason"], r["content"])
                passed += ok
                total += 1
                rec = {"arm": a.arm, "id": case["id"], "rep": rep, "passed": ok, "checks": checks, "error": err,
                       "reasoning_effort": a.reasoning_effort, "temperature": a.temperature, "sampling": sampling,
                       "content_preview": r["content"][:300],
                       **{k: r[k] for k in ("elapsed_s", "completion_tokens", "reasoning_chars", "finish_reason")}}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"{case['id']} r{rep}: {'PASS' if ok else 'FAIL'} {checks} {r['elapsed_s']}s", flush=True)
    print(f"strict {passed}/{total} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
