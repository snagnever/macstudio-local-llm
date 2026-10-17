# Flash-Next concurrency 2026-10 — campaign runbook

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decidir se o driver diário (Swift 1.5 `13839b7` no mlx-serve 26.10.1) pode servir dois ou mais agentes ao mesmo tempo com `--max-concurrent N`, sem que cada sessão fique mais de 1.5× mais lenta que sozinha e sem erros, travas ou swap.

**Architecture:** A campanha tem duas etapas em ordem fixa. **A Etapa 1 usa só tráfego artificial** (N `cache_probe.py` em paralelo mais um gerador de chamadas auxiliares curtas) e decide o `N` e a configuração de memória. **A Etapa 2 usa Claude Code real** (duas sessões em repositórios distintos) e só roda se a Etapa 1 passar com `N = 2`. O servidor sobe pelo `run-candidate.sh` de 2026-09 com `--exec`, que troca o probe único por `run-parallel-probes.sh`. Um `summarize_parallel.py` novo calcula `T_turno` por stream, a razão contra o `w1` sozinho e os gates.

**Tech Stack:** bash 3.2 (o do rig), Python 3.9 (o do rig; stdlib), pytest via `uv run`, mlx-serve 26.10.1, macmon 0.7.2, Claude Code (CLI `claude`) na Etapa 2.

**Spec:** este runbook (desenho aprovado em chat em 2026-10-17; não há `research/` separado).

## Global Constraints

