#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Optional

from metrics import parse_ane_runtime_evidence, parse_macmon


def summarize_telemetry(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        raise ValueError("telemetry log contains no valid macmon samples")
    first = samples[0]
    return {
        "ram_peak_gb": max(float(sample["ram_gb"]) for sample in samples),
        "swap_delta_gb": max(
            0.0,
            max(float(sample["swap_gb"]) for sample in samples)
            - float(first["swap_gb"]),
        ),
        "gpu_temp_start_c": float(first["gpu_temp_c"]),
        "gpu_temp_peak_c": max(
            float(sample["gpu_temp_c"]) for sample in samples
        ),
        "gpu_util_peak_pct": max(
            float(sample["gpu_pct"]) for sample in samples
        ),
        "power_peak_w": max(float(sample["power_w"]) for sample in samples),
        "telemetry_samples": len(samples),
    }


def load_telemetry(path: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for raw_line in source:
            line = raw_line.strip()
            if not line:
                continue
            try:
                samples.append(parse_macmon(line))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return samples


def enrich_records(
    records: list[dict[str, Any]],
    session_id: str,
    summary: dict[str, Any],
    runtime_evidence: Optional[dict[str, Any]] = None,
    arm: Optional[str] = None,
    context: Optional[int] = None,
) -> int:
    changed = 0
    for record in records:
        if record.get("session_id") == session_id:
            record.update(summary)
            if record.get("arm") == arm and record.get("context_target") == context:
                if runtime_evidence is not None:
                    record.update(runtime_evidence)
            changed += 1
    return changed


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, 1):
            line = raw_line.strip()
            if not line:
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            records.append(value)
    return records


def write_records(path: Path, records: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Attach one macmon session summary to campaign JSONL records."
    )
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--telemetry", required=True, type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--runtime-log", type=Path)
    parser.add_argument("--arm")
    parser.add_argument("--context", type=int)
    args = parser.parse_args()

    summary = summarize_telemetry(load_telemetry(args.telemetry))
    records = load_records(args.results)
    runtime_evidence = None
    if args.runtime_log is not None:
        if args.arm is None or args.context is None:
            raise SystemExit("--runtime-log requires --arm and --context")
        runtime_evidence = parse_ane_runtime_evidence(
            args.runtime_log.read_text(encoding="utf-8"),
            args.arm,
            args.session_id,
            args.context,
        )
    changed = enrich_records(
        records,
        args.session_id,
        summary,
        runtime_evidence,
        args.arm,
        args.context,
    )
    if changed == 0:
        raise SystemExit(f"no records found for telemetry session {args.session_id}")
    write_records(args.results, records)
    print(json.dumps({"session_id": args.session_id, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
