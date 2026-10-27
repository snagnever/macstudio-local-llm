# Etapa 4 — qualidade leve do Splash com o Swift (2026-10-25)

O braço Swift é o `k2a` (Swift 1.5 GGUF IQ4_XS no Splash 1.4.0, KV int8, `--verify-rows auto`). A referência é o `w1z` (o driver diário, Swift 1.5 MLX no mlx-serve 26.10.3). Cada coluna sobe o servidor com o `--max-context` dela. Acima de 262144, o Splash liga o YaRN estático, que muda as respostas a prompts curtos também. A bateria usa o perfil t1 (temperature 1.0, top-p 0.95, top-k 20) e `reasoning_effort` xhigh. O GSQ fica na [etapa5](etapa5-gsq-mlx-serve.md).

## Bateria

| suíte | w1z 262144 | k2a 262144 | k2a 524288 | k2a 1000000 |
|---|---:|---:|---:|---:|
| HumanEval | 142/164 | 147/164 · 151/164 (2ª rodada) | 147/164 | 142/164 · 148/164 (2ª rodada) |
| GPQA | 43/50 | 41/50 (3 trunc) | 43/50 (3 trunc) | 43/50 (2 trunc) |
| LiveCodeBench | 47/50 | 47/50 | 47/50 | 47/50 |
| IF | 19/20 | 19/20 | 18/20 | 19/20 |
| jdhodges | 34/40 | 37/40 | 37/40 | 36/40 |
| veerman | 10/12 | 10/12 | 10/12 | 9/12 |
| tempo mediano GPQA / LCB | 15.4 / 19.0 s | 16.0 / 15.9 s | 13.2 / 18.1 s | 20.7 / 14.2 s |

Gates do `summarize_ab.py`:

| comparação | G1 (acertos ≥ base − margem) | G2 (tempo ≤ 0.8 × base) |
|---|---|---|
| k2a 262144 × w1z 262144 | passa nas 6 | falha (GPQA, LCB) |
| k2a 524288 × k2a 262144 | passa nas 6 | falha (GPQA, LCB) |
| k2a 1000000 × k2a 262144 | HumanEval: média de 145 contra 149 em 2 rodadas, 1 abaixo da margem 3 (aceito como ruído, decisão do usuário); passa nas outras 5 | falha (GPQA, LCB) |

- O G2 foi feito para um candidato que deveria pensar menos (o A/B n2 × w1 da swift15). Aqui ele só informa: o Splash não é 20% mais rápido por questão, porque o `k2a` raciocina um pouco mais (GPQA: 4868 contra 3702 chars medianos). O veredito usa só o G1.
- Na primeira rodada, o jdhodges e o veerman do `w1z` não rodaram, porque a fila não achava o `uv`. A reposição rodou em 25/10.
- **HumanEval a 1M.** A primeira rodada deu 142 contra 147. Uma segunda rodada a 262144 e a 1000000 deu 151 e 148. A regra fixada antes da rodada compara as médias: 145 a 1M contra 149 a 262144, 1 questão abaixo da margem de 3. As rodadas do mesmo perfil variam 4 a 6 questões (147 e 151; 142 e 148), então a diferença fica dentro do ruído. O usuário decidiu ignorar a regra e aceitar o resultado.

## Longctx (`longctx_probe.py`, 8 perguntas, fill 0.97)

| braço (servidor) | 128K | 256K | 512K | 1M |
|---|---:|---:|---:|---:|
| w1z (262144) | 8/8 | 8/8 | — | — |
| w1zq4 (524288, YaRN 2.0) | 8/8 | 8/8 | 8/8 | — |
| k2a (262144) | 8/8 | 8/8 | — | — |
| k2a (524288) | 8/8 | 8/8 | 8/8 | — |
| k2a (1000000) | 7/8 (errou 1 soma) | 8/8 | 8/8 | 8/8 |

Todas as bandas ficam ≥ 80% e no máximo 12.5 pontos abaixo da banda de 262144.

### Cache entre perguntas no Splash

As 8 perguntas dividem o mesmo prefixo, e só a primeira deveria pagar o prefill. No `k2a`, a q04 (a primeira pergunta de soma) refaz o prefill inteiro em todos os servidores na banda de 128K e no servidor de 1M na banda de 1M (1450 s). No mlx-serve isso nunca acontece.

O log do Splash mostra a causa. A q04 encontrou o KV do prefixo no disco ("deduplicated 933,824"), mas só um estado recorrente em 24,960 tokens antes do ponto onde ela diverge. O Flash Next é híbrido: as camadas GDN levam um estado que não volta atrás, e o Splash só guarda esse estado em alguns pontos (o fim de cada pedido). Um pedido que diverge antes do último ponto guardado recalcula tudo. É o mesmo mecanismo do `middle_mutation` (hit 0, ver [etapa3](etapa3-1m.md)). Depois da q04, o Splash guarda um estado no fim do prefixo, e as perguntas seguintes acertam o cache.

Para um agente, isso afeta:

- editar ou refazer a última mensagem do usuário;
- ramificar várias chamadas a partir do mesmo contexto.

## Tool calls (`toolcall-probe.sh --sessions 20 --max-tokens 2048`)

| braço | frequency_penalty 0 | frequency_penalty 1 |
|---|---|---|
| w1z | 20/20 sessões, 80/80 turnos | 14/20 sessões, 80/80 turnos (faltam chaves na resposta final) |
| k2a | 20/20 sessões, 80/80 turnos | 13/20 sessões, 58/64 turnos |

Com penalidade 0, que os clientes do driver enviam, os dois braços passam em tudo. Com penalidade 1, os dois braços falham. No mlx-serve, a causa é o #912 (penalidade aditiva).

## Veredito

| perfil | gates e folga | T_turno ≤ 13.3 s | G1 contra 262144 | longctx | aceitável |
|---|---|---|---|---|---|
| k2a 524288 | passa | 6.7 s | passa | 100% | **sim** |
| k2a 1000000 | passa | 9.3–9.4 s | passa em 5 suítes; HumanEval 1 abaixo da margem, dentro do ruído | 100% a 1M, 87.5% a 128K | **sim** (decisão do usuário sobre o HumanEval) |

## HumanEval com os imports do prompt (2026-10-27)

O guia público nota o HumanEval com as linhas de import do prompt na frente da resposta (`regrade_humaneval.py` do `engine-updates-2026-10`), como a rodada de outubro. A nota estrita da tabela acima falha respostas sem `from typing import List` com lógica certa. Resultado em [`humaneval-regrade.json`](humaneval-regrade.json):

| run | estrita | com imports |
|---|---:|---:|
| w1z 262144 | 142/164 | 158/164 |
| k2a 262144 | 147/164 · 151/164 | 158/164 · 159/164 |
| k2a 524288 | 147/164 | 156/164 |
| k2a 1000000 | 142/164 · 148/164 | 155/164 · 158/164 |

Com os imports, o w1z e o k2a empatam a 262144, e a diferença de 1M fica em 0 a 3 questões.
