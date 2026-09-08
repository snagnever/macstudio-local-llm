#!/usr/bin/env python3
"""Extract session metrics for one opencode session.

Usage: recover_opencode_stats.py <session_id> [db_path]
Prints a JSON summary. Stdlib only.
"""
import json, sqlite3, sys, os, collections

DEFAULT_DB = os.path.expanduser("~/.local/share/opencode/opencode.db")

def main(argv):
    sid = argv[1]
    db = argv[2] if len(argv) > 2 else DEFAULT_DB
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    row = con.execute(
        "select directory, title, time_created from session where id=?", (sid,)
    ).fetchone()
    if row is None:
        raise SystemExit(f"no session {sid}")
    tok = collections.Counter()
    roles = collections.Counter()
    models, cost, times = set(), 0.0, []
    prompts = []
    for (data,) in con.execute(
        "select data from message where session_id=? order by time_created", (sid,)
    ):
        m = json.loads(data)
        roles[m.get("role")] += 1
        if m.get("modelID"):
            models.add(m["modelID"])
        cost += m.get("cost") or 0
        t = m.get("time") or {}
        if t.get("created"):
            times.append(t["created"])
        if t.get("completed"):
            times.append(t["completed"])
        tk = m.get("tokens") or {}
        for k in ("total", "input", "output", "reasoning"):
            tok[k] += tk.get(k) or 0
        cache = tk.get("cache") or {}
        tok["cache_read"] += cache.get("read") or 0
        tok["cache_write"] += cache.get("write") or 0
    tools = collections.Counter()
    for (data,) in con.execute("select data from part where session_id=?", (sid,)):
        p = json.loads(data)
        if p.get("type") == "tool":
            tools[p.get("tool") or "unknown"] += 1
    print(json.dumps({
        "session": sid, "directory": row[0], "title": row[1],
        "time_created_ms": row[2],
        "first_ms": min(times) if times else None,
        "last_ms": max(times) if times else None,
        "models": sorted(models), "cost": cost,
        "messages_by_role": dict(roles),
        "tokens": dict(tok),
        "tool_calls_by_type": dict(tools),
        "tool_calls_total": sum(tools.values()),
    }, indent=2))

if __name__ == "__main__":
    main(sys.argv)
