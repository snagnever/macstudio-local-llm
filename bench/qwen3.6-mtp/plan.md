# 2026-07-09 — qwen3.6 MTP builds: benchmark plan

## Context

Two MTP (multi-token-prediction) builds of already-benched Qwen3.6 models landed
on the rig (LM Studio arch tag `qwen35`, distinct from the `qwen3_5` /
`qwen3_5_moe` tags of the originals):

| Model (LM Studio API id) | Size | Arch tag | Baseline it maps to |
|---|---|---|---|
| `qwen3.6-27b-mtp` | 26.02 GB | `qwen35` | `qwen3.6-27b` (22.80 GB, Planning daily driver) |
| `qwen3.6-35b-a3b-mtp` | 32.61 GB | `qwen35moe` | `qwen3.6-35b-a3b@6bit` / `@8bit` |

The question MTP has to answer is **speed**: the plain `qwen3.6-27b` holds the
knowledge-generalist / Planning slot on quality but loses the agent slot to
`qwen/qwen3-coder-next` on speed
([model card](../../docs/models/qwen3.6-27b.md)). If MTP meaningfully lifts
decode t/s at equal quality, that trade-off gets re-litigated.

## Phase 1a — 3-question speed probe (first leg, thin signal)

`scripts/run-qwen36-mtp-speedprobe.sh` — clean-state, sole model at ctx 65,000,
`--parallel 1`, `--gpu max`. Standard 3-question `speed_probe.py` (trivial /
knowledge / code, temp 0) + macmon. Fast gut-check, but every question is
short-answer and reasoning-heavy — not representative of sustained generation.

## Phase 1b — scenario throughput sweep (the real speed test)

`scripts/run-qwen36-mtp-scenarios.sh` — the `tools/local-llm-bench` harness (the
tool behind the "Generation throughput by scenario" dashboard). Runs the 4 text
scenarios — **creative-writing, doc-summary, ops-agent, prefill-test** — and
reports **effective tok/s** (output ÷ total wall-clock incl. prefill, the number
you actually wait for) alongside raw generation tok/s. `--no-think`, backend
lmstudio, model resident at ctx 65k.

Comparison baseline: `tools/local-llm-bench/results/qwen3.6-27b-dense-mlx-6bit/`
(plain `qwen3.6-27b`, MLX 6-bit, same rig, `--no-think`):

| Scenario | eff t/s | gen t/s |
|---|---:|---:|
| creative-writing | 19.9 | 20.7 |
| doc-summary | 11.2 | 20.2 |
| ops-agent | 16.2 | 20.0 |
| prefill-test | 4.0 | 20.4 |

**Caveat:** baseline is MLX-6bit-*dense*; this build is the *GGUF MTP* quant
(`unsloth/Qwen3.6-27B-UD-Q6_K_XL.gguf`, the LM Studio alias `qwen3.6-27b-mtp`),
so the delta conflates the MTP head with quant + format. Read it as "does the MTP
build serve faster in practice", not an MTP-isolated measurement.

### No-think on a GGUF reasoning model (reusable finding)

The harness `--no-think` patches an external `chat_template.jinja` — the MLX
layout. A GGUF embeds its template inside the `.gguf`, so there's nothing to
patch and `--no-think` is silently ignored → the model reasons, and the low-cap
scenarios (doc-summary/prefill 150 tok) error with "produced reasoning tokens but
no visible output". Per [unsloth's Qwen3.6 docs](https://unsloth.ai/docs/models/qwen3.6#qwen3.6-27b)
there is **no `/no_think` soft switch**; the only lever is `enable_thinking=false`
— but LM Studio's OpenAI server ignores request-body `chat_template_kwargs`
(verified: still 39 reasoning tokens, 0 visible). The template's
`enable_thinking is false` branch just emits a pre-closed `<think>\n\n</think>`,
so **prefilling that block as a trailing assistant turn is the exact same tokens
and reliably disables thinking** (verified: `visible='ready'`, 0 reasoning).
Implemented as `BENCH_NOTHINK_PREFILL=1` in `bench.py` (env-gated, inert for
other harness users). Candidate to promote to `fixes/` if reused.

