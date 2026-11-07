## Etapa 2 — ABBA de um stream, 1.5.0 contra 1.6.0

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| k2f | 32K | 6.2 s | 34.6 s | 1.50 s | 0.96/0.96 | 109.5 | — | 106.5 GB | 0.00 GB | 0 | 13/13 |
| k2g | 32K | 6.1 s | 34.7 s | 1.50 s | 0.96/0.96 | 110.9 | — | 106.3 GB | 0.00 GB | 0 | 13/13 |
| k2f | 128K | 6.2 s | 167.5 s | 1.60 s | 0.99/0.99 | 111.9 | — | 108.3 GB | 0.00 GB | 0 | 13/13 |
| k2g | 128K | 6.2 s | 167.8 s | 1.60 s | 0.99/0.99 | 111.1 | — | 108.3 GB | 0.00 GB | 0 | 13/13 |
| k2f | 256K | 6.2 s | 351.3 s | 1.60 s | 1.00/1.00 | 111.7 | — | 110.9 GB | 0.00 GB | 0 | 13/13 |
| k2g | 256K | 6.2 s | 351.8 s | 1.60 s | 1.00/1.00 | 111.4 | — | 111.0 GB | 0.00 GB | 0 | 13/13 |

- k2f @ 32K: livre mínimo 0.06 GB; gates passa; alertas wired>102
- k2g @ 32K: livre mínimo 0.04 GB; gates passa; alertas wired>102
- k2f @ 128K: livre mínimo 0.06 GB; gates passa; alertas wired>102
- k2g @ 128K: livre mínimo 0.06 GB; gates passa; alertas wired>102
- k2f @ 256K: livre mínimo 0.06 GB; gates passa; alertas wired>102
- k2g @ 256K: livre mínimo 0.06 GB; gates passa; alertas wired>102

| razão `T_turno(k2g) / T_turno(k2f)` | 32K | 128K | 256K |
|---|---:|---:|---:|
| k2g | 0.984 | 1.000 | 1.000 |

Regra: ≤ 1.03 em 32K, 128K, 256K, gates do candidato e da base, `[spec-stats]`.
VERDICT: pass


## Bandas longas

| braço | contexto | reps | `T_turno` | cold TTFT | warm TTFT | decode | wired peak | needles |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `k2f` | 512K | 1 | 6.8 s | 743.8 s | 1.80 s | 102.2 | 116.2 GB | 5/5 |
| `k2g` | 512K | 3 | 6.5 s | 745.5 s | 1.80 s | 108.8 | 116.6 GB | 13/13 |
| `k2g` | 1M | 1 | 10.1 s | 1624.2 s | 3.50 s | 76.9 | 109.8 GB | 4/5 |

- **512K:** as releases empatam. A diferença de decode vem de 1 rep contra 3 e não entra na regra.
- **1M:** o `T_turno` do `k2g` fica 7–9% acima da referência `k2a` da 1.4.0 (9.3–9.4 s), fora da faixa de ±5%. O decode está igual (75–77 tok/s). A diferença vem do warm TTFT: 3.5 s contra 2.6 s, em uma amostra. O cold TTFT também subiu: 1624 s contra 1532 s.
- **1.5.0 a 1M, no mesmo dia:**

  | braço | `T_turno` | cold TTFT | warm TTFT | decode | wired peak | needles |
  |---|---:|---:|---:|---:|---:|---|
  | `k2f` | 9.8 s | 1534.1 s | 2.60 s | 71.4 | 110.1 GB | 5/5 |
  | `k2g` | 10.1 s | 1624.2 s | 3.50 s | 76.9 | 109.8 GB | 4/5 |

  A razão `k2g`/`k2f` é 1.031, com 1 rep por release. O warm TTFT sobe 0.9 s e o cold TTFT sobe 5.9% na 1.6.0. O decode fica 7.7% mais rápido na 1.6.0. A regra de paridade só vale para 32K, 128K e 256K, então este valor é uma observação e não muda o veredito. O `k2f` também fica 4–5% acima do `k2a` da 1.4.0 (9.3–9.4 s), então a maior parte da diferença contra a referência antiga vem do dia ou da 1.5.0, e cerca de 3% vem da 1.6.0. Uma rep por release não separa 3% do ruído.
- **Needle errado a 1M:** o `tool_turn` terminou com `finish_reason=stop`, 3753 tokens e 3 needles na resposta, com pelo menos um errado. O `k2a` também errou esse cenário em um dos seus runs a 1M, mas por truncamento em 4096. Uma amostra não indica regressão.

## 1M: capacidade e SSD

- O log de boot não tem `capacity_exhausted`, e os 5 requests responderam 200.
- O KV fica no SSD: quota de 32 GiB, janela de 1000000, 860153 tokens residentes.
- O disco livre caiu de 728 GB para 715 GB durante o run e voltou a 729 GB depois. O valor de 13 GB é uma leitura única, não o pico.

## `middle_mutation`

Hit 0.0 nas duas releases em todas as bandas, com o TTFT igual ao cold (32K: 34.8 s; 128K: 167.6/169.4 s; 256K: 351.4/351.9 s; 512K: 743.8/745.5 s). O `cache_probe` tem 1 amostra por braço e banda.

## `ttft_parts_ms`

Esta etapa não registra o campo. O `cache_probe` não grava o `/status` por request. A Etapa 3 grava o campo nas amostras de status a 256K.

## Memória

O livre mínimo foi de 0.04–0.06 GB em todas as bandas, nas duas releases. A swap Δ foi 0.00 GB. O plano só registra este valor.
