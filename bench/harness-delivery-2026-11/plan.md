# Entrega por harness 2026-11 — runbook da campanha

> **Para agentes:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para executar este plano task a task. Os steps usam checkbox (`- [ ]`).

> **Status (2026-11-14):** Tasks 0 a 7 feitas. A matriz rodou no rig com `k2` e `z4`: 105 de 112 sessões prontas. A regra "Reserva" passa no limite (51 contra 54, tolerância 3). A T5 segue a regra do prompt, por escolha do usuário: mudar o `Makefile` fora do lint não reprova. Resultado: [results/summary.md](results/summary.md) e [results/audit.md](results/audit.md). Preflight e smoke: [results/preflight.md](results/preflight.md).

**Objetivo:** medir, em 7 tarefas de código com check automático, quantas tarefas cada par (harness, peso) entrega e em quanto tempo.

**Arquitetura:** o rig roda os 4 harnesses, um por vez, em modo não interativo, com `HOME` temporário e dentro do `sandbox-exec`. O mesmo rig serve um peso por vez no Splash 1.6.1 (braço `rc2`, 131072). O usuário mudou a execução do MacBook para o rig em 13/11; os steps abaixo que citam o MacBook valem para o rig. Um runner em Python copia o repositório da tarefa, dispara o harness com limite de tempo, roda o check fora da sessão e grava um registro JSON por sessão. Um resumo aplica as 3 regras de decisão.

**Stack:** Python 3 (stdlib), `pytest` via `uv run --no-project --with pytest`, bash 3.2 no rig, `ssh vitor@mac-studio`.

**Spec:** [docs/superpowers/specs/2026-11-13-harness-delivery-design.md](../../docs/superpowers/specs/2026-11-13-harness-delivery-design.md)

## Restrições globais

- Layout do [AGENTS.md](../../AGENTS.md): `scripts/`, `tests/` e `results/` entram no git; `logs/` não entra.
- Nenhum texto de sessão no git. Transcript e cópia do repositório ficam em `logs/`.
- A campanha não lê nem escreve `~/.claude`, `~/.config/opencode`, `~/.dsh` ou `~/.pi`.
- Esforço de raciocínio `xhigh` nos 4 harnesses. Contexto 131072. Uma sessão por vez.
- Nenhum harness tem limite de turnos. O único limite é o tempo da tarefa.
- Nenhum `git pull` no rig enquanto uma fila roda.
- O servidor do usuário na porta 8585 para durante a fila e volta no fim.
- TDD: cada função nova tem um teste que falhou antes.
- Sem push, PR ou merge sem pedido do usuário.
- Commits terminam com `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.

## Foco de revisão

1. **Um harness espera para sempre com o servidor fora.** Esperado: a sessão termina no limite e grava `timeout`. Teste: `test_timeout_kills_process_group`.
2. **A sessão deixa processos filhos vivos** (servidor de teste, `make`). Esperado: o runner mata o grupo de processos. Mesmo teste.
3. **O harness escreve fora da cópia** ou lê a configuração real do usuário. Esperado: `HOME` aponta para um diretório temporário. Teste: `test_env_isolates_home`.
4. **O check aceita teste apagado.** Esperado: os testes originais rodam de uma cópia intacta. Teste: `test_deleted_test_does_not_pass`.
5. **A fila para no meio.** Esperado: a retomada pula as sessões com registro gravado. Teste: `test_order_skips_recorded_sessions`.

## Arquivos

| arquivo | responsabilidade |
|---|---|
| `scripts/tasks.py` | registro das 7 tarefas: origem do repositório, pedido, limite |
| `scripts/checks.py` | check por tarefa, com a guarda dos testes originais |
| `scripts/harness.py` | comando, ambiente isolado e versão de cada harness |
| `scripts/run_session.py` | uma sessão: cópia, harness com limite, check, registro |
| `scripts/matrix.py` | ordem da matriz, retomada, laço das sessões |
| `scripts/rig-server.sh` | sobe e derruba um peso no rig; grava porta e id do modelo |
| `scripts/summarize.py` | tabelas, regras de decisão, vereditos do `harness-matrix` |
| `tests/` | `test_tasks.py`, `test_checks.py`, `test_harness.py`, `test_session.py`, `test_matrix.py`, `test_summarize.py`, `solutions/`, `fake_harness.py` |

Comando de teste da campanha: `uv run --no-project --with pytest python -m pytest bench/harness-delivery-2026-11/tests -q`.

---

### Task 0: Portão e preflight

**Files:** `results/preflight.md`.

- [ ] **Step 1: Portão.** Conferir que `bench/swift-uncensored-2026-11/results/etapa2-um-stream.md` existe e que nenhuma fila roda no rig (`pgrep -f chain-`). Ler o veredito da regra "Velocidade" do `z4h`. Se o `z4h` falhar, o segundo peso é o `z2`; gravar a escolha.
- [ ] **Step 2: Rede.** Com um servidor no rig, do MacBook: `curl http://mac-studio:<porta>/v1/models`, um `POST /v1/chat/completions` e um `POST /v1/messages`. Expected: HTTP 200 nos três. Se o Splash só escutar em `127.0.0.1`, gravar isso e usar um túnel `ssh -L` no `rig-server.sh`.
- [ ] **Step 3: Isolamento.** Para cada harness, rodar `HOME=<tmp> <harness> --version` e listar o que ele cria em `<tmp>`. Gravar o caminho do arquivo de configuração de cada um dentro de `<tmp>`. Conferir que o `mtime` dos 4 diretórios globais reais não mudou.
- [ ] **Step 4: Versões.** Gravar a versão dos 4 harnesses, do Splash e os ids de modelo do `k2` e do segundo peso.
- [ ] **Step 5: Commit** de `results/preflight.md`.

