# Qwen3.8-27B denso — próximos passos 2026-10 — runbook autônomo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Executar sem supervisão os testes P1, P2, P3, P4 e P6 de [research/qwen38-27b-next-steps-20261013.md](../../research/qwen38-27b-next-steps-20261013.md) no rig, com as mesmas métricas da campanha do Flash-Next (`T_turno` a 32K e 128K, gates, memória, aceitação) e as métricas de tempo e tokens por tarefa da campanha Swift (HumanEval, GPQA, LiveCodeBench, jdhodges, Veerman, IF, loops), e publicar uma página de comparação dos stacks do 27B contra o driver Flash-Next.

**Architecture:** A campanha reusa o driver `run-candidate.sh` de 2026-09 (servidor → `cache_probe.py` → `attach_memory.py`/`attach_mtp.py`) com braços novos num bloco próprio, o `summarize_driver.py` para `T_turno` e gates, o `decide.py` da campanha flashnext-next-steps para as tabelas de decisão, e a bateria `ab-battery.sh` da campanha Swift via `run-battery.sh`. O que é novo fica em `bench/qwen38-27b-next-steps-2026-10/scripts/`: um orquestrador `run-campaign.sh` que encadeia fases, gates térmicos, decisões e arquivos de gate sem intervenção; um launcher para o Splash; um launcher GGUF do 27B; um contador de respostas vazias; e um renderizador da página `reports/qwen38-27b-stacks.html`. A pesquisa que fundamenta cada teste é o spec.

**Tech Stack:** bash 3.2 (o do rig), Python 3 (stdlib; `huggingface_hub` do venv `~/LocalProjects/local-llms/.venv`), pytest via `uv run`, mlx-serve 26.10.2, oMLX 0.7.1.dev1, Splash 1.3.1, mlx-dspark 0.20.3, llama.cpp b11569, macmon 0.7.2.

**Spec:** [research/qwen38-27b-next-steps-20261013.md](../../research/qwen38-27b-next-steps-20261013.md) (movido de `reports/Qwen38 27B denso melhor stack.md` no Task 0; notas em `research/qwen38-27b-next-steps-20261013-notes/`).

## Global Constraints

- Rig: Mac Studio M4 Max 128 GB (`ssh vitor@mac-studio`); checkout do repo no rig: `~/LocalProjects/local-llms`; um modelo servido por vez.
- Runtimes isolados em `~/.local/opt/qwen38/`: `mlx-serve-v26.10.2/mlx-serve` (tag `v26.10.2`, novo), `omlx-v0.7.1.dev1/` (já instalado pela campanha flashnext-next-steps), `mlx-dspark-v0.20.3/` (referência s27r), `splash-v1.3.1/` (novo), `llama-b11569/` (instalado pela campanha flashnext-next-steps; se faltar, o Task 2 instala). `~/.local/bin` não muda.
- Pesos (raiz `~/.cache/local-llms/qwen3.8-prefix-cache`): já no disco `mlx-community--Qwen3.8-27B-8bit-815b83c0…` e `incoai--Qwen3.8-27B-DFlash2-dedf8df6…`; novos (Task 1): `Jundot/Qwen3.8-27B-oQ8e-mtp` @ `6c76ddfb82af`, `Jundot/Qwen3.8-27B-oQ4e-mtp` @ `49c1d60367d9`, `ddalcu/Qwen3.8-27B-MLX-Serve-8bit` @ `7775059e955f`, `scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp` @ `881dc1914f65`, `ggml-org/Qwen3.8-27B-GGUF` @ `71bc7b627595` (só `*Q8_0*` e `mtp-*Q8_0*`).
- Referências fixas: **s27r** (mlx-dspark 0.20.3 + DFlash2 + mlx-community 8bit, `--prefix-cache-rungs 1024`): `T_turno` 16.7 / 25.7 s a 32K / 128K (`bench/engine-updates-2026-10/results/etapa-f-fixes.md`). **Driver Flash-Next w1** (Swift 1.5 em mlx-serve 26.10.1): 7.9 / 8.6 s (`bench/swift15-flashnext-2026-10/results/tturno-summary.json`). **Driver Flash-Next n2** (secundário: ddalcu iQ-MLX-4.7bpw em mlx-serve 26.10.1): 8.1 / 8.9 s, mesmo arquivo. A página mostra w1 (driver A) e n2 (driver B); a regra de 1.25× usa só o w1. O s27r é re-medido nesta campanha (braço `s27r`, tag `p0x`) como controle da sessão.
- Métrica: `T_turno = TTFT(tool_turn) + 512 / mediana(decode quente de identical, append, tool_turn)`, 3 reps a 32K e 128K (`middle_mutation` 1 rep), calculada por `summarize_driver.py`.
- Gates de todo braço de velocidade: zero HTTP 4xx/5xx; needles corretas (truncado não é falha); hit ≥ 0.90 em `append` e `tool_turn`; swap Δ ≤ 0.5 GB; `[spec-stats]` no boot log (braços mlx-serve). Wired > 102 GB é alerta, não gate. Braço cujo runtime não devolve `usage.prompt_tokens_details.cached_tokens` roda o `decide.py` com `--skip-gates hit_append,hit_tool_turn` e é julgado pelo warm TTFT do `tool_turn`.
- Esforço: todo braço de velocidade roda duas vezes, `xhigh` (tag `…x`, comparável à série s27r/o27) e `medium` (tag `…m`, uso recomendado). A bateria de qualidade roda em `medium`; GPQA e LiveCodeBench rodam também em `xhigh`. `high` nunca é enviado (HTTP 500, QwenLM #217).
- Respostas vazias (`finish_reason: stop` com conteúdo vazio) contam como falha de gate (QwenLM #216). Contadas por `scripts/empty_answers.py` sobre `think_turn_probe` e sobre a bateria.
- Regras de decisão (spec, §Próximos passos): reabrir o veredito de driver só com `T_turno ≤ 1.25 × w1` nas duas bandas (≤ 9.9 s a 32K, ≤ 10.8 s a 128K) e todos os gates. P1 (Splash): `≤ 0.75 × s27r` a 128K segue para a bateria. P2: o27q4 < s27r a 128K **e** HumanEval/tool-calling a ≤ 2 pontos do o27q8 vira o melhor 27B documentado; o27q8 substitui o o27 no `27b-summary.md` de qualquer forma. P3: decode ≥ 30 tok/s a 128K e `T_turno ≤ s27r` faz do mlx-serve o runtime recomendado do 27B. P4: tempo até a resposta final ≤ 0.8× o27q4, tool-calling ≥ o27q4 − 1 e zero loops promove o Swift; aceitação MTP < 0.8× a do base registra "cabeça obsoleta". P6: só 64K; RSS do host > +5 GB por sessão ou swap Δ > 0.5 GB reprova o draft-mtp no Metal.
- Sampling: perfil thinking do vendor, `temperature 1.0`, `top_p 0.95`, `top_k 20`, `presence_penalty 0`; `reasoning_effort` sempre explícito. Valores válidos do template do 27B: `xhigh`, `medium`, `low`.
- Probe: `cache_probe.py`, fixture `audit_retrieval`, needles 10/50/90, `max_tokens` 4096, cenários `cold → identical → append → middle_mutation → tool_turn`.
- Protocolo térmico: parar o driver diário; ≥ 82 GB livres antes de subir um braço; 10 min ociosos e GPU < 50 °C entre bandas (`idle-gate.sh`, agora com as portas 8484 e 8585); 120 s entre braços; ordem alterna (32K: ref → cand; 128K: cand → ref). O orquestrador tenta o gate 3 vezes (exit 75) e, se falhar, pula a banda e registra.
- Disco: `df -g /` antes de cada download; os packs novos somam ~131 GB; `fetch_pack.py --reserve-gb 150`.
- Orçamento de tempo: ~70 h de rig sem supervisão (fases de velocidade ~32 h com P7/P8, ver "Revisão de 13/10"; bateria ~40 h). O orquestrador é retomável: pula o que já tem resultado.
- Fora do escopo autônomo: P5 (qualidade agêntica com OpenCode) precisa do MacBook e de Docker; esta campanha só escreve o gate `P5_GO` em `results/gates.env`.
- Idioma: prosa em pt-BR; comandos, flags, código, comentários e mensagens de git em inglês.
- Commits: mensagem `bench(qwen38-27b): ...` terminando com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Testes: `uv run --no-project --with pytest python -m pytest <caminho> -q`, na raiz do repo.

## Review Focus

1. **Runtime sem `cached_tokens` ou sem `/v1/tokenize` (Splash, llama.cpp).** O `cache_probe.py` registra hit 0 e o gate `hit_*` reprova um braço que na verdade reusa cache. Esperado: o braço usa `--tokenizer-path` e o `decide.py --skip-gates hit_append,hit_tool_turn`; a decisão lê o warm TTFT. Checado no Task 0 (teste do `--skip-gates`) e no smoke do Task 5 Step 4 (campo `cached_tokens` presente ou não, registrado em `results/etapa1-splash-smoke.md`).
2. **Thinking desligado sem aviso no oMLX ou no Splash.** `reasoning_effort` no topo pode não ligar o thinking; a bateria mediria o modelo sem raciocínio. Esperado: `reasoning_chars > 0` em todo smoke. Checado no smoke de cada fase (Tasks 5, 6, 7, 8, 10, campo `reasoning_chars` do registro de 8K) e no gate do `run-battery.sh` (smoke do `run-ab.sh`).
3. **Respostas vazias em `xhigh` contaminando medianas.** O `summarize_driver.py` conta um `stop` vazio como servido. Esperado: a contagem aparece na decisão e reprova quando > 0 no `think_turn_probe`. Checado no Task 0 (teste do `empty_answers.py`) e em cada fase (Step "respostas vazias").
4. **Mistura de esforço ou de sessão no mesmo grupo.** Dois esforços do mesmo braço no mesmo glob dão o aviso `mistura session_id` e uma mediana sem sentido. Esperado: tags distintas (`p2x`, `p2m`) e globs por tag. Checado no Task 4 (teste do `--dry-run` do orquestrador: um glob por tag) e no stderr do `decide.py`.
5. **Driver diário não volta ou segundo servidor na porta.** Uma campanha que termina sem religar o Flash-Next deixa o rig inútil; um servidor esquecido em 8484 ou 8585 faz o braço seguinte abortar. Esperado: `idle-gate.sh` recusa com qualquer uma das cinco portas ocupada; `run-campaign.sh` religa o driver no `trap EXIT`. Checado no Task 0 (teste `--print-ports`) e no Task 4 (teste do dry-run mostra a linha `restart daily driver`).

## Revisão de 13/10: aprendizados e nova ordem

Esta seção substitui a ordem P0 → P6 do Task 6. O resto do plano continua valendo.

**O que aprendemos até agora:**

1. **Smokes de 8K (`results/etapa1-smokes.md`, effort `medium`).** Decode mediano: k27 86.5, r27d 83.6, o27q4 81.4, r27m 51.5 e l27 35.3 tok/s. Todos com `reasoning_chars > 0` e `cached_tokens` presente. O `[spec-stats]` confirma `mode=dflash` no r27d e `mode=mtp` no r27m.
2. **A cabeça MTP sozinha é lenta no mlx-serve.** O r27m decodifica 38% abaixo do r27d com o mesmo pack. Um braço só-MTP dificilmente bate o s27r.
3. **O llama.cpp não compete.** O l27 faz 35 tok/s a 8K; a 64K fica abaixo disso. O s27r faz 32 tok/s a 128K com prefix cache melhor. A P6 só confirma o NO-GO do Metal draft-mtp.
4. **Existe um Swift 1.5 27B que o mlx-serve deve carregar** ([research/swift15-27b-mlx-serve-20261013.md](../../research/swift15-27b-mlx-serve-20261013.md)): `scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp` @ `881dc1914f65`, já no disco. A cabeça MTP é a do base, sem retreino (hash idêntico, verificado no rig). O DFlash2 tem a mesma arquitetura de alvo. Ninguém publicou velocidade dele no mlx-serve.
5. **O `idle-gate.sh` media memória livre errado.** Contava só `Pages free`; depois dos downloads e dos smokes, o cache de arquivos ficou em páginas speculative e depois inactive, e o gate travou (exit 75). Agora a medida é total − wired − anônima − compressor (commits 9293a42 e 5c60abb).
6. **O gargalo do veredito continua o TTFT quente do `tool_turn`.** Para ficar a ≤ 1.25 × w1 a 128K, o 27B precisa de TTFT ≤ ~3 s e decode ≥ ~65 tok/s ao mesmo tempo. Os candidatos com chance são o Splash (prefill com ANE e cache persistente) e o mlx-serve com drafter. O decode do drafter já está perto de 84 tok/s a 8K.

**Nova ordem (prioridade por chance de mudar o veredito e por custo):**

| Ordem | Fase | Braços | Base e regra | Duração | Por quê |
|---|---|---|---|---|---|
| 1 | P0 | s27r | controle | ~3 h | Em curso desde 10:21; não muda |
| 2 | P1 | k27 | s27r, ≤ 0.75× | ~3 h | Maior decode no smoke; ataca o TTFT quente |
| 3 | P3 | r27d | s27r, ≤ 1.00× | ~2.75 h | Segundo maior decode; runtime do driver Flash-Next |
| 4 | P7 (nova) | w27d | r27d, ≤ 1.03× | ~3 h | Swift 1.5 no mlx-serve com DFlash2; smoke de 8K antes |
| 5 | P2 | o27q4, o27q8 | s27r, ≤ 1.00× | ~5.5 h | Repin do oMLX; o27q4 é a base da P4 |
| 6 | P4 | o27sw | o27q4, ≤ 1.03× | ~3 h | Swift no oMLX; depende do o27q4 |
| 7 | P8 (nova) | r27m, w27m | s27r, ≤ 1.00× | ~5.5 h | Só MTP: baixa chance, mas mede a cabeça herdada no Swift |
| 8 | P6 | l27n, l27 | s27r a 32K | ~2 h | Confirmação do NO-GO do llama.cpp; a primeira a cortar se faltar tempo |

Sondas de raciocínio: ~4.9 h no total (11 braços). Total das fases de velocidade: ~32 h a partir de 10:21 de 13/10, fim previsto em 14/10 por volta de 18:30.

**Regras novas:**

- **P7 (w27d):** mesma regra de velocidade da P4 contra a base do mesmo runtime: `T_turno ≤ 1.03 × r27d` nas duas bandas e todos os gates. Antes das bandas, o orquestrador roda um smoke de 8K (`--repeat 1`, tag `p7s`) e pula a fase se o smoke falhar: rc ≠ 0, algum `reasoning_chars == 0`, `[spec-stats]` ausente, `mode` diferente de `dflash` ou decode mediano < 60 tok/s.
- **P8 (r27m, w27m):** regra da P3 (`≤ 1.00 × s27r`). O w27m também passa pelo smoke de 8K (tag `p8s`, mesmos critérios com `mode=mtp`). Se a aceitação MTP do w27m ficar < 0.8× a do r27m, a leitura registra "cabeça herdada degrada".
- **Bateria (Task 7):** entra o w27d se a P7 passar, em `medium` (~11 h). O o27q8 continua fora.
- **Se o w27d passar a P7:** o próximo teste é o `scottlowry/…-oQ8e-mtp` @ `c7dfaa06` (30 GB, download), equivalente direto ao pack 8-bit do r27d. Fica fora desta campanha.

**Corte de 13/10, 15:00 (pedido do usuário: só os stacks com potencial de serem os mais rápidos e com melhor cache).** O P0 do s27r a 128K levou ~2 h 45 min por esforço, contra ~45 min supostos; a campanha completa passaria de 60 h. Ficam por padrão: P0 (s27r, sem o `medium` a 128K, que nenhuma decisão lê), P1 (k27), P3 (r27d), P7 (w27d) e P2 só com o o27q4. Saem para `PHASES_LATER` (rodam só com `--only`): P4 (o27sw), P8 (r27m, w27m) e P6 (l27n, l27). O o27q8 sai: 8-bit no oMLX decodifica abaixo do o27q4 e o r27d já cobre o 8-bit. A bateria (Task 7) é revista antes de rodar, porque ainda cita o o27sw.

**Escopo B de 13/10, 15:05 (escolha do usuário, a partir de um report público e da sessão "Flash-Next vs 27B").** O P1 (k27, Splash) é o único teste que ataca o TTFT quente do `tool_turn`. A campanha roda P0 → P1 e para se o P1 não passar (`STOP_UNLESS_PASS=P1`; regra do P1: `T_turno ≤ 0.75 × s27r` a 128K, ou seja ≤ 19.3 s, e todos os gates que o Splash reporta). Se o P1 passar, seguem P3 (r27d) e P7 (w27d). O P2 vira opcional, só com o o27q8 (repin `6c76ddfb82af`), para corrigir o `27b-summary.md`: `--only P2`. P4, P8 e P6 ficam só com `--only`; o P4 se pula sozinho porque o o27q4 não está em nenhuma fase.

**Como a campanha muda de ordem:** o `run-campaign.sh` lê a ordem do `phases.sh` só no início. O Task 5b implementa P7, P8 e a nova ordem; depois, a campanha para numa fronteira entre braços e reinicia. A retomada pula os braços com resultado completo (≥ 13 linhas), então nada medido se perde.

**Encerramento 14/10.** O usuário encerrou a campanha às 06:35 UTC, depois da P3; a P7 e o resto não rodaram. P0: o s27r reproduziu a referência de 08/10 (17.0 / 25.7 s em `xhigh`). P1 passou: o k27 (Splash 1.3.1 + DFlash2) fez 13.3 / 17.7 s em `xhigh` e 10.4 / 15.9 s em `medium`, razão 0.689 a 128K, e é o stack mais rápido medido para o 27B denso. P3 falhou: o r27d (mlx-serve 26.10.2 + drafter) fez 19.9 / 44.7 s, razões 1.171 / 1.739, com decode de 15.1 tok/s a 128K. `P5_GO=0`: o melhor 27B fica em 1.85× o driver Flash-Next a 128K, e o NO-GO como driver continua. A bateria de qualidade não rodou. Dados, aprendizados e próximos passos: [results/summary.md](results/summary.md).

---

## Mapa de arquivos

| Arquivo | Papel |
|---|---|
| `bench/qwen38-27b-next-steps-2026-10/plan.md` | Este runbook |
| `bench/qwen38-27b-next-steps-2026-10/scripts/run-arm.sh` | Envolve `run-candidate.sh` com `results/` e `logs/` desta campanha |
| `bench/qwen38-27b-next-steps-2026-10/scripts/run-campaign.sh` | Orquestrador autônomo: fases, gates, decisões, driver diário |
| `bench/qwen38-27b-next-steps-2026-10/scripts/phases.sh` | Definição das fases (specs `arm:ctx:reps:tag:effort`, base, regra) lida pelo orquestrador |
| `bench/qwen38-27b-next-steps-2026-10/scripts/empty_answers.py` | Conta respostas vazias em JSONL do `think_turn_probe` e da bateria |
| `bench/qwen38-27b-next-steps-2026-10/scripts/run-llama-27b.sh` | Launcher llama-server do 27B GGUF (`L27M` com draft-mtp, `L27N` sem) |
| `bench/qwen38-27b-next-steps-2026-10/scripts/render_27b_page.py` | Gera `reports/qwen38-27b-stacks.html` a partir dos JSON da campanha |
| `bench/qwen38-27b-next-steps-2026-10/tests/` | pytest dos scripts acima e dos braços novos |
| `bench/qwen38-27b-next-steps-2026-10/results/` | JSONL do probe, `props/`, `etapaN-*.md`, `gates.env`, `downloads.json`, `q/`, `think/`, `loops/`, `page-data.json` |
| `bench/qwen3.8-prefix-cache/scripts/run-splash.sh` | Launcher do Splash (novo; lê `config/splash-flags.env`) |
| `bench/qwen3.8-prefix-cache/config/splash-flags.env` | Flags do Splash descobertas no Task 2 |
| `bench/qwen3.8-prefix-cache/config/omlx-arms.json` | Modelos `oq8e-refit`, `oq4e-refit`, `swift-oq4e`; braços `T8R`, `T4R`, `TSW` |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | `FLASHNEXT_EFFORT`; blocos `k27`, `o27q8`, `o27q4`, `o27sw`, `r27m`, `r27d`, `l27`, `l27n` |
| `bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh` | Portas 8484 e 8585; `--print-ports` |
| `bench/flashnext-next-steps-2026-10/scripts/decide.py` | `--skip-gates` |
| `bench/flashnext-next-steps-2026-10/scripts/run-battery.sh` | `BATTERY_CAMPAIGN_DIR` |
| `bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh` | `MLX_TAG` por variável; alvo `splash` |
| `docs/models/qwen3.8-27b.md` | Card do modelo (não existia) |
| `reports/qwen38-27b-stacks.html`, `reports/index.html` | Página e card na seção `#dense` |

## Braços

| Braço | Runtime | Pack (revisão) | Porta | Launcher / arm | Fase |
|---|---|---|---|---|---|
| `s27r` | mlx-dspark 0.20.3 + DFlash2, `--prefix-cache-rungs 1024` | mlx-community 8bit `815b83c0` | 8484 | `run-mlx-dspark.sh S` | P0 (controle) |
| `k27` | Splash 1.3.1 | mlx-community 8bit `815b83c0` + DFlash2 `dedf8df6` | 8585 | `run-splash.sh K` | P1 |
| `o27q8` | oMLX 0.7.1.dev1 | Jundot oQ8e-mtp `6c76ddfb82af` | 8000 | `run-omlx.sh T8R` | P2 |
| `o27q4` | oMLX 0.7.1.dev1 | Jundot oQ4e-mtp `49c1d60367d9` | 8000 | `run-omlx.sh T4R` | P2 |
| `r27d` | mlx-serve 26.10.2, só drafter DFlash2 embutido (`--no-mtp`) | ddalcu 8bit `7775059e955f` | 11234 | `run-mlx-serve.sh C` | P3 |
| `r27m` | mlx-serve 26.10.2, só MTP nativa (`--no-drafter --mtp-max-depth 3`) | ddalcu 8bit `7775059e955f` | 11234 | `run-mlx-serve.sh C` | P8 |
| `w27d` | mlx-serve 26.10.2, só DFlash2 (`--no-mtp --drafter <ddalcu>/drafter`) | scottlowry Swift-1.5 oQ4e-mtp `881dc1914f65` | 11234 | `run-mlx-serve.sh C` | P7 |
| `w27m` | mlx-serve 26.10.2, só MTP herdada (`--no-drafter --mtp-max-depth 3`) | scottlowry Swift-1.5 oQ4e-mtp `881dc1914f65` | 11234 | `run-mlx-serve.sh C` | P8 |
| `o27sw` | oMLX 0.7.1.dev1 | scottlowry Swift-1.5 oQ4e-mtp `881dc1914f65` | 8000 | `run-omlx.sh TSW` | P4 |
| `l27` | llama.cpp b11569, `--spec-type draft-mtp` | ggml-org Q8_0 + mtp Q8_0 `71bc7b627595` | 8080 | `run-llama-27b.sh L27M` | P6 |
| `l27n` | llama.cpp b11569, sem spec | ggml-org Q8_0 `71bc7b627595` | 8080 | `run-llama-27b.sh L27N` | P6 |

Nomes de arquivo: `<arm>-<ctx>-t1.0-<tag>.jsonl`, tag `p<fase><x|m>` (`p1x` = fase 1, `xhigh`). O `run-seq.sh` exige braço e tag em `[a-z0-9]+`.

## Modelo de resultado

Cada fase termina com `results/etapa<N>-<nome>.md` escrito pelo `decide.py --out-md` (tabela fixa `braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles`, razão e `VERDICT`), seguido por `## Respostas vazias` (saída do `empty_answers.py`) e `## Leitura` (prosa). O orquestrador grava `P<N>_PASS=0|1` e, quando couber, `P<N>_BEST=<arm>` em `results/gates.env`.

---

### Task 0: Esqueleto da campanha, spec no lugar certo e correções do harness

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/scripts/run-arm.sh`
- Create: `bench/qwen38-27b-next-steps-2026-10/scripts/empty_answers.py`
- Create: `bench/qwen38-27b-next-steps-2026-10/tests/test_empty_answers.py`
- Create: `bench/qwen38-27b-next-steps-2026-10/tests/test_harness_fixes.py`
- Modify: `bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh:3,18,21`
- Modify: `bench/flashnext-next-steps-2026-10/scripts/decide.py:87-112,118-127`
- Modify: `bench/flashnext-next-steps-2026-10/scripts/run-battery.sh:24-27`
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh:33,385-392,508`
- Move: `reports/Qwen38 27B denso melhor stack.md` → `research/qwen38-27b-next-steps-20261013.md`; `research_notes/Qwen38 27B denso melhor stack/` → `research/qwen38-27b-next-steps-20261013-notes/`

**Interfaces:**
- Produces: `run-arm.sh <arm> <ctx> [opções do run-candidate]`; `FLASHNEXT_EFFORT=xhigh|medium|low` (default `xhigh`) lido pelo `run-candidate.sh` e impresso por `--print` como `effort: <v>`; `decide.py --skip-gates a,b`; `idle-gate.sh --print-ports` imprime `11234 8000 8080 8484 8585`; `run-battery.sh` honra `BATTERY_CAMPAIGN_DIR`; `empty_answers.py FILES… [--json]` imprime `empty=<n> of <m> stop records` e sai 0 (ou 1 com `--fail-on-any` e n > 0).

- [ ] **Step 1: Criar a branch e mover o spec**

```bash
cd ~/LocalProjects/macstudio-local-llm
git checkout -b bench/qwen38-27b-next-steps-2026-10
git add "reports/Qwen38 27B denso melhor stack.md" research_notes
git mv "reports/Qwen38 27B denso melhor stack.md" research/qwen38-27b-next-steps-20261013.md
git mv "research_notes/Qwen38 27B denso melhor stack" research/qwen38-27b-next-steps-20261013-notes
rmdir research_notes
mkdir -p bench/qwen38-27b-next-steps-2026-10/{scripts,tests,results,logs}
grep -c '\.\./bench/' research/qwen38-27b-next-steps-20261013.md
```
Expected: o `grep` imprime um número > 0 (os links relativos `../bench/…` continuam válidos, porque `research/` e `reports/` têm a mesma profundidade). `git status --short` mostra `R` para o relatório e as cinco notas.

- [ ] **Step 2: Escrever o teste do `run-arm.sh` e do `FLASHNEXT_EFFORT`**

```python
# bench/qwen38-27b-next-steps-2026-10/tests/test_harness_fixes.py
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
FN = ROOT / "bench/flashnext-next-steps-2026-10/scripts"


def _env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "AB_", "BATTERY_"))}
    env.update(extra)
    return env


def _print(arm, ctx="32768", **extra):
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), arm, ctx, "--print"],
                         capture_output=True, text=True, env=_env(**extra))
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_run_arm_writes_into_this_campaign():
    out = _print("s27r")
    assert "saida: " + str(C / "results") in out


def test_effort_defaults_to_xhigh_and_is_printed():
    assert "effort: xhigh" in _print("s27r")
    assert "effort: medium" in _print("s27r", FLASHNEXT_EFFORT="medium")


def test_effort_rejects_high():
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), "s27r", "32768", "--print"],
                         capture_output=True, text=True, env=_env(FLASHNEXT_EFFORT="high"))
    assert out.returncode == 64
    assert "effort" in out.stderr


def test_idle_gate_lists_dspark_and_splash_ports():
    out = subprocess.run(["bash", str(FN / "idle-gate.sh"), "--print-ports"],
                         capture_output=True, text=True, env=_env())
    assert out.returncode == 0
    assert out.stdout.split() == ["11234", "8000", "8080", "8484", "8585"]


def test_run_battery_honours_campaign_dir():
    out = subprocess.run(["bash", str(FN / "run-battery.sh"), "s27r", "q", "--print"],
                         capture_output=True, text=True,
                         env=_env(BATTERY_CAMPAIGN_DIR=str(C)))
    assert out.returncode == 0, out.stderr
    assert str(C / "results") in out.stdout
```

- [ ] **Step 3: Rodar o teste e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_harness_fixes.py -q`
Expected: 5 falhas (`run-arm.sh` não existe; `effort:` não é impresso; `--print-ports` desconhecido; `BATTERY_CAMPAIGN_DIR` ignorado).

- [ ] **Step 4: Escrever `run-arm.sh`**

```bash
#!/usr/bin/env bash
# Runs one arm through the 2026-09 driver with results and logs inside this campaign.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FLASHNEXT_RESULTS_DIR="$HERE/results" FLASHNEXT_LOGS_DIR="$HERE/logs"
exec bash "$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh" "$@"
```
Run: `chmod +x bench/qwen38-27b-next-steps-2026-10/scripts/run-arm.sh`

- [ ] **Step 5: `FLASHNEXT_EFFORT` no `run-candidate.sh`**

Logo após o parse de opções (depois da linha 33, antes do primeiro uso de `$CAND`), inserir:

```bash
EFFORT="${FLASHNEXT_EFFORT:-xhigh}"
case "$EFFORT" in xhigh|medium|low) ;; *) echo "run-candidate: FLASHNEXT_EFFORT must be xhigh, medium or low: $EFFORT" >&2; exit 64 ;; esac
```
Na linha 508 trocar `--reasoning-effort xhigh` por `--reasoning-effort "$EFFORT"`. No bloco `--print` (linhas 385-392), acrescentar `echo "effort: $EFFORT"` antes da linha `saida:`.

- [ ] **Step 6: Portas 8484 e 8585 no `idle-gate.sh`**

Substituir a lista fixa das linhas 3, 18 e 21 por uma variável e adicionar `--print-ports`:

```bash
PORTS=(11234 8000 8080 8484 8585)   # mlx-serve, oMLX/MTPLX, llama.cpp, mlx-dspark, Splash
```
No parse de opções: `--print-ports) echo "${PORTS[*]}"; exit 0 ;;`. Na linha 18, usar `ports ${PORTS[*]} must be free`. Na linha 21, `for p in "${PORTS[@]}"; do`. Atualizar o comentário da linha 3.

- [ ] **Step 7: `BATTERY_CAMPAIGN_DIR` no `run-battery.sh`**

Trocar a linha 24 (`HERE=…`) por:

```bash
HERE="${BATTERY_CAMPAIGN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
```
Conferir que `AB_RESULTS` e o `run-arm.sh` chamado derivam de `$HERE` (linhas seguintes já usam `$HERE/results` e `$HERE/scripts/run-arm.sh`).

- [ ] **Step 8: Rodar o teste e ver passar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_harness_fixes.py -q`
Expected: `5 passed`.

