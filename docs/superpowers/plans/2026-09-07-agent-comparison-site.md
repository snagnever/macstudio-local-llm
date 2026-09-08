# Agent Comparison Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish three model comparisons — SVGBench, a new Agent Build-Off, and a new Layout Skill Bench — to GitHub Pages, with every demo runnable in the browser.

**Architecture:** Two new `bench/` campaigns hold recovered metrics and vendored demo *source*. Two new self-contained dashboard pages read those metrics. A GitHub Actions workflow builds the demos with an explicit base path, applies documented publish-time fixes, assembles `reports/` plus the built demos, and pushes to the `gh-pages` branch. The site is in English.

**Tech Stack:** Python 3 stdlib (recovery scripts), Node 22 + npm + Vite (demo builds), Chart.js 4.4.1 via CDN (dashboards), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-07-agent-comparison-site-design.md` (sections 1-7; section 8 is done and shipped).

## Global Constraints

- **All site copy is in English.** Prose in `plan.md`, `results/*.md`, and both dashboard pages.
- **Vendored demo source excludes `node_modules`, `dist` and `.git`.** The site builds it; the repo does not store build output.
- **The artifact stays as the model produced it.** Every fix needed for hosting happens at publish time and is listed in that campaign's `plan.md`. Never edit vendored source to fix a path.
- **Numbers live once, in `results/arms.json`.** Dashboards read from it. A metric not collected is `null` and renders as a gap, never as zero.
- **Every published figure carries its `n`** and states what was not measured.
- **The site is served from `/macstudio-local-llm/`.** Every demo must work under that prefix.
- **Dashboards are self-contained**: no build step, `charts-common.js` loaded as a classic script (not a module — modules break `file://`), data inline. See `reports/README.md`.
- **Recovered numbers are measurements, not estimates.** Where a value cannot be derived, the row says "not recorded" rather than guessing.
- **Commit after every task.**

---

### Task 1: Adopt and independently verify the codex-astra STATS

Codex is writing its own `STATS.md` for `~/LocalProjects/hyper-runner-astra`, the
way the other three arms did. **This replaces the recovery this task originally
planned, and it is the better arrangement**: all four arms then carry a
self-reported record on the same headings, rather than three self-reported and
one reconstructed by a different agent from logs.

What the recovery was going to produce becomes the *check* instead. A
self-reported record cross-checked against the session logs is stronger than
either alone, and the other three arms never got that check.

**Files:**
- Create: `bench/agent-build-off/results/codex-astra.md` (copied from the arm)
- Create: `bench/agent-build-off/scripts/verify_codex_stats.py`

**Interfaces:**
- Produces: a verified `codex-astra.md` on the same headings as the other three
  arms, plus a recorded verdict on whether its self-reported tokens match the logs.

- [ ] **Step 1: Wait for the file, then read it**

```bash
ls -la /Users/vitor/LocalProjects/hyper-runner-astra/STATS.md
```

If it is absent, stop and report that — do not start reconstructing one from
logs in parallel. Two records of the same session, produced by different methods,
is exactly the confusion this task exists to avoid.

- [ ] **Step 2: Write the verification script**

Create `bench/agent-build-off/scripts/verify_codex_stats.py`:

```python
#!/usr/bin/env python3
"""Cross-check a Codex arm's self-reported token totals against its rollout logs.

Usage: verify_codex_stats.py <cwd-to-match> <rollout.jsonl> [...]
Prints the totals the logs support. Stdlib only.
"""
import json, sys, collections

def main(argv):
    want_cwd, files = argv[1], argv[2:]
    sessions, tool_calls, prompts = [], collections.Counter(), 0
    first_ts = last_ts = None
    model = None
    totals = collections.Counter()
    for path in files:
        last_tc = None
        matched = False
        with open(path) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                p = rec.get("payload") or {}
                if rec.get("type") == "session_meta":
                    if p.get("cwd") != want_cwd:
                        break
                    matched = True
                    sessions.append({"id": p.get("session_id"),
                                     "cli_version": p.get("cli_version"),
                                     "started": rec.get("timestamp")})
                if not matched:
                    continue
                ts = rec.get("timestamp")
                if ts:
                    first_ts = ts if first_ts is None or ts < first_ts else first_ts
                    last_ts = ts if last_ts is None or ts > last_ts else last_ts
                if p.get("type") == "token_count":
                    last_tc = p.get("info", {}).get("total_token_usage")
                if p.get("type") in ("custom_tool_call", "function_call"):
                    tool_calls[p.get("name") or p.get("type")] += 1
                if rec.get("type") == "response_item" and p.get("role") == "user":
                    prompts += 1
                m = p.get("model") or (p.get("info") or {}).get("model")
                if m:
                    model = m
        if last_tc:
            # Codex reports cumulative totals per session; sum across sessions.
            for k, v in last_tc.items():
                totals[k] += v
    print(json.dumps({
        "sessions": sessions, "session_count": len(sessions),
        "model": model, "first_timestamp": first_ts, "last_timestamp": last_ts,
        "tokens": dict(totals), "user_prompts": prompts,
        "tool_calls_by_type": dict(tool_calls),
        "tool_calls_total": sum(tool_calls.values()),
    }, indent=2))

if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 3: Run it and compare against the self-reported figures**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
mkdir -p bench/agent-build-off/{scripts,results}
python3 bench/agent-build-off/scripts/verify_codex_stats.py \
  /Users/vitor/LocalProjects/hyper-runner-astra \
  $(grep -l '"cwd":"/Users/vitor/LocalProjects/hyper-runner-astra"' \
      ~/.codex/sessions/2026/09/0*/*.jsonl ~/.codex/archived_sessions/*.jsonl 2>/dev/null)
```

Sanity floor: `model` must be `gpt-6-astra`, and the summed totals must be at
least the largest single session's — 10,429,199 input, 51,706 output, 8,482
reasoning. If `session_count` is 0, the `cwd` string did not match; print one
`session_meta` line and compare exactly.

Compare each figure with the same figure in the arm's `STATS.md`. **Exact
agreement is not required** — the arm may legitimately scope its totals
differently, for example excluding the session that wrote the file. What matters
is that any difference has a stated reason. Record the comparison as a table:
self-reported, log-derived, and the explanation for each gap.

- [ ] **Step 4: Record which convention the arm used for the stats session**

The three existing arms disagree on this, and it moves the headline token
figures:

| Arm | Convention |
| --- | --- |
| `opencode-qwen38` | excludes it — "Figures exclude the two later prompts that wrote this file" |
| `opencode-qwen38-superpowers` | includes it — "Totals were read while this stats request was running, so they include it" |
| `claude-opus5` | says nothing |

Establish which of the three `codex-astra` used, from its own text and from your
Step 3 comparison. This is a real cross-arm inconsistency in a headline metric,
not a footnote: Task 4 records it per arm in `arms.json` as
`statsSessionIncluded` with values `true`, `false` or `null`, and Task 7 states
it on the dashboard beside the token figures.

For `claude-opus5`, which says nothing, the value is `null` and the note reads
"not stated". Do not infer it.

- [ ] **Step 5: Copy the file into the campaign**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
cp /Users/vitor/LocalProjects/hyper-runner-astra/STATS.md \
   bench/agent-build-off/results/codex-astra.md
diff <(grep '^## ' bench/agent-build-off/results/codex-astra.md) \
     <(grep '^## ' /Users/vitor/LocalProjects/hyper-runner-claude/STATS.md)
```

The `diff` shows how this arm's headings compare with a sibling's. They do not
have to match exactly, but a heading the other three all have and this one lacks
is a gap worth naming in the write-up rather than leaving silent.

- [ ] **Step 6: Append the verification record**

Add a short section to `bench/agent-build-off/results/codex-astra.md` titled
"Verification against the session logs", holding the Step 3 comparison table and
the Step 4 convention. Mark it plainly as added when the file was adopted into
this campaign, so it is not mistaken for something the arm reported about itself.

Also note there what this arm has that the others lack: `docs/VERIFICATION.md`
(36 Vitest tests, 14 Playwright tests on Chromium 153.0.8010.12, a 17-row
acceptance table with two partial rows) and `docs/performance.json` (125.076 s
sample, mean 60.00 fps, median frame 16.70 ms, p95 17.10 ms, 1199 meshes,
137-169 draw calls, Apple M5 Pro through ANGLE Metal). It is the **only** arm
with a measured frame rate; the other three record it as not collected. That is
a gap in the others, not a win for this arm — say so.

- [ ] **Step 7: Check the brief matches the other arms**

```bash
grep -A12 "first prompt, verbatim" /Users/vitor/LocalProjects/hyper-runner-claude/STATS.md
grep -A12 -i "verbatim\|first prompt" bench/agent-build-off/results/codex-astra.md
```

If the arm quotes its brief and it matches the other three, say so. If it does
not quote one, recover it from the logs:

```bash
python3 - <<'PY' $(grep -l '"cwd":"/Users/vitor/LocalProjects/hyper-runner-astra"' ~/.codex/sessions/2026/09/0*/*.jsonl 2>/dev/null | sort | head -3)
import json, sys
for path in sys.argv[1:]:
    for line in open(path):
        try: r = json.loads(line)
        except json.JSONDecodeError: continue
        p = r.get("payload") or {}
        if r.get("type") == "response_item" and p.get("role") == "user":
            for c in p.get("content", []):
                t = c.get("text", "")
                if "runner game" in t or "SPEC" in t:
                    print(path); print(t[:1200]); sys.exit(0)