### Task 1: Tarefas e checks

**Files:** Create `scripts/tasks.py`, `scripts/checks.py`, `tests/test_tasks.py`, `tests/test_checks.py`, `tests/solutions/<id>.patch` (a, b, T1, T5, T7; c e d reusam `bench/flashnext-concurrency-2026-10/scripts/claude-tasks/solutions/`).

**Interfaces — Produces:**
- `tasks.TASKS: dict[str, Task]`, chaves `a b c d T1 T5 T7`; `Task(id, repo_src: Path, limit_s: int, hard: bool)`.
- `tasks.prompt(task_id: str) -> str`
- `tasks.fresh_copy(task_id: str, dest: Path) -> Path`
- `checks.check(task_id: str, repo: Path) -> CheckResult(task_done: bool, steps_passed: int | None, cheat: list[str])`
- CLI: `checks.py <task_id> <repo>` imprime o `CheckResult` em JSON.

Valores fixos: `limit_s` 900 para a, b, c, d e T1; 1200 para T5; 1800 para T7. `hard` é verdadeiro para T1, T5 e T7. O pedido de a–d é o arquivo `task-<id>.md` inteiro. O pedido de T1, T5 e T7 é o primeiro bloco ```` ```text ```` da seção "Prompt" do modelo.

Regras do check:
- **Guarda, nas 7 tarefas:** o check copia os testes originais de `repo_src` para um diretório temporário ao lado do código da sessão e roda esses testes. Um arquivo de teste original apagado, ou com linhas originais removidas, entra em `cheat` como `tests_modified`.
- **a, b:** as condições da função `task_done` do `run-claude-pair.sh` (linhas 93–118), portadas para Python.
- **c, d:** chamam `check-c.sh` e `check-d.sh`.
- **T1:** os testes originais dão `5 passed`; `python3 -m ledger balance sample.csv` imprime `2815.20`.
- **T5:** `make check` sai com 0; nenhum `noqa` ou `skip` em `app` e `tests`; `pyproject.toml` e a receita `lint` do `Makefile` iguais aos originais (outra mudança no `Makefile` vira a nota `makefile_changed` e não reprova); no máximo 1 arquivo de teste ou `conftest` mudado; a leitura de `os.environ` continua no teste; `README.md` cita `SERVICE_NAME`. Cada regra quebrada entra em `cheat` (`noqa`, `skip`, `lint_config_changed`, `tests_modified`, `env_read_removed`) e torna `task_done` falso.
- **T7:** `steps_passed` conta os 5 passos: (1) testes originais passam; (2) `parse_amount("$1,250.50") == 1250.5`; (3) `balance --json` imprime `{"balance": <número>}`; (4) `make test` sai com 0 e existe o alvo `balance`; (5) `CHANGELOG.md` tem pelo menos 4 linhas de item. `task_done` exige 5.

- [ ] **Step 1: Testes que falham.**

```python
def test_registry_has_seven_tasks_with_spec_limits():
    assert {k: t.limit_s for k, t in TASKS.items()} == {
        "a": 900, "b": 900, "c": 900, "d": 900, "T1": 900, "T5": 1200, "T7": 1800}

