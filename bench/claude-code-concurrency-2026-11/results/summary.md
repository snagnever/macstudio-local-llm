# Campanha B — Claude Code real, uma e duas sessões, Splash 1.5.0 × mlx-serve 26.10.3

Rig: Mac Studio M4 Max 128 GB. Data: 30/10/2026 (filas das 12:35 às 17:28 no relógio do rig, mais as reps extra).
Claude Code 2.1.292 em `claude -p`, `CLAUDE_CODE_EFFORT_LEVEL=xhigh`, mesmo modelo como principal e rápido,
`--max-turns 40` (a, b) e `60` (c, d), timeout 1800 s. Servidores a `--max-context 131072`: Splash 1.5.0 com
ukisai Swift 1.5 GGUF IQ4_XS `0142554` (flags do `k2c1`) e mlx-serve 26.10.3 com Dankpaws Swift 1.5 MLX 4.7bpw
`13839b7` (flags do `w1zc1`, o build do driver diário). Um boot por rep; 120 s entre reps. Medição por request
pelo proxy `request_log.py` (um por sessão, relógio comum por rep); "1º prompt" = TTFT do primeiro request de cada
sessão; validação do proxy e calibração das tarefas em
[`calibration.md`](calibration.md). Resumos: [`claude-summary-splash.json`](claude-summary-splash.json) e
[`claude-summary-mlx.json`](claude-summary-mlx.json) (`summarize_claude.py --variants s=subagents,d=decode_share`).

Tarefas: a (`--format json` num pacote Python pequeno), b (dois bugs num script bash), c (`--group-by` num pacote
Python de 3.7K linhas, 60–70K de contexto), d (dois bugs e um refactor num toolkit bash de 1.1K linhas, 45–75K).
Braços: `rc1`/`rm1` = uma sessão (cada tarefa 2×); `rc2`/`rm2` = par a+b e par c+d (3×); `rc2s`/`rm2s` = par c+d
com dois subagentes Explore em paralelo por sessão (3×, mais uma rep extra); `rc2d` = par c+d com
`--decode-share 1.0` (3×).

## Tabela por braço, tarefa e rep

