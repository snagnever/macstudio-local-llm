# 2026-07-12 — DeepSeek-V4-Flash UD-Q2_K_XL (Unsloth) quant A/B campaign

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether Unsloth's dynamic 2-bit quant (UD-Q2_K_XL, 96.8 GB) beats the established teamblobfish IQ2_XS-XL baseline (81 GB) enough to become the canonical DeepSeek-V4-Flash build on this rig — same runtime, same flags, only the quant changes.

**Architecture:** Single-knob A/B — isolate the variable (the MTP-campaign lesson: never infer a knob's effect from a cross-format comparison). Every run uses the exact IQ2_XS-XL GO recipe (standalone `llama-server` 2.24.0, `--no-repack -c 32768 -np 1 -ngl 999`, port 1235, temp 0, thinking off) with only the model file and alias swapped. Cheap signals gate expensive ones: speed probe → ctx-speed sweep → tool-calling + HumanEval → decision gate → LCB v6 → Terminal-Bench 2.0 → synthesis.

**Tech Stack:** llama.cpp (LM Studio 2.24.0 beta binary), `tools/local-llm-bench-m4-32gb` (`speed_probe.py`, `tool_call_bench.py`, `bench2.py`), harbor + terminus-2 + Docker for Terminal-Bench.

## Global Constraints

- **Server recipe (verbatim, every phase):**
  ```bash
  BIN=~/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.24.0
  M=~/.lmstudio/models/unsloth/DeepSeek-V4-Flash-GGUF/DeepSeek-V4-Flash-UD-Q2_K_XL-00001-of-00003.gguf
  cd "$BIN" && ./llama-server -m "$M" -a deepseek-v4-flash-udq2kxl \
    --no-repack -c 32768 -np 1 -ngl 999 --host 127.0.0.1 --port 1235
  ```
  All three flags are load-bearing (2.24.0 = `deepseek4` arch; `--no-repack` = repack abort; `-np 1` = KV overcommit). Same as baseline except the model file + alias.
- **Model alias / results key:** `deepseek-v4-flash-udq2kxl` everywhere (mirrors `deepseek-v4-flash-iq2xs`).
- **Sole-model:** 90.6 GB resident — evict everything else (`lms ps` must be empty; no mlx_lm.server; no other llama-server).
- **Thinking OFF is the model's GGUF default** — DS4 GGUF emits 0 reasoning tokens on every generation (verified for iq2xs; re-verify once for this quant in Task 1). No `BENCH_NOTHINK_PREFILL` needed.
- **Sampling:** temp 0 greedy, seed 42 — identical to every baseline number we compare against.
- **Disk preflight before every phase:** `df -h /System/Volumes/Data` must show **≥150 GB free** (2026-07-12 incident: boot volume hit 0 during this model's download and bricked all tooling).
- **Background pattern:** `nohup bash <script> >/dev/null 2>&1 & disown` (this rig lacks setsid).
- **Results boundary (AGENTS.md):** distilled summaries → `bench/deepseek-v4-flash/results/`; raw logs → `bench/deepseek-v4-flash/logs/` (gitignored); canonical per-model scores land automatically in `tools/local-llm-bench-m4-32gb/benchmarks/runs/` (submodule — commit there separately, never git-touch it from a driver script).
- **Python:** bench client venv `/Users/vitor/LocalProjects/local-llms/.venv/bin/python`, invoked from `tools/local-llm-bench-m4-32gb/`.

## Baseline scoreboard to beat (teamblobfish IQ2_XS-XL, 2026-07-05, same server recipe)

| Signal | Baseline | Source |
|---|---|---|
| Resident memory | 82.3 GB flat | M4 notes |
| Generation speed | ~10 t/s sustained | M4 notes |
| jdhodges tool-calling (40) | **87.5%** (35/40) | `toolcall_jdhodges_deepseek-v4-flash-iq2xs_20260705_130905_summary.json` |
| Veerman tool-calling (12) | **58.3%** (7/12) | `toolcall_veerman_deepseek-v4-flash-iq2xs_20260705_132128_summary.json` |
| HumanEval (100) | **88%** (0 trunc, 187.6 min, max_tokens 32768) | `humaneval_deepseek-v4-flash-iq2xs_20260705_133115_summary.json` |
| LCB v6 | **86% partial (6/7)** — ⚠️ overnight finish never completed; baseline is still 7/50 rows | `livecodebench_deepseek-v4-flash-iq2xs_20260705_164011.jsonl` |
| Terminal-Bench 2.0 | not run for this model; cross-model refs: MiniMax-M2.5 25.8%, Qwen3.5-122B 24.7% | tbench campaign |

UD-Q2_K_XL smoke facts (2026-07-12, this session): loads clean, **90.6 GB resident dead-flat** through an 1,800-token gen, **10.9–11.2 t/s** gen, 11.5–15.9 t/s prefill on short prompts, coherent output at temp 0.

---

### Task 1: Preflight + speed probe (3-question, thinking off)

**Files:**
- Create: `bench/deepseek-v4-flash/scripts/run-udq2kxl-speed-probe.sh`
- Output: `tools/local-llm-bench-m4-32gb/results/speed_probe/deepseek-v4-flash-udq2kxl_*` (submodule), driver log in `bench/deepseek-v4-flash/logs/`

**Interfaces:**
- Produces: a healthy server on `http://127.0.0.1:1235/v1` (later tasks reuse the same recipe), speed-probe JSON with per-question t/s, and a confirmed `reasoning_tokens == 0` check.

- [ ] **Step 1: Write the driver script**

```bash
cat > bench/deepseek-v4-flash/scripts/run-udq2kxl-speed-probe.sh <<'EOF'
#!/usr/bin/env bash
# UD-Q2_K_XL campaign Task 1 — preflight + 3-question speed probe (thinking off).
# Usage: bash bench/deepseek-v4-flash/scripts/run-udq2kxl-speed-probe.sh
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/udq2kxl-speed-probe-driver.log
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

# --- disk preflight (2026-07-12 incident rule) ---
FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: only ${FREE_GB}GB free (<150)"; exit 1; }
say "disk ok: ${FREE_GB}GB free"

# --- sole-model preflight ---
pgrep -f mlx_lm.server >/dev/null && { say "ABORT: mlx_lm.server running"; exit 1; }
/Users/vitor/.lmstudio/bin/lms ps 2>/dev/null | grep -q . && { say "ABORT: LM Studio has a model loaded"; exit 1; }

# --- server up (reuse if already healthy with right alias) ---
if ! curl -sf http://127.0.0.1:1235/health >/dev/null 2>&1; then
  BIN=~/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.24.0
  M=~/.lmstudio/models/unsloth/DeepSeek-V4-Flash-GGUF/DeepSeek-V4-Flash-UD-Q2_K_XL-00001-of-00003.gguf
  SRVLOG=$LOGDIR/udq2kxl-server.log
  ( cd "$BIN" && nohup ./llama-server -m "$M" -a deepseek-v4-flash-udq2kxl \
      --no-repack -c 32768 -np 1 -ngl 999 --host 127.0.0.1 --port 1235 \
      > "$SRVLOG" 2>&1 & disown )
  for i in $(seq 1 120); do
    curl -sf http://127.0.0.1:1235/health >/dev/null 2>&1 && break; sleep 5
  done
fi
curl -sf http://127.0.0.1:1235/health >/dev/null || { say "ABORT: server not healthy"; exit 1; }
say "server healthy"

# --- thinking-off verification: one generation, assert 0 reasoning tokens ---
RT=$(curl -s http://127.0.0.1:1235/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash-udq2kxl","messages":[{"role":"user","content":"Why is the sky blue? One sentence."}],"max_tokens":128,"temperature":0}' \
  | /Users/vitor/LocalProjects/local-llms/.venv/bin/python -c \
  "import json,sys; d=json.load(sys.stdin); u=d.get('usage',{}); print(u.get('completion_tokens_details',{}).get('reasoning_tokens',0)); print(d['choices'][0]['message']['content'][:100],file=sys.stderr)")
say "reasoning_tokens=$RT (must be 0)"
[ "$RT" = "0" ] || say "WARNING: nonzero reasoning tokens — investigate before benching"

# --- 3-question speed probe ---
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
cd "$ROOT/tools/local-llm-bench-m4-32gb"
"$ROOT/.venv/bin/python" scripts/speed_probe.py deepseek-v4-flash-udq2kxl results/speed_probe \
  2>&1 | tee -a "$DRIVER"
say "speed probe done — results in tools/local-llm-bench-m4-32gb/results/speed_probe/"
EOF
chmod +x bench/deepseek-v4-flash/scripts/run-udq2kxl-speed-probe.sh
```

- [ ] **Step 2: Run it**

Run: `bash bench/deepseek-v4-flash/scripts/run-udq2kxl-speed-probe.sh`
Expected: `disk ok`, `server healthy`, `reasoning_tokens=0`, then three probe questions completing with per-question tok/s ≈ 10–12 in the output JSON. Sanity answers: `4`, `A`, a valid Python function.

- [ ] **Step 3: Distill the numbers**

Read `tools/local-llm-bench-m4-32gb/results/speed_probe/deepseek-v4-flash-udq2kxl_<ts>.json`; record cold-load time (if server was cold), per-question gen t/s, and RSS (`ps -eo rss,comm | grep llama-server`) into a one-paragraph entry appended to `bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md` (create the file with a `# UD-Q2_K_XL campaign log` header on first touch).

- [ ] **Step 4: Commit**

```bash
rtk git add bench/deepseek-v4-flash/scripts/run-udq2kxl-speed-probe.sh bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md
rtk git commit -m "bench(ds4-udq2kxl): Task 1 — preflight + speed probe driver + first numbers"
```

---

### Task 2: Context-vs-speed sweep (decode t/s at KV depth)

The upstream `context_speed_bench.py` loads models via the LM Studio API — **blocked** for `deepseek4` (repack abort, no `--no-repack` in `lms load`). So this task uses a standalone probe against the already-running llama-server: one server at `-c 32768`, synthetic prompts filled to increasing depths, measuring prefill t/s and decode t/s per depth. This quantifies "how far does decode fall as context fills" — the piece the 3-question probe doesn't cover (same rationale as the MiniMax IQ2_M sweep).

**Files:**
- Create: `bench/deepseek-v4-flash/scripts/udq2kxl_ctx_probe.py`
- Output: `bench/deepseek-v4-flash/results/udq2kxl-ctxspeed.json` (distilled, tracked)

**Interfaces:**
- Consumes: healthy server from Task 1 (`http://127.0.0.1:1235/v1`, alias `deepseek-v4-flash-udq2kxl`).
- Produces: JSON list of `{"depth": int, "prompt_tokens": int, "prefill_tps": float, "decode_tps": float, "rss_gb": float}` — Task 8 charts/cites it.

- [ ] **Step 1: Write the probe**

```python
# bench/deepseek-v4-flash/scripts/udq2kxl_ctx_probe.py
#!/usr/bin/env python3
"""Decode-speed-vs-context-depth probe for deepseek-v4-flash-udq2kxl.

One llama-server at -c 32768; per target depth, send a synthetic prompt of
~depth tokens and generate 256 tokens at temp 0. Records llama-server's own
timings (prompt_per_second / predicted_per_second) plus process RSS.

Usage: .venv/bin/python bench/deepseek-v4-flash/scripts/udq2kxl_ctx_probe.py
"""
import json, subprocess, urllib.request

BASE = "http://127.0.0.1:1235/v1"
MODEL = "deepseek-v4-flash-udq2kxl"
DEPTHS = [512, 2048, 4096, 8192, 16384, 24576, 30720]  # ctx is 32768; leave gen headroom
OUT = "bench/deepseek-v4-flash/results/udq2kxl-ctxspeed.json"

# ~1 token per word for this filler; oversupply then rely on server-side truncation margin
FILLER_SENTENCE = ("The quick brown fox jumps over the lazy dog near the riverbank "
                   "while autumn leaves drift across the quiet meadow at dusk. ")

def rss_gb():
    out = subprocess.run(["ps", "-eo", "rss,comm"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "llama-server" in line:
            return round(int(line.split()[0]) / 1024 / 1024, 1)
    return None

def probe(depth):
    words_needed = int(depth * 0.75)  # sentence above ≈ 1.33 words/token
    filler = (FILLER_SENTENCE * (words_needed // 20 + 1))
    prompt = (filler + "\n\nIgnore all text above. In one short paragraph, "
              "explain what a hash map is.")
    body = json.dumps({"model": MODEL,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 256, "temperature": 0}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.load(r)
    t = d.get("timings", {})
    return {"depth": depth,
            "prompt_tokens": d.get("usage", {}).get("prompt_tokens"),
            "prefill_tps": round(t.get("prompt_per_second", 0), 1),
            "decode_tps": round(t.get("predicted_per_second", 0), 1),
            "rss_gb": rss_gb()}

if __name__ == "__main__":
    results = []
    for depth in DEPTHS:
        row = probe(depth)
        print(row, flush=True)
        results.append(row)
        with open(OUT, "w") as f:            # write-through: partial results survive a crash
            json.dump(results, f, indent=1)
    print(f"wrote {OUT}")
```

- [ ] **Step 2: Run it** (foreground; ~20–40 min — the 30k prefill alone is minutes)

Run: `cd /Users/vitor/LocalProjects/local-llms && .venv/bin/python bench/deepseek-v4-flash/scripts/udq2kxl_ctx_probe.py`
Expected: 7 rows printed with monotonically growing `prompt_tokens`; `decode_tps` starting ~11 shallow and declining with depth; `rss_gb` roughly flat around 90.6 (KV for 32k already reserved at load).

- [ ] **Step 3: Sanity-check the curve**

If `decode_tps` at depth 30720 is < 50% of the shallow value, note it prominently — that changes the Terminal-Bench viability estimate (terminus-2 runs deep contexts). Append the table to `bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md`.

- [ ] **Step 4: Commit**

```bash
rtk git add bench/deepseek-v4-flash/scripts/udq2kxl_ctx_probe.py bench/deepseek-v4-flash/results/udq2kxl-ctxspeed.json bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md
rtk git commit -m "bench(ds4-udq2kxl): Task 2 — context-vs-speed sweep"
```

---

### Task 3: Cheap quality signals — jdhodges (40) + Veerman (12) + HumanEval (100)

Ordered cheapest-first; jdhodges + Veerman together are ~30–45 min, HumanEval ~3 h (baseline took 187.6 min at ~10 t/s). One driver script runs all three sequentially so it can go unattended.

**Files:**
- Create: `bench/deepseek-v4-flash/scripts/run-udq2kxl-cheap-signals.sh`
- Output: `tools/local-llm-bench-m4-32gb/benchmarks/runs/{toolcall_jdhodges,toolcall_veerman,humaneval}_deepseek-v4-flash-udq2kxl_*` (submodule)

**Interfaces:**
- Consumes: healthy server (Task 1 recipe).
- Produces: three `*_summary.json` files with `score_pct` — Task 4's gate reads them.

- [ ] **Step 1: Write the driver**

```bash
cat > bench/deepseek-v4-flash/scripts/run-udq2kxl-cheap-signals.sh <<'EOF'
#!/usr/bin/env bash
# UD-Q2_K_XL Task 3 — jdhodges (40) -> Veerman (12) -> HumanEval (100), sequential.
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-udq2kxl-cheap-signals.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
DRIVER=$LOGDIR/udq2kxl-cheap-signals-driver.log
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "cheap-signals START"

FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: ${FREE_GB}GB free"; exit 1; }
curl -sf http://127.0.0.1:1235/health >/dev/null || { say "ABORT: server down"; exit 1; }

PY=$ROOT/.venv/bin/python
cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
export BENCH_TIMEOUT=3600

say "jdhodges START"
"$PY" scripts/tool_call_bench.py --model deepseek-v4-flash-udq2kxl --suite jdhodges \
  --base-url http://127.0.0.1:1235/v1 --force > "$LOGDIR/udq2kxl-toolcall-jdhodges.log" 2>&1
say "jdhodges rc=$?"

say "veerman START"
"$PY" scripts/tool_call_bench.py --model deepseek-v4-flash-udq2kxl --suite veerman \
  --base-url http://127.0.0.1:1235/v1 --force > "$LOGDIR/udq2kxl-toolcall-veerman.log" 2>&1
say "veerman rc=$?"

say "humaneval START (expect ~3h)"
"$PY" scripts/bench2.py humaneval --examples 100 --model deepseek-v4-flash-udq2kxl \
  --max-tokens 32768 > "$LOGDIR/udq2kxl-humaneval.log" 2>&1
say "humaneval rc=$?"
say "cheap-signals DONE"
EOF
chmod +x bench/deepseek-v4-flash/scripts/run-udq2kxl-cheap-signals.sh
```

- [ ] **Step 2: Launch unattended**

Run: `nohup bash bench/deepseek-v4-flash/scripts/run-udq2kxl-cheap-signals.sh >/dev/null 2>&1 & disown`
Expected: driver log shows the three START/rc lines over ~4 h; three summary JSONs appear under `tools/local-llm-bench-m4-32gb/benchmarks/runs/`.

- [ ] **Step 3: Verify completion + collect scores**

Run: `for f in tools/local-llm-bench-m4-32gb/benchmarks/runs/*deepseek-v4-flash-udq2kxl*_summary.json; do python3 -c "import json;d=json.load(open('$f'));print(d['run_name'],d['score_pct'],'trunc:',d.get('truncated'))"; done`
Expected: three lines. Baselines to beat: jdhodges 87.5%, Veerman 58.3%, HumanEval 88.0% / 0 trunc.

- [ ] **Step 4: Append scores to campaign log + commit**

```bash
rtk git add bench/deepseek-v4-flash/scripts/run-udq2kxl-cheap-signals.sh bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md
rtk git commit -m "bench(ds4-udq2kxl): Task 3 — tool-calling + HumanEval scores"
```
(Submodule score files get committed inside `tools/local-llm-bench-m4-32gb` on its results branch in Task 8 — never from here.)

---

### Task 4: Decision gate (no code)

- [ ] **Step 1: Apply the gate**

| Outcome | Action |
|---|---|
| UD ≥ baseline on ≥2 of 3 signals (jdhodges/Veerman/HumanEval), none catastrophically down | **Proceed** to Task 5 (LCB) and Task 6 (TBench) |
| UD below baseline across the board | **Stop** — write the NO-GO verdict in the campaign log, skip to Task 8 (synthesis), keep IQ2_XS-XL canonical, consider deleting the 97 GB quant |
| Mixed / within noise (±2 pts) | Proceed, but note that the +8 GB memory cost needs LCB/TBench to justify itself |

Record the gate decision with a dated line in `bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md`.

---

### Task 5: LiveCodeBench v6 (50, overnight)

⚠️ Baseline caveat: the IQ2_XS-XL LCB run is still **partial (6/7, 7 of 50 rows)** — its 2026-07-05 overnight arm never completed. The UD run below gives the first full-50 DS4 number. Optional Step 4 backfills the baseline for a true A/B.

**Files:**
- Create: `bench/deepseek-v4-flash/scripts/run-udq2kxl-lcb.sh`
- Output: `tools/local-llm-bench-m4-32gb/benchmarks/runs/livecodebench_deepseek-v4-flash-udq2kxl_*`

**Interfaces:**
- Consumes: healthy server (Task 1 recipe).
- Produces: LCB jsonl + summary; Task 8 cites `score_pct`.

- [ ] **Step 1: Write the driver**

```bash
cat > bench/deepseek-v4-flash/scripts/run-udq2kxl-lcb.sh <<'EOF'
#!/usr/bin/env bash
# UD-Q2_K_XL Task 5 — LCB v6 full 50. Some cases blow to 11k tok / ~19 min; expect 6-12h.
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-udq2kxl-lcb.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
DRIVER=$LOGDIR/udq2kxl-lcb-driver.log
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "LCB START"
FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: ${FREE_GB}GB free"; exit 1; }
curl -sf http://127.0.0.1:1235/health >/dev/null || { say "ABORT: server down"; exit 1; }
cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
export BENCH_TIMEOUT=3600
"$ROOT/.venv/bin/python" scripts/bench2.py livecodebench --examples 50 \
  --model deepseek-v4-flash-udq2kxl --lcb-version release_v6 --max-tokens 32768 \
  > "$LOGDIR/udq2kxl-lcb.log" 2>&1
say "LCB rc=$?"
EOF
chmod +x bench/deepseek-v4-flash/scripts/run-udq2kxl-lcb.sh
```

- [ ] **Step 2: Launch before end of day** (it self-checks the server; run overnight)

Run: `nohup bash bench/deepseek-v4-flash/scripts/run-udq2kxl-lcb.sh >/dev/null 2>&1 & disown`
Expected: `livecodebench_deepseek-v4-flash-udq2kxl_*_summary.json` by morning with 50 rows.

- [ ] **Step 3: Collect + log the score** (append to campaign log; compare vs partial-baseline 86% and cross-model LCB slots in `docs/local-llm-reference.md`)

- [ ] **Step 4 (optional, user's call): backfill the IQ2_XS-XL baseline to full 50** — rerun the same command with the baseline model file/alias (`teamblobfish` GGUF, `-a deepseek-v4-flash-iq2xs`) the following night, so the A/B is 50-vs-50 rather than 50-vs-7. Costs one more overnight; skip if the UD verdict is already decisive.

- [ ] **Step 5: Commit** (driver script + campaign log line, same pattern as Task 3.)

---

### Task 6: Terminal-Bench 2.0 (89 tasks, terminus-2, 0.5× cap)

First-ever DS4 Terminal-Bench number (the old script targeted the MLX build during the OOM era and produced nothing usable). Cross-model refs: MiniMax-M2.5 25.8%, Qwen3.5-122B 24.7%. This is the longest phase (many hours; deep contexts — Task 2's depth curve predicts effective speed).

**Files:**
- Create: `bench/terminal-bench/scripts/run-tbench-ds4-udq2kxl.sh`
- Output: `bench/terminal-bench/logs/tbench-runs/<job>` + harbor results

**Interfaces:**
- Consumes: healthy llama-server (Task 1 recipe) + Docker Desktop running.
- Produces: harbor job dir with per-task pass/fail; Task 8 cites the aggregate %.

- [ ] **Step 1: Write the driver** (adapted from `run-tbench-deepseek-v4-flash.sh`; base URL and model changed — llama-server, unlike mlx_lm.server, accepts the alias as the model name)

```bash
cat > bench/terminal-bench/scripts/run-tbench-ds4-udq2kxl.sh <<'EOF'
#!/usr/bin/env bash
# UD-Q2_K_XL Task 6 — Terminal-Bench 2.0 (89 tasks) via harbor/terminus-2 against llama-server :1235.
# Usage: nohup bash bench/terminal-bench/scripts/run-tbench-ds4-udq2kxl.sh > /dev/null 2>&1 & disown
set -u
REPO=/Users/vitor/LocalProjects/local-llms
cd "$REPO"
mkdir -p bench/terminal-bench/logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:1235/v1"
export OPENAI_API_KEY="not-needed"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"
LOGDIR=$REPO/bench/terminal-bench/logs
DRIVER_LOG="$LOGDIR/tbench-ds4-udq2kxl-driver.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"
FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { echo "ABORT: ${FREE_GB}GB free" >> "$DRIVER_LOG"; exit 1; }
curl -sf http://127.0.0.1:1235/health >/dev/null || { echo "ABORT: server down" >> "$DRIVER_LOG"; exit 1; }
harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/deepseek-v4-flash-udq2kxl" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name ds4-udq2kxl \
  > "$LOGDIR/tbench-ds4-udq2kxl.log" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
EOF
chmod +x bench/terminal-bench/scripts/run-tbench-ds4-udq2kxl.sh
```

- [ ] **Step 2: Preflight Docker + one-task smoke** — Docker Desktop must be running (`docker info` succeeds). Before the full 89, do a single-task smoke to validate the LiteLLM→llama-server path end-to-end: temporarily add `--task-name` for one known-simple task (check `harbor run --help` for the exact flag; prior campaigns used full runs, so verify) or accept the first task of a full launch and watch `tbench-ds4-udq2kxl.log` for a completed episode before leaving it unattended. A model-name rejection would appear in the first minute.

- [ ] **Step 3: Launch the full run**

Run: `nohup bash bench/terminal-bench/scripts/run-tbench-ds4-udq2kxl.sh > /dev/null 2>&1 & disown`
Expected: many-hour run; harbor writes per-task results under `bench/terminal-bench/logs/tbench-runs/ds4-udq2kxl*`.

- [ ] **Step 4: Collect the aggregate** — harbor prints the final resolved/unresolved count in the run log tail; compute % of 89, append to campaign log with the MiniMax 25.8% / 122B 24.7% comparison.

- [ ] **Step 5: Commit** (driver script + campaign log line.)

---

### Task 7: (conditional) speed regression follow-up

Only if Task 2 showed decode collapsing at depth or any bench logged sustained t/s well below the ~11 t/s shallow figure: rerun the scenario throughput harness (`tools/local-llm-bench/bench.py` — effective tok/s under realistic scenarios) for `deepseek-v4-flash-udq2kxl` vs `deepseek-v4-flash-iq2xs` back-to-back, same day, and add the comparison to the campaign log. Otherwise skip — don't pad the campaign.

---

### Task 8: Synthesis — verdict, docs, promotion

**Files:**
- Modify: `docs/models/deepseek-v4-flash/README.md` (variants table: add UD-Q2_K_XL row with status; quality table: add UD column; History: dated entry)
- Modify: `bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md` (final verdict block)
- Submodule: commit new run files inside `tools/local-llm-bench-m4-32gb` (its own results branch, per repo convention)
- Possibly modify: `docs/local-llm-reference.md` (if UD-Q2_K_XL displaces IQ2_XS-XL as the canonical DS4 build)

**Interfaces:**
- Consumes: all summary JSONs + campaign log.
- Produces: the campaign's citable verdict.

- [ ] **Step 1: Write the verdict** — one of: **UPGRADE** (UD becomes canonical; IQ2_XS-XL 81 GB freed), **KEEP BASELINE** (delete UD, reclaim 97 GB), or **SPLIT** (per-workload winner — say which workload picks which quant). Justify with the score table; memory cost (+8.3 GB resident) is part of the call.

- [ ] **Step 2: Update `docs/models/deepseek-v4-flash/README.md`** — variants table row (source repo `unsloth/DeepSeek-V4-Flash-GGUF`, 96.8 GB, 3 shards, status per verdict), measured-performance and quality tables, History entry dated with the run dates. Also fix the stale note that mainline llama.cpp lacks `deepseek4`: upstream added it in [llama.cpp PR #24162](https://github.com/ggml-org/llama.cpp/pull/24162) (KV-quant multi-turn fix in PR #25202) — the 2.24.0-beta constraint is now historical.

- [ ] **Step 3: Commit submodule results** — inside `tools/local-llm-bench-m4-32gb`, add the new `benchmarks/runs/*udq2kxl*` + `results/speed_probe/*udq2kxl*` files and an M4 notes section, commit on its results branch; then commit the pointer bump in the superproject.

- [ ] **Step 4: Final repo commit + PR**

```bash
rtk git add docs/models/deepseek-v4-flash/README.md bench/deepseek-v4-flash/results/ docs/local-llm-reference.md
rtk git commit -m "bench(ds4-udq2kxl): campaign verdict — <UPGRADE|KEEP BASELINE|SPLIT>"
rtk git push -u origin bench/deepseek-v4-udq2kxl
# then: gh pr create against main
```