- Rig: Mac Studio M4 Max 128 GB (`ssh vitor@mac-studio`); checkout no rig: `~/LocalProjects/local-llms`; um modelo servido por vez; Python do rig é 3.9 (`from __future__ import annotations` em todo script novo).
- Runtime fixo: `~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve` (`MLX_SERVE_EXPECTED_VERSION=26.10.1`). O 26.10.2 não entra: a campanha anterior não o adotou.
- Pesos fixos: `Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` `13839b7191e0973ff9fea58232267c395b76c6c0`. O iQ `dafff5c` não roda: mesmo runtime, mesmo batch; o resultado vale para os dois.
- Referência sozinho (`w1`, 26.10.1, 3 reps): `T_turno` **7.9 s a 32K e 8.6 s a 128K**; decode 84.6 / 76.7 tok/s; warm TTFT `tool_turn` 1.8 / 1.9 s; wired pico 96.1 / 111.2 GB ([swift15 tturno-summary](../swift15-flashnext-2026-10/results/tturno-summary.json)).
- Referência sozinho a 256K (`w1`, 26.10.1, 1 rep, perfil diário com `--ctx-size 262144`): `T_turno` **11.1 s**, needles 11/13 ([etapa2-swift-long](../flashnext-next-steps-2026-10/results/etapa2-swift-long.md)). A 256K a razão usa 11.1 s e o gate de needles aceita 11/13 (o mesmo que sozinho); `--kv-quant 8` exige 13/13.
- Métrica por stream: `T_turno = TTFT(tool_turn) + 512 / mediana(decode quente)`, como no `summarize_driver.py`. Métrica da campanha: `razão = T_turno(stream) / T_turno(w1 sozinho)` na mesma banda, pior stream.
- **Gate de lentidão:** razão ≤ 1.5 em todos os streams (≤ 11.9 s a 32K, ≤ 12.9 s a 128K). Razão > 2.0 reprova. Entre 1.5 e 2.0 é "aceitável com aviso" e não muda o launcher.
- **Gate de erros e travas:** zero HTTP 4xx/5xx em probes e no gerador auxiliar; nenhuma requisição com TTFT > 60 s depois do `cold`; swap Δ ≤ 0.5 GB; hit ≥ 0.95 em `append` e `tool_turn` em cada stream; needles corretas (truncado não é falha); livre mínimo ≥ 0.5 GB.
- Flags do driver além do perfil diário: só `--max-concurrent N` (e `--prefix-cache-mem` nas variantes de memória). `--prefill-decode-share` fica no default 0 na Etapa 1a e vira variante só se a Etapa 1a reprovar por TTFT.
- Sampling: `temperature 1.0`, `top_p 0.95`, `top_k 20`, `reasoning_effort xhigh` explícito, `max_tokens 4096`. Gerador auxiliar: `enable_thinking false`, `max_tokens 64`.
- Probe: `cache_probe.py`, cenários `cold → identical → append → middle_mutation → tool_turn`, 3 reps (`middle_mutation` 1), needles 10/50/90. Stream A usa `--content-class audit_retrieval`; stream B usa `--content-class code`; streams C e D reusam A e B com `--session-id` próprio (prefixos distintos, cache entries ≥ 2× N).
- Protocolo térmico: parar o driver diário; `idle-gate.sh` da campanha anterior entre bandas (10 min, GPU < 50 °C, ≥ 82 GB livres); 120 s entre braços.
- Harness: `run-candidate.sh` apaga `~/.mlx-serve/kv-cache` antes de subir e mata o que escuta na porta no fim. Resultados em `bench/flashnext-concurrency-2026-10/results/`, logs em `logs/` (via `FLASHNEXT_RESULTS_DIR`/`FLASHNEXT_LOGS_DIR`, como o `run-arm.sh` anterior).
- Idioma: prosa em pt-BR; comandos, flags, código, comentários e mensagens de git em inglês.
- Commits: `bench(flashnext): ...` terminando com `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Testes: `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests -q`.

## Review Focus

1. **`--max-concurrent` ausente ou com outro nome no 26.10.1.** O doc `cli.md` é do `main`; o 26.10.1 pode não ter a flag ou ignorá-la para MoE. Checado no Task 0 Step 2 (`--help` gravado) e no Task 2 Step 3 (`/props` do servidor mostra o valor; dois `cold` simultâneos têm TTFT que se sobrepõem no tempo, não se somam).
2. **Streams serializados sem erro.** Com a flag ignorada, os dois probes passam nos gates de hit e needles, mas o `T_turno` do segundo inclui a espera do primeiro. Checado no `summarize_parallel.py` (Task 1): lê `wall_start`/`wall_end` de cada requisição (campos novos do `cache_probe.py`, Task 1 Step 4b) e calcula `overlap`; um braço sem nenhum overlap de decode reprova com `VERDICT: fail (no overlap)`.
3. **Memória a 128K com dois streams.** Sozinho o driver chega a 0.01 GB livres a 512K e 111 GB de wired a 128K. Dois streams a 128K somam ~3.2 GB de KV mais estado DeltaNet por stream. Checado no Task 2 Step 5: a variante `w1c2m8` (`--prefix-cache-mem 8GB`) roda se `w1c2` reprovar por `PrefillDoesNotFit`, swap ou livre mínimo < 0.5 GB.
4. **Chamada auxiliar derruba o hit das sessões principais.** Prompts curtos com system prompt próprio entram no prefix cache e podem expulsar os prefixos de 128K (`--prefix-cache-entries 64`, `--prefix-cache-mem 16GB`). Checado no Task 2 Step 4: braço com gerador auxiliar compara hit do `tool_turn` com o braço sem gerador; queda > 0.03 reprova a configuração de cache, não o `N`.
5. **Claude Code manda `reasoning_effort: high` e recebe 500.** O template aceita só `xhigh`, `medium` e `low`. Checado no Task 3 Step 2: `CLAUDE_CODE_EFFORT_LEVEL=xhigh` no ambiente das duas sessões, e o smoke de um `claude -p "ping"` confere HTTP 200 no log do servidor antes do par.

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
| --- | --- | --- |
| `bench/flashnext-concurrency-2026-10/plan.md` | Create | este runbook |
| `bench/flashnext-concurrency-2026-10/scripts/run-arm.sh` | Create | wrapper do `run-candidate.sh` com saída em `results/` e `logs/` desta campanha (cópia do anterior com o caminho novo) |
| `bench/flashnext-concurrency-2026-10/scripts/run-parallel-probes.sh` | Create | sobe N `cache_probe.py` em paralelo contra `$BASE_URL`, um JSONL por stream, espera todos; opcional `--aux` liga o gerador |
| `bench/flashnext-concurrency-2026-10/scripts/aux_load.py` | Create | gerador de chamadas auxiliares (permissão, título) a cada 20 s; JSONL com TTFT, latência, status |
| `bench/flashnext-concurrency-2026-10/scripts/summarize_parallel.py` | Create | por stream: `T_turno`, decode, hit, needles, overlap; razão contra `w1`; gates; `VERDICT` |
| `bench/flashnext-concurrency-2026-10/scripts/run-claude-pair.sh` | Create | Etapa 2: duas sessões `claude -p` em paralelo contra o driver, com ambiente fixo; grava duração e turnos |
| `bench/flashnext-concurrency-2026-10/scripts/claude-tasks/` | Create | dois prompts fixos (`task-a.md`, `task-b.md`) e dois repositórios de exemplo (`repo-a/`, `repo-b/`) |
| `bench/flashnext-concurrency-2026-10/tests/test_scripts.py` | Create | dry-run dos scripts, parser do `aux_load`, gates e `VERDICT` do `summarize_parallel` |
| `bench/qwen3.8-prefix-cache/scripts/cache_probe.py` | Modify | campos novos no registro: `wall_start`, `wall_end` (epoch s) e `concurrency` vindo de `--concurrency N` (hoje fixo em 1) |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify | braços `w1c1 w1c2 w1c4 w1c2m8 w1c4m8` (bloco próprio; `QWEN38_MLX_EXTRA_ARGS="--max-concurrent N"`) |
| `bench/qwen38-flashnext-daily-driver-2026-09/tests/` ou `bench/flashnext-concurrency-2026-10/tests/test_arms.py` | Create | `--print` dos braços novos mostra a flag certa e nada mais |
| `tools/scripts/serve-flashnext-daily-driver.sh` | Modify (Task 4, condicional) | `FLASHNEXT_MAX_CONCURRENT` (default = valor aprovado) |
| `docs/models/qwen3.8-flash-next.md` | Modify (Task 4) | corrige "parallel requests queue on one slot"; tabela de concorrência |

## Braços

| braço | `--max-concurrent` | `--prefix-cache-mem` | streams | gerador auxiliar | task |
| --- | ---: | ---: | ---: | --- | --- |
| `w1c1` | 1 | 16 GB | 1 | não | 2 (controle; reproduz o `w1` de 7.9 / 8.6 s) |
| `w1c1a` | 1 | 16 GB | 1 | sim | 2 (custo das auxiliares na fila de hoje) |
| `w1c2` | 2 | 16 GB | 2 | não | 2 |
| `w1c2a` | 2 | 16 GB | 2 | sim | 2 (cenário do usuário: 2 Claude Code) |
| `w1c2m8` | 2 | 8 GB | 2 | sim | 2 (só se `w1c2`/`w1c2a` reprovar por memória) |
| `w1c4` | 4 | 16 GB | 4 | não | 2 (só a 32K; 128K só se `w1c2a` passar com livre mínimo ≥ 8 GB) |
| `w1c4a` | 4 | 16 GB | 4 | sim | 2 (idem) |
| `w1c2L` | 2 | 16 GB | 2 (256K + 32K) | sim | 2b (assimétrico; perfil diário intacto) |
| `w1c2m4` | 2 | 4 GB | 2 (256K + 256K) | sim | 2b |
| `w1c2q8` | 2 | 16 GB | 2 (256K + 256K) | sim | 2b (`--kv-quant 8`) |
| `w1c2m4q8` | 2 | 4 GB | 2 (256K + 256K) | sim | 2b (`--kv-quant 8`; única com folga prevista ≥ 2 GB) |
| `cc2` | valor aprovado na Etapa 1 | idem | 2 Claude Code | nativo do Claude Code | 3 |
| `cc1` | 1 | 16 GB | 1 Claude Code | nativo | 3 (controle da Etapa 2) |

O gerador auxiliar e os streams são o mesmo processo `run-parallel-probes.sh`; o braço define `PARALLEL_STREAMS` e `PARALLEL_AUX` no `run-candidate.sh`.

## Modelo de resultados

Todo `results/etapa<N>-*.md` começa com título e data, traz a tabela do `summarize_parallel.py` e termina com `## Veredito` e `## Leitura`. A tabela fixa é:

```
| braço | contexto | stream | T_turno | razão ÷ w1 | warm TTFT tool | hit app / tool | decode | overlap | aux p50 / p95 / errs | wired peak | livre mín | swap Δ | HTTP errs | needles |
|---|---:|---|---:|---:|---:|---|---:|---|---|---:|---:|---:|---:|---|
```

`razão ÷ w1` usa 7.9 s a 32K e 8.6 s a 128K. `overlap` é a fração de requisições de decode do stream que coincidem no tempo com decode de outro stream. `aux` é a latência total das chamadas auxiliares (mediana e p95, em s) e a contagem de erros. Abaixo da tabela, o script imprime os gates por linha e `VERDICT: pass | pass-with-warning | fail (<razões>)` por braço e banda.

---

### Task 0: Pré-voo

**Files:**
- Results: `results/etapa0-preflight.md`, `results/mlx-serve-26101-help.txt`

**Braços:** nenhum servidor sobe com pesos neste task.

- [ ] **Step 1: Parar o driver diário e conferir o disco**

Run (no rig): `pkill -f serve-flashnext-daily-driver; sleep 60; lsof -nP -iTCP:11234 -sTCP:LISTEN; df -g /`
Expected: nada escutando na 11234; ≥ 150 GB livres.

- [ ] **Step 2: Gravar o `--help` do 26.10.1 e procurar as flags**

Run: `~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve --help > results/mlx-serve-26101-help.txt; grep -n "max-concurrent\|prefill-decode-share\|prefix-cache-entries" results/mlx-serve-26101-help.txt`
Expected: as três flags aparecem com default. Se `--max-concurrent` não existir no 26.10.1, a campanha para aqui e o veredito é "não há concorrência no runtime do driver; reabrir só com o 26.10.2 ou mais novo".

- [ ] **Step 3: Conferir se o log do servidor identifica requisições**

Run: subir o driver com `tools/scripts/serve-flashnext-daily-driver.sh` em background, mandar `curl` de um chat de 1 token e um `/v1/messages` de 1 token, parar.
Expected: o log mostra uma linha por requisição com rota e tempo (anotar o formato em `etapa0-preflight.md`). Se não mostrar, o `aux_load.py` e o `run-claude-pair.sh` contam só do lado do cliente, e a Etapa 2 interativa (Task 3 Step 6) fica qualitativa.

- [ ] **Step 4: Escrever `results/etapa0-preflight.md`** com disco, flags encontradas e formato do log.

- [ ] **Step 5: Commit**

```bash
git add bench/flashnext-concurrency-2026-10/plan.md bench/flashnext-concurrency-2026-10/results/etapa0-preflight.md bench/flashnext-concurrency-2026-10/results/mlx-serve-26101-help.txt
git commit -m "bench(flashnext): concurrency campaign runbook and preflight"
```

---

### Task 1: Harness da Etapa 1 (scripts e braços)

