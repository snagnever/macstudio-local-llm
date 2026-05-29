# Local LLM Daily Reference

**Hardware:** Mac Studio M4 Max, 128 GB unified memory
**Backend:** LM Studio + MLX
**Server:** `http://<lm-studio-host>:1234/v1` (OpenAI-compatible)
**Anthropic-compat endpoint:** `http://<lm-studio-host>:1234/v1/messages`

---

## Quick Reference — "If you're doing X, use Y"

| Task | Model |
|---|---|
| Agentic coding (OpenCode, Cline, OpenClaw) | `qwen/qwen3-coder-next` |
| Hard reasoning, code review, careful single-file edits | `qwen3.6-27b` |
| Knowledge-heavy Q&A, broad-domain quality | `qwen3.6-27b` (still the knowledge king post-Phase-2) |
| Fast general chat, light coding, fast iteration | `qwen3.6-35b-a3b@6bit` or `gemma-4-26b-a4b-it-mlx@6bit` |
| Fast coder (raw decode + tool-calling, no reasoning) | **`gemma-4-26b-a4b-it-mlx@4bit`** — 100 t/s gen, HE 98 %, jdhodges 98 % |
| Vision tasks needing 26B-class quality | `gemma-4-26b-a4b-it-mlx@6bit` |
| Tiny / FIM / quick tool-calls | `gemma-4-e4b-it-mlx` — useful for autocomplete & call-and-format only; **don't ask it MATH** (14 %) |
| Inline tab-completion (FIM) | *Qwen 2.5 Coder 7B — to add*; interim: `gemma-4-e4b-it-mlx` |
| Vision / OCR / screenshots | Built-in on all current MLX models; reach for `gemma-4-26b-a4b-it-mlx@6bit` first |

**Default for OpenCode:** `qwen/qwen3-coder-next` (unchanged after Phase 2 — no Gemma beat it on the combined coding + tool-calling + knowledge profile). **Now confirmed on Terminal-Bench 2.0 (2026-05-29):** coder-next leads the rig at **32.6 %** (vendor 36.2 %); `qwen3.6-27b` dense is +1.1 pp behind at **31.5 %** but 6× slower decode → coder-next wins on the speed-adjusted agentic-loop trade-off. `qwen3.6-35b-a3b@6bit` lands #3 at **28.1 %**. Best Gemma (`gemma-4-31b` dense) is at **22.5 %**, a full ~10 pp behind — the Gemma LCB top-rank does *not* transfer to agentic shell. All seven local rows are on [`reports/quality-benchmarks-charts.html`](../reports/quality-benchmarks-charts.html#chartTBench).

> **Model ID note:** the IDs above are exactly what `GET /v1/models` returns from the LM Studio server. Use these strings verbatim in client configs — the older `mlx-community/...` paths will 404.

---

## The Model Lineup

Verified against `lms ls` / `GET /v1/models` on 2026-05-18. All MLX models below advertise `vision: true` and `trainedForToolUse: true` in their metadata (per the LM Studio model API), except where noted.

| Model ID | Total / Active | Format | Quant | Disk | Vision | Tools | Role |
|---|---|---|---|---|:---:|:---:|---|
| `qwen/qwen3-coder-next` | 80B / 3B (MoE) | MLX safetensors | **6-bit** (4-bit variant also on disk) | **64.76 GB** | ✓ | ✓ | Agentic coder |
| `qwen3.6-27b` | 27B dense | MLX safetensors | 6-bit | 22.80 GB | ✓ | ✓ | Reasoning specialist |
| `qwen3.6-35b-a3b@6bit` | 35B / 3B (MoE) | MLX safetensors | 6-bit | 29.09 GB | ✓ | ✓ | Fast generalist |
| `qwen3.6-35b-a3b@8bit` | 35B / 3B (MoE) | MLX safetensors | 8-bit | 37.75 GB | ✓ | ✓ | Same weights, heavier quant — quant A/B vs @6bit |
| `gemma-4-26b-a4b-it-mlx@4bit` | 26B / 4B (MoE) | MLX safetensors | 4-bit | 15.64 GB | ✓ | ✓ | Knowledge / quality generalist (compact) |
| `gemma-4-26b-a4b-it-mlx@6bit` | 26B / 4B (MoE) | MLX safetensors | 6-bit | 21.81 GB | ✓ | ✓ | Same weights, heavier quant — quant A/B vs @4bit |
| `gemma-4-31b-it-mlx` | 31B dense | MLX safetensors | 8-bit | 33.80 GB | ✓ | ✓ | Dense Gemma 4 above 26B-A4B; new slot to evaluate |
| `gemma-4-e4b-it-mlx` | 4B dense | MLX safetensors | 8-bit | 8.97 GB | ✓ | ✓ | Tiny fast / quick tool calls |
| `deepseek-v4-flash-dq` | DeepSeek V4 Flash | MLX safetensors | 2-bit DQ | 96.53 GB | — | — | Frontier reasoning (⚠ tight fit) |
| `text-embedding-nomic-embed-text-v1.5` | — | GGUF | Q4_K_M | 84 MB | — | — | Embeddings for RAG |

