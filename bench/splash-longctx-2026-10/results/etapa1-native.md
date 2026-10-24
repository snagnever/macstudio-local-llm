# Etapa 1 — bandas nativas, 8K a 256K (2026-10-24)

Os braços:

- `k1a`: Flash Next base GGUF UD-IQ4_XS no Splash 1.4.0 com `--verify-rows auto`.
- `k2a`: Swift 1.5 GGUF IQ4_XS no Splash 1.4.0 com `--verify-rows auto`.
- `w1z`: o driver diário, Swift 1.5 MLX 4.7bpw no mlx-serve 26.10.3.

Esta etapa mediu o 8K dos três braços e o 256K do `k1a` e do `k2a`, sempre com 3 reps (tag `lc`). O 32K e o 128K vêm do stack-updates (tags `e1`, `e5`, `e8`, 3 reps), assim como o 256K do `w1z` (`e1`, 1 rep). O `k3a` não rodou, porque o Splash 1.4.0 recusa o GGUF ([etapa0-k3-load](etapa0-k3-load.md)).

## Velocidade e cache

| braço | contexto | T_turno | cold TTFT | warm TTFT id/app/tool | hit id/app/tool | decode | wired peak | folga | swap Δ | needles |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|
| w1z | 8K | 7.7 s | 3.3 s | 0.2/1.6/1.6 s | 0.99/0.72/0.71 | 83.7 | 90.2 GB | 27.4 GB | 0 | 11/13 (1 trunc) |
| k1a | 8K | 7.2 s | 3.5 s | 0.1/1.4/1.5 s | 1.00/0.72/0.71 | 89.4 | 108.7 GB | 16.4 GB | 0 | 10/13 (3 trunc) |
| k2a | 8K | 6.2 s | 3.3 s | 0.1/1.4/1.4 s | 1.00/0.72/0.71 | 107.2 | 106.6 GB | 18.6 GB | 0 | 11/13 (1 trunc) |
| w1z | 32K | 8.0 s | 34.6 s | 0.2/1.7/1.8 s | 1.00/0.96/0.96 | 81.8 | 100.0 GB | — | 0 | 13/13 |
| k1a | 32K | 6.8 s | 36.8 s | 0.0/1.5/1.6 s | 1.00/0.96/0.96 | 98.1 | 110.3 GB | — | 0 | 13/13 |
| k2a | 32K | 6.0 s | 34.7 s | 0.0/1.5/1.5 s | 1.00/0.96/0.96 | 112.7 | 108.0 GB | — | 0 | 13/13 |
| w1z | 128K | 8.9 s | 165.7 s | 0.4/2.0/1.9 s | 1.00/0.99/0.99 | 74.0 | 107.5 GB | — | 0 | 13/13 |
| k1a | 128K | 6.8 s | 176.9 s | 0.1/1.6/1.7 s | 1.00/0.99/0.99 | 99.1 | 114.9 GB | — | 0 | 13/13 |
| k2a | 128K | 6.3 s | 167.4 s | 0.1/1.5/1.6 s | 1.00/0.99/0.99 | 108.2 | 112.6 GB | — | 0 | 13/13 |
| w1z | 256K | 9.2 s | 350.7 s | 1.2/2.3/2.3 s | 1.00/1.00/1.00 | 74.1 | 113.2 GB | 5.5 GB | 0 | 5/5 (1 rep) |
| k1a | 256K | 7.0 s | 370.6 s | 0.1/1.7/1.8 s | 1.00/1.00/1.00 | 99.1 | 116.4 GB | 9.8 GB | 0 | 11/13 |
| k2a | 256K | 6.6 s | 351.1 s | 0.1/1.6/1.7 s | 1.00/1.00/1.00 | 105.8 | 116.4 GB | 10.1 GB | 0 | 12/13 |

- **Folga** = 128 GB − wired peak − compressor peak, a partir do `*-mem.jsonl`. O stack-updates não guardou os `*-mem.jsonl` do 32K e do 128K neste formato, por isso essas linhas ficam sem valor.
- O `w1z` comprime ~8.5 GB de memória durante o load, e o Splash não comprime nada. Por isso o `w1z` tem menos wired e mais compressor.
- O hit append/tool de 0.72 a 8K vem do sufixo do probe. Os três braços mostram o mesmo valor, porque o sufixo pesa mais num prefixo curto.
- Todos os gates passam: swap Δ ≤ 0.5 GB, hit ≥ 0.90 nas bandas de gate e 0 erros HTTP. O alerta wired > 102 GB aparece em todas as linhas do Splash e no `w1z` a partir de 128K.

## Decisão (`decide.py --mode le --threshold 0.97`, base `w1z`)

| razão `T_turno / T_turno(w1z)` | 8K | 32K | 128K | 256K | veredito |
|---|---:|---:|---:|---:|---|
| k1a | 0.935 | 0.85 | 0.76 | 0.761 | pass |
| k2a | 0.805 | 0.75 | 0.71 | 0.717 | pass |

O `decide.py` rodou nas bandas de 8K e 256K. As razões de 32K e 128K saem das linhas da tabela acima.

## Needles

- **8K, todos os braços.** As falhas a 8K aparecem também no `w1z`: o raciocínio esgota as 4096 tokens (`length`), ou o modelo pede uma tool call em vez de responder. São um efeito do probe a 8K, não do motor.
- **256K, Splash.** Três respostas erradas em 26 turnos. O `k1a` devolveu um texto vazio num cold turn (693 tokens de raciocínio, `stop`). O `k1a` (`tool_turn`) e o `k2a` (`append`) repetiram a needle de 10% nas posições de 50% e 90%. O `w1z` a 256K tem só 1 rep (5/5), então a comparação de needles a 256K ainda é fraca. A Etapa 4 mede a qualidade em contexto longo com o `longctx_probe`.

## Conclusão

O `k2a` é o braço mais rápido em todas as bandas: 0.72 × o `w1z` a 256K. O ganho vem do decode (106 contra 74 tok/s a 256K). O cold TTFT e o hit ficam iguais aos do `w1z`. O `k1a` fica entre os dois. Os dois braços Splash passam no gate de 0.97 em todas as bandas e seguem para a Etapa 2 (512K).
