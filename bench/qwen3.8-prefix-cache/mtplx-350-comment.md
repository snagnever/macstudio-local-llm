# Comment draft for youssofal/MTPLX PR #350

> Paste-ready comment for PR #350 (exact semantic session anchors). Offers a
> concrete boundary case the semantic-anchor path should cover. Not yet posted.

---

A boundary case for the semantic-anchor path, with a repro it should cover.

On stock 2.10.0 (no semantic anchors), a tool turn at 128K re-prefills the whole
prompt, while a plain append over the same base restores 99%. Same base prefix, same
~1k suffix length:

| shape | cached/prompt |
|---|---|
| append (base + ~1k plain suffix) | 0.99 |
| tool_turn (base + tool-result turn, ~1k suffix) | 0.00 |

The tool turn's commit fails, so no clean anchor for the base survives:

```
store-on-prefill: len=126688 cached=0 restore=cold
session_commit: committed=false,
  reason=retokenized_prefix_older_than_session,
  unsafe_reason=stop_token_boundary_mismatch
```

The re-serialized tool-call markup shifts the token boundary, so exact-restore and
near-prefix both fall through to cold. The append case keeps its boundary and restores
via `block_prefix_boundary_clone`.

Does this PR's complete-message prefix planning make the message boundary before a tool
turn a valid anchor, so the base restores across the tool turn? That is the case #121
closed on block-overlap salvage, but at 128K the tool turn gets zero salvage
(`cached=0`), so a client that calls a tool every turn pays a full ~870s re-prefill.
The #383 cross-session preemption is a separate factor. I ruled it out as the sole
cause here: `MTPLX_POSTCOMMIT_WAIT_TIMEOUT_S=30` leaves the tool_turn miss
byte-identical.

I can build this branch and run the repro with `MTPLX_SEMANTIC_ANCHORS=1` to confirm
whether it restores the base across the tool turn. Happy to share the full debug log or
a minimal `mtplx serve` repro.

Environment: MTPLX 2.10.0, M4 Max 128 GB, macOS 26.5,
`Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed`, `--context-window 131072 --ssd-session-cache on`.