**Files:**
- Create: `scripts/run-arm.sh`, `scripts/run-parallel-probes.sh`, `scripts/aux_load.py`, `scripts/summarize_parallel.py`, `tests/test_scripts.py`, `tests/test_arms.py`
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` (bloco novo de braços, ao lado do bloco `n1|n2|...|w1`), `bench/qwen3.8-prefix-cache/scripts/cache_probe.py` (timestamps e `--concurrency`)

**Interfaces:**
- Consumes: `run-candidate.sh <arm> <ctx> --repeat 3 --tag <tag> --exec "<cmd>"` exporta `BASE_URL` e `MODEL_ID` para o comando; `cache_probe.py --base-url --model --runtime --runtime-revision --model-revision --arm --session-id --context --repeat --content-class --output`.
- Produces:
  - `run-parallel-probes.sh --streams N [--aux] --context CTX [--contexts CTX1,CTX2,...] --repeat R --arm ARM --tag TAG --out DIR` (`--contexts` dá um contexto por stream e vence `--context`; o nome do JSONL leva o contexto do stream: `<arm>-<ctx_k>-<tag>-s<k>.jsonl`) → `DIR/<arm>-<ctx>-<tag>-s<k>.jsonl` (k = 1..N) e `DIR/<arm>-<ctx>-<tag>-aux.jsonl`; exit ≠ 0 se algum probe falhar.
  - `aux_load.py --base-url URL --model ID --period 20 --duration-file PATH --output PATH` → um registro JSON por chamada: `{kind: "permission"|"title", t_start, ttft_s, total_s, status, error}`; termina quando `duration-file` some (o wrapper o apaga quando os probes acabam).
  - `summarize_parallel.py --results-dir DIR --arm ARM --context CTX|all --tag TAG [--ref-32k 7.9 --ref-128k 8.6 --ref-256k 11.1] [--markdown]` → tabela fixa e `VERDICT`; com `--context all` lê todos os contextos do tag (braços assimétricos) e aplica a referência do contexto de cada stream; braços cujo nome termina em `q8` exigem needles 13/13.
  - Braços no `run-candidate.sh`: `w1c1 w1c1a w1c2 w1c2a w1c2m8 w1c4 w1c4a` (Etapa 1) e `w1c2L w1c2m4 w1c2q8 w1c2m4q8` (Etapa 1b); cada um define `PARALLEL_STREAMS`, `PARALLEL_AUX`, `PARALLEL_CONTEXTS` (só `w1c2L`: `262144,32768`) e `QWEN38_MLX_EXTRA_ARGS`; `w1c2m8` usa `QWEN38_MLX_PREFIX_CACHE_MEM=8GB`, `w1c2m4*` `4GB`; `*q8` acrescenta `--kv-quant 8` ao `QWEN38_MLX_EXTRA_ARGS`.

- [ ] **Step 1: Testes dos braços (falham)**

```python
def test_arm_w1c2_prints_max_concurrent():
    out = run_candidate_print("w1c2", "32768")
    assert "--max-concurrent 2" in out and "--prefix-cache-mem 16GB" in out
    assert "exec: " in out and "run-parallel-probes.sh --streams 2" in out and "--aux" not in out

def test_arm_w1c2m8_prefix_cache_8gb():
    out = run_candidate_print("w1c2m8", "131072")
    assert "--max-concurrent 2" in out and "--prefix-cache-mem 8GB" in out and "--aux" in out

def test_arm_w1c2L_asymmetric_contexts():
    out = run_candidate_print("w1c2L", "262144")
    assert "--max-concurrent 2" in out and "--contexts 262144,32768" in out and "--aux" in out

def test_arm_w1c2m4q8_cache_and_kv_quant():
    out = run_candidate_print("w1c2m4q8", "262144")
    assert "--prefix-cache-mem 4GB" in out and "--kv-quant 8" in out and "--max-concurrent 2" in out

def test_arm_w1c1_has_no_extra_args():
    out = run_candidate_print("w1c1", "32768")
    assert "--max-concurrent" not in out and "--streams 1" in out
```

- [ ] **Step 2: Rodar e ver falhar** — `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests/test_arms.py -q` → FAIL (braço desconhecido).

- [ ] **Step 3: Adicionar o bloco de braços no `run-candidate.sh`**

Mesmo `LAUNCHER`, `MODEL_DIR=$SWIFTDIR`, `MODEL_REV` e binário do `w1`; `EXEC_CMD` montado pelo próprio bloco apontando para `bench/flashnext-concurrency-2026-10/scripts/run-parallel-probes.sh` com `--streams`, `--aux` (quando `PARALLEL_AUX=1`), `--context $CTX --repeat $REPEAT --arm $CAND --tag $TAG --out $RESULTS`. O `--exec` da linha de comando, se vier, vence o do braço.

- [ ] **Step 4: Rodar e ver passar** os testes do Step 1.

- [ ] **Step 4b: Timestamps no `cache_probe.py` (teste falha → passa)**

O registro de hoje não tem hora de início e fim e grava `"concurrency": 1` fixo. Sem isso o `overlap` não existe.

```python
def test_cache_probe_record_has_wall_clock_and_concurrency():
    rec = build_record(args_with(concurrency=2), scenario="append", repeat=1, server=EMPTY_SERVER,
                       wall_start=100.0, wall_end=103.5)
    assert rec["wall_start"] == 100.0 and rec["wall_end"] == 103.5 and rec["concurrency"] == 2
```

Implementar: `--concurrency` (int, default 1) no parser; `time.time()` antes do envio e depois do último chunk em `_run_scenario_repeat`, passados ao construtor do registro. Nenhum campo existente muda; os testes atuais de `bench/qwen3.8-prefix-cache/tests` continuam passando.

- [ ] **Step 5: Testes dos scripts novos (falham)**

```python
def test_run_parallel_probes_dry_run_lists_streams():
    out = run("bash", SCRIPTS/"run-parallel-probes.sh", "--dry-run", "--streams", "2", "--aux", "--context", "32768", "--repeat", "3", "--arm", "w1c2a", "--tag", "e1", "--out", "/tmp/x").stdout
    assert out.count("cache_probe.py") == 2
    assert "--content-class audit_retrieval" in out and "--content-class code" in out
    assert "--session-id w1c2a-e1-s1" in out and "--session-id w1c2a-e1-s2" in out
    assert "aux_load.py" in out

def test_run_parallel_probes_contexts_per_stream():
    out = run("bash", SCRIPTS/"run-parallel-probes.sh", "--dry-run", "--streams", "2", "--contexts", "262144,32768",
              "--repeat", "3", "--arm", "w1c2L", "--tag", "e1b", "--out", "/tmp/x").stdout
    assert "--context 262144" in out and "--context 32768" in out
    assert "w1c2L-262144-e1b-s1.jsonl" in out and "w1c2L-32768-e1b-s2.jsonl" in out

