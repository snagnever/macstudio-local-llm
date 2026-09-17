#!/usr/bin/env python3
"""Generate short, non-reasoning turns against the support model.

The support model exists to absorb short turns (session titles, commit
messages, classification, short summaries) that would otherwise queue on the
driver's single decode slot. This script plays that load: it sends chat
completions in a loop, streaming so it can time TTFT, and records one JSONL
line per turn.

It is meant to run *concurrently* with cache_probe.py against the driver, so
the driver's T_turno penalty under concurrency can be measured. On its own it
also gives the support model's solo decode/ TTFT (Etapa 1).

Usage:
    support-load.py --base-url http://127.0.0.1:11235/v1 --model <id>:no-think \
        --duration 120 --prompt-tokens 400 --max-tokens 256 \
        --output results/s1-load.jsonl

Only the standard library is used so it runs under the rig's system python3.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# Tasks the support slot is expected to absorb, in Portuguese (the language the
# tasks actually run in here). Kept short so the model does not turn them into
# reasoning problems.
TASKS = [
    "Gere um título de no máximo 6 palavras para uma sessão sobre: {topic}",
    "Escreva uma mensagem de commit de uma linha para a mudança: {topic}",
    "Classifique a intenção da frase a seguir como pergunta, pedido ou informação: {topic}",
    "Resuma em uma frase: {topic}",
    "Extraia a ação principal da frase: {topic}",
]

TOPICS = [
    "atualizar o driver de benchmark para a versão 26.9.2",
    "corrigir o parser de tool call do MiniCPM5",
    "medir a latência do turno sob concorrência",
    "adicionar o card do modelo ao índice de documentação",
    "limpar o cache de prefixo antes de cada execução fria",
    "comparar a quant mista de 4 bits com a de 8 bits",
    "subir o servidor de suporte na porta 11235",
    "registrar o consumo de memória residente e o swap",
    "validar o formato de saída em português",
    "reduzir o número de repetições da banda de 128K",
]

# Filler so prompts reach the target token count. Repeated text tokenizes
# almost linearly, which is enough to budget a prompt by characters.
FILLER = (
    "A medição acontece na mesma máquina e na mesma sessão, com o driver no ar "
    "e o modelo de suporte gerando em laço. O objetivo é isolar o custo de "
    "concorrência sem trocar o runtime do driver, mantendo o perfil de "
    "amostragem do vendor e a fixture de recuperação. Nada aqui substitui a "
    "qualidade de agente, que fica fora do escopo desta campanha. "
)


def build_prompt(target_tokens: int, turn: int, copy_heavy: bool = False) -> str:
    # Copy-heavy prompts force the model's *output* to quote its *input*, which is
    # where prompt-lookup (--ngram-draft) pays off. Used to measure that lever.
    if copy_heavy:
        head = "Reescreva exatamente o trecho entre <texto> e </texto>, sem alterar nada:"
        remaining = max(0, target_tokens * 4 - len(head) - 30)
        body = (FILLER * (remaining // len(FILLER) + 1))[:remaining]
        return f"{head}\n<texto>{body}</texto>"
    task = TASKS[turn % len(TASKS)]
    topic = TOPICS[(turn // len(TASKS)) % len(TOPICS)]
    head = task.format(topic=topic)
    # ~4 chars per token; reserve room for the head.
    remaining = max(0, target_tokens * 4 - len(head))
    filler = (FILLER * (remaining // len(FILLER) + 1))[:remaining]
    return f"{head}\n\nContexto:\n{filler}"


def one_turn(base_url: str, model: str, prompt: str, max_tokens: int,
             temperature: float | None, top_p: float | None,
             timeout: float) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if temperature is not None:
        body["temperature"] = temperature
    if top_p is not None:
        body["top_p"] = top_p

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    ttft = None
    chunks = 0
    completion_tokens = None
    prompt_tokens = None
    finish = None
    error = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if data.get("usage"):
                    completion_tokens = data["usage"].get("completion_tokens")
                    prompt_tokens = data["usage"].get("prompt_tokens")
                for choice in data.get("choices", []):
                    delta = choice.get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        if ttft is None:
                            ttft = time.monotonic() - started
                        chunks += 1
                    if choice.get("finish_reason"):
                        finish = choice["finish_reason"]
        ok = True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        ok = False
        error = f"{type(exc).__name__}: {exc}"

    total = time.monotonic() - started
    toks = completion_tokens if completion_tokens is not None else chunks
    decode_tps = None
    if ttft is not None and toks and toks > 1 and total > ttft:
        decode_tps = (toks - 1) / (total - ttft)

    return {
        "ts": time.time(),
        "ok": ok,
        "error": error,
        "ttft_s": ttft,
        "total_s": total,
        "decode_tps": decode_tps,
        "completion_tokens": toks,
        "prompt_tokens": prompt_tokens,
        "finish_reason": finish,
    }


def worker(name: int, args: argparse.Namespace, deadline: float,
           out_lock: threading.Lock, out) -> None:
    turn = name
    while time.monotonic() < deadline:
        prompt = build_prompt(args.prompt_tokens, turn, args.copy_heavy)
        row = one_turn(args.base_url, args.model, prompt, args.max_tokens,
                       args.temperature, args.top_p, args.timeout)
        row["turn"] = turn
        row["worker"] = name
        row["target_prompt_tokens"] = args.prompt_tokens
        with out_lock:
            out.write(json.dumps(row) + "\n")
            out.flush()
        turn += args.concurrency
        if args.turns and turn >= args.turns * args.concurrency:
            break
        if args.gap > 0:
            time.sleep(args.gap)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default="http://127.0.0.1:11235/v1")
    p.add_argument("--model", required=True)
    p.add_argument("--turns", type=int, default=0,
                   help="total turns per worker; 0 = run until --duration")
    p.add_argument("--duration", type=float, default=120.0,
                   help="seconds to keep generating (used when --turns=0)")
    p.add_argument("--concurrency", type=int, default=1,
                   help="parallel in-flight requests")
    p.add_argument("--prompt-tokens", type=int, default=400)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=0.95)
    p.add_argument("--gap", type=float, default=0.0,
                   help="seconds to sleep between turns in a worker")
    p.add_argument("--copy-heavy", action="store_true",
                   help="ask the model to quote its input verbatim (n-gram lever)")
    p.add_argument("--timeout", type=float, default=600.0)
    p.add_argument("--warmup", action="store_true",
                   help="send one untimed request before the loop")
    p.add_argument("--output", type=Path, required=True)
    return p


def main() -> int:
    args = build_parser().parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.warmup:
        one_turn(args.base_url, args.model, build_prompt(64, 0), 8,
                 args.temperature, args.top_p, args.timeout)

    deadline = time.monotonic() + args.duration
    out_lock = threading.Lock()
    with args.output.open("a") as out:
        threads = [
            threading.Thread(target=worker,
                             args=(i, args, deadline, out_lock, out),
                             daemon=True)
            for i in range(args.concurrency)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())