## Later phases (not this leg)

- Context-vs-speed sweep (does the MTP advantage hold as context fills?)
- Cheap-signal quality gate (HumanEval + toolcall) — MTP must not cost accuracy
- `qwen3.6-35b-a3b-mtp` repeat of whatever the 27B numbers justify

## Results

### Phase 4 — 27B dense: MTP A/B + draft-depth — 2026-07-10

Same treatment as Phases 3/3b, on the **dense** `qwen3.6-27b-mtp`
(`Qwen3.6-27B-UD-Q6_K_XL.gguf`) — checks whether MTP behaves the same without the
MoE. Scripts: `run-mtp-ab-toggle.sh qwen3.6-27b-mtp` then
`run-mtp-draftdepth-sweep.sh qwen3.6-27b-mtp 3 4 6 8`. gen t/s (parallel 4, ctx
65k, no-think):

| Scenario | OFF | **d2** | d3 | d4 | d6 | d8 | best | MTP@d2 |
|---|---:|---:|---:|---:|---:|---:|:--:|---:|
| creative-writing | 16.7 | 15.4 | 10.9 | 9.1 | 6.5 | 8.5 | **OFF** | −8% |
| doc-summary | 17.2 | **21.9** | 17.4 | 15.5 | 12.1 | 17.1 | **d2** | **+28%** |
| ops-agent | 16.6 | **19.1** | 15.1 | 13.1 | 9.6 | 13.4 | **d2** | **+15%** |
| prefill-test | 16.7 | 17.5 | 14.4 | 11.4 | 8.2 | 10.9 | **d2** | +5% |

**Verdict: the dense 27B reproduces the 35B MoE profile exactly — MTP is a
per-workload toggle, `max-draft=2` is the peak.** Same signs and near-identical
magnitudes (creative −8%, doc-summary +28% vs the MoE's +22%, ops-agent +15% vs
+13%), and the same monotonic decline past d2. So the MTP behaviour is a property
of the draft head + workload entropy, **not** of the MoE architecture — the
recommendation (on for structured/agentic, off for creative, depth fixed at 2)
holds for both Qwen3.6 MTP builds. Absolute speed is ~4–5× lower than the MoE
(dense 27B ~16–22 t/s vs A3B ~70–93) — MTP doesn't change that ranking.

Distilled JSONs: [`results/mtp-ab-27b/`](results/mtp-ab-27b/) (off/on),
[`results/mtp-draftdepth-27b/`](results/mtp-draftdepth-27b/) (d3/d4/d6/d8).

### Phase 3 — MTP A/B toggle (the correct isolation) — 2026-07-10 · HEADLINE (35B)