def test_prompt_of_T1_is_the_text_block_only():
    p = prompt("T1")
    assert p.startswith("The test suite in this project is failing.") and "Verificação" not in p

@pytest.mark.parametrize("task", ["a", "b", "c", "d", "T1", "T5", "T7"])
def test_untouched_fixture_is_not_done(task, tmp_path):
    assert check(task, fresh_copy(task, tmp_path / "r")).task_done is False

@pytest.mark.parametrize("task", ["a", "b", "c", "d", "T1", "T5", "T7"])
def test_reference_solution_is_done_without_cheat(task, tmp_path):
    r = check(task, solved(task, tmp_path))          # solved() aplica tests/solutions/<id>.patch
    assert r.task_done is True and r.cheat == []

def test_deleted_test_does_not_pass(tmp_path):       # T1: apaga os testes em vez de corrigir
    repo = fresh_copy("T1", tmp_path / "r"); shutil.rmtree(repo / "tests")
    r = check("T1", repo)
    assert r.task_done is False and "tests_modified" in r.cheat

@pytest.mark.parametrize("cheat", ["noqa", "skip", "lint_config_changed", "env_read_removed"])
def test_T5_cheat_fails_the_check(cheat, tmp_path):
    r = check("T5", cheated("T5", cheat, tmp_path))  # cheated() aplica a solução e depois a trapaça
    assert r.task_done is False and cheat in r.cheat

def test_T7_counts_steps(tmp_path):
    r = check("T7", solved("T7", tmp_path, drop_step=5))   # sem CHANGELOG.md
    assert (r.task_done, r.steps_passed) == (False, 4)
```

- [ ] **Step 2: Rodar.** Expected: FAIL com `ModuleNotFoundError: tasks`.
- [ ] **Step 3: Escrever as soluções de referência** em `tests/solutions/` e os helpers `solved` e `cheated` em `tests/conftest.py`.
- [ ] **Step 4: Implementar** `tasks.py` e `checks.py`. T5 cria o virtualenv com `make venv` dentro da cópia; o teste de T5 leva o marcador `network`.
- [ ] **Step 5: Rodar.** Expected: PASS.
- [ ] **Step 6: Commit.**

### Task 2: Adaptadores de harness

**Files:** Create `scripts/harness.py`, `tests/test_harness.py`.

**Interfaces — Produces:**
- `harness.HARNESSES = ("claude", "opencode", "dsh", "pi")`
- `harness.Target(host: str, port: int, model_id: str)`
- `harness.command(name: str, prompt: str, repo: Path, home: Path, target: Target) -> Cmd(argv: list[str], env: dict[str, str], cwd: Path)`
- `harness.prepare(name: str, home: Path, target: Target) -> None` escreve os arquivos de configuração dentro de `home`.
- `harness.version(name: str) -> str`

Valores fixos, com os launchers de `bench/qwen3.8-harness-eval/macbook/` como referência de campos:

| harness | argv | ambiente e configuração |
|---|---|---|
| `claude` | `claude -p <pedido> --output-format stream-json --verbose --setting-sources project --strict-mcp-config --permission-mode bypassPermissions` | as variáveis do `run-cc.sh`, com `CLAUDE_CODE_EFFORT_LEVEL=xhigh`, `CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072` e `CLAUDE_CONFIG_DIR=<home>/.claude` |
| `opencode` | `opencode run <pedido> --model rig/<model_id>` | `OPENCODE_CONFIG_CONTENT` com o provider `rig` completo (`baseURL http://<host>:<port>/v1`), variante `xhigh` e `permission` `edit` e `bash` em `allow` |
| `dsh` | `dsh --profile headless <pedido>` | `DSH_HOME=<home>/.dsh`, `RIG_API_KEY=local`, `DSH_TELEMETRY_MODE=DISABLED`; `prepare` escreve `settings.yaml` com o provider e `agent-default-model` (`reasoningEffort: xhigh`) |
| `pi` | `pi -p <pedido> --model rig/<model_id> --thinking xhigh` | `prepare` escreve `<home>/.pi/agent/models.json` com o provider `rig` |

