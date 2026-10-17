# Etapa 15 — instrução de effort no fim do prompt no iQ (`n2t`) (2026-10-17, mlx-serve 26.10.1)

Runbook: [plan-effort-needles.md](../plan-effort-needles.md), Task 15. `n2t` = iQ `dafff5c` servido de um overlay de hardlinks com o template [swift15-effort-tail.jinja](../../../fixes/qwen3.8-flash-next/swift15-effort-tail.jinja) (MD5 `fe68e582…`). O overlay também troca o `chat_template` do `tokenizer_config.json`, que no iQ é igual ao `chat_template.jinja`. `n2` = o mesmo pack com o template oficial.

Controles do `n2`: `low` e `medium` rodaram nesta task, na mesma fila do `n2t` (e15/t1). O `xhigh` vem do A/B da campanha Swift ([ab/t1/n2](../../swift15-flashnext-2026-10/results/ab/t1/n2), 2026-10-10, 1 rodada), porque refazer custaria ~5 h. O LCB desse controle está no avaliador corrigido: 41 → 45 ([lcb-regrade.json](../../swift15-flashnext-2026-10/results/lcb-regrade.json)). Os LCB desta task saíram do bench2 `2403125`, que já tem a correção.

## 3e — troca de effort a 128K

| probe | braço | effort | n | resultado |
|---|---|---|---:|---|
| 3e | n2t | low | 2 | switch TTFT 0.81 s hit 1.00 |
| 3e | n2t | medium | 2 | switch TTFT 5.76 s hit 0.97 |
| 3e | n2t | xhigh | 12 | prime TTFT 83.73 s hit 0.50; control TTFT 3.04 s hit 0.98; back TTFT 0.31 s hit 1.00 |

Gate (hit ≥ 0.9): passa. Os números ficam iguais aos do `w1t` ([etapa11](etapa11-effort-tail.md)): a troca de effort custa 0.8–5.8 s em vez de 167 s, e o turno de controle custa 3.0 s.

## Obediência ao effort (GPQA + LCB, 100 questões, 1 rodada)

| effort | questões | reasoning `n2t` / `n2` (IC 90%) | dentro de ×1.25? |
|---|---:|---|---|
| xhigh | 100 | ×1.05 (0.95–1.16) | sim |
| medium (A/A) | 100 | ×1.01 (0.93–1.10) | sim |
| low | 100 | ×1.02 (0.95–1.09) | sim |

| braço | medium / xhigh (IC 90%) | low / xhigh (IC 90%) |
|---|---|---|
| n2 | ×0.41 (0.34–0.51) | ×0.26 (0.21–0.33) |
| n2t | ×0.40 (0.33–0.48) | ×0.25 (0.20–0.31) |

OBEDIENCE: pass (xhigh e low dentro de ×0.80–×1.25; suítes gpqa, livecodebench; rodadas r1). Fonte: [e15-obedience.md](e15-obedience.md), [e15-obedience.json](e15-obedience.json).

O controle `xhigh` vem de outra sessão do servidor (2026-10-10), mas o shift dele (×1.05) fica perto do A/A (×1.01).

## Acerto e custo (GPQA 50 + LCB 50, seed 42, 1 rodada)

| effort | GPQA `n2` → `n2t` | LCB `n2` → `n2t` | tempo GPQA+LCB (s) | tokens | truncadas |
| --- | --- | --- | --- | --- | --- |
| xhigh | 45 → 42 | 45 → 46 | 18136 → 19082 | 1261K → 1350K | 7 → 9 |
| medium | 41 → 40 | 44 → 43 | 3217 → 2988 | 259K → 248K | 0 → 0 |
| low | 39 → 39 | 40 → 41 | 2804 → 2641 | 194K → 185K | 0 → 0 |

Margem G1 = 3 (`passed >= base - 3`): todos passam. O GPQA `xhigh` fica no limite (42 = 45 − 3).

No GPQA `xhigh`, o `n2t` perdeu 4 questões e ganhou 1. As 4 perdidas truncaram em 65536 tokens. O `n2` acertou essas questões com 18K a 63K tokens (dataset_idx 87, 88, 97, 129); o `n2t` estourou o limite nas quatro. Na direção contrária, a questão 143 truncou no `n2` e passou no `n2t` com 59521 tokens. O `w1t` mostrou o mesmo padrão no `xhigh` (7 truncadas contra 4 em 2 rodadas).

## Veredito

As regras do plano passam: 3e com hit 0.97–1.00, obediência dentro de ×0.80–×1.25 nos três efforts, e GPQA e LCB dentro da margem em cada effort. O template com o effort no fim funciona no iQ como no Swift. Ele não vira default pelo mesmo motivo da etapa 11: em prompts curtos, o mlx-serve perde o reaproveitamento do system prompt (diagramas em [etapa11-effort-tail.md](etapa11-effort-tail.md)). Esta task não mediu o 3f no `n2t`.

## Leitura

- **O iQ pensa mais que o Swift em todos os efforts, mas o effort tem mais efeito nele.** No iQ, `low` gasta ×0.26 do reasoning do `xhigh`. No Swift, `low` gasta ×0.45.
- **O `xhigh` com o effort no fim tende a pensar um pouco mais.** Nos dois packs, o shift do `xhigh` fica acima de 1 (×1.04 no Swift, ×1.05 no iQ), e as truncadas sobem (4 → 7 no Swift em 2 rodadas, 7 → 9 no iQ em 1 rodada). Cada IC inclui 1.0, então o efeito não está confirmado. Uma hipótese, não testada: a instrução fica perto do início da geração e pesa mais.
- **No iQ em `xhigh`, o limite de 65536 tokens decide parte do GPQA.** O `n2` teve 4 truncadas no GPQA e o `n2t` 7. Um cliente com `max_tokens` maior mudaria essas notas.