- [ ] **Step 9: Teste do `--skip-gates` do `decide.py` e do `empty_answers.py`**

```python
# bench/qwen38-27b-next-steps-2026-10/tests/test_empty_answers.py
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "bench/qwen38-27b-next-steps-2026-10/scripts"))
sys.path.insert(0, str(ROOT / "bench/flashnext-next-steps-2026-10/scripts"))
import empty_answers  # noqa: E402
import decide  # noqa: E402


def test_think_turn_record_empty_when_content_zero():
    assert empty_answers.is_empty({"finish_reason": "stop", "content_chars": 0, "reasoning_chars": 900})
    assert not empty_answers.is_empty({"finish_reason": "stop", "content_chars": 12})
    assert not empty_answers.is_empty({"finish_reason": "length", "content_chars": 0})


def test_bench2_record_empty_when_raw_response_blank():
    assert empty_answers.is_empty({"finish_reason": "stop", "raw_response": "  \n"})
    assert not empty_answers.is_empty({"finish_reason": "stop", "raw_response": "B"})


def test_if_probe_and_toolbench_records():
    assert empty_answers.is_empty({"finish_reason": "stop", "content_preview": ""})
    assert not empty_answers.is_empty({"finish_reason": "stop", "raw_message": {"content": "ok"}})
    assert empty_answers.is_empty({"finish_reason": "stop", "raw_message": {"content": ""}})


def test_count_over_files(tmp_path):
    f = tmp_path / "a.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in [
        {"finish_reason": "stop", "content_chars": 0},
        {"finish_reason": "stop", "content_chars": 5},
        {"finish_reason": "length", "content_chars": 0},
    ]) + "\n")
    assert empty_answers.count([f]) == (1, 2)


def _rows(arm, ctx, hit):
    base = {"arm": arm, "context_target": ctx, "finish_reason": "stop", "error": None, "correct": True,
            "decode_tps": 40.0, "ttft_ms": 5000, "cache_hit_ratio": hit, "swap_delta_gb": 0.0,
            "session_id": f"s-{arm}", "runtime": "splash"}
    return [dict(base, scenario=s) for s in ("cold", "identical", "append", "tool_turn")]


def test_decide_skip_gates_ignores_hit(tmp_path, capsys):
    (tmp_path / "logs").mkdir()
    for arm, hit in (("s27r", 0.99), ("k27", 0.0)):
        with (tmp_path / f"{arm}-32768-t1.0-p1x.jsonl").open("w") as fh:
            for r in _rows(arm, 32768, hit):
                fh.write(json.dumps(r) + "\n")
    argv = ["--results-dir", str(tmp_path), "--logs-dir", str(tmp_path / "logs"), "--glob", "*-p1x.jsonl",
            "--base", "s27r", "--cand", "k27", "--ctx", "32768", "--mode", "le", "--threshold", "1.03"]
    assert decide.main(argv) == 1
    assert "hit_append" in capsys.readouterr().out
    assert decide.main(argv + ["--skip-gates", "hit_append,hit_tool_turn"]) == 0
```

- [ ] **Step 10: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_empty_answers.py -q`
Expected: `ModuleNotFoundError: empty_answers` e, depois de criar o módulo, falha no `--skip-gates` (`unrecognized arguments`).

- [ ] **Step 11: Escrever `empty_answers.py`**

```python
#!/usr/bin/env python3
"""Count empty final answers (finish_reason stop with no visible content) in campaign JSONL files.

Handles three record shapes: think_turn_probe (content_chars), bench2 / if_probe (raw_response,
content_preview) and tool_call_bench (raw_message.content). Any other record is not empty.
usage: empty_answers.py [--json] [--fail-on-any] FILE...
"""
import argparse, json, sys
from pathlib import Path


def is_empty(rec: dict) -> bool:
    if rec.get("finish_reason") != "stop":
        return False
    if "content_chars" in rec:
        return rec["content_chars"] == 0
    if "raw_response" in rec:
        return not (rec.get("raw_response") or "").strip()
    if "content_preview" in rec:
        return not (rec.get("content_preview") or "").strip()
    if isinstance(rec.get("raw_message"), dict):
        return not (rec["raw_message"].get("content") or "").strip()
    return False