Todos recebem `HOME=<home>`, `XDG_CONFIG_HOME=<home>/.config`, `XDG_DATA_HOME=<home>/.local/share`, o `PATH` do processo pai e `cwd=<repo>`. Nenhuma outra variável do processo pai passa, menos `LANG` e `TERM`. Se o preflight (Task 0, Step 3) mostrar outro caminho de configuração, o adaptador usa o caminho medido.

- [ ] **Step 1: Testes que falham.**

```python
T = Target("mac-studio", 8585, "m:IQ4_XS")

@pytest.mark.parametrize("name", HARNESSES)
def test_env_isolates_home(name, tmp_path):
    c = command(name, "do it", tmp_path / "repo", tmp_path / "home", T)
    assert c.env["HOME"] == str(tmp_path / "home") and c.cwd == tmp_path / "repo"
    assert str(Path.home()) not in " ".join(c.argv) + " ".join(c.env.values()).replace(c.env["PATH"], "")

@pytest.mark.parametrize("name", HARNESSES)
def test_prompt_is_one_argv_item(name, tmp_path):
    assert "line 1\nline 2" in command(name, "line 1\nline 2", tmp_path, tmp_path / "h", T).argv

def test_claude_has_no_turn_cap_and_uses_xhigh(tmp_path):
    c = command("claude", "x", tmp_path, tmp_path / "h", T)
    assert "--max-turns" not in c.argv and c.env["CLAUDE_CODE_EFFORT_LEVEL"] == "xhigh"
    assert c.env["ANTHROPIC_BASE_URL"] == "http://mac-studio:8585"

def test_prepare_writes_only_inside_home(tmp_path):
    for name in HARNESSES: prepare(name, tmp_path / "h", T)
    assert "xhigh" in (tmp_path / "h/.dsh/settings.yaml").read_text()
    assert "http://mac-studio:8585/v1" in (tmp_path / "h/.pi/agent/models.json").read_text()

def test_unknown_harness_raises():
    with pytest.raises(KeyError): command("codex", "x", Path("."), Path("."), T)
```

- [ ] **Step 2: Rodar.** Expected: FAIL com `ModuleNotFoundError: harness`.
- [ ] **Step 3: Implementar** `harness.py`.
- [ ] **Step 4: Rodar.** Expected: PASS.
- [ ] **Step 5: Commit.**

### Task 3: Runner de uma sessão

**Files:** Create `scripts/run_session.py`, `tests/test_session.py`, `tests/fake_harness.py`.

**Interfaces — Consumes:** `tasks.prompt`, `tasks.fresh_copy`, `tasks.TASKS`, `checks.check`, `harness.command`, `harness.prepare`, `harness.version`.

