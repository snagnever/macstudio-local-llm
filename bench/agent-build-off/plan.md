# 2026-09-07 — Agent build-off: four stacks, one brief, one 3D game

> **Status:** closed. Source vendored, three self-reported STATS files copied, one
> log-verified (`codex-astra`), `results/arms.json` populated and validated. This
> feeds the comparison site (Task 7's dashboard).
>
> **Later addition (2026-09-08):** a fifth arm, `claude-qwen38` — Claude Code
> driving the same local Qwen3.8 Flash Next — was processed into the campaign
> from a session run on 2026-09-07 after the other four. This plan describes the
> original four; `results/arms.json` and both reports carry all five.

## What this campaign compares

Four coding-agent stacks each built the same 3D game — a runner — from an empty
folder, in one session, from the same verbatim brief, on 2026-09-07 (2026-09-06
evening BRT for `codex-astra`). Nothing here compares model *quality* on a
shared benchmark; it compares what each stack actually produced and cost to get
there — tokens, wall time, code size, defects, build output — under the same
starting prompt.

## The arms

| Arm | Source folder | Harness | Model |
| --- | --- | --- | --- |
| `opencode-qwen38` | `~/LocalProjects/hyper-runner` | opencode | `qwen3.8-flash-next` (MLX, local) |
| `opencode-qwen38-superpowers` | `~/LocalProjects/hyper-runner-superpowers` | opencode | same, plus superpowers skills |
| `claude-opus5` | `~/LocalProjects/hyper-runner-claude` | claude | `claude-opus-5` |
| `codex-astra` | `~/LocalProjects/hyper-runner-astra` | codex | `gpt-6-astra` (+ `gpt-5.6-sol`, `codex-auto-review`) |

`~/LocalProjects/hyper-runner-fable` is empty. That arm never ran; it is omitted
rather than shown as a blank column anywhere in this campaign.

`codex-astra` is not a single-model, single-agent run like the other three: its
~18.6M reported tokens span three models across five delegated agents running
partly in parallel. This makes its token total **not comparable** to the other
arms' totals — see `multiModelNote` on its roster entry in `arms.json`, and the
log-verification section of `results/codex-astra.md`.

## The verbatim brief

All four arms received the same first prompt, word for word, including the
"poiting" typo:

> You are going to create a complete and impressive 3D demo runner game, using
> modules and libraries to reduce the need of new code. You should search the
> web for most updated information, stack and best practices. Select the stack
> based on easiness to implement a functional demo on reduced time. Question me
> for decisions and ambiguities while creating the plan.
>
> - SAVE a detailed SPEC AND PLAN to SPEC.md and PLAN.md on the folder before
>   building
> - Create an AGENTS.md explaining the repo objective, poiting to both PLAN and
>   SPEC files

`hyper-runner-claude/STATS.md` and `hyper-runner-superpowers/STATS.md` both
quote this verbatim under "The first prompt, verbatim". `hyper-runner/STATS.md`
confirms the same template drove its sibling session. `codex-astra`'s STATS.md
does not quote its own first prompt; it was instead recovered word-for-word
from the Codex rollout log (see `results/codex-astra.md`) and matches exactly,
typo included — so the brief is confirmed like-for-like across all four arms
even though only three of the four state that fact themselves.

## Where source and metrics live

- **Source:** `demos/<arm>/` — each arm's repository vendored as-is (source
  only: `node_modules`, `dist`, and `.git` excluded so the site can build it
  fresh with `npm ci`). Do not edit vendored source to fix anything found later;
  file a note instead.
- **Self-reports:** `results/<arm>.md` — the STATS file each agent wrote about
  its own session, copied verbatim. `codex-astra.md` additionally carries a
  section verifying its self-reported token totals against the raw Codex
  session logs (added when it was adopted into this campaign, appended below
  its own report rather than edited into it).
