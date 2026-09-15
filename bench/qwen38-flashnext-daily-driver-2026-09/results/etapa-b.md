# Etapa B — veredito com 3 repetições (2026-09-13)

Finalistas c1 e c3, 3 reps a 32K e a 128K (`middle_mutation` com 1 rep), perfil do vendor
(`temperature=1.0`), uma sessão de servidor por run. `T_turno` = TTFT do `tool_turn` + 512 / mediana do
decode dos cenários quentes servidos (identical, append, tool_turn), calculado com valores crus.

## Resultado

| cand | runtime | `T_turno` 32K | `T_turno` 128K | corretos |
|---|---|---:|---:|---|
| **c1 ddalcu mixed-4/8** | mlx-serve 26.9.2 | **11.03 s** | **12.35 s** | 25/26 (1 truncado) |
| c3 oQ4e | oMLX 0.7.0.dev2 | 13.48 s | 15.03 s | 24/26 (2 truncados) |

**O c1 vence nas duas bandas por 18%:** 2.45 s a 32K e 2.68 s a 128K. A diferença fica bem acima do ruído
de decode entre reps.

## Detalhe (mediana das 3 reps; faixa entre reps quando varia)

| cand @ ctx | cold TTFT | TTFT quente id / app / tool | hit id / app / tool | decode quente (faixa) | wired pico | swap |
|---|---:|---|---|---|---:|---:|
| c1 @32K | 37.0 s | 0.1 / 1.9 / 1.9 s | 1.00 / 0.96 / 0.96 | 55.9 (52.1–63.1) | 97.3 GB | 0 |
| c3 @32K | 52.3 s | 1.9 / 3.8 / 3.9 s | 0.98 / 0.94 / 0.94 | 53.5 (48.2–54.5) | 91.5 GB | 0 |
| c1 @128K | 178.1 s | 0.2 / 2.0 / 2.1 s | 1.00 / 0.99 / 0.99 | 49.7 (45.7–54.6) | 108.1 GB ⚠ | 0 |
| c3 @128K | 259.4 s | 2.6 / 4.7 / 4.8 s | 1.00 / 0.99 / 0.99 | 49.9 (46.2–51.2) | 98.6 GB | 0 |

⚠ alerta de wired acima de 102 GB (não elimina). Truncado = reasoning acima de 4096 tokens.

## Leitura

1. **O que separa c1 e c3 é o TTFT, não o decode.** A 128K os dois decodificam ~50 tok/s. O c1 responde o
   turno quente em 2.1 s contra 4.8 s, e o primeiro turno em 178 s contra 259 s.
2. **TTFT e cache hit são determinísticos entre reps** (variação ≤ 0.5%). O decode varia até ±12%.
3. **A rep única da Etapa A subestimou o `T_turno` do c1 a 128K** (11.3 → 12.35 s): o decode quente mediano
   caiu de 56.2 para 49.7 com 3 reps. O ranking não mudou.
4. **Sem miss intermitente de cache:** o hit ficou idêntico nas 3 reps em todos os cenários.

## Candidatos fora da Etapa B

- c4 (MTPLX 2.11.2): recusa 128K no default (HTTP 507); com budget de 102 G falha em 2/5 cenários.
- c2 (oMLX 0.6.4): dominado pelo c3 nos mesmos pesos.

Dados: `c1-32768-t1.0-b.jsonl`, `c3-32768-t1.0-b.jsonl`, `c1-131072-t1.0-b.jsonl`, `c3-131072-t1.0-b.jsonl`.