**Produces:**
- `run_session.record_path(out: Path, pack: str, harness: str, task: str, rep: int) -> Path` → `out/sessions/<pack>-<harness>-<task>-r<rep>.json`
- `run_session.run(harness: str, task: str, pack: str, rep: int, target: Target, out: Path, logs: Path, limit_s: int | None = None) -> dict`
- CLI: `run_session.py --harness H --task T --pack P --rep N --host HOST --port PORT --model ID [--limit-s S]`

O registro tem exatamente estes campos: `harness`, `harness_version`, `pack`, `task`, `rep`, `model_id`, `task_done`, `steps_passed`, `cheat`, `wall_s`, `exit`, `timeout`, `claimed_done`, `turns`, `input_tokens`, `output_tokens`. `claimed_done` é `not timeout and exit == 0`. `turns` e os tokens ficam `null` quando o harness não informa.

O runner inicia o harness em um grupo de processos novo, grava stdout e stderr em `logs/sessions/<nome>.log`, e no limite envia `SIGTERM` ao grupo, espera 10 s e envia `SIGKILL`. A cópia do repositório fica em `logs/work/<nome>/`, ou em `~/.cache/harness-delivery-2026-11/work/<nome>/` quando `logs/` está dentro de um repositório git, e o `HOME` da sessão em `logs/home/<nome>/`. O check roda depois que o grupo terminou.

O `fake_harness.py` é um script de teste que o runner dispara no lugar do harness real (`HARNESS_BIN_<NAME>`): aplica uma solução, dorme, sai com um código, ou deixa um filho vivo, conforme a variável `FAKE_MODE`.

- [ ] **Step 1: Testes que falham.**

```python
def test_solved_session_records_done(fake, tmp_path):
    r = run("pi", "T1", "k2", 1, T, tmp_path / "res", tmp_path / "logs")   # FAKE_MODE=solve
    assert (r["task_done"], r["timeout"], r["claimed_done"], r["exit"]) == (True, False, True, 0)
    assert json.loads(record_path(tmp_path / "res", "k2", "pi", "T1", 1).read_text()) == r

def test_record_has_exactly_the_spec_fields(fake, tmp_path):
    assert set(run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")) == FIELDS

def test_timeout_kills_process_group(fake, tmp_path):                      # FAKE_MODE=hang_with_child
    r = run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l", limit_s=2)
    assert (r["timeout"], r["task_done"], r["claimed_done"]) == (True, False, False)
    assert not pid_alive(int((tmp_path / "l/work/k2-pi-b-r1/child.pid").read_text()))

def test_claims_done_without_work(fake, tmp_path):                         # FAKE_MODE=exit0_no_work
    r = run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert (r["claimed_done"], r["task_done"]) == (True, False)

def test_record_holds_no_session_text(fake, tmp_path):                     # o fake imprime "SECRET-TRANSCRIPT"
    run("pi", "b", "k2", 1, T, tmp_path / "r", tmp_path / "l")
    assert "SECRET-TRANSCRIPT" not in "".join(p.read_text() for p in (tmp_path / "r").rglob("*.json"))
```

- [ ] **Step 2: Rodar.** Expected: FAIL com `ModuleNotFoundError: run_session`.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar.** Expected: PASS.
- [ ] **Step 5: Commit.**

### Task 4: Servidor do rig e smoke por harness

**Files:** Create `scripts/rig-server.sh`, `tests/test_rig_server.sh`; Modify `results/preflight.md`.

**Produces:** `rig-server.sh start <pack> [--print]`, `rig-server.sh stop`, `rig-server.sh env`. Roda no rig. `start` para o servidor do usuário, sobe `FLASHNEXT_SPLASH_TAG=1.6.1 FLASHNEXT_SPLASH_PACK=<pack> run-candidate.sh rc2 131072 --exec '<laço>'` em segundo plano, onde o laço grava `BASE_URL` e `MODEL_ID` em `logs/server.env` e espera o arquivo `logs/server.stop`. `stop` cria esse arquivo, espera a porta fechar e sobe de novo o servidor do usuário (`tools/scripts/serve-flashnext-splash.sh 256k`). `env` imprime `logs/server.env`. `<pack>` aceita `k2`, `z2` e `z4`.

