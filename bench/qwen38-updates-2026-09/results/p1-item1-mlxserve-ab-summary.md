# P1 item 1 — mlx-serve 26.9.1 vs 26.9.2 (Flash-Next ddalcu mixed-4/8, 32K)

Veredito: **PROMOVER 26.9.2**. Decode +7,0% medio, todos os cenarios positivos, sem
regressao de cache/TTFT/correcao. M4 Max sem NAX. A/B limpo (disk cache limpo por braco,
memoria assentada entre bracos). Rodada 1 descartada por cache de disco compartilhado
(preservada em *-run1-diskcache-confound.jsonl).

| cenario | decode 26.9.1 | decode 26.9.2 | delta | cache | correcao |
|---|---:|---:|---|---|---|
| cold            | 62.3 | 68.8 | +10.4% | 0.00 | ok |
| identical       | 63.7 | 68.7 | +7.8%  | 1.00 | ok |
| append          | 62.0 | 65.7 | +6.0%  | 0.96 | ok |
| middle_mutation | 62.3 | 66.4 | +6.6%  | 0.30 | ok |
| tool_turn       | 63.5 | 66.1 | +4.0%  | 0.96 | ok |

decode medio: 62.76 -> 67.13 (+7.0%). TTFT igual entre versoes (cold 39.3 -> 37.3 s).
Dados: p1-mlxserve-v26.9.{1,2}-32768.jsonl.

## Confirmacao @128K (131072)

| cenario | decode 26.9.1 | decode 26.9.2 | delta |
|---|---:|---:|---|
| cold            | 44.3 | 61.9 | +39.8% |
| identical       | 44.9 | 63.1 | +40.7% |
| append          | 44.0 | 54.8 | +24.7% |
| middle_mutation | 42.1 | 54.2 | +28.8% |
| tool_turn       | 46.2 | 55.1 | +19.2% |

Ganho cresce com contexto: 26.9.1 cai para ~44 tok/s a 128K; 26.9.2 segura ~55-63.
Ambos cold sao frios reais (TTFT ~180-195 s). Sem falhas. 262K adiado.
Dados: p1-mlxserve-v26.9.{1,2}-131072.jsonl.

## 262K (262144) — mlx-serve 26.9.2 (leve: cold/identical/tool_turn x1)

| cenario | decode | prefill | TTFT | cache | nota |
|---|---:|---:|---:|---:|---|
| cold      | 58.8 | 676 | 379.6 s | 0.00 | correto |
| identical | 55.4 |   — |   1.0 s | 1.00 | correto (reusa) |
| tool_turn | 56.2 | 409 |   2.6 s | 1.00 | needle FALHA = truncou em max_tokens 4096 (11.6k chars de reasoning), nao erro |

**Cabe e nao colapsa a 262K:** decode ~56-59 tok/s, quase igual a 128K (58). Contra oMLX 0.6.4
@262K (27 tok/s, prefill 217, cold 1185 s): **~2.1x decode, ~3.1x prefill, ~3x cold**. O v26.8.11
caia a 17.6 tok/s. Decode praticamente plano 32K->262K (67->58->56). Cache reusa a 262K (identical/
tool_turn 1.00). O 26.9.2 e o caminho recomendado para Flash-Next em todo o range de contexto.
