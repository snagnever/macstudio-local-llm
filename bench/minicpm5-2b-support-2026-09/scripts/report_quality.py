#!/usr/bin/env python3
"""Relatório da Etapa 3: imprime as saídas e checa formato/idioma.

usage:
    report_quality.py results/etapa3-s1.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CATEGORIES = {"pergunta", "pedido", "informação", "informacao"}
CJK = re.compile(r"[\u4e00-\u9fff]")


def check_format(task_id: str, output: str) -> tuple[bool, str]:
    if not output:
        return False, "vazio"
    if task_id.startswith("titulo"):
        words = output.split()
        if len(words) > 8:
            return False, f"título longo ({len(words)} palavras)"
        return True, "ok"
    if task_id.startswith("commit"):
        if "\n" in output.strip():
            return False, "mais de uma linha"
        return True, "ok"
    if task_id.startswith("intent"):
        low = output.strip().lower().rstrip(".")
        if low not in CATEGORIES:
            return False, f"categoria fora do conjunto: {output[:40]!r}"
        return True, "ok"
    if task_id.startswith("resumo"):
        if "\n" in output.strip():
            return False, "mais de uma linha"
        return True, "ok"
    return True, "ok"


def check_language(output: str) -> tuple[bool, str]:
    if not output:
        return False, "vazio"
    if CJK.search(output):
        return False, "contém CJK"
    return True, "ok"


def main() -> int:
    path = Path(sys.argv[1])
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    fmt_ok = lang_ok = 0
    for r in rows:
        o = r.get("output")
        if isinstance(o, list):
            o = json.dumps(o, ensure_ascii=False)
        o = o or ""
        f_ok, f_note = check_format(r["task_id"], o)
        l_ok, l_note = check_language(o)
        fmt_ok += f_ok
        lang_ok += l_ok
        flags = []
        if not f_ok:
            flags.append(f"FORMATO:{f_note}")
        if not l_ok:
            flags.append(f"IDIOMA:{l_note}")
        print(f"[{r['task_id']}] {' '.join(flags) if flags else 'ok'}")
        print(f"    {o[:200]}")
    n = len(rows)
    print(f"\nresumo: formato {fmt_ok}/{n} ({100*fmt_ok/n:.0f}%)  idioma {lang_ok}/{n} ({100*lang_ok/n:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())