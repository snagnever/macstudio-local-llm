#!/usr/bin/env python3
import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PRODUCTION_ARMS = {"C", "E", "F", "G", "H"}
ARM_PORTS = {"C": 11234, "E": 8080, "F": 8080, "G": 8080, "H": 8080}
REQUIRED_CONTEXTS = {32768, 65536}
REQUIRED_SCENARIOS = {"identical", "append", "middle_mutation", "tool_turn"}
PAIRWISE_CONTEXTS = (16384, 32768)


def gate_record(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    scenario = record.get("scenario")
    if record.get("record_type") == "tool_turn":
        scenario = "tool_turn"

    threshold = {
        "identical": 0.95,
        "append": 0.90,
        "tool_turn": 0.90,
    }.get(scenario)
    cache_enabled = record.get("cache_enabled", True)
    if (
        cache_enabled
        and threshold is not None
        and record.get("cache_hit_ratio", 0.0) < threshold
    ):
        failures.append("cache_hit_ratio")

    if scenario == "middle_mutation" and cache_enabled:
        ceiling = record.get("mutation_prefix_tokens")
        if ceiling is not None and record.get("cached_tokens", 0) > ceiling + 16:
            failures.append("middle_mutation_reuse")
        elif ceiling is None and record.get("cache_hit_ratio", 0.0) > 0.55:
            failures.append("middle_mutation_reuse")
    if record.get("swap_delta_gb", 0.0) > 0.5:
        failures.append("swap_delta_gb")
    if record.get("ram_peak_gb", 0.0) > 80.0:
        failures.append("ram_peak_gb")
    if not record.get("correct", False):
        failures.append("correct")
    if record.get("error"):
        failures.append("error")
    return failures


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _comparison_signature(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("runtime"),
        record.get("model_revision"),
        record.get("context_target"),
        record.get("temperature"),
        record.get("top_p"),
        record.get("top_k"),
        record.get("min_p"),
        record.get("presence_penalty"),
        record.get("repetition_penalty"),
        record.get("max_tokens"),
    )


def _records_for_arm_context(
    records: list[dict[str, Any]], arm: str, context: int
) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("arm") == arm
        and record.get("context_target") == context
        and record.get("record_type") not in {"tool_turn", "verdict"}
    ]


