# TODO — harness das stacks do Qwen3.8-Flash-Next

Pendências do harness compartilhado (`scripts/run-candidate.sh`, `consolidate_reports.py`, `render_perf_lines.py`)
e das campanhas que o usam (`bench/engine-updates-2026-10`, `bench/qwen38-flashnext-updates-2026-10`).
Origem: revisão final da Etapa G (2026-10-09), itens Minor adiados, e perguntas que a Etapa G deixou abertas.
Marque `[x]` e cite o commit quando fechar um item.

## Harness (código)

- [ ] **Knobs herdados do ambiente.** `bench/qwen3.8-prefix-cache/scripts/run-mtplx.sh` e `run-ds4.sh` leem
  `QWEN38_MTPLX_VENDOR_DEFAULT`, `QWEN38_MTPLX_MEMORY_LIMIT`, `QWEN38_MTPLX_KV_QUANT`, `MTPLX_QSA_PREFILL` e
  `DS4_QWEN4_YARN_FACTOR` direto do env. Um chamador direto (`bench/qwen3.8-prefix-cache/scripts/run-campaign.sh`,
  `bench/qwen38-updates-2026-09/scripts/run-p2-mtplx-ab.sh`) herda o valor do shell. Fazer `unset` no topo desses
  chamadores ou documentar os knobs nos launchers.
- [ ] **`FLASHNEXT_EXEC` sem `unset`.** Se ficar exportado no shell, todo braço do `run-candidate.sh` pula o probe e
  não grava jsonl. Fazer `unset` no início do script, exceto quando o chamador (ex.: `run-quality.sh`) passa o valor
  de propósito para aquele run.
- [ ] **Comentário fora do lugar.** Em `scripts/run-candidate.sh:141`, o comentário "os dois juntos: a conta do memory
  plan só chega a 262K assim" fica na linha do m1s, mas descreve o m1xq. Mover.
- [ ] **Default do renderer reescreve a página publicada.** `render_perf_lines.py` sem `--data` usa o `reports.json`
  de setembro e grava `reports/qwen38-flashnext-perf-lines.html`, que hoje é a página de outubro. Mudar o default de
  `--data` para `bench/engine-updates-2026-10/results/reports-2026-10.json`, ou recusar gravar o perfil 2026-09 no
  arquivo publicado.
- [ ] **Legenda `est_note` incompleta.** Cita só `507` e `500`; os dados de outubro têm HTTP 400 (m1v) e
  `stream_error` (m1s). Para o ponto recusado do MTPLX a 256K, dar o motivo do fit (237 568 tokens) via
  `GROUP_NOTES[("m1", 262144, "pg")]`.

## Rótulos e dados da página

- [ ] **Mesmo comando, dois rótulos.** m1 (8K) e m1p (32K) rodam o mesmo comando (prime 64), mas o
  `MTPLX_CONFIG` do `consolidate_reports.py` rotula "default config" e "prime 64". O card do MTPLX repete a
  diferença. Rotular os dois como "prime 64".

## Re-avaliação do HumanEval (`bench/engine-updates-2026-10/scripts/regrade_humaneval.py`)

- [ ] A nota estrita vem do campo `correct` do registro, sem re-executar. Re-executar também a nota estrita.
- [ ] `fixed_by_imports` conta qualquer re-run que passa. Um timeout ou falha intermitente do run original que
  passa no re-run vira "fix por imports". Contar só os casos em que o estrito re-executado falha e o com-imports passa.
- [ ] Só as linhas de import do prompt entram. Respostas que dependem de helpers definidos no prompt
  (HumanEval/10, /38, /50) seguem reprovadas. Avaliar juntar todo o preâmbulo do prompt antes do `def` alvo.

## Medições abertas

- [ ] **Qualidade do n2 com a mesma config.** O run do n2 (2026-10-07) usou ~200 tokens por resposta; o o1 ~1 800
  e o m1x ~3 300. Rodar `bench/engine-updates-2026-10/scripts/run-quality.sh n2 131072` (tag `qual`) para uma
  comparação com o mesmo modo de reasoning. Checar antes se o mlx-serve reporta `reasoning_tokens`.
- [ ] **Qualidade do d1 (ds4).** Ficou fora da Etapa G4.
- [ ] **TTFT do `tool_turn` do d1 cresce com o contexto** (6.4 s a 128K, 20 s a 256K, 50 s a 512K) apesar do hit
  ≥ 0.94. Causa não investigada.
- [ ] **Prefill do MTPLX a 128K (274 tok/s).** Hipótese: lane densa do indexer QSA sem NAX. Não perfilado. Isolar
  com m1x a 32K (mesma config do ponto de 128K) e ler o tempo por chunk no flight recorder.
- [ ] **Banda de ~237K no MTPLX.** O fit com `--memory-limit max` é 237 568 tokens; nenhuma banda mediu perto dele.
- [ ] **Contador "MTP acc" do MTPLX (0.07).** O campo não é a taxa de aceitação; achar no log do MTPLX o contador
  certo e corrigir a extração. Hoje a página esconde a coluna para o MTPLX.