PY
```

**If the brief differs from the other three, quote both and say the arms are not
like-for-like.** Do not imply a controlled comparison that did not happen.

- [ ] **Step 8: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add bench/agent-build-off/
git commit -m "bench(build-off): adopt and verify the codex-astra STATS

This arm now reports its own stats, as the other three do, so all four carry a
self-reported record on comparable headings. Its token totals are cross-checked
against the eight Codex rollout files, and the comparison is recorded in the
file.

Also records which arms include the stats-writing session in their token totals.
The three existing arms use three different conventions, which moves a headline
figure, so it is tracked per arm rather than left implicit.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Recover the three layout-bench session metrics

`~/LocalProjects/qwen38-next-layout-bench` has no metrics at all. All three sessions are in the opencode database.

**Files:**
- Create: `bench/layout-skill-bench/scripts/recover_opencode_stats.py`
- Create: `bench/layout-skill-bench/results/{design-skill,taste-skill,taste2}.md`

**Interfaces:**
- Produces: one metrics record per arm, on the same headings Task 1 used, so the two campaigns read alike.

The three sessions:

| Arm | Session id | Title | Started |
| --- | --- | --- | --- |
| `design-skill` | `ses_f87267505ffelX5pJ5rzkCs9Pl` | Landing page 5 iterations | 2026-09-06 22:31:57 |
| `taste-skill` | `ses_f8718363bffeHuTLocWC8uYT7G` | Anti-slop frontend design skill | 2026-09-06 22:47:31 |
| `taste2` | `ses_f86fd99a2ffe1axcggL9fDiPuH` | Awwwards-Tier UI Design | 2026-09-06 23:16:35 |

- [ ] **Step 1: Write the extraction script**

`message.data` is a JSON blob holding `role`, `modelID`, `providerID`, `cost`, `time: {created, completed}` and `tokens: {total, input, output, reasoning, cache: {write, read}}`. Create `bench/layout-skill-bench/scripts/recover_opencode_stats.py`:

```python
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
```

- [ ] **Step 2: Run it for all three arms**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
mkdir -p bench/layout-skill-bench/{scripts,results}
for s in ses_f87267505ffelX5pJ5rzkCs9Pl ses_f8718363bffeHuTLocWC8uYT7G ses_f86fd99a2ffe1axcggL9fDiPuH; do
  echo "===== $s"
  python3 bench/layout-skill-bench/scripts/recover_opencode_stats.py "$s"
done
```

Sanity check: every arm's `models` must contain a `Qwen3.8-Flash-Next` id and `cost` must be 0 — these ran on the local rig. If a different model appears, that arm is not what the spec assumed; report it rather than writing it up as Qwen3.8.

- [ ] **Step 3: Establish which skill each arm ran**

`taste-skill` and `taste2` each carry an identical `skills-lock.json` pinning `brandkit`, `design-taste-frontend` and `high-end-visual-design` from `Leonxlnx/taste-skill`. `design-skill` has **no lock file**, so its configuration must be read from its session, not guessed:

```bash
sqlite3 "file:$HOME/.local/share/opencode/opencode.db?mode=ro" \
  "select data from part where session_id='ses_f87267505ffelX5pJ5rzkCs9Pl' limit 400;" \
  | grep -io "skill[^\"]\{0,80\}" | sort -u | head -20
diff <(python3 -m json.tool /Users/vitor/LocalProjects/qwen38-next-layout-bench/taste-skill/skills-lock.json) \
     <(python3 -m json.tool /Users/vitor/LocalProjects/qwen38-next-layout-bench/taste2/skills-lock.json) \
  && echo "IDENTICAL LOCKS"
```

