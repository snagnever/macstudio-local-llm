# Splash 1.6.0 contra 1.5.0 — runbook da campanha (2026-11-06)

> **Status (2026-11-06): proposto, aguarda aprovação do usuário.** Nada rodou. Branch: `bench/splash16-2026-11`, a partir da `main`.
>
> **Para agentes:** use superpowers:executing-plans. Execute as tasks em ordem. Marque cada step (`- [ ]` → `- [x]`). Pare só nas condições de "Execução".

**Objetivo:** decidir se o launcher do Splash no rig passa da 1.5.0 para a 1.6.0, e medir se a 1.6.0 acaba com a queda de decode da [#644](https://github.com/incoai/splash/issues/644) neste rig.

| # | pergunta | teste | task |
|---|---|---|---:|
| 1 | Os packs do rig carregam, e a troca de versão quebra algum cliente? | boot, API, proxy, restart do engine | 1 |
| 2 | A 1.6.0 mantém o `T_turno` e o cache de um stream? | ABBA de 32K a 256K; 512K e 1M | 2 |
| 3 | A queda de decode da #644 acontece aqui, e a 1.6.0 a remove? | carga de envelhecimento, 18 sessões | 3 |
| 4 | O scheduler novo muda o custo da segunda sessão? | sintética e Claude Code | 4 |
| 5 | O ledger de memória tira os stalls sob limite de memória? | churn com `--max-memory` | 5 |
| 6 | A qualidade continua igual? | bateria t1, longctx, tool calls | 6 |
| 7 | Uma carga de agente longa continua estável? | Claude Code por 4 h | 7 |

**Arquitetura:** a campanha reusa o `run-candidate.sh`, o `cache_probe.py`, o `run-parallel-probes.sh`, o `run-claude-pair.sh`, o `request_log.py`, o `run-battery.sh`, o `toolcall-probe.sh`, o `longctx_probe.py` e o `decide.py`. O código novo é um gerador de carga com amostras do `/status` e uma sonda do contrato da API. O benchmark `dev/benchmarks/serving` da 1.6.0 não entra: ele compila cada árvore do fonte, e a árvore da 1.5.0 não o tem. O `serving_load.py` segue os cenários e os gates publicados em [validate.md](https://github.com/incoai/splash/blob/1.6.0/docs/validate.md#serving-benchmark).

**Stack:** bash 3.2 e Python 3.9 stdlib no rig; pytest via `uv run --no-project --with pytest`.

**Spec:** este plano, o pedido do usuário de 06/11 e a [nota de stack](../../research/rig-stack-updates-20261103.md), adendo de 06/11, teste 9.

## O que a 1.6.0 muda para o rig

**Terceiro**, [notas da 1.6.0](https://github.com/incoai/splash/blob/1.6.0/docs/release-notes/1.6.0.md).

| mudança | hipótese | task |
|---|---|---:|
| KV em cache sai do residency set da fila da GPU (#692, fecha a #644) | decode não cai com o tempo; o autor diz que não reproduziu a queda | 3, 7 |
| Ledger único de memória; stall de 300–406 s vira 0.92 s num M5 Max de 36 GB | sem stall sob `--max-memory` | 5 |
| Expert store elástico; KV que espera a cópia para o SSD (#622) | 1M sem `capacity_exhausted` | 2 |
| Scheduler e TTFT por causa (`metrics.ttft_parts_ms`) | custo da segunda sessão muda, e passamos a ver a causa | 4 |
| GGUF reinstalado no primeiro start; tensores sem uso são recusados | os packs podem não subir | 0, 1 |
| `/status` schema 8; `stop_sequences` só array; 503 e 500 novos do engine | clientes e sondas podem quebrar | 1 |
| Launcher não usa mais o proxy para o servidor local | a API key não vaza | 1 |
| Corte de thinking fecha como o template | próximo turno reusa o KV além do corte | 1 |

**Sem relevância para o rig, fora do escopo:** kernels de M5 e M6, app para Mac, PDF (o rig sobe com `--language-only`), GGUF dividido na raiz, Flint e BF16 na tabela PLE. A quarentena de request também fica fora: um kill não conta para ela, e o rig não tem um request que cause falha de execução de forma repetível.

## Restrições globais

- **Rig:** Mac Studio M4 Max 128 GB. `ssh vitor@mac-studio`, ou `vitor@100.110.87.118`. Um modelo por vez. O MacBook não alcançou nenhum dos dois em 06/11.
- **Runtimes:** `~/.local/opt/qwen38/splash-v1.5.0/` e `splash-v1.6.0/`. Instalar a 1.6.0 com `SPLASH_TAG=1.6.0 install-runtime.sh splash`. Não usar `brew upgrade`. Não instalar outra versão durante a campanha. O mlx-serve não entra: ele tem campanha própria.
- **Pesos fixos:** `k2` = `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS` `0142554c963a8653912c0c8283f05f13f63653f3`. `k3` = `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF:IQ1_M` `bba88856f8c3c0c9e40e45f82d05e228b814ac43`.
- **Flags de base:** `--verify-rows auto --idle-release off --language-only --no-webui --offline`, porta 8585. Sem `--persistent-cache`.
- **Sampling:** `temperature 1.0`, `top_p 0.95`, `top_k 20`, `frequency_penalty 0`, `reasoning_effort xhigh`.
- **Gates de velocidade:** zero HTTP 4xx/5xx; needles corretas; hit ≥ 0.90 em `append` e `tool_turn`; swap Δ ≤ 0.5 GB. O livre mínimo é só registro, não gate: os braços `k2c1` e `rc*` da 1.5.0 já mostram 0.06 GB, com swap zero.
- **Protocolo térmico:** `idle-gate.sh` entre bandas; 120 s entre braços; ordem ABBA entre versões.
- **Claude Code:** fixar a 2.1.292 com `CLAUDE_BIN`, a mesma versão dos baselines. O 2.1.319 fica para o teste 4 da nota.
- **Idioma e commits:** prosa em pt-BR; código e git em inglês. Commits `bench(splash16): ...`, com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` no fim.
- **Saídas:** `results/` rastreado, com os JSONL por request e por questão. `logs/` ignorado.

## Regras de decisão

| veredito | regra |
|---|---|
| **Paridade de velocidade** | `T_turno(1.6.0) ≤ 1.03 × T_turno(1.5.0)` a 32K, 128K e 256K, com todos os gates |
| **Queda de decode** | sonda de 64 tokens no fim ÷ sonda antes da carga: ≥ 0.85 estável; 0.50–0.85 degradado; < 0.50 queda |
| **Fix confirmado** | 1.5.0 degradada ou em queda, e 1.6.0 estável, no mesmo perfil |
| **Fix sem prova** | 1.5.0 e 1.6.0 estáveis em todos os perfis. Registrar assim, sem escrever que a 1.6.0 corrigiu |
| **Regressão** | 1.6.0 degradada ou em queda onde a 1.5.0 fica estável |
| **Stall** | maior gap ≤ 10 s e p99 ≤ 5 s (G4 da 1.6.0), e todos os requests respondidos |
| **Concorrência** | `k2c2a` e `rc2`/`rc2s` no máximo 10% piores que o baseline da 1.5.0 |
| **Qualidade** | G1 do `summarize_ab.py` contra o `k2a` a 262144; longctx 8/8; tool calls 20/20 |
| **Trocar o launcher** | Tasks 1, 2, 4, 5 e 6 passam, e as Tasks 3 e 7 não mostram regressão |

O driver diário não muda nesta campanha. A troca do driver fica com o usuário.

## Review Focus

1. **`--offline` e GGUF reinstalado.** O primeiro start da 1.6.0 monta a instalação de novo, sem baixar pesos. A sequência 1.6.0 → 1.5.0 → 1.6.0 precisa subir sem rede, e o ABBA não pode pagar uma montagem a cada troca sem registro. Teste: smoke do Task 0, com o tempo até `/health` em cada start.
2. **Pack recusado pela triagem de GGUF.** A 1.6.0 recusa tensores que o modelo não aplica. Um `k2` recusado para a campanha. Um `k3` recusado sai dos perfis e fica registrado. Teste: smoke do Task 0.
3. **Sondas antigas com o `/status` 8.** O `run-parallel-probes.sh` e o `batch_smoke.py` leem `scheduler`, `active_requests` e `admission`. Teste: `test_status_reader_accepts_schema8`, Task 0, e 1 rep de `k2c2a` a 32K no smoke.
4. **Prompt fora do tamanho na carga.** Um prompt errado muda a taxa de ocupação do pool, e o teste perde o sentido. Teste: `test_aging_prompts_are_distinct_and_sized`, e a contagem real por `/v1/messages/count_tokens` fica em ±2% de 190960 no smoke.
5. **Request falho no meio da carga.** Um erro não pode parar as outras sessões nem sumir das contas. Teste: `test_failed_request_is_recorded_and_the_run_continues`.

## Execução

- **Filas:** cada fila roda no rig com `nohup bash logs/chain-tN.sh > logs/chain-tN.log 2>&1 &`. Ela para o driver diário no início e o religa no fim.
- **Código:** commit no MacBook e `git bundle` para o rig, como na [splash-longctx](../splash-longctx-2026-10/plan.md#execução-autônoma).
- **Falha:** um braço que falha não para a fila. Registrar o erro e seguir.
- **Pare e espere o usuário se:**
  1. o `k2` não subir na 1.6.0;
  2. disco livre < 150 GB, ou swap Δ > 2 GB, ou kernel panic;
  3. o driver diário não voltar no fim de uma fila;
  4. o rig seguir inacessível por SSH no Task 0.
- **Publicação:** não comentar nem reabrir issue no GitHub sem pedido do usuário.

## Tempo estimado no rig

| task | conteúdo | horas |
|---|---|---:|
| 0 | instalação e smoke | 1 |
| 1 | contrato | 1 |
| 2 | um stream | 9 |
| 3 | envelhecimento | 7; mais 3.5 se o Q2_0 entrar |
| 4 | concorrência | 4 |
| 5 | churn | 1 |
| 6 | qualidade | 8 |
| 7 | 4 h de agente, duas versões | 8 |
|  | **total** | **~39, ou ~43** |

As horas da Task 3 vêm de 284 s de prefill frio por sessão de 190960 tokens, calculados dos 351 s a 256K. As outras são estimativas a partir das campanhas anteriores.

## Mapa de arquivos

| arquivo | ação | responsabilidade |
|---|---|---|
| `bench/splash16-2026-11/scripts/run-arm.sh`, `run-seq.sh` | Create | cópias dos da `claude-code-concurrency`, com `HERE` aqui |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify | `SPLASH_160`, braços `k2f k2g k3g`, overrides |
| `bench/splash16-2026-11/scripts/serving_load.py` | Create | cenários `aging` e `churn`, sonda curta, amostras do `/status` |
| `bench/splash16-2026-11/scripts/api_contract.py` | Create | checks C1 a C7 contra um servidor no ar |
| `bench/splash16-2026-11/scripts/proxy_capture.py` | Create | proxy falso que registra requests e headers de chave |
| `bench/splash16-2026-11/scripts/engine_restart.py` | Create | mata o engine durante um stream e registra a recuperação |
| `bench/splash16-2026-11/scripts/agent_soak.sh` | Create | pares c+d de Claude Code até o tempo pedido, com sonda curta entre pares |
| `bench/splash16-2026-11/scripts/summarize_load.py` | Create | tabela por rodada, veredito de queda e de stall |
| `bench/splash16-2026-11/tests/` | Create | testes de todos os scripts novos e dos braços |
| `tools/scripts/serve-flashnext-splash.sh` | Modify (Task 8) | versão do launcher, só se a regra passar |

---

### Task 0: Pré-voo, braços, ferramentas e smoke

**Interfaces produzidas:**

- Braços `k2f` e `k2g`: o `k2a` na 1.5.0 e na 1.6.0. `k3g`: o `k3a` na 1.6.0. O `k3f` já existe.
- `FLASHNEXT_SPLASH_XARGS`: flags somadas às de base em `k2f`, `k2g`, `k3f` e `k3g`.
- `FLASHNEXT_SPLASH_TAG` (`1.5.0` por padrão, ou `1.6.0`): versão dos braços `k2c*` e `rc*`.
- `serving_load.py aging --base-url U --model M --status-url S --out P [--rounds 6] [--sessions 3] [--prompt-tokens 190960] [--max-tokens 300] [--seed 0]`
- `serving_load.py churn --base-url U --model M --status-url S --out P [--minutes 15] [--clients 3] [--base-tokens 16000] [--step-tokens 2000] [--max-tokens 1500] [--order 2,0,1] [--seed 0]`
- `serving_load.py probe --base-url U --model M --out P --label L [--reps 3]`: prompt de 64 tokens e `max_tokens` 512.
- Registros JSONL de `serving_load.py`:
  - `{"kind":"request","round","session","prompt_tokens","cached_tokens","ttft_s","decode_tok_s","max_gap_s","gaps_s","status","error"}`, com `round` e `session` valendo também no churn (rodada e cliente);
  - `{"kind":"probe","label","ttft_s","decode_tok_s"}`;
  - `{"kind":"status","t","schema_version","kv","state","disk","memory_governor","metrics"}`, com o `/status` a cada 5 s. O `memory_governor` e o `metrics` ficam `null` onde o campo não existe.
- `decode_tok_s` = `usage.completion_tokens / (t_último_chunk − t_primeiro_chunk)`. Com DFlash, um chunk pode trazer mais de um token, e por isso a conta não usa o número de chunks.
- `summarize_load.py <jsonl> [...]` grava uma tabela Markdown por rodada e imprime `verdict=estavel|degradado|queda` e `stall=pass|fail`.

**Steps:**

- [ ] **Step 1: Acesso e estado do rig.** Confirmar `ssh -o BatchMode=yes vitor@mac-studio hostname`, ou pelo IP. Gravar em `results/etapa0-preflight.md`: macOS, disco, versão do Claude Code, binários em `~/.local/opt/qwen38`, packs no cache do HF e `env | grep -i proxy`.
- [ ] **Step 2: Conferir o risco do proxy.** Se o rig tem `http_proxy` no ambiente e usou `--api-key` com a 1.5.0, avisar o usuário para trocar a chave.
- [ ] **Step 3: Instalar.** `SPLASH_TAG=1.6.0 bash bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh splash`. Conferir o SHA-256 com `SHA256SUMS` da release. Gravar `splash --version` e o help em `results/splash-160-help.txt`. Comparar o help com o `splash-150-help.txt` e registrar os flags removidos. Instalar o Claude Code 2.1.292 num prefixo próprio se o binário do rig mudou.
- [ ] **Step 4: Testes que falham** em `tests/test_arms.py` e `tests/test_tools.py`:

  ```python
  def test_k2g_runs_splash_160():            # --print: splash-v1.6.0/bin/splash, ukisai ...:IQ4_XS, --revision 0142554..., --verify-rows auto
  def test_k2f_runs_splash_150():            # igual, com splash-v1.5.0
  def test_k3g_runs_ista_on_160():           # splash-v1.6.0, ISTA ...:IQ1_M, --revision bba8885...
  def test_xargs_reach_the_server():         # FLASHNEXT_SPLASH_XARGS="--max-memory 96G" aparece no comando de k2g
  def test_rc_and_k2c_default_stays_150():   # sem override: rc2 e k2c2a usam splash-v1.5.0
  def test_tag_override_moves_rc_and_k2c():  # FLASHNEXT_SPLASH_TAG=1.6.0: os dois usam splash-v1.6.0 e EXPECTED_VERSION=1.6.0
  def test_aging_prompts_are_distinct_and_sized():  # 18 prompts, nenhum prefixo comum > 1 KB, estimativa 190960 ±2%
  def test_aging_is_deterministic():         # mesmo seed: mesmos prompts
  def test_failed_request_is_recorded_and_the_run_continues():  # servidor falso devolve 500 num request: registro com status 500, outros 17 rodam
  def test_decode_uses_completion_tokens():  # 300 tokens em 30 chunks ao longo de 3 s: decode_tok_s == 100
  def test_status_reader_accepts_schema8():  # fixture sem contended_commands e resident_kv_bytes: registro válido; em schema 6, memory_governor None
  def test_verdict_thresholds():             # razão 0.85 → estavel; 0.84 → degradado; 0.49 → queda
  def test_stall_gate():                     # gap 10.1 s → fail; p99 5.1 s → fail; request sem resposta → fail
  def test_proxy_capture_flags_key_headers():  # Authorization e x-api-key marcam has_key true; o valor da chave não vai para o arquivo
  ```

- [ ] **Step 5: Rodar e ver que falham.** `uv run --no-project --with pytest python -m pytest bench/splash16-2026-11/tests -q`.
- [ ] **Step 6: Implementar.** O haystack vem do `build_case` do `longctx_probe.py`, com um seed por sessão. Cada request termina com uma pergunta curta.
- [ ] **Step 7: Rodar e ver que passam.** As suítes de `bench/splash-concurrency-2026-10/tests` e `bench/claude-code-concurrency-2026-11/tests` também passam.
- [ ] **Step 8: Smoke no rig**, com o tempo até `/health` de cada start em `results/etapa0-smoke.md`:
  1. `k2g` a 32768, só o cold. Primeiro start: registrar a montagem da instalação.
  2. `k2f` a 32768, só o cold.
  3. `k2g` a 32768, só o cold.
  4. `k3g` a 32768, só o cold.
  5. `FLASHNEXT_SPLASH_TAG=1.6.0 k2c2a` a 32768, 1 rep. O status precisa mostrar dois requests em decode.
  6. `serving_load.py aging --rounds 1 --sessions 1` no `k2g` a 262144. `count_tokens` fica em ±2%.
- [ ] **Step 9: Commit.** `bench(splash16): Task 0 — arms, load generator, API probes`.

### Task 1: Contrato da atualização

**Files:** `scripts/api_contract.py`, `scripts/proxy_capture.py`, `scripts/engine_restart.py`, `results/etapa1-contrato.md`.

Rodar `api_contract.py --base-url U --model M --out results/contract-<ver>.jsonl` no `k2f` e no `k2g` a 32768. Cada linha traz `{"check","expected","observed","pass"}`.

| check | request | 1.5.0 | 1.6.0 |
|---|---|---|---:|
| C1 | Messages com `stop_sequences` string | 200 | 400 que cita `stop_sequences` |
| C2 | Messages com `stop_sequences` array | 200 | 200 |
| C3 | `stop` com 16385 caracteres | registrar | 400 |
| C4 | `POST /v1/chat/completions/count_tokens` contra `usage.prompt_tokens` do mesmo pedido | 404 | `input_tokens` igual |
| C5 | Request encerrado por stop, delta no `/status` | `requests.cancelled` +1 | `requests.completed` +1 |
| C6 | `/status` | `schema_version` 6 | 8; `memory_governor`, `metrics.ttft_parts_ms` e `metrics.decode_gap_causes` presentes; os dois campos removidos ausentes |
| C7 | `thinking_token_budget` 1024, e depois o turno seguinte com a resposta no histórico | registrar `cached_tokens` | `cached_tokens` passa do fim do corte, salvo corte após espaço ou quebra de linha |

- [ ] **Step 1: Testes do `api_contract.py`** contra um servidor falso: `test_contract_marks_unexpected_status_as_fail`, `test_contract_writes_one_line_per_check`. Ver que falham, implementar e ver que passam.
- [ ] **Step 2: Rodar C1 a C7** nas duas versões. Uma linha `pass: false` na coluna da 1.6.0 vira item em `etapa1-contrato.md`.
- [ ] **Step 3: Proxy.**
  - Subir `proxy_capture.py --port 9099 --out results/proxy-<ver>.jsonl`.
  - Subir o braço com `FLASHNEXT_SPLASH_XARGS="--api-key <chave de teste gerada na hora>"`.
  - Pôr um `claude` falso no início do `PATH`. Ele grava `NO_PROXY` e sai.
  - Rodar `http_proxy=http://127.0.0.1:9099 splash claude`, com os argumentos de `splash claude --help`.
  - Esperado na 1.5.0: pelo menos um hit com `has_key` true. Esse é o controle positivo.
  - Esperado na 1.6.0: zero hits, e `NO_PROXY` com os hosts de loopback.
  - Não gravar o valor da chave em nenhum arquivo.
- [ ] **Step 4: Restart do engine, só na 1.6.0.** `engine_restart.py` inicia um stream, envia SIGKILL ao processo `serve-native` e repete um request a cada 1 s. Esperado:
  - o stream termina com erro limpo;
  - os requests recebem 503 `engine_recovering` com `Retry-After`;
  - o primeiro 200 vem antes de 2 × o tempo de boot;
  - `capabilities.max_context_tokens` não muda.
- [ ] **Step 5: Gravar `results/etapa1-contrato.md` e commitar.**

### Task 2: Velocidade e cache de um stream

- [ ] **Step 1: Fila ABBA de `cache_probe`, 3 reps** por braço e banda. Cada posição é um boot com 1 rep:

  | banda | ordem |
  |---|---|
  | 32768 | `k2f`, `k2g`, `k2g`, `k2f`, `k2f`, `k2g` |
  | 131072 | `k2g`, `k2f`, `k2f`, `k2g`, `k2g`, `k2f` |
  | 262144 | `k2f`, `k2g`, `k2g`, `k2f`, `k2f`, `k2g` |

- [ ] **Step 2: Bandas longas.** `k2g` a 524288 com 3 reps, e `k2f` a 524288 com 1 rep. `k2g` a 1000000 com 1 rep; a referência é o `k2a` da 1.4.0, com 9.3–9.4 s. Rodar `k2f` a 1000000 só se o `k2g` ficar fora de ±5% dela.
- [ ] **Step 3: Resumo.** `decide.py --base k2f --cand k2g --ctx 32768,131072,262144 --mode le --threshold 1.03 --out-md results/etapa2-um-stream.md`. Acrescentar: cold TTFT, hit, `middle_mutation`, decode, wired peak, livre mínimo e swap Δ. Registrar `metrics.ttft_parts_ms` de um request de cada banda da 1.6.0.
- [ ] **Step 4: 1M.** Verificar zero `capacity_exhausted` e registrar o aumento de KV no SSD.
- [ ] **Step 5: Commit.**

### Task 3: Envelhecimento (#644)

> **Pulada pelo usuário em 07/11.** O perfil `a` e o `k3g` do perfil `p` rodaram completos. O `k3f` parou na rodada 5. Os Steps 3 e 4 não rodaram. Para a regra "Trocar o launcher", a Task 3 conta como sem regressão observada. Resultado: [results/etapa3-envelhecimento.md](results/etapa3-envelhecimento.md).

A carga repete a do comentário de 31/10 da #644: 6 rodadas de 3 sessões novas e simultâneas de ~190960 tokens, `max_tokens` 300, contexto 262144. O pool enche com prefixos de sessões mortas, a ~2.5 GB por sessão (cálculo do autor). Um boot por run.

| perfil | braços | flags somadas | por quê |
|---|---|---|---|
| `a` padrão do rig | `k2f`, `k2g` | nenhuma | é o que o launcher roda |
| `p` flags da #644 | `k3f`, `k3g` | `--max-memory 96G --max-cache-disk 64G --state-format bf16 --ple-memory 8G` | pack mais próximo do reportado, com limite que deixa o KV chegar ao teto |
| `q` condicional | `k4f`, `k4g` | as do `p` | pack exato da #644: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF:Q2_0`, ~66 GB |

Ordem: `k2f`, `k2g`, `k3g`, `k3f`. Cada run usa `--exec` e tem esta sequência:

1. `probe --label pre`, depois de um aquecimento de 1 request;
2. `aging`, com `probe --label round<N>` depois de cada rodada;
3. `probe --label fim`;
4. 10 min ociosos e `probe --label ocioso`.

- [ ] **Step 1: Fila dos perfis `a` e `p`.** Registrar o livre mínimo e os erros. Com as flags do `p`, `--max-memory 96G` e o `k3g` precisam subir; uma recusa vira registro, com a mensagem.
- [ ] **Step 2: Resumo.** `summarize_load.py` grava em `results/etapa3-envelhecimento.md`, por rodada:
  - pool de KV, `pages_cache` e `pages_free`;
  - `denied_reservations`, `pages_moved` e bytes de state e de disco;
  - mediana e última lane de decode;
  - sonda curta e TTFT, com a parte de `metrics.ttft_parts_ms` na 1.6.0.
- [ ] **Step 3: Escada.** Se `k2f` e `k3f` ficarem estáveis, baixar o `Q2_0` na revisão `ed59f92` e rodar o perfil `q`. Conferir antes o disco. Os braços `k4f` e `k4g` e o teste deles estão em [flashnext-weights-2026-11](../flashnext-weights-2026-11/tests/test_arms.py).
- [ ] **Step 4: Repetição.** Repetir o par `f`/`g` do perfil com a maior diferença, em ordem invertida. Um resultado sem repetição não vira veredito.
- [ ] **Step 5: Veredito por perfil,** com as regras do início. Em caso de regressão, escrever o rascunho do relato em `results/etapa3-relato-upstream.md` e não publicar.
- [ ] **Step 6: Commit.**

### Task 4: Concorrência e Claude Code

Tudo com `FLASHNEXT_SPLASH_TAG=1.6.0`, Claude Code 2.1.292 e tag `g1`. Os baselines são os da 1.5.0: [splash-concurrency](../splash-concurrency-2026-10/results/summary.md) e [claude-code-concurrency](../claude-code-concurrency-2026-11/results/summary.md).

| braço | contexto | reps | baseline da 1.5.0 |
|---|---|---:|---|
| `k2c1` | 32768, 131072 | 3 | 5.8 / 6.1 s |
| `k2c2a` | 32768, 131072 | 3 | pior stream 2.43× / 2.52× |
| `k2c2LL` | 262144 | 3 | 1.89×, stall no cold |
| `rc1` c, d | 131072 | 2 cada | wall e TTFT quente de `claude-summary-splash.json` |
| `rc2` c+d | 131072 | 3 | 1.4 / 4.8 s; 89.2 tok/s (p50) e 39.0 tok/s (mín) |
| `rc2s` c+d | 131072 | 3 | 2.5 / 8.4 s; 82.8 tok/s (p50) e 20.1 tok/s (mín) |

- [ ] **Step 1: Fila dos braços acima.**
- [ ] **Step 2: Controle.** Se um braço ficar > 10% pior, rodar o mesmo braço na 1.5.0 no mesmo dia, antes de chamar de regressão: 1 rep em `k2c*`, 2 em `rc*`.
- [ ] **Step 3: Resumo.** `summarize_parallel.py` e `summarize_claude.py`. Gravar `results/etapa4-concorrencia.md`, com `metrics.ttft_parts_ms` e `metrics.decode_gap_causes` do fim de cada braço da 1.6.0: eles mostram quanto do TTFT é prefill de outro request.
- [ ] **Step 4: Commit.**

### Task 5: Pressão de memória

Churn de 15 min, sob `--max-memory 64G`, contexto 131072, na ordem `k2f`, `k2g`, `k2g`, `k2f`. Esse limite força os experts a usarem o store em stream. Se o boot recusar 64G, subir de 8 em 8 GB até 88G, em todos os braços, e registrar.

- [ ] **Step 1: Fila.** Rodar `serving_load.py churn` nas quatro posições.
- [ ] **Step 2: Resumo.** `summarize_load.py` aplica o gate de stall. Gravar `results/etapa5-pressao.md`: maior gap, p99, requests sem resposta, `memory_governor.accounts` e `metrics.decode_gap_causes` na 1.6.0, tamanho do store (`streamed_experts`) e throughput de prefill e de decode.
- [ ] **Step 3: Commit.**

### Task 6: Qualidade

Rodar o `k2g` a 262144.

- [ ] **Step 1: Bateria.** `run-battery.sh k2g v16 --suites "humaneval gpqa livecodebench if jdhodges veerman" --ctx 262144`. Commitar os JSONL por questão.
- [ ] **Step 2: Longctx.** `longctx_probe.py --context 262144` e `--context 131072`.
- [ ] **Step 3: Tool calls.** `toolcall-probe.sh k2g --sessions 20 --suffix v16 --max-tokens 2048`, com `TOOLCALL_CAMPAIGN_DIR` nesta campanha.
- [ ] **Step 4: Resumo.** `summarize_ab.py`, G1 e G2, contra o `k2a` a 262144 da [splash-longctx](../splash-longctx-2026-10/results/summary.md) (158 · 159, 41, 47, 19, 37, 10). A referência é da 1.4.0, porque a 1.5.0 não tem bateria deste pack. Se G1 falhar, repetir a suíte uma vez nas duas versões, antes do veredito. Gravar `results/etapa6-qualidade.md`.
- [ ] **Step 5: Commit.**

### Task 7: Carga de agente de 4 h

`agent_soak.sh --hours 4 --tag <ver>` repete pares c+d do `run-claude-pair.sh` no mesmo servidor, com `--proxy 8686`. Entre os pares, ele roda `serving_load.py probe --label pair<N>`. Cada par deixa ~1.5 GB de prefixos (60K tokens × 2 × 12.78 KiB, a conta da #644), então 4 h devem encher o pool. Se o pool não chegar ao teto, registrar que o teste não exercitou a queda. Cada run usa `run-arm.sh <braço> 131072 --exec`, com um boot só, numa fila noturna: primeiro o `k2g`, depois o `k2f`.

- [ ] **Step 1: Teste do script.** `test_soak_stops_after_hours_and_probes_between_pairs`, com `CLAUDE_BIN` falso e `--hours 0.001`. Ver que falha, implementar e ver que passa.
- [ ] **Step 2: Fila** com `k2g` e `k2f`. Um `task_done` falso não para a fila.
- [ ] **Step 3: Resumo.** `results/etapa7-agente-4h.md`, por hora: tok/s p50, TTFT quente p50 e p90, sonda curta, `pages_cache`, `denied_reservations`, requests, erros e `task_done`. Veredito com as regras de queda.
- [ ] **Step 4: Commit.**

### Task 8: Decisão, launcher e fechamento

> **Ordem (07/11):** o usuário adicionou a [flashnext-weights-2026-11](../flashnext-weights-2026-11/plan.md) à fila, com a ordem definida lá. Os Steps 1 a 3 rodam ao fim da Task 7, e a decisão do launcher define a release dos pesos. O Step 4, o reinício do servidor do usuário e o Step 5 rodam ao fim da Task W3.

- [ ] **Step 1: `results/summary.md`.** Uma tabela por pergunta do topo, com veredito e fonte; o que não rodou; os desvios do plano.
- [ ] **Step 2: Launcher, se "Trocar o launcher" passar.**
  - Teste antes: `test_launcher_defaults_to_160`, com o `--print` do `serve-flashnext-splash.sh` mostrando `splash-v1.6.0`.
  - Trocar o `BIN` padrão e os comentários do script.
  - Não mudar o `serve-flashnext-daily-driver.sh`.
- [ ] **Step 3: Documentos.**
  - Atualizar `docs/models/qwen3.8-flash-next.md`, seção de concorrência, se a Task 4 mudar os números.
  - Na nota de stack, trocar o teste 9 por um link para o resultado.
  - Se a Task 4 mudar uma tabela pública, atualizar `reports/qwen38-flashnext-concurrency.html` pelo `render_report.py`. O texto do report fica em inglês.
- [ ] **Step 4: Conferir o driver diário.** Ele responde `/health` no fim.
- [ ] **Step 5: Push e PR** para a `main`, com o corpo terminando em `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Não fazer merge.

### Fora da fila, só com pedido do usuário

**Terminal-Bench 2.1 do `k2g`.** Leva 12–24 h. A 1.6.0 muda pouco os kernels, e a bateria da Task 6 cobre a regressão de qualidade. Rodar se o usuário quiser trocar o driver diário para a 1.6.0, com o `run-tbench-remote.sh` da [splash-longctx](../splash-longctx-2026-10/plan.md), e comparar com os 57/89 do `k2a` e os 58/89 do `w1z`.
