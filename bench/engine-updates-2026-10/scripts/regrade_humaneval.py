#!/usr/bin/env python3
"""Re-avalia runs de HumanEval do bench2.py: nota estrita e nota com os imports do prompt.

O bench2.py executa só o código da resposta. Uma resposta sem `from typing import List` falha com NameError,
mesmo com a lógica certa. Este script repete a nota estrita e a nota com as linhas de import do prompt na frente.

Uso (com o .venv do submódulo, que tem o pacote datasets):
  .venv/bin/python -I regrade_humaneval.py --out regrade.json n2 RUN_N2.jsonl o1 RUN_O1.jsonl ...
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_code(text: str) -> str:
    if "```python" in text:
        return text.split("```python")[1].split("```")[0]
    if "```" in text:
        return text.split("```")[1].split("```")[0]
    return text


def with_prompt_imports(prompt: str, code: str) -> str:
    imports = [l for l in prompt.splitlines() if l.startswith(("import ", "from "))]
    return "\n".join(imports + [code])


def passes(code: str, row: dict) -> bool:
    full = code + "\n" + row["test"] + f"\ncheck({row['entry_point']})"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(full)
        name = f.name
    try:
        return subprocess.run([sys.executable, name], capture_output=True, timeout=10).returncode == 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.unlink(name)


def regrade(records: list[dict], dataset) -> dict:
    strict = lenient = 0
    fixed = []
    for r in records:
        row = dataset[r["dataset_idx"]]
        ok = bool(r["correct"])
        ok_imports = ok or passes(with_prompt_imports(row["prompt"], extract_code(r.get("raw_response") or "")), row)
        strict += ok
        lenient += ok_imports
        if ok_imports and not ok:
            fixed.append(r["question_num"])
    return {"n": len(records), "strict": strict, "with_imports": lenient, "fixed_by_imports": fixed,
            "truncated": [r["question_num"] for r in records if r.get("finish_reason") == "length"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("runs", nargs="+", help="pares <nome> <run.jsonl>")
    a = ap.parse_args(argv)
    from datasets import load_dataset
    ds = load_dataset("openai/openai_humaneval", split="test")
    out = {}
    for name, path in zip(a.runs[::2], a.runs[1::2]):
        recs = [r for r in map(json.loads, Path(path).read_text(encoding="utf-8").splitlines()) if "question_num" in r]
        out[name] = {"run": Path(path).name, **regrade(recs, ds)}
        print(name, {k: v for k, v in out[name].items() if k != "run"})
    if a.out:
        a.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
