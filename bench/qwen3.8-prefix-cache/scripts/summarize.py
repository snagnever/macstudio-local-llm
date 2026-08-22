#!/usr/bin/env python3
import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


PRODUCTION_ARMS = {"C", "E", "F", "G", "H"}
ARM_PORTS = {"C": 11234, "E": 8080, "F": 8080, "G": 8080, "H": 8080}
REQUIRED_CONTEXTS = {32768, 65536}
REQUIRED_SCENARIOS = {"identical", "append", "middle_mutation", "tool_turn"}
PAIRWISE_CONTEXTS = (16384, 32768)
PAIRING_FIELDS = (
    "runtime",
    "runtime_revision",
    "model_id",
    "model_revision",
    "quant",
    "context_target",
    "scenario",
    "content_class",
    "prompt_identity",
    "fixture_token_hash",
    "prompt_tokens",
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "presence_penalty",
    "frequency_penalty",
    "repetition_penalty",
    "reasoning_effort",
    "max_tokens",
    "concurrency",
    "warmup_id",
)


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
    swap_delta = record.get("swap_delta_gb")
    if swap_delta is None:
        failures.append("swap_delta_gb_unavailable")
    elif swap_delta > 0.5:
        failures.append("swap_delta_gb")
    ram_peak = record.get("ram_peak_gb")
    if ram_peak is None:
        failures.append("ram_peak_gb_unavailable")
    elif ram_peak > 80.0:
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
    return tuple(record.get(field) for field in PAIRING_FIELDS)


def _pairing_metadata_present(record: dict[str, Any]) -> bool:
    if any(record.get(field) is None for field in PAIRING_FIELDS):
        return False
    return isinstance(record.get("prompt_tokens"), int) and record["prompt_tokens"] > 0


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
    return failures


def _tool_loop_passed(
    records: list[dict[str, Any]], arm: str, profile: dict[str, Any]
) -> bool:
    verdicts = [
        record
        for record in records
        if record.get("arm") == arm
        and record.get("record_type") == "verdict"
        and record.get("specprefill_enabled") == profile.get("specprefill_enabled")
        and record.get("specprefill_keep_pct") == profile.get("specprefill_keep_pct")
        and record.get("specprefill_threshold") == profile.get("specprefill_threshold")
        and record.get("mtp_enabled") == profile.get("mtp_enabled")
        and record.get("runtime_revision") == profile.get("runtime_revision")
        and record.get("model_id") == profile.get("model_id")
        and record.get("model_revision") == profile.get("model_revision")
    ]
    return any(
        record.get("correct") and int(record.get("turns_requested") or 0) >= 20
        for record in verdicts
    )


def _pairwise_result(
    records: list[dict[str, Any]],
    baseline_arm: str,
    candidate_arm: str,
    minimum_improvement: Optional[float],
) -> dict[str, Any]:
    failures: list[str] = []
    comparisons: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    candidate_by_context: dict[int, list[dict[str, Any]]] = {}
    for context in PAIRWISE_CONTEXTS:
        baseline = _records_for_arm_context(records, baseline_arm, context)
        candidate = _records_for_arm_context(records, candidate_arm, context)
        if not baseline or not candidate:
            failures.append(f"missing_{context}")
            continue
        if not all(_pairing_metadata_present(record) for record in baseline + candidate):
            failures.append("missing_pairing_metadata")
            continue
        baseline_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        candidate_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for record in baseline:
            baseline_groups[_comparison_signature(record)].append(record)
        for record in candidate:
            candidate_groups[_comparison_signature(record)].append(record)
        if baseline_groups.keys() != candidate_groups.keys():
            failures.append("incompatible_comparison")
            continue
        baseline_ttft = statistics.median(
            _median(group, "ttft_ms") for group in baseline_groups.values()
        )
        candidate_ttft = statistics.median(
            _median(candidate_groups[key], "ttft_ms") for key in baseline_groups
        )
        improvement = 0.0 if baseline_ttft <= 0 else 1 - candidate_ttft / baseline_ttft
        comparisons.append(
            {
                "context": context,
                "baseline_ttft_ms": baseline_ttft,
                "candidate_ttft_ms": candidate_ttft,
                "baseline_e2e_ms": statistics.median(
                    _median(group, "e2e_ms") for group in baseline_groups.values()
                ),
                "candidate_e2e_ms": statistics.median(
                    _median(candidate_groups[key], "e2e_ms") for key in baseline_groups
                ),
                "ttft_improvement": improvement,
            }
        )
        if minimum_improvement is not None and improvement + 1e-9 < minimum_improvement:
            failures.append(f"ttft_{context}")
        candidate_records.extend(candidate)
        candidate_by_context[context] = candidate
    failures.extend(_functional_failures(candidate_records))
    return {
        "candidate": candidate_arm,
        "baseline": baseline_arm,
        "comparisons": comparisons,
        "failures": _unique(failures),
        "candidate_by_context": candidate_by_context,
    }