Two outcomes, both must be handled honestly:
- If `design-skill` ran **no** skill, it is the baseline arm and the bench is "no skill vs one skill set, twice". Say that.
- If the two locks are identical, `taste-skill` and `taste2` are **the same skill configuration run twice**, not two skills. The write-up must present them as a repeat run, not as a skill comparison.

- [ ] **Step 4: Quote each arm's brief verbatim**

```bash
python3 - <<'PY'
import json, sqlite3, os
db = os.path.expanduser("~/.local/share/opencode/opencode.db")
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
for sid in ("ses_f87267505ffelX5pJ5rzkCs9Pl","ses_f8718363bffeHuTLocWC8uYT7G","ses_f86fd99a2ffe1axcggL9fDiPuH"):
    print("="*20, sid)
    for (data,) in con.execute(
        "select p.data from part p join message m on m.id=p.message_id "
        "where p.session_id=? order by m.time_created limit 60", (sid,)):
        p = json.loads(data)
        if p.get("type") == "text" and p.get("text"):
            print(p["text"][:900]); break
PY
```

The three session titles differ ("Landing page 5 iterations", "Anti-slop frontend design skill", "Awwwards-Tier UI Design"), so the briefs may differ too. **If they differ, the arms are three runs, not a controlled skill comparison** — record each brief and say so in every write-up and on the dashboard.

- [ ] **Step 5: Write the three `results/<arm>.md` files**

Same headings as Task 1. Per arm record: the skill configuration from Step 3, the verbatim brief from Step 4, wall time from `first_ms`/`last_ms`, tokens, tool calls, message counts, page count (five each), and the form each arm shipped (`design-skill` five static directories, `taste-skill` a Vite React app with five routes, `taste2` five static HTML pages plus a Node server).

- [ ] **Step 6: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add bench/layout-skill-bench/
git commit -m "bench(layout): recover the three layout-bench session metrics

These three runs shipped with no metrics at all. All three opencode sessions
were located and their tokens, tool calls and timings extracted from the
session database, so the record is measured rather than estimated.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Amend AGENTS.md for tracked runnable artifacts

AGENTS.md routes every harness artifact to `bench/harness-matrix/logs/`, which is gitignored, with one tracked exception for SVGs. A published, runnable demo fits neither: it must be tracked, and it is a directory.

**Files:**
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: the contract Tasks 4 and 5 rely on when they add `demos/` directories.

- [ ] **Step 1: Read the two sections you are amending**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
sed -n '/## Where does a new file go/,/## The results boundary/p' AGENTS.md
sed -n '/## Benchmark outputs policy/,/## Two machines/p' AGENTS.md
```

- [ ] **Step 2: Add the third artifact class**

In "Benchmark outputs policy", add a table distinguishing three classes:

| Class | Example | Location | Tracked |
| --- | --- | --- | --- |
| Raw run output | transcripts, traces, `*.log`, run dirs | `bench/<campaign>/logs/` | no |
| Small artifact | a model-generated SVG | `logs/` (SVG only) or `results/` | yes |
| Runnable artifact | a demo app the model wrote, published on the site | `bench/<campaign>/demos/<arm>/` | yes, source only |

State three rules for `demos/`:
- It holds **source**, never `node_modules`, `dist` or `.git`. The site builds it.
- It is the artifact as the model produced it. Hosting fixes happen at publish time and are listed in the campaign's `plan.md`.
- A campaign gets a `demos/` directory only when its artifacts are published.

- [ ] **Step 3: Record how the site is published**

AGENTS.md describes `reports/` as "self-contained Chart.js dashboards (served via GitHub Pages)" but never says how. Add one line: `reports/` plus the built demos are assembled and pushed to the `gh-pages` branch by `.github/workflows/publish-pages.yml`, which serves `https://snagnever.github.io/macstudio-local-llm/`.