| braço | rep | tarefa | wall_s | turnos | contexto final | task_done | requests | erros HTTP | Agent paralelo / subagentes |
|---|---:|---|---:|---:|---:|---|---:|---:|---|
| `rc1` | 1 | a | 137.5 | 10 | 29K | sim | 7 | 0 | — |
| `rc1` | 1 | b | 43.5 | 7 | 21K | sim | 5 | 0 | — |
| `rc1` | 2 | a | 39.5 | 12 | 22K | sim | 6 | 0 | — |
| `rc1` | 2 | b | 39.5 | 6 | 21K | sim | 5 | 0 | — |
| `rc1` | 1 | c | 150.7 | 25 | 61K | sim | 18 | 0 | — |
| `rc1` | 1 | d | 212.3 | 28 | 47K | sim | 25 | 0 | — |
| `rc1` | 2 | c | 174.9 | 28 | 67K | sim | 17 | 0 | — |
| `rc1` | 2 | d | 294.1 | 26 | 75K | sim | 21 | 0 | — |
| `rc2` | 1 | a | 57.6 | 10 | 21K | sim | 6 | 0 | — |
| `rc2` | 1 | b | 81.9 | 10 | 23K | sim | 9 | 0 | — |
| `rc2` | 2 | a | 61.7 | 9 | 22K | sim | 6 | 0 | — |
| `rc2` | 2 | b | 64.7 | 6 | 21K | sim | 5 | 0 | — |
| `rc2` | 3 | a | 60.6 | 11 | 21K | sim | 7 | 0 | — |
| `rc2` | 3 | b | 88.9 | 11 | 24K | sim | 11 | 0 | — |
| `rc2` | 1 | c | 312.3 | 27 | 61K | sim | 17 | 0 | — |
| `rc2` | 1 | d | 367.8 | 29 | 46K | sim | 21 | 0 | — |
| `rc2` | 2 | c | 344.6 | 27 | 61K | sim | 19 | 0 | — |
| `rc2` | 2 | d | 445.7 | 39 | 58K | sim | 31 | 0 | — |
| `rc2` | 3 | c | 291.0 | 23 | 62K | sim | 12 | 0 | — |
| `rc2` | 3 | d | 358.8 | 29 | 48K | sim | 27 | 0 | — |
| `rc2s` | 1 | c | 611.3 | 21 | 42K | sim | 29 | 0 | 1 / 2 |
| `rc2s` | 1 | d | 730.5 | 24 | 50K | **não** | 32 | 0 | 1 / 2 |
| `rc2s` | 2 | c | 705.2 | 19 | 46K | sim | 26 | 0 | 1 / 2 |
| `rc2s` | 2 | d | 761.8 | 26 | 52K | sim | 34 | 0 | 1 / 2 |
| `rc2s` | 3 | c | 775.7 | 19 | 67K | sim | 24 | 0 | 1 / 2 |
| `rc2s` | 3 | d | 854.9 | 28 | 49K | sim | 37 | 0 | 1 / 2 |
| `rc2s` | 4 | c | 863.8 | 19 | 64K | sim | 25 | 0 | 1 / 3 |
| `rc2s` | 4 | d | 965.9 | 26 | 62K | sim | 39 | 0 | 1 / 2 |
| `rc2d` | 1 | c | 374.9 | 32 | 63K | sim | 24 | 0 | — |
| `rc2d` | 1 | d | 494.1 | 44 | 57K | sim | 32 | 0 | — |
| `rc2d` | 2 | c | 370.8 | 29 | 65K | sim | 21 | 0 | — |
| `rc2d` | 2 | d | 380.9 | 26 | 52K | sim | 22 | 0 | — |
| `rc2d` | 3 | c | 458.7 | 40 | 68K | sim | 27 | 0 | — |
| `rc2d` | 3 | d | 458.7 | 27 | 51K | sim | 23 | 0 | — |
| `rm1` | 1 | a | 45.5 | 11 | 22K | sim | 8 | 0 | — |
| `rm1` | 1 | b | 51.6 | 7 | 21K | sim | 6 | 0 | — |
| `rm1` | 2 | a | 51.6 | 10 | 22K | sim | 10 | 0 | — |
| `rm1` | 2 | b | 46.6 | 6 | 21K | sim | 5 | 0 | — |
| `rm1` | 1 | c | 180.0 | 23 | 63K | sim | 14 | 0 | — |
| `rm1` | 1 | d | 385.2 | 61 | 75K | sim | 51 | 0 | — |
| `rm1` | 2 | c | 143.6 | 21 | 58K | sim | 12 | 0 | — |
| `rm1` | 2 | d | 221.5 | 26 | 45K | sim | 20 | 0 | — |
| `rm2` | 1 | a | 94.0 | 9 | 22K | sim | 6 | 0 | — |
| `rm2` | 1 | b | 95.0 | 6 | 21K | sim | 5 | 0 | — |
| `rm2` | 2 | a | 87.9 | 9 | 21K | sim | 8 | 0 | — |
| `rm2` | 2 | b | 85.9 | 6 | 21K | sim | 5 | 0 | — |
| `rm2` | 3 | a | 93.1 | 12 | 22K | sim | 8 | 0 | — |
| `rm2` | 3 | b | 88.9 | 6 | 21K | sim | 5 | 0 | — |
| `rm2` | 1 | c | 191.1 | 12 | 55K | **não** | 6 | 0 | — |
| `rm2` | 1 | d | 346.8 | 33 | 48K | sim | 30 | 0 | — |
| `rm2` | 2 | c | 333.5 | 21 | 61K | sim | 16 | 0 | — |
| `rm2` | 2 | d | 419.4 | 23 | 49K | sim | 19 | 0 | — |
| `rm2` | 3 | c | 422.3 | 35 | 66K | sim | 25 | 0 | — |
| `rm2` | 3 | d | 438.4 | 22 | 42K | sim | 18 | 0 | — |
| `rm2` | 4 | c | 510.4 | 34 | 90K | sim | 24 | 0 | — |
| `rm2` | 4 | d | 580.1 | 44 | 55K | sim | 29 | 0 | — |
| `rm2s` | 1 | c | 1024.6 | 21 | 69K | sim | 37 | 0 | 1 / 2 |
| `rm2s` | 1 | d | 1114.6 | 24 | 60K | sim | 37 | 0 | 1 / 2 |
| `rm2s` | 2 | c | 1064.0 | 27 | 77K | sim | 38 | 0 | 1 / 2 |
| `rm2s` | 2 | d | 1099.3 | 23 | 54K | sim | 36 | 0 | 1 / 2 |
| `rm2s` | 3 | c | 1161.0 | 36 | 72K | sim | 52 | 0 | 1 / 2 |
| `rm2s` | 3 | d | 1112.3 | 25 | 56K | sim | 32 | 0 | 1 / 2 |