Phases 1b/2 compared GGUF-vs-MLX, which conflates quant+format with the MTP draft
head — it does **not** measure MTP. The right test is the same GGUF with only LM
Studio's **Draft MTP** load toggle flipped. `scripts/run-mtp-ab-toggle.sh` loads
`qwen3.6-35b-a3b-mtp` twice (`--no-speculative-draft-mtp` vs
`--speculative-draft-mtp --speculative-draft-max-tokens 2`), everything else
fixed (ctx 65000, GPU max, parallel 4 — matching the user's Load config), and
runs the scenario sweep each way. Same-session, reproduced last night's on-run.

| Scenario | MTP OFF (gen/eff) | MTP ON (gen/eff) | Δ gen (MTP effect) |
|---|---:|---:|---:|
| creative-writing | 74.7 / 71.8 | 68.1 / 66.0 | **−9%** |
| doc-summary | 76.0 / 50.3 | 92.7 / 55.9 | **+22%** |
| ops-agent | 72.7 / 45.6 | 82.2 / 49.2 | **+13%** |
| prefill-test | 72.9 / 18.1 | 71.0 / 19.8 | −3% |

**Verdict (corrected): Draft MTP works and is workload-dependent — textbook
speculative decoding.** It wins on low-entropy/predictable output where draft
acceptance is high (doc-summary **+22%**, ops-agent **+13%**), loses on
high-entropy creative prose (**−9%**, drafts rejected → wasted verify passes), and
is a wash on prefill-bound work (−3%, little generation to accelerate). Because
it's a load-time toggle, the right setting is per-use: **MTP on for
agentic/structured/summarization, off for creative writing.** My earlier "MTP not
active on this stack" was wrong reasoning (cross-format comparison); MTP is active
and the draft-max=2 default already yields double-digit gains on agent workloads.

Distilled A/B JSONs: [`results/mtp-ab-35b-a3b/`](results/mtp-ab-35b-a3b/)
(`off/` and `on/`).

### Phase 3b — draft-depth sweep (`--speculative-draft-max-tokens`) — 2026-07-10

Does a deeper draft window widen the win? `scripts/run-mtp-draftdepth-sweep.sh`
holds MTP on and varies max-draft {4,6,8}, joined to the Phase 3 anchors OFF and
d2. gen tok/s:

| Scenario | OFF | d2 | d3 | d4 | d6 | d8 | best |
|---|---:|---:|---:|---:|---:|---:|:--:|
| creative-writing | 74.7 | 68.1 | 58.2 | 49.8 | 36.1 | 29.5 | **OFF** |
| doc-summary | 76.0 | **92.7** | 88.7 | 77.7 | 71.7 | 53.4 | **d2** |
| ops-agent | 72.7 | **82.2** | 73.7 | 66.7 | 52.0 | 41.8 | **d2** |
| prefill-test | 72.9 | 71.0 | 71.1 | 60.0 | 42.6 | 33.8 | ~OFF |

**Verdict: `max-draft=2` (the LM Studio default) is a true optimum — deeper is
strictly worse on every scenario, monotonically.** d3 (added after the initial
2→4→6→8 sweep to rule out a hidden peak) lands between d2 and d4 everywhere and is
already below the d2 peak on the structured winners (doc-summary 88.7<92.7,
ops-agent 73.7<82.2) — so there is no better setting between 2 and 4. The model
has a single MTP draft head, so it reliably predicts ~1 token ahead; drafting
3/4/6/8 compounds error, acceptance collapses, and each rejected draft still costs
a forward pass — creative-writing more than halves (74.7→29.5). **Actionable:**
leave Draft MTP at max-tokens 2; never raise it. The only two knobs that matter
are the on/off toggle (per Phase 3, by workload) and keeping depth at 2.

Distilled JSONs: [`results/mtp-draftdepth-35b-a3b/`](results/mtp-draftdepth-35b-a3b/)
(`d4/ d6/ d8/`; OFF & d2 are the Phase 3 `mtp-ab-35b-a3b/` dirs).

### Phase 2 — 35B-A3B MTP scenario throughput — 2026-07-10

`qwen3.6-35b-a3b-mtp` = `unsloth/Qwen3.6-35B-A3B-UD-Q6_K_XL.gguf` (MoE, 3B active),
thinking off via prefill, vs the MLX MoE baseline `results/qwen3.6-35b-a3b/`
(`*_lmstudio-mlx.json`), same rig.

| Scenario | 35B MLX (gen/eff) | 35B UD-Q6_K_XL GGUF (gen/eff) | Δ gen | Δ eff |
|---|---:|---:|---:|---:|
| creative-writing | 91.6 / 86.9 | 68.6 / 66.7 | **−25%** | **−23%** |
| doc-summary | 91.7 / 55.9 | 92.9 / 56.0 | +1% | +0% |
| ops-agent | 85.5 / 71.4 | 81.9 / 50.2 | −4% | **−30%** |
| prefill-test | 85.5 / 22.9 | 69.6 / 17.5 | −19% | **−24%** |

**Verdict: identical shape to the 27B — GGUF/MTP is slower or flat, never faster,
and effective throughput craters on the prefill-heavy/growing-context scenarios
(ops-agent −30%, prefill-test −24%), only holding par on the low-prefill
doc-summary.** The stakes are higher here: the MLX MoE runs 85–92 gen t/s (the 3B
active-param win), and the GGUF gives ~25% of that away on creative-writing.
(**Correction:** this is a format/quant gap, *not* an MTP verdict — see Phase 3,
which isolates the draft toggle and finds MTP does help structured workloads. On
creative-writing the MLX MoE build still wins outright.)

Distilled JSONs: [`results/scenario-throughput-35b-a3b/`](results/scenario-throughput-35b-a3b/).

### Phase 1b scenario throughput — 2026-07-10 (the headline result)

UD-Q6_K_XL GGUF (thinking off via prefill) vs the dense MLX-6bit baseline, same
rig, LM Studio, `--no-think`. gen = raw decode t/s; eff = output ÷ total
wall-clock incl. prefill.

| Scenario | dense-6bit MLX (gen/eff) | UD-Q6_K_XL GGUF (gen/eff) | Δ gen | Δ eff |
|---|---:|---:|---:|---:|
| creative-writing | 20.7 / 19.9 | 15.3 / 15.0 | **−26%** | **−25%** |
| doc-summary | 20.2 / 11.2 | 21.7 / 12.2 | +7% | +9% |
| ops-agent | 20.0 / 16.2 | 18.5 / 9.7 | −8% | **−40%** |
| prefill-test | 20.4 / 4.0 | 17.4 / 4.1 | −14% | +2% |

**Verdict: the UD GGUF/MTP build is not faster — it's slower or flat on decode
everywhere except doc-summary, and its effective throughput collapses on
ops-agent (−40%), the growing-context agent workload, pointing at slow llama.cpp
prefill vs MLX.** (**Correction:** this GGUF-vs-MLX gap is a format/quant difference, not the MTP
verdict — MTP was left at its LM Studio default here and *is* working; Phase 3
isolates it properly. The 27B A/B wasn't re-run, but the 35B A/B shows MTP helps
structured output and hurts creative, so expect the same shape here.) The heavier
Q6_K_XL quant just costs bandwidth relative to MLX on creative-writing.

Distilled per-scenario JSONs: [`results/scenario-throughput/`](results/scenario-throughput/).
Canonical copies + response dumps under
`tools/local-llm-bench/results/qwen3.6-27b-mtp/`.

### Phase 1a 3-question speed probe — 2026-07-09 (qwen3.6-27b-mtp, ctx 65k, parallel 1)

Decode t/s per question, MTP vs the 2026-05-17 plain-`qwen3.6-27b` baseline
(both sole-model, clean state):

| Question | plain 27b | 27b-mtp | Δ |
|---|---:|---:|---:|
| trivial (4) | 18.5 t/s | 20.2 t/s | +9% |
| mmlu_atmosphere (A) | 19.2 t/s | 21.1 t/s | +10% |
| code_second_largest | 19.9 t/s | 20.3 t/s | +2% |

**Verdict: no meaningful speed win.** MTP lands ~20–21 t/s vs the baseline's
~18.5–20 t/s — within run-to-run noise, not the speculative-decode multiplier
MTP heads are supposed to buy. Likely the LM Studio / llama.cpp path isn't
driving the MTP draft head (arch tag `qwen35`), so the extra 3.2 GB on disk
(26.0 vs 22.8 GB) buys nothing here. Both runs answered trivial/mmlu correctly;
both hit the 1024-token cap on the code question (reasoning spiral, content
truncated — same behavior in both, so not MTP-specific).

Distilled result: [`results/qwen3.6-27b-mtp_20260709_234802_results.json`](results/qwen3.6-27b-mtp_20260709_234802_results.json);
macmon telemetry and full run log stay in the submodule `results/speed_probe/`
and `logs/`. Peak RAM 52.3 GB, no spill, GPU 99%, 59 W.

**Implication for later phases:** without a speed advantage the MTP build has no
case for the agent slot, so a quality gate is only worth running if we first
confirm whether the MTP head *can* be enabled on this stack.
