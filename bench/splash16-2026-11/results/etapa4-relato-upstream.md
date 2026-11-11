# Rascunho: relato upstream (não publicado)

> Rascunho da Task 4. Nada foi postado. Só publicar se o usuário pedir.

**Title:** 1.6.0: two concurrent 256K sessions wait up to 30 s on memory claims (TTFT +65% vs 1.5.0)

**Setup:** Mac Studio M4 Max, 128 GB. `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS`, `--max-context 262144`, default memory flags. Two sessions with ~256K tokens of history each, sending turns at the same time, plus a small auxiliary load.

**Observed:**

| | 1.5.0 (same day) | 1.6.0 |
|---|---|---|
| turn time, stream 1 / 2 | 14.2 / 14.8 s | 17.4 / 24.4 s |
| warm tool-turn TTFT, stream 2 | 4.3 s | 2.2, 25.0, 13.8 s (3 reps) |
| aggregate decode | 89.8 tok/s | 86.5 tok/s |
| `pending` memory-claim log lines | 0 | 5641 |

- `/status` `metrics.ttft_parts_ms.claim_wait`: max 30.1 s, total 190.3 s over 164 requests.
- The same pattern shows with two 128K sessions: claim_wait max 30.3 s, total 61.4 s.
- One stream, or two 32K streams, show no claim wait.
- `decode_gap_causes.claim_wait` stays at 0. The wait hits TTFT, not decode.
- `memory_governor.system_pressure` stays `normal`, and no swap grows.

**Expected:** with the same memory as 1.5.0, two long sessions should not wait 30 s for a claim, or the wait should not repeat in each turn.

**Question:** is the ~30 s maximum a fixed claim timeout? Is there a flag to size the KV or hot-KV floor so two 256K sessions do not wait?