def count(files) -> tuple[int, int]:
    empty = stops = 0
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("finish_reason") == "stop":
                stops += 1
                empty += is_empty(rec)
    return empty, stops


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-any", action="store_true")
    a = ap.parse_args(argv)
    empty, stops = count(a.files)
    if a.json:
        print(json.dumps({"empty": empty, "stop_records": stops}))
    else:
        print(f"empty={empty} of {stops} stop records")
    return 1 if (a.fail_on_any and empty) else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 12: `--skip-gates` no `decide.py`**

Em `main()` (linhas 118-127) acrescentar `ap.add_argument("--skip-gates", default="", help="comma list of gate names to ignore, e.g. hit_append,hit_tool_turn")`. Passar `set(filter(None, a.skip_gates.split(",")))` para `decide(...)` como novo parâmetro `skip: set[str]` (default `frozenset()`), e nas duas verificações de gates (linhas 101-104) usar:

```python
        kf = [g for g in k["gates_failed"] if g.split("<")[0] not in skip]
        bf = [g for g in b["gates_failed"] if g.split("<")[0] not in skip]
        if kf:
            reasons.append(f"gates {cand}@{c // 1024}K: {','.join(kf)}")
        if bf:
            reasons.append(f"gates {base}@{c // 1024}K: {','.join(bf)}")
```
(`summarize_driver.py` grava o gate de hit como `hit_append<0.90`; o `split("<")` compara só o nome.) Na linha `Regra:` acrescentar `, ignorando {', '.join(sorted(skip))}` quando `skip` não for vazio. Confirmar que `main()` devolve o código em vez de chamar `sys.exit` direto (o teste chama `decide.main(argv)`); se hoje faz `sys.exit(main())`, manter essa forma e garantir que `main` retorna `int`.

- [ ] **Step 13: Rodar os dois arquivos de teste e os testes das campanhas tocadas**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests bench/flashnext-next-steps-2026-10/tests bench/qwen38-flashnext-daily-driver-2026-09/tests bench/engine-updates-2026-10/tests -q 2>&1 | tail -3`
Expected: todos os testes novos passam. Se `bench/flashnext-next-steps-2026-10/tests/test_scripts.py` falhar em `test_idle_gate_*` por edições locais não commitadas dessa campanha (memória via macmon, `IDLE_MAX_POLLS`), registrar as falhas em `results/etapa0-preflight.md` e não as corrigir aqui: pertencem à outra campanha.

- [ ] **Step 14: Commit**

```bash
git add research bench/qwen38-27b-next-steps-2026-10 bench/flashnext-next-steps-2026-10/scripts bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh
git commit -m "bench(qwen38-27b): campaign skeleton, spec under research/, harness fixes

Move the 27B research report and its notes to research/. Add run-arm.sh,
empty_answers.py, FLASHNEXT_EFFORT in run-candidate.sh, --skip-gates in
decide.py, ports 8484/8585 in idle-gate.sh, BATTERY_CAMPAIGN_DIR in
run-battery.sh.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: Preflight no rig e downloads fixados

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/results/etapa0-preflight.md`
- Create: `bench/qwen38-27b-next-steps-2026-10/results/downloads.json` (gerado pelo `fetch_pack.py`)

**Interfaces:**
- Consumes: `bench/flashnext-next-steps-2026-10/scripts/fetch_pack.py --repo --revision [--include] --reserve-gb --receipt`.
- Produces: diretórios de pesos em `~/.cache/local-llms/qwen3.8-prefix-cache/<org>-<repo>-<sha40>` para os cinco packs novos; `downloads.json` com `revision`, `local_dir`, `bytes`.

- [ ] **Step 1: Publicar a branch e atualizar o rig**

```bash
git push -u origin bench/qwen38-27b-next-steps-2026-10
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git status --short && git fetch origin && git checkout bench/qwen38-27b-next-steps-2026-10 && git pull --ff-only && git log -1 --oneline'
```
Expected: `git status --short` vazio antes do checkout (se houver arquivo rastreado modificado, parar e perguntar ao usuário); a última linha mostra o commit do Task 0.

- [ ] **Step 2: Preflight de versões, disco e portas**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && C=$PWD/bench/qwen38-27b-next-steps-2026-10 && {
  echo "# Etapa 0 — preflight $(date -u +%FT%TZ)"; echo
  echo "## Runtimes"; for d in ~/.local/opt/qwen38/*/; do echo "- $d"; done
  echo; echo "## Versions"
  ~/.local/opt/qwen38/mlx-dspark-v0.20.3/bin/mlx-dspark --version 2>&1 | head -1
  ~/.local/opt/qwen38/omlx-v0.7.1.dev1/bin/omlx --version 2>&1 | head -1
  ~/.local/opt/qwen38/llama-b11569/llama-server --version 2>&1 | head -2
  /opt/homebrew/bin/macmon --version; sw_vers | tr "\n" " "; echo
  echo; echo "## Disk"; df -g / | tail -1
  echo; echo "## Ports"; for p in 11234 8000 8080 8484 8585; do printf "%s: " $p; lsof -nP -tiTCP:$p -sTCP:LISTEN || echo free; done
  echo; echo "## Weights on disk"; ls -1 ~/.cache/local-llms/qwen3.8-prefix-cache | grep -i "27B"
} | tee $C/results/etapa0-preflight.md'
```
Expected: `omlx` 0.7.1.dev1 e `llama-server` b11569 presentes (se faltar algum, o Task 2 instala e anota aqui); `sw_vers` ≥ 26.4 (exigência do Splash; se < 26.4, P1 é cancelado e registrado); disco livre ≥ 400 GB; só a porta 11234 ocupada (driver diário).

- [ ] **Step 3: Baixar os packs com revisão fixada**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && C=$PWD/bench/qwen38-27b-next-steps-2026-10 && PY=~/LocalProjects/local-llms/.venv/bin/python && F=bench/flashnext-next-steps-2026-10/scripts/fetch_pack.py && R="--reserve-gb 150 --receipt $C/results/downloads.json" &&
 $PY $F --repo Jundot/Qwen3.8-27B-oQ8e-mtp --revision 6c76ddfb82af $R &&
 $PY $F --repo Jundot/Qwen3.8-27B-oQ4e-mtp --revision 49c1d60367d9 $R &&
 $PY $F --repo ddalcu/Qwen3.8-27B-MLX-Serve-8bit --revision 7775059e955f $R &&
 $PY $F --repo scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp --revision 881dc1914f65 $R &&
 $PY $F --repo ggml-org/Qwen3.8-27B-GGUF --revision 71bc7b627595 --include "*Q8_0*.gguf" --include "mtp-*Q8_0*.gguf" $R &&
 python3 -c "import json,sys; [print(r[\"repo\"], r[\"revision\"][:12], round(r[\"bytes\"]/1e9,1), \"GB\") for r in map(json.loads, open(\"$C/results/downloads.json\"))]"'
```
Expected: cinco linhas `DEST=…`; a última impressão lista os cinco repos com ~30.0, ~17.0, ~35.0, ~17.0 e ~31.8 GB. Se algum revision não existir mais no Hub (exit ≠ 0 com `RevisionNotFound`), parar e registrar em `etapa0-preflight.md`; não trocar a revisão sem anotar.

- [ ] **Step 4: Validar o layout dos packs MLX**

```bash
ssh vitor@mac-studio 'for p in Jundot-Qwen3.8-27B-oQ8e-mtp-6c76ddfb82af Jundot-Qwen3.8-27B-oQ4e-mtp-49c1d60367d9 ddalcu-Qwen3.8-27B-MLX-Serve-8bit-7775059e955f scottlowry-Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc1914f65; do d=$(ls -d ~/.cache/local-llms/qwen3.8-prefix-cache/$p* | head -1); echo "== $d"; ls $d | head -20; python3 -c "import json;c=json.load(open(\"$d/config.json\"));print(\"arch:\", c.get(\"architectures\"), \"| quant:\", c.get(\"quantization\", {}).get(\"bits\"))"; done; ls -la ~/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-7775059e955f*/drafter 2>&1 | head'
```
Expected: cada pack tem `config.json`, `model.safetensors.index.json` e `chat_template.jinja`; o pack ddalcu tem a pasta `drafter/` (DFlash2 embutido). Anexar a saída em `etapa0-preflight.md` sob `## Pack layout`.

- [ ] **Step 5: Validar o template do 27B para os valores de esforço**

```bash
ssh vitor@mac-studio 'd=$(ls -d ~/.cache/local-llms/qwen3.8-prefix-cache/Jundot-Qwen3.8-27B-oQ4e-mtp-49c1d60367d9* | head -1); grep -o "reasoning_effort[^}]*" $d/chat_template.jinja | head -5; grep -c "xhigh" $d/chat_template.jinja; grep -o "preserve_thinking[^}]*" $d/chat_template.jinja | head -2'
```
Expected: o template referencia `reasoning_effort` com `xhigh`, `medium` e `low` e `preserve_thinking`. Se aparecer `high` como valor aceito, registrar em `etapa0-preflight.md` (muda o Global Constraint sobre `high`).

- [ ] **Step 6: Commit do preflight e dos recibos (feito no rig)**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git add bench/qwen38-27b-next-steps-2026-10/results && git commit -m "bench(qwen38-27b): Task 1 - preflight and pinned downloads

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push'
```
Expected: commit com `etapa0-preflight.md` e `downloads.json`. Depois, no MacBook: `git pull --ff-only`.

---

### Task 2: Runtimes novos — Splash 1.3.1 e mlx-serve 26.10.2 — e descoberta de flags

**Files:**
- Modify: `bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh` (tag por variável; alvo `splash`)
- Create: `bench/qwen3.8-prefix-cache/config/splash-flags.env`
- Create: `bench/qwen38-27b-next-steps-2026-10/results/install-runtimes.md`
- Create: `bench/qwen38-27b-next-steps-2026-10/results/splash-help.txt`, `results/mlx-serve-26102-help.txt`, `results/mlx-serve-26102-no-drafter-flag.txt`
- Test: `bench/qwen38-27b-next-steps-2026-10/tests/test_install_runtime.py`

**Interfaces:**
- Produces: `~/.local/opt/qwen38/splash-v1.3.1/bin/splash` (ou o layout que o release trouxer; o caminho real fica em `splash-flags.env` como `SPLASH_BIN`); `~/.local/opt/qwen38/mlx-serve-v26.10.2/mlx-serve` com `--version` = `mlx-serve 26.10.2`; `splash-flags.env` com `SPLASH_BIN`, `SPLASH_FLAG_MODEL`, `SPLASH_FLAG_DRAFTER`, `SPLASH_FLAG_PORT`, `SPLASH_FLAG_HOST`, `SPLASH_FLAG_CTX`, `SPLASH_SERVE_SUBCMD`, `SPLASH_EXTRA_ARGS`; `mlx-serve-26102-no-drafter-flag.txt` com a flag exata que desliga o drafter embutido (ou a palavra `NONE`).

- [ ] **Step 1: Teste do `install-runtime.sh` parametrizado**

```python
# bench/qwen38-27b-next-steps-2026-10/tests/test_install_runtime.py
import os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALL = ROOT / "bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh"


def _run(*args, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("QWEN38_", "MLX_TAG", "INSTALL_"))}
    e.update(env)
    return subprocess.run(["bash", str(INSTALL), *args, "--print"], capture_output=True, text=True, env=e)


def test_mlx_tag_override_changes_destination():
    out = _run("mlx-serve", MLX_TAG="v26.10.2")
    assert out.returncode == 0, out.stderr
    assert "mlx-serve-v26.10.2/" in out.stdout
    assert "pre-release" not in out.stdout


def test_default_mlx_tag_is_unchanged():
    out = _run("mlx-serve")
    assert "mlx-serve-v26.10.2-pre-release.1/" in out.stdout


def test_splash_target_prints_release_url_and_dest():
    out = _run("splash")
    assert out.returncode == 0, out.stderr
    assert "github.com/incoai/splash/releases/download/v1.3.1/" in out.stdout
    assert "splash-v1.3.1/" in out.stdout
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_install_runtime.py -q`
Expected: 2 falhas (`MLX_TAG` ignorado; `splash` é uso inválido, exit 64).

- [ ] **Step 3: Parametrizar e adicionar o alvo `splash`**

No `install-runtime.sh`, trocar `MLX_TAG=v26.10.2-pre-release.1` por `MLX_TAG="${MLX_TAG:-v26.10.2-pre-release.1}"` e acrescentar `SPLASH_TAG="${SPLASH_TAG:-v1.3.1}"`. Adicionar o caso `splash)` ao lado de `llama)`:

```bash
  splash)
    DEST="$OPT/splash-$SPLASH_TAG"
    ASSET_URL="https://github.com/incoai/splash/releases/download/$SPLASH_TAG/splash-macos-arm64.tar.gz"
    SHA_URL="https://github.com/incoai/splash/releases/download/$SPLASH_TAG/splash-macos-arm64.tar.gz.sha256"
    ;;
```
O resto do fluxo (`--print` imprime `DEST` e `ASSET_URL`; download no MacBook, SHA conferido, `scp`, extração com `--strip-components=1`) é o mesmo do caso `mlx-serve`. Se o nome do asset do release 1.3.1 for outro (conferir em `https://github.com/incoai/splash/releases/tag/v1.3.1` no MacBook), ajustar `ASSET_URL` e o teste no mesmo commit. Se o Splash só for distribuído como pacote Python, trocar o caso para `uv venv --python 3.13 "$DEST" && "$DEST/bin/pip" install "splash-engine==1.3.1"` seguindo o caso `omlx`, e o teste passa a conferir `splash-v1.3.1/` apenas.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_install_runtime.py bench/flashnext-next-steps-2026-10/tests -q 2>&1 | tail -2`
Expected: os 3 novos passam; a contagem dos testes da flashnext-next-steps não muda em relação ao Task 0 Step 13.

- [ ] **Step 5: Instalar o mlx-serve 26.10.2 final no rig**

```bash
cd ~/LocalProjects/macstudio-local-llm && git add bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh bench/qwen38-27b-next-steps-2026-10 && git commit -qm "bench(qwen38-27b): Task 2 - install-runtime.sh tag override and splash target

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git pull --ff-only -q && MLX_TAG=v26.10.2 bash bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh mlx-serve 2>&1 | tail -5 && ~/.local/opt/qwen38/mlx-serve-v26.10.2/mlx-serve --version'
```
Expected: última linha `mlx-serve 26.10.2`. Se o `gh` do rig não autenticar (401, como na campanha anterior), baixar o tarball no MacBook, conferir o SHA256 publicado, `scp` para `/tmp` do rig e rodar com `INSTALL_LOCAL_ASSET=/tmp/<arquivo>` se o script suportar; senão extrair à mão em `~/.local/opt/qwen38/mlx-serve-v26.10.2/` e registrar o SHA em `install-runtimes.md`.

- [ ] **Step 6: Registrar `--help` do 26.10.2 e descobrir a flag que desliga o drafter embutido**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && C=$PWD/bench/qwen38-27b-next-steps-2026-10 && ~/.local/opt/qwen38/mlx-serve-v26.10.2/mlx-serve --help > $C/results/mlx-serve-26102-help.txt 2>&1; grep -iE "drafter|mtp-(min|max)-depth|preserve.thinking|kv-quant" $C/results/mlx-serve-26102-help.txt'
```
Expected: linhas com `--drafter`, `--mtp-min-depth`, `--mtp-max-depth`. Decidir a flag sem drafter: se existir `--no-drafter`, gravar `--no-drafter`; se `--drafter` aceitar `none`/`off`, gravar `--drafter none`; se nada disso existir, gravar `NONE`. Comando: `echo "<flag>" > $C/results/mlx-serve-26102-no-drafter-flag.txt`. Com `NONE`, o braço `r27m` passa a usar uma cópia do pack sem a pasta `drafter/` (hardlinks: `cp -al <pack> <pack>-nodrafter && rm -rf <pack>-nodrafter/drafter`) e o Task 3 aponta `r27m` para essa cópia; registrar a escolha em `install-runtimes.md`.

- [ ] **Step 7: Instalar o Splash e registrar o `--help`**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && C=$PWD/bench/qwen38-27b-next-steps-2026-10 && bash bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh splash 2>&1 | tail -5; B=$(ls ~/.local/opt/qwen38/splash-v1.3.1/bin/splash ~/.local/opt/qwen38/splash-v1.3.1/splash 2>/dev/null | head -1); echo "BIN=$B"; $B --version; $B --help > $C/results/splash-help.txt 2>&1; $B serve --help >> $C/results/splash-help.txt 2>&1; grep -iE "serve|--model|--draft|--port|--host|context|openai|cache|effort|thinking" $C/results/splash-help.txt'
```
Expected: versão `1.3.1`; o help mostra um subcomando de servidor com flags de modelo, drafter, porta, host e contexto. Se não houver modo servidor OpenAI-compatível, escrever `P1_CANCELLED=1 # splash has no OpenAI server mode` em `results/gates.env`, registrar em `install-runtimes.md` e pular o Step 8.

- [ ] **Step 8: Escrever `splash-flags.env` a partir do help**

