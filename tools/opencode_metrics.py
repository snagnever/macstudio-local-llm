#!/usr/bin/env python3
"""Extract per-model / per-provider performance metrics from the opencode SQLite DB.

Emits a single metrics.json with per-message rows plus aggregates by
(day, model) and by (model) all-time. Latency metrics (TTFT, prefill) are
proxies: opencode does not record the real first stream token, so the value is
the first text/reasoning part of the first step minus the step-start time.

Usage:
    python3 opencode_metrics.py [--db PATH] [--days N] [--project SUBSTR] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone


def default_db() -> str:
    base = os.environ.get(
        "OPENCODE_DATA_DIR",
        os.path.join(
            os.environ.get(
                "XDG_DATA_HOME", os.path.expanduser("~/.local/share")
            ),
            "opencode",
        ),
    )
    return os.path.join(base, "opencode.db")


def connect_ro(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        sys.exit(f"opencode DB not found: {path}")
    uri = f"file:{path}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def day_of(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def collect_messages(conn: sqlite3.Connection, cutoff_ms: int | None, project: str | None):
    """Return dict message_id -> message fields for completed assistant messages."""
    rows = {}
    sql = "SELECT id, data FROM message WHERE json_extract(data,'$.role')='assistant'"
    for r in conn.execute(sql):
        d = json.loads(r["data"])
        t = d.get("time") or {}
        created, completed = t.get("created"), t.get("completed")
        if not created or not completed:
            continue
        if cutoff_ms and created < cutoff_ms:
            continue
        cwd = (d.get("path") or {}).get("cwd", "")
        if project and project not in cwd:
            continue
        tok = d.get("tokens") or {}
        cache = tok.get("cache") or {}
        rows[r["id"]] = {
            "id": r["id"],
            "model": f"{d.get('providerID')}/{d.get('modelID')}",
            "provider": d.get("providerID"),
            "day": day_of(created),
            "created": created,
            "completed": completed,
            "input": tok.get("input") or 0,
            "output": tok.get("output") or 0,
            "reasoning": tok.get("reasoning") or 0,
            "total": tok.get("total") or 0,
            "cache_read": cache.get("read") or 0,
            "cache_write": cache.get("write") or 0,
            "cost": d.get("cost") or 0.0,
            "cwd": cwd,
        }
    return rows


def first_step_timing(conn: sqlite3.Connection, msg_ids: set[str]):
    """Per message: step_start time, first content start, first step-finish, tool ms."""
    parts = defaultdict(list)
    for r in conn.execute("SELECT message_id, time_created, time_updated, data FROM part"):
        if r["message_id"] not in msg_ids:
            continue
        d = json.loads(r["data"])
        parts[r["message_id"]].append((r["time_created"], r["time_updated"], d))

    timing = {}
    for mid, plist in parts.items():
        plist.sort(key=lambda x: x[0])
        step_start = None
        step_finish = None
        first_tok = None
        tool_ms = 0
        for tc, tu, d in plist:
            typ = d.get("type")
            if typ == "step-start" and step_start is None:
                step_start = tc
            elif typ == "step-finish" and step_start is not None and step_finish is None:
                step_finish = tc
            elif typ in ("text", "reasoning") and step_start is not None and step_finish is None:
                start = (d.get("time") or {}).get("start")
                if start and (first_tok is None or start < first_tok):
                    first_tok = start
            if typ == "tool" and tu and tc:
                tool_ms += max(0, tu - tc)
        timing[mid] = {
            "step_start": step_start,
            "first_tok": first_tok,
            "step_finish": step_finish,
            "tool_ms": tool_ms,
        }
    return timing


def build_rows(messages, timing):
    rows = []
    for mid, m in messages.items():
        t = timing.get(mid, {})
        ss, ft, sf = t.get("step_start"), t.get("first_tok"), t.get("step_finish")
        ttft = (ft - ss) if (ss and ft and ft >= ss) else None
        # Sub-50ms means the provider did not record a real first-token time
        # (remote providers stamp the part start next to step-start). Treat as
        # unknown so TTFT and prefill are not fabricated.
        if ttft is not None and ttft < 50:
            ttft = None
        gen_end = sf or m["completed"]
        gen_ms = (gen_end - ft) if (ft and gen_end and gen_end > ft) else None
        tps = (m["output"] * 1000.0 / gen_ms) if (gen_ms and m["output"]) else None
        prefill = (m["input"] * 1000.0 / ttft) if (ttft and ttft > 0 and m["input"]) else None
        ctx = m["total"] or (m["input"] + m["cache_read"] + m["output"])
        tps_per_kctx = (tps / ctx * 1000) if (tps and ctx) else None
        cache_in = m["input"] + m["cache_read"]
        rows.append({
            "id": mid,
            "model": m["model"],
            "provider": m["provider"],
            "day": m["day"],
            "ttft_ms": ttft,
            "prefill_tps": round(prefill, 1) if prefill else None,
            "tps": round(tps, 2) if tps else None,
            "tps_per_kctx": round(tps_per_kctx, 4) if tps_per_kctx else None,
            "context": ctx,
            "output": m["output"],
            "input": m["input"],
            "reasoning": m["reasoning"],
            "cache_read": m["cache_read"],
            "cache_hit_ratio": round(m["cache_read"] / cache_in, 4) if cache_in else None,
            "reasoning_ratio": round(m["reasoning"] / m["output"], 4) if m["output"] else None,
            "cost": m["cost"],
            "tool_ms": t.get("tool_ms", 0),
        })
    return rows


def _stats(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"median": None, "p90": None, "n": 0}
    vals.sort()
    p90 = vals[min(len(vals) - 1, int(round(0.9 * (len(vals) - 1))))]
    return {"median": round(statistics.median(vals), 3), "p90": round(p90, 3), "n": len(vals)}


def aggregate(rows, keys):
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in keys)].append(r)
    out = []
    for key, grp in groups.items():
        rec = dict(zip(keys, key))
        rec["messages"] = len(grp)
        rec["cost_sum"] = round(sum(r["cost"] for r in grp), 6)
        rec["output_sum"] = sum(r["output"] for r in grp)
        for metric in ("ttft_ms", "tps", "tps_per_kctx", "context", "prefill_tps",
                       "cache_hit_ratio", "reasoning_ratio"):
            rec[metric] = _stats([r[metric] for r in grp])
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=default_db())
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--project", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cutoff = None
    if args.days:
        cutoff = int((datetime.now(tz=timezone.utc).timestamp() - args.days * 86400) * 1000)

    conn = connect_ro(args.db)
    messages = collect_messages(conn, cutoff, args.project)
    timing = first_step_timing(conn, set(messages))
    rows = build_rows(messages, timing)

    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "db": args.db,
        "days": args.days,
        "project": args.project,
        "message_count": len(rows),
        "by_model": sorted(aggregate(rows, ["model"]), key=lambda x: -x["messages"]),
        "by_provider": sorted(aggregate(rows, ["provider"]), key=lambda x: -x["messages"]),
        "by_day_model": aggregate(rows, ["day", "model"]),
        "by_day_provider": aggregate(rows, ["day", "provider"]),
        "rows": rows,
    }
    text = json.dumps(payload, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print(f"wrote {args.out}: {len(rows)} messages, {len(payload['by_model'])} models")
    else:
        print(text)


if __name__ == "__main__":
    main()
