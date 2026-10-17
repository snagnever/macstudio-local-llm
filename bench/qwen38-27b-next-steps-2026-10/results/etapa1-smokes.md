# Etapa 1: 8K smokes (2026-10-13, effort medium, 9293a42)

All five arms passed with rc=0 and no HTTP errors. Criteria: reasoning_chars > 0 on every record; cached_tokens reported on k27 and l27; [spec-stats] present on the mlx-serve arms.

| Arm | Median decode tok/s | Min reasoning_chars | cached_tokens identical / append / tool_turn | hit append / tool_turn |
|---|---|---|---|---|
| k27 | 86.5 | 847 | 2688 / 2688 / 2688 | 0.72 / 0.71 |
| l27 | 35.3 | 983 | 2690 / 2690 / 2690 | 0.72 / 0.71 |
| o27q4 | 81.4 | 825 | 2689 / 2689 / 2689 | 0.72 / 0.71 |
| r27d | 83.6 | 1724 | 2663 / 2663 / 2663 | 0.71 / 0.71 |
| r27m | 51.5 | 1543 | 2663 / 2663 / 2663 | 0.71 / 0.71 |

Hit on append and tool_turn is about 0.71 at 8K because the new turn is about 1K tokens of a 3.7K prompt. The 0.90 gate applies at 32K and 128K.

[spec-stats] modes: r27d mode=dflash (drafter only, --no-mtp); r27m mode=mtp depth=3 (MTP head only). This confirms that the two P3 arms run different speculation paths.

The first smoke run waited 7 min in idle-gate because the gate counted only Pages free (2.6 GB, with 86 GB of speculative file cache). Commit 9293a42 fixes the gate.
