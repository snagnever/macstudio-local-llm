# Reddit post — draft

Draft for the user to post. Every number appears on the page. Update this draft when the page changes; no test checks it.

**Title:** I ran the same 7 coding tasks through Claude Code, OpenCode, pi and dsh on one local model (Qwen3.8 Flash-Next, M4 Max). The harness made no measurable difference, and my benchmark was wrong three times.

**Body:**

Setup: one Mac Studio M4 Max 128 GB, one model (Qwen3.8 Flash-Next, Swift 1.5 IQ4_XS GGUF, 128K context), 4 harnesses, 7 small coding tasks, 2 weight packs (standard, and an uncensored Heretic v2 pack at the same quantization level), 2 repetitions. That is 112 sessions. Each session runs in a sandbox on a fresh repository copy, and a hidden script decides whether the task is done.

What I found:

- **105 of 112 sessions done.**
- **Harness: no measurable difference in tasks done.** pi 27 of 28, Claude Code 27 of 28, dsh 26 of 28, OpenCode 25 of 28. With two repetitions I cannot rank them. dsh was the slowest on 5 of 7 tasks and pi the fastest on 5 of 7.
- **Uncensored pack, coding: 51 against 54 tasks done.** The net gap of 3 equals 3 misses on one task in one repetition. I measured no slowdown in session time.
- **Uncensored pack, refusals: 96% to 0% on AdvBench** (100 prompts). The page shows counts only.
- **Speed cost: 2% to 5% slower per agent turn.**
- **All 7 failed sessions reported success.** Exit code 0, no timeout. In these runs no failing session crashed or gave up; each one said the work was finished.

The part I did not expect: in the first run my own benchmark was wrong on 36 of 112 records (16 wrong verdicts, 20 wrong cheat flags).

1. The sandbox hid the parent `.git`, the linter failed with a permission error, and the environment task scored 0 of 16. After the fix: 6 of 16, and 13 of 16 once defect 3 was fixed too.
2. A cheat detector flagged 20 sessions because a new test changes an import line.
3. The check enforced a rule the prompt never stated (do not touch the Makefile). That one line flipped the verdict on the uncensored pack: 47 against 51 fails my rule, 51 against 54 passes.

Two of the three defects turned good sessions into failures; the third marked honest sessions as cheating. All three looked like model behaviour in the table. I only found them by opening the repositories of the sessions.

Limits: two repetitions, one model family, small tasks (under 6 minutes each), OpenCode was on an older build (1.15.10), and the two packs differ in quantization recipe as well as in the uncensoring.

Charts, the failure list, method and all 112 records: https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-harness-delivery.html
