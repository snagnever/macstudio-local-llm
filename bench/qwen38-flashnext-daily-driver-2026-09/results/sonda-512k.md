# Sonda de capacidade a 512K (2026-09-13)

`cold` + `identical` a 524288 tokens, 1 tentativa por candidato, perfil do vendor (`temperature=1.0`).
`iogpu.wired_limit_mb` = 0 (default, sem `sudo`) durante toda a sonda.

| cand | alcança 512K | follow-up | decode cold | cold TTFT | wired pico | mecanismo |
|---|---|---|---:|---:|---:|---|
| c1 mlx-serve 26.9.2 | **sim** | **sim** (identical 0.6 s, hit 1.00) | 42.6 tok/s | 844.6 s | 104.3 GB | YaRN fator 2.0 via `--config-overrides`, KV 8-bit |
| c2 oMLX 0.6.4 | não testado | — | — | — | — | oMLX sem YaRN: teto 262K |
| c3 oMLX 0.7.0.dev2 | não testado | — | — | — | — | oMLX sem YaRN: teto 262K |
| c4 MTPLX 2.11.2 | não testado | — | — | — | — | recusa já a 128K (fit 114.688 tokens) |

## Leitura

- **O c1 serve 512K com follow-up sem `sudo`.** O log confirma o YaRN (`factor 2.0000 (window 262144 -> 524288)`).
  Needles corretas no cold; o follow-up reusou o prefixo inteiro.
- **Está na borda de memória:** memória livre mínima de 0.01 GB durante a run, sem swap. Um app pesado aberto
  em paralelo pode derrubar esse caso. O `sudo sysctl iogpu.wired_limit_mb=124518` dá margem se 512K virar uso real.
- **Decode a temp 1.0 é menor que o arquivado a temp 0:** 42.6 contra 51.4 tok/s (campanha qwen38-updates).
  A MTP aceita menos drafts sob amostragem.
- O primeiro turno leva ~14 min. 512K é capacidade, não uso diário responsivo.
- oMLX não tem mecanismo de YaRN (o rope do `qwen4_exp` ignora o tipo); o MTPLX só estenderia via overlay de
  `config.json`, sem sentido para um runtime que já recusa 128K.

Dados: `c1-524288-t1.0-yarn2.jsonl`.