- [ ] **Step 4: Verify the contract now covers the new campaigns**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
grep -n "demos/" AGENTS.md
grep -n "gh-pages" AGENTS.md
```

Both must return hits. Re-read the amended sections once and confirm no existing rule now contradicts them — in particular that the `bench/**/logs/**` gitignore rule is untouched.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): add the tracked runnable-artifact class

A published demo app fits neither the ignored raw-output rule nor the
single-file SVG exception: it must be tracked and it is a directory. Adds
bench/<campaign>/demos/<arm>/ for source only, and records that the site is
assembled to gh-pages by a workflow.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Build the agent-build-off campaign

**Files:**
- Create: `bench/agent-build-off/plan.md`
- Create: `bench/agent-build-off/results/arms.json`
- Create: `bench/agent-build-off/demos/{opencode-qwen38,opencode-qwen38-superpowers,claude-opus5,codex-astra}/`
- Copy: `~/LocalProjects/hyper-runner{,-superpowers,-claude,-astra}/STATS.md` → `results/<arm>.md` for the three that have one

**Interfaces:**
- Consumes: `results/codex-astra.md` from Task 1.
- Produces: `results/arms.json`, the single source of numbers for Task 7's dashboard.

| Arm | Source folder | Harness | Model |
| --- | --- | --- | --- |
| `opencode-qwen38` | `~/LocalProjects/hyper-runner` | opencode | `qwen3.8-flash-next` (MLX, local) |
| `opencode-qwen38-superpowers` | `~/LocalProjects/hyper-runner-superpowers` | opencode | same, plus superpowers skills |
| `claude-opus5` | `~/LocalProjects/hyper-runner-claude` | claude | `claude-opus-5` |
| `codex-astra` | `~/LocalProjects/hyper-runner-astra` | codex | `gpt-6-astra` |

`~/LocalProjects/hyper-runner-fable` is empty. That arm never ran; omit it rather than showing a blank column.

- [ ] **Step 1: Vendor the four demo sources**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
set -e
vendor() {  # $1 = source dir, $2 = arm name
  dest="bench/agent-build-off/demos/$2"
  mkdir -p "$dest"
  rsync -a --exclude node_modules --exclude dist --exclude .git \
        --exclude '.DS_Store' "$1"/ "$dest"/
  echo "$2: $(du -sk "$dest" | cut -f1) KB"
}
vendor ~/LocalProjects/hyper-runner              opencode-qwen38
vendor ~/LocalProjects/hyper-runner-superpowers  opencode-qwen38-superpowers
vendor ~/LocalProjects/hyper-runner-claude       claude-opus5
vendor ~/LocalProjects/hyper-runner-astra        codex-astra
du -sh bench/agent-build-off/demos
```

Expected roughly: 153 KB, 402 KB, 624 KB, 4.2 MB — about 5.4 MB total. `codex-astra` is large because of 2.2 MB of licensed assets and 1.9 MB of verification screenshots; both are cited by its verification record, so both are kept. Confirm `public/assets/ATTRIBUTION.md` came across with it.

- [ ] **Step 2: Confirm nothing unwanted was vendored**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
find bench/agent-build-off/demos -name node_modules -o -name dist -o -name .git | head
find bench/agent-build-off/demos -name 'package-lock.json' | wc -l
```

First command must print nothing. Second must print `4` — every arm needs its lockfile, because `npm ci` against it is what makes the build reproducible.

- [ ] **Step 3: Copy the other three STATS files**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
cp ~/LocalProjects/hyper-runner/STATS.md             bench/agent-build-off/results/opencode-qwen38.md
cp ~/LocalProjects/hyper-runner-superpowers/STATS.md bench/agent-build-off/results/opencode-qwen38-superpowers.md
cp ~/LocalProjects/hyper-runner-claude/STATS.md      bench/agent-build-off/results/claude-opus5.md
ls bench/agent-build-off/results/
```

Four `.md` files must be present — these three plus `codex-astra.md` from Task 1.
All four are now self-reported by the agent that did the work, which makes them
comparable; only `codex-astra.md` additionally carries a log cross-check.

- [ ] **Step 4: Write `results/arms.json`**

Follow the two-array model `reports/README.md` documents: an `arms` roster and a tidy `results` list. Numbers appear once.

```json
{
  "campaign": "agent-build-off",
  "brief": "<the verbatim brief, quoted once>",
  "arms": [
    {"id": "claude-opus5", "harness": "claude", "model": "claude-opus-5",
     "hosted": true, "label": "Claude + Opus 5", "color": "#e76f51"}
  ],
  "results": [
    {"arm": "claude-opus5", "metric": "wallMinutes", "value": 41.9},
    {"arm": "claude-opus5", "metric": "tokensOutput", "value": 240076},
    {"arm": "claude-opus5", "metric": "sourceLines", "value": 2111},
    {"arm": "claude-opus5", "metric": "meanFps", "value": null,
     "note": "not collected"}
  ]
}
```

Populate every arm across the metrics the four `results/*.md` files share: `wallMinutes`, `activeMinutes`, `tokensOutput`, `tokensInputUncached`, `tokensCacheRead`, `tokensReasoning`, `userPrompts`, `questionsAsked`, `toolCalls`, `sourceLines`, `sourceFiles`, `docLines`, `directDeps`, `installedPackages`, `bundleRawKB`, `bundleGzipKB`, `buildSeconds`, `testsPassing`, `defectsFound`, `meanFps`.

A metric a given arm never recorded is `value: null` with a `note`. Do not compute a substitute.

Each arm also carries `statsSessionIncluded` on its roster entry, from Task 1
Step 4 — `true`, `false`, or `null` with the note "not stated". The arms disagree
on whether the session that wrote the stats file is inside their own token
totals, which shifts the token comparison directly. It is a roster field rather
than a metric because it qualifies how every token figure for that arm should be
read.

- [ ] **Step 5: Validate arms.json mechanically**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
python3 - <<'PY'
import json, collections
d = json.load(open("bench/agent-build-off/results/arms.json"))
arms = {a["id"] for a in d["arms"]}
assert arms == {"opencode-qwen38","opencode-qwen38-superpowers","claude-opus5","codex-astra"}, arms
seen = collections.Counter((r["arm"], r["metric"]) for r in d["results"])
dupes = [k for k, v in seen.items() if v > 1]
assert not dupes, f"duplicate records: {dupes}"
bad = [r for r in d["results"] if r["arm"] not in arms]
assert not bad, f"unknown arm: {bad}"
metrics = {r["metric"] for r in d["results"]}
missing = [(a, m) for a in arms for m in metrics if (a, m) not in seen]
print("arms:", len(arms), "| metrics:", len(metrics), "| records:", len(d["results"]))
print("nulls:", sum(1 for r in d["results"] if r["value"] is None))
print("gaps (no record at all):", missing or "none")
PY
```

Every `(arm, metric)` pair must have exactly one record. A pair with no record is a gap the dashboard cannot render — add it with `value: null` and a note.

- [ ] **Step 6: Write `bench/agent-build-off/plan.md`**

Preserve the dated-title convention the other campaigns use. Cover: what the study compares, the verbatim brief, the arm table above, the note that `hyper-runner-fable` never ran, where source and metrics live, and a **Publish-time fixes** section listing exactly what the workflow does to each arm (filled in by Task 9, referenced here).

State the limits plainly: the local arms cost no money and took far longer; one arm ran with a skill library the others lacked; only `codex-astra` has a measured frame rate.

- [ ] **Step 7: Cross-reference from the harness matrix**

Add one line to each matching `bench/harness-matrix/results/<harness>/<model>.md` pointing at this campaign, so the matrix stays the index into every artifact. `codex/gpt-6-astra` has no verdict file in the matrix; note its absence in the commit message rather than creating one.

- [ ] **Step 8: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add AGENTS.md bench/agent-build-off/ bench/harness-matrix/results/
git commit -m "bench(build-off): campaign, four vendored demo sources, arms.json

Same brief, one session, from an empty folder, through four agent stacks. Source
is vendored without node_modules, dist or .git; the site builds it. Metrics live
once in results/arms.json, with every uncollected value null rather than
substituted.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Build the layout-skill-bench campaign

**Files:**
- Create: `bench/layout-skill-bench/plan.md`
- Create: `bench/layout-skill-bench/results/arms.json`
- Create: `bench/layout-skill-bench/demos/{design-skill,taste-skill,taste2}/`

**Interfaces:**
- Consumes: the three `results/<arm>.md` files from Task 2.
- Produces: `results/arms.json` for Task 8's dashboard.

- [ ] **Step 1: Vendor the three sources**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
set -e
for arm in design-skill taste-skill taste2; do
  dest="bench/layout-skill-bench/demos/$arm"
  mkdir -p "$dest"
  rsync -a --exclude node_modules --exclude dist --exclude .git --exclude '.DS_Store' \
        --exclude 'tsconfig.tsbuildinfo' --exclude 'server.log' \
        "$HOME/LocalProjects/qwen38-next-layout-bench/$arm"/ "$dest"/
  echo "$arm: $(du -sk "$dest" | cut -f1) KB"
done
du -sh bench/layout-skill-bench/demos
```

Expected roughly 60 KB, 256 KB, 270 KB — about 0.6 MB. Keep each arm's `skills-lock.json` and `.agents/` where present: they are the record of which skill ran.

- [ ] **Step 2: Write `results/arms.json`**

Same shape as Task 4. Metrics per arm: `wallMinutes`, `tokensOutput`, `tokensInputUncached`, `tokensCacheRead`, `toolCalls`, `messages`, `pageCount` (5 each), plus string fields for `skillConfig`, `brief` and `form`.

If Task 2 established that `taste-skill` and `taste2` ran an identical skill configuration, set `skillConfig` to the same value for both and add a top-level `"note"` saying the bench is a repeat run rather than two skills. If the briefs differ, carry each arm's own `brief` verbatim.

- [ ] **Step 3: Validate arms.json**

Run the same validation script as Task 4 Step 5, with the arm set `{"design-skill","taste-skill","taste2"}`.

- [ ] **Step 4: Write `bench/layout-skill-bench/plan.md`**

Cover: what the study compares, each arm's skill configuration and verbatim brief, the three shipped forms, and a **Publish-time fixes** section (Task 9 fills the detail).

**State the comparison's real strength honestly at the top.** If the briefs differ, or if two arms share one skill configuration, this is not a controlled skill comparison and the page must not present it as one.

- [ ] **Step 5: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add bench/layout-skill-bench/
git commit -m "bench(layout): campaign, three vendored page sets, arms.json

One model, five pages, three runs. Each arm's skill lock and brief are recorded
so the page can state what the comparison actually controls for.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Preserve the two pages that live only on gh-pages

`gh-pages` holds `index.html`, `overview.html` and `perf-lines.html`. The last two exist **nowhere on `main`**. The publish workflow overwrites the branch, so they must be brought onto `main` first or they are lost.

**Files:**
- Create: `reports/overview.html`, `reports/perf-lines.html`

- [ ] **Step 1: Confirm they are absent from main and present on gh-pages**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git fetch origin gh-pages
git ls-tree -r origin/gh-pages --name-only
ls reports/
```

`gh-pages` must list the three files. `reports/` must not contain `overview.html` or `perf-lines.html`.

- [ ] **Step 2: Copy them onto main**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git show origin/gh-pages:overview.html   > reports/overview.html
git show origin/gh-pages:perf-lines.html > reports/perf-lines.html
wc -l reports/overview.html reports/perf-lines.html
```

- [ ] **Step 3: Check they still work standalone**

Open each in the browser preview. They are older pages about the Qwen3.8-27B prefix-cache work. Confirm they render and the console is clean. Do **not** restyle or rewrite them — they are preserved as they are. If one is broken already, say so in the commit message rather than fixing it here.

- [ ] **Step 4: Add them to the reports README**

`reports/README.md` documents the dashboards in a table. Add a row for each, noting they predate the current dashboards and are preserved so the published site keeps its existing URLs.

- [ ] **Step 5: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add reports/
git commit -m "reports: bring overview and perf-lines onto main

Both pages existed only on the gh-pages branch. The publish workflow overwrites
that branch, so without this they would be lost and their published URLs would
break.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Build the Agent Build-Off dashboard

**Files:**
- Create: `reports/agent-build-off.html`

**Interfaces:**
- Consumes: `bench/agent-build-off/results/arms.json` (Task 4) and the four `results/<arm>.md` files.
- Produces: a page Task 9 links from the hub and Task 10 publishes.

- [ ] **Step 1: Read the conventions before writing**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
sed -n '1,60p' reports/README.md
grep -n "window.ChartsCommon" -A 30 reports/charts-common.js | tail -32
```

`ChartsCommon` exposes `initTheme`, `buildGroupedChart`, `buildRankedChart`, `buildScatterChart`, `buildRadarChart`, `buildScoreboard`, `setupSortableTable`, `highlightBestPerColumn`, `metricValue`, `seriesFor`, `deriveRanked`, `createFilterState`, `createFilterBar`, `fmt1`, `fmtInt`. Load it as a classic script: `<script src="charts-common.js"></script>`, never as a module.

- [ ] **Step 2: Inline the data from arms.json**

Copy the `arms` and `results` arrays into the page's inline script, keeping the field names. Do not fetch the JSON at runtime — the page must open from `file://` as the other dashboards do.

- [ ] **Step 3: Build the comparison**

The page answers one question: same brief, one session, from an empty folder — what does each agent stack deliver?

- A scoreboard across every shared metric: wall time, active time, tokens by class, source lines and files, dependencies direct and transitive, bundle size raw and gzipped, build time, tests, tool calls, defects found.
- A **Play** button per arm linking to `demos/build-off/<arm>/`. Those paths only resolve on the published site; that is expected.
- The defect narratives, which are the sharpest content in the four records — a Rapier collision bug found by per-frame tracing, a hitbox defect found by a scripted autopilot, a shader flicker traced by reading installed shader source, and `codex-astra`'s corrected findings.

- [ ] **Step 4: State what is not comparable**

In the page's own words, not a footnote:
- The two local arms cost nothing to run and took far longer. One took 90 minutes; another's raw clock spans 11 hours, of which 1 h 49 m is active time.
- `opencode-qwen38-superpowers` ran with a skills library the others lacked.
- Only `codex-astra` has a measured frame rate — 60.00 fps mean over 125 s. The other three record it as not collected. That is a gap in the others, not a win for this arm.
- `hyper-runner-fable` never ran and is absent.
- The arms do not agree on whether the session that wrote their stats file is
  counted in their own token totals: one excludes it, one includes it, one does
  not say. Show each arm's `statsSessionIncluded` beside its token figures. A
  token comparison across arms that disagree on this is approximate, and the page
  must say so rather than presenting the totals as directly comparable.

- [ ] **Step 5: Verify every figure traces to the data**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
python3 - <<'PY'
import json, re
src = open("reports/agent-build-off.html").read()
data = json.load(open("bench/agent-build-off/results/arms.json"))
vals = {str(r["value"]) for r in data["results"] if r["value"] is not None}
nums = set(re.findall(r"\b\d[\d,]{2,}\b", re.sub(r"<script[^>]*>.*?</script>", "", src, flags=re.S)))
stray = {n for n in nums if n.replace(",", "") not in {v.replace(".0","") for v in vals} and n not in {"2026"}}
print("prose numbers not traceable to arms.json:", sorted(stray) or "none")
PY
```

Investigate every number the check flags. A figure in prose that is not in `arms.json` is either a typo or a number that should live in the data.

- [ ] **Step 6: Check it renders**

Open `reports/agent-build-off.html` in the browser preview. Confirm every chart builds, the console is clean, the scoreboard sorts, and every `null` renders as a gap rather than `0`.

- [ ] **Step 7: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add reports/agent-build-off.html
git commit -m "reports: add the Agent Build-Off dashboard

Four agent stacks, one brief, one session each. Figures come from
bench/agent-build-off/results/arms.json; uncollected metrics render as gaps.
The page states what is not comparable rather than footnoting it.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Build the Layout Skill Bench dashboard

**Files:**
- Create: `reports/layout-skill-bench.html`

**Interfaces:**
- Consumes: `bench/layout-skill-bench/results/arms.json` (Task 5).

- [ ] **Step 1: Inline the data and build the grid**

Same conventions as Task 7: classic `<script src="charts-common.js">`, data inline, no runtime fetch.

The page is primarily visual: a 3 × 5 grid, one row per arm, each cell linking to the real page. Session metrics per arm sit above the grid.

Link targets on the published site:
- `design-skill` → `demos/layout/design-skill/<n>/` for n = 1..5
- `taste-skill` → `demos/layout/taste-skill/<n>` for n = 1..5
- `taste2` → `demos/layout/taste2/<n>.html` for n = 1..5

The three differ because the three arms shipped different forms, and Task 9 rewrites two of them at publish time. Use these exact shapes.

- [ ] **Step 2: State what the comparison controls for**

Take this from `bench/layout-skill-bench/plan.md` (Task 5) rather than assuming. If the briefs differ across arms, quote each one and present the arms as three runs. If two arms share one skill configuration, say the bench is a repeat run rather than two skills. **Do not present a controlled skill comparison unless Task 2 established one.**

- [ ] **Step 3: Verify and render**

Run the same figure-tracing check as Task 7 Step 5, against `bench/layout-skill-bench/results/arms.json`. Then open the page in the browser preview and confirm it renders with a clean console.

- [ ] **Step 4: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add reports/layout-skill-bench.html
git commit -m "reports: add the Layout Skill Bench dashboard

One model, five pages, three runs, with each arm's skill configuration and brief
recorded so the page states what the comparison actually controls for.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Write the publish-time fixes

Every fix here exists because model-written source assumes it is served from a domain root. The site is served from `/macstudio-local-llm/`. **The tracked source keeps what the model wrote**; the fix is applied to the copy the workflow builds.

**Files:**
- Create: `bench/layout-skill-bench/demos/taste-skill.basepath.patch`
- Create: `tools/publish/fix-layout-arms.sh`
- Modify: `bench/agent-build-off/plan.md`, `bench/layout-skill-bench/plan.md` (the Publish-time fixes sections)

**Interfaces:**
- Produces: the patch and script Task 10's workflow invokes.

| Arm | Problem | Fix |
| --- | --- | --- |
| `opencode-qwen38` | no `base` in `vite.config.ts`; emits `/assets/…` | `vite build --base=…` |
| `opencode-qwen38-superpowers` | same | same |
| `claude-opus5` | none — `base: './'` already set | build unchanged |
| `codex-astra` | none — `base: './'` already set | build unchanged |
| `taste-skill` | no `base`, **and** a router that collapses every subpath to page 1 | `--base=…` + a patch + `404.html` |
| `design-skill` | index and in-page switchers link to `/1/`…`/5/` absolutely | rewrite to relative |
| `taste2` | pages link extensionlessly (`href="1"`), resolved by a Node server the static host does not run; no index | rewrite to `1.html` and generate an index |

- [ ] **Step 1: Confirm the taste-skill router problem**

```bash
sed -n '10,40p' /Users/vitor/LocalProjects/macstudio-local-llm/bench/layout-skill-bench/demos/taste-skill/src/App.tsx
```

`normalize()` matches `window.location.pathname` against `PATHS` (`/1`…`/5`) and returns `/1` for anything else. Under `/macstudio-local-llm/demos/layout/taste-skill/1`, nothing matches, so every URL collapses to page 1. `navigate()` pushes bare `/1`, which leaves the site entirely. This is the only fix that changes program logic, which is why it is a reviewable patch file rather than an inline edit.

- [ ] **Step 2: Write the patch**

Create `bench/layout-skill-bench/demos/taste-skill.basepath.patch` — a `git apply`-able patch making `normalize` strip Vite's injected base and `navigate` prepend it:

```diff
--- a/src/App.tsx
+++ b/src/App.tsx
@@
 const PATHS: string[] = ITERATIONS.map((i) => i.path);
 
+const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");
+
 function normalize(pathname: string) {
   const clean = pathname.replace(/\/+$/, "");
-  return PATHS.includes(clean) ? clean : "/1";
+  const rel = clean.startsWith(BASE) ? clean.slice(BASE.length) || "/1" : clean;
+  return PATHS.includes(rel) ? rel : "/1";
 }
 
 function navigate(path: string) {
-  if (path === window.location.pathname) return;
-  window.history.pushState({}, "", path);
+  const target = BASE + path;
+  if (target === window.location.pathname) return;
+  window.history.pushState({}, "", target);
   window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
   window.dispatchEvent(new PopStateEvent("popstate"));
 }
```

`Switcher` compares against `PATHS` values, which stay relative, so it needs no change. Verify the patch applies cleanly to a scratch copy — never to the tracked source:

```bash
REPO=/Users/vitor/LocalProjects/macstudio-local-llm
PATCH="$REPO/bench/layout-skill-bench/demos/taste-skill.basepath.patch"
rm -rf /tmp/ts-check
cp -R "$REPO/bench/layout-skill-bench/demos/taste-skill" /tmp/ts-check
cd /tmp/ts-check && git apply --check "$PATCH" && echo "patch applies cleanly"
```

`git apply --check` needs no repository, only the file it patches, so the scratch
copy does not have to be initialised as one.

- [ ] **Step 3: Write the layout fix script**

Create `tools/publish/fix-layout-arms.sh`. It operates on the assembled site tree, never on the repo:

```bash
#!/usr/bin/env bash
# Apply publish-time path fixes to the built layout arms.
# Usage: fix-layout-arms.sh <site-dir>
# <site-dir>/demos/layout/{design-skill,taste-skill,taste2} must already exist.
set -euo pipefail
SITE="${1:?usage: fix-layout-arms.sh <site-dir>}"
L="$SITE/demos/layout"

# design-skill: absolute "/1/".."/5/" links -> relative.
# The index sits one level above the page dirs; each page dir links to siblings.
sed -i.bak -E 's#href="/([1-5])/"#href="\1/"#g' "$L/design-skill/index.html"
for n in 1 2 3 4 5; do
  sed -i.bak -E 's#href="/([1-5])/"#href="../\1/"#g' "$L/design-skill/$n/index.html"
done
find "$L/design-skill" -name '*.bak' -delete

# taste2: extensionless "href=\"1\"" was resolved by its Node server; make it static.
for n in 1 2 3 4 5; do
  sed -i.bak -E 's#href="([1-5])"#href="\1.html"#g' "$L/taste2/$n.html"
done
find "$L/taste2" -name '*.bak' -delete

# taste2 shipped no index page; generate one listing the five.
cat > "$L/taste2/index.html" <<'HTML'
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>taste2 — five iterations</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1.5rem}
li{margin:.4rem 0}</style></head><body>
<h1>taste2 — five iterations</h1>
<p>Five landing-page iterations generated in one session. This index is added at
publish time; the run itself served these pages from a small Node server.</p>
<ol><li><a href="1.html">Iteration 1</a></li><li><a href="2.html">Iteration 2</a></li>
<li><a href="3.html">Iteration 3</a></li><li><a href="4.html">Iteration 4</a></li>
<li><a href="5.html">Iteration 5</a></li></ol>
</body></html>
HTML

# taste-skill: history-API routing needs a fallback for deep links.
cp "$L/taste-skill/index.html" "$L/taste-skill/404.html"

echo "layout arms fixed under $L"
```

```bash
chmod +x /Users/vitor/LocalProjects/macstudio-local-llm/tools/publish/fix-layout-arms.sh
```

Note `sed -i.bak` with an explicit suffix: that form works on both BSD and GNU sed, and the workflow runs on Linux while you are testing on macOS.

- [ ] **Step 4: Record every fix in both campaign plans**

Add a **Publish-time fixes** section to `bench/agent-build-off/plan.md` and `bench/layout-skill-bench/plan.md`, reproducing the table above and naming the patch file and script. A reader must be able to see exactly how the published artifact differs from what the model wrote.

- [ ] **Step 5: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add tools/publish/ bench/layout-skill-bench/demos/taste-skill.basepath.patch bench/*/plan.md
git commit -m "tools(publish): base-path fixes for the hosted demos

