# Astra SVGBench Parallel Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and integrate 28 SVGBench SVG artifacts from seven parallel `gpt-6-astra` agents.

**Architecture:** The root agent coordinates seven isolated agents in waves of three, three, and one. Each agent owns one prompt and four files. The root validates artifacts before updating shared metadata.

**Tech Stack:** Codex multi-agent tools, `gpt-6-astra`, SVG/XML, Python 3, existing SVGBench tools.

**Spec:** `docs/superpowers/specs/2026-09-12-astra-svgbench-parallel-run-design.md`

## Global Constraints

- Use `gpt-6-astra` with reasoning effort `medium`.
- Use `fork_turns: none` for every child agent.
- Run at most three child agents concurrently.
- Store artifacts in `bench/harness-matrix/logs/codex/gpt-6-astra/`.
- Child agents must not inspect existing SVGs, reports, renders, scores, or verdicts.
- Preserve unrelated working-tree changes.
- Stop new repair work when estimated use reaches 350 Codex credits.
- Do not create judge verdicts during this execution.

---

### Task 1: Preflight and assignment map

**Files:**
- Read: `AGENTS.md`
- Read: `bench/harness-matrix/scripts/svgbench/questions.json`
- Read: `bench/harness-matrix/results/codex/gpt-5.6-sol.md`

**Interfaces:**
- Consumes: SVGBench question indexes `0`, `4`, `5`, `6`, `7`, `12`, and `13`
- Produces: fixed prompt-to-slug assignments

- [ ] **Step 1: Record the working-tree baseline**

Run `git status --short --untracked-files=all`.

Expected: existing Sol artifacts and report changes can be present. No Astra output path exists.

- [ ] **Step 2: Verify the source prompts**

Run:

```bash
jq '.[0], .[4], .[5], .[6], .[7], .[12], .[13]' bench/harness-matrix/scripts/svgbench/questions.json
```

Expected: seven objects with `prompt` and `requirements`.

- [ ] **Step 3: Use the fixed assignment map**

```text
0  cow-plowing
4  rubber-ducky
5  picnic-on-clouds
6  stunt-car
7  dolphin
12 fruit-stall
13 treasure-barrel
```

Each slug produces `-v1.svg`, `-v2.svg`, `-v3.svg`, and `-animated.svg`.

### Task 2: Generate seven prompt families

**Files:**
- Create: `bench/harness-matrix/logs/codex/gpt-6-astra/*.svg`

**Interfaces:**
- Consumes: one exact prompt and its complete requirements array per agent
- Produces: four SVG files and a summary per agent

- [ ] **Step 1: Dispatch wave one**

Dispatch question indexes `0`, `4`, and `5` concurrently.
Set model `gpt-6-astra`, effort `medium`, and `fork_turns: none`.

Use this instruction with the assigned index and slug:

```text
Create four self-contained SVG artifacts for SVGBench question INDEX.
Read only AGENTS.md and array element INDEX from bench/harness-matrix/scripts/svgbench/questions.json.
Do not inspect any existing SVG, report, render, score, or verdict.
Write only SLUG-v1.svg, SLUG-v2.svg, SLUG-v3.svg, and SLUG-animated.svg under bench/harness-matrix/logs/codex/gpt-6-astra/.
Create v1 first. Make v2 and v3 intentional visual revisions.
Create animated from the best static composition with SVG or CSS animation.
Use no external resources. Ensure every file is valid XML.
Do not modify shared metadata or any other file.
Return the four paths and a concise description of each revision.
```

- [ ] **Step 2: Dispatch wave two as slots open**

Dispatch question indexes `6`, `7`, and `12` with the same instruction.
Use long event waits. Do not poll completed agents repeatedly.

- [ ] **Step 3: Dispatch wave three**

Dispatch question index `13` after a slot opens.
Wait for all seven agents to finish or request attention.

### Task 3: Validate Astra artifacts

**Files:**
- Inspect: `bench/harness-matrix/logs/codex/gpt-6-astra/*.svg`

**Interfaces:**
- Consumes: 28 generated SVG files
- Produces: a pass or exact validation errors

