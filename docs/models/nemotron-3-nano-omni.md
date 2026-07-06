# Nemotron-3 Nano Omni

> **Status: ⚫ REMOVED 2026-05-18** — dropped from disk in the inventory pass that also removed the never-loaded DeepSeek-V4-Flash 4-bit.
> This card is a removal record; the model was never benchmarked on this rig.
> Last updated: 2026-07-05

## At a glance (official)

| Field | Value | Source |
|---|---|---|
| Vendor | NVIDIA — `nvidia/nemotron-3-nano-omni` (exact HF repo id not recorded in repo docs; not re-fetched for a removed model) | [local-llm-reference.md](../local-llm-reference.md) |
| Official specs | Not captured — the model was removed before any per-model documentation effort | — |

## Variants on this rig

| API id | Source repo | Format | Quant | Disk | Runtime | Status | Notes |
|---|---|---|---|---|---|---|---|
| `nvidia/nemotron-3-nano-omni` | nvidia (GGUF conversion, exact repo not recorded) | GGUF | Q4_K_M | 26 GB | LM Studio | ⚫ REMOVED 2026-05-18 | Dropped in inventory pass; `lms`/HF entries gone |

## Architecture & spec notes
Not captured before removal.

## Local performance (measured)
Not measured — removed before any benchmark phase reached it.

## Quality benchmarks (measured)
Not measured.

## Feasibility & verdict
Removed 2026-05-18 without a feasibility run. The [local-llm-reference.md](../local-llm-reference.md) removal note instructs: drop it from any client config that still references it.

## Known issues & fixes
None recorded.

## Loading & memory
No longer on disk (was 26 GB GGUF Q4_K_M).

## Client configuration
None — remove any stale references from client configs (per the removal note).

## External links
- Vendor family page: https://huggingface.co/nvidia (exact model repo id not recorded)

## History
- **≤2026-05-17** — on disk as GGUF Q4_K_M, 26 GB; never benchmarked.
- **2026-05-18** — ⚫ removed from disk in the inventory pass ([local-llm-reference.md](../local-llm-reference.md) watchlist/removal note).
