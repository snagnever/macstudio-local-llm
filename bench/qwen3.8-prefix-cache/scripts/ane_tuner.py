#!/usr/bin/env python3
"""Run the pinned oMLX ANE tuner and preserve its hardware-local result."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TERMINAL_STATUSES = {"completed", "error", "cancelled"}


def _required(recommendation: dict[str, Any], key: str) -> Any:
    value = recommendation.get(key)
    if value is None:
        raise ValueError(f"ANE tuner recommendation is missing {key}")
    return value


def profile_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("status") != "completed":
        raise ValueError("ANE tuner run is not completed")
    recommendation = snapshot.get("recommendation")
    if not isinstance(recommendation, dict):
        raise ValueError("ANE tuner run has no recommendation")
    if not recommendation.get("enabled"):
        raise ValueError("ANE tuner recommends the GPU-only baseline")

    gdn_enabled = bool(recommendation.get("gdn_enabled"))
    cpu_enabled = bool(recommendation.get("cpu_enabled"))
    profile: dict[str, Any] = {
        "qwen35_ane_prefill_enabled": True,
        "qwen35_ane_prefill_sequence_length": int(
            _required(recommendation, "sequence_length")
        ),
        "qwen35_ane_prefill_fraction": float(
            _required(recommendation, "mlp_fraction")
        ),
        "qwen35_ane_prefill_gdn": gdn_enabled,
        "qwen35_ane_prefill_cpu_enabled": cpu_enabled,
        "qwen35_ane_prefill_cpu_threads": int(
            _required(recommendation, "cpu_threads")
        ),
        "qwen35_ane_prefill_cpu_shared_resource": bool(
            _required(recommendation, "cpu_shared_resource")
        ),
    }
    if gdn_enabled:
        profile["qwen35_ane_prefill_gdn_fraction"] = float(
            _required(recommendation, "gdn_fraction")
        )
    if cpu_enabled:
        for source, target in (
            ("cpu_fraction", "qwen35_ane_prefill_cpu_fraction"),
            ("cpu_down_fraction", "qwen35_ane_prefill_cpu_down_fraction"),
            ("cpu_gdn_fraction", "qwen35_ane_prefill_cpu_gdn_fraction"),
        ):
            profile[target] = float(_required(recommendation, source))
    return profile


def _request_json(
    url: str, *, method: str = "GET", body: dict[str, Any] | None = None
) -> dict[str, Any]:
    encoded = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        url,
        data=encoded,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"oMLX tuner HTTP {error.code}: {detail}") from error
    except (URLError, OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"oMLX tuner request failed: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError("oMLX tuner returned a non-object response")
    return payload


def run_tuner(
    base_url: str,
    model_id: str,
    sequence_length: int,
    repeats: int,
    timeout_seconds: int,
    poll_seconds: float,
) -> dict[str, Any]:
    request_body = {
        "model_id": model_id,
        "sequence_length": sequence_length,
        "repeats": repeats,
        "allow_cpu": True,
        "allow_cpu_gate": True,
        "allow_cpu_down": True,
        "allow_ane_gdn": True,
        "allow_cpu_gdn": True,
        "allow_cpu_shared_resource": True,
    }
    root = base_url.rstrip("/")
    started = _request_json(
        f"{root}/admin/api/bench/ane-tune/start",
        method="POST",
        body=request_body,
    )
    tuning_id = started.get("tuning_id")
    if not isinstance(tuning_id, str) or not tuning_id:
        raise RuntimeError("oMLX tuner did not return a tuning_id")
    deadline = time.monotonic() + timeout_seconds
    while True:
        snapshot = _request_json(
            f"{root}/admin/api/bench/ane-tune/{tuning_id}/results"
        )
        print(
            f"ANE tuner status={snapshot.get('status')} "
            f"phase={snapshot.get('phase')} "
            f"progress={snapshot.get('current')}/{snapshot.get('total')}",
            flush=True,
        )
        if snapshot.get("status") in TERMINAL_STATUSES:
            snapshot["request"] = request_body
            return snapshot
        if time.monotonic() >= deadline:
            raise TimeoutError(f"ANE tuner exceeded {timeout_seconds} seconds")
        time.sleep(poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--runtime-revision", default="v0.6.3rc2")
    parser.add_argument("--sequence-length", type=int, default=2048)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()

    snapshot = run_tuner(
        args.base_url,
        args.model_id,
        args.sequence_length,
        args.repeats,
        args.timeout_seconds,
        args.poll_seconds,
    )
    result = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": "oMLX",
        "runtime_revision": args.runtime_revision,
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "snapshot": snapshot,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if snapshot.get("status") != "completed":
        raise RuntimeError(
            f"ANE tuner ended with {snapshot.get('status')}: {snapshot.get('error')}"
        )
    profile = profile_from_snapshot(snapshot)
    args.profile.parent.mkdir(parents=True, exist_ok=True)
    args.profile.write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"ANE tuner result: {args.result}")
    print(f"ANE profile: {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
