#!/usr/bin/env python3
"""Converte os JSONL da sonda de capacidade a 512K no `sonda-512k.json` que
`render_dashboard.py --sonda` lê (ver a tabela "Sonda de capacidade a 512K"
em `scripts/render_dashboard.py`: chaves `reaches`, `followup`, `decode_tps`,
`cold_ttft_s`, `note` — além de `wired_peak_gb`, `mechanism` e `truncated`,
guardados aqui mesmo que a página ainda não os exiba).

Truncamento (`finish_reason: "length"`) no `cold` conta como alcançar a
banda, não como recusa: a 512K com reasoning xhigh e um teto de tokens
pequeno, truncar é esperado e prova o oposto de uma recusa — o servidor
rodou o prefill de 512K e gerou tokens. Um `identical` truncado conta como
follow-up servido pelo mesmo motivo.

Não roda benchmark nenhum: só lê JSONL já escrito em disco.

Uso:
    python3 scripts/sonda_to_json.py --results-dir results \\
        [--glob 'c*-524288-t1.0-yarn2.jsonl'] [--no-yarn c2,c3] \\
        --out /tmp/sonda-512k.json
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any

DEFAULT_GLOB = "c*-524288-t1.0-yarn2.jsonl"
NOTE_MAXLEN = 160


def _candidate_id(record: dict[str, Any], path: str) -> str:
    arm = record.get("arm")
    if arm:
        return str(arm)
    return Path(path).name.split("-", 1)[0]


def _truncate(s: Any, n: int = NOTE_MAXLEN) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


DEFAULT_MAX_TOKENS = 4096


def _is_truncated(record: dict[str, Any]) -> bool:
    """cache_probe's truncation convention: `finish_reason: "length"`, with
    `error` either null/empty or set to the matching `"finish_reason:length"`
    string. At 512K with reasoning xhigh and a small max_tokens cap, this is
    a plausible and meaningful outcome — the server ran the prefill and
    generated tokens — not a refusal or a crash, so it must not be scored
    like one.

    `finish_reason == "length"` alone is NOT enough: a record can be capped
    at max_tokens AND carry an unrelated failure (e.g. a socket error hit
    while streaming the truncated response) in `error`. Any `error` other
    than the `finish_reason:length` marker itself means a real failure, not
    a clean truncation — it must fall through to the normal failure path."""
    if record.get("finish_reason") != "length":
        return False
    err = record.get("error")
    return not err or str(err).startswith("finish_reason:length")


def load_records(results_dir: str, pattern: str) -> dict[str, list[dict[str, Any]]]:
    """`<candidate id>` -> its probe records, in file/line order."""
    by_cand: dict[str, list[dict[str, Any]]] = {}
    for f in sorted(glob.glob(str(Path(results_dir) / pattern))):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                cid = _candidate_id(r, f)
                by_cand.setdefault(cid, []).append(r)
    return by_cand


def convert(by_cand: dict[str, list[dict[str, Any]]], no_yarn: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    for cid, records in by_cand.items():
        cold = next((r for r in records if r.get("scenario") == "cold"), None)

        if cold is None:
            # Server refused or crashed before writing the cold record at all.
            out[cid] = {
                "reaches": False,
                "followup": None,
                "note": "sem registro cold (recusa ou crash; ver boot log)",
            }
            continue

        identical = next((r for r in records if r.get("scenario") == "identical"), None)

        cold_truncated = _is_truncated(cold)
        reaches = (bool(cold.get("correct")) and not cold.get("error")) or cold_truncated

        identical_truncated = identical is not None and _is_truncated(identical)
        if identical is None:
            followup: bool | None = None
        elif identical_truncated:
            # The follow-up request was accepted and served (truncated at the
            # cap, not refused) — that is a served follow-up.
            followup = True
        else:
            followup = bool(identical.get("correct")) and not identical.get("error")

        decode_tps = cold.get("decode_tps")
        cold_ttft_s = cold.get("ttft_ms") / 1000 if cold.get("ttft_ms") is not None else None
        wired_vals = [r.get("ram_peak_gb") for r in records if r.get("ram_peak_gb") is not None]

        note_parts: list[str] = []
        cold_error = cold.get("error")
        cold_stream_error = isinstance(cold_error, str) and cold_error.startswith("stream_error:")
        if cold_truncated:
            max_tokens = cold.get("max_tokens") or DEFAULT_MAX_TOKENS
            note_parts.append(f"truncado em {max_tokens} tokens (chegou a 512K)")
        elif not reaches:
            if cold_stream_error:
                # cache_probe's in-stream-error marker (finish_reason "error"/
                # None with no HTTP failure) -- name the failing finish_reason
                # instead of the raw "stream_error:<x>" string.
                note_parts.append(f"erro no stream ({cold.get('finish_reason')})")
            elif cold_error:
                note_parts.append(_truncate(cold_error))
            elif cold.get("correct") is False:
                # Correct=False with no error at all: the server answered, the
                # answer was just wrong -- distinct from a refusal/crash.
                note_parts.append("resposta incorreta")

        identical_error = identical.get("error") if identical is not None else None
        identical_stream_error = isinstance(identical_error, str) and identical_error.startswith("stream_error:")
        if identical_truncated:
            note_parts.append("follow-up truncado")
        elif identical_stream_error:
            note_parts.append("follow-up com erro no stream")
        elif followup is False:
            note_parts.append("follow-up recusado")

        out[cid] = {
            "reaches": reaches,
            "truncated": cold_truncated,
            "followup": followup,
            "decode_tps": round(decode_tps, 1) if decode_tps is not None else None,
            "cold_ttft_s": round(cold_ttft_s, 1) if cold_ttft_s is not None else None,
            "wired_peak_gb": max(wired_vals) if wired_vals else None,
            "mechanism": cold.get("runtime_revision"),
            "note": "; ".join(note_parts),
        }

    for cid in no_yarn:
        if cid in out:
            continue  # a probe file exists for this candidate — use it, not the fixed row
        out[cid] = {
            "reaches": False,
            "followup": None,
            "note": "runtime sem YaRN (oMLX): teto 262K",
        }

    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--glob", default=DEFAULT_GLOB)
    ap.add_argument(
        "--no-yarn",
        default="",
        help="IDs de candidatos separados por virgula sem suporte a YaRN "
             "(ex.: c2,c3) — recebem uma linha fixa 'runtime sem YaRN', a "
             "menos que ja exista arquivo de sonda para o candidato.",
    )
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    by_cand = load_records(a.results_dir, a.glob)
    no_yarn = [c.strip() for c in a.no_yarn.split(",") if c.strip()]
    sonda = convert(by_cand, no_yarn)

    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sonda, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out_path} ({len(sonda)} candidatos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