- [ ] **Step 1: Teste que falha.** `tests/test_rig_server.sh`: `start z4 --print` contém `FLASHNEXT_SPLASH_PACK=z4`, `rc2 131072` e `--exec`; `start z9 --print` sai com 64.
- [ ] **Step 2: Rodar.** Expected: FAIL (arquivo ausente).
- [ ] **Step 3: Implementar** e rodar. Expected: PASS.
- [ ] **Step 4: Sincronizar o rig** por `git bundle`, como na swift-uncensored. Subir o `k2`.
- [ ] **Step 5: Smoke.** Para cada harness: `run_session.py --harness <h> --task b --pack smoke --rep 0 ...`. Expected: `task_done` verdadeiro. Gravar em `results/preflight.md` o `wall_s` e de onde vêm `turns` e tokens em cada harness.
- [ ] **Step 6: Servidor fora.** `rig-server.sh stop`, depois uma sessão por harness com `--limit-s 120`. Expected: a sessão termina em até 130 s, com `task_done` falso.
- [ ] **Step 7: Harness que falha.** Se um harness falhar no Step 5 ou 6 e a correção passar de 1 h de trabalho, ele sai da matriz. Gravar o motivo em `results/preflight.md`.
- [ ] **Step 8: Commit.** Os registros `smoke-*` não entram em `results/sessions/`.

### Task 5: Matriz e resumo

**Files:** Create `scripts/matrix.py`, `scripts/summarize.py`, `tests/test_matrix.py`, `tests/test_summarize.py`.

**Interfaces — Consumes:** `run_session.run`, `run_session.record_path`, `harness.HARNESSES`, `tasks.TASKS`.

**Produces:**
- `matrix.order(packs: tuple[str, str], harnesses: tuple[str, ...], out: Path) -> list[Session(pack, harness, task, rep)]`
- CLI: `matrix.py --packs k2,z4 --harnesses claude,opencode,dsh,pi [--dry-run]` troca o peso com `ssh vitor@mac-studio rig-server.sh` e chama `run_session.run`.
- `summarize.load(out: Path) -> list[dict]`
- `summarize.table(records) -> dict[(harness, pack), {"done": int, "n": int, "median_wall_done_s": float | None}]`
- `summarize.reserva(records, base="k2", cand="z4") -> dict` com `pass`, `done_base`, `done_cand`, `tolerance`, `ratio`
- `summarize.rank(records) -> list[tuple[str, int, float | None]]`
- `summarize.valido(records) -> bool`
- CLI: `summarize.py --out results --md results/summary.md --matrix-dir ../harness-matrix/results`

Ordem: repetição 1 roda o primeiro peso e depois o segundo; repetição 2 inverte. Dentro de um peso, as tarefas seguem `a b c d T1 T5 T7`, e a tarefa de índice `i` começa pelo harness de índice `i mod n`. `order` omite as sessões que já têm registro.

Regras: `tolerance = ceil(0.05 × n)` com `n` sessões do peso (3 para 56). `reserva.pass` exige `done_cand ≥ done_base − tolerance` e `ratio ≤ 1.25`, com `ratio` = mediana de `wall_s` das sessões prontas do candidato sobre a da base. `rank` ordena por tarefas prontas somando os pesos; quando a diferença é de até 1 tarefa, vence a menor mediana de `wall_s` das sessões prontas. `valido` é verdadeiro quando o peso base fecha pelo menos 1 tarefa `hard`.

- [ ] **Step 1: Testes que falham.**