## Tabela por braço (requests do proxy)

| braço | servidor | perfil | sessões | `max_concurrent` | 1º prompt TTFT | TTFT quente p50 / p90 | tok/s quente p50 / mín | requests | erros HTTP | swap Δ máx | mín livre |
|---|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|
| `rc1` | Splash 1.5.0 | pequeno (a, b) | 1 | 1 | 23.7 s | 0.9 / 1.4 s (boa / boa) | 127.6 / 80.0 (boa / boa) | 23 | 0 | 0.00 GB | 0.06 GB |
| `rc1` | Splash 1.5.0 | realista (c, d) | 1 | 1 | 23.9 s | 1.0 / 1.6 s (boa / boa) | 126.1 / 78.9 (boa / boa) | 81 | 0 | 0.00 GB | 0.06 GB |
| `rc2` | Splash 1.5.0 | pequeno (a, b) | 2 | 2 | 27.7 s | 1.4 / 3.4 s (boa / aceitável) | 90.2 / 39.7 (boa / aceitável) | 44 | 0 | 0.00 GB | 0.06 GB |
| `rc2` | Splash 1.5.0 | realista (c, d) | 2 | 2 | 26.4 s | 1.4 / 4.8 s (boa / aceitável) | 89.2 / 39.0 (boa / aceitável) | 127 | 0 | 0.00 GB | 0.06 GB |
| `rc2s` | Splash 1.5.0 | realista (c, d) | 2 | 6 | 29.4 s | 2.5 / 8.4 s (aceitável / ruim) | 82.8 / 20.1 (boa / ruim) | 246 | 0 | 0.00 GB | 0.06 GB |
| `rc2d` | Splash 1.5.0 | realista (c, d) | 2 | 2 | 26.4 s | 2.2 / 5.1 s (aceitável / ruim) | 80.8 / 42.5 (boa / aceitável) | 149 | 0 | 0.00 GB | 0.03 GB |
| `rm1` | mlx-serve 26.10.3 | pequeno (a, b) | 1 | 1 | 25.0 s | 0.3 / 0.8 s (boa / boa) | 88.0 / 66.9 (boa / boa) | 29 | 0 | 0.00 GB | 0.01 GB |
| `rm1` | mlx-serve 26.10.3 | realista (c, d) | 1 | 1 | 25.2 s | 0.4 / 1.2 s (boa / boa) | 84.8 / 67.0 (boa / boa) | 97 | 0 | 0.00 GB | 0.01 GB |
| `rm2` | mlx-serve 26.10.3 | pequeno (a, b) | 2 | 2 | 38.2 s | 0.4 / 1.2 s (boa / boa) | 41.0 / 31.0 (aceitável / aceitável) | 37 | 0 | 0.00 GB | 0.01 GB |
| `rm2` | mlx-serve 26.10.3 | realista (c, d) | 2 | 2 | 38.2 s | 0.4 / 1.0 s (boa / boa) | 39.9 / 19.6 (aceitável / ruim) | 167 | 0 | 0.00 GB | 0.01 GB |
| `rm2s` | mlx-serve 26.10.3 | realista (c, d) | 2 | 5 | 43.5 s | 0.5 / 4.5 s (boa / aceitável) | 39.7 / 6.7 (aceitável / ruim) | 232 | 0 | 0.00 GB | 0.01 GB |