Four arms assume a domain root; the site serves from /macstudio-local-llm/.
Path fixes are applied to the build copy, never to the vendored source, and each
one is listed in its campaign plan. taste-skill needs a real patch: its router
collapses every unrecognised path to page 1, so under a subpath every URL would
show the same page.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: Add the publish workflow

**Files:**
- Create: `.github/workflows/publish-pages.yml`

**Interfaces:**
- Consumes: everything from Tasks 4-9.
- Produces: the assembled site on the `gh-pages` branch.

GitHub Pages for this repo serves branch `gh-pages`, path `/`, `build_type: legacy`. Do **not** change the Pages source — that is a repository setting the user owns. Push to the branch instead.

- [ ] **Step 1: Write the workflow**

```yaml
name: Publish Pages

on:
  push:
    branches: [main]
    paths:
      - 'reports/**'
      - 'bench/agent-build-off/demos/**'
      - 'bench/layout-skill-bench/demos/**'
      - 'tools/publish/**'
      - '.github/workflows/publish-pages.yml'
  workflow_dispatch:

concurrency:
  group: publish-pages
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      BASE: /macstudio-local-llm
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '22'

      - name: Build the Agent Build-Off demos
        run: |
          set -euo pipefail
          for arm in opencode-qwen38 opencode-qwen38-superpowers claude-opus5 codex-astra; do
            echo "::group::$arm"
            pushd "bench/agent-build-off/demos/$arm"
            npm ci
            npx vite build --base="$BASE/demos/build-off/$arm/"
            popd
            echo "::endgroup::"
          done

      - name: Build the taste-skill layout arm
        run: |
          set -euo pipefail
          pushd bench/layout-skill-bench/demos/taste-skill
          git apply ../taste-skill.basepath.patch
          npm ci
          npx vite build --base="$BASE/demos/layout/taste-skill/"
          git checkout -- src/App.tsx
          popd

      - name: Assemble the site
        run: |
          set -euo pipefail
          mkdir -p site/demos/build-off site/demos/layout
          cp -R reports/. site/
          touch site/.nojekyll
          for arm in opencode-qwen38 opencode-qwen38-superpowers claude-opus5 codex-astra; do
            cp -R "bench/agent-build-off/demos/$arm/dist" "site/demos/build-off/$arm"
          done
          cp -R bench/layout-skill-bench/demos/taste-skill/dist site/demos/layout/taste-skill
          cp -R bench/layout-skill-bench/demos/design-skill  site/demos/layout/design-skill
          mkdir -p site/demos/layout/taste2
          cp -R bench/layout-skill-bench/demos/taste2/pages/. site/demos/layout/taste2/
          rm -f site/demos/layout/design-skill/skills-lock.json
          rm -rf site/demos/layout/design-skill/.agents
          tools/publish/fix-layout-arms.sh site

      - name: Check the assembled tree
        run: |
          set -euo pipefail
          test -f site/index.html
          test -f site/overview.html
          test -f site/perf-lines.html
          test -f site/agent-build-off.html
          test -f site/layout-skill-bench.html
          test -f site/harness-matrix-svgbench.html
          test -f site/charts-common.js
          for arm in opencode-qwen38 opencode-qwen38-superpowers claude-opus5 codex-astra; do
            test -f "site/demos/build-off/$arm/index.html"
          done
          for arm in design-skill taste-skill taste2; do
            test -f "site/demos/layout/$arm/index.html"
          done
          test -f site/demos/layout/taste-skill/404.html
          if grep -rIl 'src="/assets/\|href="/assets/' site/demos >/dev/null 2>&1; then
            echo "root-absolute asset paths survived the base fix:"
            grep -rIl 'src="/assets/\|href="/assets/' site/demos
            exit 1
          fi
          du -sh site

      - name: Publish to gh-pages
        run: |
          set -euo pipefail
          cd site
          git init -q .
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -qm "Publish site from ${GITHUB_SHA::7}"
          git push -q --force \
            "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" \
            HEAD:gh-pages
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Two details that matter. `.nojekyll` must exist or GitHub Pages will drop any path beginning with an underscore. The force push is safe because `gh-pages` is a generated branch and Task 6 already moved its only unique content onto `main`.

- [ ] **Step 2: Validate the YAML parses**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
python3 -c "
import sys
try:
    import yaml
except ImportError:
    sys.exit('PyYAML not installed; check the file with: gh workflow view, or install pyyaml')
d = yaml.safe_load(open('.github/workflows/publish-pages.yml'))
print('jobs:', list(d['jobs']))
print('steps:', [s.get('name') or s.get('uses') for s in d['jobs']['build']['steps']])
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add .github/workflows/publish-pages.yml
git commit -m "ci: assemble and publish the site to gh-pages

Builds each demo with an explicit base path, applies the documented publish-time
fixes, assembles reports/ plus the built demos, and force-pushes to gh-pages.
The whole reports/ directory is published for the first time; until now the
branch carried three files.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: Verify the assembled site locally, before any deploy

Prove the site works before it is published, by running the workflow's own steps on this machine.

**Files:** none — this task produces evidence, not artifacts.

- [ ] **Step 1: Build every demo**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
set -euo pipefail
BASE=/macstudio-local-llm
for arm in opencode-qwen38 opencode-qwen38-superpowers claude-opus5 codex-astra; do
  echo "===== $arm"
  ( cd "bench/agent-build-off/demos/$arm" && npm ci && npx vite build --base="$BASE/demos/build-off/$arm/" )
done
( cd bench/layout-skill-bench/demos/taste-skill \
  && git apply ../taste-skill.basepath.patch \
  && npm ci && npx vite build --base="$BASE/demos/layout/taste-skill/" \
  && git checkout -- src/App.tsx )
```

