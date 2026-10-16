# Flash-Next, próximos passos de 2026-10 — resumo da campanha (2026-10-16)

**O driver principal continua o Swift 1.5 (`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` `13839b7`) no mlx-serve 26.10.1.**
**O driver secundário continua o ddalcu iQ-MLX-4.7bpw `dafff5c` no mesmo runtime e com as mesmas flags.**

O `reasoning_effort` default continua `xhigh`. O harness deve fixar o effort por sessão: trocar o effort no meio da sessão zera o cache. O perfil `512k` do launcher passa a usar o Swift 1.5.

Rig: Mac Studio M4 Max 128 GB. Runbook: [plan.md](../plan.md). Metas e regras de cada task estão no runbook.

## Runtimes que rodaram

O plano previa versões que mudaram durante a campanha. As linhas abaixo dizem o que rodou.

| braços | runtime no plano | runtime que rodou | motivo |
| --- | --- | --- | --- |
| `n2x`, `o1rm` | mlx-serve 26.10.2-pre-release.1 | mlx-serve 26.10.2 (estável) | a estável traz o estado GDN em f32 e corrige a calibração do prefill ([research/qwen38-flashnext-updates-20261014.md](../../../research/qwen38-flashnext-updates-20261014.md)) |
| `g0`, `g1` | llama.cpp b11569 | llama.cpp b11609 | o b11600 deixa de prender a tabela PLE na GPU (**terceiro**) |
| `o1x`, `o1r`, `x1` | oMLX 0.7.1.dev1 | oMLX 0.7.1.dev2 (lançado em 2026-10-15) | ruling Task R2 do ledger |
| `g1m` | mlx-serve 26.10.2-pre (llama.cpp embutido) | não rodou | o llama.cpp embutido (b11429) não tem o fix de `mul_mat_id` do b11569 nem o fix da PLE do b11600 |

Os braços `w1`, `n2`, `w1q4` e `w1p8` rodaram no mlx-serve 26.10.1.

## Decisões

| # | teste | braços | regra | resultado | decisão | fonte |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | mlx-serve 26.10.2 × 26.10.1 no n2 | n2, n2x | ≤ 0.97× nas duas bandas | razão 1.038 a 32K e 1.000 a 128K; a 256K o 26.10.2 recusou o `tool_turn` (`PrefillDoesNotFit`) | 26.10.2 não adotado; o runtime fica 26.10.1 | [etapa1-runtime.md](etapa1-runtime.md) |
| 2 | Swift 1.5 a 256K/512K | W1, W1Q4 | gates padrão | 256K: `T_turno` 11.1 s, needles 11/13 (falha); 512K: 13.3 s, needles 13/13, livre mínimo 0.01 GB | perfil `512k` com Swift (ruling: a banda de 512K define o perfil) | [etapa2-swift-long.md](etapa2-swift-long.md) |
| 3 | bateria agêntica | W1, N2 | regras 3a–3f | 3a/3b: `w1` − `n2` = 0 casos em 20; 3c: nenhum `char_run` até ~203K; 3d: `medium` e `low` falham o G1 no LCB reavaliado (40–42 contra 47); 3e: troca de effort com hit 0.00; 3f: `w1` 36/40 e 10/12 contra 34/40 e 8/12 do `n2` | effort default `xhigh`, fixo por sessão; sessão longa liberada no `w1` | [etapa3-agent.md](etapa3-agent.md) |
| 4 | Terminal-Bench | — | — | adiado | — | — |
| 5 | Jundot refit | o1x, o1r, o1rm, W1 | paridade, G1, ≤ 0.97× | `o1rm` 1.075× e 1.046× o `w1`, needles 12/13 a 128K; `o1r`/`o1x` 1.000 e 1.034; G1 Veerman 7/12 contra 10/12 na rodada 1; 9/12 contra 8/12 na rodada 2 (16/24 contra 18/24) | o refit tem a mesma qualidade e velocidade do oQ4e antigo; com o `2615fc0` apagado, o refit fica como pack do oMLX; `o1rm` não vira driver | [etapa5-refit.md](etapa5-refit.md) |
| 6 | scottlowry Swift oQ4e | s1m, W1 | ≤ 0.97×, G1 | não rodou: `o1rm` acima de 1.03× nas duas bandas (`RUN_TASK6=0`) | — | [etapa6-scottlowry.md](etapa6-scottlowry.md) |
| 7 | mix6 v2 | x1, o1r | G1 + margem, swap 0 a 256K | G1 passa em todas as suítes; nenhuma suíte acima da margem; swap Δ 0.00 GB; wired +7.6 GB a 256K | não substitui o refit | [etapa7-mix6.md](etapa7-mix6.md) |
| 8 | GGUF + MTP | g0, g1 | smoke ≥ 70 tok/s | decode `g1` 52.1 tok/s (`g0` 36.0) | parar; pesos (99 GB) apagados do rig em 2026-10-16 | [etapa8-gguf.md](etapa8-gguf.md) |
| 9 | --ple-gpu + 8 GB | W1P8 | ≤ 0.95× a 128K | `ple gather: cpu`; headroom 16 GB fixo; bandas não rodaram | `--ple-gpu` não vira perfil opcional | [etapa9-plegpu.md](etapa9-plegpu.md) |

