# STATS — Landing Page 5 Iterations (`vanilla`)

This report records the opencode session that produced the `vanilla` arm of the
layout-skill bench: the no-skill baseline the other three arms lacked. All
figures come from the opencode session database
(`~/.local/share/opencode/opencode.db`), read after the run, the same source and
method the other three reports use.

## Session

| Field | Value |
| --- | --- |
| Session id | `ses_f7c061a51ffeyHva3VEA9OGKh7` |
| Session title | "Second brain landing page 5 iterations" |
| Directory | `/Users/vitor/LocalProjects/qwen38-next-layout-bench/vanilla` |
| Started | 2026-09-08 23:23:07 -03:00 |
| Last token event | 2026-09-08 23:38:40 -03:00 |
| Wall time | 932.9 s (15.5 min), first message to last recorded token event |
| Harness | opencode, `build` agent |
| Model | `qwen/qwen3.8-flash` through **openrouter**, variant `high` |
| Cost | US$ 0.028931, as the session row records it |

A first attempt in the same directory, `ses_f7c06ef81ffeE0sXHY1yDmKlvu`
("Second Brain Landing Page Iterations", 23:22:13, 0.6 min, 5 bash calls,
330 output tokens), wrote no file and was abandoned. Its numbers are **not**
in the totals below; only the session that produced the pages is.

## This arm is not like-for-like with the other three

Two differences, both from the session record, neither of them a judgement:

1. **Different model and serving.** The other three arms ran
   `ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit` on the rig, through the
   local `rigfn` provider, at variant `xhigh`, and cost nothing. This arm ran
   `qwen/qwen3.8-flash` through openrouter at variant `high`, and billed. A
   different model build, a different thinking level, and a hosted path: wall
   time and token counts do not compare across that line.
2. **Different prompt.** The brief body matches the campaign brief except for
   one trailing space (319 characters against 318, same text). It is preceded
   by two lines that pin this arm as the baseline:

   > do not use any skills.
   > do not look at other files.

## Tokens

| Kind | Tokens |
| --- | --- |
| Output | 30,166 |
| Uncached input | 37,981 |
| Cache read | 472,064 |
| Reasoning | 3,197 |

## Process

| Metric | Value |
| --- | --- |
| Messages | 24 (3 user + 21 assistant) |
| User turns | 3: the brief, then "continue, algo ralhou", then "try again" |
| Tool calls | 24 parts: 8 write, 5 bash, 2 edit, 2 todowrite, 1 grep, 1 read, and 5 that aborted |
| Files written | 6: `index.html` (the switcher) and `1/`–`5/index.html` |
| Pages | 5 |

The two extra user turns are nudges after failures, not design direction: the
run needed to be restarted twice before it finished the five pages.

## Not collected

- Rendered quality, of any kind. This campaign scores nothing; the pages are
  the artifact and the eye is the judge.
- A second run of this arm on the local model, which is what a clean
  no-skill baseline for the other three would need.