**A demo that does not build is a finding to report, not a demo to drop from the site.** Say which arm failed and why.

- [ ] **Step 2: Assemble the tree**

Run the workflow's "Assemble the site" and "Check the assembled tree" steps verbatim from `.github/workflows/publish-pages.yml`. Every assertion must pass, including the root-absolute asset check.

- [ ] **Step 3: Serve it at the real prefix**

The site lives under `/macstudio-local-llm/`, so serving `site/` at the root would hide exactly the bugs this task exists to catch.

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
rm -rf /tmp/site-root && mkdir -p /tmp/site-root
cp -R site /tmp/site-root/macstudio-local-llm
cd /tmp/site-root && python3 -m http.server 8099 &
sleep 1 && echo "serving http://localhost:8099/macstudio-local-llm/"
```

- [ ] **Step 4: Walk every page in the browser**

Open `http://localhost:8099/macstudio-local-llm/` in the browser preview and check each in turn:

- The hub, and every card link from it.
- `agent-build-off.html`, `layout-skill-bench.html`, `harness-matrix-svgbench.html`, `benchmark-charts.html`, `quality-benchmarks-charts.html`, `terminal-bench-scoreboard.html`, `overview.html`, `perf-lines.html`.
- All four Build-Off demos. Each must load its bundle and reach a start screen with a clean console.
- All three layout arms, and **all five pages within each**. For `taste-skill` specifically, click through the switcher to pages 2-5 and confirm the URL changes and the page changes — that is the bug the patch fixes, and it will silently show page 1 five times if the patch did not take.
- Reload directly on `demos/layout/taste-skill/3` to confirm the `404.html` fallback works.

