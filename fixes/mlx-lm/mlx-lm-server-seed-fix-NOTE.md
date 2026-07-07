# Local port: honor per-request `seed` in `mlx_lm.server` (for the degeneration rate run)

**This is a PORT of an existing upstream PR — do NOT refile.** Tracked as
ml-explore/mlx-lm issue [#1245](https://github.com/ml-explore/mlx-lm/issues/1245), fix PR
[#1331](https://github.com/ml-explore/mlx-lm/pull/1331) (open as of 2026-05-31).

## Why we needed it

`mlx_lm.server`'s sampler uses `@partial(mx.compile, inputs=mx.random.state, outputs=mx.random.state)`
for `categorical_sampling` / `apply_xtc`. In the server's generation thread the compiled function
captures RNG state and **ignores per-request `mx.random.seed()`**, so stochastic completions don't vary
by seed. We hit this hard: in our first degeneration sweep **all 50 multi-seed groups were
byte-identical**, which made a *stochastic* failure mode look deterministic and produced a wrong
"XTC fixes the loop" conclusion. Real loop *rates* require seeds that actually vary.

## What was changed (installed venv only; venv is gitignored)

Adapted #1331 to our installed `mlx-lm==0.31.3`:

- `mlx_lm/sample_utils.py`
  - `make_sampler(..., use_compiled_sampling: bool = True)`.
  - New uncompiled twins `apply_xtc_uncompiled` + `categorical_sampling_uncompiled` (no `mx.compile`).
  - When `use_compiled_sampling=False`, the sampler routes through the uncompiled twins so
    `mx.random.seed()` is honored.
- `mlx_lm/server.py`
  - `_make_sampler(...)`: pass `use_compiled_sampling=not (args.seed is not None and temperature > 0)`
    (keeps our `*tokenizer.encode("\n")` XTC ragged-list fix).
  - single-serve path: bypass `fetch_nearest_cache` / `insert_cache` for seeded stochastic requests
    (`_bypass_cache = args.seed is not None and temperature > 0`) so a prior sampled assistant
    continuation can't be replayed across seeds.

Verified: a 2-seed gate (same XTC combo, seeds 0 vs 1) now returns **different** text (`VARY`), where
before it was identical. The rate run (`bench/degeneration/scripts/run-degeneration-rates.sh`) depends on this.

> Note: our local `server.py` differs from #1331's base (e.g. it uses a local `generation_stream`,
> not the imported one), so #1331 does not apply as a raw patch here — this is a behavior-equivalent
> hand-port of the parts we needed. Drop it once #1331 (or equivalent) lands upstream.
