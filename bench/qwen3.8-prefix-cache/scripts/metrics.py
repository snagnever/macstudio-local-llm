import json
import re
from typing import Any, Optional


SERVER_MEASUREMENT_FIELDS = (
    "specprefill_draft_model",
    "specprefill_draft_revision",
    "specprefill_selected_tokens",
    "specprefill_scored_tokens",
    "specprefill_draft_ms",
    "specprefill_target_ms",
    "static_prefix_cached_tokens",
    "static_prefix_boundary_tokens",
    "ane_prefill_tuned",
    "ane_compiled_mlp_layers",
    "ane_compiled_gdn_layers",
    "ane_executed_operations",
    "prompt_work_mode",
    "speculation_mode",
    "drafter_id",
    "drafter_revision",
    "draft_cap_policy",
    "draft_cap_resolved",
    "drafted_tokens",
    "accepted_tokens",
    "accept_length",
    "verification_steps",
    "machine_roofline_tps",
    "decode_roofline_ratio",
)


def _metric_field(metrics: dict[str, float], field: str) -> Any:
    for name, value in metrics.items():
        metric_name = name.split("{")[0]
        if metric_name.endswith(field) or metric_name.endswith(f"{field}_total"):
            return value
    return None


def _metric_delta_field(
    before: dict[str, float], after: dict[str, float], field: str
) -> Any:
    before_value = _metric_field(before, field)
    after_value = _metric_field(after, field)
    if before_value is None or after_value is None:
        return None
    delta = after_value - before_value
    return delta if delta >= 0 else None


def normalize_server_measurements(
    usage: dict[str, Any],
    metrics_before: dict[str, float],
    metrics_after: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """Keep only server-reported values; missing telemetry remains unavailable."""
    if metrics_after is None:
        metrics_after = metrics_before
        metrics_before = {}
    result = {field: None for field in SERVER_MEASUREMENT_FIELDS}
    blocks = [usage]
    for name in ("x_mlx_dspark", "x_omlx", "server_metrics"):
        block = usage.get(name)
        if isinstance(block, dict):
            blocks.insert(0, block)
    for field in SERVER_MEASUREMENT_FIELDS:
        for block in blocks:
            if field in block and block[field] is not None:
                result[field] = block[field]
                break
        if result[field] is None:
            if field == "ane_executed_operations":
                result[field] = _metric_delta_field(
                    metrics_before, metrics_after, field
                )
            else:
                result[field] = _metric_field(metrics_after, field)
    mode = result["prompt_work_mode"]
    if mode not in {"full", "cached", "sparse"}:
        result["prompt_work_mode"] = None
    return result


def parse_prometheus(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, value = line.rsplit(None, 1)
        result[name] = float(value)
    return result


def metric_delta(
    before: dict[str, float], after: dict[str, float]
) -> dict[str, float]:
    keys = before.keys() | after.keys()
    return {
        key: after.get(key, 0.0) - before.get(key, 0.0)
        for key in keys
    }


def parse_ane_runtime_evidence(
    text: str, arm: str, session_id: str, context: int
) -> dict[str, Any]:
    """Bind one v0.6.3rc2 ANE compilation and one MLP profile to this run.

    oMLX emits exactly one eager compilation declaration and one
    ``benchmark-ane-profile`` MLP summary for an isolated ANE benchmark run.
    Anything else is ambiguous: never select a last declaration or aggregate
    profiles that might belong to unrelated work.
    """
    compiled_events = []
    profile_events = []
    unidentifiable_event = False
    compiled_pattern = re.compile(
        r"^Eagerly compiled \d+ MLP and \d+ GDN procedures into (\d+) "
        r"instance-pinned ANE programs \(sequence_length=\d+\)$"
    )
    profile_pattern = re.compile(
        r"^\[benchmark-ane-profile\] category=mlp operations=(\d+) "
        r"configured_layers=\d+(?: observed_shapes=[0-9.]+)?$"
    )
    for raw_line in text.splitlines():
        line = raw_line.strip()
        compiled = compiled_pattern.fullmatch(line)
        if compiled:
            compiled_events.append(int(compiled.group(1)))
        elif "Eagerly compiled" in line and "ANE programs" in line:
            unidentifiable_event = True
        profile = profile_pattern.fullmatch(line)
        if profile:
            profile_events.append(int(profile.group(1)))
        elif "[benchmark-ane-profile]" in line:
            unidentifiable_event = True
    if (
        not unidentifiable_event
        and len(compiled_events) == 1
        and len(profile_events) == 1
    ):
        compiled_programs = compiled_events[0]
        executed_operations = profile_events[0]
    else:
        compiled_programs = None
        executed_operations = None
    return {
        "ane_runtime_log_arm": arm,
        "ane_runtime_log_session_id": session_id,
        "ane_runtime_log_context": context,
        "ane_runtime_log_compiled_programs": compiled_programs,
        "ane_runtime_log_executed_operations": executed_operations,
    }


def parse_macmon(line: str) -> dict[str, Any]:
    sample = json.loads(line)
    memory = sample.get("memory", {})
    temperature = sample.get("temp", {})
    gpu_usage = sample.get("gpu_usage", [None, 0])
    return {
        "ram_gb": memory.get("ram_usage", 0) / 1e9,
        "swap_gb": memory.get("swap_usage", 0) / 1e9,
        "gpu_pct": float(gpu_usage[1]) * 100 if len(gpu_usage) > 1 else 0.0,
        "power_w": float(sample.get("all_power", 0.0)),
        "gpu_temp_c": float(temperature.get("gpu_temp_avg", 0.0)),
    }
