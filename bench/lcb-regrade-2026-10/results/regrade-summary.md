# Reavaliação do LiveCodeBench — resultados (2026-10-14)

Runner corrigido: prelúdio de imports do harness oficial e programa rodando de arquivo temporário (ver
[`../plan.md`](../plan.md)). Execução no rig com o `bench2.py` de `a4a95bb`. Os veredictos por questão estão em
[`verdicts.json`](verdicts.json).

## Resumo

- 96 respostas passam de falha para acerto. Nenhuma passa de acerto para falha.
- Causas: 60 `NameError` no teste 0 (nome do prelúdio, em geral `List` de `typing`) e 36
  `[Errno 7] Argument list too long`.
- Nenhuma virada vem de timeout. Uma resposta truncada continua errada.
- A soma original de cada modelo reproduz a nota publicada (por exemplo 27b 62%, gemma @6bit 80%,
  coder-next 56%, Q3_K_S 72%). A regra de junção (resposta mais recente por questão) é a mesma dos cards.
- As notas reavaliadas ficam perto das referências da comunidade que
  `reports/quality-benchmarks-charts.html` já cita: coder-next 84% (comunidade ~80%), 27b 88% (comunidade ~84%).

## Nota por modelo (rodada de 50 questões mais reexecuções)

| run | questions | original | regraded | to pass | to fail | causes of the change |
|---|---:|---:|---:|---:|---:|---|
| agents-a1-xl (MLX) | 50 | 32/50 (64%) | 41/50 (82%) | 9 | 0 | fail_test0 ×8, Errno 7 ×1 |
| deepseek-v4-flash 2bit-DQ (MLX) | 50 | 3/50 (6%) | 7/50 (14%) | 4 | 0 | fail_test0 ×4 |
| deepseek-v4-flash IQ2_XS (GGUF, partial) | 7 | 6/7 (86%) | 6/7 (86%) | 0 | 0 |  |
| gemma-4-26b-a4b @4bit | 50 | 33/50 (66%) | 38/50 (76%) | 5 | 0 | fail_test0 ×3, Errno 7 ×2 |
| gemma-4-26b-a4b @6bit | 50 | 40/50 (80%) | 44/50 (88%) | 4 | 0 | fail_test0 ×2, Errno 7 ×2 |
| gemma-4-31b | 50 | 38/50 (76%) | 45/50 (90%) | 7 | 0 | Errno 7 ×4, fail_test0 ×3 |
| gemma-4-e4b | 50 | 34/50 (68%) | 37/50 (74%) | 3 | 0 | Errno 7 ×3 |
| minimax-m2.5 (MLX, aborted) | 38 | 26/38 (68%) | 29/38 (76%) | 3 | 0 | Errno 7 ×3 |
| minimax-m2.5 Q3_K_S (GGUF) | 50 | 36/50 (72%) | 39/50 (78%) | 3 | 0 | Errno 7 ×3 |
| qwen3.6-27b | 50 | 31/50 (62%) | 44/50 (88%) | 13 | 0 | fail_test0 ×12, Errno 7 ×1 |
| qwen3.6-35b-a3b @6bit | 50 | 27/50 (54%) | 41/50 (82%) | 14 | 0 | fail_test0 ×13, Errno 7 ×1 |
| qwen3-coder-next | 50 | 28/50 (56%) | 42/50 (84%) | 14 | 0 | fail_test0 ×14 |
| swift15 A/B t0 n2 | 50 | 41/50 (82%) | 45/50 (90%) | 4 | 0 | Errno 7 ×4 |
| swift15 A/B t0 w1 | 50 | 41/50 (82%) | 45/50 (90%) | 4 | 0 | Errno 7 ×4 |
| swift15 A/B t1 n2 | 50 | 41/50 (82%) | 45/50 (90%) | 4 | 0 | Errno 7 ×4 |
| swift15 A/B t1 w1 | 50 | 42/50 (84%) | 47/50 (94%) | 5 | 0 | Errno 7 ×4, fail_test0 ×1 |

`fail_test0` nesta coluna é sempre `rc=1` com `NameError`. O Swift 1.5 da campanha
`bench/flashnext-next-steps-2026-10` (xhigh 43 → 47, medium 27 → 41, pacote iQ 41 → 45) não entra aqui: os
JSONL estão só no rig, fora do repositório.

## Nota por arquivo

