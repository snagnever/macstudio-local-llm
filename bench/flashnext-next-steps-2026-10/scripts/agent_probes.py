#!/usr/bin/env python3
"""Agentic regression probes 3a, 3b, 3c and 3e of research/qwen38-flashnext-next-steps-20261012.md.

Each subcommand talks to a server that is already up (run it through ``run-arm.sh <arm> <ctx> --exec``,
which exports BASE_URL and MODEL_ID) and appends one JSON record per request to ``--output``.

  contradiction  3a: one session of N turns; each turn is a user task, a fabricated tool call, a known tool
                 result (an ``ls`` listing or a pytest run) and the model's answer. A turn fails when the
                 answer is empty, misses the fact in the tool result, or names a file/test that the tool
                 result does not contain (invented). The answer and its reasoning are re-sent in the next
                 turn (preserve_thinking, the card default). Also the "fixed multi-turn task" of 3d.
  charcount      3b: 20 prompts "about N characters" (pt, en, ko). Loop = finish_reason length with empty
                 content.
  longsession    3c: one session that grows with ~8K-token tool results until the prompt passes the largest
                 target (default 200000 tokens). Flags any run of 20+ identical characters ("!!!!"), the
                 degeneration heuristic of bench/degeneration, empty answers and missed anomaly codes.
  effortswitch   3e: at a fixed context, prime with xhigh, then the same appended turn with xhigh (control),
                 with another effort (switch) and with xhigh again (back). Records TTFT and cache hit.
  summary        print markdown tables of the JSONL files given.
  loops          print the loop rate of degeneration_sweep.py outputs (results/loops/*.jsonl), per file and prompt.

Sampling is the vendor thinking profile (temperature 1.0, top_p 0.95, top_k 20, presence_penalty 0) and
``reasoning_effort`` is always sent. ``--dry-run`` prints the first request of a subcommand and exits.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "bench" / "qwen3.8-prefix-cache" / "scripts"))
sys.path.insert(0, str(REPO / "bench" / "degeneration" / "scripts"))

SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0}
EFFORTS = ("xhigh", "medium", "low")  # the only values the chat template accepts
TOOLS = [
    {"type": "function", "function": {"name": "ls", "description": "List a directory.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                                                     "required": ["path"]}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run the test suite with pytest.",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                                                     "required": ["path"]}}},
    {"type": "function", "function": {"name": "read_log", "description": "Read one chunk of the service log.",
                                      "parameters": {"type": "object", "properties": {"chunk": {"type": "integer"}},
                                                     "required": ["chunk"]}}},
]
SYSTEM = "You are a careful coding agent. Base every statement on the tool results you were given."
STEMS = ["parser", "cache", "router", "schema", "billing", "auth", "ledger", "export", "sync", "queue",
         "render", "retry", "tokens", "limits", "audit", "probe", "planner", "metrics", "loader", "index"]
DECOYS = ["main.py", "utils.py", "config.py", "helpers.py", "app.py", "__init__.py", "settings.py", "models.py"]
CHAR_RUN = re.compile(r"(\S)\1{19,}")
PY_NAME = re.compile(r"\b[\w-]+\.py\b")
TEST_NAME = re.compile(r"\btest_(?!suite_)[a-z0-9_]+\b")  # test_suite_NN is the file name, not a test


# ---------- HTTP ----------

def chat(base_url: str, body: dict, timeout: int) -> tuple[dict, float]:
    req = urllib.request.Request(f"{base_url.rstrip('/')}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data, time.perf_counter() - t0


def split_message(message: dict) -> tuple[str, str]:
    """Return (content, reasoning) whatever field the server used for the thinking."""
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    if "</think>" in content:
        head, _, tail = content.partition("</think>")
        reasoning = reasoning or head.replace("<think>", "")
        content = tail
    return content.strip(), reasoning


def body(model: str, messages: list[dict], effort: str, max_tokens: int, tools: bool = False) -> dict:
    b = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False,
         "reasoning_effort": effort, **SAMPLING}
    if tools:
        b["tools"] = TOOLS
    return b


# ---------- 3a: contradiction after a tool result ----------

def make_turn(i: int, seed: int) -> dict:
    """Turn i of the 3a session: an ls listing (even i) or a pytest run (odd i), with what the answer must
    contain and the names the tool result does contain."""
    rnd = random.Random(seed * 1000 + i)
    if i % 2 == 0:
        py = sorted(f"{s}_{rnd.randint(10, 99)}.py" for s in rnd.sample(STEMS, 4))
        other = sorted(rnd.sample(["README.md", "pyproject.toml", "Makefile", "data.csv", "notes.txt"], 2))
        listing = "\n".join(sorted(py + other))
        return {"kind": "ls", "call": {"name": "ls", "arguments": json.dumps({"path": f"src/pkg{i:02d}"})},
                "result": listing, "expected": py, "known": set(py),
                "question": f"Turn {i}: list the Python files in src/pkg{i:02d}. Answer with the file names only, "
                            "comma-separated. Do not call more tools."}
    names = [f"test_{s}_{rnd.randint(1, 9)}" for s in rnd.sample(STEMS, 5)]
    failing = names[rnd.randrange(5)]
    lines = [f"tests/test_suite_{i:02d}.py::{n} {'FAILED' if n == failing else 'PASSED'}" for n in names]
    lines += ["", f"FAILED tests/test_suite_{i:02d}.py::{failing} - AssertionError: expected 3, got 4",
              "========================= 1 failed, 4 passed in 0.42s ========================="]
    return {"kind": "pytest", "call": {"name": "run_tests", "arguments": json.dumps({"path": f"tests/test_suite_{i:02d}.py"})},
            "result": "\n".join(lines), "expected": [failing], "known": set(names),
            "question": f"Turn {i}: which test failed in tests/test_suite_{i:02d}.py? Answer with the test function "
                        "name only. Do not call more tools."}


def judge_turn(turn: dict, content: str, finish: str | None, tool_calls) -> tuple[str, list[str]]:
    """ok | empty | length | tool_call | invented | missing, plus the invented names."""
    if finish == "length":
        return "length", []
    if not content:
        return ("tool_call" if tool_calls else "empty"), []
    found = set(PY_NAME.findall(content)) if turn["kind"] == "ls" else set(TEST_NAME.findall(content))
    invented = sorted(n for n in found if n not in turn["known"])
    if turn["kind"] == "pytest" and re.search(r"\ball (\d+ )?tests? (passed|pass)\b|\bno tests? failed\b", content, re.I):
        invented.append("<all tests passed>")
    if invented:
        return "invented", invented
    if not all(e in content for e in turn["expected"]):
        return "missing", []
    return "ok", []


def cmd_contradiction(a) -> int:
    rc = 0
    for rnd_i in range(1, a.rounds + 1):
        messages = [{"role": "system", "content": f"{SYSTEM} Session {a.arm}-{rnd_i}-{a.reasoning_effort}."}]
        started = time.perf_counter()
        for i in range(1, a.turns + 1):
            turn = make_turn(i, rnd_i)
            call_id = f"call_{rnd_i}_{i}"
            messages += [{"role": "user", "content": turn["question"]},
                         {"role": "assistant", "content": "",
                          "tool_calls": [{"id": call_id, "type": "function", "function": turn["call"]}]},
                         {"role": "tool", "tool_call_id": call_id, "content": turn["result"]}]
            if a.dry_run:
                print(json.dumps(body(a.model or "MODEL", messages, a.reasoning_effort, a.max_tokens, True))[:2000])
                return 0
            rec = {"probe": "3a", "arm": a.arm, "round": rnd_i, "turn": i, "kind": turn["kind"],
                   "reasoning_effort": a.reasoning_effort, **SAMPLING}
            try:
                data, secs = chat(a.base_url, body(a.model, messages, a.reasoning_effort, a.max_tokens, True), a.timeout)
                choice = data["choices"][0]
                msg = choice.get("message") or {}
                content, reasoning = split_message(msg)
                verdict, invented = judge_turn(turn, content, choice.get("finish_reason"), msg.get("tool_calls"))
                reasoning_invented = sorted(
                    n for n in (PY_NAME.findall(reasoning) if turn["kind"] == "ls" else TEST_NAME.findall(reasoning))
                    if n not in turn["known"] and n not in DECOYS)
                rec.update(verdict=verdict, invented=invented, reasoning_invented=reasoning_invented, secs=round(secs, 2),
                           finish_reason=choice.get("finish_reason"), content=content[:400],
                           reasoning_chars=len(reasoning), usage=data.get("usage"))
                assistant = {"role": "assistant", "content": content}
                if reasoning and a.preserve_thinking:
                    assistant["reasoning_content"] = reasoning
                messages.append(assistant)
            except Exception as error:
                rec.update(verdict="error", error=f"{type(error).__name__}: {error}"[:300])
                rc = 3
            write(a.output, rec)
            if rec["verdict"] == "error":
                break
        write(a.output, {"probe": "3a", "arm": a.arm, "round": rnd_i, "turn": 0, "kind": "session",
                         "reasoning_effort": a.reasoning_effort, "session_secs": round(time.perf_counter() - started, 1)})
    return rc


# ---------- 3b: character-count loop ----------

TOPICS = {"en": ["a lighthouse at night", "a used bicycle for sale", "a rainy market street", "a quiet library",
                 "an old wooden boat", "a mountain trail", "a small bakery"],
          "pt": ["um farol à noite", "uma bicicleta usada à venda", "uma feira num dia de chuva",
                 "uma biblioteca silenciosa", "um barco de madeira antigo", "uma trilha na serra", "uma padaria pequena"],
          "ko": ["밤의 등대", "중고 자전거 판매", "비 오는 시장 거리", "조용한 도서관", "오래된 나무 배", "산길"]}
TEMPLATES = {"en": "Write a description of {t} in about {n} characters. Reply with the text only.",
             "pt": "Escreva uma descrição de {t} com cerca de {n} caracteres. Responda só com o texto.",
             "ko": "{t}에 대한 설명을 약 {n}자로 써 주세요. 텍스트만 답하세요."}
SIZES = [80, 120, 160, 200, 280, 350, 500]


def charcount_prompts() -> list[dict]:
    out = []
    for lang in ("en", "pt", "ko"):
        for k, topic in enumerate(TOPICS[lang]):
            n = SIZES[k % len(SIZES)]
            out.append({"id": f"{lang}{k + 1:02d}", "lang": lang, "target": n,
                        "prompt": TEMPLATES[lang].format(t=topic, n=n)})
    return out  # 7 + 7 + 6 = 20


def cmd_charcount(a) -> int:
    prompts = charcount_prompts()
    rc = 0
    for rnd_i in range(1, a.rounds + 1):
        for p in prompts:
            msgs = [{"role": "user", "content": p["prompt"]}]
            if a.dry_run:
                print(json.dumps(body(a.model or "MODEL", msgs, a.reasoning_effort, a.max_tokens)))
                return 0
            rec = {"probe": "3b", "arm": a.arm, "round": rnd_i, "id": p["id"], "lang": p["lang"],
                   "target_chars": p["target"], "reasoning_effort": a.reasoning_effort, **SAMPLING}
            try:
                data, secs = chat(a.base_url, body(a.model, msgs, a.reasoning_effort, a.max_tokens), a.timeout)
                choice = data["choices"][0]
                content, reasoning = split_message(choice.get("message") or {})
                fin = choice.get("finish_reason")
                rec.update(finish_reason=fin, content_chars=len(content), reasoning_chars=len(reasoning),
                           completion_tokens=(data.get("usage") or {}).get("completion_tokens"), secs=round(secs, 2),
                           loop=fin == "length" and not content, content=content[:300])
            except Exception as error:
                rec.update(loop=None, error=f"{type(error).__name__}: {error}"[:300])
                rc = 3
            write(a.output, rec)
    return rc


# ---------- 3c: long-session degeneration ----------

def log_chunk(i: int, lines: int, seed: int = 1) -> tuple[str, str]:
    rnd = random.Random(seed * 100000 + i)
    code = f"E{seed}{4000 + i}"
    rows = []
    bad = rnd.randrange(lines)
    for j in range(lines):
        status = f"status=error code={code}" if j == bad else "status=ok"
        rows.append(f"2026-10-13T{10 + j // 3600 % 10:02d}:{j // 60 % 60:02d}:{j % 60:02d}Z worker-{rnd.randint(1, 64):02d} "
                    f"batch={i * 10000 + j} latency_ms={rnd.randint(5, 900)} {status}")
    return "\n".join(rows), code


def degenerate_text(text: str, finish: str | None) -> tuple[bool, str]:
    from degeneration_sweep import degenerate
    return degenerate(text, finish)


def cmd_longsession(a) -> int:
    """One session per round (different log content per round), each grown until the prompt passes the
    largest target."""
    targets = sorted(int(t) for t in a.targets.split(","))
    for rnd_i in range(1, a.rounds + 1):
        messages = [{"role": "system", "content": f"{SYSTEM} Long session {a.arm}-{rnd_i}."}]
        for i in range(1, 400):
            chunk, code = log_chunk(i, a.chunk_lines, rnd_i)
            call_id = f"call_log_{rnd_i}_{i}"
            messages += [{"role": "user", "content": f"Read log chunk {i} and report the error code it contains, "
                                                     "then one sentence on what to check next."},
                         {"role": "assistant", "content": "",
                          "tool_calls": [{"id": call_id, "type": "function",
                                          "function": {"name": "read_log", "arguments": json.dumps({"chunk": i})}}]},
                         {"role": "tool", "tool_call_id": call_id, "content": chunk}]
            if a.dry_run:
                print(json.dumps({"turn": i, "roles": [m["role"] for m in messages], "chunk_chars": len(chunk),
                                  "sampling": {**SAMPLING, "reasoning_effort": a.reasoning_effort}}))
                return 0
            rec = {"probe": "3c", "arm": a.arm, "round": rnd_i, "turn": i, "code": code,
                   "reasoning_effort": a.reasoning_effort, **SAMPLING}
            try:
                data, secs = chat(a.base_url, body(a.model, messages, a.reasoning_effort, a.max_tokens, True), a.timeout)
                choice = data["choices"][0]
                content, reasoning = split_message(choice.get("message") or {})
                fin = choice.get("finish_reason")
                prompt_tokens = int((data.get("usage") or {}).get("prompt_tokens") or 0)
                deg, why = degenerate_text(content, fin) if content else (fin == "length", "empty")
                run = CHAR_RUN.search(content + "\n" + reasoning)
                rec.update(prompt_tokens=prompt_tokens, finish_reason=fin, secs=round(secs, 2),
                           code_found=code in content, empty=not content, degenerate=deg, why=why,
                           char_run=run.group(0)[:40] if run else None, reasoning_chars=len(reasoning),
                           content=content[:300])
                assistant = {"role": "assistant", "content": content}
                if reasoning and a.preserve_thinking:
                    assistant["reasoning_content"] = reasoning
                messages.append(assistant)
            except Exception as error:
                rec.update(error=f"{type(error).__name__}: {error}"[:300])
                write(a.output, rec)
                return 3
            write(a.output, rec)
            if rec["prompt_tokens"] >= targets[-1]:
                break
    return 0


# ---------- 3e: cost of switching reasoning_effort ----------

def cmd_effortswitch(a) -> int:
    from cache_probe import RuntimeTokenizer, cache_hit_ratio, cached_tokens_from_usage, fixture_token_target
    from fixtures import build_fixture, build_suffix
    from sse_client import stream_chat

    if a.dry_run:
        print(json.dumps({"steps": ["prime xhigh (max_tokens 1)", "control xhigh", f"switch {a.switch_to}", "back xhigh"],
                          "sampling": SAMPLING}))
        return 0
    tok = RuntimeTokenizer(a.base_url, a.model)
    fixture = build_fixture(fixture_token_target(a.context), tok)
    suffix, _ = build_suffix(1024, tok, f"Tool result confirms {fixture.needles[0]}. {fixture.question}")
    rc = 0
    for rep in range(1, a.rounds + 1):
        base = [{"role": "system", "content": f"You are a deterministic audit retrieval assistant. Effort probe {rep:03d}."},
                {"role": "user", "content": f"{fixture.text}\n\n{fixture.question}"}]
        turn = [*base, {"role": "user", "content": suffix}]
        steps = [("prime", base, "xhigh", 1), ("control", turn, "xhigh", 4096),
                 ("switch", turn, a.switch_to, 4096), ("back", turn, "xhigh", 4096)]
        for name, msgs, effort, mt in steps:
            rec = {"probe": "3e", "arm": a.arm, "context_target": a.context, "round": rep, "step": name,
                   "reasoning_effort": effort, **SAMPLING}
            try:
                res = stream_chat(a.base_url, {"model": a.model, "messages": msgs, "max_tokens": mt,
                                               "reasoning_effort": effort, **SAMPLING}, timeout_s=a.timeout)
                prompt = int(res.usage.get("prompt_tokens") or 0)
                cached = cached_tokens_from_usage(res.usage)
                rec.update(ttft_ms=round(res.ttft_ms, 1), prompt_tokens=prompt, cached_tokens=cached,
                           cache_hit_ratio=round(cache_hit_ratio(cached, prompt), 4), finish_reason=res.finish_reason,
                           needles_ok=name == "prime" or (res.finish_reason != "length"
                                                          and all(n in res.text for n in fixture.needles)))
            except Exception as error:
                rec.update(error=f"{type(error).__name__}: {error}"[:300])
                rc = 3
            write(a.output, rec)
    return rc


# ---------- summary ----------

def load(paths: list[Path]) -> list[dict]:
    out = []
    for p in paths:
        out += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


def cmd_summary(a) -> int:
    recs = load(a.files)
    by: dict[tuple, list[dict]] = {}
    for r in recs:
        by.setdefault((r["probe"], r["arm"], r.get("reasoning_effort")), []).append(r)
    print("| probe | braço | effort | n | resultado |\n|---|---|---|---:|---|")
    for (probe, arm, effort), rs in sorted(by.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        if probe == "3a":
            turns = [r for r in rs if r.get("turn")]
            counts = {v: sum(1 for r in turns if r.get("verdict") == v)
                      for v in ("ok", "invented", "missing", "empty", "tool_call", "length", "error")}
            secs = [r["session_secs"] for r in rs if r.get("kind") == "session"]
            res = ", ".join(f"{k} {v}" for k, v in counts.items()) + (f"; sessão mediana {statistics.median(secs):.0f} s" if secs else "")
            n = len(turns)
        elif probe == "3b":
            loops = sum(1 for r in rs if r.get("loop"))
            toks = [r["completion_tokens"] for r in rs if r.get("completion_tokens")]
            res = f"loop {loops}; erros {sum(1 for r in rs if r.get('error'))}; tokens medianos {statistics.median(toks) if toks else '—'}"
            n = len(rs)
        elif probe == "3c":
            big = [r for r in rs if r.get("prompt_tokens", 0) >= 140000]
            res = (f"turnos ≥140K {len(big)}; char_run {sum(1 for r in rs if r.get('char_run'))}; "
                   f"degenerate {sum(1 for r in rs if r.get('degenerate'))}; vazio {sum(1 for r in rs if r.get('empty'))}; "
                   f"código errado {sum(1 for r in rs if r.get('code_found') is False)}; "
                   f"prompt máx {max((r.get('prompt_tokens', 0) for r in rs), default=0)}; erros {sum(1 for r in rs if r.get('error'))}")
            n = len(rs)
        else:
            steps = {}
            for r in rs:
                steps.setdefault(r["step"], []).append(r)
            res = "; ".join(f"{s} TTFT {statistics.median([x['ttft_ms'] for x in v if 'ttft_ms' in x]) / 1000:.2f} s "
                            f"hit {statistics.median([x['cache_hit_ratio'] for x in v if 'cache_hit_ratio' in x]):.2f}"
                            for s, v in steps.items() if any('ttft_ms' in x for x in v))
            n = len(rs)
        print(f"| {probe} | {arm} | {effort} | {n} | {res} |")
    return 0


def cmd_loops(a) -> int:
    print("| arquivo | prompt | loops | n | erros | tokens médios |\n|---|---|---:|---:|---:|---:|")
    for f in a.files:
        by: dict[str, list[dict]] = {}
        for r in load([f]):
            by.setdefault(r["prompt"], []).append(r)
        for prompt, rs in sorted(by.items()):
            ok = [r for r in rs if "error" not in r]
            toks = [r["tokens"] for r in ok if r.get("tokens") is not None]
            print(f"| {f.stem} | {prompt} | {sum(1 for r in ok if r.get('degenerate'))} | {len(ok)} | "
                  f"{len(rs) - len(ok)} | {round(sum(toks) / len(toks)) if toks else '—'} |")
    return 0


def write(path: Path, rec: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({k: rec.get(k) for k in ("probe", "arm", "round", "turn", "id", "step", "verdict", "loop",
                                              "prompt_tokens", "char_run", "error") if k in rec},
                     ensure_ascii=False), flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("contradiction", "charcount", "longsession", "effortswitch"):
        p = sub.add_parser(name)
        p.add_argument("--base-url")
        p.add_argument("--model")
        p.add_argument("--arm", default="dry")
        p.add_argument("--output", type=Path)
        p.add_argument("--reasoning-effort", default="xhigh", choices=EFFORTS)
        p.add_argument("--timeout", type=int, default=3600)
        p.add_argument("--rounds", type=int, default=2)
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--no-preserve-thinking", dest="preserve_thinking", action="store_false")
    sub.choices["contradiction"].add_argument("--turns", type=int, default=20)
    sub.choices["contradiction"].add_argument("--max-tokens", type=int, default=16384)
    sub.choices["charcount"].add_argument("--max-tokens", type=int, default=32768)
    sub.choices["longsession"].add_argument("--targets", default="150000,200000")
    sub.choices["longsession"].add_argument("--chunk-lines", type=int, default=320)
    sub.choices["longsession"].add_argument("--max-tokens", type=int, default=4096)
    sub.choices["effortswitch"].add_argument("--context", type=int, default=131072)
    sub.choices["effortswitch"].add_argument("--switch-to", default="medium", choices=EFFORTS)
    for name in ("summary", "loops"):
        sub.add_parser(name).add_argument("files", nargs="+", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "summary":
        return cmd_summary(a)
    if a.cmd == "loops":
        return cmd_loops(a)
    if not a.dry_run:
        for k in ("base_url", "model", "output"):
            if getattr(a, k) is None:
                ap.error(f"--{k.replace('_', '-')} is required")
        a.output.parent.mkdir(parents=True, exist_ok=True)
    return {"contradiction": cmd_contradiction, "charcount": cmd_charcount,
            "longsession": cmd_longsession, "effortswitch": cmd_effortswitch}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
