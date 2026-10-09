# 2026-10-07 — Engines atualizadas: Flash-Next e Qwen3.8-27B contra o mlx-serve 26.10.1

> **Status (2026-10-08): concluída.** Flash-Next: o n2 (mlx-serve 26.10.1 + iQ) continua como driver; nenhum runtime atualizado chega a 0.97 × o `T_turno` dele. 27B (fechado em 128K por decisão do usuário): o oMLX 0.7.0 lidera entre os braços que passam nos gates. Veredito em [results/summary.md](results/summary.md).
>
> **Etapa F (2026-10-08): concluída.** A perda de cache do MTPLX vinha do prime do probe; com prime de 64 tokens o
> MTPLX passa (Flash-Next 8.8 s a 32K, 27B 30.2 s a 128K). O veredito do Flash-Next não muda. No 27B o mlx-dspark com
> `--prefix-cache-rungs 1024` passa a liderar (16.7 / 25.7 s). Ver
> [results/etapa-f-fixes.md](results/etapa-f-fixes.md).
>
> **Objetivo:** medir se os runtimes atualizados (MTPLX 2.12.2, oMLX 0.7.0, mlx-dspark 0.20.3,
> ds4 upstream) batem a referência no mlx-serve 26.10.1. São duas perguntas, com um veredito cada:
> o driver Flash-Next e o Qwen3.8-27B. A campanha mede velocidade, cache e memória.
> **Fora de escopo:** qualidade (HumanEval, tool-calling, Terminal-Bench), mlx-vlm 0.7.6,
> LM Studio 0.4.25, llama.cpp b11461, o fork ivanfioravanti do ds4 e a fidelidade dos packs.
>
> Campanha anterior (referência n2, protocolo, `T_turno`):
> [../qwen38-flashnext-updates-2026-10/results/summary.md](../qwen38-flashnext-updates-2026-10/results/summary.md).
> Protocolo e harness de origem: [../qwen38-flashnext-daily-driver-2026-09/plan.md](../qwen38-flashnext-daily-driver-2026-09/plan.md).

## O que mudou (web, 07/10/2026)

| Peça | No rig | Última | Mudança que importa aqui |
|---|---|---|---|
| MTPLX | 2.11.2 (`~/.local/bin`); `uv tool` 2.10.0 | **2.12.2** (03/10) | 2.11.3: decode Flash-Next 62.5 → 79.3 tok/s, prompts de 261K. 2.12.0: prefill +85% a 4K, +42% a 65K. 2.12.1: memory guard reescrito; em 128 GB o limite cai de 96 para 90 GiB (`MTPLX_MEMORY_LIMIT_BYTES=96G` restaura). |
| oMLX | 0.7.0.dev2; `uv tool` 0.6.4 | **0.7.0** (30/09) | Memory guard refeito; prefill Flash-Next mais rápido (QSA, fusões); partial block caching (prefill do turno seguinte 1174 → 37 tokens). |
| mlx-dspark | 0.18.0; `uv tool` 0.17.2 | **0.20.3** (05/10) | O ganho do speculative decoding se mantém em prompts de agente (27B 4-bit: 1.85× a 32K). |
| ds4 | fork ivanfioravanti | **antirez/ds4 upstream** | Suporta Qwen3.8 Flash Next (Metal) com `--mtp`. Usa GGUF próprio `qwen38-q4k` (165.11 GiB de arquivo, 69.74 GiB residentes, tabela n-gram BF16 de 95.37 GiB lida do disco). |

Os números acima vêm das release notes, medidos em M5 Max. Nenhum foi medido no M4 Max.

## Pesos

Comparação arquivo a arquivo entre a revisão local e o HEAD do HF em 07/10:

