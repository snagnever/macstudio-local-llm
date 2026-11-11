# Task 2: Velocidade e cache de um stream (2026-11-11)

**A 1.6.1 passa nos dois modos PLE. A razão de `T_turno` contra a 1.5.0 fica entre 1.000 e 1.017 em 32K, 128K e 256K, abaixo do limite de 1.03. Com PLE `auto`, o wired peak cai 29 GB em todas as bandas. A 1M, o decode sobe de 71–77 para 102 tok/s.**

Fila `logs/chain-t123.sh`, das 15:11 às 19:27 (relógio do rig), com a rep a 1M das 18:35 às 19:27. Cada posição do ABBA é um boot com 1 rep, então cada braço tem 3 reps por banda. O braço `k2hp` é o `k2h` com `--ple-memory off`. As tags são `p<N>` para o `k2f`, `a<N>` para o `k2h` e `o<N>` para o `k2hp`.

## PLE `auto` (`k2h`)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| k2f | 32K | 6.0 s | 34.6 s | 1.50 s | 0.96/0.96 | 114.4 | 106.5 GB | 0.00 GB | 0 | 13/13 |
| k2h | 32K | 6.1 s | 33.1 s | 1.50 s | 0.96/0.96 | 111.1 | 77.5 GB | 0.00 GB | 0 | 13/13 |
| k2f | 128K | 6.0 s | 167.5 s | 1.60 s | 0.99/0.99 | 115.2 | 108.3 GB | 0.00 GB | 0 | 13/13 |
| k2h | 128K | 6.1 s | 160.5 s | 1.50 s | 0.99/0.99 | 112.4 | 79.8 GB | 0.00 GB | 0 | 13/13 |
| k2f | 256K | 6.3 s | 351.3 s | 1.60 s | 1.00/1.00 | 108.7 | 111.0 GB | 0.00 GB | 0 | 13/13 |
| k2h | 256K | 6.3 s | 337.1 s | 1.60 s | 1.00/1.00 | 109.1 | 82.2 GB | 0.00 GB | 0 | 13/13 |

| razão `T_turno(k2h) / T_turno(k2f)` | 32K | 128K | 256K |
|---|---:|---:|---:|
| `auto` | 1.017 | 1.017 | 1.000 |

`decide.py`: **VERDICT: pass.** Os gates passam nos dois braços em todas as bandas.

## PLE `off` (`k2hp`)

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| k2hp | 32K | 6.0 s | 33.1 s | 1.40 s | 0.96/0.96 | 112.6 | 106.6 GB | 0.00 GB | 0 | 13/13 |
| k2hp | 128K | 6.0 s | 160.4 s | 1.50 s | 0.99/0.99 | 115.0 | 108.6 GB | 0.00 GB | 0 | 13/13 |
| k2hp | 256K | 6.3 s | 337.0 s | 1.60 s | 1.00/1.00 | 107.8 | 111.0 GB | 0.00 GB | 0 | 12/13 (1 trunc) |

As linhas do `k2f` são as mesmas da tabela de cima.

| razão `T_turno(k2hp) / T_turno(k2f)` | 32K | 128K | 256K |
|---|---:|---:|---:|
| `off` | 1.000 | 1.000 | 1.000 |

`decide.py`: **VERDICT: pass.** O `12/13` a 256K é um request truncado em `max_tokens`, não um needle errado.

## Leitura

- **Cold TTFT:** a 1.6.1 fica 4–5% mais rápida em 128K e 256K nos dois modos (160.5 s contra 167.5 s; 337 s contra 351 s). Em 32K, a diferença é de 1.5 s.
- **Decode com `auto`:** fica 2–3% abaixo da 1.5.0 em 32K e 128K e empata em 256K. Esse valor explica a razão 1.017. Com `off`, o decode fica entre −1.6% e −0.2% contra a 1.5.0.
- **Memória com `auto`:** o wired peak cai 29 GB, porque a tabela PLE de 27465 MiB fica no SSD. O alerta `wired>102` some. Com `off`, o wired peak fica igual ao da 1.5.0.
- **Livre mínimo:** 0.01–0.06 GB em todos os braços, como na splash16. O valor vem do cache de arquivos do macOS e não indica pressão, porque o swap Δ fica em 0.
- **Os dois modos passam.** A Task 3 escolhe o modo PLE pela regra do plano.

## 1M (`k2h`, PLE `auto`, 1 rep)

| braço | fonte | `T_turno` | cold TTFT | warm TTFT | decode | wired peak | needles |
|---|---|---:|---:|---:|---:|---:|---|
| `k2f` | splash16 | 9.8 s | 1534.1 s | 2.60 s | 71.4 | 110.1 GB | 5/5 |
| `k2g` | splash16 (referência) | 10.1 s | 1624.2 s | 3.50 s | 76.9 | 109.8 GB | 4/5 |
| `k2h` | esta campanha | 7.0 s | 1477.8 s | 2.00 s | 101.7 | 97.0 GB | 5/5 |

- **Capacidade:** o log de boot não tem `capacity_exhausted`, e os 5 requests responderam sem erro.
- **KV:** o log de boot diz `window 1000000, resident 1000000`. Na 1.6.0, a mesma linha dizia 860153 tokens residentes. O cache SSD continua com quota de 32 GiB.
- **PLE:** o log de boot confirma que 27465 MiB da tabela ficam no SSD, com um cache de linhas de 237 MiB.
- **Decode:** sobe 32% contra o `k2g` (101.7 contra 76.9 tok/s), e o `tool_turn` chega a 118 tok/s. A 1M não entra na regra, e a comparação usa 1 rep de outro dia. Uma causa possível é a memória que a tabela PLE libera, mas esta campanha não separa as causas.

## `middle_mutation`

Hit 0 nos três braços em todas as bandas, com o TTFT igual ao cold: 32K 34.7/33.2/33.2 s, 128K 167.6/160.6/160.5 s, 256K 351.4/337.1/337.0 s (`k2f`/`k2h`/`k2hp`). A 1M, o `k2h` também tem hit 0 e TTFT 1477.6 s. A fila roda `middle_mutation` só no primeiro boot de cada braço e banda, então cada valor é 1 amostra. O comportamento é o mesmo da 1.5.0 e da 1.6.0.

## Desvios

- **Cenários:** os boots depois do primeiro de cada braço e banda rodam `cold,identical,append,tool_turn`, sem `middle_mutation`. Isso não muda o `T_turno`, que não usa esse cenário.
- **`summarize_driver` avisa que mistura `session_id`:** o aviso é esperado, porque cada rep vem de um boot.

Fontes: `k2f-*-p<N>.jsonl`, `k2h-*-a<N>.jsonl`, `k2h-*-o<N>.jsonl`, `k2h-1000000-t1.0-l1.jsonl`.
