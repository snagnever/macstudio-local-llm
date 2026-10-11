# Campanha swift15-flashnext-2026-10 — Swift 1.5 × n2 com reasoning explícito

Plano de implementação: [docs/superpowers/plans/2026-10-10-flashnext-swift15-ab.md](../../docs/superpowers/plans/2026-10-10-flashnext-swift15-ab.md).
Pesquisa de origem: [research/qwen38-flashnext-derivatives-20261009.md](../../research/qwen38-flashnext-derivatives-20261009.md) §3 e §10.

## 1. Pergunta

O Swift 1.5 (w1) mantém a qualidade do n2 e chega à resposta final mais rápido com thinking livre?

O card do Swift 1.5 declara 63% menos tokens de thinking no GPQA-Diamond, com −0,2 no GPQA-D, −2,0 no AIME
e −3,1 no IFBench. O ganho está no número de tokens de raciocínio. O `T_turno` (512 tokens fixos) não o mede.

## 2. Braços

| braço | pesos | runtime |
| --- | --- | --- |
| n2 | `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw` @ `dafff5c` | mlx-serve 26.10.1 |
| w1 | `Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` @ `13839b7` | mlx-serve 26.10.1 |

Os dois braços usam o mesmo comando de servidor (`run-candidate.sh`, bloco `n1|n2|n2p|w1`). Só o `--model`
muda: 131072 tokens, MTP, prefix cache 16 GB RAM / 100 GB disco / 64 entradas.

Licença do Swift 1.5: Swift Open License v1.0. O usuário confirmou em 2026-10-10 que o uso está OK.

## 3. Por que o run de qualidade de 07/10 não serve

O `bench2.py` não enviava `reasoning_effort`. Cada servidor aplicava o próprio default. No HumanEval de
2026-10-07, o n2 respondeu com 201 tokens por questão, 0 `reasoning_tokens` e nenhum `<think>`: ele não pensou.
O o1 e o m1x pensaram (1 807 e 3 345 tokens por questão). Esta campanha manda `reasoning_effort` e o sampling
explícitos em toda requisição.

## 4. Bateria

`reasoning_effort` **xhigh** em todas as suítes.

| suíte | n | max_tokens | runner |
| --- | ---: | ---: | --- |
| HumanEval | 164 | 32768 | `bench2.py humaneval` |
| GPQA-Diamond (amostra seed 42) | 50 | 65536 | `bench2.py gpqa` |
| LiveCodeBench v6 (amostra seed 42) | 50 | 65536 | `bench2.py livecodebench` |
| jdhodges | 40 | 32768 | `tool_call_bench.py` |
| Veerman | 12 | 32768 | `tool_call_bench.py` |
| IF (estilo IFEval) | 20 | 16384 | `scripts/if_probe.py` |

Os runners ficam no submódulo `tools/local-llm-bench-m4-32gb` (branch `feat/reasoning-effort`).

## 5. Perfis de sampling

| perfil | parâmetros | papel |
| --- | --- | --- |
| **t1** | `temperature 1.0`, `top_p 0.95`, `top_k 20`, `min_p 0`, `presence_penalty 0`, `repetition_penalty 1.0` | principal: sampling do vendor e do uso diário |
| **t0** | `temperature 0` | controle reproduzível; modo das baterias de qualidade anteriores |

Fonte do t1: `generation_config.json` dos dois packs (`temperature 1.0`, `top_p 0.95`, `top_k 20`) e card do
Swift 1.5 ("temperature 1.0 · top_p 0.95 · top_k 20 · min_p 0 · presence_penalty 0 · repetition_penalty 1").

Cada braço roda a bateria nos dois perfis, numa só subida do servidor, com t1 primeiro
(`scripts/run-ab.sh <braço>`). A saída fica em `results/ab/<perfil>/<braço>/<suíte>.jsonl`.

## 6. Gates

Calculados por perfil com `scripts/summarize_ab.py`:

- **G1 qualidade:** por suíte, `acertos(w1) ≥ acertos(n2) − margem`. Margens: HumanEval 3, GPQA 3, LCB 3,
  jdhodges 2, Veerman 1, IF 2.
- **G2 thinking:** `tempo mediano(w1) ≤ 0,8 × tempo mediano(n2)` no GPQA e no LCB.

Calculado com `summarize_driver.py`:

- **G3 velocidade:** `T_turno(w1) ≤ 1,03 × T_turno(n2)` a 32K e a 128K. O `T_turno` roda no perfil t1.

Regra de decisão (o t1 decide, porque é o perfil do uso diário):

- **Promover o w1** se G1 e G2 passarem em t1, G1 passar em t0, e G3 passar.
- **Desempate:** se G1 de uma suíte passar num perfil e falhar no outro, rode de novo essa suíte em t1 nos
  dois braços. Use a média das duas rodadas de t1.
- **Manter o n2** se G2 falhar em t1, ou se G1 falhar depois do desempate.

## 7. Ordem dos runs

1. Smoke n2 e smoke w1: `scripts/run-ab.sh <braço> --smoke`. HumanEval 1–3 e `samplecheck` (`if07` três
   vezes) nos dois perfis. Gate: reasoning presente (`completion_tokens` mediano > 500 ou `reasoning_chars` > 0);
   em t1, ao menos 2 respostas distintas em 3.
2. Bateria n2 (t1, t0).
3. Bateria w1 (t1, t0).
4. `T_turno`: n2 e w1 a 32K, depois w1 e n2 a 128K (`scripts/run-arm.sh <braço> <ctx> --repeat 3 --tag fn`).

Antes de cada run: o `run-candidate.sh` mata o que escuta na porta 11234 e apaga `~/.mlx-serve/kv-cache`.
Pare o driver diário e confira que nenhuma outra sessão está com um run ativo.

## 8. Limites conhecidos

- Uma rodada por braço e perfil. Em t1, a amostragem tem variância: 1 a 3 questões de diferença ficam dentro do
  ruído. O t0 é o controle reproduzível.
- GPQA e LCB usam amostras de 50 questões, não os conjuntos completos.
- A sonda IF é uma checagem no estilo IFEval. Ela não reproduz o IFBench do card.
- Os pesos dos dois braços têm o mesmo layout e o mesmo runtime, mas a tabela n-gram difere (hashes LFS
  diferentes). O A/B compara os dois packs, não só o fine-tune.
