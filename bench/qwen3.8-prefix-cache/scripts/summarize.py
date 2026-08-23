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
REQUIRED_REPETITIONS = {1, 2, 3}
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
CONTROL_GROUP_FIELDS = tuple(
    field for field in PAIRING_FIELDS if field != "prompt_identity"
)
SPECPREFILL_PROFILES = {
    "M": ("Qwen/Qwen3.5-2B", "15852e8c16360a2fea060d615a32b45270f8a8fc", 0.40),
    "N": ("Qwen/Qwen3.5-0.8B", "2fc06364715b967f1860aea9cf38778875588b17", 0.50),
}
SPECULATIVE_ARMS = ("R", "S")
SPECULATIVE_CONTEXTS = (8192, 32768)
SPECULATIVE_CLASSES = ("code", "math", "chat", "tool_call_json")
SPECULATIVE_SCENARIOS = (
    "cold", "identical", "append", "middle_mutation", "tool_turn"
)
SPECULATIVE_TELEMETRY = (
    "drafter_id",
    "drafter_revision",
    "draft_cap_resolved",
    "accept_length",
    "verification_steps",
)
SPECULATIVE_SAMPLING = {
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "repetition_penalty": 1.0,
    "reasoning_effort": "xhigh",
}


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


def _control_group_signature(record: dict[str, Any]) -> tuple[Any, ...]:
    """Return the stable comparison controls, excluding per-repeat prompt text."""
    return tuple(record.get(field) for field in CONTROL_GROUP_FIELDS)


def _pairing_metadata_present(record: dict[str, Any]) -> bool:
    if any(record.get(field) is None for field in PAIRING_FIELDS):
        return False
    return isinstance(record.get("prompt_tokens"), int) and record["prompt_tokens"] > 0