def evaluate_specprefill(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    evaluations: dict[str, dict[str, Any]] = {}
    for arm in ("M", "N"):
        evaluation = _pairwise_result(records, "L", arm, 0.20)
        candidate_records = [
            record
            for context_records in evaluation["candidate_by_context"].values()
            for record in context_records
        ]
        if not all(
            isinstance(record.get("needle_verdicts"), dict)
            and all(record["needle_verdicts"].get(position) is True for position in ("10", "50", "90"))
            for record in candidate_records
        ):
            evaluation["failures"] = _unique(evaluation["failures"] + ["needle_evidence"])
        if not any(record.get("static_prefix_correct") is True for record in candidate_records):
            evaluation["failures"] = _unique(evaluation["failures"] + ["static_prefix"])
        profile = candidate_records[0] if candidate_records else {}
        if not _tool_loop_passed(records, arm, profile):
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
    evaluation = _pairwise_result(records, "J", "O", None)
    candidate_records = [
        record
        for context_records in evaluation["candidate_by_context"].values()
        for record in context_records
    ]
    baseline_records = [
        record
        for context in PAIRWISE_CONTEXTS
        for record in _records_for_arm_context(records, "J", context)
    ]
    if any(record.get("specprefill_enabled") is not False for record in candidate_records + baseline_records):
        evaluation["failures"] = _unique(
            evaluation["failures"] + ["confounded_specprefill"]
        )
    gain_contexts = [
        comparison["context"]
        for comparison in evaluation["comparisons"]
        if comparison["ttft_improvement"] + 1e-9 >= 0.05
    ]
    if not gain_contexts:
        evaluation["failures"] = _unique(evaluation["failures"] + ["ttft"])
    active_records = [
        record
        for context in gain_contexts
        for record in evaluation["candidate_by_context"].get(context, [])
    ]
    if active_records and not all(record.get("ane_prefill_enabled") is True for record in active_records):
        evaluation["failures"] = _unique(evaluation["failures"] + ["ane_not_enabled"])
    compiled_layers = sum(
        int(record.get(field) or 0)
        for record in active_records
        for field in ("ane_compiled_mlp_layers", "ane_compiled_gdn_layers")
    )
    operations = sum(
        int(record.get("ane_executed_operations") or 0)
        for record in active_records
    )
    if compiled_layers == 0 or operations == 0:
        status = "INCONCLUSIVE"
    elif evaluation["failures"]:
        status = "FAIL"
    else:
        status = "PASS"
    return {"O": {**evaluation, "status": status, "ane_operations": operations}}


def specprefill_selection(
    evaluations: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    winners = [
        {"arm": arm, **evaluation}
        for arm, evaluation in evaluations.items()
        if evaluation.get("advance_to_65k")
    ]
    return {
        "schema_version": 3,
        "winner": winners[0] if len(winners) == 1 else None,
        "profiles": evaluations,
    }


def omlx_mtp_gate(records: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = [
        record
        for record in records
        if record.get("arm") == "L"
        and record.get("context_target") == 32768
        and record.get("mtp_enabled") is True
        and record.get("specprefill_enabled") is False
    ]
    return {
        "schema_version": 3,
        "arm": "L",
        "passed": bool(evidence) and not any(gate_record(record) for record in evidence),
        "records": len(evidence),
    }


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
    parser.add_argument(
        "--specprefill-selection",
        type=Path,
        default=campaign / "results" / "specprefill-selection.json",
    )
    parser.add_argument(
        "--omlx-mtp-gate",
        type=Path,
        default=campaign / "results" / "omlx-mtp-gate.json",
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
    selection = specprefill_selection(specprefill)
    args.specprefill_selection.parent.mkdir(parents=True, exist_ok=True)
    args.specprefill_selection.write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    mtp_gate = omlx_mtp_gate(records)
    args.omlx_mtp_gate.parent.mkdir(parents=True, exist_ok=True)
    args.omlx_mtp_gate.write_text(
        json.dumps(mtp_gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if survivors else 2


if __name__ == "__main__":
    raise SystemExit(main())