| file | rows | original | regraded | to pass | to fail |
|---|---:|---:|---:|---:|---:|
| `swift15/ab/t0/n2/livecodebench.jsonl` | 50 | 41 | 45 | 4 | 0 |
| `swift15/ab/t0/w1/livecodebench.jsonl` | 50 | 41 | 45 | 4 | 0 |
| `swift15/ab/t1/n2/livecodebench.jsonl` | 50 | 41 | 45 | 4 | 0 |
| `swift15/ab/t1/w1/livecodebench.jsonl` | 50 | 42 | 47 | 5 | 0 |
| `runs/_Users_vitor_.lmstudio_models_mlx-community_DeepSeek-V4-Flash-2bit-DQ_20260531_020641.jsonl` | 50 | 3 | 7 | 4 | 0 |
| `runs/agents-a1-xl-mlx_20260704_221932.jsonl` | 50 | 32 | 41 | 9 | 0 |
| `runs/deepseek-v4-flash-iq2xs_20260705_164011.jsonl` | 7 | 6 | 6 | 0 | 0 |
| `runs/gemma-4-26b-a4b-it-mlx@4bit_20260520_162943.jsonl` | 50 | 32 | 37 | 5 | 0 |
| `runs/gemma-4-26b-a4b-it-mlx@4bit_20260524_133314.jsonl` | 9 | 1 | 1 | 0 | 0 |
| `runs/gemma-4-26b-a4b-it-mlx@6bit_20260521_202147.jsonl` | 50 | 39 | 43 | 4 | 0 |
| `runs/gemma-4-26b-a4b-it-mlx@6bit_20260524_153026.jsonl` | 4 | 1 | 1 | 0 | 0 |
| `runs/gemma-4-31b-it-mlx_20260522_094125.jsonl` | 50 | 38 | 45 | 7 | 0 |
| `runs/gemma-4-e4b-it-mlx_20260522_151009.jsonl` | 50 | 34 | 37 | 3 | 0 |
| `runs/minimax-m2.5_20260704_133646.jsonl` | 16 | 10 | 12 | 2 | 0 |
| `runs/minimax-m2.5_20260704_152521.jsonl` | 11 | 9 | 9 | 0 | 0 |
| `runs/minimax-m2.5_20260704_165910.jsonl` | 11 | 7 | 8 | 1 | 0 |
| `runs/qwen3.6-27b_20260523_003246.jsonl` | 9 | 4 | 8 | 4 | 0 |
| `runs/qwen3.6-27b_20260523_092939.jsonl` | 5 | 3 | 5 | 2 | 0 |
| `runs/qwen3.6-27b_20260523_104610.jsonl` | 4 | 1 | 3 | 2 | 0 |
| `runs/qwen3.6-27b_20260523_230817.jsonl` | 3 | 2 | 2 | 0 | 0 |
| `runs/qwen3.6-27b_20260524_004542.jsonl` | 3 | 3 | 3 | 0 | 0 |
| `runs/qwen3.6-27b_20260524_014640.jsonl` | 3 | 3 | 3 | 0 | 0 |
| `runs/qwen3.6-27b_20260524_022225.jsonl` | 3 | 1 | 3 | 2 | 0 |
| `runs/qwen3.6-27b_20260524_025559.jsonl` | 3 | 3 | 3 | 0 | 0 |
| `runs/qwen3.6-27b_20260524_035728.jsonl` | 3 | 1 | 1 | 0 | 0 |
| `runs/qwen3.6-27b_20260524_051417.jsonl` | 3 | 3 | 3 | 0 | 0 |
| `runs/qwen3.6-27b_20260524_062225.jsonl` | 3 | 2 | 3 | 1 | 0 |
| `runs/qwen3.6-27b_20260524_070516.jsonl` | 3 | 1 | 3 | 2 | 0 |
| `runs/qwen3.6-27b_20260524_082224.jsonl` | 3 | 2 | 2 | 0 | 0 |
| `runs/qwen3.6-27b_20260524_095356.jsonl` | 2 | 2 | 2 | 0 | 0 |
| `runs/qwen3.6-35b-a3b@6bit_20260522_182159.jsonl` | 24 | 11 | 20 | 9 | 0 |
| `runs/qwen3.6-35b-a3b@6bit_20260522_210336.jsonl` | 22 | 13 | 17 | 4 | 0 |
| `runs/qwen3.6-35b-a3b@6bit_20260522_232735.jsonl` | 4 | 3 | 4 | 1 | 0 |
| `runs/qwen3.6-35b-a3b@6bit_20260524_123328.jsonl` | 1 | 0 | 0 | 0 | 0 |
| `runs/qwen_qwen3-coder-next_20260522_173911.jsonl` | 50 | 28 | 42 | 14 | 0 |
| `runs/qwen_qwen3-coder-next_20260524_124855.jsonl` | 1 | 0 | 0 | 0 | 0 |
| `runs/unsloth_minimax-m2.5_20260705_200751.jsonl` | 50 | 34 | 37 | 3 | 0 |
| `runs/unsloth_minimax-m2.5_20260706_004651.jsonl` | 2 | 0 | 0 | 0 | 0 |
| `runs/unsloth_minimax-m2.5_20260706_090036.jsonl` | 5 | 2 | 2 | 0 | 0 |

