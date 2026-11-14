"""Tables and decision rules over the session records.

usage: summarize.py [--out results] [--md results/summary.md] [--matrix-dir ../harness-matrix/results]
                    [--base k2] [--cand z4]

Rules (the campaign only recommends):
  Reserva  the candidate pack closes at least (base - tolerance) tasks, tolerance = ceil(5% of the sessions of
           one pack), and its median wall time over done sessions is at most 1.25x the base's.
  Harness  order by done tasks over both packs; when two neighbours differ by at most 1 task, the lower median
           wall time over done sessions goes first.
  Válido   the base pack closes at least one hard task (T1, T5, T7) in some harness.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

import tasks

HERE = Path(__file__).resolve().parents[1]
MAX_RATIO = 1.25
TOLERANCE_SHARE = 0.05


def load(out: Path) -> list[dict]:
    """The session records of the matrix; smoke records are left out."""
    files = sorted((Path(out) / "sessions").glob("*.json"))
    return [json.loads(f.read_text()) for f in files if not f.name.startswith("smoke-")]


def _median_done(records: list[dict]) -> float | None:
    walls = [r["wall_s"] for r in records if r["task_done"]]
    return round(statistics.median(walls), 1) if walls else None


def _cell(records: list[dict]) -> dict:
    return {"done": sum(r["task_done"] for r in records), "n": len(records),
            "median_wall_done_s": _median_done(records)}


def table(records: list[dict]) -> dict:
    """One cell per (harness, pack)."""
    keys = sorted({(r["harness"], r["pack"]) for r in records})
    return {k: _cell([r for r in records if (r["harness"], r["pack"]) == k]) for k in keys}


def reserva(records: list[dict], base: str = "k2", cand: str = "z4") -> dict:
    b, c = ([r for r in records if r["pack"] == p] for p in (base, cand))
    mb, mc = _median_done(b), _median_done(c)
    out = {"done_base": sum(r["task_done"] for r in b), "done_cand": sum(r["task_done"] for r in c),
           "tolerance": math.ceil(TOLERANCE_SHARE * len(b)), "ratio": round(mc / mb, 3) if mb and mc else None}
    # The pooled median moves with the mix of done tasks; the ratio per task does not.
    out["ratio_by_task"] = {}
    for t in tasks.TASKS:
        tb, tc = (_median_done([r for r in p if r["task"] == t]) for p in (b, c))
        if tb and tc:
            out["ratio_by_task"][t] = round(tc / tb, 2)
    out["pass"] = None if out["ratio"] is None else (
        out["done_cand"] >= out["done_base"] - out["tolerance"] and out["ratio"] <= MAX_RATIO)
    return out


def rank(records: list[dict]) -> list[tuple[str, int, float | None]]:
    rows = []
    for h in sorted({r["harness"] for r in records}):
        mine = [r for r in records if r["harness"] == h]
        rows.append((h, sum(r["task_done"] for r in mine), _median_done(mine)))
    rows.sort(key=lambda row: -row[1])
    for _ in rows:                       # bubble passes: a tie of one task goes to the faster harness
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            if a[1] - b[1] <= 1 and b[2] is not None and (a[2] is None or b[2] < a[2]):
                rows[i], rows[i + 1] = b, a
    return rows


def valido(records: list[dict], base: str = "k2") -> bool:
    return any(r["task_done"] for r in records if r["pack"] == base and tasks.TASKS[r["task"]].hard)


def _fmt(v) -> str:
    return "–" if v is None else str(v)


def render(records: list[dict], base: str = "k2", cand: str = "z4") -> str:
    """The summary page, in Portuguese like the other campaign pages. No session text."""
    cells, res = table(records), reserva(records, base, cand)
    packs = [p for p in (base, cand) if any(r["pack"] == p for r in records)]
    lines = ["# Entrega por harness — resumo", "",
             f"Sessões: {len(records)}. Pesos: {', '.join(f'`{p}`' for p in packs)}. "
             "Cada célula mostra tarefas prontas / sessões e a mediana de tempo das sessões prontas.", "",
             "## Harness × peso", "", "| harness | " + " | ".join(f"`{p}` prontas | `{p}` mediana (s)" for p in packs)
             + " |", "|---|" + "---:|" * (2 * len(packs))]
    for h in sorted({r["harness"] for r in records}):
        row = [f"{cells[(h, p)]['done']}/{cells[(h, p)]['n']} | {_fmt(cells[(h, p)]['median_wall_done_s'])}"
               if (h, p) in cells else "– | –" for p in packs]
        lines.append(f"| {h} | " + " | ".join(row) + " |")
    lines += ["", "## Por tarefa", "", "| tarefa | " + " | ".join(f"`{p}` prontas" for p in packs)
              + " | mediana (s) |", "|---|" + "---:|" * (len(packs) + 1)]
    for t in tasks.TASKS:
        mine = [r for r in records if r["task"] == t]
        per = [f"{sum(r['task_done'] for r in mine if r['pack'] == p)}/{sum(r['pack'] == p for r in mine)}"
               for p in packs]
        lines.append(f"| {t} | " + " | ".join(per) + f" | {_fmt(_median_done(mine))} |")
    reasons = Counter()
    for r in records:
        reasons["timeout"] += bool(r["timeout"])
        reasons["declarou pronto sem estar"] += bool(r["claimed_done"] and not r["task_done"])
        reasons["saiu com erro"] += bool(not r["timeout"] and r["exit"] not in (0, None))
        reasons.update(r["cheat"])
    lines += ["", "## Motivos de falha", "", "| motivo | sessões |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in reasons.items() if v] or ["| nenhum | 0 |"]
    per_task = list(res["ratio_by_task"].values())
    verdict = {True: "passa", False: "falha", None: "sem veredito"}[res["pass"]]
    lines += ["", "## Regras", "",
              f"- **Reserva** (`{cand}` contra `{base}`): {verdict}. Prontas {res['done_cand']} contra "
              f"{res['done_base']}, tolerância {res['tolerance']}; razão de tempo {_fmt(res['ratio'])} "
              f"(limite {MAX_RATIO})" + (f"; por tarefa, de {min(per_task)} a {max(per_task)}." if per_task else "."),
              "- **Harness**, da melhor para a pior: "
              + "; ".join(f"{h} ({d} prontas, mediana {_fmt(m)} s)" for h, d, m in rank(records)) + ".",
              f"- **Válido**: {'sim' if valido(records, base) else 'não'}. "
              + ("O peso base fecha pelo menos 1 tarefa difícil." if valido(records, base)
                 else "O peso base não fecha nenhuma tarefa difícil; as tarefas difíceis não separam nada."),
              "", "Com 2 repetições por combinação, uma diferença de 1 tarefa entre dois harnesses ou entre dois pesos não dá veredito. A razão de tempo junta todas as tarefas: o peso que falha uma tarefa lenta fica com a mediana menor.", ""]
    return "\n".join(lines)


def write_matrix_verdicts(records: list[dict], matrix_dir: Path) -> list[Path]:
    """One verdict file per (harness, model) in the harness-matrix layout."""
    written = []
    for h, model in sorted({(r["harness"], r["model_id"]) for r in records}):
        mine = [r for r in records if (r["harness"], r["model_id"]) == (h, model)]
        cell, pack = _cell(mine), mine[0]["pack"]
        per_task = ", ".join(f"{t} {sum(r['task_done'] for r in mine if r['task'] == t)}/"
                             f"{sum(r['task'] == t for r in mine)}" for t in tasks.TASKS)
        path = Path(matrix_dir) / h / (model.replace("/", "-").replace(":", "-") + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {h} × {model}\n\n"
            f"- **Campanha:** [harness-delivery-2026-11](../../../harness-delivery-2026-11/results/summary.md), "
            f"peso `{pack}`.\n"
            "- **Tarefa:** 7 tarefas de código com check automático, uma sessão não interativa por tarefa.\n"
            f"- **Config:** {h} {mine[0]['harness_version']}, Splash 1.6.1, contexto 131072, reasoning effort "
            "`xhigh`, `HOME` isolado.\n"
            f"- **Resultado:** {cell['done']}/{cell['n']} tarefas prontas. Por tarefa: {per_task}.\n"
            f"- **Tempo:** mediana de {_fmt(cell['median_wall_done_s'])} s nas sessões prontas.\n"
            f"- **Raw:** `bench/harness-delivery-2026-11/logs/` (fora do git).\n")
        written.append(path)
    return written


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "results")
    ap.add_argument("--md", type=Path)
    ap.add_argument("--matrix-dir", type=Path)
    ap.add_argument("--base", default="k2")
    ap.add_argument("--cand", default="z4")
    a = ap.parse_args(argv)
    records = load(a.out)
    md = render(records, a.base, a.cand)
    (a.md.write_text(md) if a.md else print(md))
    if a.matrix_dir:
        write_matrix_verdicts(records, a.matrix_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
