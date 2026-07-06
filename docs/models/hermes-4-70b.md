# Hermes-4-70B

> **Status: 🔴 BLOCKED** (2026-07-02) — chat-template (minja) render errors break tool-calling requests before a single token is generated. Both bugs are diagnosed and the fix is documented ([writeup](../hermes-4-minja-render-error-writeup.md)); benching is pending template fix + LM Studio cache refresh.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [NousResearch/Hermes-4-70B](https://huggingface.co/NousResearch/Hermes-4-70B), fine-tune of Meta-Llama/Llama-3.1-70B | HF card |
| Parameters | 71B dense | HF card |
| Architecture | `llama` (Llama-3.1) | HF card + local load |
| Native context | not stated on card (fetched 2026-07-05); Llama-3.1 lineage | HF card |
| License | Llama3 | HF card |
| Modalities | text only | HF card |
| Reasoning | Hybrid thinking mode: toggled via `thinking=True` template flag (or system prompt); emits `<think>…</think>`; `keep_cots=True` preserves prior-turn CoT | HF card |
| Tool calling | ✓ — tools in system message `<tools>…</tools>`, calls emitted as `<tool_call>{…}</tool_call>` (vLLM parser `hermes`, SGLang `qwen25`) | HF card |
| Vendor sampling | `temperature=0.6, top_p=0.95, top_k=20` | HF card |
| Vendor claims | "Top quality" reasoning across math/code/STEM/logic; SOTA on RefusalBench *(vendor — not reproduced locally)* | HF card |
| Release | 2025-08-25 (technical report) | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `nousresearch/hermes-4-70b` | [lmstudio-community/Hermes-4-70B-MLX-6bit](https://huggingface.co/lmstudio-community/Hermes-4-70B-MLX-6bit) | MLX | 6-bit (mlx_lm, LM Studio team conversion) | 57.3 GB | LM Studio MLX (mlx-llm 1.9.1) | 🔴 **BLOCKED 2026-07-02** | Loads fine as `llama` arch; the build's own `chat_template.jinja` throws at render on tool-calling requests |

## Architecture & spec notes
- Dense Llama-3.1-70B fine-tune with **hybrid reasoning extensions**: the chat template rewrites prior assistant turns to strip chain-of-thought when `thinking` is on — and that rewrite is exactly where the blocking bug lives (see Known issues).
- This build's `model.yaml` maps an OpenAI-style **`reasoning_effort`** request field onto the jinja `thinking` variable — so a client sending `"reasoning_effort": "medium"` (e.g. `hermes-agent`) silently flips the buggy template branch on.
- Llama-3-Chat format (role headers + special tags); the card says to render with `add_generation_prompt=True`.
- For MLX models LM Studio prefers the standalone `chat_template.jinja` over the copy embedded in `tokenizer_config.json` — only the standalone file needs patching.

## Local performance (measured)

None — blocked at prompt render. No speed probe, no soak. Dense 70B MLX at 6-bit → expect slow decode ("quality reference, not a throughput pick" per the [phase-5 plan](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)).

## Quality benchmarks (measured)

| Bench | MLX 6-bit | Notes |
|---|---|---|
| Tool-calling | **0%** pre-fix | **Not a quality signal** — every request errored at template render, before any tokens; the model never saw a prompt |
| HumanEval / LCB / MMLU / speed | ⏸ not run | Parked until the template renders |

## Feasibility & verdict

- **2026-07-02 — 🔴 BLOCKED at prompt render.** Tool-calling requests fail with:
  ```
  Error rendering prompt with jinja template: "Cannot perform operation + on undefined values"
  ```
  Fires during prompt *rendering*, upstream of the model — **not** the quant, not the weights, not null `content` in the messages (tool-call turns carry `content: ""`, which concatenates fine). Two independent template bugs produce this identical error; full diagnosis in the [minja render-error writeup](../hermes-4-minja-render-error-writeup.md).
- **Why it's intermittent:** cause #1 needs thinking=on (via `reasoning_effort` → `thinking`) **and** a prior assistant turn without `</think>` — which is why a naive repro "renders fine" and the generic LM Studio advice ("get the lmstudio-community template") is useless here: *this is already the lmstudio-community build*.
- **Minja ≠ Jinja2:** LM Studio renders with minja (C++). Missing attribute access is falsy (no error), an out-of-range list index returns *undefined* rather than raising, but `+` on an undefined operand throws. The diagnostic reproduction is Python Jinja2 with default `Undefined` against the real payload: `thinking=False` renders OK, `thinking=True` errors — that's the tell.
- **Unblock path (prerequisite before any bench):** apply both template guards (below) to `chat_template.jinja`, **eject + reload the model** (or restart the server) to flush LM Studio's parsed-template cache, verify with a single `lms.py check` warmup, then run the standard 70B ladder (speed probe → tool-calling → HumanEval → LCB → MMLU). Until then it stays out of the run queue ([testing-plan #17](../testing-plan.md), [phase-5 seq 6](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md)).
- **Hypothesis to test post-fix:** a Hermes/Llama-70B is a **reasoning + tool-use** play, not a coder — compare tool-calling and knowledge against `qwen3.6-27b` (95% jdhodges).

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| `Cannot perform operation + on undefined values` on tool-calling requests (intermittent) | **#1 — CoT-strip index (the one that bites agents):** with thinking on, the template runs `content.split('</think>', 1)[1]` on every prior assistant turn; a normal reply with no `</think>` → 1-element list → `[1]` out of range → undefined in minja → `+` throws | Guard the strip — only cut when there's something to cut: `{%- if '</think>' in content %}{%- set content = '<think> </think>' + content.split('</think>', 1)[1] -%}{%- endif %}`. Apply to **both** assistant branches (with and without tool_calls). Byte-identical output when `</think>` is present. **Documented, not yet applied on-rig.** |
| Same error, on the very first line (latent — hasn't fired here) | **#2 — `bos_token` concat:** both branches open with `bos_token + '<|start_header_id|>…'`; if the render context leaves `bos_token` undefined → same error | Default it: `{%- if not bos_token is defined %}{% set bos_token = '<|begin_of_text|>' %}{% endif %}` (matches this build's `special_tokens_map.json`; no-op when LM Studio supplies it, so no double-BOS — verified exactly one `<|begin_of_text|>` in output) |
| Template edit appears to have no effect | LM Studio **caches** the parsed template (`~/.lmstudio/.internal/model-index-cache.json`) and serves this as a virtual model (`nousresearch/hermes-4-70b` → `Hermes-4-70B-MLX-6bit`) | **Eject + reload** the model or restart the server; a plain "regenerate" keeps the stale cache. Only `chat_template.jinja` matters for MLX — the copy in `tokenizer_config.json` can be left alone |

Also in the [reference troubleshooting section](../local-llm-reference.md).

## Loading & memory
- 57.3 GB weights — fits the ~80 GB weights+KV pairing rule only barely; treat as effectively sole-large-model.
- **Operational note (2026-07-05):** was co-resident with `qwen3.6-27b` when `agents-a1-xl` arrived (~110 GB combined weights, swap maxed, `Spill=YES`); both were unloaded per the single-large-model residency rule (swap 19.9 GB → 166 MB). See [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md).

## Client configuration
- Model id: `nousresearch/hermes-4-70b` (LM Studio `/v1` endpoint, port 1234) — virtual id backed by the `Hermes-4-70B-MLX-6bit` concrete build.
- Sampling: vendor recommends `temperature=0.6, top_p=0.95, top_k=20`.
- **Do not send `reasoning_effort`** until the template is patched — it flips `thinking=true` and arms cause #1 on any multi-turn conversation with a plain assistant reply.
- Tool format: Hermes-native `<tool_call>` JSON (the format other local models here emulate as a workaround — see the DeepSeek-V4-Flash tool-template comparison in [M4 notes](../../tools/local-llm-bench-m4-32gb/results/M4_MAX_128GB_NOTES.md)).

## External links
- Vendor: https://huggingface.co/NousResearch/Hermes-4-70B (Llama3 license, released 2025-08-25)
- MLX conversion: https://huggingface.co/lmstudio-community/Hermes-4-70B-MLX-6bit (LM Studio team, mlx_lm, 6-bit, 57.3 GB)

## History
- **2026-07-02** — 🔴 BLOCKED: tool-calling requests fail at prompt render with the minja `+ on undefined` error. Root-caused to two independent `chat_template.jinja` bugs (CoT-strip index + `bos_token` concat); fixes documented in the [writeup](../hermes-4-minja-render-error-writeup.md). (Note: the [phase-5 plan](../benchmark-plans/2026-07-05-phase-5-new-arrivals.md) attributes the break to `bos_token` alone — the primary trigger is actually the CoT-strip.)
- **2026-07-05** — Phase-5 new-arrivals plan parks it as seq 6: "do not bench until the template renders"; a Claude-Agent-SDK provider that may carry the template fix is in flight. Unloaded from co-residency the same day to free the rig for `agents-a1-xl`.