> **Removed from disk since the previous inventory pass** (2026-05-18): `nvidia/nemotron-3-nano-omni` (GGUF Q4_K_M, 26 GB) and `deepseek-v4-flash` 4-bit (151 GB, never loaded — exceeded 128 GB unified mem). Their `lms`/HF entries are gone; drop them from any client config that still references them. The DQ variant of DeepSeek V4 Flash (96.53 GB) remains.

> **Out-of-scope community re-quants on disk** (alignment-stripped variants — not daily-driver candidates): `qwen3.6-27b-paro` (z-lab, 18.80 GB), `qwen3.6-27b-ud-mlx` (unsloth 4-bit, 26.21 GB), `qwen3.6-27b-jang_4m-crack` (dealignai 4-bit, 17.55 GB), `gemma-4-31b-jang_4m-crack` (dealignai 8-bit, 22.69 GB).

### Detailed pros/cons

**`qwen/qwen3-coder-next` — Agentic Coder**

| Pros | Cons |
|---|---|
| Best-in-class local agentic coding (SWE-rebench Pass@5 64.6%) | Largest practical model on disk (64.76 GB at 6-bit) |
| Trained for Claude Code / Qwen Code / Cline scaffolds — well-formed tool calls | 4-bit variant on disk if you need to free RAM for a second model |
| Native 256K context, extends to 1M with YaRN | KV cache grows fast in long agent loops — cap context at load |
| Only 3B active params → fast inference despite 80B total | |
| Ideal for multi-step tool-calling workflows | |

**`qwen3.6-27b` — Reasoning Specialist**

| Pros | Cons |
|---|---|
| Highest raw reasoning quality on the rig | Dense → slower (~20 tok/s), all 27B params active every token |
| SWE-bench Verified 77.2; T-Bench 2.0 vendor 59.3 (Opus 4.5 parity), but **on this rig 31.5 %** ⌛0.5x cap (2026-05-29 measured) — frontier vendors run more elaborate agent harnesses than terminus-2 | Not optimized for long agentic loops |
| 6-bit preserves syntax precision | Larger first-token latency |
| Vision + tool use capable | |

**`qwen3.6-35b-a3b` — Fast Generalist**

| Pros | Cons |
|---|---|
| Excellent quality/speed balance — ~30 tok/s | Less specialized for coding than coder-next |
| Only 3B active → near-instant responses | Less deep on hard reasoning than the 27B dense |
| Good middle option when coder-next feels overkill and dense feels slow | |
| Wide-domain knowledge, vision + tools | |

**`gemma-4-26b-a4b-it-mlx` — Fast Coder + Vision Generalist (post-Phase-2)**

| Pros | Cons |
|---|---|
| **HumanEval 98 %, jdhodges 98 %, Veerman 83 %** — coding + tool-calling parity with the best Phase 1 model | Knowledge ceiling **below `qwen3.6-27b`** by 10pp MMLU, 5pp MATH, 11pp DROP, 17pp GPQA — Phase 2 confirmed |
| **`@4bit` is the fastest model on this rig** (100 t/s ops-agent gen, 15.64 GB) | LCB **66 %** (post-Step-B): 8 of 9 32k truncations are real model limits at 65k, not cap-too-tight |
| **`@6bit` is the family flagship and the rig's LCB ceiling at 80 %** (post-Step-B, +18pp over best Qwen 27b 62 %) — MATH 83 %, GPQA 53 %; 80.8 t/s gen at 21.81 GB | |
| Vision + tools advertised on both quants | |
| Knowledge avg 78.0 % (@6bit), 76.4 % (@4bit) — between coder-next and 35b-a3b | |