def test_aux_load_prompts_and_record_shape():
    from aux_load import build_request, record
    req = build_request("permission")
    assert req["max_tokens"] == 64 and req["chat_template_kwargs"] == {"enable_thinking": False}
    assert 200 <= approx_tokens(req["messages"]) <= 400
    r = record("title", t_start=1.0, ttft_s=0.4, total_s=0.9, status=200, error=None)
    assert set(r) == {"kind", "t_start", "ttft_s", "total_s", "status", "error"}

def test_summarize_parallel_gates_and_verdict(tmp_path):
    write_fixture_streams(tmp_path, arm="w1c2", ctx=32768, tag="e1",
                          tturno=[9.0, 11.0], hit=[0.97, 0.96], overlap=[0.8, 0.8])
    s = summarize(tmp_path, "w1c2", 32768, "e1", ref_32k=7.9, ref_128k=8.6)
    assert s["verdict"] == "pass" and max(r["ratio"] for r in s["streams"]) == pytest.approx(11.0/7.9)

def test_summarize_parallel_fails_without_overlap(tmp_path):
    write_fixture_streams(tmp_path, arm="w1c2", ctx=32768, tag="e1", tturno=[8.0, 15.9], hit=[0.97, 0.97], overlap=[0.0, 0.0])
    s = summarize(tmp_path, "w1c2", 32768, "e1")
    assert s["verdict"].startswith("fail") and "no overlap" in s["verdict"]

def test_summarize_parallel_ref_256k_and_kv_quant_needles(tmp_path):
    write_fixture_streams(tmp_path, arm="w1c2q8", ctx=262144, tag="e1b", tturno=[15.0, 16.0], hit=[0.99, 0.99],
                          overlap=[0.7, 0.7], needles=["12/13", "13/13"])
    s = summarize(tmp_path, "w1c2q8", 262144, "e1b", ref_256k=11.1)
    assert s["verdict"].startswith("fail") and "needles" in s["verdict"]   # kv-quant arm needs 13/13

def test_summarize_parallel_warning_band(tmp_path):
    write_fixture_streams(tmp_path, arm="w1c2", ctx=131072, tag="e1", tturno=[13.5, 14.0], hit=[0.99, 0.99], overlap=[0.7, 0.7])
    assert summarize(tmp_path, "w1c2", 131072, "e1")["verdict"] == "pass-with-warning"   # 14.0/8.6 = 1.63
