# 2026-10-06 — Qwen3.8-Flash-Next: updates de runtime e de pesos do driver diário

> **Objetivo:** decidir se o driver diário troca de runtime (mlx-serve 26.9.2 → 26.10.1) e de pesos
> (ddalcu `mixed-4-8bit` → `iQ-MLX-4.7bpw`). São duas perguntas, medidas em dois A/B com uma
> variável cada ([[isolate-the-variable-when-measuring]]).
> **Fora de escopo:** Terminal-Bench, MTPLX 2.12.x, oMLX 0.7.0, contexto acima de 128K, e o
> efeito do 26.9.6 sobre o thinking de turnos anteriores (ver "Limitações").
>
> Campanha anterior (protocolo, harness, `T_turno`):
> [../qwen38-flashnext-daily-driver-2026-09/plan.md](../qwen38-flashnext-daily-driver-2026-09/plan.md).
> Plano de execução (tasks, scripts, testes):
> [docs/superpowers/plans/2026-10-06-qwen38-flashnext-updates-2026-10.md](../../docs/superpowers/plans/2026-10-06-qwen38-flashnext-updates-2026-10.md).

## O que mudou (web, 06/10/2026)

| Peça | No rig | Última | Fonte |
|---|---|---|---|
| mlx-serve | 26.9.2 (MLX 0.32.2) | **26.10.1** (01/10), asset `mlx-serve-bin-macos-arm64.tar.gz`, SHA256 `e53056e481364ff72188fafea8b3eb0aeb0b5b7cebcd6e6e7d26bf1ce4223873` | [releases](https://github.com/ddalcu/mlx-serve/releases) |
| Pesos | `ddalcu/…-mixed-4-8bit` @ `ef5b919` | **`ddalcu/…-iQ-MLX-4.7bpw` @ `dafff5c`** (01/10). O `mixed-4-8bit` foi descontinuado em 06/10 (commit `3191916`, só README). | [card iQ](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw) |

Deltas declarados entre 26.9.2 e 26.10.1 que tocam o driver (a validar, não a assumir):

- 26.9.3: decode MoE 54.3 → 56.3 tok/s no M4 Max; sem queda da MTP entre 16K e 32K; prefill em
  passos de 8192 (+8%); `--kv-quant turbo2/turbo4` removidos.
- 26.9.4: hit de cache dá a mesma saída greedy que o cold; `/props` mostra os settings em vigor.
- 26.9.6: lookup drafting da MTP ligado por default (`MLX_SERVE_MTP_LOOKUP=0` desliga); o thinking de
  turnos anteriores não entra mais no prompt.
- 26.10.1: MTP +5–8% no M4 Max; +12% acima de 32K; `--ple-gpu` opcional (decode +15% a 128K,
  carrega a tabela n-gram de 32 GB na memória); correção do loop do lookup drafting.

O `iQ-MLX-4.7bpw` tem o mesmo layout e os mesmos 75 GB do `mixed-4-8bit`. A diferença é a calibração
dos experts com importance matrix. Publicado (não medido): top-1 contra bf16 88.6% contra 87.9%, KLD
mediana 0.0052 contra 0.0066, code 96.0 contra 88.0, prose 81.2 contra 87.0, em 290 posições. O
`ngram_table.bin` é idêntico nos dois packs (LFS SHA256 `c8ab74bc…51d2`, 32 000 153 976 bytes).

## Braços

| braço | pesos | runtime | papel |
|---|---|---|---|
| **c1** | `mixed-4-8bit` @ `ef5b919` | mlx-serve 26.9.2 | incumbente, re-medido na mesma sessão |
| **n1** | `mixed-4-8bit` @ `ef5b919` | mlx-serve 26.10.1 | A/B de runtime: c1 × n1 |
| **n2** | `iQ-MLX-4.7bpw` @ `dafff5c` | mlx-serve 26.10.1 | A/B de pesos: n1 × n2 |
| n2p (opcional) | `iQ-MLX-4.7bpw` @ `dafff5c` | mlx-serve 26.10.1 + `--ple-gpu` | A/B de flag: n2 × n2p |

Os quatro braços usam a config c1: `--mtp`, `--ssm-checkpoint-max 16`, prefix cache 16GB/100GB/64,
KV sem quantização. Só a coluna "papel" muda entre dois braços comparados.

## Protocolo

Harness e métrica iguais aos da campanha anterior: `cache_probe.py`, fixture `audit_retrieval`,
needles 10/50/90, perfil do vendor (`temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning xhigh,
limite 4096 tokens), MTP on. Métrica de manchete:
`T_turno = TTFT do tool_turn + 512 / mediana do decode quente (identical, append, tool_turn)`.

- **Etapa 0 — smoke a 8K.** n1 e n2, `cold,identical,tool_turn`, 1 rep. Prova que o binário carrega
  os dois packs, que o log tem `[spec-stats]` (MTP ativa) e que o `/props` responde.
- **Etapa 1 — A/B de velocidade.** c1, n1 e n2 a **32768** e **131072**, 5 cenários, 3 reps
  (`middle_mutation` 1 rep). Ordem a 32K: c1 → n1 → n2. Ordem a 128K: n2 → n1 → c1. A ordem
  invertida dilui deriva térmica e de page cache. Uma banda fecha na mesma sessão.
- **Etapa 2 — sinal barato de qualidade dos pesos.** n1 e n2 no daily launcher (128K, mesmos flags),
  HumanEval 164 e tool-calling jdhodges 40 + Veerman 12, temp 0. Só detecta regressão grande: 164
  problemas não separam 0.7 pp de top-1.
- **Etapa P (opcional) — `--ple-gpu`.** n2p a 32K e 128K, 3 reps, contra o n2 da Etapa 1.
  Roda só depois do veredito das Etapas 1 e 2.

Higiene herdada: limpar `~/.mlx-serve/kv-cache` antes de cada `cold` (o `run-candidate.sh` faz),
memória livre ≥ 82 GB antes de subir um braço, GPU < 50 °C entre bandas. O `run-candidate.sh` mata
o que escuta na porta 11234: parar o daily driver antes de começar.

## Critérios de decisão

Gates (iguais aos da campanha anterior), por braço, a 32K e 128K: hit ≥ 0.90 em `append` e
`tool_turn`; needles corretas (truncado não é falha); swap delta ≤ 0.5 GB; zero HTTP 4xx/5xx;
`[spec-stats]` presente no log. Wired acima de 102 GB é alerta, não gate.

- **Runtime (c1 × n1):** promover o 26.10.1 se o n1 passa nos gates e o `T_turno` do n1 é ≤ 1.03 ×
  o do c1 nas duas bandas. O TTFT é determinístico entre reps e o decode varia até ±12%, então 3% é
  o limite de "paridade". Se o n1 ganha mais de 3% numa banda, registrar o ganho.
- **Pesos (n1 × n2):** adotar o `iQ` se o n2 passa nos gates, o `T_turno` do n2 fica a ±3% do n1
  nas duas bandas, o HumanEval do n2 ≥ n1 − 2 problemas e o tool-calling do n2 ≥ n1 − 1 caso. A
  justificativa da troca é: paridade no rig, KLD publicado melhor e o pack antigo sem updates. A
  campanha não mede a fidelidade; o `summary.md` diz isso.
- **`--ple-gpu` (n2 × n2p):** vira perfil opcional só se o `T_turno` a 128K cai ≥ 5%, swap ≤ 0.5 GB e
  nenhum cenário é recusado. Não entra no perfil 512k sem uma sonda própria.

## Limitações

- O `cache_probe.py` não reenvia thinking no `tool_turn` (a mensagem do assistant só tem
  `tool_calls`), e o `tool_loop.py` só faz rodadas de tool. Então nenhum dos dois mede a mudança do
  26.9.6 ("o thinking de turnos anteriores não entra no prompt"). Num agente real, um turno novo do
  usuário depois de um turno com thinking pode re-prefilar a partir do último assistant. Isso fica
  para o uso diário observado (`reports/opencode-metrics.html`), não para esta campanha.
- O perfil 1M documentado com `--kv-quant turbo4` deixa de existir no 26.10.1. O perfil 512k usa
  `--kv-quant 8` e continua válido, mas não é re-medido aqui.

## Entregáveis

- `results/<braço>-<ctx>-t1.0-ab.jsonl`, `results/<braço>-8192-t1.0-smoke.jsonl`,
  `results/props/<nome>.json` (snapshot do `/props`).
- `results/quality-n1-n2.md`: HumanEval e tool-calling lado a lado, por problema discordante.
- `results/summary.md`: veredito em prosa, tabela por banda com `T_turno`, cold TTFT, warm TTFT do
  `tool_turn`, hit, decode, wired, needles.
- Se promovido: card [docs/models/qwen3.8-flash-next.md](../../docs/models/qwen3.8-flash-next.md),
  launcher [tools/scripts/serve-flashnext-daily-driver.sh](../../tools/scripts/serve-flashnext-daily-driver.sh)
  e symlink `~/.local/bin/mlx-serve` atualizados. Rollback: symlink de volta para
  `mlx-serve-v26.9.2` e `FLASHNEXT_MODEL` apontando para o pack `ef5b919`.