def _repeat_pairing_failure(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> Optional[str]:
    """Validate the campaign's exact r1/r2/r3 evidence within one control group."""
    def by_repeat(records: list[dict[str, Any]]) -> Optional[dict[int, dict[str, Any]]]:
        grouped: dict[int, dict[str, Any]] = {}
        for record in records:
            repeat = record.get("repeat")
            if not isinstance(repeat, int) or repeat not in REQUIRED_REPETITIONS:
                return None
            if repeat in grouped:
                return None
            grouped[repeat] = record
        return grouped if set(grouped) == REQUIRED_REPETITIONS else None

    baseline_by_repeat = by_repeat(baseline)
    candidate_by_repeat = by_repeat(candidate)
    if baseline_by_repeat is None or candidate_by_repeat is None:
        return "repetitions"
    identities: list[str] = []
    for repeat in sorted(REQUIRED_REPETITIONS):
        baseline_identity = baseline_by_repeat[repeat].get("prompt_identity")
        candidate_identity = candidate_by_repeat[repeat].get("prompt_identity")
        if not isinstance(baseline_identity, str) or not baseline_identity:
            return "prompt_identity"
        if baseline_identity != candidate_identity:
            return "prompt_identity"
        identities.append(baseline_identity)
    return None if len(set(identities)) == len(REQUIRED_REPETITIONS) else "prompt_identity"


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
        and record.get("specprefill_draft_model") == profile.get("specprefill_draft_model")
        and record.get("specprefill_draft_revision") == profile.get("specprefill_draft_revision")
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
    contexts: tuple[int, ...] = PAIRWISE_CONTEXTS,
) -> dict[str, Any]:
    failures: list[str] = []
    comparisons: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    baseline_records: list[dict[str, Any]] = []
    candidate_by_context: dict[int, list[dict[str, Any]]] = {}
    for context in contexts:
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
            baseline_groups[_control_group_signature(record)].append(record)
        for record in candidate:
            candidate_groups[_control_group_signature(record)].append(record)
        if baseline_groups.keys() != candidate_groups.keys():
            failures.append("incompatible_comparison")
            continue
        pairing_failure = None
        for key in baseline_groups:
            pairing_failure = _repeat_pairing_failure(
                baseline_groups[key], candidate_groups[key]
            )
            if pairing_failure is not None:
                break
        if pairing_failure is not None:
            failures.append(pairing_failure)
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
        baseline_records.extend(baseline)
        candidate_by_context[context] = candidate
    failures.extend(_functional_failures(baseline_records + candidate_records))
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
        expected_draft_model, expected_draft_revision, expected_keep_pct = SPECPREFILL_PROFILES[arm]
        if not all(
            record.get("specprefill_enabled") is True
            and record.get("specprefill_keep_pct") == expected_keep_pct
            and record.get("specprefill_threshold") == 8192
            and record.get("specprefill_draft_model") == expected_draft_model
            and record.get("specprefill_draft_revision") == expected_draft_revision
            for record in candidate_records
        ):
            evaluation["failures"] = _unique(evaluation["failures"] + ["profile"])
        cold_sparse = [
            record for record in candidate_records if record.get("scenario") == "cold"
        ]
        warm_cached = [
            record for record in candidate_records
            if record.get("static_prefix_correct") is True
        ]
        if (
            not cold_sparse
            or not warm_cached
            or not all(record.get("prompt_work_mode") == "sparse" for record in cold_sparse)
            or not all(record.get("prompt_work_mode") == "cached" for record in warm_cached)
        ):
            evaluation["failures"] = _unique(evaluation["failures"] + ["prompt_work_mode"])
        if not all(
            isinstance(record.get("needle_verdicts"), dict)
            and all(record["needle_verdicts"].get(position) is True for position in ("10", "50", "90"))
            for record in candidate_records
        ):
            evaluation["failures"] = _unique(evaluation["failures"] + ["needle_evidence"])
        static_evidence = {
            context: any(
                record.get("static_prefix_correct") is True
                and record.get("static_prefix_prior_match") is True
                and record.get("prompt_work_mode") == "cached"
                and isinstance(record.get("static_prefix_boundary_tokens"), int)
                and record["static_prefix_boundary_tokens"] > 0
                and isinstance(record.get("static_prefix_cached_tokens"), (int, float))
                and record["static_prefix_cached_tokens"] >= record["static_prefix_boundary_tokens"]
                for record in context_records
            )
            for context, context_records in evaluation["candidate_by_context"].items()
        }
        if set(static_evidence) != set(PAIRWISE_CONTEXTS) or not all(static_evidence.values()):
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
    log_evidence = [
        record
        for record in active_records
        if record.get("ane_runtime_log_arm") == "O"
        and record.get("ane_runtime_log_session_id") == record.get("session_id")
        and record.get("ane_runtime_log_context") == record.get("context_target")
        and isinstance(record.get("ane_runtime_log_compiled_programs"), (int, float))
        and record["ane_runtime_log_compiled_programs"] > 0
        and isinstance(record.get("ane_runtime_log_executed_operations"), (int, float))
        and record["ane_runtime_log_executed_operations"] > 0
    ]
    if len(log_evidence) != len(active_records):
        evaluation["failures"] = _unique(evaluation["failures"] + ["ane_runtime_log"])
    compiled_layers = sum(
        int(record.get(field) or 0)
        for record in active_records
        for field in ("ane_compiled_mlp_layers", "ane_compiled_gdn_layers")
    )
    operations = sum(
        int(record.get("ane_executed_operations") or 0)
        for record in active_records
    )
    if compiled_layers == 0 or operations == 0 or len(log_evidence) != len(active_records):
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
    comparison = _pairwise_result(records, "K", "L", None, contexts=(32768,))
    baseline = _records_for_arm_context(records, "K", 32768)
    evidence = _records_for_arm_context(records, "L", 32768)
    failures = list(comparison["failures"])
    code_records = baseline + evidence
    expected_results = {
        record.get("code_result_expected") for record in code_records
        if isinstance(record.get("code_result_expected"), int)
        and not isinstance(record.get("code_result_expected"), bool)
    }
    observed_results = {
        record.get("code_result_value") for record in code_records
        if isinstance(record.get("code_result_value"), int)
        and not isinstance(record.get("code_result_value"), bool)
    }
    if (
        not code_records
        or not all(record.get("code_result_verdict") is True for record in code_records)
        or len(expected_results) != 1
        or len(observed_results) != 1
        or expected_results != observed_results
    ):
        failures.append("code_result")
    if not evidence or not all(
        record.get("content_class") == "code"
        and record.get("mtp_enabled") is True
        and record.get("specprefill_enabled") is False
        and isinstance(record.get("mtp_acceptance"), (int, float))
        and record["mtp_acceptance"] > 0
        for record in evidence
    ):
        failures.append("mtp_evidence")
    if not comparison["comparisons"] or comparison["comparisons"][0]["candidate_e2e_ms"] >= comparison["comparisons"][0]["baseline_e2e_ms"]:
        failures.append("e2e")
    if not baseline or _median(evidence, "cache_hit_ratio") + 1e-9 < _median(baseline, "cache_hit_ratio"):
        failures.append("cache_hit_ratio")
    if not _tool_loop_passed(records, "L", evidence[0] if evidence else {}):
        failures.append("tool_loop")
    return {
        "schema_version": 3,
        "arm": "L",
        "passed": not _unique(failures),
        "records": len(evidence),
        "failures": _unique(failures),
    }


