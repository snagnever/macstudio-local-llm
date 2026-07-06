# Nomic Embed Text v1.5

> **Status: 🟢 ACTIVE** (embeddings for RAG — un-benched by design; the quality-benchmark suite targets generative models).
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor / base model | [nomic-ai/nomic-embed-text-v1.5](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) | HF card |
| Parameters | 0.1B (long-context BERT architecture) | HF card |
| Embedding dims | 768 full, Matryoshka-truncatable to 512/256/128/64 (MTEB 62.28 → 56.10 across sizes) *(vendor)* | HF card |
| Native context | 2,048 tokens (dynamic RoPE scaling to 8,192 with config changes) | HF card |
| License | Apache 2.0 | HF card |
| Release | February 2024 | HF card |
| Multimodal | text embeddings aligned with nomic-embed-vision-v1.5 | HF card |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `text-embedding-nomic-embed-text-v1.5` | GGUF conversion (exact conversion repo not recorded; not in current LM Studio store — verify repo before re-downloading) | GGUF | Q4_K_M | 84 MB | LM Studio | 🟢 ACTIVE | Embeddings endpoint for RAG |

## Architecture & spec notes
- BERT-family encoder, not a generative model — served via `/v1/embeddings`, not chat completions.
- **Task prefixes are required** for correct behavior: `search_document:` (indexing), `search_query:` (queries), plus `clustering:` / `classification:` — omitting them degrades retrieval quality (HF card).

## Local performance (measured)
Not measured — no embedding benchmarks in the local suite; footprint (84 MB) is negligible.

## Quality benchmarks (measured)
Not measured — the rig's benchmark suite (HumanEval/LCB/MMLU/…) targets generative models. Vendor MTEB numbers above are *vendor* claims.

## Feasibility & verdict
Trivially feasible at 84 MB; loads alongside anything. The only open item is provenance: the model is no longer listed in the current LM Studio store, so the exact GGUF conversion repo should be verified before reinstalling on a new machine ([local-llm-reference.md](../local-llm-reference.md) lineup note).

## Known issues & fixes

| Symptom | Cause | Fix / status |
|---|---|---|
| Poor retrieval quality | Missing task prefixes | Prepend `search_document:` / `search_query:` per HF card |
| Model absent from LM Studio store | Store listing changed | Verify conversion repo before re-download |

## Loading & memory
84 MB — coexists with any model; no memory-math considerations. Load via LM Studio; exposed on the standard `/v1/embeddings` endpoint.

## Client configuration
- Model id: `text-embedding-nomic-embed-text-v1.5`
- Use OpenAI-compatible embeddings API at `http://<lm-studio-host>:1234/v1/embeddings`.
- Choose embedding dimensionality (768 default) per Matryoshka truncation if the vector store benefits from smaller vectors.

## External links
- Vendor: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5

## History
- **≤2026-05** — installed as the RAG embeddings model (84 MB GGUF Q4_K_M); recorded in the [lineup](../local-llm-reference.md).
- **2026-07-05** — model card created; noted missing from current LM Studio store.
