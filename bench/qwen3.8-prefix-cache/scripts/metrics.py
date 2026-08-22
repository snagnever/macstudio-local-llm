import json
from typing import Any


SERVER_MEASUREMENT_FIELDS = (
    "specprefill_draft_model",
    "specprefill_draft_revision",
    "specprefill_selected_tokens",
    "specprefill_scored_tokens",
    "specprefill_draft_ms",
    "specprefill_target_ms",
    "static_prefix_cached_tokens",
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
        if name.split("{")[0].endswith(field):
            return value
    return None


def normalize_server_measurements(
    usage: dict[str, Any], metrics: dict[str, float]
) -> dict[str, Any]:
    """Keep only server-reported values; missing telemetry remains unavailable."""
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
            result[field] = _metric_field(metrics, field)
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
