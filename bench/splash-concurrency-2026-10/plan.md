# Splash concurrency 2026-10 — campaign runbook

> **Status (2026-10-29): aprovado e em execução autônoma.** O usuário aprovou o plano com os braços `w1zc*` e pediu execução autônoma. Branch: `bench/splash-concurrency-2026-10`, a partir da `main`.
>
> **Para agentes:** use superpowers:executing-plans. Execute as tasks em ordem, sem pedir confirmação entre elas. Marque cada step (`- [ ]` → `- [x]`). Pare só se o Task 0 Step 4 mostrar que o Splash não faz batch, ou se o rig cair.

**Objetivo:** repetir no Splash a bateria de concorrência que o [flashnext-concurrency-2026-10](../flashnext-concurrency-2026-10/plan.md) rodou no mlx-serve 26.10.1, e responder:

1. Quantas sessões (N = 2, 3, 4) o Splash serve ao mesmo tempo com o Swift 1.5, dentro dos mesmos gates?
2. O Splash ganha vazão total com N > 1? No mlx-serve, cada stream ficou ~2× mais lento e a vazão total não cresceu.
3. Duas sessões de Claude Code no Splash terminam antes de duas sessões em sequência?
4. O `--decode-share` do Splash tira o stall das chamadas curtas durante um prefill longo, que o `--prefill-decode-share` do mlx-serve não tirou?

O resultado entra no relatório público [reports/qwen38-flashnext-concurrency.html](../../reports/qwen38-flashnext-concurrency.html) como uma segunda série (Splash) ao lado do mlx-serve.

**Arquitetura:** reuso quase total do harness anterior. O `run-parallel-probes.sh`, o `aux_load.py`, o `summarize_parallel.py`, o `run-claude-pair.sh` e o `render_report.py` ficam em `bench/flashnext-concurrency-2026-10/scripts/` e recebem só parâmetros novos. Os braços novos (`k2c*`) entram no `run-candidate.sh`, ao lado do bloco `w1c*`. O Splash não tem `--max-concurrent`: ele faz batch de todos os requests admitidos (`--queue-size`, default 32). Por isso o `N` de cada braço é só o número de streams do cliente.

## O que mudou desde a campanha anterior

| item | campanha mlx-serve (18/10) | esta campanha |
|---|---|---|
| runtime | mlx-serve 26.10.1 | Splash 1.5.0 (saiu em 28/10) |
| pesos | Swift 1.5 MLX 4.7bpw `13839b7` | Swift 1.5 GGUF `IQ4_XS` `0142554` (o `k2a` da [splash-longctx](../splash-longctx-2026-10/plan.md)) |
| controle de concorrência | `--max-concurrent N` | nenhum no servidor; `--queue-size` limita a fila; `--decode-share` (default 0.5) |
| solo de referência | `w1` 7.9 / 8.6 / 11.1 s (32K / 128K / 256K) | `k2c1` medido no Task 2 com a 1.5.0; o `k2a` da 1.4.0 dá 6.0 / 6.3 / 6.6 s ([etapa1-native](../splash-longctx-2026-10/results/etapa1-native.md)) |

**Novidades do Splash que importam para o teste:**

