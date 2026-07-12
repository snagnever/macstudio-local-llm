# Qwen3.5-122B-A10B (MoE, GGUF)

> **Status: 🔴 NO-GO (Planning-slot challenger) — benched, rejected.** A *faster
> sidegrade, not an upgrade*: one-shot quality ties [`qwen3.6-27b`](qwen3.6-27b.md)
> (LCB **62 % exact tie**), decodes ~2× faster (~36 t/s), but is a distinctly
> weaker agent (Terminal-Bench **24.7 %** vs 31.5 %, #5 on rig) and forces
> sole-model 75 GB residency. **The 27B keeps the Planning slot.**
> Last updated: 2026-07-12

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [Qwen/Qwen3.5-122B-A10B](https://huggingface.co/Qwen) | unsloth docs (fetched 2026-07-10) |
| Parameters | **122B total / 10B active** MoE; 48 layers; 256 experts (8 routed + 1 shared) | HF card (unsloth) |
| Architecture | Hybrid `16 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE))`; attention 32 Q / **2 KV** heads @ dim 256; DeltaNet 64 V / 16 QK heads @ dim 128. Local LM Studio arch tag `qwen35moe` | HF card |
| Native context | 262,144 (up to ~1M with YaRN); run locally at 65,536 | HF card / local |
| License | Apache 2.0 | HF card |
| Generation | Qwen3.**5** — one generation behind the rig's Qwen3.6 daily drivers | HF card |
| Modalities | text + image + video input, text output | HF card |
| Reasoning | **Thinking mode by default** (`<think>…</think>`); disableable via `enable_thinking=false` | HF card |
| MTP | Draft head in the GGUF; vendor claims ~1.4–2.2× decode | unsloth docs |
| Vendor sampling | thinking: `temp=0.6, top_p=0.95, top_k=20`; non-thinking: `temp=0.7, top_p=0.8, top_k=20` | unsloth docs |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `qwen3.5-122b-a10b-mtp` | [unsloth/Qwen3.5-122B-A10B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.5-122B-A10B-MTP-GGUF) | GGUF | UD-Q4_K_S | 75.23 GB | LM Studio llama.cpp | 🔴 **benched — NO-GO** | Sole variant benched; MTP left OFF for the quality/speed baseline |

Optional quality-bump quant (untested): UD-Q4_K_XL, 78.6 GB — the one-step probe if a MARGINAL result had warranted it (it didn't).

## Architecture & spec notes
- **MoE 122B total / 10B active** — the whole reason it fits and runs fast: only
  ~10B params touched per token → ~36 t/s decode at 4-bit, ~2× the dense 27B.
- **Cheap hybrid KV** — same Gated DeltaNet + Gated Attention family as the rig's
  `qwen3.6-27b` / `qwen3.6-35b-a3b`; only ~¼ of layers are full attention (2 KV
  heads) → KV cost is tiny (est. ~5 GiB over weights at 65k ctx).
- **Thinking model** — `<think>` by default. This drives both its quality (LCB
  ties the 27B) *and* its two failure modes: **truncation** (spirals past the 65k
  cap → graded fail) and **high-step agentic thrash** (see Terminal-Bench).
- Arch tag `qwen35moe` loads on stock LM Studio llama.cpp — no special runtime.

## Local performance (measured, 2026-07-10 → 07-12)

| Metric | 122B Q4_K_S | vs `qwen3.6-27b` |
|---|---|---|
| Sustained generation | **~36 t/s** (35.6–39.6 gen across scenarios) | **~2× faster** (27B ~20 t/s) |
| Cold load (sole-model) | **20.9 s** | — |
| Resident memory | **75.23 GB** (est. 75.14 GiB total incl. KV @ 65k) | 27B is 22.8 GB |
| Soak stability | **swap 0, no spill, GPU 97 %** | — |
| Full campaign wall-clock | **~37.5 h** (HE 3.4 / MMLU 1.3 / DROP 1.4 / MATH 5.1→cut / LCB 8 / T-Bench 18.5) | — |

Scenario throughput (`tools/local-llm-bench/bench.py`, no-think via
`BENCH_NOTHINK_PREFILL=1`, gen / eff t/s):

| Scenario | 27B gen / eff | 122B gen / eff |
|---|---:|---:|
| creative-writing | 20.7 / 19.9 | **37.8 / 36.1** |
| doc-summary | 20.2 / 11.2 | **39.6 / 23.2** |
| ops-agent | 20.0 / 16.2 | **35.6 / 20.1** |
| prefill-test | 20.4 / 4.0 | **35.8 / 7.5** |

Prefill is also ~2× better — no dense-27B-style prefill-collapse tarpit.

## Quality benchmarks (measured)

Config: thinking ON, temp 0, seed 42, ctx 65,536, `--max-tokens 65536`.

| Bench | 122B Q4_K_S | `qwen3.6-27b` 6-bit | Δ |
|---|---|---|---|
| HumanEval (100) | **96 %** | 93 % | **+3** |
| MMLU (100) | 87 % | 88 % | −1 |
| DROP (100) | 89 % | 90 % | −1 |
| MATH | ~87 % (60/69, **skipped** at Q69 per user request) | 88 % | ~−1 |
| **LiveCodeBench-50** | **62 % (31/50)** | 62 % (31/50) | **0 — exact tie** |
| jdhodges tool-calling (40) | 95 % (38/40) | 95 % | tie |
| Veerman tool-calling (12) | 83 % (10/12) | 83.3 % | tie |
| **Terminal-Bench 2.0 (89)** | **24.7 % (22/89)** ⌛0.5x | 31.5 % (28/89) | **−6.8** |

**LCB is a statistical dead heat — identical per difficulty:** easy 10/15=10/15,
medium 14/23=14/23, hard 7/12=7/12; same-question head-to-head traded 3 wins each
way. The 122B took **4 truncations** at the 65k cap (all graded fail) yet still
matched — a capable one-shot coder whose over-thinking costs it questions.

Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/*_qwen3.5-122b-a10b-mtp_*`;
Terminal-Bench: `bench/terminal-bench/logs/tbench-runs/qwen3.5-122b-a10b/`.

## Terminal-Bench 2.0 — the deciding leg

**24.7 % (22/89)**, terminus-2 / Docker, `--agent-timeout-multiplier 0.5`, thinking
ON, ~18.5 h. Rig standing: **#5** — below MiniMax-M2.5 (25.8 %) and every Qwen
thinker, above the Gemmas.

| Model | T-Bench |
|---|---|
| `qwen3-coder-next` | 32.6 % |
| `qwen3.6-27b` | 31.5 % |
| `qwen3.6-35b-a3b@6bit` | 28.1 % |
| `minimax-m2.5` (both GGUF quants) | 25.8 % |
| **`qwen3.5-122b-a10b`** | **24.7 %** |
| `gemma-4-31b` | 22.5 % |
| `gemma-4-26b-a4b@6bit` | 21.3 % |

**Failure analysis:** median episode count is **10 for both PASS and FAIL** → the
failures are *wrong/incomplete solutions that fail the verifier*, not timeouts or
infra. Three modes: (1) dominant — agent terminates believing it succeeded but the
output fails unit tests (`chess-best-move` wrong answer; `db-wal-recovery` 0/7,
never produced valid output); (2) partial completions graded as full fails
(`build-cython-ext` 7/11 tests pass → still FAIL, so 24.7 % *understates* work
done); (3) minority thrash-to-timeout (`build-pov-ray` 128 episodes). No
`AgentTimeoutError` / context / connection errors — the litellm "model isn't mapped
yet" warning was cosmetic. **Root cause: capable one-shot reasoner, weak agentic
executor** — over-thinks, under-executes; same trait as its LCB truncations.

## Feasibility & verdict

- **Role tested: Planning-slot challenger** to `qwen3.6-27b`. **🔴 NO-GO.**
- **Faster sidegrade, not an upgrade.** One-shot quality is a wash (±3 pp
  everywhere, LCB an exact tie), decode ~2×, but a distinctly weaker agent
  (−6.8 pp T-Bench) with an active truncation/thrash liability, and it forces
  **sole-model 75 GB** where the 27B swaps in at 22.8 GB and pairs with the coder
  stack.
- **Headline lesson: test the newest *generation*, not the biggest *old* model.**
  The one-generation-older Qwen3.5-122B lost to the newer, smaller Qwen3.6
  27B / coder-next on every axis that matters.
- **Only niche:** a fast one-shot planner on a dedicated box where 2× speed beats
  the 27B's pairing flexibility — too narrow for a permanent slot.
- **SWE-with-agents stack unchanged:** `coder-next@4bit` (agent loop) +
  `gemma-4-26b-a4b@6bit` (single-shot code ceiling) resident; `qwen3.6-27b`
  swap-in planner. The 122B stays on the bench.

Plan + full data: [bench/qwen3.5-122b-a10b/plan.md](../../bench/qwen3.5-122b-a10b/plan.md).

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| `--no-think` / scenario bench produced 0 output tokens | GGUF has no external `chat_template.jinja` for `--no-think` to patch; LM Studio ignores request-body `chat_template_kwargs` | Use `BENCH_NOTHINK_PREFILL=1` (prefills a pre-closed `<think>\n\n</think>`); added to `bench.py` + `speed_probe.py` this campaign |
| LCB / MATH questions spiral past the 65k cap → truncated FAIL | Thinking-model over-reasoning (up to ~65k tokens / ~36 min per question) | Not a bug — model trait. `BENCH_TIMEOUT=3600` bounds wedges; the truncation cost is a real quality ding |
| `setsid` not found when launching the detached driver | macOS ships no `setsid` | Detach via `nohup python3 -c "os.setsid(); os.execvp('bash', …)"` (new session, PPID=1) |
| litellm "This model isn't mapped yet" during Terminal-Bench | litellm lacks cost/context metadata for a custom local model | Cosmetic — completions succeed; no effect on results |

## Loading & memory
- **Sole-model only:** 75.23 GB resident (est. 75.14 GiB incl. KV @ 65k) — evict
  everything else; loads via LM Studio in ~21 s.
- Cheap hybrid KV means 65k ctx fits comfortably under the ~80 GB rule; drop to
  32,768 for the knowledge subset if pairing-slot prefill spikes are a concern.
- Never pairs with the coder/Gemma stack — this is the core operational cost that
  sinks it for a slot the 22.8 GB 27B fills more flexibly.

## Client configuration
- Model id: `qwen3.5-122b-a10b-mtp` (verbatim from LM Studio `GET /v1/models`).
- Context at load: 65,536; sampling for benches was temp 0 / seed 42 (repo
  reproducibility convention — deliberately diverges from vendor temps).
- Load-time **Draft MTP** toggle is exposed (`--speculative-draft-mtp`) but was
  left OFF for the quality/speed baseline; per the [qwen3.6 MTP study](../../bench/qwen3.6-mtp/plan.md)
  it would help structured/agentic decode at draft depth 2.

## External links
- Vendor: https://huggingface.co/unsloth/Qwen3.5-122B-A10B-MTP-GGUF (Apache 2.0)
- unsloth docs: https://unsloth.ai/docs/models/qwen3.5

## History
- **2026-07-10** — Candidate identified + staged (unsloth Q4_K_S, 75.23 GB). Gate 0–2
  + fast tool-calling: speed ~2× the 27B, tool-calling ties.
- **2026-07-11** — Quality ladder (thinking ON): HumanEval 96, MMLU 87, DROP 89,
  MATH ~87 (cut at Q69), **LCB-50 62 % exact tie**. Fixed the no-think prefill in
  `bench.py` + `speed_probe.py`.
- **2026-07-12** — Terminal-Bench **24.7 % (22/89)**, #5 on rig. **Final verdict:
  🔴 NO-GO** — faster sidegrade, weaker agent; `qwen3.6-27b` keeps the Planning slot.