```bash
# bench/qwen3.8-prefix-cache/config/splash-flags.env — written from `splash --help` on 2026-10-NN (Task 2 Step 7).
# Only names of flags; run-splash.sh supplies the values. Keep every variable, set unused ones to "".
SPLASH_BIN="$HOME/.local/opt/qwen38/splash-v1.3.1/bin/splash"
SPLASH_SERVE_SUBCMD="serve"          # subcommand that starts the OpenAI-compatible server
SPLASH_FLAG_MODEL="--model"
SPLASH_FLAG_DRAFTER="--draft-model"  # DFlash2 drafter path flag, or "" if the engine finds it alone
SPLASH_FLAG_HOST="--host"
SPLASH_FLAG_PORT="--port"
SPLASH_FLAG_CTX="--context-length"   # max context flag, or "" if there is none
SPLASH_EXTRA_ARGS=""                 # word-split; e.g. "--kv-bits 8" if the help shows a KV option
SPLASH_HAS_CACHED_TOKENS=unknown     # set by the P1 smoke: yes|no
```
Substituir cada valor pelo nome real lido em `splash-help.txt`. Copiar o arquivo para o repo no MacBook (`scp vitor@mac-studio:~/LocalProjects/local-llms/bench/qwen3.8-prefix-cache/config/splash-flags.env bench/qwen3.8-prefix-cache/config/`) ou editá-lo no rig e commitar de lá.

- [ ] **Step 9: Registrar as instalações e commitar**

Escrever `results/install-runtimes.md` com: tag e SHA256 de cada tarball, caminhos finais, saída de `--version`, a flag escolhida para `r27m`, e o status do Splash (servidor OpenAI sim/não; macOS ≥ 26.4 sim/não).

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git add bench/qwen38-27b-next-steps-2026-10/results bench/qwen3.8-prefix-cache/config/splash-flags.env && git commit -m "bench(qwen38-27b): Task 2 - mlx-serve 26.10.2 and Splash 1.3.1 installs, flag discovery

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push'
```
No MacBook: `git pull --ff-only`.

---

### Task 3: Braços novos — launchers, config do oMLX e blocos no `run-candidate.sh`

**Files:**
- Create: `bench/qwen3.8-prefix-cache/scripts/run-splash.sh`
- Create: `bench/qwen38-27b-next-steps-2026-10/scripts/run-llama-27b.sh`
- Modify: `bench/qwen3.8-prefix-cache/config/omlx-arms.json` (modelos `oq8e-refit`, `oq4e-refit`, `swift-oq4e`; braços `T8R`, `T4R`, `TSW`)
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh:56-70` (variáveis) e um bloco novo após `s27|s27g|s27r)`
- Test: `bench/qwen38-27b-next-steps-2026-10/tests/test_arms.py`

**Interfaces:**
- Consumes: `pack_dir <prefix>` do `run-candidate.sh`; `run-omlx.sh <ARM>` com `OMLX_MODEL_ROOT`, `QWEN38_OMLX_BIN`, `QWEN38_OMLX_EXPECTED_VERSION`; `run-mlx-serve.sh C` com `QWEN38_MLX_*`; `splash-flags.env`.
- Produces: braços `k27 o27q8 o27q4 o27sw r27m r27d l27 l27n` aceitos por `run-arm.sh <arm> <ctx> --print`; `run-splash.sh K [--print]` imprime a linha de comando; `run-llama-27b.sh L27M|L27N [--print]`.

- [ ] **Step 1: Teste dos braços (`--print`)**

```python
# bench/qwen38-27b-next-steps-2026-10/tests/test_arms.py
import os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
NO_DRAFTER = (C / "results/mlx-serve-26102-no-drafter-flag.txt")


def _env():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "SPLASH_"))}


def _print(arm, ctx="32768"):
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), arm, ctx, "--print"],
                         capture_output=True, text=True, env=_env())
    assert out.returncode == 0, f"{arm}: {out.stderr}"
    return out.stdout


def _server_line(text):
    lines = text.splitlines()
    i = next(i for i, l in enumerate(lines) if l.startswith("launcher:"))
    return lines[i + 1]


def test_unknown_arm_is_rejected():
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), "zz9", "32768", "--print"],
                         capture_output=True, text=True, env=_env())
    assert out.returncode == 64


def test_omlx_refit_arms_use_0711_and_new_packs():
    for arm, pack, letter in (("o27q8", "Jundot-Qwen3.8-27B-oQ8e-mtp-6c76ddfb82af", "T8R"),
                              ("o27q4", "Jundot-Qwen3.8-27B-oQ4e-mtp-49c1d60367d9", "T4R"),
                              ("o27sw", "scottlowry-Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc1914f65", "TSW")):
        out = _print(arm)
        assert f"run-omlx.sh {letter}" in out
        assert "omlx-v0.7.1.dev1/bin/omlx" in out
        assert pack in out


def test_mlx_serve_27b_arms_use_26102_and_ddalcu_pack():
    d = _print("r27d")
    assert "mlx-serve-v26.10.2/mlx-serve" in _server_line(d)
    assert "ddalcu-Qwen3.8-27B-MLX-Serve-8bit-7775059e955f" in _server_line(d)
    for flag in ("--prefix-cache-mem 16GB", "--prefix-cache-disk 100GB", "--prefix-cache-entries 64", "--mtp-max-depth 3"):
        assert flag in _server_line(d)
    assert "--ple-gpu" not in _server_line(d)
    assert "--kv-quant" not in _server_line(d)


def test_r27m_disables_the_bundled_drafter():
    flag = NO_DRAFTER.read_text().strip() if NO_DRAFTER.exists() else "NONE"
    m, d = _server_line(_print("r27m")), _server_line(_print("r27d"))
    if flag == "NONE":
        assert "-nodrafter" in m and "-nodrafter" not in d
    else:
        assert flag in m and flag not in d


def test_splash_arm_uses_tokenizer_path_and_port_8585():
    out = _print("k27")
    assert "run-splash.sh K" in out
    s = _server_line(out)
    assert "8585" in s and "mlx-community--Qwen3.8-27B-8bit-815b83c0" in s and "DFlash2" in s
    assert "--tokenizer-path" in out


def test_llama_arms_flags():
    m, n = _server_line(_print("l27", "65536")), _server_line(_print("l27n", "65536"))
    for flag in ("-np 1", "--no-kv-unified", "-fa on", "-ngl 99", "-c 65536", "--jinja",
                 '"reasoning_effort":"medium"', "--alias qwen38-27b-gguf"):
        assert flag in m and flag in n
    assert "--spec-type draft-mtp" in m and "--spec-draft-n-max 2" in m and "mtp-Qwen3.8-27B-Q8_0.gguf" in m
    assert "--spec-type" not in n


def test_llama_effort_follows_env():
    out = subprocess.run(["bash", str(C / "scripts/run-arm.sh"), "l27", "65536", "--print"],
                         capture_output=True, text=True, env={**_env(), "FLASHNEXT_EFFORT": "xhigh"})
    assert '"reasoning_effort":"xhigh"' in _server_line(out.stdout)


def test_reference_arm_s27r_still_prints():
    assert "run-mlx-dspark.sh S" in _print("s27r") and "--prefix-cache-rungs 1024" in _print("s27r")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_arms.py -q`
Expected: todos menos `test_unknown_arm_is_rejected` e `test_reference_arm_s27r_still_prints` falham com `candidato desconhecido` (exit 64).

- [ ] **Step 3: Modelos e braços no `omlx-arms.json`**

Em `"models"` acrescentar:

```json
    "oq8e-refit": {"repository": "Jundot/Qwen3.8-27B-oQ8e-mtp", "revision": "6c76ddfb82af"},
    "oq4e-refit": {"repository": "Jundot/Qwen3.8-27B-oQ4e-mtp", "revision": "49c1d60367d9"},
    "swift-oq4e": {"repository": "scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp", "revision": "881dc1914f65"}
```
Em `"arms"`, ao lado de `"T"`, acrescentar três braços com as mesmas chaves e o `model_key` respectivo (`oq8e-refit` → `T8R`, `oq4e-refit` → `T4R`, `swift-oq4e` → `TSW`):

```json
    "T8R": {
      "model_key": "oq8e-refit",
      "cache_enabled": true,
      "model_settings": {
        "mtp_enabled": true,
        "mtp_adaptive_max_depth": 3,
        "dflash_enabled": false,
        "turboquant_kv_enabled": false,
        "specprefill_enabled": false,
        "qwen35_ane_prefill_enabled": false
      }
    }
```
Se `omlx_config.py` resolver o diretório do modelo pelo sha completo (`_target_model_dir`, linha 149) e o `revision` de 12 caracteres não casar, completar a revisão com o sha de 40 caracteres lido de `results/downloads.json` (campo `revision`). Se `validate_arm` (linha 155) rejeitar chaves desconhecidas em `model_settings`, acrescentar as três chaves novas à lista permitida no mesmo commit.

- [ ] **Step 4: Launcher `run-splash.sh`**

```bash
#!/usr/bin/env bash
# Starts the Splash engine (Inco AI) as an OpenAI-compatible server for one arm.
# Arms: K = mlx-community 8bit target + DFlash2 drafter, defaults from splash-flags.env.
# env: SPLASH_MODEL (target dir, required), SPLASH_DRAFTER (drafter dir, optional), QWEN38_CTX_SIZE (default 32768),
#      QWEN38_SPLASH_EXPECTED_VERSION (checked against `splash --version`), QWEN38_SPLASH_PORT (default 8585)
# usage: run-splash.sh K [--print]
set -euo pipefail
ARM="${1:?usage: $0 K [--print]}"; shift
PRINT=""; [[ "${1:-}" == --print ]] && PRINT=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/splash-flags.env
source "$HERE/config/splash-flags.env"
[[ "$ARM" == K ]] || { echo "run-splash: unknown arm: $ARM" >&2; exit 64; }
MODEL="${SPLASH_MODEL:?SPLASH_MODEL is required}"
CTX="${QWEN38_CTX_SIZE:-32768}"; PORT="${QWEN38_SPLASH_PORT:-8585}"
CMD=("$SPLASH_BIN" "$SPLASH_SERVE_SUBCMD" "$SPLASH_FLAG_MODEL" "$MODEL" "$SPLASH_FLAG_HOST" 0.0.0.0 "$SPLASH_FLAG_PORT" "$PORT")
[[ -n "${SPLASH_FLAG_CTX:-}" ]] && CMD+=("$SPLASH_FLAG_CTX" "$CTX")
[[ -n "${SPLASH_DRAFTER:-}" && -n "${SPLASH_FLAG_DRAFTER:-}" ]] && CMD+=("$SPLASH_FLAG_DRAFTER" "$SPLASH_DRAFTER")
# shellcheck disable=SC2206
[[ -n "${SPLASH_EXTRA_ARGS:-}" ]] && CMD+=($SPLASH_EXTRA_ARGS)
if [[ -n "$PRINT" ]]; then echo "${CMD[*]}"; exit 0; fi
[[ -f "$MODEL/config.json" ]] || { echo "run-splash: missing $MODEL/config.json" >&2; exit 66; }
if [[ -n "${QWEN38_SPLASH_EXPECTED_VERSION:-}" ]]; then
  v="$("$SPLASH_BIN" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  [[ "$v" == "$QWEN38_SPLASH_EXPECTED_VERSION" ]] || { echo "run-splash: version $v != $QWEN38_SPLASH_EXPECTED_VERSION" >&2; exit 65; }
fi
exec "${CMD[@]}"
```
O `run-candidate.sh` para o servidor com SIGTERM no wrapper e depois mata quem escuta na porta. O spec avisa que `pkill` faz o Splash renascer; por isso o launcher usa `exec`, para que o PID do wrapper seja o do servidor.

- [ ] **Step 5: Launcher `run-llama-27b.sh`**

```bash
#!/usr/bin/env bash
# llama-server for the dense Qwen3.8-27B GGUF (ggml-org Q8_0) on port 8080.
# Arms: L27M = --spec-type draft-mtp with the Q8_0 MTP head, n-max 2; L27N = no speculation.
# env: QWEN38_GGUF_DIR (required), QWEN38_CTX_SIZE (default 65536), QWEN38_LLAMA_SERVER_BIN,
#      FLASHNEXT_EFFORT (xhigh|medium|low, default medium; passed via --chat-template-kwargs)
# usage: run-llama-27b.sh L27M|L27N [--print]
set -euo pipefail
ARM="${1:?usage: $0 L27M|L27N [--print]}"; shift
PRINT=""; [[ "${1:-}" == --print ]] && PRINT=1
BIN="${QWEN38_LLAMA_SERVER_BIN:-$HOME/.local/opt/qwen38/llama-b11569/llama-server}"
DIR="${QWEN38_GGUF_DIR:?QWEN38_GGUF_DIR is required}"
CTX="${QWEN38_CTX_SIZE:-65536}"; EFFORT="${FLASHNEXT_EFFORT:-medium}"
case "$EFFORT" in xhigh|medium|low) ;; *) echo "run-llama-27b: bad effort $EFFORT" >&2; exit 64 ;; esac
MAIN="$(ls "$DIR"/Qwen3.8-27B-Q8_0*.gguf 2>/dev/null | grep -v '^.*/mtp-' | head -1 || true)"
MTP="$(ls "$DIR"/mtp-Qwen3.8-27B-Q8_0.gguf 2>/dev/null | head -1 || true)"
[[ -n "$PRINT" || -f "$MAIN" ]] || { echo "run-llama-27b: no Q8_0 gguf in $DIR" >&2; exit 66; }
MAIN="${MAIN:-$DIR/Qwen3.8-27B-Q8_0.gguf}"; MTP="${MTP:-$DIR/mtp-Qwen3.8-27B-Q8_0.gguf}"
CMD=("$BIN" -m "$MAIN" --host 0.0.0.0 --port 8080 --alias qwen38-27b-gguf -c "$CTX" -np 1 --no-kv-unified -fa on -ngl 99
     --jinja --chat-template-kwargs "{\"reasoning_effort\":\"$EFFORT\",\"preserve_thinking\":true}" --metrics)
case "$ARM" in
  L27M) CMD+=(--spec-type draft-mtp -md "$MTP" --spec-draft-n-max 2) ;;
  L27N) ;;
  *) echo "run-llama-27b: unknown arm: $ARM" >&2; exit 64 ;;
esac
if [[ -n "$PRINT" ]]; then echo "${CMD[*]}"; exit 0; fi
[[ "$ARM" == L27N || -f "$MTP" ]] || { echo "run-llama-27b: missing $MTP" >&2; exit 66; }
exec "${CMD[@]}"
```
Se o `llama-server --help` do b11569 (`~/.local/opt/qwen38/llama-b11569/llama-server --help | grep -E "spec-draft|kv-unified|-md"`) usar nomes diferentes, ajustar o launcher e o teste no mesmo commit e anotar em `install-runtimes.md`.

- [ ] **Step 6: Variáveis e blocos no `run-candidate.sh`**

Perto das linhas 56-70 acrescentar:

```bash
MLXSERVE_26102F="$OPT/mlx-serve-v26.10.2/mlx-serve"
SPLASH_131="$OPT/splash-v1.3.1"
DD27="$(pack_dir ddalcu-Qwen3.8-27B-MLX-Serve-8bit-7775059e955f)"
DD27_NODRAFTER="${DD27}-nodrafter"
OQ8E_R="$(pack_dir Jundot-Qwen3.8-27B-oQ8e-mtp-6c76ddfb82af)"
OQ4E_R="$(pack_dir Jundot-Qwen3.8-27B-oQ4e-mtp-49c1d60367d9)"
SW27="$(pack_dir scottlowry-Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc1914f65)"
GGUF27="$(pack_dir ggml-org-Qwen3.8-27B-GGUF-71bc7b627595)"
NO_DRAFTER_FLAG_FILE="$ROOT/bench/qwen38-27b-next-steps-2026-10/results/mlx-serve-26102-no-drafter-flag.txt"
```
(`pack_dir` devolve `…-MISSING` quando o pack não está no disco; o `--print` continua funcionando e o run real sai 66.) Depois do bloco `s27|s27g|s27r)` inserir:

```bash
    # --- Qwen3.8-27B next steps 2026-10 (bench/qwen38-27b-next-steps-2026-10) ---
    o27q8|o27q4|o27sw) LAUNCHER="$HARNESS/run-omlx.sh"; PORT=8000; RUNTIME=omlx; REV=v0.7.1.dev1
        PROBE_PY="$OMLX_0711/bin/python"; TOKENIZER=""; SERVER_NAME=omlx; METRICS=""
        export QWEN38_OMLX_BIN="$OMLX_0711/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.1.dev1 OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
        case "$CAND" in
          o27q8) ARM=T8R; MODEL_DIR="$OQ8E_R"; MODEL_REV=6c76ddfb82af ;;
          o27q4) ARM=T4R; MODEL_DIR="$OQ4E_R"; MODEL_REV=49c1d60367d9 ;;
          o27sw) ARM=TSW; MODEL_DIR="$SW27"; MODEL_REV=881dc1914f65 ;;
        esac ;;
    r27d|r27m) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=C; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.2
        MODEL_DIR="$DD27"; MODEL_REV=7775059e955f; PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
        export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102F" MLX_SERVE_EXPECTED_VERSION=26.10.2 QWEN38_CTX_SIZE="$CTX"
        export QWEN38_MLX_PREFIX_CACHE_MEM=16GB QWEN38_MLX_PREFIX_CACHE_DISK=100GB QWEN38_MLX_PREFIX_CACHE_ENTRIES=64
        unset QWEN38_MLX_DRAFTER QWEN38_MLX_KV_QUANT QWEN38_MLX_PLE_GPU
        export QWEN38_MLX_EXTRA_ARGS="--mtp-max-depth 3"
        if [[ "$CAND" == r27m ]]; then
          REV=v26.10.2-mtp-only
          NDF="$( [[ -f "$NO_DRAFTER_FLAG_FILE" ]] && cat "$NO_DRAFTER_FLAG_FILE" || echo NONE )"
          if [[ "$NDF" == NONE ]]; then MODEL_DIR="$DD27_NODRAFTER"; else export QWEN38_MLX_EXTRA_ARGS="$QWEN38_MLX_EXTRA_ARGS $NDF"; fi
        fi
        export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" ;;
    k27) LAUNCHER="$HARNESS/run-splash.sh"; ARM=K; PORT=8585; RUNTIME=splash; REV=v1.3.1
        MODEL_DIR="$MC27"; MODEL_REV=815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9
        PROBE_PY="$OPT/mlx-dspark-v0.20.3/bin/python"; TOKENIZER="$MC27"; SERVER_NAME=splash; METRICS=""
        export SPLASH_MODEL="$MC27" SPLASH_DRAFTER="$DFLASH2" QWEN38_CTX_SIZE="$CTX" QWEN38_SPLASH_EXPECTED_VERSION=1.3.1 QWEN38_SPLASH_PORT=8585 ;;
    l27|l27n) LAUNCHER="$ROOT/bench/qwen38-27b-next-steps-2026-10/scripts/run-llama-27b.sh"; PORT=8080; RUNTIME=llama.cpp; REV=b11569
        MODEL_DIR="$GGUF27"; MODEL_REV=71bc7b627595; PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=llama-server; METRICS=""
        MODEL_ID_PREF=qwen38-27b-gguf
        export QWEN38_GGUF_DIR="$GGUF27" QWEN38_LLAMA_SERVER_BIN="$LLAMA_B11569" QWEN38_CTX_SIZE="$CTX" FLASHNEXT_EFFORT="$EFFORT"
        if [[ "$CAND" == l27 ]]; then ARM=L27M; else ARM=L27N; REV=b11569-nospec; fi ;;
```
Conferir que `run-mlx-serve.sh` exige `model.safetensors.index.json` (linha 128): o pack ddalcu tem o índice. Conferir que o `--print` imprime `--tokenizer-path` quando `TOKENIZER` não é vazio (o `k27` depende disso); se o `--print` só imprime a linha do launcher e `probe:` sem os argumentos, acrescentar `--tokenizer-path` à linha `probe:` impressa.

- [ ] **Step 7: Rodar os testes dos braços e os das campanhas anteriores**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests bench/engine-updates-2026-10/tests bench/flashnext-next-steps-2026-10/tests/test_arms.py bench/qwen3.8-prefix-cache/tests -q 2>&1 | tail -3`
Expected: os 9 testes de `test_arms.py` passam; nenhuma regressão nos braços antigos (mesma contagem de `passed` que antes do Step 6; registrar as duas contagens em `results/etapa0-preflight.md` sob `## Test baseline`).

- [ ] **Step 8: Smoke de `--print` no rig (packs presentes)**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git pull --ff-only -q && for a in s27r k27 o27q8 o27q4 o27sw r27d r27m; do echo "== $a"; bash bench/qwen38-27b-next-steps-2026-10/scripts/run-arm.sh $a 32768 --print | grep -E "launcher|MISSING|effort" ; done; for a in l27 l27n; do echo "== $a"; bash bench/qwen38-27b-next-steps-2026-10/scripts/run-arm.sh $a 65536 --print | grep -E "launcher|MISSING"; done'
```
Expected: nenhuma linha com `MISSING`. Se `r27m` usar a cópia `-nodrafter`, criá-la agora: `cp -al "$DD27" "${DD27}-nodrafter" && rm -rf "${DD27}-nodrafter/drafter"` (hardlinks; custa só metadados).

- [ ] **Step 9: Commit**

```bash
git add bench/qwen3.8-prefix-cache bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh bench/qwen38-27b-next-steps-2026-10
git commit -m "bench(qwen38-27b): Task 3 - arms k27, o27q8/q4/sw, r27d/m, l27/l27n and launchers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 4: Orquestrador autônomo `run-campaign.sh`

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/scripts/phases.sh`
- Create: `bench/qwen38-27b-next-steps-2026-10/scripts/run-campaign.sh`
- Test: `bench/qwen38-27b-next-steps-2026-10/tests/test_campaign.py`

**Interfaces:**
- Consumes: `run-arm.sh`, `idle-gate.sh --minutes N`, `decide.py`, `empty_answers.py`, `think_turn_probe.py`, `run-battery.sh`, `tools/scripts/serve-flashnext-daily-driver.sh daily`.
- Produces: `run-campaign.sh [--dry-run] [--from P1] [--only P2] [--skip-battery]`; `results/gates.env` (`P1_PASS`, `P1_BEST`, …, `P5_GO`, `CAMPAIGN_DONE`); `results/campaign-log.md` (uma linha por braço: data, braço, banda, tag, exit); `logs/campaign.log`.

- [ ] **Step 1: Teste do dry-run**

```python
# bench/qwen38-27b-next-steps-2026-10/tests/test_campaign.py
import os, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"


def _dry(*args, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("QWEN38_", "FLASHNEXT_"))}
    e.update(env)
    out = subprocess.run(["bash", str(C / "scripts/run-campaign.sh"), "--dry-run", *args],
                         capture_output=True, text=True, env=e)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_dry_run_lists_phases_in_order_and_restarts_driver():
    out = _dry()
    order = [m.group(1) for m in re.finditer(r"^=== phase (P\d)", out, re.M)]
    assert order == ["P0", "P1", "P2", "P3", "P4", "P6", "PQ"]
    assert out.rstrip().splitlines()[-1].startswith("restart daily driver")
    assert "stop daily driver" in "\n".join(out.splitlines()[:3])


def test_every_arm_runs_both_efforts_and_both_bands():
    out = _dry()
    assert re.search(r"FLASHNEXT_EFFORT=xhigh bash \S*run-arm\.sh k27 32768 --repeat 3 --tag p1x", out)
    assert re.search(r"FLASHNEXT_EFFORT=medium bash \S*run-arm\.sh k27 131072 --repeat 3 --tag p1m", out)
    assert re.search(r"FLASHNEXT_EFFORT=xhigh bash \S*run-arm\.sh s27r 131072 --repeat 3 --tag p0x", out)


def test_band_order_alternates():
    out = _dry("--only", "P2")
    lines = [l for l in out.splitlines() if "run-arm.sh" in l and "p2x" in l]
    arms_32 = [l.split("run-arm.sh ")[1].split()[0] for l in lines if " 32768 " in l]
    arms_128 = [l.split("run-arm.sh ")[1].split()[0] for l in lines if " 131072 " in l]
    assert arms_32 == ["o27q8", "o27q4"] and arms_128 == ["o27q4", "o27q8"]


def test_idle_gate_precedes_each_band_and_decide_follows_phase():
    out = _dry("--only", "P1")
    assert out.count("idle-gate.sh --minutes 10") == 2
    assert "decide.py" in out and "--glob k27-*-p1x.jsonl" in out and "--glob s27r-*-p0x.jsonl" in out
    assert "--skip-gates hit_append,hit_tool_turn" in out  # Splash may not report cached_tokens
    assert "empty_answers.py" in out


def test_llama_phase_is_capped_at_64k():
    out = _dry("--only", "P6")
    assert "l27 65536" in out and "131072" not in out  # think probes of P6 also run at 64K


def test_from_skips_earlier_phases():
    out = _dry("--from", "P3")
    assert "=== phase P1" not in out and "=== phase P3" in out


def test_skip_battery_drops_pq():
    assert "=== phase PQ" not in _dry("--skip-battery")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_campaign.py -q`
Expected: 7 falhas (`run-campaign.sh` não existe).

- [ ] **Step 3: Escrever `phases.sh`**

```bash
#!/usr/bin/env bash
# Phase table of the Qwen3.8-27B next-steps campaign. Sourced by run-campaign.sh; no side effects.
# Each phase: PHASE_<id>_ARMS (space-separated arms, reference first), PHASE_<id>_CTXS, PHASE_<id>_BASE
# (reference arm for decide.py), PHASE_<id>_RULE (decide.py args), PHASE_<id>_SKIP (decide.py --skip-gates or "").
# Speed phases run every arm at xhigh (tag p<N>x) and medium (tag p<N>m), 3 reps, bands 32K then 128K.
PHASES=(P0 P1 P2 P3 P4 P6)

PHASE_P0_ARMS="s27r";              PHASE_P0_CTXS="32768 131072"; PHASE_P0_BASE="";     PHASE_P0_RULE="";                              PHASE_P0_SKIP=""
PHASE_P1_ARMS="k27";               PHASE_P1_CTXS="32768 131072"; PHASE_P1_BASE="s27r"; PHASE_P1_RULE="--mode le --threshold 0.75";    PHASE_P1_SKIP="hit_append,hit_tool_turn"
PHASE_P2_ARMS="o27q8 o27q4";       PHASE_P2_CTXS="32768 131072"; PHASE_P2_BASE="s27r"; PHASE_P2_RULE="--mode le --threshold 1.00";    PHASE_P2_SKIP=""
PHASE_P3_ARMS="r27d r27m";         PHASE_P3_CTXS="32768 131072"; PHASE_P3_BASE="s27r"; PHASE_P3_RULE="--mode le --threshold 1.00";    PHASE_P3_SKIP=""
PHASE_P4_ARMS="o27sw";             PHASE_P4_CTXS="32768 131072"; PHASE_P4_BASE="o27q4"; PHASE_P4_RULE="--mode le --threshold 1.03";   PHASE_P4_SKIP=""
PHASE_P6_ARMS="l27n l27";          PHASE_P6_CTXS="32768 65536";  PHASE_P6_BASE="s27r"; PHASE_P6_RULE="--mode le --threshold 1.00 --ctx 32768"; PHASE_P6_SKIP="hit_append,hit_tool_turn"

# Reference arm whose p0x files feed every decision; the base glob is derived from it.
REF_ARM=s27r; REF_TAG=p0x
# Driver ratio that reopens the driver verdict (spec): T_turno <= 1.25 x w1 (7.9 / 8.6 s).
W1_T32=7.9; W1_T128=8.6; DRIVER_RATIO=1.25
```

- [ ] **Step 4: Escrever `run-campaign.sh`**

```bash
#!/usr/bin/env bash
# Unattended runner of the Qwen3.8-27B next-steps campaign: speed phases P0..P6, then the quality
# battery PQ. Resumable: an arm whose results file already exists is skipped. Writes results/gates.env,
# results/campaign-log.md and etapa<N>-*.md. Start on the rig with:
#   nohup caffeinate -i bash $C/scripts/run-campaign.sh > $C/logs/campaign.log 2>&1 &
# usage: run-campaign.sh [--dry-run] [--from P<N>] [--only P<N>] [--skip-battery]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
FN="$REPO/bench/flashnext-next-steps-2026-10/scripts"; S="$HERE/scripts"; R="$HERE/results"; L="$HERE/logs"
# shellcheck source=phases.sh
source "$S/phases.sh"
DRY=""; FROM=""; ONLY=""; BATTERY=1
while [[ $# -gt 0 ]]; do case "$1" in
  --dry-run) DRY=1; shift ;; --from) FROM="$2"; shift 2 ;; --only) ONLY="$2"; shift 2 ;;
  --skip-battery) BATTERY=""; shift ;; *) echo "usage: $0 [--dry-run] [--from P<N>] [--only P<N>] [--skip-battery]" >&2; exit 64 ;;
esac; done
mkdir -p "$R" "$L"
say() { echo "$(date '+%F %T') $*"; }
run() { if [[ -n "$DRY" ]]; then echo "$*"; else say "run: $*"; eval "$@"; fi; }
gate_set() { [[ -n "$DRY" ]] && { echo "gates.env: $1=$2"; return; }; grep -v "^$1=" "$R/gates.env" 2>/dev/null > "$R/gates.env.tmp" || true; echo "$1=$2" >> "$R/gates.env.tmp"; mv "$R/gates.env.tmp" "$R/gates.env"; }
gate_get() { grep "^$1=" "$R/gates.env" 2>/dev/null | tail -1 | cut -d= -f2; }
have_result() { [[ -z "$DRY" && -s "$R/$1-$2-t1.0-$3.jsonl" ]]; }

idle_gate() {  # retry the thermal/memory gate three times; return 75 if the band must be skipped
  local i; for i in 1 2 3; do run "bash $FN/idle-gate.sh --minutes 10" && return 0; say "idle-gate failed ($i/3)"; [[ -n "$DRY" ]] && return 0; sleep 300; done; return 75
}
stop_driver() { [[ -n "$DRY" ]] && echo "stop daily driver"; run "P=\$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true); [ -n \"\$P\" ] && kill \$P; sleep 5; true"; }
restart_driver() { [[ -n "$DRY" ]] && printf 'restart daily driver: '; run "nohup bash $REPO/tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &"; }
trap 'say "exit: restarting driver"; restart_driver' EXIT

run_arm() {  # arm ctx tag effort
  if have_result "$1" "$2" "$3"; then say "skip $1@$2 $3 (exists)"; return 0; fi
  run "FLASHNEXT_EFFORT=$4 bash $S/run-arm.sh $1 $2 --repeat 3 --tag $3"; local rc=$?
  [[ -n "$DRY" ]] || echo "| $(date -u +%FT%TZ) | $1 | $2 | $3 | $4 | $rc |" >> "$R/campaign-log.md"
  run "sleep 120"; return $rc
}

run_phase() {  # P<N>
  local p="$1" n="${1#P}" arms ctxs base rule skip ordered ctx arm eff tag
  arms="$(eval echo "\$PHASE_${p}_ARMS")"; ctxs="$(eval echo "\$PHASE_${p}_CTXS")"; base="$(eval echo "\$PHASE_${p}_BASE")"
  rule="$(eval echo "\$PHASE_${p}_RULE")"; skip="$(eval echo "\$PHASE_${p}_SKIP")"
  echo "=== phase $p: arms [$arms] ctx [$ctxs]"
  if [[ "$p" == P4 && -z "$DRY" && "$(gate_get P2_PASS)" != 1 ]]; then say "P4 skipped: P2 did not pass"; gate_set P4_PASS skipped; return; fi
  local first=1
  for ctx in $ctxs; do
    # alternate order: first band reference -> candidate, later bands candidate -> reference
    if [[ $first == 1 ]]; then ordered="$arms"; else ordered="$(echo $arms | tr ' ' '\n' | tail -r | tr '\n' ' ')"; fi; first=0
    idle_gate || { say "band $ctx of $p skipped (idle-gate)"; continue; }
    for eff in xhigh medium; do
      [[ $eff == xhigh ]] && tag="p${n}x" || tag="p${n}m"
      for arm in $ordered; do run_arm "$arm" "$ctx" "$tag" "$eff"; done
    done
  done
  [[ -z "$base" ]] && return
  local skipflag=""; [[ -n "$skip" ]] && skipflag="--skip-gates $skip"
  local md="$R/etapa${n}-$(echo $arms | cut -d' ' -f1).md"; local pass=1 best=""
  for arm in $arms; do
    run "python3 $FN/decide.py --results-dir $R --logs-dir $L --glob ${base}-*-p?x.jsonl --glob ${arm}-*-p${n}x.jsonl --base $base --cand $arm $rule $skipflag --title 'Etapa $n: $arm vs $base (xhigh)' --out-md $md" || pass=0
    run "python3 $FN/decide.py --results-dir $R --logs-dir $L --glob ${arm}-*-p${n}m.jsonl --glob ${arm}-*-p${n}x.jsonl --title 'Etapa $n: $arm medium vs xhigh' --out-md $md"
    [[ $pass == 1 && -z "$best" ]] && best="$arm"
  done
  { echo; echo "## Respostas vazias (think_turn_probe)"; } >> "$md" 2>/dev/null || true
  for arm in $arms; do run "python3 $S/empty_answers.py $R/think/$arm-*.jsonl >> $md 2>/dev/null || true"; done
  gate_set "${p}_PASS" "$pass"; [[ -n "$best" ]] && gate_set "${p}_BEST" "$best"
}

run_think() {  # think_turn_probe on every candidate of a phase (arms, ctx), both efforts
  local arm eff ctx="$2"; mkdir -p "$R/think"
  for arm in $1; do for eff in xhigh medium; do
    [[ -z "$DRY" && -s "$R/think/$arm-$eff.jsonl" ]] && continue
    run "bash $S/run-arm.sh $arm $ctx --tag think$eff --exec \"python3 $FN/think_turn_probe.py --base-url \\\$BASE_URL --model \\\$MODEL_ID --arm $arm --context $ctx --reasoning-effort $eff --repeat 3 --output $R/think/$arm-$eff.jsonl\""
    run "sleep 120"
  done; done
}

