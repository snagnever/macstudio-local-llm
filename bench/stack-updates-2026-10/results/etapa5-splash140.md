# Etapa 5 — Splash 1.4.0 com GGUF do Flash-Next × w1 (2026-10-23)

`k1` e `k1a` = `unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ4_XS` `766911a` no Splash 1.4.0, com o draft DFlash2 que o Splash escolhe (`incoai/Qwen3.8-Flash-Next-DFlash2` `a22a174`). `k1` usa `--verify-rows all`, e `k1a` usa `auto`, o padrão da 1.4.0. A referência é o `w1` do Task 1 (Swift 1.5 MLX no mlx-serve 26.10.1). 32K e 128K com 3 reps.

## Desvio do plano: pesos

O plano previa o `ggml-org/Qwen3.8-Flash-Next-GGUF` IQ4_NL `91fb003`. O Splash 1.4.0 não carrega esse pack. Ele só aceita um GGUF dividido quando as partes ficam numa pasta `VARIANT/`, e o ggml-org deixa os dois shards na raiz. `:IQ4_NL` falha com "no single GGUF matches", e `:IQ4_NL-00001-of-00002` falha com "the GGUF's split files do not match its split.count" (`install/upstream.py`, `select_gguf`). O UD-IQ4_XS da Unsloth (93.7 GB) usa pastas e tem o tamanho mais próximo. Os pesos são do Flash-Next base, não do Swift 1.5. A comparação com o `w1` mistura runtime e pesos.

## Velocidade

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| w1 | 32K | 8.0 s | 34.5 s | 1.80 s | 0.96/0.96 | 83.1 | 0.689 | 96.9 GB | -0.01 GB | 0 | 12/13 (1 trunc) |
| k1 | 32K | 7.0 s | 36.8 s | 1.60 s | 0.96/0.96 | 94.1 | — | 110.6 GB | 0.00 GB | 0 | 13/13 |
| k1a | 32K | 6.8 s | 36.8 s | 1.60 s | 0.96/0.96 | 98.1 | — | 110.3 GB | 0.00 GB | 0 | 13/13 |
| w1 | 128K | 8.7 s | 165.6 s | 2.00 s | 0.99/0.99 | 76.1 | 0.733 | 110.9 GB | 0.00 GB | 0 | 12/13 (1 trunc) |
| k1 | 128K | 7.1 s | 177.0 s | 1.70 s | 0.99/0.99 | 93.7 | — | 114.8 GB | -0.02 GB | 0 | 13/13 |
| k1a | 128K | 6.8 s | 176.9 s | 1.70 s | 0.99/0.99 | 99.1 | — | 114.9 GB | 0.00 GB | 0 | 13/13 |

- Todos os gates passam. O alerta wired > 102 GB aparece em todas as linhas do Splash.
- O probe não acha `[spec-stats]` no boot log do Splash, porque essa linha é do mlx-serve. A aceitação do draft vem do log do Splash: 3.5 a 4.2 tokens por ciclo a 128K.

| razão `T_turno(cand) / T_turno(w1)` | 32K | 128K |
|---|---:|---:|
| k1 | 0.875 | 0.816 |
| k1a | 0.850 | 0.782 |

`decide.py --mode le --threshold 0.97`: VERDICT: pass para os dois.

## Determinismo

`cache_probe.py` com temperatura 0, cenários `cold,identical`, 2 reps. `greedy_tokens_hash` cobre só o `content` final.

| braço | hash do content | tokens de saída (cold, cold, identical, identical) |
|---|---|---|
| k1 (`all`) | igual nos 4 requests | 590, 1609, 1256, 1183 |
| k1a (`auto`) | igual nos 4 requests | 810, 761, 546, 1381 |

A resposta final não muda, mas o comprimento da saída muda entre requests iguais nos dois modos. O raciocínio diverge a temperatura 0 mesmo com `--verify-rows all` e sem prefix cache (os dois `cold`). Os requests não usaram `cache_salt`, que o mantenedor recomenda na #483.

## Veredito

O Splash 1.4.0 passa a regra de velocidade: `T_turno` 0.78–0.88 × o `w1`, com decode de 94–99 tok/s contra 76–83. A recomendação não é trocar o driver ainda. Os pesos testados são o Flash-Next base, não o Swift 1.5. A qualidade e as tool calls do Splash não foram medidas. O wired fica perto de 115 GB a 128K, e a 256K não foi testada. O próximo teste é o Swift 1.5 GGUF da UkisAI (`IQ4_XS`, pastas `VARIANT/`) no Splash, que isola o runtime.

## Leitura

- O ganho vem do decode. O DFlash2 aceita cerca de 4 tokens por ciclo, e o decode não cai de 32K para 128K. O prefill a frio é 7% mais lento que o do `w1` a 128K (177 contra 166 s).
- O `k1a` é 3–4% mais rápido que o `k1`. O ganho do verify adaptativo é pequeno neste rig.
- O Splash deixa residentes a tabela PLE (27.5 GB) e os experts (62.6 GB), conforme o boot log.
- O `/v1/tokenize` não existe no Splash. O probe registra 404 e usa o fallback, como no braço `k27`.