Use `read_console_messages` after each page. Report every 404 and every console error.

- [ ] **Step 5: Stop the server and report**

```bash
pkill -f "http.server 8099" || true
```

Report which pages passed, which failed, and what was not checked. State plainly that audio and physical mobile behaviour are unverified — the STATS records already say so and the site repeats it.

- [ ] **Step 6: Commit any fixes**

If Steps 1-4 surfaced problems, fix them at the right layer — a path fix belongs in `tools/publish/fix-layout-arms.sh`, never in vendored source — and commit. If everything passed, there is nothing to commit; say so.

---

### Task 12: Update the hub and deploy

**Files:**
- Modify: `reports/index.html`

- [ ] **Step 1: Add a card per new benchmark**

`reports/index.html` is the hub. Add cards linking `agent-build-off.html` and `layout-skill-bench.html`, alongside the existing SVG section. Also link `overview.html` and `perf-lines.html` so the preserved pages stay reachable from the site rather than only by direct URL.

Match the existing card markup and section structure; do not restyle the page.

- [ ] **Step 2: Verify the hub**

Open `reports/index.html` in the browser preview. Every card link must resolve, and the console must be clean. Re-run Task 11's Step 2-4 assembly and walk if the hub changed any link target.

- [ ] **Step 3: Commit and push**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git add reports/index.html
git commit -m "reports: link the two new benchmarks from the hub