## Tempo de tarefa e tempo poupado


**Splash 1.5.0** (`claude-summary-splash.json`)

| bloco | tarefa | solo (s) | no par (s) | wall do par (s) | soma dos solos (s) | tempo poupado | task_done | erros |
|---|---|---:|---:|---:|---:|---:|---|---:|
| small | a | 88.5 | 60.0 | 78.5 | 130.0 | +40% | sim | 0 |
| small | b | 41.5 | 78.5 | 78.5 | 130.0 | +40% | sim | 0 |
| realistic | c | 162.8 | 316.0 | 390.8 | 416.0 | +6% | sim | 0 |
| realistic | d | 253.2 | 390.8 | 390.8 | 416.0 | +6% | sim | 0 |
| subagents | c | — | 739.0 | 860.9 | 416.0 | -107% | **não** | 0 |
| subagents | d | — | 860.9 | 860.9 | 416.0 | -107% | **não** | 0 |
| decode_share | c | — | 401.5 | 444.6 | 416.0 | -7% | sim | 0 |
| decode_share | d | — | 444.6 | 444.6 | 416.0 | -7% | sim | 0 |

subagents: parallel_agent_calls=8, subagents_spawned=17, requests max_concurrent=6, warm p50/p90=2.535/8.439, tps p50/min=82.75/20.1, prefill_turns=85

**mlx-serve 26.10.3** (`claude-summary-mlx.json`)

| bloco | tarefa | solo (s) | no par (s) | wall do par (s) | soma dos solos (s) | tempo poupado | task_done | erros |
|---|---|---:|---:|---:|---:|---:|---|---:|
| small | a | 48.5 | 91.7 | 92.0 | 97.7 | +6% | sim | 0 |
| small | b | 49.1 | 89.9 | 92.0 | 97.7 | +6% | sim | 0 |
| realistic | c | 161.8 | 422.1 | 479.3 | 465.2 | -3% | **não** | 0 |
| realistic | d | 303.4 | 446.2 | 479.3 | 465.2 | -3% | **não** | 0 |
| subagents | c | — | 1083.2 | 1125.0 | 465.2 | -142% | sim | 0 |
| subagents | d | — | 1108.7 | 1125.0 | 465.2 | -142% | sim | 0 |

subagents: parallel_agent_calls=6, subagents_spawned=12, requests max_concurrent=5, warm p50/p90=0.47450000000000003/4.51, tps p50/min=39.7/6.7, prefill_turns=76

## Faixas de experiência por servidor e cenário

Faixas da spec: resposta começa (TTFT quente) ≤ 2 s boa / 2–5 aceitável / > 5 ruim; geração ≥ 60 tok/s boa /
30–60 aceitável / < 30 ruim; primeiro prompt ≤ 30 s boa / 30–60 aceitável / > 60 ruim. Mediana e pior caso
(p90 do TTFT, mínimo do tok/s) do perfil realista, exceto onde indicado.

