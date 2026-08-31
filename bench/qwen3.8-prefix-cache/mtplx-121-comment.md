# Comment draft for youssofal/MTPLX #121

> Paste-ready follow-up comment for issue #121 (tool_call_history_rewrite). Not an
> issue, a data point that the class of problem still costs a full re-prefill for
> tool turns at long context on 2.10.0. Phrased as a question, not a demand.

---

Still seeing the `tool_call_history_rewrite` class cost a full re-prefill for tool
turns at long context on 2.10.0, with no block-overlap salvage. Reporting in case
it's a known residual or a regression against the 2.4.x fix.

**Setup.** MTPLX 2.10.0, M4 Max 128 GB, macOS 26.5, `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed`,
`--profile turbo --generation-mode mtp --context-window 131072 --ssd-session-cache on`.
Same ~125k-token base prefix. Measure `cached_tokens / prompt_tokens`.

**Result** (5 request shapes over the base, 3 reps each):

| shape | cached/prompt |
|---|---|
| identical | 1.00 |
| append (base + ~1k plain suffix) | 0.99 |
| tool_turn (base + tool-result turn, ~1k suffix) | 0.00 |

`append` and `tool_turn` share the same base and the same ~1k suffix length. `append`
reuses 99% via `block_prefix_boundary_clone`. `tool_turn` goes fully cold. The
postcommit receipt on the tool turn:

```
store-on-prefill: len=126688 cached=0 restore=cold
session_commit: committed=false,
  reason=retokenized_prefix_older_than_session,
  unsafe_reason=stop_token_boundary_mismatch
```

The tool turn's re-serialized markup shifts the token boundary, so the base isn't
reused at all, not even the block-overlap salvage that #121 closed on. At 128K this
is a ~870s full re-prefill per tool turn.

**What I checked, so this isn't a config gap.**
- `--ssd-session-cache on` (the default). `append` needs it. Without it, `append` also
  drops to 0.00.
- `MTPLX_POSTCOMMIT_WAIT_TIMEOUT_S=30`, the value the managed app sets. No change. The
  full 5×3 run is byte-identical with and without it. So it isn't the async postcommit
  preemption alone. The tool suffix boundary is the blocker.
- Not a bank-capacity issue. Shrinking the RAM bank to 12G did not change it, and a
  short `cold` then `tool_turn` sequence does hit 0.99. The miss needs the append and
  middle churn before the tool turn.

**Question.** Is block-overlap salvage expected to apply to a tool-turn suffix at long
context, or is a full re-prefill per tool turn the accepted behavior here? For agent
clients that call a tool every turn at 100k+ context, this dominates latency. A block
or content-addressed cache reuses the shared base and recomputes only the tail. Happy
to share the full debug log or a minimal `mtplx serve` repro.