**`gemma-4-31b-it-mlx` — Dense Knowledge (benched, demote)**

| Pros | Cons |
|---|---|
| Dense 31B at 8-bit (33.80 GB); DROP **85 %** is its only standout (vs `@6bit`'s 79 %) | **6× slower decode than `@6bit`** (13.7 vs 80.8 gen t/s) for indistinguishable quality on every other bench |
| Vision + tools per metadata | HumanEval −2, LCB −2, MMLU −1, MATH −4, GPQA −5 vs `@6bit` — pays the dense tax for no return |
| | Keep on disk only as a reproducibility reference; not for daily rotation |

**`gemma-4-e4b-it-mlx` — Tiny / FIM / quick-call only (benched)**

| Pros | Cons |
|---|---|
| MLX 8-bit / 8.97 GB — loads in seconds, can coexist with any other model | **MATH collapses to 14 %** at this size — do not use for math/reasoning |
| HumanEval 91 %, jdhodges 88 % — useful for autocomplete and call-and-format work | Veerman 67 % (−16pp vs the larger Gemmas); MMLU 65 %, GPQA 34 % |
| Vision + tools | Throughput **not** dramatically faster than `@4bit` MoE (70 vs 100 ops-agent gen t/s) — MLX optimises MoE A3B routing well |

**`deepseek-v4-flash-dq` — Frontier Reasoning (constrained)**

| Pros | Cons |
|---|---|
| Frontier-class reasoning at home | 96.53 GB weights → must be the **only** loaded model; cap context at 32 768 |
| MLX-native | 2-bit DQ; quality vs the un-quantized version unknown locally |
| | No tool-use training per model card |

---

## Loading Strategy

### Memory Math

Total unified memory: **128 GB**
- macOS + background apps baseline: ~20 GB
- Practical wired memory ceiling: ~95 GB

**Rule of thumb: keep total loaded weights + KV cache under ~80 GB.**

| Combo | Weights | Verdict |
|---|---|---|
| `coder-next` (6-bit) alone | 64.76 GB | OK — keep context ≤ 65k for headroom |
| `coder-next` (4-bit variant) alone | ~44 GB | Comfortable — room for 128k context |
| `qwen3.6-27b` alone | 22.80 GB | Tons of headroom |
| `qwen3.6-35b-a3b@6bit` alone | 29.09 GB | Tons of headroom |
| `qwen3.6-35b-a3b@8bit` alone | 37.75 GB | Tons of headroom |
| `gemma-4-26b-a4b-it-mlx@4bit` alone | 15.64 GB | Tons of headroom |
| `gemma-4-26b-a4b-it-mlx@6bit` alone | 21.81 GB | Tons of headroom |
| `gemma-4-31b-it-mlx` (8-bit dense) alone | 33.80 GB | Tons of headroom |
| `gemma-4-e4b-it-mlx` (8-bit) alone | 8.97 GB | Tiny footprint; coexists with anything |
| `gemma-4-26b-a4b@4bit` + `qwen3.6-27b` | 38.4 GB | Comfortable — viable two-model resident pair |
| `gemma-4-26b-a4b@4bit` + `qwen3.6-35b-a3b@6bit` | 44.7 GB | Comfortable |
| `gemma-4-31b` + `qwen3.6-27b` | 56.6 GB | OK — comfortable two-model pair, dense-Gemma + dense-Qwen |
| `coder-next` (6-bit) + `gemma-4-26b-a4b@4bit` | 80.4 GB | Tight — only with strict context caps; prefer JIT swap |
| `coder-next` (6-bit) + `qwen3.6-35b-a3b@6bit` | 93.8 GB | ❌ Risky — close to the practical ceiling |
| `coder-next` (6-bit) + `qwen3.6-27b` | 87.6 GB | ❌ Has caused queue stall historically |
| All three Qwens simultaneously | 124.6 GB | ❌ Don't. Swap will hit and crawl |
| `deepseek-v4-flash-dq` alone | 96.53 GB | ⚠ Only model resident; context ≤ 32 768 |

### Recommended Pattern: One Model at a Time

Enable LM Studio's **Just-in-Time (JIT) Model Loading**:

- Settings → Developer → **Just-in-Time Model Loading** → ON
- **Keep last used JIT loaded model loaded in memory** → OFF (or set short timeout)

LM Studio will load the model on first request and unload it when another is needed. Cold-load penalty: ~5–15 s per swap. Worth it to avoid the queue-stall problem.

### Context Length on Load

When loading a model in LM Studio, **always set Context Length explicitly**:

| Use case | Recommended context |
|---|---|
| Agentic loops (OpenCode, OpenClaw, Cline) | 65,536 |
| Long-doc Q&A | 131,072 |
| Short chat / quick tasks | 32,768 |

Don't max out at 262k+ unless actively needed — KV cache reserves memory proportional to this setting, and unbounded growth was the root cause of past stalls.

---

## Client Configurations

### OpenCode

Config: `~/.config/opencode/opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "lmstudio": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LM Studio (Mac Studio)",
      "options": {
        "baseURL": "http://<lm-studio-host>:1234/v1"
      },
      "models": {
        "qwen/qwen3-coder-next": {
          "name": "Qwen3 Coder Next 80B-A3B",
          "tools": true
        },
        "qwen3.6-27b": {
          "name": "Qwen 3.6 27B (dense, reasoning)",
          "tools": true
        },
        "qwen3.6-35b-a3b": {
          "name": "Qwen 3.6 35B-A3B (fast MoE)",
          "tools": true
        },
        "gemma-4-26b-a4b-it-mlx": {
          "name": "Gemma 4 26B-A4B (knowledge generalist)",
          "tools": true
        }
      }
    }
  },
  "model": "lmstudio/qwen/qwen3-coder-next"
}
```

Swap in-session with `/models`.

### OpenClaw

`~/.openclaw/config.yaml`:

```yaml
llm:
  name: mac-studio-local
  type: openai-compatible
  api: openai-responses
  base_url: http://<lm-studio-host>:1234/v1
  api_key: <your-lm-studio-key>
  model: qwen/qwen3-coder-next
  timeout_ms: 120000
  context_window: 65536
```

### Cline / Roo Code (VS Code)

Settings → API Provider → **LM Studio** → Base URL: `http://<lm-studio-host>:1234`
Select `qwen/qwen3-coder-next` from the model list.

### Aider

```bash
aider \
  --openai-api-base http://<lm-studio-host>:1234/v1 \
  --openai-api-key dummy \
  --model openai/qwen/qwen3-coder-next
```

### Claude Code (uses Anthropic-compat endpoint)

```bash
export ANTHROPIC_BASE_URL=http://<lm-studio-host>:1234
export ANTHROPIC_AUTH_TOKEN=<your-lm-studio-key>
claude
```

### Continue.dev (for FIM, after adding Qwen 2.5 Coder 7B)

`~/.continue/config.json`:

```json
{
  "models": [{
    "title": "Qwen3 Coder Next (chat)",
    "provider": "openai",
    "model": "qwen/qwen3-coder-next",
    "apiBase": "http://<lm-studio-host>:1234/v1"
  }],
  "tabAutocompleteModel": {
    "title": "Qwen 2.5 Coder 7B (FIM)",
    "provider": "openai",
    "model": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    "apiBase": "http://<lm-studio-host>:1234/v1"
  }
}
```

---

## Daily Commands

```bash
# Check server is alive and list loaded models
curl -s http://<lm-studio-host>:1234/v1/models | jq '.data[].id'

# Quick chat test
curl -s http://<lm-studio-host>:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen/qwen3-coder-next",
    "messages": [{"role": "user", "content": "hello"}]
  }' | jq '.choices[0].message.content'

# Watch memory pressure during heavy use
sudo memory_pressure

# LM Studio CLI (if installed: brew install lmstudio or via app)
lms ps              # list loaded models with status
lms load <model>    # load a specific model
lms unload <model>  # unload
lms server start    # start the server
```

---

## Troubleshooting

**Symptom: requests queue and never return**
- Likely cause: two large MLX models loaded simultaneously
- Fix: eject one (My Models → Eject), then restart the request
- If queues stay stuck after eject: restart LM Studio entirely

**Symptom: very slow response after switching models**
- Normal cold-load: 5–15 s for JIT loading
- Persistent slowness: context length too high — reload with lower ceiling
- Check `memory_pressure` for swap usage

**Symptom: tool calls malformed in OpenCode/Cline/OpenClaw**
- Switch to `qwen/qwen3-coder-next` (trained for tool scaffolds)
- If already on coder-next: drop context to ≤32k and retry
- Verify `"tools": true` is set in client config

**Symptom: kernel panic / Mac reboot during long agent session**
- MLX KV-cache unbounded growth (known issue)
- Fix: always cap context length at load time
- Keep LM Studio updated

**Symptom: 404 on model name from API**
- Model identifier must match exactly what `/v1/models` returns
- Verify with: `curl http://<lm-studio-host>:1234/v1/models | jq '.data[].id'`

---

## Performance Expectations (verified on this rig)

Headline numbers from [`benchmarking/local-llm-bench/results/`](benchmarking/local-llm-bench/results/) (LM Studio MLX, M4 Max 128GB / 40-GPU). "Gen tok/s" is pure decode; "Effective tok/s" includes prefill — what you actually wait for in agentic loops. See the per-scenario JSON for context-length curves.

| Model | Gen tok/s | Effective tok/s (ops-agent) | Prefill at 8.5k ctx | Status |
|---|---|---|---|---|
| `qwen/qwen3-coder-next` (6-bit MoE, 80B/3B) | 68–70 | **55.8** | 13.6 s (eff drops to 9.0 t/s) | ✓ Verified |
| `qwen3.6-35b-a3b@6bit` (MoE, 35B/3B) | 85–92 | **71.4** | 10.8 s (eff drops to 9.0 t/s) | ✓ Verified — fastest in lineup |
| `qwen3.6-27b` (6-bit dense) | 20 | **16.2** | 67 s (eff collapses to 1.9 t/s) | ✓ Verified — prefill is the killer |
| `qwen3.6-35b-a3b@8bit` | TBD | TBD | TBD | Pending — Phase 2 #9 |
| `gemma-4-26b-a4b-it-mlx@4bit` | TBD | TBD | TBD | Pending — Phase 2 #4 |
| `gemma-4-26b-a4b-it-mlx@6bit` | TBD | TBD | TBD | Pending — Phase 2 #5 |
| `gemma-4-31b-it-mlx` (8-bit dense) | TBD | TBD | TBD | Pending — Phase 2 #6 |
| `gemma-4-e4b-it-mlx` (8-bit, 4B) | TBD — expect fastest | TBD | TBD | Pending — Phase 2 #7 |
| `deepseek-v4-flash-dq` (2-bit DQ) | TBD | TBD | TBD | Pending — Phase 3 #10 |

Numbers depend on context size, prompt length, and concurrent activity. Use as a sanity check, not a substitute for re-benching.

## Benchmark Results (verified on this rig)

Headline accuracy + tool-calling scores from [`../tools/local-llm-bench-m4-32gb/benchmarks/runs/`](../tools/local-llm-bench-m4-32gb/benchmarks/runs/) (n=100 per knowledge bench except LCB n=50, 40/12 per tool suite; `temp=0, seed=42`). Full matrix in [`testing-plan.md`](testing-plan.md). Updated 2026-05-24 after Phase 1 LCB backfill + Step B Gemma reruns.

| Model | HumanEval | LCB v6 | MMLU | MATH | DROP | GPQA | jdhodges | veerman |
|---|---|---|---|---|---|---|---|---|
| `qwen/qwen3-coder-next` (6-bit) | 89 % | 56 % | 76 % | 84 % | 83 % | 37 % | 90 % | 83.3 % |
| `qwen3.6-27b` (6-bit dense) | 93 % | **62 %** | 88 % | 88 % | 90 % | 70 % † | 95 % | 83.3 % |
| `qwen3.6-35b-a3b@6bit` | 87 % | 54 % | 83 % | 89 % | 89 % | 65 % † | 97.5 % | 75.0 % |
| `gemma-4-26b-a4b@4bit` | 98 % | 66 % | 78 % | 80 % | 79 % | 47 % | 97.5 % | 83.3 % |
| `gemma-4-26b-a4b@6bit` | 97 % | **80 %** | 78 % | 83 % | 79 % | 53 % | 97.5 % | 83.3 % |
| `gemma-4-31b-it-mlx` (8-bit dense) | 95 % | 76 % | 77 % | 79 % | 85 % | 48 % | 97.5 % | 83.3 % |
| `gemma-4-e4b-it-mlx` (4B/8-bit) | 91 % | 68 % | 65 % | 14 % | 65 % | 34 % | 87.5 % | 66.7 % |

† = GPQA at 32 768 cap, raw scores under-count due to thinking spirals. Corrected ceilings: 27b ≈ 78–85 %, 35b-a3b ≈ 75–83 %. See [testing-plan.md truncation finding](testing-plan.md#truncation-finding-gpqa--thinking-models).

- **`gemma-4-26b-a4b@6bit` is the rig's LCB ceiling at 80 %** (+18 pp over the best Qwen). Knowledge generalist slot is still `qwen3.6-27b`; LCB-specific recommendation has diverged from knowledge after Phase 2 + Step B.
- **LiveCodeBench (v6)** support was added to the harness on 2026-05-18 — see [`local-llm-bench-m4-32gb/scripts/bench2.py`](local-llm-bench-m4-32gb/scripts/bench2.py). Contamination-resistant rolling-window coding suite; supersedes HumanEval as the primary frontier-comparable coding metric. Run with `--max-tokens 65536` for any thinking model or Gemma 4.
- **GPQA gap** on `qwen3-coder-next` (37 %) reflects the reasoning-model vs single-pass divide — coder-next emits zero thinking tokens by design.
- **Tool calling** ranks ahead of knowledge for daily-driver decisions (per upstream finding): both Phase 1 daily-drivers exceed 80 % on both suites with identical veerman scores, but jdhodges separates them (35b-a3b: 97.5 %, 27b: 95 %, coder-next: 90 %).

---

## Network Access from Other Devices

LM Studio is exposed on the LAN at `http://<lm-studio-host>:1234`. To use from another machine on the network:

1. Confirm LM Studio's **Server Settings → Serve on Local Network** is ON
2. From the other machine: `curl http://<lm-studio-host>:1234/v1/models`
3. If blocked: check macOS firewall (System Settings → Network → Firewall → allow LM Studio)

For access from outside the LAN, install **Tailscale** on both ends — gives each device a stable `100.x` IP without exposing port 1234 publicly.

---

## Watchlist (Models to Consider Adding)

| Candidate | Purpose | Status / When |
|---|---|---|
| `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` | Inline FIM autocomplete (Continue.dev, Zed) | Add when starting IDE autocomplete workflow |
| `mlx-community/Qwen2.5-VL-72B-Instruct-4bit` | Heavy vision: OCR, diagram parsing, screenshots | Add only if built-in vision on current Gemma/Qwen MLX models proves insufficient |
| `mlx-community/Kimi-K2.6-Thinking-*` distilled | Currently #1 on open-source agentic coding leaderboard | Watch for a fitting distillation size |
| `0xSero/Gemma-4-21B-REAP` (GGUF) | Upstream's daily-driver winner — REAP-pruned Gemma 4 | Optional reproducibility check; lower priority now that the un-pruned 26B-A4B is local |

> `DeepSeek-V4-Flash-2bit-DQ` was moved off the watchlist — it's now downloaded (`deepseek-v4-flash-dq`, 96.53 GB). The 4-bit `deepseek-v4-flash` (151 GB) **has been removed from disk** as of 2026-05-18 (it never fit in 128 GB unified memory). Only the DQ variant remains.

---

## Useful Links

- LM Studio docs: https://lmstudio.ai/docs
- MLX community on Hugging Face: https://huggingface.co/mlx-community
- OpenCode docs: https://opencode.ai/docs
- Apple MLX framework: https://github.com/ml-explore/mlx
- Qwen3-Coder card: https://huggingface.co/Qwen/Qwen3-Coder-Next
- Cline (VS Code): https://github.com/cline/cline

---

## Maintenance Routine

**Weekly**
- Check `mlx-community` on HF for updates to current models
- Review LM Studio update notes
- Clean up unused models (My Models → ⋯ → Delete)

**Monthly**
- Re-evaluate model lineup against new releases
- Update OpenCode / Cline / Aider via their respective package managers
- Test that all clients still connect correctly

**Whenever a new flagship lands**
- Don't replace immediately — A/B against current default for a few sessions before swapping
- Keep the previous model around until the new one has proven itself on real workflows