def evaluate_arms(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        arm = record.get("arm")
        if isinstance(arm, str):
            grouped[arm].append(record)

    evaluations: dict[str, dict[str, Any]] = {}
    for arm, arm_records in sorted(grouped.items()):
        probe_records = [
            record
            for record in arm_records
            if record.get("record_type") not in {"tool_turn", "verdict"}
        ]
        if not probe_records:
            continue
        failures = _unique(
            failure
            for record in probe_records
            for failure in gate_record(record)
        )
        contexts = {
            int(record["context_target"])
            for record in probe_records
            if record.get("context_target") is not None
        }
        scenarios = {
            str(record["scenario"])
            for record in probe_records
            if record.get("scenario") is not None
        }
        tool_verdict = any(
            record.get("record_type") == "verdict" and record.get("correct")
            for record in arm_records
        )
        first = probe_records[0]
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
            "records": len(probe_records),
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


def _speculative_pair_key(record: dict[str, Any]) -> tuple[Any, ...]:
    """All controls that must be exact when comparing Q to a speculative arm."""
    return tuple(record.get(field) for field in PAIRING_FIELDS) + (record.get("repeat"),)


def _token_equivalent(baseline: dict[str, Any], candidate: dict[str, Any]) -> bool:
    baseline_hash = baseline.get("greedy_tokens_hash")
    candidate_hash = candidate.get("greedy_tokens_hash")
    if isinstance(baseline_hash, str) and baseline_hash and baseline_hash == candidate_hash:
        return True
    return bool(
        baseline.get("logit_tie_evidence")
        and candidate.get("logit_tie_evidence")
        and baseline.get("correct")
        and candidate.get("correct")
    )


def _speculative_sampling_matches(
    record: dict[str, Any], temperature: float
) -> bool:
    return record.get("temperature") == temperature and all(
        record.get(field) == value for field, value in SPECULATIVE_SAMPLING.items()
    )


def _candidate_speculative_pairs(
    records: list[dict[str, Any]],
    candidate: str,
    baseline_arm: str,
    *,
    temperature: float,
    content_classes: tuple[str, ...],
    repetitions: set[int],
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[str]]:
    baseline = {
        _speculative_pair_key(record): record
        for record in records
        if record.get("arm") == baseline_arm
        and record.get("record_type") != "verdict"
        and record.get("context_target") in SPECULATIVE_CONTEXTS
        and record.get("content_class") in content_classes
        and record.get("repeat") in repetitions
        and _speculative_sampling_matches(record, temperature)
    }
    candidates = {
        _speculative_pair_key(record): record
        for record in records
        if record.get("arm") == candidate
        and record.get("record_type") != "verdict"
        and record.get("context_target") in SPECULATIVE_CONTEXTS
        and record.get("content_class") in content_classes
        and record.get("repeat") in repetitions
        and _speculative_sampling_matches(record, temperature)
    }
    if not baseline or not candidates:
        return [], ["pairs"]
    missing = sorted(set(baseline) ^ set(candidates), key=str)
    if missing:
        return [], ["pairs"]
    pairs = [(baseline[key], candidates[key]) for key in sorted(baseline, key=str)]
    expected = {
        (context, content_class, scenario, repeat)
        for context in SPECULATIVE_CONTEXTS
        for content_class in content_classes
        for scenario in SPECULATIVE_SCENARIOS
        for repeat in repetitions
    }
    observed = {
        (
            int(base["context_target"]),
            str(base["content_class"]),
            str(base["scenario"]),
            int(base["repeat"]),
        )
        for base, _ in pairs
    }
    return pairs, ([] if observed == expected else ["pairs"])


def evaluate_speculative_decode(
    records: list[dict[str, Any]], baseline_arm: str = "Q"
) -> dict[str, Any]:
    """Apply Gate 8 without inventing a metric when a pair is absent."""
    result: dict[str, Any] = {}
    passing: list[dict[str, Any]] = []
    for candidate in SPECULATIVE_ARMS:
        greedy_pairs, greedy_missing = _candidate_speculative_pairs(
            records,
            candidate,
            baseline_arm,
            temperature=0,
            content_classes=("code",),
            repetitions={1},
        )
        performance_pairs, performance_missing = _candidate_speculative_pairs(
            records,
            candidate,
            baseline_arm,
            temperature=1.0,
            content_classes=SPECULATIVE_CLASSES,
            repetitions=REQUIRED_REPETITIONS,
        )
        inconclusive: list[str] = []
        if greedy_missing:
            inconclusive.append("greedy_pairs")
        if performance_missing:
            inconclusive.append("performance_pairs")
        failures: list[str] = []
        if greedy_pairs:
            for baseline, speculative in greedy_pairs:
                if not _token_equivalent(baseline, speculative):
                    failures.append("token_equivalence")
                if not baseline.get("correct") or not speculative.get("correct"):
                    failures.append("correct")
        if performance_pairs:
            for baseline, speculative in performance_pairs:
                if not baseline.get("correct") or not speculative.get("correct"):
                    failures.append("correct")
                if any(speculative.get(field) is None for field in SPECULATIVE_TELEMETRY):
                    inconclusive.append("telemetry")
                if baseline.get("decode_tps") in (None, 0) or speculative.get("decode_tps") is None:
                    inconclusive.append("decode_tps")
                if baseline.get("e2e_ms") in (None, 0) or speculative.get("e2e_ms") is None:
                    inconclusive.append("warm_total")
                if baseline.get("cache_hit_ratio") is None or speculative.get("cache_hit_ratio") is None:
                    inconclusive.append("cache_hit")
                if baseline.get("ttft_ms") is None or speculative.get("ttft_ms") is None:
                    inconclusive.append("warm_ttft")
        tool_ok = any(
            record.get("arm") == candidate
            and record.get("record_type") == "verdict"
            and record.get("turns_requested") == 20
            and record.get("correct")
            and _speculative_sampling_matches(record, 1.0)
            for record in records
        )
        if not tool_ok:
            inconclusive.append("tool_loop")
        if inconclusive:
            result[candidate] = {
                "arm": candidate, "baseline": baseline_arm, "status": "INCONCLUSIVE",
                "failures": _unique(inconclusive), "median_decode_speedup": {},
                "greedy_pair_count": len(greedy_pairs),
                "performance_pair_count": len(performance_pairs),
            }
            continue
        by_context: dict[int, list[float]] = defaultdict(list)
        by_class: dict[str, list[float]] = defaultdict(list)
        warm_speedups: list[float] = []
        cache_regressions: list[bool] = []
        ttft_regressions: list[bool] = []
        for baseline, speculative in performance_pairs:
            speedup = float(speculative["decode_tps"]) / float(baseline["decode_tps"])
            by_context[int(baseline["context_target"])].append(speedup)
            by_class[str(baseline["content_class"])].append(speedup)
            if baseline["scenario"] == "identical":
                warm_speedups.append(float(baseline["e2e_ms"]) / float(speculative["e2e_ms"]))
                cache_regressions.append(float(speculative["cache_hit_ratio"]) < float(baseline["cache_hit_ratio"]))
                ttft_regressions.append(float(speculative["ttft_ms"]) > float(baseline["ttft_ms"]) * 1.10)
        medians = {str(context): statistics.median(values) for context, values in by_context.items()}
        class_speedups = {name: statistics.median(values) for name, values in by_class.items()}
        if medians.get("8192", 0.0) < 1.25:
            failures.append("decode_8k")
        if medians.get("32768", 0.0) < 1.15:
            failures.append("decode_32k")
        if sum(value > 1.0 for value in class_speedups.values()) < 3:
            failures.append("class_gain")
        if any(value < 0.95 for value in class_speedups.values()):
            failures.append("class_regression")
        if not warm_speedups:
            inconclusive.append("warm_pairs")
        elif statistics.median(warm_speedups) < (1 / 0.90):
            failures.append("warm_total")
        if any(cache_regressions):
            failures.append("cache_hit")
        if any(ttft_regressions):
            failures.append("warm_ttft")
        if inconclusive:
            status = "INCONCLUSIVE"
            failures = _unique(inconclusive)
        else:
            status = "PASS" if not _unique(failures) else "FAIL"
            failures = _unique(failures)
        evaluation = {
            "arm": candidate, "baseline": baseline_arm, "status": status,
            "failures": failures, "median_decode_speedup": medians,
            "class_speedups": class_speedups,
            "warm_total_speedup": statistics.median(warm_speedups) if warm_speedups else None,
            "greedy_pair_count": len(greedy_pairs),
            "performance_pair_count": len(performance_pairs),
        }
        result[candidate] = evaluation
        if status == "PASS":
            passing.append(evaluation)
    winner = None
    if passing:
        winner = min(
            passing,
            key=lambda item: (-float(item["warm_total_speedup"]), -float(item["median_decode_speedup"]["32768"])),
        )
    result["winner"] = {"arm": winner["arm"] if winner else baseline_arm, "selected": winner is not None}
    return result


def _summary_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("record_type") in {"tool_turn", "verdict"}:
            continue
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
    speculative: dict[str, Any],
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
    lines.extend(
        [
            "",
            "## mlx-dspark Gate 8",
            "",
            "| Arm | Status | 8K decode | 32K decode | 32K warm total | Failures |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for arm in SPECULATIVE_ARMS:
        evaluation = speculative.get(arm, {})
        decode = evaluation.get("median_decode_speedup", {})
        warm = evaluation.get("warm_total_speedup")
        lines.append(
            f"| {arm} | {evaluation.get('status', 'INCONCLUSIVE')} | "
            f"{decode.get('8192', 0.0):.3f} | {decode.get('32768', 0.0):.3f} | "
            f"{warm if warm is not None else '—'} | "
            f"{', '.join(evaluation.get('failures', [])) or '—'} |"
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
    parser.add_argument(
        "--dspark-selection",
        type=Path,
        default=campaign / "results" / "mlx-dspark-selection.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    records = _load_jsonl(args.cache_results) + _load_jsonl(args.tool_results)
    evaluations = evaluate_arms(records)
    specprefill = evaluate_specprefill(records)
    ane = evaluate_ane(records)
    speculative = evaluate_speculative_decode(records)
    _write_summary(args.summary, records, evaluations, specprefill, ane, speculative)

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
    args.dspark_selection.parent.mkdir(parents=True, exist_ok=True)
    args.dspark_selection.write_text(
        json.dumps(speculative, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if survivors else 2


if __name__ == "__main__":
    raise SystemExit(main())