run_battery() {  # PQ: Swift-style quality and time/tokens per task on the finalists
  echo "=== phase PQ: quality battery"
  local arms="o27q4 o27sw" best; best="$(gate_get P1_BEST)$(gate_get P3_BEST)"
  [[ -n "$best" && " $arms " != *" $best "* ]] && arms="$arms $best"
  [[ -n "$DRY" ]] && arms="o27q4 o27sw k27"
  local arm
  for arm in $arms; do
    idle_gate || { say "battery $arm skipped (idle-gate)"; continue; }
    run "BATTERY_CAMPAIGN_DIR=$HERE bash $FN/run-battery.sh $arm q --effort medium --ctx 131072 --label $arm-medium --loops"
    run "sleep 120"
    run "BATTERY_CAMPAIGN_DIR=$HERE bash $FN/run-battery.sh $arm q --suites 'gpqa livecodebench' --effort xhigh --ctx 131072 --label $arm-xhigh"
    run "sleep 120"
  done
  run "python3 $REPO/bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $R/q/t1 --base o27q4-medium --cand o27sw-medium --out $R/etapaq-swift-vs-base.md"
  run "python3 $REPO/bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $R/q/t1 --base o27q4-xhigh --cand o27q4-medium --out $R/etapaq-effort-o27q4.md"
  run "python3 $S/empty_answers.py $R/q/t1/*/*.jsonl --json > $R/etapaq-empty.json"
}

echo "=== campaign start $(date -u +%FT%TZ) dry=${DRY:-0} from=${FROM:-} only=${ONLY:-}"
stop_driver
sel=("${PHASES[@]}"); [[ -n "$ONLY" ]] && sel=("$ONLY")
started=""; [[ -z "$FROM" ]] && started=1
for p in "${sel[@]}"; do
  [[ "$p" == "$FROM" ]] && started=1; [[ -n "$started" ]] || continue
  run_phase "$p"
  [[ "$p" == P0 ]] || run_think "$(eval echo "\$PHASE_${p}_ARMS")" "$( [[ "$p" == P6 ]] && echo 65536 || echo 131072 )"
done
if [[ -n "$BATTERY" && -z "$ONLY" || "$ONLY" == PQ ]]; then run_battery; fi
# Driver gate for P5 (manual, needs the MacBook + Docker): any arm with T_turno <= 1.25 x w1 on both bands.
run "python3 $S/driver_gate.py --results-dir $R --w1 $W1_T32 $W1_T128 --ratio $DRIVER_RATIO --out $R/gates.env"
gate_set CAMPAIGN_DONE "$(date -u +%FT%TZ)"
```
Notas de implementação: `tail -r` existe no macOS (bash 3.2 do rig); `eval echo "\$PHASE_${p}_ARMS"` substitui arrays associativos, que o bash 3.2 não tem. O `--only PQ` roda só a bateria. Em dry-run, o `trap EXIT` imprime `restart daily driver: nohup …` como última linha, e o `echo "restart daily driver (trap)"` final deve ser removido para não duplicar. Os `think_turn_probe` da fase P6 rodam a 64K pelo bug llama.cpp #27756; os das outras fases a 128K.

- [ ] **Step 5: Escrever `driver_gate.py`**

```python
#!/usr/bin/env python3
"""Write P5_GO=<arm> (or 0) into gates.env: the fastest 27B arm whose T_turno is within --ratio of the
Flash-Next driver on both bands, computed from this campaign's medium-effort files (*-p?m.jsonl).
usage: driver_gate.py --results-dir DIR --w1 T32 T128 --ratio 1.25 --out gates.env
"""
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "bench/qwen38-flashnext-daily-driver-2026-09/scripts"))
from summarize_driver import load_records, summarize  # noqa: E402