```python
H = ("claude", "opencode", "dsh", "pi")

def test_order_has_112_sessions_and_mirrors_packs(tmp_path):
    o = order(("k2", "z4"), H, tmp_path)
    assert len(o) == 112 and len(set(o)) == 112
    assert [s.pack for s in o[::28]] == ["k2", "z4", "z4", "k2"]

def test_first_harness_rotates_by_task(tmp_path):
    o = order(("k2", "z4"), H, tmp_path)
    assert [s.harness for s in o[0:28:4]] == ["claude", "opencode", "dsh", "pi", "claude", "opencode", "dsh"]

def test_order_skips_recorded_sessions(tmp_path):
    record_path(tmp_path, "k2", "claude", "a", 1).parent.mkdir(parents=True)
    record_path(tmp_path, "k2", "claude", "a", 1).write_text("{}")
    assert len(order(("k2", "z4"), H, tmp_path)) == 111

def test_reserva_passes_at_three_fewer_and_fails_at_four():
    assert reserva(recs(k2_done=40, z4_done=37))["pass"] is True
    assert reserva(recs(k2_done=40, z4_done=36))["pass"] is False

def test_reserva_fails_when_slower_than_1_25x():
    assert reserva(recs(k2_done=40, z4_done=40, k2_wall=100, z4_wall=126))["pass"] is False

def test_tolerance_is_proportional_when_a_harness_leaves():
    assert reserva(recs(k2_done=30, z4_done=27, harnesses=H[:3]))["tolerance"] == 3   # ceil(0.05 × 42)

def test_rank_breaks_one_task_tie_by_time():
    r = rank(recs_by_harness({"pi": (20, 300), "claude": (21, 500), "dsh": (10, 100), "opencode": (15, 200)}))
    assert [h for h, *_ in r] == ["pi", "claude", "opencode", "dsh"]

def test_valido_needs_one_hard_task_on_base():
    assert valido(recs(k2_done=16, hard_done=0)) is False

def test_summary_names_the_two_repetition_caveat(tmp_path):
    assert "2 repetições" in render(recs(k2_done=40, z4_done=40))
```

- [ ] **Step 2: Rodar.** Expected: FAIL com `ModuleNotFoundError: matrix`.
- [ ] **Step 3: Implementar** `matrix.py` e `summarize.py`. O `summary.md` traz: tabela harness × peso, tabela por tarefa, contagem de `timeout`, de `claimed_done` sem `task_done` e de cada `cheat`, e o veredito das 3 regras.
- [ ] **Step 4: Rodar a suíte inteira.** Expected: PASS.
- [ ] **Step 5: `matrix.py --dry-run`.** Expected: 112 linhas, ou o total da matriz reduzida.
- [ ] **Step 6: Commit.**

### Task 6: Rodar a matriz

- [x] **Step 1:** Sincronizar o rig. Rodar `matrix.py` em segundo plano no MacBook, com `caffeinate -i`. Teto: 33 h.
- [x] **Step 2:** Se a fila parar, rodar o mesmo comando; a retomada pula as sessões gravadas.
- [x] **Step 3:** No fim: `rig-server.sh stop`, conferir que o servidor do usuário responde em 8585, contar os registros em `results/sessions/`.
- [x] **Step 4: Commit** dos registros.

### Task 7: Resultado

**Files:** `results/summary.md`, `bench/harness-matrix/results/<harness>/<modelo>.md` (um por par), `bench/swift-uncensored-2026-11/plan.md`, este `plan.md`.

- [x] **Step 1:** `summarize.py`. Ler o `summary.md` e conferir 3 células da tabela contra os registros.
- [x] **Step 2:** Auditar, nos logs, 5 sessões com `claimed_done` verdadeiro e `task_done` falso. Gravar no `summary.md` a contagem por causa, sem texto de sessão.
- [x] **Step 3:** Atualizar o status deste plano e apontar a Task 3 da swift-uncensored para o `summary.md`.
- [x] **Step 4:** Rodar a suíte inteira. Expected: PASS.
- [x] **Step 5: Commit.** Sem push nem PR sem pedido do usuário.