Excluídos: `.archived_failed_livecodebench_qwen3.6-27b_20260522_235202.jsonl` (rodada descartada) e
`livecodebench_minimax-m2.5_20260704_143737.jsonl` (vazio).

## Rodadas publicadas sem respostas salvas

Estas notas vêm do mesmo runner, mas só o resumo existe. Nem o repositório nem o rig guardam o JSONL com
`raw_response`. Elas não podem ser reavaliadas; trate cada uma como limite inferior.

| Rodada | Nota publicada | Onde |
|---|---|---|
| minimax-m2.5 UD-IQ2_M | 76% (38/50) @32k | `docs/models/minimax-m2.5.md`, `bench/minimax-m2.5/results/*_summary.json` |
| qwen3.5-122b-a10b Q4_K_S | 62% (31/50) | `docs/models/qwen3.5-122b-a10b.md` |
| deepseek-v4-flash UD-Q2_K_XL | 56% bruto, 73,7% | `bench/deepseek-v4-flash/results/udq2kxl-campaign-log.md` |
| deepseek-v4-flash 0731 (ds4) | 56% bruto, 78% thinking HIGH | `bench/deepseek-v4-flash/results/0731-ds4-campaign-log.md` |

## Números publicados que mudam

Nenhum destes arquivos foi editado. A coluna "proposta" é a edição sugerida, à espera de aprovação.

### Cards em `docs/models/`

| Arquivo:linha | Hoje | Proposta |
|---|---|---|
| `docs/models/README.md:15` | gemma-4-26b-a4b **80%** @6bit / 66% @4bit | 88% @6bit / 76% @4bit |
| `docs/models/README.md:23` | minimax LCB 72% @60k (68% @32k) | 78% @60k (74% @32k) |
| `docs/models/README.md:25` | agents-a1-xl LCB 64% | 82% |
| `docs/models/README.md:26` | gemma-4-31b LCB 76% | 90% |
| `docs/models/README.md:33` | qwen3.5-122b "LCB 62% exact tie with 27B" | 27B passa a 88%; o 122B não tem respostas salvas, então o empate deixa de valer |
| `docs/models/gemma-4-26b-a4b/README.md:4,61` | @6bit 80%, "rig ceiling", +18 pp sobre o 27b (62%) | 88%; empata com o 27b (88%); o teto do rig passa a ser o gemma-4-31b (90%) |
| `docs/models/gemma-4-26b-a4b/README.md:61,73,123` | @4bit 64 → 66%; @6bit 78 → 80% (Step B) | @4bit 74 → 76%; @6bit 86 → 88% |
| `docs/models/gemma-4-26b-a4b/README.md:20` | "local LCB v6 n=50 subset scored 80" | 88 |
| `docs/models/gemma-4-26b-a4b/README.md:75` | "@6bit drops from 1st (80%)" | não é mais 1º no LCB: 31b 90%, 26b@6bit e 27b 88% |
| `docs/models/gemma-4-31b.md:61,73` | 76%, −2 contra o teto de 80% | 90%, +2 contra o @6bit (88%); vira o maior LCB do rig fora o Swift 1.5 |
| `docs/models/gemma-4-e4b.md:57` | 68% contra 80%, −12 | 74% contra 88%, −14 |
| `docs/models/agents-a1-xl.md:58,110` | 64% (32/50), "> 27b 62 / coder-next 56 / 35b-a3b 54, < gemma@6bit 80 / gemma-31b 76" | 82% (41/50); < 31b 90, 27b 88, @6bit 88, coder-next 84; empata com o 35b-a3b (82) |
| `docs/models/agents-a1-xl.md:77` | gate "LCB ≥ ~62% (beat 27b)": passa por 64 contra 62 | **o gate muda**: 82 contra 88 não bate o 27b; com MMLU 82% < 85%, o gate falha |
| `docs/models/qwen3-coder-next.md:59,150` | 56% | 84% |
| `docs/models/qwen3-coder-next.md:67,74` | "LCB rank 5th"; "@6bit holds the LCB ceiling (80% vs 56%)" | 4º (84%); 31b 90% contra 84% |
| `docs/models/qwen3.6-27b.md:86,138` | 62%, "+6 pp over coder-next; rig ceiling is @6bit at 80%" | 88%, +4 pp sobre o coder-next; empata com o @6bit |
| `docs/models/qwen3.6-27b.md:103,104` | "only Phase 1 model to clear 60%"; "LCB recommendation diverges to gemma @6bit" | os três da Fase 1 passam de 80%; a recomendação de LCB não diverge mais (empate 88/88) |
| `docs/models/qwen3.6-35b-a3b.md:87,139` | 54% (27/50), "ceiling ~66% with cap ≥ 96k" | 82% (41/50); o teto estimado sobe para ~94% |
| `docs/models/qwen3.6-35b-a3b.md:103,116` | "6th on LCB (54%)", "54% as the defensible floor" | 82%; ver a nova ordem |
| `docs/models/qwen3.5-122b-a10b.md:5,76,168` | 62% "exact tie" com o 27b | o 27b passa a 88%; o 122b fica como limite inferior (sem respostas salvas) |
| `docs/models/minimax-m2.5.md:75,79,116` | IQ2_M 76% "beats Q3_K_S's 68% raw AND its 72% @60k", "LCB +8" | Q3_K_S passa a 74% @32k e 78% @60k; o IQ2_M (76%) não pode ser reavaliado, então a conclusão "IQ2_M bate o Q3_K_S no LCB" fica sem suporte |
| `docs/models/minimax-m2.5.md:5,115,157` | 68% → 72% | 74% → 78% |
| `docs/models/deepseek-v4-flash/README.md:60` | 2bit-DQ "6% floor (40/50 degenerated)" | 14% (7/50) |

