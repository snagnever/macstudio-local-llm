# Etapa A — triagem 1-shot a 32K, 128K e 256K (2026-09-13)

Os 4 candidatos, 1 rep, perfil do vendor (`temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning xhigh,
limite 4096 tokens). 32K e 128K com 5 cenários; 256K com `cold`, `identical` e `tool_turn`.
`T_turno` = TTFT do `tool_turn` + 512 / decode quente (mediana). Menor é melhor.

## Ranking por `T_turno`

| cand | runtime | 32K | 128K | 256K |
|---|---|---:|---:|---:|
| c1 ddalcu mixed-4/8 | mlx-serve 26.9.2 | 10.8 s | **11.3 s** | **14.2 s** |
| c3 oQ4e | oMLX 0.7.0.dev2 | 12.6 s | 15.2 s | 16.7 s |
| c4 MTPLX Opt-Speed | MTPLX 2.11.2 | **10.6 s** | recusa HTTP 507 | recusa HTTP 507 |
| c2 oQ4e | oMLX 0.6.4 | 17.1 s | 22.8 s | 28.7 s |

## Detalhe por banda

| cand @ ctx | cold TTFT | TTFT quente id / app / tool | hit id / app / tool | prefill | decode quente | correção | wired pico |
|---|---:|---|---|---:|---:|---|---:|
| c1 @32K | 37.3 s | 0.1 / 1.9 / 1.9 s | 1.00 / 0.96 / 0.96 | 733 | 57.5 | truncado (middle) | 90.5 GB |
| c2 @32K | 59.6 s | 2.0 / 4.2 / 4.3 s | 0.97 / 0.94 / 0.94 | 458 | 40.1 | ok | 91.3 GB |
| c3 @32K | 52.5 s | 1.9 / 3.9 / 4.0 s | 0.97 / 0.94 / 0.94 | 520 | 59.2 | ok | 90.8 GB |
| c4 @32K | 47.9 s | 0.1 / 3.7 / 3.3 s | 1.00 / 0.96 / 0.96 | 570 | 70.3 | ok | 100.9 GB |
| c1 @128K | 177.8 s | 0.2 / 2.2 / 2.2 s | 1.00 / 0.99 / 0.99 | 707 | 56.2 | ok | 106.4 GB ⚠ |
| c2 @128K | 277.9 s | 2.8 / 5.1 / 5.6 s | 0.99 / 0.99 / 0.99 | 452 | 29.8 | ok | 95.7 GB |
| c3 @128K | 259.2 s | 2.5 / 4.7 / 4.8 s | 0.99 / 0.99 / 0.99 | 485 | 49.1 | ok | 94.3 GB |
| c4 @128K | — | — | — | — | — | recusa 507 | — |
| c1 @256K | 378.6 s | 0.6 / — / 2.6 s | 1.00 / — / 1.00 | 678 | 44.2 | truncado (cold) | 108.5 GB ⚠ |
| c2 @256K | 1187.4 s | 3.3 / — / 7.0 s | 1.00 / — / 0.99 | 216 | 23.6 | ok | 101.0 GB |
| c3 @256K | 578.0 s | 3.3 / — / 5.9 s | 1.00 / — / 0.99 | 444 | 47.5 | ok | 100.1 GB |
| c4 @256K | — | — | — | — | — | recusa 507 | 88.7 GB |

⚠ alerta de wired acima de 102 GB (não elimina; swap delta 0 em todas as runs). Truncado = o reasoning
passou de 4096 tokens; não conta como falha.

## Gates (32K e 128K)

- c1, c2, c3: passam em hit (≥ 0.90 em append e tool_turn), correção, swap e erros HTTP.
- c4: passa a 32K; **reprova a 128K por recusa HTTP 507** (erro de servidor numa banda diária).

## Achados

1. **O c1 é o único que mantém o `T_turno` quase plano com o contexto:** 10.8 → 11.3 → 14.2 s. O c3 vai de
   12.6 a 16.7 s; o c2, de 17.1 a 28.7 s.
2. **O c4 tem o melhor `T_turno` a 32K, mas não serve 128K neste Mac com o default.** O MTPLX 2.11.2 calcula
   um fit de 114.688 tokens (engine budget 96 GiB − pesos 77.3 GiB − transientes) e recusa antes do swap.
   Mensagem do servidor: "--context-window 262144 exceeds this machine's memory-plan fit of 114688 tokens".
   O driver atual roda com 131072 tokens.
3. **A dev2 dobra a 0.6.4 no contexto longo, nos mesmos pesos:** a 256K, cold 578 s contra 1187 s e decode
   47.5 contra 23.6.
4. **O c1 faz multi-turno a 256K sem `sudo`:** follow-up servido com hit 1.00 (identical 0.6 s, tool_turn 2.6 s).
5. **O cache reusa bem a partir de 128K** em c1, c2 e c3 (hit ≥ 0.99). A 32K, o oMLX fica em 0.94.

## Consequências para a Etapa B

- c2 sai (dominado pelo c3 nos mesmos pesos).
- Finalistas de 128K: **c1 e c3**, salvo o teste isolado do c4 com `MTPLX_MEMORY_LIMIT_BYTES=102G`.
- O c4 a 128K no default será gravado de novo com o probe corrigido; a primeira run quebrou antes do
  registro de recusa e deixou o arquivo vazio.

Dados: `c{1,2,3,4}-{32768,262144}-t1.0.jsonl`, `c{1,2,3}-131072-t1.0.jsonl`.
