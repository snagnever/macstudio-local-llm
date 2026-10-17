# LiveCodeBench publicado: avaliador antigo × reavaliado (2026-10-16)

O avaliador antigo é o `bench2.py` do submódulo `tools/local-llm-bench-m4-32gb` em `a4a95bb`. Ele rodava as
respostas sem o preâmbulo de imports do LiveCodeBench oficial e por `python -c`, que falha em entradas grandes
(`E2BIG`). A correção entrou no `main` do submódulo em `2403125` (PR #3), e o ponteiro do repo foi atualizado para
esse commit.

A coluna "reavaliado" vem de [`scripts/lcb_regrade.py`](../scripts/lcb_regrade.py) sobre as respostas gravadas.
Nas 4 respostas do Swift, o `bench2.py` em `2403125` e o `lcb_regrade.py` dão o mesmo veredito nas 200 questões
(0 divergências). Nenhuma resposta aprovada passou a falhar em nenhum arquivo. Mesmas 50 questões
(`release_v6`, seed 42) em todas as linhas.

## Números publicados

| campanha | braço / pack | perfil | arquivo | bruto | reavaliado | onde está publicado |
| --- | --- | --- | --- | ---: | ---: | --- |
| swift15-flashnext-2026-10 | `n2` iQ-MLX 4.7bpw | t1 (`xhigh`, sampling do vendor) | `bench/swift15-flashnext-2026-10/results/ab/t1/n2/livecodebench.jsonl` | 41 | 45 | swift15 `summary.md`, `ab-summary-t1.md`, `page-data.json`; `reports/qwen38-flashnext-swift15.html`; `reports/qwen38-flashnext-m4max-guide.html`; `docs/models/qwen3.8-flash-next.md` (linha do Swift 1.5); post do Reddit (`reddit-post-m4max-guide.md`, não editado) |
| swift15-flashnext-2026-10 | `w1` Swift 1.5 MLX-4.7bpw | t1 (`xhigh`, sampling do vendor) | `bench/swift15-flashnext-2026-10/results/ab/t1/w1/livecodebench.jsonl` | 42 | 47 | os mesmos lugares da linha acima |
| swift15-flashnext-2026-10 | `n2` iQ-MLX 4.7bpw | t0 (`xhigh`, temperatura 0) | `bench/swift15-flashnext-2026-10/results/ab/t0/n2/livecodebench.jsonl` | 41 | 45 | swift15 `summary.md`, `ab-summary-t0.md`, `page-data.json`; `reports/qwen38-flashnext-swift15.html` |
| swift15-flashnext-2026-10 | `w1` Swift 1.5 MLX-4.7bpw | t0 (`xhigh`, temperatura 0) | `bench/swift15-flashnext-2026-10/results/ab/t0/w1/livecodebench.jsonl` | 41 | 45 | os mesmos lugares da linha acima |
| flashnext-next-steps-2026-10 (3d) | `w1` `xhigh` r1 / r2 | t1 | `results/e3d/t1/w1-xhigh-r{1,2}/livecodebench.jsonl` | 43 / 43 | 47 / 47 | já publicado reavaliado: `etapa3-agent.md`, card (seção do effort); os `e3d-summary-*.md` gerados trazem o bruto |
| flashnext-next-steps-2026-10 (3d) | `w1` `medium` r1 / r2 | t1 | `results/e3d/t1/w1-medium-r{1,2}/livecodebench.jsonl` | 27 / 25 | 41 / 40 | idem |
| flashnext-next-steps-2026-10 (3d) | `w1` `low` r1 / r2 | t1 | `results/e3d/t1/w1-low-r{1,2}/livecodebench.jsonl` | 26 / 25 | 42 / 41 | idem |
| flashnext-next-steps-2026-10 (5, 7) | `o1x` oMLX | t1 | `results/e5/t1/o1x/livecodebench.jsonl` | 41 | 45 | já publicado reavaliado: `etapa5-refit.md`, `e5-lcb-regrade.md`; `etapa5-quality-o1x-o1r.md` (gerado) traz o bruto |
| flashnext-next-steps-2026-10 (5, 7) | `o1r` oMLX refit | t1 | `results/e5/t1/o1r/livecodebench.jsonl` | 42 | 46 | já publicado reavaliado: `etapa5-refit.md`, `etapa7-mix6.md`, `e5-lcb-regrade.md`; `etapa7-quality-o1r-x1.md` (gerado) traz o bruto |
| flashnext-next-steps-2026-10 (7) | `x1` oMLX mix6 v2 | t1 | `results/e5/t1/x1/livecodebench.jsonl` | 43 | 47 | idem |

## O que mudou nos arquivos

- Campanha do Swift: `results/lcb-regrade.json` guarda, por braço e perfil, as questões que o avaliador novo
  aprova. `scripts/render_page.py` aplica esse arquivo às notas, ao G1, ao tempo por acerto e à contagem por
  dificuldade. A página `reports/qwen38-flashnext-swift15.html` e o `page-data.json` foram regerados. O G1 do LCB
  continua passando: t1 45 → 47 (+2), t0 45 → 45.
- `reports/qwen38-flashnext-m4max-guide.html`: as duas notas do LCB no JSON embutido foram trocadas à mão
  (41 → 45, 42 → 47). O renderer (`render_m4max_guide.py`) lê `time.t1.livecodebench.arms.*.passed` do
  `page-data.json` do Swift, que agora traz a nota reavaliada; uma nova renderização dá os mesmos valores.
- `bench/qwen38-27b-next-steps-2026-10/results/page-data.json` copia as notas do Swift em `n2_quality` e
  `w1_quality` (41 e 42). A página do 27B não mostra esses campos; o arquivo ficou como está.

## Sem respostas gravadas

Nenhum. Não há LiveCodeBench publicado do Qwen3.8 27B (a bateria de qualidade não rodou) nem da campanha
`qwen38-flashnext-daily-driver-2026-09` ou de `bench/qwen38-flash-next/`.
