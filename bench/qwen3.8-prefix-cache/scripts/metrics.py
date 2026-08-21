import json
from typing import Any


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
    gpu_usage = sample.get("gpu_usage", [None, 0])
    return {
        "ram_gb": memory.get("ram_usage", 0) / 1e9,
        "swap_gb": memory.get("swap_usage", 0) / 1e9,
        "gpu_pct": float(gpu_usage[1]) * 100 if len(gpu_usage) > 1 else 0.0,
        "power_w": float(sample.get("all_power", 0.0)),
        "gpu_temp_c": float(sample.get("gpu_temp", 0.0)),
    }