- **1.4.1 (26/10):** [#579](https://github.com/incoai/splash/pull/579) corrige requests em fila que travavam sob pressão de memória enquanto outro request cresce o KV. É o cenário de dois streams a 128K e 256K.
- **1.5.0 (28/10):**
  - kernels quantizados mais rápidos no M3, M4 e M5 ([#600](https://github.com/incoai/splash/pull/600), [#602](https://github.com/incoai/splash/pull/602)). O solo da 1.4.0 deixa de valer; o Task 2 mede o solo de novo;
  - Messages e Responses devolvem `timings` (prompt, decode, cached tokens, draft). O probe pode gravar esses campos;
  - `/v1/models` informa os reasoning efforts aceitos (ajuda no Review Focus 5);
  - abreviações de flags (`--max-mem`) deixam de valer: conferir o launcher;
  - caches persistentes de MoE recomeçam (não usamos `--persistent-cache`);
  - aviso: no M5 e M6 a saída depende dos requests concorrentes. O M4 Max não está na lista, mas o docs/internals diz que MoE GGUF não é invariante ao batch em nenhum chip.
- **Docs do Splash:** a [performance.md](https://github.com/incoai/splash/blob/main/docs/performance.md) mostra 2.0× a 3.9× de vazão com 4 prompts curtos concorrentes e uma vantagem que cresce com a carga (3.8× a quatro requests de 32K no 35B). Esses números são de outros modelos e outros Macs. Esta campanha mede o Swift 1.5 no M4 Max.

## Restrições globais

As restrições de [flashnext-concurrency-2026-10](../flashnext-concurrency-2026-10/plan.md#global-constraints) e as emendas dela valem aqui (livre mínimo só para leitura, overlap pela janela de decode, trava > 60 s fora de `cold` e `middle_mutation`, `--prompt-salt` nos streams 3 e 4, barreira de início). As diferenças:

- **Runtime fixo:** Splash 1.5.0 em `~/.local/opt/qwen38/splash-v1.5.0/bin/splash`. Não trocar de versão no meio da campanha. Se sair uma 1.5.x, ela vira emenda, não troca silenciosa.
- **Pesos fixos:** `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS` `0142554c963a8653912c0c8283f05f13f63653f3`, draft `incoai/Qwen3.8-Flash-Next-DFlash2` `a22a174`, `--offline` depois do primeiro boot da 1.5.0.
- **Flags base de todo braço `k2c*`:** as do `k2a` (`--verify-rows auto --idle-release off --language-only --no-webui --offline`), porta 8585, `--host 0.0.0.0`. Variantes mudam uma flag por vez.
- **Referência solo:** o `k2c1` de cada banda (3 reps) no Task 2. A `razão` de cada stream divide pelo `k2c1` da mesma banda, não pelo `w1`. A comparação entre runtimes usa o `T_turno` absoluto.
- **Gates:** os mesmos da campanha anterior. Lentidão: razão ≤ 1.5 passa, 1.5–2.0 passa com aviso, > 2.0 reprova. Erros: zero HTTP 4xx/5xx (inclui 503 de fila cheia), nenhuma trava > 60 s, swap Δ ≤ 0.5 GB, hit ≥ 0.95 em `append` e `tool_turn`, needles corretas.
- **Métrica nova, só de leitura:** `vazão total = soma do decode dos streams nas janelas de overlap ÷ decode do k2c1`. O `summarize_parallel.py` imprime a coluna. Ela responde à pergunta 2 e não é gate.
- **Daily driver:** fica parado durante cada fila e volta no fim (`tools/scripts/serve-flashnext-daily-driver.sh`). O rig serve um modelo por vez.
- **Prioridade do rig:** a sessão "Atualizações de stack preferidas" pausa o trabalho no rig enquanto esta campanha roda (pedido do usuário, 29/10). Avisar aquela sessão quando o rig ficar livre.
- **Commits:** `bench(splash-concurrency): ...`, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push e PR só no Task 6.
- **Testes:** rodar cada pasta em separado (as duas têm um `conftest.py` próprio): `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests -q`, o mesmo para `bench/splash-concurrency-2026-10/tests` e `bench/qwen3.8-prefix-cache/tests/test_cache_probe.py`.
- **Tag:** `e1` em todas as bandas e em todos os braços, também a 256K. O `--ref-arm` acha o solo pela mesma tag.
- **Checkout no rig:** um worktree próprio, `~/LocalProjects/macstudio-local-llm-splashconc`, na branch desta campanha. O checkout principal do rig fica na branch da outra sessão, com o waiter `wait-t5r.sh` dela.

## Review Focus

1. **O Splash serializa em vez de fazer batch para o Flash-Next.** O batch é documentado para o 27B e o 35B; o Flash-Next é block-sparse e usa SSD para KV. Checado no Task 0 Step 4 (`/status.admission` durante dois `cold` ao mesmo tempo) e pelo gate de overlap do `summarize_parallel.py` (`VERDICT: fail (no overlap)`).
2. **Admissão espera por memória.** O Splash segura requests numa fila de memória (`held_behind_refusal`) em vez de recusar com HTTP. Isso não gera erro, mas gera TTFT longo. Checado: o `run-parallel-probes.sh` grava `/status` a cada 10 s num `*-status.jsonl`; o resumo conta as amostras com espera por memória.
3. **Wired peak acima de 116 GB a 256K com dois streams.** O `k2a` sozinho a 256K chega a 116.4 GB de wired e 10.1 GB de folga. Dois streams de 256K podem não caber. A variante `k2c2Ls` (`--state-format bf16`) roda se o `k2c2LL` reprovar por memória.
4. **Saída muda com o batch.** Com `--verify-rows auto` e MoE GGUF, o batch muda os tokens. Isso não é bug, mas pode mudar needles. Se as needles caírem só nos braços com N ≥ 2, o braço `k2c2v` (`--verify-rows all`) separa o efeito do batch do efeito do verify budget.
5. **Claude Code manda `reasoning_effort` que o template recusa.** A 1.5.0 lista os efforts aceitos em `/v1/models`. Checado no Task 4 Step 1 antes do par.

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `bench/splash-concurrency-2026-10/plan.md` | Create | este runbook |
| `bench/splash-concurrency-2026-10/scripts/run-arm.sh` | Create | cópia do `run-arm.sh` anterior com `FLASHNEXT_RESULTS_DIR`/`FLASHNEXT_LOGS_DIR` desta campanha |
| `bench/splash-concurrency-2026-10/tests/test_splash_arms.py` | Create | `--print` dos braços `k2c*`: flags certas, porta 8585, nenhuma `--max-concurrent` |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify | bloco `k2c*` (abaixo); caminho do Splash 1.5.0 |
| `bench/flashnext-concurrency-2026-10/scripts/run-parallel-probes.sh` | Modify | `--runtime`, `--serialize` (flock no cliente) e `--status-url URL` (grava `/status` a cada 10 s) |
| `bench/flashnext-concurrency-2026-10/scripts/summarize_parallel.py` | Modify | `--ref-arm ARM` (solo medido no lugar das constantes do `w1`); coluna `vazão total`; contagem de espera por memória |
| `bench/qwen3.8-prefix-cache/scripts/cache_probe.py`, `bench/flashnext-concurrency-2026-10/scripts/aux_load.py` | Modify | `--request-lock PATH`: flock exclusivo em volta de cada request (fila no cliente do `k2c1x2`) |
| `bench/flashnext-concurrency-2026-10/scripts/run-claude-pair.sh` | Modify | `--base-url` e `--model` parametrizados (hoje apontam para a 11234) |
| `bench/flashnext-concurrency-2026-10/scripts/render_report.py` | Modify | segunda série (Splash) em cada gráfico e tabela; seção "mlx-serve × Splash" |
| `bench/flashnext-concurrency-2026-10/tests/*.py` | Modify | testes das flags novas |
| `reports/qwen38-flashnext-concurrency.html` | Regenerate | página pública |
| `reports/index.html` | Modify | atualizar o card do relatório (data e descrição), sem card novo |
| `tools/scripts/serve-flashnext-splash.sh` | Modify (Task 5, condicional) | caminho da 1.5.0; `SPLASH_DECODE_SHARE` opcional |
| `docs/models/qwen3.8-flash-next.md` | Modify (Task 5) | tabela de concorrência com as duas colunas de runtime |

## Braços

| braço | streams | gerador auxiliar | contextos | flag além da base | por quê |
|---|---:|---|---|---|---|
| `k2c1` | 1 | não | 32K, 128K, 256K | — | solo de referência na 1.5.0 |
| `k2c1a` | 1 | sim | 32K, 128K | — | custo das auxiliares com uma sessão |
| `k2c2` | 2 | não | 32K, 128K | — | batch puro |
| `k2c2a` | 2 | sim | 32K, 128K | — | cenário do usuário: duas sessões de agente |
| `k2c1x2` | 2 | sim | 32K, 128K | lock no cliente (`--serialize`) | controle "fila contra batch"; o Splash não tem chave para desligar o batch, então o `run-parallel-probes.sh` serializa os streams com um lock de arquivo |
| `k2c3a` | 3 | sim | 32K, 128K | — | N = 3 |
| `k2c4` | 4 | não | 32K; 128K se `k2c3a` passar | — | N = 4 |
| `k2c4a` | 4 | sim | 32K; 128K se `k2c3a` passar | — | N = 4 com auxiliares |
| `k2c2L` | 2 (256K + 32K) | sim | 262144,32768 | `--max-context 262144` | assimétrico, como o `w1c2L` |
| `k2c2LL` | 2 (256K + 256K) | sim | 262144 | `--max-context 262144` | duas sessões longas |
| `k2c2Ls` | 2 (256K + 256K) | sim | 262144 | + `--state-format bf16` | só se `k2c2LL` reprovar por memória |
| `k2c2ad1` | 2 | sim | 128K | `--decode-share 1.0` | stall das auxiliares (pergunta 4) |
| `k2c2ad0` | 2 | sim | 128K | `--decode-share 0` | idem, extremo oposto |
| `k2c2v` | 2 | sim | 128K | `--verify-rows all` | só se as needles caírem com N ≥ 2 (Review Focus 4) |
| `kcc1` | 1 Claude Code | nativo | — | — | controle da Etapa 2 |
| `kcc2` | 2 Claude Code | nativo | — | — | Etapa 2 |
| `w1zc1` | 1 | não | 32K, 128K | mlx-serve 26.10.3, flags do driver diário | solo do mlx-serve no build do driver de hoje |
| `w1zc2a` | 2 | sim | 32K, 128K | mlx-serve 26.10.3, `--max-concurrent 2` | duas sessões no mesmo build |

**Pesos e runtimes:** os `k2c*` e os `kcc*` usam o Swift 1.5 GGUF `IQ4_XS` `0142554` no Splash 1.5.0. Os `w1zc*` usam o Swift 1.5 MLX 4.7bpw `13839b7` no mlx-serve 26.10.3. A campanha anterior rodou na 26.10.1; os `w1zc*` (pedido do usuário, 29/10) fazem a tabela "mlx-serve × Splash" comparar o build do driver de hoje. A razão do `w1zc2a` usa o `w1zc1` da banda (`--ref-arm w1zc1`).

## Modelo de resultados

A tabela do `summarize_parallel.py` é a mesma da campanha anterior, com duas colunas novas no fim: `vazão total` e `espera mem`. `razão ÷ solo` usa o `k2c1` da banda. Cada `results/etapa<N>-*.md` começa com título e data e termina com `## Veredito` e `## Leitura`.

---

### Task 0: Pré-voo e coordenação do rig

- [x] **Step 1: Confirmar que o rig está livre.** A sessão "Atualizações de stack preferidas" parou o Terminal-Bench do `w1z` às 09:56 CET de 29/10, em 51 de 89 tarefas. Ela retoma o `w1z` (~16 h, contra o driver na 11234) quando esta campanha avisar. Conferir no rig: `pgrep -fl "cache_probe|run-candidate|harbor|splash serve"` vazio, além do daily driver na 11234. O waiter `bench/splash-longctx-2026-10/logs/wait-t5r.sh` fica vivo: ele só dispara depois de `CHAIN-tb21-r1z: done`, que não acontece durante esta campanha.
- [x] **Step 2: Instalar o Splash 1.5.0** em `~/.local/opt/qwen38/splash-v1.5.0/`, lado a lado. Não alterar a 1.4.0 nem a 1.4.1: o `k2a` e o `k3r` da outra sessão dependem delas. Usar o mesmo método da 1.4.1 (ver `bench/stack-updates-2026-10/plan.md`). Conferir `sw_vers` (≥ 26.4 não é exigido para o CLI, só para o app), `splash --version` e ≥ 150 GB livres em disco.
- [x] **Step 3: Gravar o `--help`** em `results/splash-150-help.txt`. Conferir que `--queue-size`, `--decode-share` e `--verify-rows` existem e anotar os defaults.
- [x] **Step 4: Smoke de batch.** Parar o daily driver. Subir o `k2c1` a 32K. Mandar dois `cold` de 32K ao mesmo tempo, gravar `/status` a cada 5 s e o log do servidor. Esperado: as duas janelas de decode se sobrepõem e o `/status` mostra dois requests rodando. Se o Splash serializar, a campanha para e o veredito é "o Splash não faz batch para o Flash-Next".
- [x] **Step 5:** escrever `results/etapa0-preflight.md` (versão, flags, formato do `/status`, resultado do smoke) e fazer commit.

### Task 1: Harness

- [x] **Step 1: Testes que falham** em `tests/test_splash_arms.py` (`--print` dos `k2c*`) e nos testes do `summarize_parallel.py` (`--ref-arm`, `vazão total`) e do `run-parallel-probes.sh` (`--serialize`, `--status-url`).
- [x] **Step 2:** bloco `k2c*` no `run-candidate.sh`, copiado da forma do bloco `w1c*` (linhas 504–522), com `PAR_N`, `PAR_AUX` e `PARALLEL_CONTEXTS` pelo nome do braço e sem `--max-concurrent`.
- [x] **Step 3:** flags novas nos scripts da campanha anterior. Os testes antigos continuam passando.
- [x] **Step 4:** smoke de ponta a ponta no rig: `k2c2a` a 32K, 1 rep, tag `smoke`. Commit.

### Task 2: Etapa 1 — tráfego artificial, 32K e 128K

Fila única no rig (`logs/q-e1.sh`), com `idle-gate.sh` entre bandas e 120 s entre braços. Ordem: `k2c1` → `k2c1a` → `k2c2` → `k2c2a` → `k2c1x2` → `k2c3a` → `k2c4` → `k2c4a` → `w1zc1` → `w1zc2a`, primeiro a 32K, depois a 128K. 3 reps, tag `e1`.

- [ ] **Step 1:** rodar a fila a 32K. Resumo: `summarize_parallel.py --ref-arm k2c1 --context 32768 --tag e1 --markdown`.
- [ ] **Step 2:** rodar a fila a 128K. O `k2c4*` a 128K roda só se o `k2c3a` a 128K passou.
- [ ] **Step 3:** `summarize_parallel.py --vs k2c1x2` para `batch beats queue` nas duas bandas.
- [ ] **Step 4:** escrever `results/etapa1-sintetica.md` e `results/etapa1-verdict.env` com `N_APPROVED`, `BATCH_BEATS_QUEUE` e `GAIN_32K`/`GAIN_128K` (vazão total do maior N aprovado). Commit.

### Task 2b: Etapa 1b — 256K

- [ ] **Step 1:** `k2c1` a 262144, 3 reps (o solo de 256K).
- [ ] **Step 2:** `k2c2L` e `k2c2LL`, 3 reps, com barreira de início.
- [ ] **Step 3:** `k2c2Ls` só se o `k2c2LL` reprovar por memória (recusa HTTP, espera por memória > 60 s, swap ou stream ausente).
- [ ] **Step 4:** `results/etapa1b-256k.md` e `MODE_256K` no `etapa1b-verdict.env`. Commit.

### Task 3: Etapa 1c — `--decode-share` e verify

- [ ] **Step 1:** `k2c2ad1` e `k2c2ad0` a 128K, 3 reps. Comparar `aux p95` e o pior stream contra o `k2c2a` (`--decode-share 0.5`).
- [ ] **Step 2:** `k2c2v` só pelo Review Focus 4.
- [ ] **Step 3:** `results/etapa1c-extras.md`. Commit.

### Task 4: Etapa 2 — Claude Code real (só com `N_APPROVED ≥ 2`)

- [ ] **Step 1:** smoke `claude -p "ping"` contra o Splash na 8585; HTTP 200 no log; efforts aceitos lidos de `/v1/models`.
- [ ] **Step 2:** `kcc1` com as tarefas `task-a` e `task-b` da campanha anterior, em sequência, 2 reps.
- [ ] **Step 3:** `kcc2` com as duas tarefas em paralelo, 3 reps.
- [ ] **Step 4:** `results/etapa2-claude-code.md`. Gate: `wall_s` de cada sessão ≤ 1.5× o controle, zero erros, tarefas feitas. Leitura extra: o par termina antes das duas tarefas em sequência? Commit.

### Task 5: Decisão, launcher e documentação

- [ ] **Step 1:** `results/summary.md` no formato do summary anterior, com a tabela de decisões e a tabela "mlx-serve × Splash" (pior stream, vazão total, aux p95, `T_turno` absoluto, por banda e por N).
- [ ] **Step 2:** launcher do Splash: caminho da 1.5.0 e, se o Task 3 aprovar, `SPLASH_DECODE_SHARE`. O perfil diário do mlx-serve não muda nesta campanha.
- [ ] **Step 3:** `docs/models/qwen3.8-flash-next.md`: tabela de concorrência com as duas colunas. Atualizar o "O que não foi medido" do summary anterior (Splash) com link para este summary.
- [ ] **Step 4:** commit.

### Task 6: Relatório e PR

- [ ] **Step 1:** `render_report.py` com a série Splash; regerar `reports/qwen38-flashnext-concurrency.html`; testes do render passam.
- [ ] **Step 2:** atualizar o card do relatório em `reports/index.html` (data, descrição em inglês que cita o Splash).
- [ ] **Step 3:** conferir a página no browser pane (os dois runtimes em cada gráfico, tema claro e escuro, largura de celular).
- [ ] **Step 4:** push e PR. Avisar a sessão "Atualizações de stack preferidas" que o rig está livre.

## Custo estimado

| etapa | braços × bandas | tempo no rig |
|---|---|---|
| Task 0 | smoke | 0.5 h |
| Task 2 (32K) | 8 braços × 3 reps | ~3 h |
| Task 2 (128K) | 6–8 braços × 3 reps | ~6–8 h |
| Task 2b (256K) | 3–4 braços × 3 reps | ~5–6 h |
| Task 3 | 2–3 braços × 3 reps a 128K | ~3 h |
| Task 4 | 2 + 3 reps de Claude Code | ~3 h |
| `w1zc*` | 2 braços × 2 bandas | ~1.5 h |
| **total** | | **~22–27 h de rig** |

A estimativa usa os tempos da campanha anterior. O Splash decodifica ~35% mais rápido que o mlx-serve, mas o cold de 128K e 256K custa o mesmo (prefill igual), e o cold domina o tempo das reps.

## O que este plano não cobre

- O Flash-Next base (`k1a`) e o GSQ-RCO-Coder (`k3*`) com concorrência. O `k2a` é o braço Splash mais rápido da [splash-longctx](../splash-longctx-2026-10/plan.md).
- 512K e 1M com dois streams.
- Mais de 4 streams.
- O app desktop do Splash 1.5.0 (só o CLI roda no rig).

## Emendas durante a execução (2026-10-29)

- **Filas no rig.** Os scripts de fila ficam em `logs/` do worktree do rig (não rastreados), como nas campanhas anteriores:
  - `logs/chain.sh <label> "<step>"`: para o daily driver, roda os steps e religa o driver;
  - `logs/q-e1.sh`: Etapa 1 a 32K e a 128K (com os `w1zc*`), depois a Etapa 1c (`k2c2ad1`, `k2c2ad0`) e a Etapa 1b (256K). Os braços condicionais (`k2c4*` a 128K, `k2c2Ls`) decidem pelo `VERDICT` do `summarize_parallel.py`;
  - `logs/q-e2.sh`: Etapa 2. Um waiter começa a fila quando aparece `CHAIN-e1: done`.
- **Etapa 1c antes da 1b.** As variantes de `--decode-share` rodam a 128K, logo depois da banda de 128K. A 256K vem por último, porque é a mais longa.
- **Etapa 2 sem esperar o `N_APPROVED`.** A Etapa 2 roda em seguida, na mesma janela de rig, para a comparação com o mlx-serve ficar completa. O gate de tempo continua o mesmo; o veredito usa o `N_APPROVED` da Etapa 1.
- **Etapa 2 no Splash.** O servidor é o `k2c1` a 131072, um boot por rep, como o `w1c1` da campanha anterior. O `run-claude-pair.sh` já lê `BASE_URL` e `MODEL_ID` do `run-candidate.sh --exec`, então não mudou. No rig, o `claude` não está no `PATH` de um shell sem login: a fila usa `CLAUDE_BIN=/opt/homebrew/bin/claude` (Claude Code 2.1.292).
- **Smoke de ponta a ponta (Task 1 Step 4).** `k2c2a` a 32K, 1 rep, tag `smoke`: dois streams e o gerador auxiliar terminam com exit 0, overlap 0.33, hit 0.96, o `status.jsonl` tem dados. É uma rep só, então a razão não vale como resultado.
