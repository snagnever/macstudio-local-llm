# 2026-09-07 — Layout skill bench: three design skills, one brief, one model

> **Status:** closed. Source vendored, three self-reports recovered from the
> opencode session database, `results/arms.json` populated and validated. This
> feeds the comparison site's dashboard.

**This is a controlled comparison: three different skills, on one identical
brief.** It is not "one skill vs. a no-skill baseline" and it is not "one skill
configuration run twice." All three sessions ran the same local model
(Qwen3.8 Flash Next, MLX) against the byte-identical verbatim brief quoted
below; each loaded a different design skill:

| Arm | Skill that fired | Source |
| --- | --- | --- |
| `design-skill` | `frontend-design` | user's global skill directory (`~/.agents/skills/frontend-design`) |
| `taste-skill` | `design-taste-frontend` | `Leonxlnx/taste-skill` package, vendored under `.agents/skills/` |
| `taste2` | `high-end-visual-design` | `Leonxlnx/taste-skill` package, vendored under `.agents/skills/` |

`taste-skill` and `taste2` share a byte-identical `skills-lock.json` (both
pin `brandkit`, `design-taste-frontend`, `high-end-visual-design` from
`Leonxlnx/taste-skill`), and it would be easy to read that lock file alone and
conclude the two arms ran the same configuration twice. **They did not.** A
lock file records what skills were *available* to a session, not which one
was *invoked*. Reading each session's actual transcript in the opencode
database shows the first user message in each case is one complete skill
document, ending with a "Base directory for this skill:" line naming exactly
one of the three pinned skills — `design-taste-frontend` for `taste-skill`,
`high-end-visual-design` for `taste2`. `brandkit` does not appear in either
session's text at all. `design-skill` has no lock file whatsoever (it isn't
part of the `Leonxlnx/taste-skill` package), and its own transcript shows it
loaded `frontend-design` from the user's global skill directory — so it is
not a no-skill baseline either. Full supporting detail (message lengths,
on-disk SKILL.md byte counts, the lock-file diff) is in
`results/taste2.md`'s "Honesty check" section, which is the canonical account
that `results/design-skill.md` and `results/taste-skill.md` point back to.

## The verbatim brief

All three arms received this exact text (SHA `eaebe847...`, 318 characters),
confirmed byte-identical against the opencode session database:

> I want you to design the landing page for a note-taking application as
> essentially a second brain. You should design five iterations and each of
> them should be accessible within the slash one, slash two, slash three like
> pages directory. And then you should add a little button that lets me
> switch between them easily.

`design-skill` received the skill document and this brief concatenated into
one message. `taste-skill` and `taste2` each received the skill document as
its own message, with the brief following as a separate user turn. The words
of the brief itself do not differ.

## The three shipped forms

| Arm | Form |
| --- | --- |
| `design-skill` | Five static HTML directories, no build step, no framework — `index.html` (switcher) plus `1/`…`5/`, each with its own `index.html` |
| `taste-skill` | A Vite + React + TypeScript app (react 19, motion, tailwind v4, vite 7) with five client-side routes `/1`…`/5` and a fixed-position switcher nav |
| `taste2` | Five static HTML pages (`pages/1.html`…`pages/5.html`) served by a small plain `node:http` server (`server.js`, no framework); `/` redirects to `/1` |

All three ship exactly 5 design iterations, matching the brief's ask.

## Where source and metrics live

- **Source:** `demos/<arm>/` — each arm's project vendored as-is (source
  only: `node_modules`, `dist`, `.git`, `.DS_Store`, `tsconfig.tsbuildinfo`,
  and `server.log` excluded). `taste-skill/` and `taste2/` keep their
  `skills-lock.json` and vendored `.agents/skills/` — these are the record of
  which skills were *available*, not proof of which one ran (see above).
  `design-skill/` has neither, matching its own report. Do not edit vendored
  source to fix anything found later; file a note instead.
- **Self-reports:** `results/<arm>.md` — recovered from the opencode session
  database (`~/.local/share/opencode/opencode.db`) via
  `scripts/recover_opencode_stats.py`, since none of the three runs shipped
  with its own stats file. `results/taste2.md` carries the full "Honesty
  check" for all three arms; the other two reports point back to it rather
  than repeating it.
- **Numbers:** `results/arms.json` — the single source of every figure the
  dashboard renders, in the two-array model (`arms` roster + tidy `results`
  list; see `reports/README.md`). Metrics: `wallMinutes`, `tokensOutput`,
  `tokensInputUncached`, `tokensCacheRead`, `toolCalls`, `messages`,
  `pageCount` (5 for every arm). Roster string fields: `skillConfig` (the
  skill that actually fired), `brief` (verbatim, carried per-arm since it is
  identical), and `form`. Every `(arm, metric)` pair appears exactly once —
  mechanically checked (see Validation below). No metric here was
  uncollected, so `arms.json` has zero nulls.

## Publish-time fixes

*(Filled in by Task 9 — the workflow that builds and publishes each vendored
demo. Left as a placeholder here so this plan stays the reference for what the
publish step is expected to do to each arm before the dashboard links to it.)*

- TBD: build command for `taste-skill/` (`npm ci` then `npm run build`,
  expected) versus the two static arms (`design-skill/`, `taste2/`), which
  need no build step — `taste2/` needs its small `server.js` run instead of
  a static file server, or its pages served directly by path.
- TBD: any per-arm adjustment needed purely to get each form serving under
  the site's routing, without touching design content.

## Limits, stated plainly

- **Wall time and token cost are not proxies for design quality.** They
  reflect how much the loaded skill asked the model to do (`taste-skill`'s
  87KB skill document versus `taste2`'s 10KB one, versus `design-skill`'s
  skill+brief combined into a single message) more than any inherent
  difference between the three skills' output quality.
- **Only `design-skill` combined the skill and the brief into one message;**
  the other two arms received them as two separate user turns. This is a
  difference in how the session was set up, not in the words of the brief.
- **`taste2` is the only session with a mid-run auto-compaction event** and
  an extra "continue" nudge message — its `messages` count (19) includes both
  of those alongside the two substantive turns the other two arms also have.
- **All three ran on the same local model at zero API cost** (Qwen3.8 Flash
  Next, MLX, local rig) — this bench does not compare cost or hosted-model
  behavior at all, only skill choice on identical local conditions.

## Validation

`results/arms.json` is checked mechanically: every `(arm, metric)` pair has
exactly one record, no result names an arm outside the roster, and any gap
(a pair with no record at all) is listed rather than silently missing. As of
this campaign's construction: 3 arms × 7 metrics = 21 records, 0 nulls,
0 gaps.