```

- [ ] **Step 6: Rodar e ver falhar.**

- [ ] **Step 7: Implementar `run-parallel-probes.sh`** — spawn com `&`, `wait` em cada PID, cria o `duration-file` antes dos probes e o apaga depois; classes por índice: ímpar `audit_retrieval`, par `code`; `--dry-run` imprime os comandos e sai 0.

- [ ] **Step 8: Implementar `aux_load.py`** — `build_request(kind) -> dict`, `record(...) -> dict`, `main(argv) -> int`; dois system prompts fixos em inglês (classificador de permissão de comando bash; gerador de título de sessão) com um bloco de ~250 tokens de contexto falso; `urllib` só; alterna `permission`/`title`; grava TTFT pelo primeiro chunk do stream.

- [ ] **Step 9: Implementar `summarize_parallel.py`** — reusa `t_turno`, `_median`, `_is_http_error` do `summarize_driver.py` (import por caminho); `overlap` calculado dos campos `wall_start`/`wall_end` do Step 4b: fração dos registros quentes do stream cujo intervalo cruza o intervalo de algum registro de outro stream; gates e limites do "Global Constraints"; `VERDICT` por braço e banda.

- [ ] **Step 10: Rodar e ver passar** todos os testes da campanha.

- [ ] **Step 11: Commit**

```bash
git add bench/flashnext-concurrency-2026-10 bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh bench/qwen3.8-prefix-cache/scripts/cache_probe.py bench/qwen3.8-prefix-cache/tests
git commit -m "bench(flashnext): parallel probe harness and max-concurrent arms"
```

---

### Task 2: Etapa 1 — testes artificiais (antes de qualquer Claude Code)

**Files:**
- Results: `results/etapa1-sintetica.md`, JSONL por stream, `results/etapa1-verdict.env`

**Ordem fixa.** Nenhum braço da Etapa 2 sobe antes de `etapa1-verdict.env` existir com `N_APPROVED ≥ 2`.

- [ ] **Step 1: `idle-gate.sh`** (`bash ../flashnext-next-steps-2026-10/scripts/idle-gate.sh`) → exit 0.

- [ ] **Step 2: Controle `w1c1` a 32K e 128K** — `bash scripts/run-arm.sh w1c1 32768 --repeat 3 --tag e1`, idem `131072`. Gate: `T_turno` dentro de ±3% de 7.9 / 8.6 s. Fora disso, parar e investigar o rig antes de medir concorrência.

- [ ] **Step 3: `w1c2` a 32K** — `run-arm.sh w1c2 32768 --repeat 3 --tag e1`; `summarize_parallel.py --arm w1c2 --context 32768 --tag e1 --markdown`. Conferir `overlap > 0` em ambos os streams e `/props` com `max_concurrent: 2` (anotar o campo exato). Sem overlap: Review Focus 1; a campanha para e o veredito é "flag sem efeito no 26.10.1".

- [ ] **Step 4: `w1c1a` e `w1c2a` a 32K** — mede o custo das auxiliares na fila de hoje e no batch. Comparar hit do `tool_turn` entre `w1c2` e `w1c2a` (Review Focus 4) e `aux p95` entre `w1c1a` e `w1c2a`.

- [ ] **Step 5: `w1c2` e `w1c2a` a 128K** — idle-gate antes. Se reprovar por `PrefillDoesNotFit`, swap ou livre mínimo < 0.5 GB: rodar `w1c2m8` a 128K e a 32K.

- [ ] **Step 6: `w1c4` e `w1c4a` a 32K** — só se `w1c2a` passou nas duas bandas. 128K com 4 streams só se o livre mínimo do `w1c2a` a 128K foi ≥ 8 GB.

- [ ] **Step 7: Escrever `results/etapa1-sintetica.md`** com a tabela de todos os braços e bandas, veredito por `N`, e `results/etapa1-verdict.env`:

```
N_APPROVED=<0|2|4>
PREFIX_CACHE_MEM=<16GB|8GB>
NOTE=<uma linha>
```

Regra: `N_APPROVED` é o maior `N` cujo braço `*a` (com gerador) passou (`pass` ou `pass-with-warning`) a 32K **e** a 128K. `pass-with-warning` entra no `NOTE`.

- [ ] **Step 8: Commit** — `bench(flashnext): etapa 1 - synthetic concurrency on the Swift 1.5 driver`.

---

### Task 2b: Etapa 1b — 256K com dois streams (só se `w1c2a` passou a 128K)

**Files:**
- Results: `results/etapa1b-256k.md`, JSONL por stream, `results/etapa1b-verdict.env`

**Por que uma etapa própria.** Sozinho a 256K o driver fica com ~0.03 GB livres. A conta do perfil diário (pesos ~68–75 GB, prefix cache 16 GB, overhead fixo ~21–36 GB, KV de atenção 6.4 GB por stream, reserva do SO 8 GB) não deixa lugar para um segundo stream de 256K. Cada braço tira uma coisa. A ordem vai do que não muda o perfil diário ao que muda mais.

**Memória esperada por braço (KV + cache, contra o perfil diário a 256K com 1 stream):**

| braço | KV dos 2 streams | prefix cache em RAM | Δ contra 1 stream |
| --- | ---: | ---: | ---: |
| `w1c2L` | 6.4 + 0.8 GB | 16 GB | +0.8 GB |
| `w1c2m4` | 6.4 + 6.4 GB | 4 GB | −5.6 GB |
| `w1c2q8` | 3.2 + 3.2 GB | 16 GB | +0.0 GB |
| `w1c2m4q8` | 3.2 + 3.2 GB | 4 GB | −12.0 GB |

O overhead de prefill (scratch do chunk de 1024 tokens por stream) não está na conta e é a incógnita que o braço mede.

- [ ] **Step 1: Pré-condição** — `results/etapa1-verdict.env` com `N_APPROVED ≥ 2`. Sem isso, escrever `etapa1b-256k.md` com uma linha ("não rodou: Etapa 1 reprovou a 128K") e pular para o Task 3.

- [ ] **Step 2: Controle `w1c1` a 256K, 1 rep** — `run-arm.sh w1c1 262144 --repeat 1 --tag e1b`. Gate: `T_turno` dentro de ±5% de 11.1 s (1 rep, ruído maior). Registrar o livre mínimo: é a folga real para os braços seguintes.

- [ ] **Step 3: `w1c2L` (256K + 32K)** — `run-arm.sh w1c2L 262144 --repeat 3 --tag e1b`; `summarize_parallel.py --arm w1c2L --context all --tag e1b --markdown`. Razão do stream A contra 11.1 s, do stream B contra 7.9 s. Se passar, o cenário "uma sessão longa e uma curta" está resolvido sem mudar o perfil.

- [ ] **Step 4: `w1c2m4` (256K + 256K, cache 4 GB)** — idle-gate antes. Reprovação esperada por `PrefillDoesNotFit` ou livre mínimo < 0.5 GB conta como resultado, não como erro de harness: registrar a mensagem exata do servidor no `etapa1b-256k.md`. Comparar o warm TTFT do `tool_turn` com o `w1c2a` a 128K: a diferença é o custo de restaurar do SSD.

- [ ] **Step 5: `w1c2q8` (256K + 256K, KV 8-bit)** — gate extra: needles 13/13 nos dois streams. Needle errada reprova o `--kv-quant 8` para o driver, mesmo que a memória caiba.

- [ ] **Step 6: `w1c2m4q8`** — só se `w1c2m4` **ou** `w1c2q8` reprovou por memória e nenhum reprovou por needles. É a única variante com folga prevista ≥ 2 GB.

- [ ] **Step 7: `--os-reserve-gib 4`** não entra como braço: a campanha anterior mediu recusa por ~0.3 GB com 4 GB e OOM de Metal com 2 GB a 512K. Se o melhor braço de 256K reprovar por menos de 1 GB, anotar como "próximo passo possível", sem rodar.

- [ ] **Step 8: Escrever `results/etapa1b-256k.md`** com a tabela de todos os braços e `results/etapa1b-verdict.env`:

```
N_APPROVED_256K=<0|2>
MODE_256K=<asym|m4|q8|m4q8|none>
PREFIX_CACHE_MEM_256K=<16GB|4GB>
KV_QUANT_256K=<off|8>
NOTE=<uma linha>
```

Regra: `MODE_256K` é o primeiro braço da ordem acima que passou (`pass` ou `pass-with-warning`). `asym` significa "2 streams só se um deles for ≤ 32K"; o launcher não muda nesse caso.

- [ ] **Step 9: Commit** — `bench(flashnext): etapa 1b - two streams at 256K`.

---

### Task 3: Etapa 2 — Claude Code real (só com `N_APPROVED ≥ 2`)

**Files:**
- Create: `scripts/run-claude-pair.sh`, `scripts/claude-tasks/task-a.md`, `scripts/claude-tasks/task-b.md`, `scripts/claude-tasks/repo-a/`, `scripts/claude-tasks/repo-b/`
- Results: `results/etapa2-claude-code.md`, `results/cc-*.json`, `logs/cc-*-server.log`

**Interfaces:**
- Consumes: `tools/scripts/serve-flashnext-daily-driver.sh` com `FLASHNEXT_MAX_CONCURRENT` (Task 4 adiciona a variável; até lá o script da Etapa 2 passa a flag por `QWEN38_MLX_EXTRA_ARGS`-equivalente do launcher diário, ou sobe o servidor pelo `run-candidate.sh w1c2 --exec`).
- Produces: `run-claude-pair.sh --sessions 1|2 --tag TAG` → `results/cc-<tag>-<k>.json` com o JSON de `claude -p --output-format json` (campos `duration_ms`, `num_turns`, `is_error`) mais `wall_s` e `http_errs` (do log do servidor, se o Task 0 Step 3 achou o formato).

- [ ] **Step 1: Tarefas fixas.** `repo-a/`: pacote Python pequeno (3 módulos, 4 testes); `task-a.md` pede uma flag nova no CLI com teste. `repo-b/`: script bash com 2 bugs plantados; `task-b.md` pede corrigir e adicionar um teste. Cada tarefa deve exigir 8 a 12 tool calls e caber em ~10 min sozinha. Um `git init` por repo para o Claude Code ter o estado limpo; `run-claude-pair.sh` restaura com `git checkout -- . && git clean -fd` antes de cada run.

- [ ] **Step 2: Ambiente das sessões** (fixo no script):

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:11234 ANTHROPIC_AUTH_TOKEN=local
export ANTHROPIC_MODEL="$MODEL_ID" ANTHROPIC_DEFAULT_HAIKU_MODEL="$MODEL_ID" ANTHROPIC_SMALL_FAST_MODEL="$MODEL_ID"
export CLAUDE_CODE_EFFORT_LEVEL=xhigh
```