def _functional_failures(records: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    if any(gate_record(record) for record in records):
        failures.append("functional")
    if any(record.get("needle_correct") is False for record in records):
        failures.append("needle")
    explicit_tool = [record["tool_loop_correct"] for record in records if "tool_loop_correct" in record]
    if explicit_tool and not all(explicit_tool):
        failures.append("tool_loop")
    return failures


def _tool_loop_passed(records: list[dict[str, Any]], arm: str) -> bool:
    explicit = [
        record["tool_loop_correct"]
        for record in records
        if record.get("arm") == arm and "tool_loop_correct" in record
    ]
    if explicit:
        return all(explicit)
    verdicts = [
        record
        for record in records
        if record.get("arm") == arm and record.get("record_type") == "verdict"
    ]
    return any(
        record.get("correct") and int(record.get("turns_requested") or 0) >= 20
        for record in verdicts
    )


def _pairwise_result(
    records: list[dict[str, Any]],
    baseline_arm: str,
    candidate_arm: str,
    minimum_improvement: float,
) -> dict[str, Any]:
    failures: list[str] = []
    comparisons: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    for context in PAIRWISE_CONTEXTS:
        baseline = _records_for_arm_context(records, baseline_arm, context)
        candidate = _records_for_arm_context(records, candidate_arm, context)
        if not baseline or not candidate:
            failures.append(f"missing_{context}")
            continue
        baseline_signatures = {_comparison_signature(record) for record in baseline}
        candidate_signatures = {_comparison_signature(record) for record in candidate}
        if baseline_signatures != candidate_signatures or len(baseline_signatures) != 1:
            failures.append("incompatible_comparison")
            continue
        baseline_ttft = _median(baseline, "ttft_ms")
        candidate_ttft = _median(candidate, "ttft_ms")
        improvement = 0.0 if baseline_ttft <= 0 else 1 - candidate_ttft / baseline_ttft
        comparisons.append(
            {
                "context": context,
                "baseline_ttft_ms": baseline_ttft,
                "candidate_ttft_ms": candidate_ttft,
                "baseline_e2e_ms": _median(baseline, "e2e_ms"),
                "candidate_e2e_ms": _median(candidate, "e2e_ms"),
                "ttft_improvement": improvement,
            }
        )
        if improvement + 1e-9 < minimum_improvement:
            failures.append(f"ttft_{context}")
        candidate_records.extend(candidate)
    failures.extend(_functional_failures(candidate_records))
    return {
        "candidate": candidate_arm,
        "baseline": baseline_arm,
        "comparisons": comparisons,
        "failures": _unique(failures),
    }


def evaluate_specprefill(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    evaluations: dict[str, dict[str, Any]] = {}
    for arm in ("M", "N"):
        evaluation = _pairwise_result(records, "L", arm, 0.20)
        if not _tool_loop_passed(records, arm):
            evaluation["failures"] = _unique(evaluation["failures"] + ["tool_loop"])
        evaluation["status"] = "PASS" if not evaluation["failures"] else "FAIL"
        evaluation["advance_to_65k"] = False
        evaluations[arm] = evaluation
    passing = [
        evaluation
        for evaluation in evaluations.values()
        if evaluation["status"] == "PASS"
    ]
    if passing:
        best = max(
            passing,
            key=lambda evaluation: statistics.mean(
                comparison["ttft_improvement"]
                for comparison in evaluation["comparisons"]
            ),
        )
        best["advance_to_65k"] = True
    return evaluations


def evaluate_ane(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    evaluation = _pairwise_result(records, "J", "O", 0.05)
    candidate_records = [record for record in records if record.get("arm") == "O"]
    if any(record.get("specprefill_enabled") for record in candidate_records):
        evaluation["failures"] = _unique(
            evaluation["failures"] + ["confounded_specprefill"]
        )
    compiled_layers = sum(
        int(record.get(field) or 0)
        for record in candidate_records
        for field in ("ane_compiled_mlp_layers", "ane_compiled_gdn_layers")
    )
    operations = sum(
        int(record.get("ane_executed_operations") or 0)
        for record in candidate_records
    )
    if compiled_layers == 0 or operations == 0:
        status = "INCONCLUSIVE"
    elif evaluation["failures"]:
        status = "FAIL"
    else:
        status = "PASS"
    return {"O": {**evaluation, "status": status, "ane_operations": operations}}


def evaluate_arms(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        arm = record.get("arm")
        if isinstance(arm, str):
            grouped[arm].append(record)

    evaluations: dict[str, dict[str, Any]] = {}
    for arm, arm_records in sorted(grouped.items()):
        failures = _unique(
            failure
            for record in arm_records
            for failure in gate_record(record)
        )
        contexts = {
            int(record["context_target"])
            for record in arm_records
            if record.get("context_target") is not None
        }
        scenarios = {
            str(record["scenario"])
            for record in arm_records
            if record.get("scenario") is not None
        }
        tool_verdict = any(
            record.get("record_type") == "verdict" and record.get("correct")
            for record in arm_records
        )
        first = arm_records[0]
        evaluations[arm] = {
            "arm": arm,
            "runtime": first.get("runtime"),
            "model_id": first.get("model_id"),
            "port": ARM_PORTS.get(arm),
            "passed": not failures,
            "complete": (
                REQUIRED_CONTEXTS.issubset(contexts)
                and REQUIRED_SCENARIOS.issubset(scenarios)
                and tool_verdict
            ),
            "failures": failures,
            "contexts": sorted(contexts),
            "scenarios": sorted(scenarios),
            "tool_verdict": tool_verdict,
            "records": len(arm_records),
        }
    return evaluations


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            records.append(record)
    return records


def _median(records: list[dict[str, Any]], field: str) -> float:
    values = [float(record[field]) for record in records if record.get(field) is not None]
    return statistics.median(values) if values else 0.0


def _summary_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        scenario = record.get("scenario") or record.get("record_type") or "unknown"
        key = (
            record.get("runtime"),
            record.get("arm"),
            record.get("context_target"),
            scenario,
        )
        groups[key].append(record)

    rows: list[dict[str, Any]] = []
    for key, group in sorted(groups.items(), key=lambda item: str(item[0])):
        runtime, arm, context, scenario = key
        failures = sum(bool(gate_record(record)) for record in group)
        rows.append(
            {
                "runtime": runtime,
                "arm": arm,
                "context": context,
                "scenario": scenario,
                "count": len(group),
                "ttft_median_ms": _median(group, "ttft_ms"),
                "e2e_median_ms": _median(group, "e2e_ms"),
                "cache_hit_median": _median(group, "cache_hit_ratio"),
                "failures": failures,
            }
        )
    return rows


def _write_summary(
    path: Path,
    records: list[dict[str, Any]],
    evaluations: dict[str, dict[str, Any]],
    specprefill: dict[str, dict[str, Any]],
    ane: dict[str, dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Qwen3.8 prefix-cache campaign summary",
        "",
        f"> Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Runtime gates",
        "",
        "| Arm | Runtime | Records | Status | Complete | Failures |",
        "|---|---|---:|---|---|---|",
    ]
    for arm, evaluation in evaluations.items():
        status = "PASS" if evaluation["passed"] else "FAIL"
        complete = "yes" if evaluation["complete"] else "no"
        failures = ", ".join(evaluation["failures"]) or "—"
        lines.append(
            f"| {arm} | {evaluation['runtime']} | {evaluation['records']} | "
            f"{status} | {complete} | {failures} |"
        )

    lines.extend(
        [
            "",
            "## Measurements",
            "",
            "| Runtime | Arm | Context | Scenario | N | TTFT median ms | E2E median ms | Cache hit median | Failed records |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in _summary_rows(records):
        context = row["context"] if row["context"] is not None else "—"
        lines.append(
            f"| {row['runtime']} | {row['arm']} | {context} | {row['scenario']} | "
            f"{row['count']} | {row['ttft_median_ms']:.2f} | "
            f"{row['e2e_median_ms']:.2f} | {row['cache_hit_median']:.4f} | "
            f"{row['failures']} |"
        )
    lines.extend(
        [
            "",
            "## SpecPrefill gate",
            "",
            "| Arm | Baseline | Status | Advance to 65K | Failures |",
            "|---|---|---|---|---|",
        ]
    )
    for arm, evaluation in specprefill.items():
        lines.append(
            f"| {arm} | {evaluation['baseline']} | {evaluation['status']} | "
            f"{'yes' if evaluation['advance_to_65k'] else 'no'} | "
            f"{', '.join(evaluation['failures']) or '—'} |"
        )
    ane_evaluation = ane["O"]
    lines.extend(
        [
            "",
            "## ANE prefill gate",
            "",
            "| Arm | Baseline | Status | Confirmed operations | Failures |",
            "|---|---|---|---:|---|",
            f"| O | {ane_evaluation['baseline']} | {ane_evaluation['status']} | "
            f"{ane_evaluation['ane_operations']} | "
            f"{', '.join(ane_evaluation['failures']) or '—'} |",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    campaign = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Summarize Qwen3.8 cache gates.")
    parser.add_argument(
        "--cache-results",
        type=Path,
        default=campaign / "results" / "cache-probe.jsonl",
    )
    parser.add_argument(
        "--tool-results",
        type=Path,
        default=campaign / "results" / "tool-loop.jsonl",
    )
    parser.add_argument(
        "--summary", type=Path, default=campaign / "results" / "summary.md"
    )
    parser.add_argument(
        "--survivors",
        type=Path,
        default=campaign / "results" / "runtime-survivors.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    records = _load_jsonl(args.cache_results) + _load_jsonl(args.tool_results)
    evaluations = evaluate_arms(records)
    specprefill = evaluate_specprefill(records)
    ane = evaluate_ane(records)
    _write_summary(args.summary, records, evaluations, specprefill, ane)

    survivors = [
        evaluation
        for arm, evaluation in evaluations.items()
        if arm in PRODUCTION_ARMS and evaluation["passed"]
    ]
    payload = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "survivors": survivors,
    }
    args.survivors.parent.mkdir(parents=True, exist_ok=True)
    args.survivors.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if survivors else 2


if __name__ == "__main__":
    raise SystemExit(main())
