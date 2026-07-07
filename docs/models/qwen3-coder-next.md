# Qwen3-Coder-Next (80B-A3B)

> **Status: 🟢 DAILY DRIVER — Agent role winner.**
> Terminal-Bench 2.0 **32.6 %** — #1 on rig, measured 2026-05-29 (vendor claims 36.2 %). Default model for OpenCode / Cline / OpenClaw / Claude Code agentic loops.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [Qwen/Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) | HF card (fetched 2026-07-05) |
| Parameters | 80B total MoE / 3B active (79B non-embedding, hidden dim 2048) | HF card |
| Architecture | `qwen3_next` — 48 layers, hybrid: 12 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE)); 512 experts / 10 active + 1 shared, expert dim 512 | HF card |
| Attention | Hybrid: Gated Attention (16 Q-heads, 2 KV-heads) + Gated DeltaNet (32 V-heads, 16 QK-heads); `full_attention_interval: 4` → only 12 of 48 layers keep a growing KV cache | HF card + [reference doc](../local-llm-reference.md#two-resident-pair-context-math) |
| Native context | 262,144 tokens; 1M with YaRN per [reference doc](../local-llm-reference.md) *(YaRN extension not stated on fetched card)* | HF card / local docs |
| License | Apache 2.0 | HF card |
| Reasoning | **Non-thinking only** — does not generate `<think></think>` blocks; single-pass by design (harness logs `think=0` on every response) | HF card + [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md) |
| Tool calling | ✓ — trained for Claude Code / Qwen Code / Cline (card also lists Coder, Kilo, Trae scaffolds) | HF card |
| Vendor sampling | `temperature=1.0, top_p=0.95, top_k=40` | HF card |
| Vendor claims | SWE-bench Verified 70.6 %, SWE-bench Pro 44.3 %, Terminal-Bench 2.0 36.2 % *(vendor — T-Bench reproduced locally at 32.6 %, see below)*; SWE-rebench Pass@5 64.6 % *(vendor, as cited in [reference doc pros/cons](../local-llm-reference.md#detailed-proscons) — not on the fetched card)* | HF card + local docs |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `qwen/qwen3-coder-next` | [lmstudio-community/Qwen3-Coder-Next-MLX-6bit](https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-6bit) | MLX safetensors | 6-bit | 64.76 GB | LM Studio MLX | 🟢 **Benched — daily driver** | Full Phase 1 suite + LCB backfill + T-Bench A1 all on this variant |
| `qwen/qwen3-coder-next@4bit` | [lmstudio-community/Qwen3-Coder-Next-MLX-4bit](https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-4bit) | MLX safetensors | 4-bit | ~44 GB | LM Studio MLX | ⏳ **Un-benched** (pending Phase 2 #8 quant A/B) | Kept on disk for two-resident pairing — see Loading & memory |

**Pinned HF revisions** (verified 2026-07-06 via HF API: no upstream commits since download → local snapshot = current `main`): 6-bit: [`6b4712e`](https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-6bit/tree/6b4712e5519c7a7c5612992c5fca1608f42a14c2) (downloaded 2026-05-16) · 4-bit: [`03cba26`](https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-4bit/tree/03cba26036330b7553d252c1f3fb899f16cc5ea5) (downloaded 2026-04-28).

## Architecture & spec notes
- Hybrid linear-attention design is why its long context is cheap: with `full_attention_interval: 4`, only **12 of 48** layers grow a KV cache (the other 36 are Gated DeltaNet with constant recurrent state), at just **2 KV heads × head_dim 256**. KV at 128k is only ~3.3 GB — far cheaper than any dense model on the rig. Details: [reference doc § Two-Resident Pair context math](../local-llm-reference.md#two-resident-pair-context-math).
- 512-expert MoE with 10 active + 1 shared expert; 3B active params is why an 80B model decodes at ~68–70 t/s on this rig.
- **Zero thinking tokens by design** — the single-pass architecture is a deliberate trade: it caps GPQA-style reasoning (37 %) but makes agentic loops fast and token-cheap (full Phase 1 suite in 1.9 h vs 27b's 37.6 h).
- MLX 6-bit conversion by the LM Studio team using `mlx_lm` (version not stated on card), safetensors BF16/U32, 64.7 GB per card / 64.76 GB on disk.

## Local performance (measured)

| Metric | MLX 6-bit |
|---|---|
| Generation | **68–70 t/s** decode (67.8 eff / 70.2 gen on quick probe) |
| Effective throughput (ops-agent) | **55.8 t/s** (incl. prefill) |
| Prefill @ 8.5k ctx | **13.6 s** — effective drops to 9.0 t/s on prefill-heavy turns |
| Tool-call runs | 18.6 t/s (jdhodges), 35.4 t/s (Veerman) |
| Memory | 64.76 GB weights; wired peaked 88 GB with KV during Phase 1, swap flat at 66–68 MB |
| Wall-clock, full Phase 1 suite | **1.9 h** (19× faster than `qwen3.6-27b` dense) |

Sources: [reference doc § Performance Expectations](../local-llm-reference.md#performance-expectations-verified-on-this-rig), [testing-plan.md](../testing-plan.md) throughput matrix, [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).
4-bit variant throughput: ⏳ TBD (Phase 2 #8) — quality delta vs 6-bit is estimated (~3–4 pp), not measured.

## Quality benchmarks (measured)

Config: MLX 6-bit, n=100 per knowledge bench (LCB n=50), `temp=0, seed=42`, ctx 65,536, sole-model. Phase 1 run 2026-05-17; LCB backfill 2026-05-24; T-Bench 2026-05-29.

| Bench | Score | Notes |
|---|---|---|
| **Terminal-Bench 2.0** | **32.6 %** (29/89 PASS) | **#1 on rig** (vendor 36.2 % — 3.6 pp gap, consistent with 6-bit quant cost vs vendor BF16). ⌛0.5x agent-timeout cap → defensible floor. 16.8 h |
| HumanEval | 89 % | Saturated bench — LCB is the canonical coding signal |
| LiveCodeBench v6 (n=50) | 56 % | Clean: 0 truncations, 0 errors after Q19 rerun at 65k (Q19 = genuine model failure, not cap artifact). 42 min |
| MMLU | 76 % | |
| MATH | 84 % | On par with `qwen3.6-27b` (88 %) at 19× the suite speed |
| DROP | 83 % | |
| GPQA | 37 % | Floor by design — zero thinking tokens, 0 truncations; can't reason through grad-level MCQs single-pass |
| jdhodges tool-calling (40) | 90 % | |
| Veerman tool-calling (12) | 83.3 % | Combined tool-calling 88.5 % |

Knowledge avg 73.8 % — lowest of the Phase 1 trio, but the T-Bench inversion is the headline: **LCB rank 5th → T-Bench rank 1st (+4 spots)**. The agentic shell loop is this model's design target; static benches miss it. Best Gemma (LCB ceiling 80 %) lands ~10 pp behind on T-Bench.
Raw data: `tools/local-llm-bench-m4-32gb/benchmarks/runs/*_qwen_qwen3-coder-next_20260517_*`, `livecodebench_qwen_qwen3-coder-next_MERGED_summary.json`, `tbench_qwen-qwen3-coder-next_*.{jsonl,_summary.json}`.

## Feasibility & verdict

- **Agent role winner — 🟢 DAILY DRIVER.** Confirmed twice: Phase 2 could not displace it (Gemma `@4bit` codes well but its knowledge floor is too low for general agentic use), and Terminal-Bench 2.0 (2026-05-29) put it **#1 on the rig at 32.6 %**.
- `qwen3.6-27b` dense is only 1.1 pp behind on T-Bench (31.5 %) but 6× slower decode (~20 vs ~68 t/s) — in high-turn-count agentic loops the speed advantage compounds, so coder-next wins the speed-adjusted trade-off.
- **Not the quality king:** switch to `qwen3.6-27b` for single hard questions (knowledge avg 85.8 vs 73.8), and `gemma-4-26b-a4b@6bit` holds the one-shot LCB ceiling (80 % vs 56 %). Those leads do **not** transfer to agentic shell.
- **Vendor honesty check:** 32.6 % measured vs 36.2 % claimed is a 3.6 pp gap, consistent with MLX 6-bit quant cost — the vendor's agentic-default branding is honest.
- **Remaining work:** Phase 2 #8 quant A/B (`@4bit` vs `@6bit`) — unlocks the ⭐ recommended two-resident pair with measured numbers.

Plans: [2026-05-22-livecodebench-phase-1.md](../../bench/lcb-phase1/plan.md) · [2026-05-24-terminal-bench-phase-a-plus-b.md](../../bench/terminal-bench/plan.md) · [testing-plan.md](../testing-plan.md)

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| Malformed tool calls in OpenCode/Cline/OpenClaw at long context | Degrades past ~32k ctx | Drop context to ≤ 32k and retry; verify `"tools": true` in client config. See [Troubleshooting](../local-llm-reference.md#troubleshooting) |
| KV cache grows fast in long agent loops | Unbounded context reservation was the root cause of past queue stalls | **Always cap context length at load time** (65,536 for agent loops) |
| GPQA / grad-level reasoning floor (37 %) | Zero thinking tokens by design — single-pass | Not a bug; route hard reasoning to `qwen3.6-27b` |
| Queue stalls when paired with a second large model | 6-bit + 27b = 87.6 GB breaks the ~80 GB rule | JIT swap, or pair the **4-bit** variant instead |

## Loading & memory

- **Sole resident (6-bit, 64.76 GB):** OK — keep context **≤ 65k** for headroom. 4-bit (~44 GB) alone is comfortable with room for 128k.
- **Pairing (~80 GB weights+KV rule):**

| Combo | Weights | Verdict |
|---|---|---|
| `coder-next@4bit` + `gemma-4-26b-a4b@6bit` ⭐ | ~66 GB | **Recommended pair** — agent loops + fast generalist; ~14 GB KV headroom; both models architecturally KV-cheap. Set both to 65,536; ~70.5 GB total |
| `coder-next@4bit` + `qwen3.6-27b` | ~67 GB | Viable — planning + agent in one session |
| `coder-next@6bit` + `gemma-4-26b-a4b@4bit` | 80.4 GB | Tight — at the 80 GB rule before any KV; **prefer JIT swap** |
| `coder-next@6bit` + `qwen3.6-27b` | 87.6 GB | ❌ Has caused queue stalls historically |
| `coder-next@6bit` + `qwen3.6-35b-a3b@6bit` | 93.8 GB | ❌ Risky — near the practical ceiling |

- **Big repo in the window?** Its hybrid layers make long context the cheap one: push coder-next to 131,072 (~3.3 GB KV) and keep the paired model at 32–64k.
- Why pair at 4-bit: dropping the coder to 4-bit costs an estimated ~3–4 pp agentic quality and buys ~14 GB shared KV headroom. Full math: [reference doc § Loading Strategy](../local-llm-reference.md#loading-strategy).

## Client configuration

Model id: `qwen/qwen3-coder-next` (LM Studio `/v1` endpoint, port 1234). Local benches ran temp 0 / seed 42; vendor recommends `temperature=1.0, top_p=0.95, top_k=40`.

**OpenCode** (`~/.config/opencode/opencode.json`) — default model:

```json
{
  "provider": { "lmstudio": {
    "npm": "@ai-sdk/openai-compatible",
    "options": { "baseURL": "http://<lm-studio-host>:1234/v1" },
    "models": { "qwen/qwen3-coder-next": { "name": "Qwen3 Coder Next 80B-A3B", "tools": true } }
  }},
  "model": "lmstudio/qwen/qwen3-coder-next"
}
```

**OpenClaw** (`~/.openclaw/config.yaml`):

```yaml
llm:
  type: openai-compatible
  base_url: http://<lm-studio-host>:1234/v1
  model: qwen/qwen3-coder-next
  timeout_ms: 120000
  context_window: 65536
```

**Aider:**

```bash
aider --openai-api-base http://<lm-studio-host>:1234/v1 \
      --openai-api-key dummy \
      --model openai/qwen/qwen3-coder-next
```

**Cline / Roo Code:** API Provider → LM Studio → Base URL `http://<lm-studio-host>:1234`, select `qwen/qwen3-coder-next`. Full snippets (incl. Claude Code and Continue.dev): [reference doc § Client Configurations](../local-llm-reference.md#client-configurations).

## External links
- Vendor: https://huggingface.co/Qwen/Qwen3-Coder-Next
- MLX 6-bit conversion (benched): https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-6bit (LM Studio team via `mlx_lm`, 64.7 GB)
- MLX 4-bit conversion (on disk, un-benched): https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-4bit

## History
- **2026-05-17** — Phase 1 full suite (n=100, 1.9 h): HumanEval 89 %, MMLU 76 %, MATH 84 %, DROP 83 %, GPQA 37 %, jdhodges 90 %, Veerman 83.3 %. Verdict: speed/agentic-tool king, not the quality king ([M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)).
- **2026-05-22 → 05-24** — LCB v6 backfill ([plan](../../bench/lcb-phase1/plan.md)): 56 %, clean after Q19 rerun at 65k (genuine model failure, not cap artifact).
- **2026-05-22** — Phase 2 verdict: agentic-coder slot **unchanged** — no Gemma displaced it on the combined coding + tool-calling + knowledge profile.
- **2026-05-24 → 05-29** — Terminal-Bench 2.0 Phase A+B ([plan](../../bench/terminal-bench/plan.md)): **32.6 %, #1 on rig** (vendor 36.2 %); LCB rank inverted (+4 spots). Agent role winner confirmed.
- **Pending** — Phase 2 #8: `@4bit` quant A/B to validate the ⭐ two-resident pair with measured numbers.
