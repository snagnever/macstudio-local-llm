#!/usr/bin/env python3
"""Etapa 3 — roda as tarefas reais de suporte contra um modelo e grava as saídas.

Tarefas de texto (título, commit, classificação, resumo) rodam com `:no-think`,
perfil `temperature=0.7, top_p=0.95`. As tarefas de tool call mandam o schema e
capturam `tool_calls`.

A avaliação é por rubrica (formato, conteúdo, idioma) e cega: use build_blind.py
para embaralhar as saídas dos modelos antes de julgar.

usage:
    quality-run.py --base-url http://127.0.0.1:11235/v1 --model <id>:no-think \
        --arm s1 --tasks scripts/quality-tasks.json --output results/etapa3-s1.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

INSTRUCTIONS = {
    "session_title": "Gere um título curto para a sessão a seguir, com no máximo 6 palavras. "
                     "Responda em português e apenas com o título.",
    "commit_message": "Escreva uma mensagem de commit de uma linha para a mudança descrita. "
                      "Responda em português e apenas com a mensagem.",
    "classification": "Classifique a frase a seguir como 'pergunta', 'pedido' ou 'informação'. "
                      "Responda em português e apenas com a categoria.",
    "tool_summary": "Resuma em uma frase o resultado da ferramenta a seguir. "
                    "Responda em português e apenas com o resumo.",
}


def post(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_text(base_url, model, task, temperature, top_p, timeout, guided=False):
    instruction = INSTRUCTIONS.get(task["type"], "")
    prompt = f"{instruction}\n\n{task['input']}"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
        "temperature": temperature,
        "top_p": top_p,
    }
    if guided and task["type"] == "classification":
        body["guided_choice"] = ["pergunta", "pedido", "informação"]
    t0 = time.monotonic()
    try:
        data = post(f"{base_url}/chat/completions", body, timeout)
        msg = data["choices"][0]["message"]
        return {
            "output": (msg.get("content") or "").strip(),
            "reasoning": msg.get("reasoning"),
            "finish_reason": data["choices"][0].get("finish_reason"),
            "usage": data.get("usage"),
            "ok": True,
            "elapsed_s": round(time.monotonic() - t0, 3),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"output": None, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "elapsed_s": round(time.monotonic() - t0, 3)}


def run_tool(base_url, model, task, temperature, top_p, timeout):
    tool = task["tool"]
    body = {
        "model": model,
        "messages": [{"role": "user", "content": task["user"]}],
        "tools": [{"type": "function", "function": tool}],
        "tool_choice": "auto",
        "max_tokens": 256,
        "temperature": temperature,
        "top_p": top_p,
    }
    t0 = time.monotonic()
    try:
        data = post(f"{base_url}/chat/completions", body, timeout)
        msg = data["choices"][0]["message"]
        return {
            "output": msg.get("tool_calls") or (msg.get("content") or "").strip(),
            "tool_calls": msg.get("tool_calls"),
            "content": msg.get("content"),
            "finish_reason": data["choices"][0].get("finish_reason"),
            "usage": data.get("usage"),
            "ok": True,
            "elapsed_s": round(time.monotonic() - t0, 3),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"output": None, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "elapsed_s": round(time.monotonic() - t0, 3)}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:11235/v1")
    p.add_argument("--model", required=True)
    p.add_argument("--arm", required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=0.95)
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--guided-classification", action="store_true",
                   help="constrain classification tasks with guided_choice")
    args = p.parse_args()

    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with args.output.open("a", encoding="utf-8") as out:
        for rep in range(args.repeat):
            for task in tasks["text_tasks"] + tasks["tool_tasks"]:
                is_tool = task["id"].startswith("tool-")
                if is_tool:
                    result = run_tool(args.base_url, args.model, task, args.temperature,
                                      args.top_p, args.timeout)
                else:
                    result = run_text(args.base_url, args.model, task, args.temperature,
                                      args.top_p, args.timeout, args.guided_classification)
                record = {"arm": args.arm, "task_id": task["id"],
                          "task_type": task["type"] if not is_tool else "tool_call",
                          "guided": bool(args.guided_classification and not is_tool
                                         and task["type"] == "classification"),
                          "repeat": rep + 1, **result}
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                rows.append(record)
    ok = sum(1 for r in rows if r["ok"])
    print(f"{args.output}: {len(rows)} tarefas, {ok} ok, {len(rows) - ok} erro")
    return 0


if __name__ == "__main__":
    sys.exit(main())