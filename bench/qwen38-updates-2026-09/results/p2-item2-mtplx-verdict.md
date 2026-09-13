# P1 item 2 — MTPLX 2.11.1 vs 2.11.2 (Qwen3.8-27B Optimized-Speed, arm V, 32K)

Veredito: **PROMOVER 2.11.2 — correcao, nao so velocidade.**

A MTP nativa do 2.11.1 e lossy a 32K neste modelo: aceita tokens de draft errados e
responde errado em 15/15 cenarios (needles todas falsas). Controle decisivo: 2.11.1 em
AR (MTP off) responde CORRETO. Logo a falha e da MTP do 2.11.1, nao do harness (mesmo
modelo, fixtures e tokenizer nos dois bracos; so a versao/MTP mudou). O 2.11.2 corrige
com MTP ligada.

| config              | correcao        | decode tok/s |
|---------------------|-----------------|-------------:|
| 2.11.1 MTP (turbo)  | erra 15/15      | ~25 (invalido) |
| 2.11.1 AR (dense)   | correto         | 19.8 |
| 2.11.2 MTP (turbo)  | correto         | 42.0 |

O "+67% decode" da A/B bruta e artefato (bracos geraram conteudos diferentes). A leitura
valida: 2.11.2 MTP correto ~2.1x o baseline correto (2.11.1 dense). Escopo do achado: 27B
Optimized-Speed, 32K, depth 3, reasoning xhigh; pode ser especifico de config/modelo.

Dados: p2-mtplx-v2.11.{1,2}-32768.jsonl (A/B); p2-control-mtplx-v2.11.1-ar-cold.jsonl (controle).