| cenário | Splash 1.5.0 | mlx-serve 26.10.3 |
|---|---|---|
| 1 sessão: resposta começa | **boa** (1.0 s; p90 1.6 s) | **boa** (0.4 s; p90 1.2 s) |
| 1 sessão: geração | **boa** (126 tok/s; mín 79) | **boa** (85 tok/s; mín 67) |
| 1 sessão: primeiro prompt (~19K) | **boa** (23.7 s) | **boa** (25.0 s) |
| 2 sessões: resposta começa | **boa** na mediana (1.4 s), **aceitável** no p90 (4.8 s) | **boa** (0.4 s; p90 1.0 s) |
| 2 sessões: geração | **boa** na mediana (89 tok/s), **aceitável** no pior caso (39) | **aceitável** (40 tok/s), **ruim** no pior caso (20) |
| 2 sessões: primeiro prompt | **boa** (26.4 s c+d; 27.7 s a+b) | **aceitável** (38.2 s, c+d e a+b) |
| 2 sessões + subagentes: resposta começa | **aceitável** (2.5 s), **ruim** no p90 (8.4 s) | **boa** (0.5 s), **aceitável** no p90 (4.5 s) |
| 2 sessões + subagentes: geração | **boa** na mediana (83 tok/s), **ruim** no pior caso (20) | **aceitável** (40 tok/s), **ruim** no pior caso (6.7) |
| 2 sessões + `--decode-share 1.0` | TTFT **aceitável** (2.2 s; p90 5.1 s), geração **boa** (81; mín 43) | — |

## As três perguntas da spec

**1. Quanto a segunda sessão custa numa tarefa realista?** No Splash a mediana do TTFT quente vai de 1.0 s para
1.4 s e o p90 de 1.6 s para 4.8 s; a geração cai de 126 para 89 tok/s na mediana e de 79 para 39 no pior caso.
As tarefas c e d levam ~2× o tempo solo quando rodam juntas (316 e 391 s contra 163 e 253 s), e o par termina 6%
antes do que as duas em sequência. No mlx-serve o TTFT quente não muda (0.4 s nas duas condições) mas a geração
cai pela metade, de 85 para 40 tok/s na mediana (pior caso 20); as tarefas levam 1.5–2.6× (422 e 446 s contra
162 e 303 s) e o par termina 3% depois da sequência. A diferença entre os servidores é como a lentidão aparece:
no Splash a resposta demora mais a começar e o par ainda ganha um pouco; no mlx-serve ela começa igual, corre
mais devagar e o par não ganha nada. Os tempos de tarefa contam só sessões que terminaram a tarefa.

**2. Subagentes mudam o custo? Duas sessões com subagentes se comportam como N = 4?** O N real medido pelo proxy
foi **6 streams no Splash e 5 no mlx-serve** (duas sessões, cada uma com dois Explore em paralelo; o
`parallel_agent_calls` confirma uma chamada dupla de `Agent` por sessão em todas as reps). O custo muda muito: no
Splash o par c+d levou 861 s de wall (contra 391 s sem subagentes), TTFT quente 2.5 s na mediana e 8.4 s no p90,
tok/s mínimo 20; no mlx-serve 1 125 s (contra 479 s), tok/s 40 na mediana e 6.7 no mínimo. Os subagentes também
criam turnos de prefill (85 no Splash, 76 no mlx-serve, cada subagente começa frio). Em relação às duas tarefas em
sequência, o par com subagentes fica 107% (Splash) e 142% (mlx-serve) mais lento. A resposta é não: não se
comportam como N = 4, mas como 5–6 streams, e o pior caso cai para a faixa ruim nos dois servidores.

**3. `--decode-share 1.0` ajuda o par real no Splash?** Não. Com a flag o par c+d levou 445 s de wall contra 391 s
sem ela, o TTFT quente subiu de 1.4 para 2.2 s na mediana (p90 4.8 → 5.1 s) e a geração caiu de 89 para 81 tok/s
na mediana; o mínimo melhorou pouco (39 → 43). Com `--decode-share 1.0` o par passa a terminar 7% depois da
sequência, em vez de 6% antes. A vantagem dos probes sintéticos (`k2c2ad1`) não aparece com o Claude Code real.

## Veredito