| Pack | Revisão local | HEAD | Arquivos mudados | Ação |
|---|---|---|---|---|
| `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw` | `dafff5c` | `dafff5c` | — | nenhuma |
| `Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed` | `6bc2f6e` | `34ae535` | `README.md` | nenhuma |
| `Jundot/Qwen3.8-Flash-Next-oQ4e-mtp` | `2615fc0` | `2615fc0` | — | nenhuma |
| `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed` | `123db8b` | `1d5087d` | `README.md`, `mtplx_runtime.json` | diretório novo @ `1d5087d`: hardlinks + o `mtplx_runtime.json` novo |
| `Jundot/Qwen3.8-27B-oQ8e-mtp` | `c99e5aa` | `c99e5aa` | — | nenhuma |
| `mlx-community/Qwen3.8-27B-8bit` | `815b83c` | `815b83c` | — | nenhuma |
| `incoai/Qwen3.8-27B-DFlash2` | `dedf8df` | `015e795` | — (só o card) | nenhuma |
| ds4 upstream `qwen38-q4k` | — | via `download_model.sh qwen38-q4k` | arquivo novo | download de 165 GiB |

Disco livre em 07/10: 512 GB. O download do ds4 só começa se o disco tiver ≥ 280 GB livres.

## Braços

| parte | braço | runtime | pesos | papel |
|---|---|---|---|---|
| Flash-Next | **n2** | mlx-serve 26.10.1 | iQ-MLX-4.7bpw @ `dafff5c` | referência, re-medida na mesma sessão |
| Flash-Next | m1 | MTPLX 2.12.2 | Youssofal Optimized-Speed @ `6bc2f6e` | candidato |
| Flash-Next | m1b | MTPLX 2.12.2 + `MTPLX_MEMORY_LIMIT_BYTES=96G` | idem | só se o m1 recusar 128K com HTTP 507 |
| Flash-Next | o1 | oMLX 0.7.0 | Jundot oQ4e-mtp @ `2615fc0` (`qwen4_ple_ssd_offload: true`) | candidato |
| Flash-Next | d1 | ds4 upstream (antirez) | `qwen38-q4k` | smoke com gate |
| 27B | **r27** | mlx-serve 26.10.1 | mlx-community 8bit @ `815b83c` + drafter DFlash2 @ `dedf8df` | referência |
| 27B | m27 | MTPLX 2.12.2 | Youssofal 27B Optimized-Speed @ `1d5087d` | candidato |
| 27B | o27 | oMLX 0.7.0 | Jundot oQ8e-mtp @ `c99e5aa` | candidato |
| 27B | s27 | mlx-dspark 0.20.3 | mlx-community 8bit @ `815b83c` + DFlash2 @ `dedf8df` | candidato |

No Flash-Next e no 27B, os candidatos comparam stacks (runtime + formato dos pesos). Eles não isolam uma
variável só ([[isolate-the-variable-when-measuring]]). O veredito escolhe uma stack, não explica a causa.
O r27 e o s27 usam os mesmos pesos e o mesmo drafter, então esse par isola o runtime.

Se o mlx-serve 26.10.1 não carregar o DFlash2 como drafter do 27B, o r27 roda sem drafter e o relatório
registra isso. A verificação fica no smoke.

## Protocolo

Mesmo harness da Etapa 1 de 2026-10: `run-candidate.sh` → `cache_probe.py` → `summarize_driver.py`.
Cenários `cold → identical → append → tool_turn → middle_mutation`. Perfil do probe: `temperature=1.0`,
`top_p=0.95`, `top_k=20`, reasoning `xhigh`, limite 4096 tokens. Config de servidor de cada runtime:
MTP ligada, prefix cache equivalente a 16 GB RAM / 100 GB disco onde o runtime tiver o knob, KV sem
quantização até 256K.

**Funil de bandas:**

1. **Smoke 8K** (1 rep, `cold,identical,tool_turn`) em todos os braços. Confere carga, `/props` ou
   equivalente, e telemetria de MTP.
2. **32K e 128K**, 3 reps, em todos os braços que passaram no smoke.
3. **256K**, 1 rep, em quem passou nos gates a 128K.
4. **512K**, 1 rep, via YaRN 2.0 (`--kv-quant 8` onde existir), no n2, no líder Flash-Next (se não for o
   n2) e no líder 27B. Um runtime sem YaRN não entra; o relatório registra o motivo.

**Gate do d1:** smoke a 32K, 1 rep. O d1 só entra no funil se o decode quente passar de 70 tok/s.