Adds cards for the Agent Build-Off and the Layout Skill Bench, and links the
preserved overview and perf-lines pages so they stay reachable from the site.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin HEAD
```

- [ ] **Step 4: Run the workflow**

The workflow triggers on push to `main`. This work is on a branch, so trigger it manually once merged, or dispatch it against the branch:

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
gh workflow run publish-pages.yml --ref "$(git branch --show-current)"
sleep 20
gh run list --workflow=publish-pages.yml --limit 3
```

Watch it to completion with `gh run watch`. If it fails, read the failing step's log and fix the cause — do not re-run hoping for a different result.

- [ ] **Step 5: Verify the live site**

```bash
cd /Users/vitor/LocalProjects/macstudio-local-llm
git fetch origin gh-pages
git ls-tree -r origin/gh-pages --name-only | head -40
git ls-tree -r origin/gh-pages --name-only | wc -l
```

Then open `https://snagnever.github.io/macstudio-local-llm/` in the browser and repeat Task 11 Step 4's walk against the live site. GitHub Pages can take a minute or two to serve a fresh push; if a page 404s, re-check before concluding it is broken.

- [ ] **Step 6: Report**

State which pages are live, which demos run, and what remains unverified. If anything is broken on the live site that passed locally, say so and name the difference.

---

## What this plan assumes from its predecessor

SVGBench was re-judged and published under a single judge by
`docs/superpowers/plans/2026-09-07-svgbench-rejudge.md`, which is complete. This
plan reuses `reports/harness-matrix-svgbench.html` as-is and does not re-open any
scoring question.