- **Numbers:** `results/arms.json` — the single source of every figure the
  dashboard renders, in the two-array model (`arms` roster + tidy `results`
  list; see `reports/README.md`). A metric a given arm did not record is
  `value: null` with a `note` explaining why — never zero, never a computed
  substitute. Every `(arm, metric)` pair appears exactly once; this is
  mechanically checked (see Validation below).

## Publish-time fixes

Every fix below exists because the model-written source assumes it is served
from a domain root; the site actually serves from `/macstudio-local-llm/`.
**The tracked source under `demos/` keeps exactly what the model wrote** —
none of these fixes touch it. They are applied to the copy the publish
workflow builds, by `tools/publish/fix-layout-arms.sh` and (for `taste-skill`,
see the sibling `layout-skill-bench` campaign, not this one) a patch file.

| Arm | Problem | Fix |
| --- | --- | --- |
| `opencode-qwen38` | no `base` in `vite.config.ts`; emits `/assets/…` | `vite build --base=…` |
| `opencode-qwen38-superpowers` | same | same |
| `claude-opus5` | none — `base: './'` already set | build unchanged |
| `codex-astra` | none — `base: './'` already set | build unchanged |

Only the two `opencode-qwen38*` arms need a build-time flag
(`vite build --base=/macstudio-local-llm/demos/build-off/<arm>/`); the other
two already build with a relative base and need no adjustment at all. None of
these four arms need `tools/publish/fix-layout-arms.sh` — that script covers
the `layout-skill-bench` arms' post-build link rewrites, which this campaign
doesn't have.

## Limits, stated plainly

- **Cost is not comparable.** The two local `opencode` arms ran on this
  machine's own MLX-served model — effectively free in currency, but far
  slower in wall time (`opencode-qwen38-superpowers` took 11h22m raw clock,
  including a 9h13m mid-task sleep, versus `claude-opus5`'s 41.9 minutes
  end to end). The hosted arms (`claude-opus5`, `codex-astra`) cost real
  API/subscription spend that isn't captured here at all.
- **One arm had a skill library the others lacked.** `opencode-qwen38-superpowers`
  ran with the superpowers skill set (brainstorming, writing-plans,
  executing-plans, worktrees, TDD, systematic-debugging, finishing) available;
  the other three arms did not have any comparable library.
- **Only `codex-astra` has a measured frame rate.** Its
  `docs/performance.json` records a 125.076 s sample at a mean 60.00 fps on
  an Apple M5 Pro. The other three arms all record frame-rate-under-load as
  "not collected" — a gap in their own verification, not a strength unique to
  `codex-astra`'s build quality.
- **`codex-astra` is multi-model, multi-agent.** Its token total spans three
  models across five delegated agents and is not comparable to the other three
  arms' single-model, single-agent totals (see above).
- **`statsSessionIncluded` differs per arm** and qualifies every token figure:
  `opencode-qwen38` excludes the session that wrote its own stats file,
  `opencode-qwen38-superpowers` includes it, `claude-opus5` does not state
  either way (`null`), and `codex-astra` states that it excludes it (though a
  log-verification pass found the excluded-session explanation doesn't fully
  reconcile the size of the gap — see `results/codex-astra.md`).
- **Accounting conventions differ across arms** for at least two metrics:
  wall-clock basis (`opencode-qwen38` measures first-files-written to
  final-source-edit; `codex-astra` measures first-to-last token-usage record;
  `claude-opus5`/`opencode-qwen38-superpowers` both measure first-prompt to
  final-report) and source-line counting (`codex-astra` reports test lines
  separately from source lines; other arms may fold test files into their
  source totals). Each affected metric in `arms.json` carries a note.

## Validation

`results/arms.json` is checked mechanically: every `(arm, metric)` pair has
exactly one record, no result names an arm outside the roster, and any gap
(a pair with no record at all) is listed rather than silently missing. As of
this campaign's construction: 4 arms × 20 metrics = 80 records, 14 nulls
(each with a note), zero gaps.