**Ordem:** parte Flash-Next completa (veredito e commit), depois a parte 27B. Dentro de cada banda, a
ordem dos braços alterna entre bandas, como na Etapa 1 (32K: ref → candidatos; 128K: candidatos → ref).

**Higiene:** um servidor por vez; porta livre antes de cada braço; 10 min ociosos entre bandas;
`~/.mlx-serve/kv-cache` e os caches de disco dos outros runtimes limpos entre braços.

## Gates

Os mesmos da campanha anterior: zero HTTP 4xx/5xx; needles corretas; hit ≥ 0.90 em `append` e
`tool_turn` a partir de 32K; swap delta ≤ 0.5 GB; telemetria de MTP presente. O alerta `wired>102`
não é gate.

## Critérios de decisão

- **Flash-Next:** um candidato substitui o n2 só se passar nos gates e tiver
  `T_turno ≤ 0.97 × T_turno(n2)` a 32K e a 128K. Empate (±3%) mantém o n2.
- **27B:** os braços são ranqueados por `T_turno` a 32K e 128K. O relatório declara o líder e a margem
  dele sobre o r27. A campanha não decide papel de agente para o 27B, porque não mede qualidade.
- **Runtime promovido:** o symlink em `~/.local/bin` só muda para um runtime que vencer uma das partes.

## Limitações

- Sem qualidade: um vencedor em velocidade pode responder pior. Promover um runtime novo no driver
  diário exige, depois, a qualidade barata da campanha anterior.
- 256K e 512K com 1 rep: leitura de capacidade, não de ranking.
- O cold do 27B a 512K pode passar de 1 h por braço (128K levou ~14 min no MTPLX 2.11 em agosto).

## Entregáveis

- `results/etapa0-smoke.md` (smoke e gate do d1)
- `results/flashnext-summary.md` (veredito Flash-Next)
- `results/27b-summary.md` (ranking 27B)
- `results/summary.md` (as duas respostas na primeira frase)
- Se houver promoção: launcher, card do modelo e memória atualizados.

## Etapa F — A/B das correções (2026-10-08)

> Pedido do usuário depois do veredito: testar as correções achadas na web
> ([results/fixes-research.md](results/fixes-research.md)). A Etapa F não muda o veredito acima sem dado novo.

Um knob por braço contra o braço original da campanha ([[isolate-the-variable-when-measuring]]). Mesmo protocolo:
3 reps, perfil do probe igual, gates iguais, tag `fx`.

