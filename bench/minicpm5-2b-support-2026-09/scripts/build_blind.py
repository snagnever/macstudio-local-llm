#!/usr/bin/env python3
"""Embaralha as saídas da Etapa 3 para julgamento cego.

Lê os `etapa3-<arm>.jsonl`, agrupa por tarefa e reatribui rótulos anônimos por
tarefa (A/B/C), de forma que nenhum viés de posição favoreça um modelo. Grava:

    results/etapa3-blind.jsonl   — uma linha por (tarefa, saída), com judge_id
    results/etapa3-map.json      — judge_id -> arm (NÃO mostrar ao juiz)

usage:
    build_blind.py --results-dir results --arms s1 s2 s3 \
        --tasks scripts/quality-tasks.json
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path, default=Path("results"))
    p.add_argument("--arms", nargs="+", required=True)
    p.add_argument("--tasks", type=Path, default=Path("scripts/quality-tasks.json"))
    p.add_argument("--seed", type=int, default=20260915)
    args = p.parse_args()

    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    task_lookup = {}
    for t in tasks["text_tasks"]:
        task_lookup[t["id"]] = {"type": t["type"], "input": t["input"]}
    for t in tasks["tool_tasks"]:
        task_lookup[t["id"]] = {"type": "tool_call", "input": t["user"],
                                "tool": t["tool"]}

    by_task: dict[str, list[dict]] = defaultdict(list)
    for arm in args.arms:
        for row in load(args.results_dir / f"etapa3-{arm}.jsonl"):
            if row.get("repeat", 1) == 1 and row.get("ok"):
                by_task[row["task_id"]].append(row)

    rng = random.Random(args.seed)
    blind = []
    mapping = {}
    for task_id in sorted(by_task):
        rows = by_task[task_id]
        rng.shuffle(rows)
        for idx, row in enumerate(rows):
            judge_id = f"{task_id}-{chr(65 + idx)}"
            blind.append({
                "judge_id": judge_id,
                "task_id": task_id,
                "task_type": row["task_type"],
                "input": task_lookup.get(task_id, {}).get("input"),
                "tool": task_lookup.get(task_id, {}).get("tool"),
                "output": row.get("output"),
            })
            mapping[judge_id] = row["arm"]

    (args.results_dir / "etapa3-blind.jsonl").write_text(
        "".join(json.dumps(b, ensure_ascii=False) + "\n" for b in blind),
        encoding="utf-8")
    (args.results_dir / "etapa3-map.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(blind)} itens cegos para {len(by_task)} tarefas; mapa em etapa3-map.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())