def pick(summary: dict, w1: tuple[float, float], ratio: float) -> tuple[str, float] | None:
    best = None
    for (arm, ctx), row in summary.items():
        if ctx != 32768 or not row.get("t_turno_s"):
            continue
        hi = summary.get((arm, 131072))
        if not hi or not hi.get("t_turno_s") or row["gates_failed"] or hi["gates_failed"]:
            continue
        if row["t_turno_s"] <= ratio * w1[0] and hi["t_turno_s"] <= ratio * w1[1]:
            if best is None or hi["t_turno_s"] < best[1]:
                best = (arm, hi["t_turno_s"])
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--w1", type=float, nargs=2, required=True)
    ap.add_argument("--ratio", type=float, default=1.25)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    files = sorted(a.results_dir.glob("*-p?m.jsonl"))
    summary = summarize(load_records(files)) if files else {}
    best = pick(summary, tuple(a.w1), a.ratio)
    lines = [l for l in (a.out.read_text().splitlines() if a.out.exists() else []) if not l.startswith("P5_GO=")]
    lines.append(f"P5_GO={best[0] if best else 0}")
    a.out.write_text("\n".join(lines) + "\n")
    print(lines[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
Se `summarize_driver.py` expuser outros nomes (`load_records`/`summarize` são os nomes a confirmar na leitura do módulo, por volta das linhas 59-127), usar os nomes reais. Acrescentar ao `test_campaign.py`:

```python
def test_driver_gate_picks_only_arms_within_ratio(tmp_path):
    import json, sys
    sys.path.insert(0, str(C / "scripts")); import driver_gate
    def rows(arm, t32, t128):
        out = []
        for ctx, ttft, dec in ((32768, (t32 - 512 / 60) * 1000, 60.0), (131072, (t128 - 512 / 50) * 1000, 50.0)):
            for s in ("cold", "identical", "append", "tool_turn"):
                out.append({"arm": arm, "context_target": ctx, "scenario": s, "finish_reason": "stop", "error": None,
                            "correct": True, "decode_tps": dec, "ttft_ms": ttft, "cache_hit_ratio": 0.99,
                            "swap_delta_gb": 0.0, "session_id": f"{arm}-{ctx}", "runtime": "x"})
        return out
    for arm, t32, t128 in (("k27", 9.0, 10.0), ("o27q4", 15.0, 20.0)):
        (tmp_path / f"{arm}-32768-t1.0-p1m.jsonl").write_text("\n".join(json.dumps(r) for r in rows(arm, t32, t128) if r["context_target"] == 32768) + "\n")
        (tmp_path / f"{arm}-131072-t1.0-p1m.jsonl").write_text("\n".join(json.dumps(r) for r in rows(arm, t32, t128) if r["context_target"] == 131072) + "\n")
    out = tmp_path / "gates.env"; out.write_text("P1_PASS=1\n")
    assert driver_gate.main(["--results-dir", str(tmp_path), "--w1", "7.9", "8.6", "--ratio", "1.25", "--out", str(out)]) == 0
    assert "P5_GO=k27" in out.read_text() and "P1_PASS=1" in out.read_text()
```

- [ ] **Step 6: Rodar e ver passar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_campaign.py -q`
Expected: `8 passed`. Rodar também `bash bench/qwen38-27b-next-steps-2026-10/scripts/run-campaign.sh --dry-run | head -40` e ler a sequência com olhos humanos: `stop daily driver`, `=== phase P0`, `idle-gate`, quatro `run-arm.sh s27r …` (2 bandas × 2 esforços), etc.

- [ ] **Step 7: Commit**

```bash
git add bench/qwen38-27b-next-steps-2026-10
git commit -m "bench(qwen38-27b): Task 4 - unattended campaign runner, phase table, driver gate

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 5: Smokes de 8K por runtime novo (Splash, oMLX refit, mlx-serve 26.10.2, llama) e correções

Antes de soltar o orquestrador, cada runtime novo sobe uma vez a 8K com 1 rep para pegar erro de flag, thinking desligado, ausência de `cached_tokens` e respostas vazias. Isso evita descobrir o problema no meio de uma noite de 128K.

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/results/etapa1-smokes.md`
- Modify (condicional): `bench/qwen3.8-prefix-cache/config/splash-flags.env`, `run-splash.sh`, `omlx-arms.json`, `run-llama-27b.sh`

- [ ] **Step 1: Parar o driver diário e conferir o gate**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git pull --ff-only -q && P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 5; pgrep -fl "run-candidate|cache_probe|mlx-serve|omlx|mtplx|mlx-dspark|splash|llama-server" || echo none; bash bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh --minutes 0'
```
Expected: `none` e `idle-gate: ready`.

- [ ] **Step 2: Smokes de 8K, 1 rep, `medium`**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && C=$PWD/bench/qwen38-27b-next-steps-2026-10 && for a in k27 o27q4 r27d r27m; do FLASHNEXT_EFFORT=medium caffeinate -i bash $C/scripts/run-arm.sh $a 8192 --repeat 1 --tag smoke 2>&1 | tail -3; sleep 60; done; FLASHNEXT_EFFORT=medium caffeinate -i bash $C/scripts/run-arm.sh l27 8192 --repeat 1 --tag smoke 2>&1 | tail -3' 2>&1 | tee /tmp/smokes.log
```
Expected: cinco linhas `>>> <arm>-8192-t1.0-smoke: OK`. Um exit 65 é versão errada; 66 é peso ausente; 69 é servidor que não subiu (ler `logs/<name>-boot.log`). Corrigir a causa (flag em `splash-flags.env`, chave em `omlx-arms.json`, nome de flag no launcher llama) e repetir só o braço que falhou.

- [ ] **Step 3: Ler os registros do smoke**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms/bench/qwen38-27b-next-steps-2026-10/results && for f in *-8192-t1.0-smoke.jsonl; do python3 - "$f" <<'"'"'EOF'"'"'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
print(sys.argv[1])
for r in rows:
    print(f"  {r['scenario']:16} ttft={r['ttft_ms']/1000:6.1f}s dec={r.get('decode_tps') or 0:5.1f} hit={r.get('cache_hit_ratio')} cached={r.get('cached_tokens')} reason_chars={r.get('reasoning_chars')} comp={r.get('completion_tokens')} fin={r.get('finish_reason')} ok={r.get('correct')} err={r.get('error')} mtp={r.get('mtp_acceptance')}")
EOF
done'
```
Expected por braço: `reasoning_chars > 0` em todo cenário (thinking ligado); `err=None`; `ok=True` ou `fin=length`. Para `k27` e `l27`, anotar se `cached` é `None`/`0` (sem `cached_tokens`) ou um número; gravar `SPLASH_HAS_CACHED_TOKENS=yes|no` em `splash-flags.env`. Se `k27` ou `l27` tiverem `cached_tokens` reais, remover o `--skip-gates` da fase correspondente em `phases.sh` (e ajustar `test_campaign.py`). Para `r27m`, conferir no boot log `grep -E "\[spec-stats\]|drafter|mtp" logs/r27m-8192-t1.0-smoke-boot.log | tail -5`: deve mostrar MTP ativa e nenhum `dflash` carregado; `r27d` deve mostrar o drafter.

- [ ] **Step 4: Thinking desligado em algum runtime**

Se `reasoning_chars == 0` em `o27q4`: o oMLX precisa de `enable_thinking: true` no pedido. Nesse caso (e só nesse caso), acrescentar ao `cache_probe.py` o argumento `--chat-template-kwargs JSON` que entra em `body["chat_template_kwargs"]`, e ao `run-candidate.sh` a variável `FLASHNEXT_CHAT_KWARGS` repassada como `--chat-template-kwargs`. Nos blocos `o27q8|o27q4|o27sw`, exportar `FLASHNEXT_CHAT_KWARGS="{\"enable_thinking\":true,\"reasoning_effort\":\"$EFFORT\"}"`. Escrever um teste em `test_arms.py` que confere a string no `--print` dos três braços oMLX, e um em `bench/qwen3.8-prefix-cache/tests/test_cache_probe.py` que confere o campo no corpo do pedido (seguir o padrão dos testes que já constroem o corpo nesse arquivo). Repetir o smoke do `o27q4`. Se `reasoning_chars == 0` em `k27`, procurar em `splash-help.txt` uma flag de thinking/effort do servidor e colocá-la em `SPLASH_EXTRA_ARGS`; se não existir, registrar e seguir (o Splash mediria o modo não-thinking; a decisão de P1 então vale só para velocidade e fica marcada como tal em `etapa1-smokes.md`).

- [ ] **Step 5: Registrar e commitar**

Escrever `results/etapa1-smokes.md` com a tabela dos cinco braços (ttft frio, decode, hit identical, reasoning_chars, cached_tokens presente, aceitação) e as correções feitas.

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git add bench && git commit -m "bench(qwen38-27b): Task 5 - 8K smokes of Splash, oMLX refit, mlx-serve 26.10.2 and llama arms

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push'
```
No MacBook: `git pull --ff-only` e rodar a suíte completa desta campanha: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests -q`. Expected: tudo passa.

---

### Task 5b: Braços w27d e w27m, fases P7 e P8 e nova ordem

Origem: "Revisão de 13/10". A campanha já está rodando; este task muda só código e testes no MacBook. O reinício no rig é o Step 7.

**Files:**
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` (blocos `w27d`, `w27m`; lista de braços na linha de uso)
- Modify: `bench/qwen38-27b-next-steps-2026-10/scripts/phases.sh` (ordem, P3 só r27d, P7, P8)
- Modify: `bench/qwen38-27b-next-steps-2026-10/scripts/run-campaign.sh` (smoke de 8K antes de P7 e P8)
- Modify: `bench/qwen38-27b-next-steps-2026-10/scripts/render_27b_page.py` (tabela de braços, `GATE_DOC` de P7 e P8)
- Test: `bench/qwen38-27b-next-steps-2026-10/tests/test_arms.py`, `test_campaign.py`, `test_render_27b_page.py`

**Interfaces:**
- Consumes: `run-mlx-serve.sh C` com `QWEN38_MLX_MODEL_DIR`, `QWEN38_MLX_DRAFTER` (vira `--drafter`) e `QWEN38_MLX_EXTRA_ARGS`; variáveis `SW27` (pack Swift) e `DD27` (pack ddalcu) do `run-candidate.sh`; `run_arm`, `idle_gate`, `say` e `run` do `run-campaign.sh`.
- Produces: braços `w27d`, `w27m`; `PHASES=(P0 P1 P3 P7 P2 P4 P8 P6)`; arquivos `w27d-<ctx>-t1.0-p7{x,m}.jsonl`, `r27m|w27m-<ctx>-t1.0-p8{x,m}.jsonl`; smoke `w27d-8192-t1.0-p7s.jsonl`, `w27m-8192-t1.0-p8s.jsonl`; `P7_PASS`, `P8_PASS`, `P7_SMOKE=0|1`, `P8_SMOKE_w27m=0|1` em `gates.env`.

- [ ] **Step 1: Testes que falham**

Em `test_arms.py`: `run-candidate.sh w27d 32768 --print` mostra `QWEN38_MLX_MODEL_DIR` com `Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc191`, `--no-mtp`, um `QWEN38_MLX_DRAFTER` que termina em `/drafter` dentro do pack ddalcu `7775059e955f`, porta 11234, `MODEL_REV=881dc1914f65` e `REV=v26.10.2-swift-drafter`. O `w27m` mostra o mesmo pack, `--no-drafter --mtp-max-depth 3`, nenhum `QWEN38_MLX_DRAFTER` e `REV=v26.10.2-swift-mtp`.
Em `test_campaign.py` (dry-run): a ordem das fases é `P0 P1 P3 P7 P2 P4 P8 P6`; P3 tem só `r27d`; P8 tem `r27m w27m`; o dry-run mostra a linha `smoke w27d 8192 p7s` antes da primeira banda de P7 e `smoke w27m 8192 p8s` antes de P8; a decisão de P7 usa `--base r27d --threshold 1.03` com o glob base `r27d-*-p3x.jsonl`.
Em `test_render_27b_page.py`: `w27d` e `w27m` aparecem na tabela de braços com fase P7 e P8; `r27m` aparece com P8.

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests -q`
Expected: os testes novos falham; os outros 56 passam.

- [ ] **Step 2: Braços no `run-candidate.sh`**

Junto do bloco `r27d|r27m`, mesmo estilo:

```bash
  w27d|w27m) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=C; PORT=11234; RUNTIME=mlx-serve
      MODEL_DIR="$SW27"; MODEL_REV=881dc1914f65; PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
      export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102F" MLX_SERVE_EXPECTED_VERSION=26.10.2 QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_PREFIX_CACHE_MEM=16GB QWEN38_MLX_PREFIX_CACHE_DISK=100GB QWEN38_MLX_PREFIX_CACHE_ENTRIES=64
      unset QWEN38_MLX_DRAFTER QWEN38_MLX_KV_QUANT QWEN38_MLX_PLE_GPU QWEN38_MLX_DRAFT_BLOCK_SIZE QWEN38_MLX_CONFIG_OVERRIDES
      # Swift 1.5 27B (oQ4e, MTP head inherited from the base). w27m: MTP alone; w27d: the ddalcu DFlash2 drafter alone.
      if [[ "$CAND" == w27m ]]; then
        REV=v26.10.2-swift-mtp; export QWEN38_MLX_EXTRA_ARGS="--no-drafter --mtp-max-depth 3"
      else
        REV=v26.10.2-swift-drafter; export QWEN38_MLX_EXTRA_ARGS="--no-mtp" QWEN38_MLX_DRAFTER="$DD27/drafter"
      fi
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" ;;
```

Conferir com `ls` no rig (só leitura) que `$DD27/drafter/config.json` existe. Se não existir, usar o diretório `incoai--Qwen3.8-27B-DFlash2-dedf8df6…` e registrar a troca no relatório.

- [ ] **Step 3: `phases.sh`**

```bash
PHASES=(P0 P1 P3 P7 P2 P4 P8 P6)
PHASE_P3_ARMS="r27d";              PHASE_P3_CTXS="32768 131072"; PHASE_P3_BASE="s27r"; PHASE_P3_RULE="--mode le --threshold 1.00";    PHASE_P3_SKIP=""
PHASE_P7_ARMS="w27d";              PHASE_P7_CTXS="32768 131072"; PHASE_P7_BASE="r27d"; PHASE_P7_RULE="--mode le --threshold 1.03";   PHASE_P7_SKIP=""
PHASE_P8_ARMS="r27m w27m";         PHASE_P8_CTXS="32768 131072"; PHASE_P8_BASE="s27r"; PHASE_P8_RULE="--mode le --threshold 1.00";    PHASE_P8_SKIP=""
# 8K smoke before the bands; the phase (or the arm, for P8) is skipped when it fails.
PHASE_P7_SMOKE="w27d:dflash"; PHASE_P8_SMOKE="w27m:mtp"; SMOKE_MIN_DECODE=60
```

As outras fases não mudam. A base de uma fase cuja base não é o `REF_ARM` usa o glob `<base>-*-p<N da fase da base>x.jsonl` (P4 já faz isso com o27q4 → `p2x`; P7 usa r27d → `p3x`).

- [ ] **Step 4: Smoke no `run-campaign.sh`**

Antes do `idle_gate` da primeira banda de uma fase com `PHASE_<P>_SMOKE`, para cada `arm:mode`: `FLASHNEXT_EFFORT=medium run-arm.sh <arm> 8192 --repeat 1 --tag p<n>s`, e então um checador Python (função nova em `driver_gate.py` ou script `smoke_check.py`) que lê o JSONL e o boot log e falha se: rc ≠ 0, algum `reasoning_chars == 0`, `[spec-stats]` ausente, `mode=` diferente do esperado, ou decode mediano < `SMOKE_MIN_DECODE`. Gravar `P7_SMOKE=0|1` / `P8_SMOKE_w27m=0|1`. Na P7, smoke reprovado pula a fase inteira (`say "phase P7 skipped (smoke)"`). Na P8, smoke reprovado tira só o `w27m` da fase; o `r27m` roda. Retomada: smoke com arquivo de resultado presente não roda de novo.

- [ ] **Step 5: Página**

Tabela `ARMS` do `render_27b_page.py`: adicionar `w27d` (P7) e `w27m` (P8) com pack `scottlowry Swift-1.5 oQ4e-mtp`, rev `881dc191`, porta 11234; mudar `r27m` para P8. `GATE_DOC`: `P7_PASS` = "w27d at or under 1.03 × r27d on both bands", `P8_PASS` = "r27m or w27m at or under s27r on both bands", `P7_SMOKE` e `P8_SMOKE_w27m` = "8K smoke passed (reasoning, spec-stats mode, decode ≥ 60 tok/s)".

- [ ] **Step 6: Testes e commit**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests -q`
Expected: tudo passa (56 + os novos). Rodar também `bash run-campaign.sh --dry-run` e conferir a ordem.

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh bench/qwen38-27b-next-steps-2026-10/scripts bench/qwen38-27b-next-steps-2026-10/tests
git commit -m "bench(qwen38-27b): w27d/w27m Swift 1.5 arms on mlx-serve, phases P7/P8, new phase order

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Reiniciar a campanha no rig (precisa de aprovação do usuário para parar o processo)**

Numa fronteira entre braços (linha nova em `results/campaign-log.md`): parar `run-campaign.sh` e `idle-gate.sh`; atualizar o checkout do rig com `git push vitor@mac-studio:LocalProjects/local-llms-27b HEAD:refs/heads/macbook-sync` e `git merge --ff-only macbook-sync`; reiniciar com `nohup caffeinate -i bash $C/scripts/run-campaign.sh --skip-battery`, sem `--from`. A retomada pula os braços completos. Um braço interrompido no meio roda de novo do zero.

---

### Task 6: Soltar a campanha (P0 → P1 → P3 → P7 → P2 → P4 → P8 → P6) e acompanhar

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/results/campaign-log.md`, `results/gates.env`, `results/etapa{1,2,3,4,6}-*.md`, `results/think/*.jsonl`, JSONL de todos os braços

- [ ] **Step 1: Iniciar sem supervisão**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && C=$PWD/bench/qwen38-27b-next-steps-2026-10 && echo "| quando (UTC) | braço | ctx | tag | esforço | exit |" > $C/results/campaign-log.md && echo "|---|---|---|---|---|---|" >> $C/results/campaign-log.md && nohup caffeinate -i bash $C/scripts/run-campaign.sh --skip-battery > $C/logs/campaign.log 2>&1 & sleep 20; tail -5 ~/LocalProjects/local-llms/bench/qwen38-27b-next-steps-2026-10/logs/campaign.log'
```
Expected: `=== campaign start`, `stop daily driver`, `=== phase P0`, `idle-gate: …`. A bateria fica para o Task 7, porque depende de ler as decisões de P1–P4 antes.

- [ ] **Step 2: Acompanhar a cada ~2 h sem interferir**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms/bench/qwen38-27b-next-steps-2026-10 && tail -3 logs/campaign.log; echo; tail -6 results/campaign-log.md; echo; cat results/gates.env 2>/dev/null; echo; ls results/*.jsonl | wc -l'
```
Expected: o número de JSONL cresce (4 por braço por fase: 2 bandas × 2 esforços); exits 0. Um exit 69 repetido no mesmo braço (servidor não sobe) é motivo para matar a campanha (`pkill -f run-campaign.sh`), corrigir e retomar com `--from P<N>` (os braços já medidos são pulados). Duração prevista (ordem da Revisão de 13/10): P0 ~3 h, P1 ~3 h, P3 ~2.75 h, P7 ~3 h, P2 ~5.5 h, P4 ~3 h, P8 ~5.5 h, P6 ~2 h, think probes ~4.9 h: ~32 h.

- [ ] **Step 3: Verificar o fim das fases de velocidade**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms/bench/qwen38-27b-next-steps-2026-10 && grep -c "" results/campaign-log.md; cat results/gates.env; for f in results/etapa*-*.md; do echo "== $f"; grep -E "^\| (s27r|k27|o27|r27|l27)|VERDICT|empty=" $f; done; lsof -nP -tiTCP:11234 -sTCP:LISTEN && echo "driver back"'
```
Expected: `CAMPAIGN_DONE=<ts>`, `P1_PASS`, `P2_PASS`, `P3_PASS`, `P4_PASS`, `P6_PASS`, `P7_PASS`, `P8_PASS`, `P7_SMOKE` e `P8_SMOKE_w27m` definidos, `P5_GO=<arm|0>`, tabelas com `T_turno` para cada braço a 32K e 128K (64K para `l27`), e `driver back`. Se alguma banda foi pulada por `idle-gate` (linha `band … skipped`), rodar só ela: `--only P<N>` (braços com resultado são pulados).

- [ ] **Step 4: Commitar os resultados brutos de velocidade (feito no rig)**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && du -sh bench/qwen38-27b-next-steps-2026-10/results && find bench/qwen38-27b-next-steps-2026-10/results -size +1M && git add bench/qwen38-27b-next-steps-2026-10/results && git commit -m "bench(qwen38-27b): Task 6 - speed phases P0-P6, think probes, decisions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push'
```
Expected: `find -size +1M` não lista nada (se listar, mover o arquivo para `logs/` e deixar em `results/` uma cópia com `content` cortado a 500 caracteres, como a campanha flashnext-next-steps faz).

---

### Task 7: Bateria de qualidade e tempo/tokens por tarefa (PQ)

A bateria roda em `o27q4` (base refit), `o27sw` (Swift 1.5) e no melhor braço de P1/P3 se for outro (`P1_BEST`/`P3_BEST`). Perfil t1, esforço `medium`, contexto 131072, suítes HumanEval, GPQA, LiveCodeBench, jdhodges, Veerman e IF, mais a sweep de loops; GPQA e LiveCodeBench também em `xhigh`. Isso reproduz as métricas da página Swift (tempo até a resposta final, tokens por resposta, tokens/s, acerto, truncamentos) para o 27B.

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/results/q/t1/<label>/<suite>.jsonl`, `results/loops/q-<label>.jsonl`, `results/etapaq-*.md`, `results/etapaq-empty.json`, `results/humaneval-regrade.json`

- [ ] **Step 1: Conferir o submódulo de bench e soltar a bateria**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && git -C tools/local-llm-bench-m4-32gb log -1 --oneline && git -C tools/local-llm-bench-m4-32gb merge-base --is-ancestor a4a95bb HEAD && echo "runner ok" && C=$PWD/bench/qwen38-27b-next-steps-2026-10 && nohup caffeinate -i bash $C/scripts/run-campaign.sh --only PQ > $C/logs/campaign-pq.log 2>&1 & sleep 30; tail -3 ~/LocalProjects/local-llms/bench/qwen38-27b-next-steps-2026-10/logs/campaign-pq.log'
```
Expected: `runner ok` (o `tool_call_bench.py` grava `reasoning_chars` a partir de `a4a95bb`); `=== phase PQ`. Duração prevista: ~10–12 h por braço em `medium` mais ~5 h de GPQA+LCB em `xhigh`: 30–45 h no total. O `run-battery.sh` sobe o servidor uma vez por chamada e grava `results/q/t1/<label>/<suite>.jsonl`.

- [ ] **Step 2: Acompanhar**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms/bench/qwen38-27b-next-steps-2026-10 && tail -2 logs/campaign-pq.log; for d in results/q/t1/*/; do echo "$d: $(ls $d | tr "\n" " ")"; done; ls results/loops 2>/dev/null'
```
Expected: cada label acumula `humaneval.jsonl gpqa.jsonl livecodebench.jsonl jdhodges.jsonl veerman.jsonl if.jsonl`; `loops/q-<label>.jsonl` com 32 linhas.

- [ ] **Step 3: Regrade do HumanEval e tabelas**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && C=bench/qwen38-27b-next-steps-2026-10 && python3 bench/engine-updates-2026-10/scripts/regrade_humaneval.py --out $C/results/humaneval-regrade.json $(for d in $C/results/q/t1/*/; do l=$(basename $d); echo "$l-t1 $d/humaneval.jsonl"; done) && cat $C/results/etapaq-swift-vs-base.md && cat $C/results/etapaq-effort-o27q4.md && cat $C/results/etapaq-empty.json && python3 bench/flashnext-next-steps-2026-10/scripts/agent_probes.py loops $C/results/loops/*.jsonl'
```
Expected: tabela G1/G2 Swift × base (`passed`, `median_s`, `median_completion`, `median_reasoning_chars` por suíte); tabela `medium` × `xhigh` do o27q4; contagem de respostas vazias; taxa de loops por label. Registrar em `results/etapaq-leitura.md`: a decisão de P4 pela regra do spec (tempo até a resposta final ≤ 0.8× o27q4; tool-calling ≥ o27q4 − 1; zero loops) e a decisão de P2 sobre qualidade (HumanEval e tool-calling do o27q4 a ≤ 2 pontos do o27q8 — **o o27q8 não entra na bateria por custo; a comparação usa o o27q4 contra os números publicados da Jundot no card, e isso fica dito**). Se o usuário quiser o o27q8 na bateria, rodar `BATTERY_CAMPAIGN_DIR=$C bash bench/flashnext-next-steps-2026-10/scripts/run-battery.sh o27q8 q --effort medium --label o27q8-medium` (~12 h).

- [ ] **Step 4: Commitar**

```bash
ssh vitor@mac-studio 'cd ~/LocalProjects/local-llms && find bench/qwen38-27b-next-steps-2026-10/results -size +1M; git add bench/qwen38-27b-next-steps-2026-10/results && git commit -m "bench(qwen38-27b): Task 7 - quality battery, time and tokens per task, loops

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push'
```
Expected: nenhum arquivo > 1 MB (os JSONL de bateria com `raw_response` podem passar; nesse caso aplicar o corte a 500 caracteres descrito no Task 6 Step 4 e manter o original em `logs/`).

---

### Task 8: Página `reports/qwen38-27b-stacks.html`, card no índice e card do modelo

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/scripts/render_27b_page.py`
- Create: `bench/qwen38-27b-next-steps-2026-10/tests/test_render_27b_page.py`
- Create: `bench/qwen38-27b-next-steps-2026-10/results/page-data.json` (gerado)
- Create: `reports/qwen38-27b-stacks.html` (gerado)
- Modify: `reports/index.html` (card na seção `#dense`)
- Create: `docs/models/qwen3.8-27b.md`
- Modify: `docs/models/README.md` (linha do 27B), `bench/engine-updates-2026-10/results/27b-summary.md` (nota de pin superado), `research/qwen38-27b-next-steps-20261013.md` (link para os resultados)

**Interfaces:**
- Consumes: `summarize_driver.summarize/load_records` (formato `<arm>@<ctx>`), `summarize_ab.load_arm/suite_stats` (`bench/swift15-flashnext-2026-10/scripts/summarize_ab.py`), `bench/swift15-flashnext-2026-10/results/tturno-summary.json` e `results/ab/t1/w1/*.jsonl` (referência Flash-Next w1, xhigh), `results/gates.env`.
- Produces: `render_27b_page.py [--results DIR] [--out reports/qwen38-27b-stacks.html] [--json-out results/page-data.json]`; `page-data.json` com `{"generated_at", "arms": [{id, name, runtime, pack, rev, port, phase}], "speed": {"<ctx>": {"<arm>-<effort>": {t_turno_s, warm_ttft_tool_s, cold_ttft_s, decode_tps, hit_tool, mtp_acceptance, wired_peak_gb, gates_failed}}}, "w1": {"32768": {...}, "131072": {...}}, "quality": {"<label>": {"<suite>": {n, passed, truncated, median_s, median_completion, median_reasoning_chars, total_s}}}, "empty": {...}, "loops": {"<label>": {degenerate, total}}, "gates": {raw text of gates.env}}`.

- [ ] **Step 1: Teste do renderizador com dados sintéticos e com os dados reais**

```python
# bench/qwen38-27b-next-steps-2026-10/tests/test_render_27b_page.py
import json, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
sys.path.insert(0, str(C / "scripts"))
import render_27b_page as rp  # noqa: E402


def _speed_rows(arm, ctx, tag, t_ttft_ms, dec):
    base = {"arm": arm, "context_target": ctx, "finish_reason": "stop", "error": None, "correct": True,
            "decode_tps": dec, "ttft_ms": t_ttft_ms, "cache_hit_ratio": 0.99, "swap_delta_gb": 0.0,
            "session_id": f"{arm}-{ctx}-{tag}", "runtime": "x", "ram_peak_gb": 40.0}
    return [dict(base, scenario=s) for s in ("cold", "identical", "append", "tool_turn")]


@pytest.fixture
def results(tmp_path):
    for arm, tag, ttft, dec in (("s27r", "p0x", 9700, 32.0), ("k27", "p1x", 2500, 60.0), ("k27", "p1m", 2400, 61.0)):
        for ctx in (32768, 131072):
            (tmp_path / f"{arm}-{ctx}-t1.0-{tag}.jsonl").write_text(
                "\n".join(json.dumps(r) for r in _speed_rows(arm, ctx, tag, ttft, dec)) + "\n")
    q = tmp_path / "q/t1/o27q4-medium"; q.mkdir(parents=True)
    (q / "gpqa.jsonl").write_text("\n".join(json.dumps({"question_num": i, "correct": i % 2 == 0, "finish_reason": "stop",
                                                        "elapsed_s": 20.0 + i, "completion_tokens": 1500, "reasoning_chars": 4000})
                                            for i in range(4)) + "\n")
    (tmp_path / "gates.env").write_text("P1_PASS=1\nP1_BEST=k27\nP5_GO=0\n")
    return tmp_path


def test_payload_has_speed_per_effort_and_quality(results):
    p = rp.build_payload(results, w1_summary={"w1@32768": {"t_turno_s": 7.9}, "w1@131072": {"t_turno_s": 8.6}}, w1_ab=None)
    s = p["speed"]["131072"]
    assert set(s) == {"s27r-xhigh", "k27-xhigh", "k27-medium"}
    assert s["s27r-xhigh"]["t_turno_s"] == 25.7
    assert s["k27-medium"]["t_turno_s"] == round(2.4 + 512 / 61.0, 1)
    assert p["w1"]["131072"]["t_turno_s"] == 8.6
    assert p["quality"]["o27q4-medium"]["gpqa"]["passed"] == 2
    assert p["quality"]["o27q4-medium"]["gpqa"]["median_s"] == 21.5
    assert p["gates"]["P1_BEST"] == "k27"


def test_html_mentions_every_arm_and_both_bands(results, tmp_path):
    out = tmp_path / "page.html"
    rp.main(["--results", str(results), "--out", str(out), "--json-out", str(tmp_path / "pd.json"), "--no-w1"])
    html = out.read_text()
    for needle in ("s27r", "k27", "32K", "128K", "T_turno", "Time per task", "Tokens per answer", "Flash-Next"):
        assert needle in html
    assert "<script src=\"http" not in html  # self-contained, like the other reports


@pytest.mark.skipif(not (C / "results/gates.env").exists(), reason="campaign results not committed yet")
def test_real_data_renders_and_matches_decision_tables():
    p = rp.build_payload(C / "results", w1_summary=rp.load_w1_summary(), w1_ab=rp.load_w1_ab())
    assert "s27r-xhigh" in p["speed"]["131072"]
    assert p["w1"]["32768"]["t_turno_s"] == 7.9
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_render_27b_page.py -q`
Expected: `ModuleNotFoundError: render_27b_page`.

- [ ] **Step 3: Escrever `render_27b_page.py`**

Estrutura obrigatória (o corpo HTML segue o estilo de `bench/swift15-flashnext-2026-10/scripts/render_page.py`: CSS inline, Chart.js embutido como nas outras páginas de `reports/`, tema claro/escuro por `prefers-color-scheme`, texto em inglês):

```python
#!/usr/bin/env python3
"""Render reports/qwen38-27b-stacks.html: the dense Qwen3.8-27B stacks measured in
bench/qwen38-27b-next-steps-2026-10 against the Flash-Next driver (w1).
usage: render_27b_page.py [--results DIR] [--out HTML] [--json-out JSON] [--no-w1]
"""
import argparse, json, re, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "bench/qwen38-27b-next-steps-2026-10"
sys.path.insert(0, str(ROOT / "bench/qwen38-flashnext-daily-driver-2026-09/scripts"))
sys.path.insert(0, str(ROOT / "bench/swift15-flashnext-2026-10/scripts"))
from summarize_driver import load_records, summarize  # noqa: E402
import summarize_ab  # noqa: E402

ARMS = [  # id, name, runtime, pack, rev, port, phase
    ("s27r", "mlx-dspark 0.20.3 + DFlash2", "mlx-dspark 0.20.3", "mlx-community 8bit", "815b83c0", 8484, "P0"),
    ("k27", "Splash 1.3.1", "Splash 1.3.1", "mlx-community 8bit + DFlash2", "815b83c0", 8585, "P1"),
    ("o27q8", "oMLX oQ8e refit", "oMLX 0.7.1.dev1", "Jundot oQ8e-mtp", "6c76ddfb", 8000, "P2"),
    ("o27q4", "oMLX oQ4e refit", "oMLX 0.7.1.dev1", "Jundot oQ4e-mtp", "49c1d603", 8000, "P2"),
    ("r27d", "mlx-serve 26.10.2 MTP + drafter", "mlx-serve 26.10.2", "ddalcu 8bit", "7775059e", 11234, "P3"),
    ("r27m", "mlx-serve 26.10.2 MTP only", "mlx-serve 26.10.2", "ddalcu 8bit", "7775059e", 11234, "P3"),
    ("o27sw", "oMLX Swift 1.5 oQ4e", "oMLX 0.7.1.dev1", "scottlowry Swift-1.5 oQ4e-mtp", "881dc191", 8000, "P4"),
    ("l27", "llama.cpp b11569 draft-mtp", "llama.cpp b11569", "ggml-org Q8_0 + mtp", "71bc7b62", 8080, "P6"),
    ("l27n", "llama.cpp b11569 no spec", "llama.cpp b11569", "ggml-org Q8_0", "71bc7b62", 8080, "P6"),
]
FILE_RE = re.compile(r"^(?P<arm>[a-z0-9]+)-(?P<ctx>\d+)-t1\.0-p(?P<phase>\d)(?P<eff>[xm])\.jsonl$")
EFFORT = {"x": "xhigh", "m": "medium"}
SUITES = ("humaneval", "gpqa", "livecodebench", "jdhodges", "veerman", "if")
W1_SUMMARY = ROOT / "bench/swift15-flashnext-2026-10/results/tturno-summary.json"
W1_AB = ROOT / "bench/swift15-flashnext-2026-10/results/ab/t1/w1"


def load_w1_summary() -> dict:
    return json.loads(W1_SUMMARY.read_text()) if W1_SUMMARY.exists() else {}


def load_w1_ab() -> dict | None:
    return summarize_ab.load_arm(W1_AB) if W1_AB.exists() else None


def _speed(results: Path) -> dict:
    out: dict[str, dict] = {}
    for f in sorted(results.glob("*-t1.0-p?[xm].jsonl")):
        m = FILE_RE.match(f.name)
        if not m:
            continue
        summary = summarize(load_records([f]))
        for (arm, ctx), row in summary.items():
            out.setdefault(str(ctx), {})[f"{arm}-{EFFORT[m['eff']]}"] = {
                "t_turno_s": row["t_turno_s"], "warm_ttft_tool_s": row["warm_ttft_s"].get("tool_turn"),
                "cold_ttft_s": row["cold_ttft_s"], "decode_tps": row["decode_tps"], "hit_tool": row["hit"].get("tool_turn"),
                "mtp_acceptance": row["mtp_acceptance"], "wired_peak_gb": row["wired_peak_gb"], "gates_failed": row["gates_failed"]}
    return out


def _quality(results: Path) -> dict:
    out = {}
    for d in sorted((results / "q/t1").glob("*/")) if (results / "q/t1").exists() else []:
        arm = summarize_ab.load_arm(d)
        out[d.name] = {s: summarize_ab.suite_stats(arm[s]) for s in SUITES if s in arm}
    return out


def _gates(results: Path) -> dict:
    g = results / "gates.env"
    return dict(l.split("=", 1) for l in g.read_text().splitlines() if "=" in l) if g.exists() else {}


def build_payload(results: Path, w1_summary: dict, w1_ab) -> dict:
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "arms": [dict(zip(("id", "name", "runtime", "pack", "rev", "port", "phase"), a)) for a in ARMS],
            "speed": _speed(results),
            "w1": {str(c): {"t_turno_s": w1_summary.get(f"w1@{c}", {}).get("t_turno_s")} for c in (32768, 131072)},
            "quality": _quality(results),
            "w1_quality": {s: summarize_ab.suite_stats(w1_ab[s]) for s in SUITES if w1_ab and s in w1_ab} if w1_ab else {},
            "gates": _gates(results)}


