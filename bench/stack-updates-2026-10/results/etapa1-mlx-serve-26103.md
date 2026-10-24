# Etapa 1 — mlx-serve 26.10.3 × 26.10.1 no driver principal (2026-10-22)

`w1` = Swift 1.5 `13839b7` no mlx-serve 26.10.1 (o driver diário). `w1z` = os mesmos pesos e flags no 26.10.3. 32K e 128K com 3 reps, 256K com 1 rep.

## Velocidade

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| w1 | 32K | 8.0 s | 34.5 s | 1.80 s | 0.96/0.96 | 83.1 | 0.689 | 96.9 GB | -0.01 GB | 0 | 12/13 (1 trunc) |
| w1z | 32K | 8.0 s | 34.6 s | 1.80 s | 0.96/0.96 | 81.8 | 0.662 | 100.0 GB | 0.00 GB | 0 | 13/13 |
| w1 | 128K | 8.7 s | 165.6 s | 2.00 s | 0.99/0.99 | 76.1 | 0.733 | 110.9 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| w1z | 128K | 8.9 s | 165.7 s | 1.90 s | 0.99/0.99 | 74.0 | 0.712 | 107.5 GB | 0.00 GB | 0 | 13/13 |
| w1 | 256K | 9.9 s | 350.5 s | 2.10 s | 1.00/1.00 | 65.4 | 0.779 | 111.3 GB | 0.00 GB | 0 | 5/5 |
| w1z | 256K | 9.2 s | 350.7 s | 2.30 s | 1.00/1.00 | 74.1 | 0.912 | 113.2 GB | 0.00 GB | 0 | 5/5 |

- Todos os gates passam nas três bandas. O alerta wired > 102 GB aparece a 128K e a 256K nos dois braços.

| razão `T_turno(w1z) / T_turno(w1)` | 32K | 128K | 256K |
|---|---:|---:|---:|
| w1z | 1.000 | 1.023 | 0.929 |

`decide.py --mode le --threshold 1.03`: VERDICT: pass.

## Tool calls

`scripts/toolcall-probe.sh`: 5 sessões de 4 turnos do `tool_loop.py` por penalidade, a 65536, sampling thinking do vendor, `reasoning_effort` xhigh. "Turnos" conta tool calls estruturadas e válidas. "Sessões" conta a resposta final com todos os valores dos tool results.

| braço | `frequency_penalty` | turnos | sessões | mediana por turno |
|---|---:|---:|---:|---:|
| w1 | 0 | 20/20 | 5/5 | 1.15 s |
| w1 | 1 | 20/20 | 5/5 | 1.13 s |
| w1z | 0 | 20/20 | 5/5 | 1.50 s |
| w1z | 1 | 20/20 | **2/5** | 1.93 s |

Com `frequency_penalty 1`, a 26.10.3 emite todas as tool calls. Em 3 das 5 sessões, porém, a resposta final degenera: o reasoning vira uma sequência de pontos, o content fica vazio e faltam os valores `ARGON-1844-EMBER` e `NEON-6301-ORBIT` (dump em `logs/tool-loop/w1z-fp1-s2-*-final.json`). A 26.10.1 não mostra esse efeito. A explicação provável: a 26.10.1 ignora a penalidade, e a 26.10.3 a aplica com a definição aditiva da OpenAI (fix da #912) sobre um reasoning longo. Isso não foi confirmado no código.

Uma primeira versão do probe usava o protocolo de 20 turnos numa sessão só. Nela, o `w1` falha no turno 5 com as duas penalidades: depois das 4 tarefas do prompt, o modelo responde em texto apesar de `tool_choice: required` (`results/toolcall/w1-fp{0,1}-strict20.jsonl`). Esse defeito não é o da #912, e a versão de 5 sessões o evita.

## Veredito

Recomendar o mlx-serve 26.10.3 no driver diário. Ele passa nas três condições: tool calls em 20/20 com penalidade 0 e com 1, gates nas três bandas, e `T_turno` a 1.000 × o `w1` a 32K e a 1.023 × a 128K. A 256K, ele é 7% mais rápido, com 1 rep. A troca fica com o usuário. Um harness que mande `frequency_penalty 1` (o Crush) recebe respostas finais degeneradas em 3 de 5 sessões na 26.10.3. OpenCode e Hermes não mandam essa penalidade por padrão; isso não foi verificado nesta campanha.

## Leitura

- A 32K e a 128K os dois runtimes empatam: TTFT, hit e cold iguais, decode 1–3% menor no 26.10.3.
- A 256K o decode do `w1z` sobe de 65.4 para 74.1 tok/s, e a aceitação MTP de 0.78 para 0.91. Com 1 rep, isso é indicação, não medida.
- O turno do `tool_loop` fica mais lento no 26.10.3 (mediana 1.50 contra 1.15 s com penalidade 0). O `T_turno` do probe de cache não mostra essa diferença.
