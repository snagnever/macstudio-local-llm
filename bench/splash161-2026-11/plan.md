# Splash 1.6.1 contra 1.5.0 — runbook da campanha (2026-11-11)

> **Status (2026-11-11): proposto, aguarda aprovação do usuário.** Nada rodou. Branch: `bench/splash161-2026-11`, a partir da `bench/splash16-2026-11` (PR #84, sem merge).
>
> **Para agentes:** use superpowers:executing-plans. Execute as tasks em ordem. Marque cada step (`- [ ]` → `- [x]`). Pare só nas condições de "Execução".

**Objetivo:** decidir se o launcher do Splash no rig passa da 1.5.0 para a 1.6.1. A [splash16](../splash16-2026-11/results/summary.md) manteve a 1.5.0 por uma regressão: duas sessões de 256K ficaram até 65% mais lentas na 1.6.0, com espera por memória de até 30 s. A 1.6.1 muda essa espera, o staging de experts no M4 Max e o modo padrão da tabela PLE.

| # | pergunta | teste | task |
|---|---|---|---:|
| 1 | O pack carrega, e a troca de versão quebra algum cliente? | boot, API, log, restart do engine | 0, 1 |
| 2 | A 1.6.1 mantém o `T_turno` de um stream, nos dois modos de PLE? | ABBA de 32K a 256K; 1M | 2 |
| 3 | A regressão de duas sessões longas some? | `k2c2LL` a 256K e `k2c2a` a 128K, com controle no mesmo dia | 3 |
| 4 | As sessões do Claude Code mantêm o ganho da 1.6.0? | `rc2` e `rc2s` a 131072 | 4 |
| 5 | Sob limite de memória, a 1.6.1 continua sem stall? | churn com `--max-memory 64G` | 5 |
| 6 | A qualidade continua igual? | bateria t1, tool calls, longctx | 6 |
| 7 | Uma carga de agente de 4 h continua estável? | Claude Code por 4 h | 7 |

**Arquitetura:** a campanha reusa os scripts da splash16 pelo caminho: `serving_load.py`, `api_contract.py`, `engine_restart.py`, `proxy_capture.py`, `agent_soak.sh` e `summarize_load.py`. Ela reusa também o `run-candidate.sh`, o `cache_probe.py`, o `run-parallel-probes.sh`, o `run-claude-pair.sh`, o `request_log.py`, o `run-battery.sh`, o `toolcall-probe.sh`, o `longctx_probe.py`, o `summarize_ab.py` e o `decide.py`. O código novo é um braço `h` no `run-candidate.sh`, uma correção no parser de log do Claude Code e um resumo da espera por memória.

**Stack:** bash 3.2 e Python 3.9 stdlib no rig; pytest via `uv run --no-project --with pytest`.

**Spec:** este plano, o pedido do usuário de 11/11 e a [nota de stack de 11/11](../../research/rig-stack-updates-20261111.md), teste 1.

## O que a 1.6.1 muda para o rig

**Terceiro**, [notas da 1.6.1](https://github.com/incoai/splash/blob/1.6.1/docs/release-notes/1.6.1.md). Nenhum número é de M4 Max.

| mudança | hipótese | task |
|---|---|---:|
| Uma lane mantém na RAM as páginas copiadas no SSD até um claim precisar delas | a espera por memória de duas sessões de 256K cai | 3 |
| Dois requests longos no limite de memória terminam como cada um sozinho | idem | 3, 5 |
| `--ple-memory auto` lê a tabela PLE de 28.8 GB pelo SSD, com cache de 237 MiB | sobram ~28 GB para KV; o primeiro token de um prompt novo pode atrasar | 2, 3 |
| GPUs M4 Max com mais de 10 cores fazem staging de experts; o decode depende do batch | o decode de um stream e o de dois streams mudam | 2, 3 |
| Kernels de prefill e de decode longo criados antes do Ready | o primeiro start fica mais longo; requests não esperam kernel | 0 |
| Linha de log `Done · request N · …` | o `claude_requests.py` deixa de ler o log | 0 |
| Engine que para de vez sai com exit 69; `/status` ganha campos | as sondas e a fila precisam aceitar isso | 1 |
| Update apaga do cache do HF os arquivos do commit anterior sem link | o pack do `k2f` pode sumir do cache | 0 |
| GGUF com `general.alignment` abaixo de 8 é recusado | o pack pode não subir | 0 |

**Fora do escopo:** `--activations auto` (vale só para M5 ou mais novo), app para Mac, PDF, Bonsai, Qwen3.6 e o 27B.

## Restrições globais

- **Rig:** Mac Studio M4 Max 128 GB. `ssh vitor@mac-studio`, ou `vitor@100.110.87.118`. Um modelo por vez.
- **Runtimes:** `~/.local/opt/qwen38/splash-v1.5.0/` e `splash-v1.6.1/`. Instalar a 1.6.1 com `SPLASH_TAG=1.6.1 install-runtime.sh splash`. Não usar `brew upgrade`. Não instalar outra versão durante a campanha. A 1.6.0 fica instalada e fora da fila.
- **Pesos fixos:** `k2` = `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS` `0142554c963a8653912c0c8283f05f13f63653f3`.
- **Flags de base:** `--verify-rows auto --idle-release off --language-only --no-webui --offline`, porta 8585. Sem `--persistent-cache`.
- **Modos de PLE na 1.6.1:** `auto` é o padrão da release. `off` mantém a tabela na RAM, como na 1.6.0. Os resultados com `off` usam a tag com sufixo `p` e a runtime-revision com sufixo `-ple-off`.
- **Sampling:** `temperature 1.0`, `top_p 0.95`, `top_k 20`, `frequency_penalty 0`, `reasoning_effort xhigh`.
- **Gates de velocidade:** zero HTTP 4xx/5xx; needles corretas; hit ≥ 0.90 em `append` e `tool_turn`; swap Δ ≤ 0.5 GB.
- **Controle no mesmo dia:** todo veredito de concorrência compara com a 1.5.0 na mesma fila. A splash16 mostrou que o decode somado do `k2c2LL` muda 2 vezes entre dias.
- **Protocolo térmico:** `idle-gate.sh` entre bandas; 120 s entre braços; ordem ABBA entre versões.
- **Claude Code:** fixar a 2.1.292 com `CLAUDE_BIN`, a mesma versão dos baselines.
- **Idioma e commits:** prosa em pt-BR; código e git em inglês. Commits `bench(splash161): ...`, com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` no fim.
- **Saídas:** `results/` rastreado, com os JSONL por request e por questão. `logs/` ignorado. Um JSONL de `/status` acima de 1 MB fica só com o último registro de cada boot.

## Regras de decisão

| veredito | regra |
|---|---|
| **Paridade de velocidade** | `T_turno(1.6.1) ≤ 1.03 × T_turno(1.5.0)` a 32K, 128K e 256K, com todos os gates, em cada modo de PLE |
| **Concorrência** | média do pior stream em 3 reps de `k2c2LL` a 256K e de `k2c2a` a 128K ≤ 1.10 × a média da 1.5.0 na mesma fila |
| **Claude Code** | wall do par e warm TTFT p50 de `rc2` e `rc2s` ≤ 1.10 × o controle da 1.5.0 na mesma fila. O tok/s mínimo fica só como registro |
| **Stall** | maior gap ≤ 10 s e p99 ≤ 5 s, e todos os requests respondidos |
| **Qualidade** | G1 do `summarize_ab.py` contra o `k2f` da W1 e da W2 da [campanha de pesos](../flashnext-weights-2026-11/results/summary.md); tool calls ≥ `k2f` − 1 nos perfis `fp0` e `fp1`; longctx 8/8 |
| **Queda de decode** | sonda de 64 tokens no fim ÷ sonda antes da carga: ≥ 0.85 estável; 0.50–0.85 degradado; < 0.50 queda |
| **Modo de PLE do launcher** | o modo que passa nas Tasks 2 e 3. Se os dois passam, o de menor pior stream no `k2c2LL`. Empate em 5%: `auto`, porque não precisa de flag |
| **Trocar o launcher** | as Tasks 1 a 6 passam num mesmo modo de PLE, e a Task 7 não mostra regressão |

O driver diário não muda nesta campanha. A troca do driver fica com o usuário.

## Review Focus

1. **Log novo e parser antigo.** Se o `claude_requests.py` não casar com a linha `Done` da 1.6.1, ele devolve zero requests sem erro, e o TTFT quente fica vazio. Teste: `test_parse_splash_log_reads_161_lines`, com linhas reais do smoke, e `test_parse_splash_log_counts_match_proxy` na Task 4.
2. **Pack do `k2f` apagado pelo update.** A 1.6.1 pode apagar do cache do HF arquivos que a 1.5.0 lê com `--offline`. Teste: smoke do Task 0 na ordem `h`, `f`, `h`, com o tamanho do snapshot antes e depois.
3. **Warm-up do primeiro start.** O primeiro start da 1.6.1 cria os kernels antes do Ready e pode levar minutos. Ele não pode cair dentro de uma medida do ABBA. Teste: smoke do Task 0, com o tempo até `/health` de cada start; o primeiro start fica fora das medidas.
4. **PLE em stream esconde custo no cold.** O modo `auto` lê linhas da PLE do SSD num prompt novo. O cold TTFT de cada banda entra no resumo da Task 2, separado do warm.
5. **Exit 69 no meio de uma fila.** Se o engine parar de vez, o servidor sai, e o braço seguinte sobe outro. A fila registra o exit e segue. Teste: `test_run_seq_records_exit_69_and_continues`.

## Execução

- **Filas:** cada fila roda no rig com `nohup bash logs/chain-tN.sh > logs/chain-tN.log 2>&1 &`. Ela para o servidor do usuário na porta 8585 no início e o religa no fim, com o `serve-flashnext-splash.sh` na 1.5.0.
- **Código:** commit no MacBook e `git bundle` para o rig, como na [splash-longctx](../splash-longctx-2026-10/plan.md#execução-autônoma).
- **Falha:** um braço que falha não para a fila. Registrar o erro e seguir.
- **Ordem com portão:** as Tasks 6 e 7 só rodam se as Tasks 1 a 5 passarem num mesmo modo de PLE. Se não passarem, a Task 8 fecha a campanha com o launcher na 1.5.0.
- **Pare e espere o usuário se:**
  1. o `k2h` não subir na 1.6.1;
  2. o `k2f` não subir depois de um boot da 1.6.1;
  3. disco livre < 150 GB, ou swap Δ > 2 GB, ou kernel panic;
  4. o servidor do usuário não voltar no fim de uma fila;
  5. o rig seguir inacessível por SSH no Task 0.
- **Publicação:** não comentar nem abrir issue no GitHub sem pedido do usuário.

## Tempo estimado no rig

| task | conteúdo | horas |
|---|---|---:|
| 0 | instalação e smoke | 1.5 |
| 1 | contrato | 1 |
| 2 | um stream, dois modos de PLE | 7 |
| 3 | concorrência, controle no mesmo dia | 5 |
| 4 | Claude Code | 3 |
| 5 | churn | 1 |
| 6 | qualidade, com portão | 9 |
| 7 | 4 h de agente, com portão | 4.5 |
|  | **total** | **~32; ~18.5 sem as Tasks 6 e 7** |

As horas vêm das Tasks equivalentes da splash16 e da W1 da campanha de pesos.

## Mapa de arquivos

| arquivo | ação | responsabilidade |
|---|---|---|
| `bench/splash161-2026-11/scripts/run-arm.sh`, `run-seq.sh` | Create | cópias dos da splash16, com `HERE` aqui; o `run-seq.sh` grava o exit de cada braço |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify | `SPLASH_161`, braços `k[1-8]h`, tag `1.6.1`, `FLASHNEXT_SPLASH_XARGS` e `FLASHNEXT_SPLASH_REVX` nos braços `k2c*` e `rc*` |
| `bench/flashnext-concurrency-2026-10/scripts/claude_requests.py` | Modify | regex `STARTED` e `DONE` que aceitam o número do request |
| `bench/splash16-2026-11/scripts/api_contract.py` | Modify | `--version 1.6.1`, com o comportamento esperado da 1.6.x |
| `bench/splash161-2026-11/scripts/summarize_claims.py` | Create | espera por memória por boot, do JSONL de `/status` |
| `bench/splash161-2026-11/tests/` | Create | testes dos braços, do parser, do resumo e da fila |
| `tools/scripts/serve-flashnext-splash.sh` | Modify (Task 8) | versão e modo de PLE do launcher, só se a regra passar |

---

### Task 0: Pré-voo, braços, ferramentas e smoke

**Interfaces produzidas:**

- `SPLASH_161="$OPT/splash-v1.6.1/bin/splash"`. Braços `k[1-8]h`: o `k[1-8]f` na 1.6.1, com `SREV=v1.6.1` e `SVER=1.6.1`.
- `FLASHNEXT_SPLASH_TAG` aceita `1.5.0`, `1.6.0` e `1.6.1`.
- `FLASHNEXT_SPLASH_XARGS` chega aos braços `k[1-8][fgh]`, `k2c*` e `rc*`. `FLASHNEXT_SPLASH_REVX` é somado ao fim da runtime-revision desses braços. Sem as duas variáveis, o comando de todo braço antigo fica igual.
- `claude_requests.parse_splash_log(text)` aceita as linhas da 1.5.0, da 1.6.0 e da 1.6.1, com o mesmo schema de saída.
- `api_contract.py --version 1.6.1`: os mesmos esperados da `1.6.0`.
- `summarize_claims.py <status.jsonl> [...] --out-md P`: uma linha por boot, com `claim_wait` máximo e total, gaps `prefill_unit` e o último `pages_cache`. Os campos vêm de `metrics.ttft_parts_ms` e `metrics.decode_gap_causes`.
- `run-seq.sh` grava `=== <data> end <arm>@<ctx> rc=<exit>` para cada braço e segue com exit diferente de 0.

**Steps:**

- [x] **Step 1: Acesso e estado do rig.** Confirmar `ssh -o BatchMode=yes vitor@mac-studio hostname`. Gravar em `results/etapa0-preflight.md`: macOS, disco, versão do Claude Code, binários em `~/.local/opt/qwen38`, tamanho do snapshot `0142554` no cache do HF e `env | grep -i proxy` num shell interativo (`zsh -ilc`).
- [x] **Step 2: Proxy.** Se o shell interativo do rig define `http_proxy` e o servidor usou `--api-key` com a 1.5.0, avisar o usuário para trocar a chave.
- [x] **Step 3: Instalar.** `SPLASH_TAG=1.6.1 bash bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh splash`. O asset é `splash-1.6.1-arm64-macos26.tar.gz`, com digest `sha256:0ed408a781f951a13ff58bed95c9e8c1d1dc67ab9d649fcaf365972b6720ce6c`. Gravar `splash --version` e o help em `results/splash-161-help.txt`. Comparar com o `splash-160-help.txt` da splash16 e registrar os flags novos e os removidos. Confirmar que `--ple-memory off` existe.
- [x] **Step 4: Testes que falham** em `tests/test_arms.py` e `tests/test_tools.py`:

  ```python
  def test_k2h_runs_splash_161():             # --print: splash-v1.6.1/bin/splash, ukisai ...:IQ4_XS, --revision 0142554..., --runtime-revision v1.6.1-verify-auto
  def test_k2f_and_k2g_are_unchanged():       # k2f: splash-v1.5.0, v1.5.0-verify-auto; k2g: splash-v1.6.0, v1.6.0-verify-auto
  def test_tag_161_moves_k2c_and_rc():        # FLASHNEXT_SPLASH_TAG=1.6.1: k2c2LL e rc2 usam splash-v1.6.1 e --runtime-revision v1.6.1-verify-auto
  def test_bad_tag_is_refused():              # FLASHNEXT_SPLASH_TAG=1.7.0: exit 64
  def test_xargs_and_revx_reach_k2c_and_rc(): # XARGS="--ple-memory off", REVX="-ple-off": o comando tem "--verify-rows auto --ple-memory off" e a revision termina em "-ple-off"
  def test_old_k2c_commands_stay_the_same():  # sem as variáveis: k2c2LL e rc2 na 1.5.0 têm o mesmo --print de antes (fixture gravada antes da mudança)
  def test_run_seq_records_exit_69_and_continues():  # braço falso sai com 69: a linha "end ... rc=69" aparece, e o braço seguinte roda
  def test_claims_summary_reads_last_status_per_boot():  # fixture de 2 boots: claim_wait máximo 30.3 e 0; total 61.4 e 0
  def test_claims_summary_accepts_status_without_metrics():  # registro com metrics null (1.5.0): linha com "–", sem erro
  def test_contract_accepts_161_as_16x():     # api_contract --version 1.6.1 com o servidor falso da 1.6.0: todas as linhas pass true
  ```

- [x] **Step 5: Rodar e ver que falham.** `uv run --no-project --with pytest python -m pytest bench/splash161-2026-11/tests -q`.
- [x] **Step 6: Implementar.** Gravar a fixture de `test_old_k2c_commands_stay_the_same` antes de mudar o `run-candidate.sh`.
- [x] **Step 7: Rodar e ver que passam.** As suítes de `bench/splash16-2026-11/tests`, `bench/flashnext-concurrency-2026-10/tests` e `bench/flashnext-weights-2026-11/tests` também passam.
- [x] **Step 8: Smoke no rig**, com o tempo até `/health` de cada start e o tamanho do snapshot `0142554` em `results/etapa0-smoke.md`:
  1. `k2h` a 32768, só o cold. É o primeiro start: registrar o warm-up (`Warming up · N of M steps`).
  2. `k2f` a 32768, só o cold. Ele precisa subir com `--offline`.
  3. `k2h` a 32768 com `FLASHNEXT_SPLASH_XARGS="--ple-memory off"`, só o cold.
  4. `FLASHNEXT_SPLASH_TAG=1.6.1 k2c2a` a 32768, 1 rep. O `/status` precisa mostrar dois requests em decode.
  5. `FLASHNEXT_SPLASH_TAG=1.6.1 rc1` com a tarefa `a`, 1 rep. Copiar 3 linhas `Started` e 3 linhas `Done` do log do servidor para `tests/fixtures/splash-161-log.txt`.
- [x] **Step 9: Parser do log.** Escrever `test_parse_splash_log_reads_161_lines` com a fixture do Step 8: 3 requests, com `input_tokens`, `cached_tokens`, `output_tokens`, `ttft_s` e `tps` iguais aos das linhas. Ver que falha. Mudar as regex `STARTED` e `DONE` do `claude_requests.py` para aceitar `request N · ` opcional depois de `Started · ` e de `Done · `. Ver que passa, com os testes antigos do `test_claude_requests.py`.
- [x] **Step 10: Commit.** `bench(splash161): Task 0 — 1.6.1 arms, log parser, claim summary`.

### Task 1: Contrato da atualização

**Files:** `results/etapa1-contrato.md`, `results/contract-161.jsonl`, `results/engine-restart-161.json`.

- [x] **Step 1: C1 a C7** com `api_contract.py --version 1.6.1` no `k2h` a 32768. A splash16 tem o resultado da 1.5.0 e da 1.6.0. Uma linha `pass: false` vira item em `etapa1-contrato.md`.
- [x] **Step 2: Proxy.** Repetir o Step 3 da Task 1 da splash16 só na 1.6.1, com a chave de teste gerada na hora. Esperado: zero hits e `NO_PROXY` com os hosts de loopback. Não gravar o valor da chave em nenhum arquivo.
- [x] **Step 3: Restart do engine.** `engine_restart.py` no `k2h`. Esperado, como na 1.6.0: 503 `engine_recovering` com `Retry-After`, primeiro 200 antes de 2 × o tempo de boot, e `capabilities.max_context_tokens` igual. Registrar se o servidor sai com exit 69 em vez de voltar.
- [x] **Step 4: `/status` novo.** Registrar a presença de `console.dropped_lines`, `memory_governor.count_checks`, `metal.pipelines_created_while_serving`, `kv_spill.releases` e `tokenizer_cache.misses`. Registrar `metal.pipelines_created_while_serving` no fim de cada braço das Tasks 2 e 3.
- [x] **Step 5: Gravar `results/etapa1-contrato.md` e commitar.**

### Task 2: Velocidade e cache de um stream

O braço `k2hp` é o `k2h` com `FLASHNEXT_SPLASH_XARGS="--ple-memory off"` e `FLASHNEXT_SPLASH_REVX=-ple-off`.

- [x] **Step 1: Fila ABBA de `cache_probe`, 3 reps** por braço e banda. Cada posição é um boot com 1 rep:

  | banda | ordem |
  |---|---|
  | 32768 | `k2f`, `k2h`, `k2hp`, `k2hp`, `k2h`, `k2f`, `k2f`, `k2h`, `k2hp` |
  | 131072 | `k2hp`, `k2h`, `k2f`, `k2f`, `k2h`, `k2hp`, `k2hp`, `k2h`, `k2f` |
  | 262144 | `k2f`, `k2h`, `k2hp`, `k2hp`, `k2h`, `k2f`, `k2f`, `k2h`, `k2hp` |

- [x] **Step 2: 1M.** `k2h` a 1000000 com 1 rep. A referência é o `k2g` da splash16. Verificar zero `capacity_exhausted`.
- [x] **Step 3: Resumo.** `decide.py --base k2f --cand k2h --ctx 32768,131072,262144 --mode le --threshold 1.03`, e o mesmo com `--cand k2hp`. Gravar `results/etapa2-um-stream.md` com: cold TTFT, warm TTFT, hit, `middle_mutation`, decode, wired peak, livre mínimo e swap Δ de cada braço.
- [x] **Step 4: Commit.**

### Task 3: Concorrência de requests paralelos

Esta é a task que decide a campanha. Tudo com tag `h1` (1.6.1, PLE `auto`), `h1p` (1.6.1, PLE `off`) e `f1` (1.5.0), na mesma fila, e com o `/status` gravado a cada 5 s.

| braço | contexto | ordem dos boots, 1 rep cada |
|---|---|---|
| `k2c2LL` | 262144 | `f1`, `h1`, `h1p`, `h1p`, `h1`, `f1`, `f1`, `h1`, `h1p` |
| `k2c2a` | 131072 | `h1p`, `h1`, `f1`, `f1`, `h1`, `h1p`, `h1p`, `h1`, `f1` |

- [x] **Step 1: Fila.** Para `h1` e `h1p`, usar `FLASHNEXT_SPLASH_TAG=1.6.1`. Para `h1p`, somar `FLASHNEXT_SPLASH_XARGS="--ple-memory off"` e `FLASHNEXT_SPLASH_REVX=-ple-off`.
- [x] **Step 2: Resumo.** `summarize_parallel.py` por tag, e `summarize_claims.py` nos JSONL de `/status`. Gravar `results/etapa3-concorrencia.md` com:
  - pior stream, s1 e s2, decode somado e warm TTFT da tool, por tag, com a média das 3 reps;
  - `claim_wait` máximo e total, gaps `prefill_unit` e linhas `pending` no log de boot;
  - a razão de cada tag da 1.6.1 contra o `f1`, e o veredito da regra "Concorrência" por modo de PLE.
- [x] **Step 3: Escolher o modo de PLE** pela regra do início, com as Tasks 2 e 3. As Tasks 4 a 7 rodam só nesse modo. Se nenhum modo passa, pular para a Task 8.
- [x] **Step 4: Commit.**

### Task 4: Sessões do Claude Code

Tarefas c e d, contexto 131072, `CLAUDE_BIN` na 2.1.292. A tag da 1.6.1 é `h1` ou `h1p`, a do modo escolhido.

| perfil | 1.5.0 (`f1`) | 1.6.1 |
|---|---:|---:|
| `rc2` | 2 reps | 3 reps |
| `rc2s` | 2 reps | 3 reps |

- [x] **Step 1: Teste.** `test_parse_splash_log_counts_match_proxy`: com um log da 1.6.1 e o JSONL do `request_log.py` do mesmo par, o número de requests lidos do log fica igual ao do proxy. Ver que falha sem a correção do Task 0 e passa com ela. Usar os arquivos da primeira rep.
- [x] **Step 2: Fila,** alternando as releases: `f1`, `h`, `h`, `f1`, `h` para cada perfil.
- [x] **Step 3: Resumo.** `summarize_claude.py`. Gravar `results/etapa4-claude-code.md` com o wall, o warm TTFT p50 e p90, o warm tok/s p50 e mínimo, as tarefas cumpridas e o veredito da regra "Claude Code".
- [x] **Step 4: Commit.**

### Task 5: Pressão de memória

Churn de 15 min sob `--max-memory 64G`, contexto 131072, na ordem `k2f`, `k2h`, `k2h`, `k2f`, no modo de PLE escolhido. A splash16 mediu um maior gap de 48.8 s na 1.5.0 e de 2.5 s na 1.6.0.

- [x] **Step 1: Fila.** `serving_load.py churn` nas quatro posições.
- [x] **Step 2: Resumo.** `summarize_load.py` aplica o gate de stall. Gravar `results/etapa5-pressao.md`: maior gap, p99, requests sem resposta, requests feitos e `metrics.decode_gap_causes` na 1.6.1.
- [x] **Step 3: Commit.**

### Task 6: Qualidade

Só roda se as Tasks 1 a 5 passam no modo de PLE escolhido. Braço `k2h` no modo escolhido, a 262144.

- [x] **Step 1: Bateria.** `run-battery.sh k2h v161 --suites "humaneval gpqa livecodebench if jdhodges veerman" --ctx 262144`, com effort `xhigh`, como a W1 da campanha de pesos. Commitar os JSONL por questão.
- [x] **Step 2: Tool calls.** `toolcall-probe.sh k2h --sessions 20 --suffix v161 --max-tokens 2048`, com `TOOLCALL_CAMPAIGN_DIR` nesta campanha. O script roda os perfis `fp0` e `fp1`. A nota conta sessões com todos os turnos certos, como a W1.
- [x] **Step 3: Longctx.** `longctx_probe.py --context 262144` e `--context 131072`.
- [x] **Step 4: Resumo.** `summarize_ab.py`, G1 e G2, do `k2h` contra o `k2f` W1 (293 de 336) e contra o `k2f` W2 (302 de 336). O G1 passa se passa nas duas comparações. Se uma suíte falhar no G1, repetir a suíte uma vez no `k2h` e no `k2f`, antes do veredito. Gravar `results/etapa6-qualidade.md`, com a mediana de tokens em gpqa e livecodebench.
- [x] **Step 5: Commit.**

### Task 7: Carga de agente de 4 h

Só roda se a Task 6 passa. `agent_soak.sh --hours 4 --tag h161` no `k2h`, no modo escolhido, a 131072, com um boot só. As referências são o `k2f` e o `k2g` da Task 7 da splash16, de outro dia. Por isso, só a regra de queda, que compara a sonda do fim com a sonda do início do mesmo run, dá veredito.

- [ ] **Step 1: Fila.** Um `task_done` falso não para a fila. Se o pool não chegar ao teto, registrar que o teste não exercitou a queda.
- [ ] **Step 2: Resumo.** `results/etapa7-agente-4h.md`, por hora: tok/s p50, TTFT quente p50 e p90, sonda curta, `pages_cache`, `denied_reservations`, requests, erros e `task_done`.
- [ ] **Step 3: Commit.**

### Task 8: Decisão, launcher e fechamento

- [ ] **Step 1: `results/summary.md`.** Uma tabela por pergunta do topo, com veredito e fonte; o modo de PLE escolhido; o que não rodou; os desvios do plano.
- [ ] **Step 2: Launcher, se "Trocar o launcher" passar.**
  - Teste antes: `test_launcher_defaults_to_161`, com o `--print` do `serve-flashnext-splash.sh` mostrando `splash-v1.6.1` e, no modo `off`, `--ple-memory off`.
  - Trocar o `BIN` padrão, os flags e os comentários do script.
  - Não mudar o `serve-flashnext-daily-driver.sh`.
- [ ] **Step 3: Servidor do usuário.** Religar a porta 8585 com o launcher do Step 2, ou com a 1.5.0 se a regra falhar. Conferir `/health` e `/v1/models`.
- [ ] **Step 4: Documentos.**
  - Na nota de stack de 11/11, trocar o teste 1 por um link para o resultado.
  - Atualizar `reports/qwen38-flashnext-splash160.html` pelo `render_page.py` da splash16, com uma seção da 1.6.1, ou criar uma página nova se a seção não couber. O texto do report fica em inglês. Atualizar o card em `reports/index.html`.
  - Se o launcher mudar, atualizar a recomendação de `reports/qwen38-flashnext-concurrency.html` pelo `render_report.py` e a seção "November update" de `reports/qwen38-flashnext-m4max-guide.html`.
- [ ] **Step 5: Push e PR.** Base: a `main`, se o PR #84 já tiver merge; senão, a `bench/splash16-2026-11`. O corpo termina em `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Não fazer merge.

### Fora da fila, só com pedido do usuário

- **Terminal-Bench 2.1 do `k2h`.** Leva 12–24 h. Rodar se o usuário quiser trocar o driver diário para a 1.6.1, e comparar com os 57/89 do `k2a`.
- **Perfil `p` da Task 3 da splash16** (`--max-memory 96G` e as flags da #644) na 1.6.1.