def render_html(p: dict) -> str:
    # Sections: "Agent turn (T_turno) · 32K / 128K" (bar per arm×effort, w1 reference line), "Warm TTFT and decode",
    # "Time per task" (median s per suite per label), "Tokens per answer (median)", "Accuracy", "Gates and verdicts",
    # "Setup and how to reproduce". Chart.js is embedded from reports/charts-common.js like the sibling pages.
    ...  # build with f-strings; keep every label listed above verbatim


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=C / "results")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/qwen38-27b-stacks.html")
    ap.add_argument("--json-out", type=Path, default=C / "results/page-data.json")
    ap.add_argument("--no-w1", action="store_true")
    a = ap.parse_args(argv)
    p = build_payload(a.results, {} if a.no_w1 else load_w1_summary(), None if a.no_w1 else load_w1_ab())
    a.json_out.write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    a.out.write_text(render_html(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
O `render_html` é escrito por inteiro no Task (o `...` acima marca só onde entra; o teste `test_html_mentions_every_arm_and_both_bands` fixa os rótulos obrigatórios: `T_turno`, `Time per task`, `Tokens per answer`, `Flash-Next`, `32K`, `128K`, e cada id de braço). Reusar de `render_page.py` as funções de CSS e o bloco de tema; se `charts-common.js` for carregado por `<script src="charts-common.js">` relativo nas páginas irmãs, fazer o mesmo (o teste só proíbe `http`).

- [ ] **Step 4: Rodar os testes e gerar a página real**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests/test_render_27b_page.py -q && python3 bench/qwen38-27b-next-steps-2026-10/scripts/render_27b_page.py && ls -la reports/qwen38-27b-stacks.html bench/qwen38-27b-next-steps-2026-10/results/page-data.json`
Expected: `3 passed`; os dois arquivos existem. Abrir `reports/qwen38-27b-stacks.html` no browser embutido e conferir que os gráficos renderizam nas duas bandas e que a linha de referência w1 aparece.

- [ ] **Step 5: Card no `reports/index.html`**

Na `<section class="block" id="dense">`, ao lado dos cards existentes, acrescentar (copiando a forma dos vizinhos):

```html
<a class="card" href="qwen38-27b-stacks.html">
  <div class="c-title">Qwen3.8-27B dense · stacks vs the Flash-Next driver</div>
  <div class="c-desc">Splash 1.3.1, oMLX 0.7.1 refit packs, mlx-serve 26.10.2 native MTP, Swift 1.5 27B and llama.cpp draft-mtp measured on the M4 Max 128 GB: agent-turn time at 32K/128K, time and tokens per task, accuracy, gates.</div>
  <div class="c-meta">2026-10 · qwen38-27b-stacks.html</div>
</a>
```
Se já houver um card para `overview.html` ou `perf-lines.html` do 27B nessa seção, manter os dois: eles são as páginas históricas de agosto.

- [ ] **Step 6: Card do modelo `docs/models/qwen3.8-27b.md`**

Seguir a forma de `docs/models/qwen3.6-27b.md`: status, "At a glance (official)" (64 camadas, 48 GDN + 16 atenção, 4 KV heads × 256, contexto 262144, Apache-2.0, lançamento 2026-08-14, MTP 1 camada, thinking por padrão, `reasoning_effort` xhigh/medium/low, sampling do vendor), "Variants on this rig" (a tabela de braços desta campanha com revisão, disco, runtime, porta, status), "Local performance (measured)" (as tabelas `T_turno` de `27b-summary.md`, `etapa-f-fixes.md` e das etapas desta campanha, com data), "Quality (measured)" (a tabela da bateria), "Quirks" (`high` → HTTP 500; `xhigh` vazio; oMLX `enable_thinking`; llama.cpp #27756 e #30174; oMLX #4214; Splash `pkill`), "Verdict" (o veredito desta campanha, com link para `research/qwen38-27b-next-steps-20261013.md` e para `results/etapa*`), e uma nota: "A referência `[[qwen38-27b-nogo-verdict]]` usada em planos de setembro apontava para um gate de Terminal-Bench que nunca rodou no rig; o veredito vigente é o desta campanha." Acrescentar a linha do 27B em `docs/models/README.md`.

- [ ] **Step 7: Notas de pin superado e link no spec**

Em `bench/engine-updates-2026-10/results/27b-summary.md`, logo abaixo do título, acrescentar: `> 2026-10: o braço o27 usou o pack Jundot oQ8e-mtp @ c99e5aad, re-quantizado em 11/10 (6c76ddfb). Medições do pack novo: bench/qwen38-27b-next-steps-2026-10/results/etapa2-o27q8.md.` Em `research/qwen38-27b-next-steps-20261013.md`, abaixo do título, acrescentar `> Resultados: [bench/qwen38-27b-next-steps-2026-10/](../bench/qwen38-27b-next-steps-2026-10/plan.md); página: [reports/qwen38-27b-stacks.html](../reports/qwen38-27b-stacks.html).`

- [ ] **Step 8: Testes de toda a campanha e commit**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests bench/swift15-flashnext-2026-10/tests/test_render_page.py -q 2>&1 | tail -2`
Expected: tudo passa (o teste de card do índice da campanha Swift continua passando: o card novo não altera os existentes).

```bash
git add reports/qwen38-27b-stacks.html reports/index.html docs/models bench/qwen38-27b-next-steps-2026-10 bench/engine-updates-2026-10/results/27b-summary.md research/qwen38-27b-next-steps-20261013.md
git commit -m "bench(qwen38-27b): Task 8 - stacks page, index card, model card, superseded-pin notes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 9: Veredito, PR e encerramento

**Files:**
- Create: `bench/qwen38-27b-next-steps-2026-10/results/summary.md`
- Modify: `docs/models/qwen3.8-flash-next.md` (uma linha em "Next tests" apontando para o summary do 27B), `docs/local-llm-reference.md` (linha do Qwen3.8-27B com status e link)

- [ ] **Step 1: Escrever `results/summary.md`**

Conteúdo, nesta ordem: (1) tabela de ranking por `T_turno` a 32K e 128K de todos os braços em `xhigh` e `medium`, com s27r e w1 como linhas de referência e a razão sobre w1; (2) uma linha por fase com `VERDICT` e a regra aplicada (copiar das `etapaN-*.md`); (3) tabela da bateria (acerto, mediana de tempo, tokens medianos, truncados, respostas vazias, loops) para `o27q4-medium`, `o27sw-medium`, o melhor de P1/P3 se rodou, e w1 (xhigh, da campanha Swift, marcado como esforço diferente); (4) o valor de `P5_GO` e o que ele significa (se `0`: "nenhum braço do 27B chegou a 1.25× o driver; P5 não roda; o NO-GO como driver continua"; se um braço: "P5 deve rodar no MacBook com OpenCode contra o w1 antes de qualquer promoção"); (5) "Configuração recomendada do 27B hoje" (runtime, pack, flags, esforço) com as razões medidas; (6) "O que não foi medido" (o27q8 na bateria, 256K, P5).

- [ ] **Step 2: Atualizar as referências**

Em `docs/models/qwen3.8-flash-next.md`, na nota "Next tests", acrescentar `Dense 27B next steps: bench/qwen38-27b-next-steps-2026-10/results/summary.md`. Em `docs/local-llm-reference.md`, acrescentar uma linha para `qwen3.8-27b` com o status decidido (🔴 NO-GO para driver, ou 🟡 condicional a P5) e o link para o card. Em `bench/qwen38-flashnext-daily-driver-2026-09/plan.md:248` e `bench/qwen38-updates-2026-09/plan.md:199`, trocar `([[qwen38-27b-nogo-verdict]])` por `(veredito: docs/models/qwen3.8-27b.md)`.

- [ ] **Step 3: Religar o driver diário e conferir o rig limpo**

```bash
ssh vitor@mac-studio 'lsof -nP -tiTCP:11234 -sTCP:LISTEN >/dev/null && echo "driver up" || (nohup bash ~/LocalProjects/local-llms/tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 & sleep 60; curl -s http://localhost:11234/v1/models | head -c 200); for p in 8000 8080 8484 8585; do lsof -nP -tiTCP:$p -sTCP:LISTEN && echo "port $p busy" || true; done; pgrep -fl "run-campaign|cache_probe" || echo "no campaign process"'
```
Expected: `driver up` (ou o JSON de `/v1/models` com o id do Swift 1.5), nenhuma porta de teste ocupada, `no campaign process`.

- [ ] **Step 4: Commit e PR**

```bash
git add bench/qwen38-27b-next-steps-2026-10 docs/models docs/local-llm-reference.md bench/qwen38-flashnext-daily-driver-2026-09/plan.md bench/qwen38-updates-2026-09/plan.md
git commit -m "bench(qwen38-27b): Task 9 - campaign summary, verdict, reference updates

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
gh pr create --title "bench(qwen38-27b): next steps 2026-10 — Splash, oMLX refit, mlx-serve 26.10.2, Swift 1.5 27B, GGUF" --body "$(cat <<'EOF'
## Summary
- Unattended campaign on the dense Qwen3.8-27B: speed phases P0–P6 (T_turno at 32K/128K, xhigh and medium), think-turn probes, Swift-style quality battery with time and tokens per task, loops.
- New: Splash 1.3.1 launcher, llama.cpp 27B launcher, oMLX refit arms, mlx-serve 26.10.2 native-MTP arms, campaign runner, `reports/qwen38-27b-stacks.html`, `docs/models/qwen3.8-27b.md`.
- Verdict: see `bench/qwen38-27b-next-steps-2026-10/results/summary.md`.

## Test plan
- [ ] `uv run --no-project --with pytest python -m pytest bench/qwen38-27b-next-steps-2026-10/tests bench/flashnext-next-steps-2026-10/tests bench/engine-updates-2026-10/tests bench/qwen38-flashnext-daily-driver-2026-09/tests -q`
- [ ] `reports/qwen38-27b-stacks.html` opens and the index card links to it
- [ ] daily driver is back on 11234

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Auto-revisão (feita ao escrever o plano)

- **Cobertura do spec.** P1 → Tasks 2, 3, 5, 6 (braço `k27`, regra 0.75×, `--skip-gates`); P2 → Tasks 1, 3, 6, 7 (packs refit, braços `o27q8`/`o27q4`, bateria do `o27q4`); P3 → Tasks 2, 3, 6 (`r27d`/`r27m`, `--mtp-max-depth 3`, `think_turn_probe`); P4 → Tasks 1, 3, 6, 7 (`o27sw`, tempo até resposta final e tokens via `summarize_ab`, loops, aceitação MTP comparada no `etapa4`); P6 → Tasks 1, 3, 6 (`l27`/`l27n`, 64K, RSS no `mem-sampler` via `server_rss_gb`); P5 → gate `P5_GO` (Task 4) e instrução no Task 9; métricas do Flash-Next → mesmo probe e `decide.py`; métricas da Swift → `run-battery.sh` + `summarize_ab.py` (Task 7) e página (Task 8). Lacuna assumida e dita: o27q8 fora da bateria por custo (Task 7 Step 3).
- **Placeholders.** O único trecho marcado com `...` é o corpo de `render_html` (Task 8 Step 3), com os rótulos obrigatórios fixados pelo teste. As flags do Splash dependem de descoberta (Task 2 Step 8) e ficam num arquivo de configuração testado pelo `--print`.
- **Consistência de nomes.** `FLASHNEXT_EFFORT` (Tasks 0, 3, 4); tags `p<N>x`/`p<N>m` (Tasks 4, 8, `FILE_RE`); `BATTERY_CAMPAIGN_DIR` (Tasks 0, 4, 7); `--skip-gates hit_append,hit_tool_turn` (Tasks 0, 4); labels `<arm>-medium`/`<arm>-xhigh` (Tasks 4, 7, 8); `gates.env` chaves `P<N>_PASS`, `P<N>_BEST`, `P5_GO`, `CAMPAIGN_DONE` (Tasks 4, 8, 9).
- **Review Focus.** Cada um dos cinco itens tem o teste ou o passo que o verifica indicado no próprio item.
