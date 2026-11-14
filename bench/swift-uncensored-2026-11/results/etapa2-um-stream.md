# Etapa 2 — velocidade e cache de um stream

Data: 2026-11-13 e 14. Rig: Mac Studio M4 Max 128 GB, Splash 1.6.1, `cache_probe`, temperatura 1.0, `reasoning_effort` `xhigh`.

Cada braço tem 2 boots por contexto, com 5 cenários por boot. A ordem é espelhada: o `k2h` roda no começo e no fim a 32K e a 256K, e nas 2 posições do meio a 128K. A fila durou de 17:08 a 01:25, com 24 boots e nenhum erro. Dados: `results/<braço>-<contexto>-t1.0-s<N>.jsonl`.

Comando do veredito, por braço:

```bash
python3 bench/flashnext-next-steps-2026-10/scripts/decide.py \
  --results-dir bench/swift-uncensored-2026-11/results --glob '*-t1.0-s[0-9]*.jsonl' \
  --base k2h --cand <braço> --ctx 32768,131072,262144 --mode le --threshold 1.05
```

## Medidas

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit (append / tool_turn) | decode tok/s | prefill tok/s | wired peak | livre mínimo | swap Δ | erros HTTP | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| `k2h` | 32K | 6.0 s | 33.1 s | 1.50 s | 0.96 / 0.96 | 112.1 | 824 | 78.0 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z4h` | 32K | 6.1 s | 33.4 s | 1.50 s | 0.96 / 0.96 | 109.8 | 817 | 80.1 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z2h` | 32K | 6.2 s | 33.5 s | 1.50 s | 0.96 / 0.96 | 108.7 | 815 | 64.7 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z3h` | 32K | 6.2 s | 33.5 s | 1.50 s | 0.96 / 0.96 | 107.2 | 816 | 64.4 GB | 0.06 GB | 0.00 GB | 0 | 9/10 (1 truncada) |
| `k2h` | 128K | 5.9 s | 160.5 s | 1.50 s | 0.99 / 0.99 | 117.0 | 783 | 80.0 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z4h` | 128K | 6.2 s | 161.8 s | 1.50 s | 0.99 / 0.99 | 110.0 | 777 | 82.1 GB | 0.05 GB | 0.00 GB | 0 | 10/10 |
| `z2h` | 128K | 6.2 s | 162.0 s | 1.60 s | 0.99 / 0.99 | 109.9 | 775 | 66.6 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z3h` | 128K | 6.1 s | 162.1 s | 1.60 s | 0.99 / 0.99 | 113.4 | 775 | 66.5 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `k2h` | 256K | 6.2 s | 337.3 s | 1.60 s | 1.00 / 1.00 | 112.2 | 761 | 82.4 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z4h` | 256K | 6.4 s | 339.8 s | 1.60 s | 1.00 / 1.00 | 105.9 | 755 | 84.7 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z2h` | 256K | 6.3 s | 340.3 s | 1.60 s | 1.00 / 1.00 | 108.7 | 754 | 69.2 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |
| `z3h` | 256K | 6.2 s | 340.4 s | 1.60 s | 1.00 / 1.00 | 112.2 | 754 | 69.0 GB | 0.06 GB | 0.00 GB | 0 | 10/10 |

O prefill vem do campo `prompt_tps` do cenário `cold`. Todos os gates passam em todos os braços. A resposta truncada do `z3h` gasta os 4096 tokens no cenário `middle_mutation`; ela não conta como needle errada.

## Veredito da regra "Velocidade"

Regra: `T_turno(braço) ≤ 1.05 × T_turno(k2h)` a 32K, 128K e 256K, com todos os gates.

| braço | 32K | 128K | 256K | veredito |
|---|---:|---:|---:|---|
| `z4h` | 1.017 | 1.051 | 1.032 | **falha** (128K) |
| `z2h` | 1.033 | 1.051 | 1.016 | **falha** (128K) |
| `z3h` | 1.033 | 1.034 | 1.000 | **passa** |

## Leitura

- O `z4h` e o `z2h` passam do limite por 0.001 a 128K. A diferença é de 0.3 s por turno.
- A diferença vem do decode. A 128K o `k2h` faz 118.3 e 115.7 tok/s nos 2 boots; o `z4h` faz 109.8 e 110.2; o `z3h` faz 116.3 e 110.5.
- O cold TTFT fica até 1.2% acima do `k2h`. O warm TTFT fica até 0.1 s acima. O hit do cache é igual.
- O decode do `z3h` varia 5% entre 2 boots do mesmo contexto. Com 2 boots por braço, a margem de 0.001 fica dentro dessa variação. A campanha não repetiu a fila.
- Em todos os contextos, o decode varia até 10.3% entre 2 boots do mesmo braço: o `k2h` faz 104.6 e 115.4 tok/s a 256K. A diferença entre os braços fica dentro dessa variação ([report](../../../reports/qwen38-flashnext-uncensored-speed.html)).
- O `z2h` e o `z3h` usam 13 GB menos de memória que o `k2h`. O `z4h` usa 2 GB mais.

## Decisão

- Pela regra escrita, só o `z3h` passa em "Velocidade".
- A campanha [harness-delivery-2026-11](../../harness-delivery-2026-11/plan.md) previa trocar o `z4` pelo `z2` nesse caso. O `z2h` falha com a mesma razão, e a troca não melhora a velocidade. A campanha mantém o `z4`: ele tem a menor taxa de recusa e o menor número de respostas vazias da [Etapa 1](etapa1-recusa.md). Essa campanha mede o tempo de entrega direto, com a regra "Reserva".