Uma sessão de Claude Code fica na faixa boa nos dois servidores, em todas as métricas. Duas sessões continuam na
faixa boa na mediana no Splash e perdem metade da geração no mlx-serve (faixa aceitável, pior caso ruim). O par
termina 6% antes da sequência no Splash e 3% depois no mlx-serve, então rodar duas sessões vale a pena no Splash
se a lentidão da mediana for aceitável para quem usa, e no mlx-serve só pela conveniência de duas janelas. Subagentes em paralelo custam caro nos dois servidores: 5–6 streams, wall 2–3× o do par
simples, pior caso na faixa ruim. `--decode-share 1.0` não ajuda o par real.

Funcional: 62 sessões (58 nas filas mais 4 nas reps extra), zero erros HTTP, 60 com `task_done`. As duas sem `task_done` foram falhas do
modelo, não do harness: `rc2s r1` d corrigiu o off-by-one do `rotate.sh` mas continuou apagando o arquivo mais
novo quando há KEEP+1; `rm2 r1` c parou em 12 turnos com resposta vazia e só tocou em `report.py`. Uma rep extra
(`r4`) de cada um desses braços rodou depois das filas para haver três pares completos (as duas com `task_done`).
As reps falhas ficam nos arquivos e nas tabelas por rep, mas não entram nos tempos de tarefa (`pair_s`,
`pair_wall_s`, tempo poupado): uma sessão que saiu com 0 sem fazer a tarefa não tem tempo de tarefa. Por isso
`task_done` é `false` nos blocos `subagents` (Splash) e `realistic` (mlx-serve) dos resumos. Swap Δ 0.00 GB em todos os braços; mínimo de memória livre 0.01–0.06 GB, o
padrão da máquina com estes servidores.

## Leitura

- **O custo da segunda sessão tem forma diferente em cada servidor.** O Splash mantém a geração alta e paga em
  TTFT (fila na admissão: o p90 vai a 4.8 s); o mlx-serve mantém o TTFT e divide a geração entre as duas sessões
  (batch de decode, 40 tok/s). Para quem digita e espera a primeira palavra, o mlx-serve parece mais vivo; para
  quem espera a resposta inteira, o Splash termina antes.
- **O tempo poupado pelo par é pequeno (+6% no Splash, −3% no mlx-serve)** porque as duas sessões disputam a
  mesma GPU; o ganho vem só dos intervalos em que uma sessão espera ferramenta enquanto a outra decodifica.
- **O solo também varia.** Na tarefa a do Splash uma rep levou 137 s por um turno de 7 037 tokens (88 s a 80 tok/s);
  a média do solo do perfil pequeno (88.5 s) e o "tempo poupado" de 40% do par a+b carregam esse outlier. O par
  c+d é a leitura confiável.
- **Subagentes não valem o custo com estes servidores.** O proxy mostra 5–6 streams; o p90 do TTFT vai à faixa ruim
  e o tok/s mínimo cai a 20 (Splash) e 6.7 (mlx-serve). A sessão principal faz menos turnos (a exploração vai para
  os Explore), mas o wall dobra ou triplica.
- **O mlx-serve 26.10.3 não implementa `count_tokens`** (404 em 1 ms); o Claude Code segue sem ele. O Splash
  responde `{"input_tokens": N}`. O resumo descarta essas respostas, que não são turnos do modelo.
- **Comparação com os `kcc*` de 29/10** (mesmo Splash, tarefas a+b): par a+b wall 61.7 s lá, 78.5 s aqui (3 reps,
  variação do modelo); TTFT quente do par 1.8 s lá (log do servidor), 1.4 s aqui (proxy); tok/s 90 nos dois.

## O que não foi medido

- Sessão interativa (permissões, títulos, resumo de contexto): só `claude -p`.
- Terminal-Bench no Splash; 256K real; 512K e 1M; mais de 6 streams; outros modelos.
- `--decode-share` em valores intermediários; `--max-concurrent` explícito no mlx-serve (o default faz batch).
- Variância: 2 reps solo e 3–4 reps por par; os p90 vêm de 100–230 requests por braço, não de muitas reps.
