# 2026-07-10 — qwen3.6-35b-a3b UD-MLX-4bit: daily-driver candidate benchmark plan

## Context

A new quant of the already-benched `qwen3.6-35b-a3b` landed on the rig:
`unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` (LM Studio API id
**`qwen3.6-35b-a3b-ud-mlx`**), Unsloth's **dynamic 4-bit** MLX conversion —
**20 GB on disk**, vs the daily driver `@6bit` (27 GB) and `@8bit` (37.75 GB).

| Model (LM Studio id) | Source | Format / quant | Disk | Role |
|---|---|---|---:|---|
| `qwen3.6-35b-a3b@6bit` | mlx-community | MLX 6-bit | 27 GB | 🟢 **DAILY DRIVER** (baseline) |
| `qwen3.6-35b-a3b-ud-mlx` | unsloth | **MLX UD-4bit** | **20 GB** | ⚗️ **candidate under test** |
| `qwen3.6-35b-a3b@8bit` | mlx-community | MLX 8-bit | 37.75 GB | ⏸ quant A/B pending (Phase 2 #9) |

### The bet

Unsloth's UD ("Unsloth Dynamic") quants keep the layers that matter at higher
precision and squeeze the rest, pitching **near-higher-quant quality at a
4-bit footprint**. The question:

> **Does UD-4bit preserve `@6bit` daily-driver quality while being 26 % smaller
> (and, being 4-bit, faster to decode / cheaper to page)?** If yes it is a
> strictly better daily driver — more pairing headroom (20 GB pairs with far
> more), faster loops, same slot. If it gives up meaningful quality it stays a
> curiosity and `@6bit` keeps the slot.

Unlike the [MTP GGUF study](../qwen3.6-mtp/plan.md), this is a **clean quant A/B**:
same weights family, same MLX format, same runtime, same rig — the only variable
is the quantization. Deltas are quant-isolated (per
[isolate-the-variable](../../docs/models/qwen3.6-35b-a3b.md)).

### The landmine (why tool-calling goes first)

`docs/models/qwen3.6-35b-a3b.md` records that **`mlx-community` 4-bit MoE
checkpoints of this model had a tool-call regression** (malformed calls) that did
**not** reproduce on the 6-bit conversion. A UD **4-bit MoE** sits squarely in
that danger zone. So tool-calling is both the **first cheap signal** (it heads the
committed ladder anyway) and the **primary go/no-go**: if calls come back
malformed, the model is dead for the agent / daily-driver slot and we stop before
spending the expensive tail.

## Config (locked to the `@6bit` scoreboard for apples-to-apples)

Every number must be comparable to the `@6bit` row in
[testing-plan.md](../../docs/testing-plan.md) and
[docs/models/qwen3.6-35b-a3b.md](../../docs/models/qwen3.6-35b-a3b.md), so we
reuse its exact config:

- **Runtime:** LM Studio MLX, sole model, clean state, `--gpu max`.
- **Context:** `65,536` (the agentic-loop ctx `@6bit` and LCB ran at).
- **Quality benches:** `temp 0, seed 42`, thinking **on** (it is a thinking
  model), `n=100` per knowledge bench, **LCB v6 `n=50` at `--max-tokens 65536`**
  (matches the 2026-05-24 backfill), jdhodges `40`, veerman `12`.
- **Throughput:** `--no-think`. Works here — the UD-MLX build ships an external
  `chat_template.jinja` for the harness to patch (unlike the MTP GGUF, whose
  embedded template forced the `BENCH_NOTHINK_PREFILL` workaround).
- **Baseline:** `qwen3.6-35b-a3b@6bit`, same rig. `@6bit` anchors are already
  recorded — no rerun needed unless a same-session sanity re-anchor is wanted.

### `@6bit` anchors (targets to match-or-beat)

| Signal | `@6bit` |
|---|---|
| gen t/s (creative / doc-sum / ops-agent / prefill) | 91.6 / 91.7 / 85.5 / 85.5 |
| eff t/s (same order) | 86.9 / 55.9 / 71.4 / 22.9 |
| jdhodges (40) / veerman (12) | **97.5 %** / **75.0 %** |
| HumanEval / LCB v6 (n=50) / MMLU | 87 % / 54 % / 83 % |
| MATH / DROP / GPQA raw | 89 % / 89 % / 65 % |
| Terminal-Bench 2.0 (0.5x cap) | **28.1 %** (#3 on rig) |

## Phase 0 — preflight + tool-call sanity (minutes) · **HARD GATE**

Confirm the served id and clean state, then a **3-call tool-use sanity probe**
before spending anything — the 4-bit MoE tool-call landmine.

```bash
/Users/vitor/.lmstudio/bin/lms unload --all
/Users/vitor/.lmstudio/bin/lms load qwen3.6-35b-a3b-ud-mlx \
  --context-length 65536 --gpu max --parallel 4 --ttl 172800 -y
curl -s http://127.0.0.1:1234/v1/models | tr ',' '\n' | grep -i '"id"'   # expect qwen3.6-35b-a3b-ud-mlx
```

Sanity probe: a handful of `tool_call_bench.py --suite jdhodges --only <3 ids>`
cases (or a raw curl with a `tools` payload). **Gate:** if the model emits
malformed / unparsed tool calls, **stop** — record DOA in Results, skip Phases
1–3. This is the mlx-community-4bit regression reproducing.

## Phase 1 — speed (~30 min)

**1a — 3-question speed probe.** Clean single-stream decode t/s vs `@6bit`'s
~90 t/s sustained. Reuse the MTP driver shape (sole model, `--parallel 1`,
`speed_probe.py`), left resident for 1b.

```bash
# adapt bench/qwen3.6-mtp/scripts/run-qwen36-mtp-speedprobe.sh:
#   MODEL=qwen3.6-35b-a3b-ud-mlx, CTX=65536, --parallel 1
# writes results/speed_probe/qwen3.6-35b-a3b-ud-mlx_*.json + macmon telemetry
```

**1b — scenario-throughput sweep (the real speed test).** The
`tools/local-llm-bench` harness, 4 text scenarios, gen + **effective** t/s.
Because the external `chat_template.jinja` is present, use the harness's native
`--no-think` (no `BENCH_NOTHINK_PREFILL`).

```bash
# adapt bench/qwen3.6-mtp/scripts/run-qwen36-mtp-scenarios.sh (drop BENCH_NOTHINK_PREFILL,
# pass --no-think): for sc in creative-writing doc-summary ops-agent prefill-test
cd tools/local-llm-bench
python3 bench.py --backend lmstudio --no-think \
  --scenario scenarios/$sc.json \
  --model qwen3.6-35b-a3b-ud-mlx --model-label qwen3.6-35b-a3b-ud-mlx-4bit
```

Compare gen + eff to the `@6bit` anchors above. **Expectation:** 4-bit should be
≥ `@6bit` on decode (fewer bits to move); watch effective t/s on the
prefill-heavy ops-agent / prefill-test.

## Phase 2 — cheap-signal ladder (the committed order)

`tool-calling → HumanEval → LCB → MMLU` — the Phase-5 cheap-signal ladder from
[testing-plan.md](../../docs/testing-plan.md). Phase 0 ran only a 3-call sanity
probe; here tool-calling runs at full `n` alongside the rest.

```bash
cd tools/local-llm-bench-m4-32gb
M=qwen3.6-35b-a3b-ud-mlx
# 1. tool-calling (the landmine, now at full n)
python3 scripts/tool_call_bench.py --model $M --suite jdhodges   # 40
python3 scripts/tool_call_bench.py --model $M --suite veerman    # 12
# 2. HumanEval
python3 scripts/bench2.py humaneval    --model $M --examples 164
# 3. LiveCodeBench v6 (n=50, 65k cap — matches @6bit backfill)
python3 scripts/bench2.py livecodebench --model $M --examples 50 \
  --lcb-version release_v6 --max-tokens 65536
# 4. MMLU  ← cheap-signal gate ends here
python3 scripts/bench2.py mmlu         --model $M --examples 100
```

Each result compared to its `@6bit` anchor (97.5 / 75.0 / 87 / 54 / 83).

### Gate decision

UD-4bit earns the expensive tail if it **matches-or-beats `@6bit` on the cheap
signals within quant noise (~±2–3 pp)** — with **tool-calling non-negotiable**
(malformed calls fail regardless of knowledge scores). A 4-bit quant shedding a
couple of points on LCB/MMLU is expected and acceptable *if* the size/speed win
justifies it; a large knowledge drop or broken tool-calls fail the gate and
`@6bit` keeps the daily-driver slot.

## Phase 3 — expensive tail (gated, ~15 h + optional completeness)

Only if Phase 2 clears the gate.

**Terminal-Bench 2.0** — full 64-task suite via the Harbor / terminus-2 chain at
`--agent-timeout-multiplier 0.5`, comparable to the published `@6bit` **28.1 %**
(#3 on rig). Follow [bench/terminal-bench/plan.md](../terminal-bench/plan.md);
the `@6bit` thinking-format guard passed on this exact chain, so no template
surgery expected.

**Optional completeness** (fills the daily-driver scoreboard, not in the core
"speed → cheap → tbench" ask): `MATH` / `DROP` / `GPQA@65k` via `bench2.py`
(GPQA at `--max-tokens 65536` per the truncation finding). Run these only if the
verdict is close and the full knowledge row would decide it.

### Phase 3 — Terminal-Bench 2.0 — _(running 2026-07-10)_

Full suite via the Harbor / terminus-2 / LiteLLM chain at `--agent-timeout-multiplier
0.5`, `-n 1` (sequential), thinking-on — directly comparable to the published `@6bit`
**28.1 %** (25/64 PASS, #3 on rig). Driver: `scripts/run-tbench-ud-mlx.sh` (adapted
from the `@6bit` T-Bench driver; served id `openai/qwen3.6-35b-a3b-ud-mlx`). Expected
~15 h.

**Docker network pool fix (reusable).** First launch failed **every** task
immediately with `Error response from daemon: all predefined address pools have been
fully subnetted` (60/60 failed, 0 ran). Cause: **29 orphaned docker-compose networks
from prior runs** had saturated Docker's small default address pool (~31 subnets), so
even the first sequential task couldn't create its network. Fix: `docker network
prune -f` (33 → 4 networks). `@6bit` ran fine on the same default pool, which proves
Harbor tears down each task's network — so a *clean* start needs no daemon change;
just prune leftovers before a run. Relaunched clean: 0 pool errors, tasks pulling +
executing. The driver preflight also asserts thinking-on (reasoning_tokens>0).

## Deliverables (per [AGENTS.md](../../AGENTS.md))

- **This campaign** `bench/qwen3.6-ud-mlx/` — family folder (the sibling
  `qwen3.6-27b-ud-mlx` may get the same treatment later). `plan.md` (this file),
  `scripts/` drivers adapted from the MTP campaign, distilled `results/*.json`,
  raw logs under `logs/` (gitignored).
- **Canonical scores** → `tools/local-llm-bench/results/qwen3.6-35b-a3b-ud-mlx-4bit/`
  (throughput) and the `local-llm-bench-m4-32gb` run tree (quality), per the
  results boundary.
- **Model card** `docs/models/qwen3.6-35b-a3b.md` — flip the UD-MLX-4bit variants
  row from "not yet benched" to its scores + a dated results section; update the
  daily-driver verdict **only if** UD-4bit clears the gate and wins on
  size/speed at parity quality.

## Results

### Phase 0 — preflight + tool-call sanity — 2026-07-10 · **GATE PASSED**

Loaded `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` (served id `qwen3.6-35b-a3b-ud-mlx`)
sole/clean at ctx 65,536, `--gpu max --parallel 4` — **21.66 GB resident**, 6.3 s
load. 3-call tool-use sanity probe (temp 0, seed 42), all clean:

| Probe | Expectation | Result |
|---|---|---|
| weather (2-arg, enum) | well-formed call | ✅ `get_weather{"city":"Tokyo","unit":"celsius"}`, `finish_reason=tool_calls`, JSON parses |
| "say hello, no tool" | no tool call | ✅ `finish_reason=stop`, content `Hello`, no call |
| add (2 int args) | well-formed call | ✅ `add{"a":17,"b":25}`, JSON parses |

**Verdict: the `mlx-community` 4-bit MoE tool-call regression does NOT reproduce
on this UD-4bit MLX build.** Calls are well-formed, args parse, and the model
correctly abstains when no tool applies. UD-4bit is a live daily-driver candidate
— proceed to Phase 1.

**Harness note (reusable):** `bench.py --no-think` resolves its template via the
`--model` string as an on-disk path (`~/.lmstudio/models/<model>/chat_template.jinja`).
The served id `qwen3.6-35b-a3b-ud-mlx` has no such dir, but LM Studio's API also
accepts the **repo-path id** `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` (verified),
which both routes the request and resolves the template. So scenario runs pass
`--model unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit --model-label qwen3.6-35b-a3b-ud-mlx-4bit --no-think`.

### Phase 1a — 3-question speed probe — 2026-07-10

Sole-model, ctx 65,536, `--parallel 1`, temp 0. Decode t/s (computed from
tokens/elapsed), thinking on (probe default — measures raw decode regardless):

| Question | UD-4bit | @6bit anchor |
|---|---:|---:|
| trivial | 88.3 t/s | ~90 |
| mmlu_atmosphere | 89.9 t/s | ~90 |
| code_second_largest | 96.5 t/s (spiral, hit 1024 cap) | ~90 |

**Verdict: no decode speed change vs `@6bit` — 88–96 t/s, same band.** Being 4-bit
buys nothing on decode here: MLX MoE decode is compute-bound on the 3B active
params, not weight-bandwidth-bound, so fewer bits don't accelerate token
generation. Peak RAM 44.4 GB, GPU 97 %, 32 W, no spill. The code question spiralled
past the 1024-token cap (0 visible), the same thinking-spiral behaviour `@6bit`/27b
show — not UD-specific.

**No-think mechanism (reusable finding).** Two harness snags surfaced disabling
thinking for the scenario sweep:
1. `check_backend` validates `--model` against `GET /v1/models`, which lists only
   the **served id** `qwen3.6-35b-a3b-ud-mlx` — so the repo-path id (which the
   completions endpoint *does* accept) fails preflight. Must pass the served id.
2. `bench.py --no-think` string-replaces the *Qwen3.5* `add_generation_prompt`
   block; this is a **Qwen3.6** template with an `enable_thinking` conditional the
   replace doesn't match → it silently no-ops, leaving thinking ON.

   Fix: patch the template directly to force the pre-closed `<think>\n\n</think>`
   block, **reload** so LM Studio reads it, run with the plain served id, then
   restore (`chat_template.jinja.nothink-backup`). Verified: `reasoning_tokens=0`,
   direct answer. Baked into `scripts/run-ud-scenarios.sh` (backup + trap-restore).
   The `@6bit` baseline is confirmed no-think (its 150-cap doc-summary emits clean
   direct output), so this is apples-to-apples.

### Phase 1b — scenario throughput — 2026-07-10 · HEADLINE

The real speed test: `tools/local-llm-bench`, 4 scenarios, no-think, ctx 65k,
parallel 4. UD-4bit vs the `@6bit` MLX anchors (my parse reproduces the recorded
`@6bit` gen/eff exactly, so the deltas are clean):

| Scenario | UD-4bit gen/eff | `@6bit` gen/eff | Δ gen | Δ eff |
|---|---:|---:|---:|---:|
| creative-writing | 98.8 / 95.9 | 91.6 / 86.9 | **+8 %** | **+10 %** |
| doc-summary | 96.4 / 61.9 | 91.7 / 55.9 | **+5 %** | **+11 %** |
| ops-agent | 96.3 / 80.8 | 85.5 / 71.4 | **+13 %** | **+13 %** |
| prefill-test | 97.9 / 23.8 | 85.5 / 22.9 | **+14 %** | +4 % |

**Verdict: UD-4bit is faster than `@6bit` on every scenario (+5–14 % gen,
+4–13 % effective) at 26 % less disk (20 vs 27 GB).** This *corrects* the Phase 1a
read of "no speed win": 1a was a `--parallel 1`, thinking-on single stream
dominated by a reasoning spiral — not representative. Under realistic sustained
no-think generation at parallel 4, the lighter 4-bit weights cut per-token
bandwidth and UD pulls clearly ahead, holding ~96–99 gen t/s across all four
workloads (vs `@6bit`'s 85–92). The biggest wins are on the agentic/structured
workloads (ops-agent +13 %), exactly the daily-driver loop.

**So on speed + footprint, UD-4bit dominates `@6bit`.** The daily-driver decision
now hinges entirely on Phase 2: does the 4-bit quant hold `@6bit`'s quality
(tool-calling already clean in Phase 0; HumanEval / LCB / MMLU next)?

Distilled JSONs: `tools/local-llm-bench/results/qwen3.6-35b-a3b-ud-mlx-4bit/`.

### Phase 2a — fast cheap signals — 2026-07-10

`tool-calling (jdhodges 40 + veerman 12) → HumanEval (100) → MMLU (100)`, temp 0,
seed 42, ctx 65k — matched to the `@6bit` example counts. Driver:
`scripts/run-ud-cheapsignals-fast.sh`. LCB v6 (the multi-hour tail) held pending
these. Targets to match-or-beat: jdhodges 97.5 / veerman 75.0 / HumanEval 87 / MMLU 83.

**Methodology note — first run was accidentally thinking-off (corrected).** The
first pass reused the already-resident model via `lms load` (a no-op on a loaded
model), which kept the **no-think template still in LM Studio's memory** from the
Phase 1b sweep (Phase 1b restored the file on disk but never reloaded). So all four
benches ran with reasoning disabled (`mean_reasoning=0`), non-comparable to the
`@6bit` thinking-on anchors. Fixed the driver to `unload --all → load` and to
**assert `reasoning_tokens>0` before running** (probe read 199). Re-run thinking-on
in progress.

**Secondary data point — UD-4bit THINKING-OFF** (kept because a daily driver often
runs no-think for speed):

| Bench | UD think-off | `@6bit` think-on |
|---|---:|---:|
| jdhodges (40) | 95 % (38/40) | 97.5 % |
| veerman (12) | 75 % (9/12) | 75.0 % |
| HumanEval (100) | 88 % | 87 % |
| MMLU (100) | 78 % | 83 % |

Even with reasoning off, UD ties/leads on HumanEval (+1) and Veerman (=), trails
slightly on jdhodges (−2.5), and gives up the most on MMLU (−5) — the knowledge
bench that leans hardest on reasoning. The thinking-on re-run is the comparable one.

### Phase 2a (thinking-on) — 2026-07-10

Re-run with reasoning genuinely on (probe reasoning_tokens=199; MMLU mean
reasoning 1923). **Second caching gotcha:** `tool_call_bench.py` auto-carries
prior entries unless `--force` — the first thinking-on pass silently reused the
thinking-off tool-calling results, so jdhodges/veerman were re-run separately with
`--force`.

| Bench (thinking-on) | UD-4bit | `@6bit` | Δ |
|---|---:|---:|---:|
| HumanEval (100) | **82 %** (0 trunc) | 87 % | **−5** |
| MMLU (100) | **78 %** (0 trunc) | 83 % | **−5** |
| jdhodges (40) | **97.5 %** (39/40) | 97.5 % | **=** |
| veerman (12) | **83.3 %** (10/12) | 75.0 % | **+8.3** |

(Tool-calling runs reasoning-free on both UD and `@6bit` — the harness emits the
call directly, `mean_reasoning=0` on both — so those two rows are apples-to-apples
regardless of the thinking toggle.)

**Phase 2a verdict — a clean split by workload type.** UD-4bit **matches or beats
`@6bit` on the agentic/tool-calling signals** (jdhodges tie, Veerman **+8.3**, the
multi-turn suite that's the rig's baseline holdout) but takes a **−5 pp hit on raw
knowledge/coding** (HumanEval −5, MMLU −5) — the expected 4-bit tax. Two curiosities:
HumanEval is *worse* thinking-on (82) than off (88) — reasoning hurts on simple
functions; and MMLU is 78 % with or without thinking — reasoning doesn't lift UD
the way it lifts `@6bit` (600–2700 reasoning tokens/q → 83).

**Gate read:** against the "match-or-beat within ±2–3 pp" bar, UD-4bit **clears the
agentic legs and fails the knowledge legs**. So it does *not* cleanly replace
`@6bit` as the knowledge daily driver — but it's a strong **agentic** candidate
(tool-calling parity/win + faster + 26 % smaller). That reframes the expensive
tail: Terminal-Bench (agentic shell) is now the more decision-relevant bench than
LCB (hard coding, where HumanEval −5 predicts a trail).
