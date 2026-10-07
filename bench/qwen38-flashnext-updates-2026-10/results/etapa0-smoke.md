# Etapa 0 — smoke 8K de n1 e n2

mlx-serve 26.10.1, `cold → identical → tool_turn`, 1 rep, `temperature=1.0`, reasoning `xhigh`, limite 4096 tokens.
Os dois braços carregaram e responderam sem erro HTTP.

| braço | pesos | cold decode / TTFT | identical decode / TTFT / hit | tool_turn decode / TTFT / hit | needles | MTP aceitação | wired pico |
| --- | --- | --- | --- | --- | --- | --- | --- |
| n1 | mixed-4-8bit @ ef5b919 | 77.8 / 3.55 s | 89.2 / 0.13 s / 0.99 | 79.3 / 1.61 s / 0.71 | 3/3 ok | 0.613 | 81.94 GB |
| n2 | iQ-MLX-4.7bpw @ dafff5c | 87.2 / 3.32 s | 88.1 / 0.13 s / 0.99 | 80.8 / 1.62 s / 0.71 | cold e identical ok; tool_turn 0/3 | 0.581 | 81.33 GB |

Referência c1 (26.9.2, mesmos pesos do n1) na Etapa 0 de 2026-09: cold 59.9 tok/s, identical 71.2, tool_turn 51.3.

## `/props`

Os dois braços mostram `version=26.10.1`, `kv_quant=off`, `mtp.loaded=true`, `mtp.depth=6`, `mtp.adaptive=true`,
`pld.default_on=true`, prefix cache 16 GB RAM / 100 GB disco e `ngram_warm` completo (32 000 153 976 bytes).
O `/props` não expõe a flag `--ple-gpu`.

## `[spec-stats]`

16 linhas em cada boot log. O 26.10.1 escreve linhas `[spec-stats]` sem `mode=` (`lazy=`, `lookup_table=`).
O commit 9e648fb faz o `attach_mtp.py` ignorar essas linhas. Os dois `jsonl` foram re-anexados depois do fix.

## Notas

1. **Hit de 0.71 no tool_turn a 8K é estrutural.** O cache reusa 2701 de 3802 tokens; o turno novo traz
   1027 tokens de sufixo. O c1 deu 0.72 no mesmo cenário em 2026-09. O gate de hit ≥ 0.90 vale a partir de 32K.
2. **n2 errou as needles no tool_turn** com `finish_reason=stop` e 1028 tokens de saída. É uma amostra a
   `temperature=1.0`. O c1 também falhou esse cenário a 8K em 2026-09 (truncado). Conferir a 32K e na Etapa 2.
3. **Decode do n1 a 8K é ~30% maior que o do c1 de 2026-09** com os mesmos pesos. A Etapa 1 mede isso
   com o c1 na mesma sessão.
4. O campo `quant` do n2 sai `unknown`: o nome do pack não segue o padrão que o harness reconhece. Não afeta as métricas.

Dados: `n{1,2}-8192-t1.0-smoke.jsonl`, `props/n{1,2}-8192-t1.0-smoke.json`.
