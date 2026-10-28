"""Export one row per finished Terminal-Bench trial of an arm to results/tbench21-<arm>-tasks.csv.

The harbor job dirs live in the gitignored logs/tbench-runs/; this table keeps reward, phase minutes, tokens and
request counts in git so a later arm (e.g. the base Flash Next) can be paired with these task by task.
usage: export_tbench.py <arm>... [--runs DIR] [--out DIR]
"""
import argparse
import csv
import datetime as dt
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
FIELDS = ["task", "reward", "timeout", "error", "total_min", "env_min", "agent_min", "verifier_min",
          "input_tokens", "cache_tokens", "output_tokens", "episodes", "requests", "median_request_s"]


def _minutes(span):
    if not span or not span.get("started_at") or not span.get("finished_at"):
        return None
    start, end = (dt.datetime.fromisoformat(span[k].replace("Z", "+00:00")) for k in ("started_at", "finished_at"))
    return round((end - start).total_seconds() / 60, 1)


def rows(job):
    out = []
    for f in Path(job).glob("*/result.json"):
        r = json.loads(f.read_text())
        agent = r.get("agent_result") or {}
        meta = agent.get("metadata") or {}
        times = meta.get("api_request_times_msec") or []
        error = (r.get("exception_info") or {}).get("exception_type", "")
        out.append({
            "task": f.parent.name.split("__")[0],
            "reward": ((r.get("verifier_result") or {}).get("rewards") or {}).get("reward") or 0.0,
            "timeout": int(error == "AgentTimeoutError"),
            "error": error,
            "total_min": _minutes(r),
            "env_min": _minutes(r.get("environment_setup")),
            "agent_min": _minutes(r.get("agent_execution")),
            "verifier_min": _minutes(r.get("verifier")),
            "input_tokens": agent.get("n_input_tokens"),
            "cache_tokens": agent.get("n_cache_tokens"),
            "output_tokens": agent.get("n_output_tokens"),
            "episodes": meta.get("n_episodes"),
            "requests": len(times),
            "median_request_s": round(statistics.median(times) / 1000, 1) if times else None,
        })
    return sorted(out, key=lambda row: row["task"])


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("arms", nargs="+")
    p.add_argument("--runs", type=Path, default=HERE / "logs" / "tbench-runs")
    p.add_argument("--out", type=Path, default=HERE / "results")
    a = p.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    for arm in a.arms:
        data = rows(a.runs / f"tb21-{arm}")
        path = a.out / f"tbench21-{arm}-tasks.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(data)
        print(f"{path}: {len(data)} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