## Notas por task

- **Task 1.** A 32K o `n2x` tem decode 80.0 tok/s contra 84.3 do `n2`. A 128K os dois ficam em 8.9 s. A 256K o 26.10.2 pediu ~11.1 GB com ~10.0 GB livres. A causa provável é o estado GDN em f32 (ledger, Task 1).
- **Task 2.** Os erros de needle a 256K terminaram com `finish_reason=stop`. A 512K o Swift fica no mesmo limite de memória que o iQ (13.0 s, livre mínimo 0.05 GB).
- **Task 3.** Os 4 turnos vazios do `n2` no 3c chamam uma tool em vez de responder (`finish_reason=tool_calls`). Não é degeneração de texto. A causa do 3e é o template oficial: a instrução de effort fica no início do system prompt.
- **Task 5.** A diferença do `o1rm` vem do decode (74.9 contra 82.8 tok/s a 32K). A falha de paridade 1.034 a 128K no oMLX é ruído de decode: sem as respostas truncadas, a mediana fica 55.6 (`o1x`) contra 56.7 (`o1r`).
- **Task 7.** O `x1` usou `umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp` em `73d2cd0`. O umixer aposentou o repo `-v2`. Os arquivos têm o mesmo SHA de LFS do `-v2` em `ed5c722`.
- **Task 8.** A MTP dá +45% de decode sobre o `g0`, mas parte de uma base baixa. O `g1` chega a 0.07 GB livres já a 32K.
- **Task 9.** A conta do runtime é 68.2 GB de pesos + 29.8 GB de tabela + 16 GB de headroom = 114 GB. Isso passa do working set de 107.5 GB.

## Limites

- A 256K cada braço tem 1 rep, exceto o `w1` da Task 2, com 3.
- As Tasks 5 e 7 têm uma bateria t1 por braço. O Veerman tem 12 casos. A rodada 2 (2026-10-16) inverteu a diferença de 3 casos da rodada 1, então ela era ruído.
- Números de terceiros estão marcados como **terceiro** nos arquivos de etapa.
- O Terminal-Bench (Task 4) foi adiado. Ele depende de uma segunda máquina com Docker.
- O avaliador de LiveCodeBench do submódulo (`bench2.py`, `a4a95bb`) roda sem o preâmbulo de imports do LiveCodeBench oficial. Ele também passa o programa por `python -c`, que falha em entradas grandes (`E2BIG`). `scripts/lcb_regrade.py` reavalia as respostas gravadas. As decisões usam o LCB reavaliado. As notas brutas também estão nos arquivos de etapa. Nenhuma resposta aprovada virou reprovada. A correção entrou no `main` do submódulo em `2403125` (PR #3), e o ponteiro do submódulo foi atualizado para esse commit. Nas 4 respostas gravadas do Swift, o `bench2.py` novo e o `lcb_regrade.py` dão a mesma nota em todas as questões.
- O LCB publicado em campanhas anteriores está baixo pelo mesmo motivo. Na campanha do Swift, em t1, o `n2` passa de 41 para 45 e o `w1` de 42 para 47; em t0, os dois passam de 41 para 45. Os números publicados e onde foram corrigidos: [lcb-regrade-published.md](lcb-regrade-published.md).
- A sonda de velocidade (`cache_probe.py`) limita cada requisição a 4096 tokens. Em `xhigh`, algumas respostas dos braços que não são Swift bateram esse limite antes de responder. Elas contam como `trunc`, não como erro de needle. O commit `0d78dcc` acrescenta `--max-tokens` (opcional; o default 4096 fica) e grava o início da resposta nos needles errados.
- Em 2026-10-16 o usuário apagou do rig o GGUF (99 GB), o Jundot `2615fc0` (123 GB) e o mix6 (117 GB), depois das rodadas de 2026-10-16.
- A taxa de loop do `vendor_t1_xhigh` mede respostas que batem 16384 tokens sem EOS. No `story_en`, o Swift fica em 3/8 e os três packs oMLX em 5/8 (rodada 2026-10-16 do `w1`; [etapa5-refit.md](etapa5-refit.md)).
