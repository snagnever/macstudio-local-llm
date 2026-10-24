# Etapa 8 — Swift 1.5 GGUF no Splash 1.4.0 × w1 (2026-10-23)

`k2` e `k2a` = `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS` `0142554` (os pesos do `w1` em GGUF, 97.7 GB) no Splash 1.4.0, com o draft DFlash2 que o Splash escolhe. `k2` usa `--verify-rows all`, e `k2a` usa `auto`. A referência é o `w1` (Swift 1.5 MLX "4.7" no mlx-serve 26.10.1). A velocidade do `w1` vem do Task 1, e a bateria do Task 6. 32K e 128K com 3 reps, e 256K só no `k2a`, com 1 rep.

## Velocidade

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| w1 | 32K | 8.0 s | 34.5 s | 1.80 s | 0.96/0.96 | 83.1 | 0.689 | 96.9 GB | -0.01 GB | 0 | 12/13 (1 trunc) |
| k2 | 32K | 6.3 s | 34.7 s | 1.50 s | 0.96/0.96 | 107.4 | — | 108.1 GB | 0.00 GB | 0 | 13/13 |
| k2a | 32K | 6.0 s | 34.7 s | 1.50 s | 0.96/0.96 | 112.7 | — | 108.0 GB | 0.00 GB | 0 | 13/13 |
| w1 | 128K | 8.7 s | 165.6 s | 2.00 s | 0.99/0.99 | 76.1 | 0.733 | 110.9 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| k2 | 128K | 6.4 s | 167.4 s | 1.60 s | 0.99/0.99 | 106.6 | — | 112.6 GB | 0.00 GB | 0 | 13/13 |
| k2a | 128K | 6.3 s | 167.4 s | 1.60 s | 0.99/0.99 | 108.2 | — | 112.6 GB | 0.00 GB | 0 | 13/13 |
| w1 | 256K | 9.9 s | 350.5 s | 2.10 s | 1.00/1.00 | 65.4 | 0.779 | 111.3 GB | 0.00 GB | 0 | 5/5 |
| k2a | 256K | 6.3 s | 351.1 s | 1.60 s | 1.00/1.00 | 110.1 | — | 110.9 GB | -0.03 GB | 0 | 5/5 |

- Todos os gates passam. O alerta wired > 102 GB aparece em todas as linhas do Splash.
- O draft aceita 3.6 a 3.8 tokens por ciclo a 128K (log do Splash).

| razão `T_turno(cand) / T_turno(w1)` | 32K | 128K | 256K |
|---|---:|---:|---:|
| k2 | 0.787 | 0.736 | — |
| k2a | 0.750 | 0.724 | 0.636 |

Com os mesmos pesos, o Splash fica mais rápido que no Task 5. O `k2a` faz 6.0 s contra 6.8 s do `k1a` a 32K. O IQ4_XS do Swift é 4 GB maior que o UD-IQ4_XS, mas o Swift gera menos tokens.

## Qualidade (`run-battery.sh`, perfil t1, xhigh, 131072)

| suíte | métrica | w1 | k2a |
|---|---|---:|---:|
| HumanEval | acertos | 141/164 | **142/164** |
| HumanEval | tempo total | 2105 s | 1046 s |
| LiveCodeBench | acertos | 46/50 | **47/50** |
| LiveCodeBench | tempo total | 3619 s | 2863 s |
| LiveCodeBench | reasoning mediano | 4435 chars | 5271 chars |

`summarize_ab.py`: G1 (qualidade) passa nas duas suítes. G2 (thinking) falha no LiveCodeBench, porque o `k2a` raciocina 19% mais em caracteres.

## Tool calls (`toolcall-probe.sh k2a`, 5 sessões × 4 turnos)

| `frequency_penalty` | turnos | sessões | mediana por turno |
|---:|---:|---:|---:|
| 0 | 16/17 | 4/5 | 0.80 s |
| 1 | 12/14 | 3/5 | 1.01 s |

O `tool_loop.py` encerra a sessão no primeiro turno errado, por isso o total de turnos é menor que 20. As três falhas são no turno 1:
- penalidade 0, sessão 2: o modelo responde sem tool call, apesar de `tool_choice: required`;
- penalidade 1, sessão 3: o mesmo defeito;
- penalidade 1, sessão 4: a tool call `read_fixture` chega com argumentos que não são JSON válido.

O `w1` faz 20/20 com as duas penalidades no mesmo probe. A causa não foi isolada. Ela pode estar no tratamento de `tool_choice: required` pelo Splash, no parser de tool calls ou no verify adaptativo. O `k2` (`--verify-rows all`) não passou pelo probe.

## Veredito

Não trocar o driver ainda. O `k2a` passa em velocidade (0.72–0.75 × o `w1`, e 0.64 a 256K sem swap) e em qualidade (HumanEval e LiveCodeBench iguais ou 1 ponto acima). Mas falha na regra de tool calls: 16/17 turnos e 4/5 sessões com penalidade 0, contra 20/20 do `w1`. Para um driver de agentes, essa falha pesa mais que o ganho de velocidade. O próximo passo é medir a taxa de falha com mais sessões, no `k2` e no `k2a`, e ver o conteúdo da resposta que veio sem tool call.

## Leitura

- É o resultado mais rápido da campanha. A 256K, o `T_turno` cai de 9.9 para 6.3 s, porque o decode do Splash não cai com o contexto (110 tok/s contra 65 do `w1`).
- O prefill a frio é igual ao do `w1` (34.7 contra 34.5 s a 32K, 351 contra 350 s a 256K).
- O verify adaptativo (`k2a`) ganha 2–5% sobre o `k2`.
- A memória fica em 108–113 GB wired, sem swap, até 256K.