- [ ] **Step 1: Verify the filename set**

Run:

```bash
find bench/harness-matrix/logs/codex/gpt-6-astra -maxdepth 1 -type f -name '*.svg' -print | sort
```

Expected: exactly 28 files across seven slugs and four takes.

- [ ] **Step 2: Parse every file as XML**

Run:

```bash
python3 -c "import glob,xml.etree.ElementTree as E; fs=glob.glob('bench/harness-matrix/logs/codex/gpt-6-astra/*.svg'); assert len(fs)==28, len(fs); assert all(E.parse(f).getroot().tag.endswith('svg') for f in fs); print('28 SVG files parse as XML')"
```

Expected: `28 SVG files parse as XML`.

- [ ] **Step 3: Reject external resources**

Run:

```bash
rg -n -i 'https?://' bench/harness-matrix/logs/codex/gpt-6-astra/*.svg
```

Expected: no matches.

- [ ] **Step 4: Verify animation markup**

Run:

```bash
for f in bench/harness-matrix/logs/codex/gpt-6-astra/*-animated.svg; do rg -q '<animate|<animateTransform|@keyframes|animation:' "$f" || echo "missing animation: $f"; done
```

Expected: no output.

- [ ] **Step 5: Repair failed families once**

Send the original agent only its failed paths and validation errors.
Request structural repair only. Repeat Steps 1 through 4 once.

### Task 4: Integrate the Astra pair

**Files:**
- Create: `bench/harness-matrix/results/codex/gpt-6-astra.md`
- Modify: `bench/harness-matrix/results/svgbench/participants.json`
- Modify: `bench/harness-matrix/results/svgbench/manifest.json`
- Modify: `bench/harness-matrix/results/svgbench/scores.json`
- Modify: `reports/harness-matrix-svgbench.html`
- Modify: artifact report outputs selected by `tools/artifacts_data.py`

**Interfaces:**
- Consumes: validated artifacts and existing evaluator commands
- Produces: an unscored `codex/gpt-6-astra` pair in metadata and reports

- [ ] **Step 1: Write the pair record**

Match `bench/harness-matrix/results/codex/gpt-5.6-sol.md`.
Record date `2026-09-12`, model, effort, procedure, 28 artifacts, and unscored status.

- [ ] **Step 2: Add the participant entry**

Add key `codex/gpt-6-astra` to `participants.json`.
Set harness `Codex`, hosted `true`, effort `medium`, date, and source path.

- [ ] **Step 3: Regenerate manifest and scores**

Run:

```bash
python3 bench/harness-matrix/scripts/svgbench/svgbench_eval.py manifest
python3 bench/harness-matrix/scripts/svgbench/svgbench_eval.py score
```

Expected: 28 Astra artifacts appear as unscored. Existing score means do not change.

- [ ] **Step 4: Refresh reports**

Run the gallery generator documented in `.claude/skills/svgbench-eval/SKILL.md`.
Run the artifact-data generator documented in `reports/README.md`.

### Task 5: Verify and record the run

**Files:**
- Verify: all files from Tasks 2 through 4

**Interfaces:**
- Consumes: integrated artifacts, metadata, reports, and tests
- Produces: verification evidence and one isolated commit

- [ ] **Step 1: Run focused tests**

```bash
python3 -m pytest bench/harness-matrix/tests/test_svgbench_eval.py bench/harness-matrix/tests/test_gallery_data.py tools/tests/test_artifacts_data.py
```

Expected: all selected tests pass.

- [ ] **Step 2: Run repository validation**

Run `task validate`.

Expected: exit status 0.

- [ ] **Step 3: Inspect the final diff**

Run `git status --short --untracked-files=all` and `git diff --check`.

Expected: no whitespace errors. Existing unrelated changes remain intact.

- [ ] **Step 4: Commit only Astra run files**

Stage the Astra directory, Astra pair record, and verified regenerated shared files.
Do not stage unrelated files from the baseline.

Commit with:

```bash
git commit -m "bench(svgbench): add parallel Astra artifact series"
```