| braço | base | knob | banda | problema que testa |
|---|---|---|---|---|
| m1t | m1 | `MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0` | 32K | MTPLX sem reuso (#567) |
| m1h | m1 | probe manda `x-mtplx-session-id` por conversa | 32K | MTPLX sem identidade de sessão |
| m1th | m1 | os dois knobs acima | 32K | soma dos dois |
| r27b | r27 | `--draft-block-size 5` | 32K e 128K | queda de decode do DFlash2 |
| s27g | s27 | `--no-memory-guard` | 32K | `append` com hit 0.87 |
| m1p | m1 | prime do probe com `max_tokens` 64 (default 1) | 32K | prime classificado como tarefa de background |
| m1hp | m1 | header de sessão + prime com 64 tokens | 32K | cliente com formato de agente |
| m27f | m27 | o knob MTPLX vencedor | 128K | só se algum m1* passar nos gates a 32K |

O header de sessão do m1h é um id por conversa do probe (`<session-id>-<cenário>-<rep>`), igual para o prime e o
pedido medido. É o que um cliente de agente manda. O braço muda o cliente, não o servidor.

**Leitura:**

- Um knob "corrige" o problema quando o braço passa no gate que o original falhou, na mesma banda.
- MTPLX: se um m1* passar nos gates, compare o `T_turno` com o n2 (8.2 s a 32K). O teto de 128K (HTTP 507) fica fora
  da Etapa F: a única saída conhecida (KV q8) muda uma segunda variável.
- r27b: compare decode e `T_turno` com o r27 nas duas bandas.
- s27g: se passar no gate, o s27 vira o líder do 27B por `T_turno`; o relatório diz isso.

**Ruling (2026-10-08, depois do m1h):** o m1h recebeu HTTP 503 `session_busy` em 4 primes. No código do 2.12.2
(`engine_session.is_background_request`), um pedido sem histórico, com `max_tokens` ≤ 48 e system prompt diferente do
da sessão principal é tarefa de background (o formato de um job de título do Open WebUI). O prime do probe tem
`max_tokens` 1 e o system prompt muda a cada rep, então cai nessa regra: sem header, roda sem sessão; com header, recebe
503 enquanto o turno anterior grava. Os braços m1p e m1hp isolam esse efeito; o m1th saiu da rodada (teria os mesmos
503). O probe ganha `--prime-max-tokens`, com default 1 nos outros braços.

Fora da Etapa F: ds4 `--mtp-draft`, n2 512K com prefix cache menor, `max_tokens` do probe, PR #754 (sem release).

Entregável: `results/etapa-f-fixes.md`, memória e `results/summary.md` atualizados.

## Etapa G — dados para a página perf-lines (2026-10-09)

> Pedido do usuário: atualizar `reports/qwen38-flashnext-perf-lines.html` com a stack de outubro. llama.cpp fica de
> fora. Plano de execução: `docs/superpowers/plans/2026-10-09-flashnext-page-etapa-g.md`.

**Séries da página:** n2 (mlx-serve 26.10.1 + iQ, driver), o1 (oMLX 0.7.0), MTPLX 2.12.2 (melhor config que
passar), d1 (ds4 upstream) e c1 (mlx-serve 26.9.2, referência de setembro). c2, c3 e c4 saem do gráfico.

**Medições que faltam** (protocolo da campanha, tag `pg`; métricas: `T_turno`, TTFT cold e quente, decode, prefill,
hit por cenário, aceitação da MTP, wired de pico, memória livre mínima, swap):

| bloco | braço | bandas | reps |
|---|---|---|---|
| G1 · 8K completo | n2, o1, m1, d1 | 8K | 3 |
| G2 · MTPLX ao máximo | m1v (config padrão do vendor) | 128K | 1, depois 3 se passar |
| | m1x (`--memory-limit max`) | 128K | só se o m1v recusar |
| | m1q (`--paged-kv-quantization q8`) | 128K, 256K | só se o m1x recusar; 3 reps a 128K, 1 a 256K |
| G3 · ds4 até 512K | d1 | 128K (3), 256K (1), 512K com `DS4_QWEN4_YARN_FACTOR=2` (1) | — |

O m1 da G1 já usa o prime de 64 tokens (default dos braços MTPLX desde `0eb4988`). Os m1* da G2 também.

**Regras:**

- Um knob por braço; a página rotula cada ponto MTPLX com a config que o produziu (ex.: "KV q8").
- O d1 a 512K roda com YaRN 2 (`DS4_QWEN4_YARN_FACTOR=2`); o rótulo diz isso, como o n2 a 512K (YaRN 2 + KV 8-bit).
- Recusa (HTTP 4xx/5xx, `PrefillDoesNotFit`) é dado: o ponto aparece como "refused" com o motivo.
- O driver diário fica parado durante as medições e volta no fim.

**Página (G5):** o consolidador lê os diretórios das campanhas de setembro e de outubro. Ele escolhe, por série e
banda, o grupo canônico de maior rep. A página ganha:

- chip e versões em destaque, com a data;
- a nota de que números públicos (M5 Max, M3 Ultra) não se comparam com os do M4 Max, e de que o prefill relativo
  oMLX × mlx-serve muda com o chip (mlx-serve issue #658);
- a nota do prime de 64 tokens no MTPLX;
- o aviso "speed, cache and memory only; no agent reliability", com o link do teste do zenn;
- texto em inglês (regra do site).

**G4 (opcional) · qualidade barata:** HumanEval 164 + tool-calling jdhodges 40 + Veerman 12, temp 0, para o1 e o
melhor MTPLX, no formato de `quality-n1-n2.md`. Detecta só regressão grande de pesos; não mede a corrupção de KV
multi-turno que o zenn relatou.

**Entregável:** página regenerada, `results/etapa-g-page.md`, PR separado do #48.
