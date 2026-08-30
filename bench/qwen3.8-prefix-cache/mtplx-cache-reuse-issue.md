# Issue draft — MTPLX 2.10.0: tool turn re-prefills a 99% cached prefix under multi-session churn (128K)

> Draft for youssofal/MTPLX. Written for the maintainer.
> Status (2026-08-30): REPRODUCED (two byte-identical full runs) and traced with
> `MTPLX_DEBUG_PREFIX_DIVERGENCE=1`. Postable. Numbers came through a custom probe,
> but the mechanism is visible in the debug log and the repro sketch is vendor-only.

## Summary

At 131072 context with `--ssd-session-cache on`, a request whose prefix is 99.2%
identical to a banked entry (only the trailing ~1k tokens differ) re-prefills the
full prompt instead of restoring the shared prefix. It happens for a `tool_turn`
shape (base context + a tool-result turn) after other shapes over the same base
(exact resend, append, mid-edit) have run. Cost: a full ~870s re-prefill at 128K
instead of a ~120s restore+suffix.

Prefix reuse works in isolation (a base then a tool turn hits 0.99). It breaks only
under churn — several large sessions over the same base processed first.

## Environment

- MTPLX 2.10.0 (`pip install mtplx==2.10.0`)
- Apple M4 Max, 128 GB unified memory (Mac16,9), macOS 26.5.2 (25F84)
- Model: `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed` (native MTP, depth 3)
- Serve: `--profile turbo --generation-mode mtp --context-window 131072
  --ssd-session-cache on`
- Session bank: auto `48.0G total, 24.0G per-session, 48 entries`

## Reproduction

Over one ~125k-token base prefix, run these shapes in order, 3 repeats each, each
non-cold shape primed with the base first:

1. `cold` — base only.
2. `identical` — resend base.
3. `append` — base + ~1k plain-text suffix.
4. `middle_mutation` — base with ~64 tokens changed near the middle.
5. `tool_turn` — base + a tool-result turn (~1k-token suffix).

Measured `cached_tokens / prompt_tokens`:

| shape | reps |
|---|---|
| cold | 0.00, 0.00, 0.00 |
| identical | 1.00, 1.00, 1.00 |
| append | 0.99, 0.99, 0.99 |
| middle_mutation | 0.02, 0.02, 0.00 |
| **tool_turn** | **0.00, 0.00, 0.00** |

`tool_turn` re-prefills every time (~870s at 128K), even though `append` — the same
base plus a different ~1k suffix — reuses fine. In isolation (`cold → tool_turn`, or
`cold → middle_mutation → tool_turn`, one repeat), `tool_turn` hits 0.99.

## What the debug log shows (`MTPLX_DEBUG_PREFIX_DIVERGENCE=1`)

At the `tool_turn` measured request the best banked match is the `append` entry:

```
prefix-diverge: entry_len=126645 matched=125610 prompt_len=126688
  entry [125586:125650]: '... in that order.\n\nappend-record-000000 append-record-...'
  prompt[125586:125650]: '... in that order.<|im_end|>\n<|im_start|>assistant ... <tool_call> ...'
store-on-prefill: len=126688 boundaries=7 cached=0 restore=cold
```

So 125610 of 126688 tokens (99.2%) are a shared prefix, and the two diverge only at
the suffix. The request still stores `cached=0 restore=cold` — a full re-prefill.

Two factors combine:

1. **Postcommit backlog.** The region shows 27 `postcommit cross-session yield ...
   reason=cross_session_foreground_preempted`, backlog up to `count: 4`. The
   `tool_turn` prime (which would bank a clean base) is preempted by the following
   foreground request, so no clean-prefix entry is committed in time. In the
   isolated runs a `prefix-diverge: ... clean prefix (matched=126688)` entry exists
   and `exact-restore` fires. Under churn it does not.
2. **Near-prefix not restored.** With only the `append` entry available (identical
   base, divergent suffix), the runtime does not restore the 125610 shared tokens —
   it re-prefills. `near-prefix reject: entry_len=126645 matched=125610 min_restore=0
   reason=served`.

Either behavior alone would explain the miss; together they make `tool_turn`
re-prefill under any realistic churn.

## Expected

A request that shares a 99% prefix with a banked entry should restore that prefix
and prefill only the divergent tail (as `append` does), rather than re-prefilling
from scratch. Block/content-addressed caches (e.g. oMLX, mlx-dspark) reuse the
shared base here and recompute only the tail.

## Minimal reproduction (vendor tooling)

```bash
MTPLX_DEBUG_PREFIX_DIVERGENCE=1 mtplx serve \
  --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
  --context-window 131072 --ssd-session-cache on --port 8000 &

# P = a ~125k-token base prompt.
# 1) Send P (cold).
# 2) Send P + suffix_A (a ~1k plain-text continuation).       -> reuses base (hit)
# 3) Send P with ~64 mid tokens changed.                      -> partial
# 4) Send P + suffix_tool (a tool-result turn, ~1k tokens).   -> observed: full re-prefill
# Repeat 2-4 a few times to build the postcommit backlog.
# Inspect usage.prompt_tokens_details.cached_tokens on step 4, and the debug log.
```

## What to investigate

1. Why the `tool_turn` prime's clean-base commit is dropped/preempted under a
   postcommit backlog (`cross_session_foreground_preempted`, backlog 4). The 2.9.1
   note "postcommit within 0.6s now awaited instead of discarded" seems not to hold
   under backlog.
2. Why the near-prefix path rejects a 125610/126688 (99.2%) match with a divergent
   suffix (`reason=served`, `min_restore=0`) instead of restoring the shared prefix.
3. Whether the append suffix vs tool suffix distinction matters, or it is purely the
   "no clean-prefix entry present + only a divergent-suffix entry available" case.

## Notes

- Not a capacity/eviction problem: shrinking the RAM bank to 12G did not reproduce
  the miss (the probe re-primes the base before each measure). Not an SSD-restore
  problem either.
- `--ssd-session-cache off` is worse: it also loses `append` at 128K (0.00), which
  2.9.2 reused via the live frontier at the same 24G per-session cap.
