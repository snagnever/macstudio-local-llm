# Etapa C — contexto longo com reps (2026-09-15)

Objetivo: dar `T_turno` comparável a 256K e 512K. A Etapa A tinha 1 rep a 256K sem `append`; a sonda
de 512K não tinha `tool_turn`. A Etapa C não muda o veredito; fecha as duas bandas longas.

Perfil do vendor (`temperature=1.0`), uma sessão de servidor por run. `T_turno` = TTFT do `tool_turn`
+ 512 / mediana do decode dos cenários quentes servidos. Valores crus, 2 casas.

## Resultado

| cand @ ctx | `T_turno` | tool TTFT | decode quente | cold TTFT | hit app/tool | reps |
|---|---:|---:|---:|---:|---:|---|
| c1 @256K | **13.9 s** | 2.22 s | 43.8 tok/s | 379 s | 0.996 / 0.996 | 3 |
| c1 @512K | **13.6 s** | 3.08 s | 48.5 tok/s | 845 s | — / 0.998 | 2 |
| c3 @256K | 17.7 s | 5.80 s | 43.2 tok/s | 578 s | 0.993 / 0.993 | 3 |
| c2 @256K | 27.3 s | 6.66 s | 24.8 tok/s | 1186 s | 0.993 / 0.993 | 3 |
| c4 @256K | recusa | — | — | — | — | — (HTTP 507) |

## Leitura

1. **O c1 fica plano até 512K:** 11.0 → 12.35 → 13.9 → 13.6 s. O `T_turno` a 512K é igual ao de 256K
   porque o decode quente a 512K (48.5) ficou acima do de 256K (43.8) nessas runs; ambos ~14 s.
2. **O que separa c1 e c3 a 256K é o TTFT quente:** 2.22 s contra 5.80 s. O decode empata (~43 tok/s).
3. **A dev2 é 2× a 0.6.4 nos mesmos pesos a 256K:** cold 578 contra 1186 s, decode 43.2 contra 24.8.
4. **512K com `tool_turn` (novo):** o follow-up de ferramenta responde em 3.1 s com hit 1.00; a sonda
   antiga só tinha cold + identical.

Dados: `c1-262144-t1.0-c.jsonl`, `c3-262144-t1.0-c.jsonl`, `c2-262144-t1.0-c.jsonl`,
`c1-524288-t1.0-yarn2-c.jsonl`. Fora: c4 a 256K (507 já registrado); c2/c3/c4 a 512K (oMLX sem YaRN,
MTPLX recusa já a 128K).
