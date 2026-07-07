# Model Cards

Per-model deep dives for every model with local experience on this rig (Mac Studio M4 Max, 128 GB unified — see [machine-configuration.md](../machine-configuration.md)). Each card combines **official source documentation** (fetched from HuggingFace / upstream, with source links) and **local experience** (measured benchmarks, throughput, feasibility verdicts, bugs found + patches, client configs, memory math).

**Relationship to other docs:** these cards are the per-model deep dive. [local-llm-reference.md](../local-llm-reference.md) remains the daily cheat-sheet (what to load for which task). [M4_MAX_128GB_NOTES.md](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) is the append-only benchmark log the cards cite as ground truth.

## Verdict at a glance

### Active lineup (daily drivers + roles)
| Model | Status | Role | HumanEval | LCB v6 | T-Bench | eff t/s | Disk | Runtime |
|---|---|---|---|---|---|---|---|---|
| [qwen3-coder-next](qwen3-coder-next.md) | 🟢 DAILY DRIVER | **Agent** (T-Bench #1) | 89% | 56% | **32.6%** | 55.8 | 64.76 GB (6-bit) | MLX |
| [qwen3.6-27b](qwen3.6-27b.md) | 🟢 DAILY DRIVER | **Planning / knowledge** (85.8% avg, top of rig) | 93% | 62% | 31.5% | 16.2 | 22.80 GB | MLX |
| [gemma-4-26b-a4b](gemma-4-26b-a4b/README.md) | 🟢 DAILY DRIVER | **Code** (@6bit LCB ceiling; @4bit fastest on rig) | 97–98% | **80%** @6bit / 66% @4bit | 21.3 / 20.2% | 66.6 / **80.7** | 21.81 / 15.64 GB | MLX |
| [qwen3.6-35b-a3b](qwen3.6-35b-a3b.md) | 🟢 DAILY DRIVER | Fast generalist (@8bit quant A/B pending) | 87% | 54% | 28.1% | 71.4 | 29.09 GB (6-bit) | MLX |
| [gemma-4-e4b](gemma-4-e4b.md) | 🟡 NICHE | Tiny / FIM / quick tool-calls (⚠ MATH 14%) | 91% | 68% | 4.5% | 62.9 | 8.97 GB | MLX |
| [nomic-embed-text-v1.5](nomic-embed-text-v1.5.md) | 🟢 ACTIVE | Embeddings for RAG (un-benched by design) | — | — | — | — | 84 MB | GGUF |

### Tested, parked
| Model | Status | Why | Headline | Disk | Runtime |
|---|---|---|---|---|---|
| [minimax-m2.5](minimax-m2.5.md) | 🟢 GO via GGUF (MLX 🔴 NO-GO: kernel panic ×3) | MMLU pending; Terminal-Bench NO-GO (memory); ctx ≤64k (60k rec.) | jdhodges 95%, HumanEval 94%, LCB 72% @60k (68% @32k), 36.8 t/s | 98.7 GB | llama.cpp |
| [deepseek-v4-flash](deepseek-v4-flash/README.md) | 🟢 GO via GGUF / 🟡 CONSTRAINED MLX (OOM patched; 2-bit loops) | LCB tail in progress; sole-model only | jdhodges 87.5%, HumanEval 88%, ~10 t/s non-thinking | 81 GB (GGUF) / 96.53 GB (MLX) | llama.cpp 2.24.0 / patched mlx-lm |
| [agents-a1-xl](agents-a1-xl.md) | 🟡 GO (marginal) | thinking tax; expensive tail deferred | jdhodges 92.5%, HumanEval 97%, LCB 64%, eff 35.9 t/s | 27.8 GB | MLX |
| [gemma-4-31b](gemma-4-31b.md) | 🟡 DEMOTED (MLX) / ⚪ QAT GGUF planned | dense tax: 6× slower than 26b-a4b@6bit, no quality return | LCB 76%, 13.7 t/s | 33.80 GB | MLX |
| [hermes-4-70b](hermes-4-70b/README.md) | 🔴 BLOCKED | minja template render error (fix documented, unbenched) | tool-calling 0% pre-fix (render error, not quality) | 57.3 GB | MLX |

### NO-GO / removed
| Model | Status | Why | Runtime |
|---|---|---|---|
| [kimi-dev-72b](kimi-dev-72b.md) | 🔴 NO-GO (2026-07-05) | ~7 t/s — slowest on rig; disqualified at speed gate | llama.cpp |
| [nemotron-3-nano-omni](nemotron-3-nano-omni.md) | ⚫ REMOVED 2026-05-18 | dropped in inventory pass, never benched | GGUF |

### Planned
| Model | Status | Next step |
|---|---|---|
| [mellum2-12b](mellum2-12b.md) | ⚪ PLANNED (Phase 5 seq 5) | load-probe — `mellum` arch likely needs the maintainer's mlx-lm fork |
| [gemma-4-31b](gemma-4-31b.md) QAT GGUF | ⚪ PLANNED (Phase 5 seq 2) | engine A/B (llama.cpp Q4_0 QAT vs MLX 8-bit) |

## Cross-cutting patches & upstream contributions

Model-specific patches live in each card's Known issues section. These span models / the runtime itself (all under [`fixes/mlx-lm/`](../../fixes/mlx-lm)):

| Artifact | What it fixes | Upstream |
|---|---|---|
| [`mlx-lm-find-negative-start.patch`](../../fixes/mlx-lm/mlx-lm-find-negative-start.patch) | 404 on short prompts (<11 tokens) in `mlx_lm.server` | — |
| [`mlx-lm-xtc-special-tokens-flatten.patch`](../../fixes/mlx-lm/mlx-lm-xtc-special-tokens-flatten.patch) | XTC sampling vs special tokens | — |
| [`mlx-lm-server-seed-fix-NOTE.md`](../../fixes/mlx-lm/mlx-lm-server-seed-fix-NOTE.md) | server seed handling note | — |
| Tool-call marker merge fix ([writeup](../mlx-lm/tool-call-marker-merge-writeup.md)) | tool calls silently dropped when the tokenizer merges the marker's closing `>` with the next byte — affects **any** model whose `<tool_call>` markers aren't atomic special tokens (DS4-Flash: 0→82% jdhodges) | [issue #1335](https://github.com/ml-explore/mlx-lm/issues/1335) · [PR #1336](https://github.com/ml-explore/mlx-lm/pull/1336) |
| DeepSeek-V4 cache-materialize fix ([card](deepseek-v4-flash/README.md)) | Metal `resource_limit` live-buffer leak (~1 buffer/layer/decode-step) | [issue #1332](https://github.com/ml-explore/mlx-lm/issues/1332) · [Blaizzy/mlx-lm#25](https://github.com/Blaizzy/mlx-lm/pull/25) · vs [PR #1192](https://github.com/ml-explore/mlx-lm/pull/1192) |

## Conventions
- **Badges:** 🟢 DAILY DRIVER / GO / ACTIVE · 🟡 GO (marginal) / DEMOTED / NICHE / CONSTRAINED · 🔴 NO-GO / BLOCKED · ⚫ REMOVED · ⚪ PLANNED
- **Bench config** unless noted: temp=0, seed=42, ctx 32,768; n=100 (HumanEval/MMLU/MATH/DROP/GPQA), n=50 (LCB v6), n=40 (jdhodges), n=12 (Veerman). "eff t/s" = effective throughput in the ops-agent scenario harness.
- **Provenance:** every local number traces to a repo file; every official spec traces to a fetched URL; vendor claims are labeled *vendor*. Variants name their exact source repo (author/name on HF) — conversion-level quirks attach to the source repo, not the vendor.
- **Pinned HF revisions:** each card's Variants section records the HF commit sha of the local snapshot (short sha linked to the full commit tree) plus the download date. Method: LM Studio stores no revision metadata, so pinning is established by cross-referencing local weight-file mtimes against the HF API's `sha`/`lastModified` — when no upstream commit postdates the download, local snapshot = that sha (verified 2026-07-06 for all 18 on-disk source repos). If a converter later force-pushes, re-verify before trusting the pin.
