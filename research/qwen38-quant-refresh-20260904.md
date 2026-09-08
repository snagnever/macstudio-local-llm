# 2026-09-04 — Revisão das quantizações Qwen3.8 para o M4 Max 128 GB

Consulta ao Hugging Face em 05/09 UTC (04/09 no rig). Somente metadados/cards; nenhum peso baixado ou substituído.

## Packs já usados

Comparação de revisão remota com os snapshots pinados: [evidência JSON](../bench/qwen38-flash-next/results/quant-refresh-20260904.json).

- Densa MTPLX Optimized-Speed: `123db8b` → `766cec2`; Optimized-Quality: `09f71b3` → `35ec534`. Em ambos, somente `mtplx_runtime.json` mudou em 03/09: referência ao trunk por ID do Hub e remoção de caminhos locais do autor. Hashes de pesos, tokenizer e demais arquivos iguais. Não é uma nova quantização.
- Densa mlx-community 8bit, True2456 AWQ 5.0bpw, Jundot oQ8e-mtp e ddalcu 8bit: revisões iguais às locais.
- Flash-Next ddalcu mixed-4/8 (`ef5b919`) e Jundot oQ4e-mtp (`2615fc0`): revisões iguais às locais.

## Alternativas consultadas

- [MTPLX Flash-Next Optimized-Speed](https://huggingface.co/Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed): pack existente de 28/08, updates de 30/08 apenas no README; 115.1 GB segundo o card, ~83 GB residente mais working set com n-gram em SSD. É candidato a comparar com ddalcu agora que MTPLX 2.11.1 foi instalado, não atualização dos pesos ddalcu. Não medido no rig.
- [Flash-Next oQ6e](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-oQ6e-mtp) e [oQ8e](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-oQ8e-mtp), publicados em 31/08: repositórios ~150.47 e ~194.89 GB respectivamente. Cards mostram menor decode que oQ4e em M3 Ultra 256 GB; não apresentam avaliação ampla de qualidade. Não priorizar no rig 128 GB sem planejar memória/offload e demonstrar benefício.
- [mlx-community Flash-Next 4bit](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-4bit), 02/09, ~111.55 GB: conversão g32 com correção da dupla aplicação de offset RMSNorm no fluxo mlx-vlm. Não é atualização direta do pack ddalcu nem evidência de que o nosso esteja afetado. Card valida integridade dos norms e saída coerente.
- [ivanfioravanti Flash-Next DS4 Q4](https://huggingface.co/ivanfioravanti/Qwen3.8-Flash-Next-DS4-Q4), 04/09: experts Q4_K/imatrix e down MXFP4, projeções densas Q8; base+MTP 74.9 GB e PLE separado 30.5 GB (~105.4 GB para rodar com MTP). Requer runtime/branch DS4 próprio. Autor reporta ~87 GiB a 262K e MTP 45.2 tok/s nesse contexto, medidos em M3 Ultra 512 GB. Candidata experimental, não substituta comprovada. Sua avaliação de drift em continuações curtas não equivale a Terminal-Bench.

## Recomendação

Manter pesos atuais da densa e ddalcu mixed-4/8 do Next. Não há atualização de pesos obrigatória nas opções já usadas. Prioridade de novo A/B: Next MTPLX Optimized-Speed + 2.11.1 contra ddalcu + mlx-serve 26.9.1, depois DS4 se a meta for contexto longo. Não atribuir qualidade campeã sem avaliações funcionais comparáveis; as evidências locais atuais sustentam velocidade/cache e smoke, não vitória geral em agente.