Smoke: `claude -p "reply with pong" --output-format json` → `is_error: false`; no log do servidor nenhum 4xx/5xx (Review Focus 5).

- [ ] **Step 3: Testes do script (falham → passam)**

```python
def test_run_claude_pair_dry_run():
    out = run("bash", SCRIPTS/"run-claude-pair.sh", "--dry-run", "--sessions", "2", "--tag", "e2").stdout
    assert out.count("claude -p") == 2 and "task-a.md" in out and "task-b.md" in out
    assert "CLAUDE_CODE_EFFORT_LEVEL=xhigh" in out and "ANTHROPIC_DEFAULT_HAIKU_MODEL=" in out
```

- [ ] **Step 4: Controle `cc1`** — driver com `--max-concurrent 1`; `run-claude-pair.sh --sessions 1 --tag a` com `task-a`, depois `--tag b` com `task-b`. 2 reps cada. Registrar `wall_s`, `num_turns`, `is_error`.

- [ ] **Step 5: Par `cc2`** — driver com `--max-concurrent $N_APPROVED` e `--prefix-cache-mem $PREFIX_CACHE_MEM`; `run-claude-pair.sh --sessions 2 --tag e2`, 3 reps. Gates: `is_error false` nas duas; `wall_s` de cada sessão ≤ 1.5× o controle da mesma tarefa; zero 4xx/5xx; swap Δ ≤ 0.5 GB (mem-sampler do harness anterior).

- [ ] **Step 6: Sessão interativa (qualitativa, o usuário dirige).** Com o mesmo driver no ar, duas janelas de `claude` interativas em `repo-a` e `repo-b`, as mesmas tarefas, com permissões em modo padrão para que o classificador de permissão e o título de sessão rodem. O script `run-claude-pair.sh --interactive-env` só imprime o `export` a colar. Registrar: travas visíveis (> 60 s sem resposta), retries, títulos gerados, contagem de `/v1/messages` no log do servidor por sessão (se o formato permitir).

- [ ] **Step 7: Escrever `results/etapa2-claude-code.md`** com a tabela `| braço | tarefa | rep | wall_s | ÷ controle | num_turns | is_error | http errs | swap Δ |`, a leitura da sessão interativa e `## Veredito`.

- [ ] **Step 8: Commit** — `bench(flashnext): etapa 2 - two Claude Code sessions on one driver`.

---

### Task 4: Decisão e documentação

**Files:**
- Modify: `tools/scripts/serve-flashnext-daily-driver.sh`, `docs/models/qwen3.8-flash-next.md`
- Create: `results/summary.md`

- [ ] **Step 1: Launcher.** Se a Etapa 2 passou: `FLASHNEXT_MAX_CONCURRENT="${FLASHNEXT_MAX_CONCURRENT:-$N_APPROVED}"` e `--max-concurrent "$FLASHNEXT_MAX_CONCURRENT"` no `COMMAND`; `PREFIX_CACHE_MEM` se a Etapa 1 escolheu 8 GB. Se reprovou: default `1`, variável documentada como opt-in com o aviso da razão medida. **256K:** com `MODE_256K=none` ou `asym`, o launcher força `--max-concurrent 1` quando `--ctx-size` > 131072 (o perfil `512k` já é 1 por construção); com `m4`, `q8` ou `m4q8`, o perfil `256k` (novo, opcional) sobe com `--ctx-size 262144`, o `--prefix-cache-mem` e o `--kv-quant` de `etapa1b-verdict.env`, e `--max-concurrent 2`.

- [ ] **Step 2: Card do modelo.** Substituir "One model at a time. The MoE does not batch decode: parallel requests queue on one slot." pelo resultado medido (N aprovado por banda, inclusive 256K e o modo que passou, razão por banda, custo das auxiliares, memória), com link para `results/summary.md`. Card em inglês.