A ordem nova do LCB no rig (n=50): Swift 1.5 w1 t1 94%, gemma-4-31b 90%, gemma-4-26b @6bit 88%, qwen3.6-27b
88%, qwen3-coder-next 84%, agents-a1-xl 82%, qwen3.6-35b-a3b 82%, minimax Q3_K_S 78%, gemma-4-26b @4bit 76%,
gemma-4-e4b 74%.

### Relatórios em `reports/`

| Arquivo:linha | Hoje | Proposta |
|---|---|---|
| `reports/benchmark-charts.html:766–827` (dados `bench:'LCB'`) | coder 56, d27b 62, a3b35 54, g26_4 66, g26_6 80, g31 76, ge4b 68, a1 64, mmq3 72 | 84, 88, 82, 76, 88, 90, 74, 82, 78; q122b 62 e mmiq2 76 ficam com nota de limite inferior |
| `reports/benchmark-charts.html:333,384,401,418,435` | "LCB ceiling 80%", "LCB 64", "LCB 72%", "LCB 76", "LCB 62 exact tie" | 88 (sem "ceiling"), 82, 78, 76 (sem reavaliação), sem "exact tie" |
| `reports/benchmark-charts.html:551,596` | "@6bit at 80% is the rig's LCB ceiling, +18 pp over the best Qwen (27b at 62%)"; "Gemma — which topped LCB at 80%" | 31b 90% no topo; @6bit e 27b empatam em 88% |
| `reports/benchmark-charts.html:724,728` (refNote) | "LCB 72% @60k (68% @32k raw)"; IQ2_M "LCB 76%" | "78% @60k (74% @32k)"; IQ2_M: acrescentar "not regraded (no saved answers)" |
| `reports/quality-benchmarks-charts.html:548,555,568,579,590` | coder 56, d27b 62, g26 80, ge4b 68, q122b 62 "(ties 27B exactly)" | 84, 88, 88, 74; q122b 62 como limite inferior, sem "ties" |
| `reports/quality-benchmarks-charts.html:233` | a1 "LCB v6 64" | 82 |
| `reports/qwen38-flashnext-swift15.html:275` | LCB 41/50 (iQ) contra 42/50 (Swift), +1 | 45/50 contra 47/50, +2 |
| `reports/qwen38-flashnext-m4max-guide.html:537` (dados) | `passed` 41 (n2) / 42 (w1) | 45 / 47 |

A conclusão do guia e do relatório do Swift 1.5 ("mesma nota, menos thinking") continua válida: a diferença
segue dentro do ruído de 2–3 questões.

### Notas da campanha Swift 1.5 em `bench/`

| Arquivo:linha | Hoje | Proposta |
|---|---|---|
| `bench/swift15-flashnext-2026-10/results/summary.md:28` | LCB 41 / 42 / 41 / 41 (n2 t1, w1 t1, n2 t0, w1 t0) | 45 / 47 / 45 / 45 |
| `bench/swift15-flashnext-2026-10/results/ab-summary-t1.md:15` | 41/50, 42/50 | 45/50, 47/50 |
| `bench/swift15-flashnext-2026-10/results/ab-summary-t0.md:15` | 41/50, 41/50 | 45/50, 45/50 |
| `bench/swift15-flashnext-2026-10/results/page-data.json` | `livecodebench` com os acertos antigos | regenerar com os veredictos novos |

### Sem mudança

- `research/quality-benchmarks-2026-05.md` e `research/qwen38-flashnext-derivatives-20261009.md`: só citam notas
  declaradas por fornecedores ou pela comunidade.
- `reports/benchmarks.html`: os números de LCB (1,6% a 45,5%) não vêm de nenhum JSONL deste levantamento. Não
  verifiquei de qual runner eles vêm.
- `docs/models/deepseek-v4-flash/README.md:60`: IQ2_XS parcial 6/7 não muda.