- [ ] **Step 3: `results/summary.md`** no formato das campanhas anteriores: veredito em negrito, runtimes que rodaram, tabela de decisões (Etapa 1 e 2 com regra, resultado, decisão, fonte), notas, "o que não foi medido" (iQ `dafff5c`, 256K/512K, `--prefill-decode-share`, 26.10.2 só-SSD, > 4 streams).

- [ ] **Step 4: Testes** — `uv run --no-project --with pytest python -m pytest bench/flashnext-concurrency-2026-10/tests -q` → todos passam; `bash -n tools/scripts/serve-flashnext-daily-driver.sh`.

- [ ] **Step 5: Commit** — `bench(flashnext): concurrency verdict, launcher flag and model card`.

## Custo estimado

| Etapa | braços × bandas | tempo de rig |
| --- | --- | --- |
| 0 | — | 20 min |
| 1 | `w1c1`, `w1c1a`, `w1c2`, `w1c2a` × 2 bandas; `w1c4`, `w1c4a` a 32K; `w1c2m8` condicional | ~5 h (128K com cold de ~165 s × 2 streams × 3 reps) |
| 1b | `w1c1` 1 rep; `w1c2L`, `w1c2m4`, `w1c2q8` × 3 reps; `w1c2m4q8` condicional (cold de 256K ~6 min por rep por stream) | ~4–5 h |
| 2 | `cc1` 4 runs, `cc2` 3 runs, 1 sessão interativa | ~2 h |
| 4 | — | 30 min |

## O que este plano não cobre

- iQ `dafff5c`: mesmo runtime; se o usuário quiser, `w1c2a` roda com `FLASHNEXT_MODEL` do iQ como braço extra sem mudança de script.
- 512K: o driver sozinho já usa `--kv-quant 4` e fica em < 0.1 GB livres; dois streams ficam fora. 256K com 4 streams fica fora em qualquer variante.
- `--os-reserve-gib` abaixo de 8: só anotado (Task 2b Step 7), nunca rodado.
- mlx-serve 26.10.2 (cache só-SSD, batch de Flash-Next com imagens): fora, por decisão da campanha anterior.
- Qualidade da resposta sob concorrência: a amostragem é a mesma; `needles` é o único controle.

## Emendas durante a execução (2026-10-17)

- **Livre mínimo deixa de ser gate.** O `vm_stat` "Pages free" cai para ~0.01 GB no carregamento de todo modelo (cache de arquivo), e as rodadas sozinho de 2026-10 já registravam 0.01–0.06 GB de 32K a 256K. O valor fica na tabela só para leitura. A falta de memória aparece como swap Δ > 0.5 GB, recusa HTTP (`PrefillDoesNotFit`) ou um stream que morre (`missing streams`).
- **Condição do `w1c4` a 128K** (Task 2 Step 6): roda se o `w1c2a` a 128K passou e o wired peak dele ficou ≤ 115 GB, no lugar de "livre mínimo ≥ 8 GB".
- **Etapa 1b:** a reprovação "por memória" do Task 2b Steps 4 e 6 passa a ser recusa HTTP, swap ou stream ausente.
- **Overlap** usa a janela de decode de cada requisição (`wall_first_token` a `wall_end`), não a requisição inteira: a espera na fila não conta. O `T_turno` usa o TTFT medido no cliente (`client_ttft_ms`).
- **Trava (> 60 s)** vale para `identical`, `append`, `tool_turn` e chamadas auxiliares. `cold` e `middle_mutation` são presos ao prefill (o `w1` sozinho leva 92 s no `middle_mutation` a 128K).
- **Streams 3 e 4** recebem `--prompt-salt s3`/`s4`: o prompt do `cache_probe.py` não depende do `--session-id`.
- **Commits** terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (modelo da sessão de execução).

### Smoke (1 rep, `w1c2a` a 32K, antes da Etapa 1)

O harness rodou de ponta a ponta no rig. O log de boot mostra `[batched] gdn batched decode engaged (slots=2)`. Cada stream decodificou a ~42.8 tok/s enquanto o outro rodava (sozinho: 84.6), então o total ficou perto do decode de um stream só. `T_turno` 13.8 s nos dois streams (razão 1.75). É uma rep só; a Etapa 1 mede com 3.

### Braço `w1c1x2` (pedido do usuário, 2026-10-17)

| braço | `--max-concurrent` | `--prefix-cache-mem` | streams | gerador auxiliar | task |
| --- | ---: | ---: | ---: | --- | --- |
| `w1c1x2` | 1 (explícito) | 16 GB | 2 | sim | 2 (controle serializado: a fila de hoje com duas sessões) |

O gate contra o `w1` sozinho compara com uma sessão que não divide o servidor. A pergunta "o batch é melhor que a fila?" pede o mesmo par de streams num slot só. O `w1c1x2` roda a 32K e a 128K. O `summarize_parallel.py --vs w1c1x2` imprime a razão do pior stream e a da média entre o braço com batch e o serializado, mais `batch beats queue: yes|no` (as duas razões ≤ 1.0). O gate de overlap não vale para o `w1c1x2`, porque ali o overlap 0 é o esperado.

Regra de decisão acrescentada ao Task 2 Step 7 e ao Task 4 Step 1: o `etapa1-verdict.env` ganha `BATCH_BEATS_QUEUE=<yes|no>` por banda. O launcher só muda o default para `N = 2` se o braço `*a` passou **e** `batch beats queue: yes` nas duas bandas. Sem isso, a concorrência fica como opt-in documentado.
