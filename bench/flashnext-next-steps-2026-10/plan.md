# Flash-Next next steps 2026-10 — campaign runbook

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Executar, na ordem decidida pelo usuário em 2026-10-12, os testes 1, 2, 3, 5, 6, 7, 8 e 9 de [research/qwen38-flashnext-next-steps-20261012.md](../../research/qwen38-flashnext-next-steps-20261012.md): runtime novo (mlx-serve 26.10.2-pre-release.1) no driver secundário, Swift 1.5 a 256K/512K, bateria agêntica sem Docker, packs oMLX novos (Jundot refit, scottlowry Swift oQ4e, umixer mix6 v2), GGUF com MTP e `--ple-gpu` com prefix cache menor. Cada teste termina com uma decisão escrita em `results/` pelas regras do spec.

**Architecture:** A campanha reusa o driver `run-candidate.sh` de 2026-09 (servidor → `cache_probe.py` → `attach_memory.py`/`attach_mtp.py`) com braços novos num bloco próprio, e o `summarize_driver.py` para medianas, `T_turno` e gates. Scripts novos ficam em `bench/flashnext-next-steps-2026-10/scripts/`: wrapper `run-arm.sh`, fila `run-seq.sh`, gate térmico `idle-gate.sh`, instalação isolada `install-runtime.sh`, download fixado `fetch_pack.py`, tabela e decisão `decide.py`, sonda de thinking reenviado `think_turn_probe.py`, sondas agênticas `agent_probes.py`, bateria de qualidade `run-battery.sh` (envolve o `ab-battery.sh` da campanha Swift e o `degeneration_sweep.py`) e launcher GGUF `run-llama-flashnext.sh`.

**Tech Stack:** bash 3.2 (o do rig), Python 3 (stdlib; `huggingface_hub` do venv `~/LocalProjects/local-llms/.venv`), pytest via `uv run`, mlx-serve 26.10.1 e 26.10.2-pre-release.1, oMLX 0.7.1.dev1, llama.cpp b11569, macmon 0.7.2, gh.

**Spec:** research/qwen38-flashnext-next-steps-20261012.md

## Global Constraints

- Rig: Mac Studio M4 Max 128 GB (`ssh vitor@mac-studio`); checkout do repo no rig: `~/LocalProjects/local-llms`; um modelo servido por vez.
- Runtimes isolados em `~/.local/opt/qwen38/`: `mlx-serve-v26.10.1/mlx-serve` (referência), `mlx-serve-v26.10.2-pre-release.1/mlx-serve`, `omlx-v0.7.1.dev1/`, `llama-b11569/`; `~/.local/bin` não muda nesta campanha (prerelease).
- Drivers: principal `w1` = `Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` `13839b7`; secundário `n2` = `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw` `dafff5c`. Referências medidas no 26.10.1: `n2` 8.1 / 8.9 s, `w1` 7.9 / 8.6 s (`T_turno` a 32K / 128K).
- Métrica: `T_turno = TTFT(tool_turn) + 512 / mediana(decode quente de identical, append, tool_turn)`, 3 reps a 32K e 128K (`middle_mutation` 1 rep), calculada por `summarize_driver.py`.
- Gates de todo braço de velocidade: zero HTTP 4xx/5xx; needles corretas (truncado não é falha); hit ≥ 0.90 em `append` e `tool_turn`; swap Δ ≤ 0.5 GB; `[spec-stats]` no boot log (braços mlx-serve). Wired > 102 GB é alerta, não gate.
- Regra de runtime (prerelease, proposta do spec): adotar o 26.10.2-pre só com `T_turno ≤ 0.97 ×` 26.10.1 nas duas bandas; ±3% mantém o 26.10.1.
- Regra de pesos: paridade `|r − 1| ≤ 0.03`. Troca de driver: só com `T_turno ≤ 0.97 × w1` a 32K e a 128K. `--ple-gpu`: `T_turno ≤ 0.95 ×` controle a 128K.
- Sampling: perfil thinking do vendor, `temperature 1.0`, `top_p 0.95`, `top_k 20`, `presence_penalty 0`; `reasoning_effort` sempre explícito (`xhigh`, salvo o sweep do 3d). O template aceita só `xhigh`, `medium` e `low`.
- Probe: `cache_probe.py`, fixture `audit_retrieval`, needles 10/50/90, `max_tokens` 4096, cenários `cold → identical → append → middle_mutation → tool_turn`.
- Protocolo térmico: parar o driver diário; ≥ 82 GB livres antes de subir um braço; 10 min ociosos e GPU < 50 °C entre bandas (`scripts/idle-gate.sh`); 120 s entre braços (`scripts/run-seq.sh`); ordem alterna (32K: ref → cand; 128K: cand → ref).
- Harness: o `run-candidate.sh` apaga `~/.mlx-serve/kv-cache` antes de subir, espera até 30 s a porta liberar (senão aborta sem matar nada) e, no fim, mata o que escuta na porta do servidor que ele subiu.
- Disco: `df -g /` antes de cada download; #5–#8 somam ~444 GB; o `fetch_pack.py` recusa baixar com menos de download + 150 GB livres (100 GB do tier de disco do prefix cache + 50 GB de margem).
- Terminal-Bench (teste #4): adiado.
- Idioma: prosa em pt-BR; comandos, flags, código, comentários e mensagens de git em inglês.
- Commits: mensagem `bench(flashnext): ...` terminando com a linha `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Testes: `uv run --no-project --with pytest python -m pytest <caminho> -q`.

## Review Focus

1. **Binário errado ou string de versão diferente.** O `run-candidate.sh` compara `mlx-serve --version` com `MLX_SERVE_EXPECTED_VERSION` e sai com 65 se diferir; um tarball com outro layout deixa o binário fora do caminho. Checado no Task 0 Step 6 (versão gravada em `results/mlx-serve-26102-version.txt` e conferida contra o `run-candidate.sh` no Step 13) e no smoke do Task 1 Step 3 (`/props` com `version`).
2. **oMLX 0.7.1.dev1 ignora as variáveis `OMLX_*` do launcher.** O release removeu ~150 variáveis; se `OMLX_BASE_PATH`, `OMLX_MODEL_DIR`, `OMLX_PORT` ou `OMLX_CACHE_ENABLED` sumiram, o servidor sobe com base path, porta ou cache default e mede outra config. Checado no Task 0 Step 9 (grep no pacote instalado e `--help`) e no smoke do Task 5 Step 5 (porta 8000, `settings.json` lido, linha `PLE forced to SSD`).
3. **Servidor estranho na porta, cache quente ou sessões misturadas.** O driver diário na 11234 faz o braço abortar; um `kv-cache` de disco de outra sessão deixa o `cold` quente; JSONL de duas sessões no mesmo glob mistura medianas. Checado no Step "Parar o driver diário" de cada task, no `idle-gate.sh` (recusa porta ocupada) e no aviso `mistura session_id` do `summarize_driver.py` que o `decide.py` repassa no stderr.
4. **Reasoning sem efeito ou effort inválido.** A campanha Swift mediu tool-calling com ~110 tokens e `reasoning_chars` `n/d`; um effort `high` faz o template levantar exceção. Checado no Task 3 Step 9 (gate `reasoning mediano (chars)` > 0 no 3f) e nos `choices` de `agent_probes.py`/`think_turn_probe.py` (`xhigh`, `medium`, `low`).
5. **Disco cheio no meio de um download ou do tier de KV.** Um pack de 106–125 GB com menos de 100 GB sobrando quebra o prefix cache de disco e os runs de 512K. Checado no Task 0 Step 4 (`df -g /`), no `--dry-run` do `fetch_pack.py` antes de cada download (Tasks 5, 6, 7, 8) e na reserva de 150 GB do script.

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
| --- | --- | --- |
| `bench/flashnext-next-steps-2026-10/plan.md` | Create | este runbook |
| `bench/flashnext-next-steps-2026-10/scripts/run-arm.sh` | Create (pronto) | wrapper do `run-candidate.sh`, saída em `results/` e `logs/` da campanha |
| `bench/flashnext-next-steps-2026-10/scripts/run-seq.sh` | Create (pronto) | fila `arm:ctx:reps:tag[:yarn]`, 120 s entre braços, `--dry-run` |
| `bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh` | Create (pronto) | 10 min ociosos, GPU < 50 °C (macmon), ≥ 82 GB livres, portas livres |
| `bench/flashnext-next-steps-2026-10/scripts/install-runtime.sh` | Create (pronto) | instala mlx-serve 26.10.2-pre, oMLX 0.7.1.dev1, llama.cpp b11569 com SHA256 conferido |
| `bench/flashnext-next-steps-2026-10/scripts/fetch_pack.py` | Create (pronto) | download fixado em revisão completa, hardlink por hash, reserva de disco, recibo |
| `bench/flashnext-next-steps-2026-10/scripts/decide.py` | Create (pronto) | tabela fixa da campanha, razão de `T_turno`, `VERDICT` |
| `bench/flashnext-next-steps-2026-10/scripts/think_turn_probe.py` | Create (pronto) | `tool_turn` com e sem o thinking anterior; TTFT do 1º prompt pós-load |
| `bench/flashnext-next-steps-2026-10/scripts/agent_probes.py` | Create (pronto) | probes 3a, 3b, 3c, 3e; `summary`; `loops` |
| `bench/flashnext-next-steps-2026-10/scripts/run-battery.sh` | Create (pronto) | bateria t1 da campanha Swift + taxa de loop, por braço |
| `bench/flashnext-next-steps-2026-10/scripts/run-llama-flashnext.sh` | Create (pronto) | launcher GGUF: `GN`, `GM` (llama.cpp), `GX` (mlx-serve 26.10.2) |
| `bench/flashnext-next-steps-2026-10/tests/test_scripts.py` | Create (pronto) | testes dos scripts acima (dry-run, checkers, decide) |
| `bench/flashnext-next-steps-2026-10/tests/test_arms.py` | Create (Task 0) | testes dos braços novos no `run-candidate.sh` |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify (Task 0) | braços `n2x n2xd w1x w1q4 w1xq4 w1c8 w1xc8 w1p8 w1xp8 o1rm s1m o1x o1r x1 g0 g1 g1m` |
| `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh` | Modify (Task 0) | `QWEN38_MLX_EXTRA_ARGS` (só o braço `n2xd`) |
| `bench/qwen3.8-prefix-cache/scripts/run-omlx.sh` | Modify (Task 0) | arms `FR` e `FM` |
| `bench/qwen3.8-prefix-cache/config/omlx-arms.json` | Modify (Tasks 5 e 7) | modelos e arms `FR` (refit) e `FM` (mix6 v2) |
| `bench/degeneration/scripts/degeneration_sweep.py` | Modify (Task 0) | config `vendor_t1_xhigh` |
| `tools/scripts/serve-flashnext-daily-driver.sh` | Modify (Tasks 1, 2) | binário do perfil diário (se o 26.10.2 for adotado); pack do perfil `512k` (se o Swift falhar) |
| `docs/models/qwen3.8-flash-next.md`, `bench/qwen38-flash-next/references.md` | Modify (Task 10) | resultados da campanha |

"Pronto" = o arquivo já foi escrito junto com este plano e passa em `tests/test_scripts.py`.

## Braços

| braço | pesos | runtime | task |
| --- | --- | --- | --- |
| `n2` | iQ-MLX-4.7bpw `dafff5c` | mlx-serve 26.10.1 | 1 (referência) |
| `n2x` | iQ-MLX-4.7bpw `dafff5c` | mlx-serve 26.10.2-pre-release.1 | 1, 3 |
| `n2xd` | iQ `dafff5c` + profundidade MTP | mlx-serve 26.10.2-pre | 1 (opcional) |
| `w1` / `w1x` | Swift 1.5 `13839b7` | 26.10.1 / 26.10.2-pre | 1, 2, 3, 5, 6, 8 |
| `w1q4` / `w1xq4` | Swift 1.5 + KV 4-bit + YaRN 2.0 | 26.10.1 / 26.10.2-pre | 2 (512K) |
| `w1c8` / `w1xc8` | Swift 1.5, prefix cache 8 GB | 26.10.1 / 26.10.2-pre | 9 (controle) |
| `w1p8` / `w1xp8` | Swift 1.5, prefix cache 8 GB + `--ple-gpu` | 26.10.1 / 26.10.2-pre | 9 |
| `o1x` | Jundot oQ4e `2615fc0` | oMLX 0.7.1.dev1 (arm `FN`) | 5 |
| `o1r` | Jundot oQ4e refit `c4ddfb5` | oMLX 0.7.1.dev1 (arm `FR`) | 5, 7 |
| `o1rm` | Jundot oQ4e refit `c4ddfb5` | mlx-serve 26.10.2-pre | 5 |
| `s1m` | scottlowry Swift 1.5 oQ4e `e8ed008` | mlx-serve 26.10.2-pre | 6 |
| `x1` | umixer oQ4e-mix6-mtp-v2 (HEAD no download) | oMLX 0.7.1.dev1 (arm `FM`) | 7 |
| `g0` / `g1` | ggml-org IQ4_NL + MTP Q8_0 (HEAD no download) | llama.cpp b11569 sem / com `draft-mtp` | 8 |
| `g1m` | ggml-org IQ4_NL + MTP Q8_0 | mlx-serve 26.10.2-pre (llama.cpp embutido) | 8 |

Depois do Task 1, `results/driver-arms.env` fixa os braços do runtime vencedor: `W1`, `N2`, `W1Q4`, `W1C8`, `W1P8` e `RT`. Os Tasks 2, 3, 5, 6, 8 e 9 leem esse arquivo.

## Modelo de resultados

Todo `results/etapa<N>-*.md` de velocidade começa com o título da etapa e a data, traz a tabela fixa gerada pelo `decide.py` e termina com `## Veredito` (uma frase com a decisão e as razões numéricas) e `## Leitura` (o que mudou, o que surpreendeu, limites). A tabela fixa é:

```
| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
```

`warm TTFT` é a mediana do `tool_turn`; `hit` é `append / tool_turn`; `needles` é corretos/registros, com os truncados entre parênteses. Abaixo da tabela, o `decide.py` lista o livre mínimo e os gates por linha e, com `--base/--cand`, a razão de `T_turno` e a linha `VERDICT: pass` ou `VERDICT: fail (<razões>)`.

---

### Task 0: Pré-voo, runtimes e harness

**Files:**
- Create: `bench/flashnext-next-steps-2026-10/tests/test_arms.py`
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`, `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh`, `bench/qwen3.8-prefix-cache/scripts/run-omlx.sh`, `bench/degeneration/scripts/degeneration_sweep.py`
- Results: `results/etapa0-preflight.md`, `results/install-runtimes.md`, `results/mlx-serve-26102-version.txt`, `results/mlx-serve-26102-help.diff`, `results/omlx-0711-env.txt`

**Braços:** nenhum servidor sobe neste task.

| item | o que confere |
| --- | --- |
| disco | `df -g /`, `du` da raiz de modelos |
| runtimes | inventário de `~/.local/opt/qwen38/` e `~/.local/bin` |
| template | default de `reasoning_effort` no `chat_template.jinja` |
| oMLX | variáveis `OMLX_*` do launcher no 0.7.1.dev1 |

- [ ] **Step 1: Publicar o plano e os scripts num branch (na máquina onde o plano foi escrito)**

```bash
cd ~/LocalProjects/macstudio-local-llm
git checkout -b bench/flashnext-next-steps-2026-10
git add research/qwen38-flashnext-next-steps-20261012.md \
  bench/flashnext-next-steps-2026-10/plan.md bench/flashnext-next-steps-2026-10/scripts bench/flashnext-next-steps-2026-10/tests
git commit -m "bench(flashnext): next-steps 2026-10 spec, runbook and campaign scripts

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push -u origin bench/flashnext-next-steps-2026-10
```

Expected: o commit lista o spec (`research/qwen38-flashnext-next-steps-20261012.md`, ainda não rastreado em 2026-10-13) e os arquivos de `bench/flashnext-next-steps-2026-10/`. As mudanças locais de outras pastas continuam fora do commit.

- [ ] **Step 2: Trazer o branch para o rig**

```bash
ssh vitor@mac-studio
cd ~/LocalProjects/local-llms
git status --short
git fetch origin && git checkout bench/flashnext-next-steps-2026-10 && git pull --ff-only
git -C tools/local-llm-bench-m4-32gb merge-base --is-ancestor a4a95bb HEAD && echo "submodule >= a4a95bb"
```

Expected: `git status` sem arquivos rastreados modificados; `submodule >= a4a95bb` (o runner grava `reasoning_chars` no tool-calling). Se o `git status` mostrar mudanças rastreadas, pare e pergunte ao usuário antes de trocar de branch.

- [ ] **Step 3: Rodar os testes dos scripts prontos**

```bash
cd ~/LocalProjects/local-llms
uv run --no-project --with pytest python -m pytest bench/flashnext-next-steps-2026-10/tests/test_scripts.py -q
```

Expected: `9 passed`.

- [ ] **Step 4: Disco e versões já medidas**

Regra do `AGENTS.md`: antes de testar uma versão, procurar a string em `bench/*/results/` e `docs/models/`.

```bash
cd ~/LocalProjects/local-llms
grep -rl -E "26\.10\.2|0\.7\.1\.dev1|c4ddfb5|e8ed008|mix6|b11569" bench/*/results docs/models || echo "no previous measurement"
```

Expected: `no previous measurement` (conferido em 2026-10-13).

```bash
df -g /
du -sh ~/.cache/local-llms/qwen3.8-prefix-cache/* | sort -h
du -sh ~/.mlx-serve/kv-cache 2>/dev/null
```

Expected do `df`: `Available` ≥ 600 (GB). Em 2026-10-13 o rig tinha 749 GB livres. Os downloads de #5–#8 somam ~444 GB e o tier de disco do prefix cache pede 100 GB. Com menos de 600 GB, rode os Tasks 5–8 em sequência e apague, antes do Task 7, o pack que o Task 5 declarar substituído (o `2615fc0`, 123 GB) — só com o OK do usuário.

- [ ] **Step 5: Inventário de runtimes**

```bash
ls ~/.local/opt/qwen38/
ls -la ~/.local/bin | grep -E 'mlx-serve|omlx|llama|mtplx|dspark'
~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve --version
~/.local/opt/qwen38/omlx-v0.7.0/bin/omlx --version
~/.local/opt/qwen38/llama-v0.2.0-b10566/llama-server --version 2>&1 | tail -2
/opt/homebrew/bin/macmon --version; /opt/homebrew/bin/gh --version | head -1
```

Expected (lido em 2026-10-13): `mlx-serve 26.10.1`, `0.7.0`, `version: 0.2.0-dev (build 10566, ...)`, `macmon 0.7.2`; `~/.local/bin/mlx-serve` → `mlx-serve-v26.10.1`. Ainda não existem `mlx-serve-v26.10.2-pre-release.1`, `omlx-v0.7.1.dev1` e `llama-b11569`.

- [ ] **Step 6: Instalar o mlx-serve 26.10.2-pre-release.1**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
mkdir -p $C/results
bash $C/scripts/install-runtime.sh mlx-serve 2>&1 | tee -a $C/results/install-runtimes.md
~/.local/opt/qwen38/mlx-serve-v26.10.2-pre-release.1/mlx-serve --version 2>&1 | sed -n 's/^mlx-serve //p' | head -1 \
  | tee $C/results/mlx-serve-26102-version.txt
```

Expected: `sha256 check: OK` e a versão `26.10.2-pre-release.1` em `mlx-serve-26102-version.txt`. Se o GitHub não publicar digest, o script sai com 65 e imprime o hash: confira com a página do release e rode de novo com `INSTALL_EXPECTED_SHA256=<o hash conferido>`. Se a versão impressa for outra string (por exemplo `26.10.2`), o Step 13 grava essa string no `run-candidate.sh`.

- [ ] **Step 7: Flags novas do 26.10.2-pre**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
OLD=~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve; NEW=~/.local/opt/qwen38/mlx-serve-v26.10.2-pre-release.1/mlx-serve
diff <("$OLD" --help 2>&1) <("$NEW" --help 2>&1) > $C/results/mlx-serve-26102-help.diff
grep -n -i -E 'mtp|depth|ssd|reason|think|gguf|llama|ple|prefix|draft' $C/results/mlx-serve-26102-help.diff
"$NEW" --help 2>&1 | grep -oE -- '--mtp[a-z-]*depth[a-z-]*' | head -1 | tee $C/results/mlx-serve-26102-depth-flag.txt
```

Expected: o diff lista as flags novas. `mlx-serve-26102-depth-flag.txt` tem a flag de profundidade da MTP ou fica vazio. Vazio = o Task 1 Step 10 não roda.

- [ ] **Step 8: Instalar o oMLX 0.7.1.dev1**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/install-runtime.sh omlx 2>&1 | tail -5 | tee -a $C/results/install-runtimes.md
```

Expected: a versão `0.7.1.dev1` e a versão do MLX. Se `omlx --version` imprimir outra string, troque `QWEN38_OMLX_EXPECTED_VERSION=0.7.1.dev1` no bloco `o1x|o1r|x1` do Step 12 por essa string.

- [ ] **Step 9: Variáveis `OMLX_*` e settings por modelo no 0.7.1.dev1**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
PY=~/.local/opt/qwen38/omlx-v0.7.1.dev1/bin/python
SP="$($PY -c 'import omlx, os; print(os.path.dirname(omlx.__file__))')"
{
  for v in OMLX_BASE_PATH OMLX_MODEL_DIR OMLX_PORT OMLX_CACHE_ENABLED OMLX_MOE_EXPERT_OFFLOAD; do
    echo "$v files_in_package=$(grep -rl "$v" "$SP" | wc -l | tr -d ' ')"
  done
  echo "repo_scripts_using_OMLX_MOE_EXPERT_OFFLOAD=$(grep -rl OMLX_MOE_EXPERT_OFFLOAD bench tools/scripts fixes 2>/dev/null | wc -l | tr -d ' ')"
  $PY - <<'EOF'
import inspect
import omlx.model_settings as ms
src = inspect.getsource(ms)
print("SETTINGS_VERSION", getattr(ms, "SETTINGS_VERSION", None))
print("qwen4_ple_ssd_offload_known", "qwen4_ple_ssd_offload" in src, "mtp_enabled_known", "mtp_enabled" in src)
EOF
  ~/.local/opt/qwen38/omlx-v0.7.1.dev1/bin/omlx serve --help 2>&1 | grep -E -- '--base-path|--model-dir|--port|--memory-guard'
} | tee $C/results/omlx-0711-env.txt
```

Expected: `files_in_package` ≥ 1 para `OMLX_BASE_PATH`, `OMLX_MODEL_DIR`, `OMLX_PORT` e `OMLX_CACHE_ENABLED` (as quatro que `run-omlx.sh` usa); `OMLX_MOE_EXPERT_OFFLOAD` 0 no pacote e 0 nos scripts do repo; `SETTINGS_VERSION 1`; `qwen4_ple_ssd_offload_known True`.

Se alguma das quatro variáveis tiver 0 e o `--help` listar `--base-path`, `--model-dir` e `--port`, aplique em `bench/qwen3.8-prefix-cache/scripts/run-omlx.sh`, logo depois da linha `COMMAND=(env "OMLX_BASE_PATH=...`:

```bash
# oMLX 0.7.1.dev1 removed most OMLX_* variables: pass the same values as flags when asked to.
if [[ -n "${QWEN38_OMLX_CLI_FLAGS:-}" ]]; then
  COMMAND+=(--base-path "$OMLX_BASE_PATH" --model-dir "$OMLX_MODEL_DIR" --port "$OMLX_PORT")
fi
```

e acrescente `QWEN38_OMLX_CLI_FLAGS=1` ao último `export` do bloco `o1x|o1r|x1` do Step 12. Se `SETTINGS_VERSION` não for 1 ou `qwen4_ple_ssd_offload_known` for `False`, pare: o `omlx_config.py` gera um `model_settings.json` que o 0.7.1.dev1 lê de outro jeito; registre em `omlx-0711-env.txt` e pergunte ao usuário antes do Task 5.

- [ ] **Step 10: Escrever o teste dos braços (falha)**

`bench/flashnext-next-steps-2026-10/tests/test_arms.py`:

```python
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
RUN_ARM = HERE / "scripts" / "run-arm.sh"
ROOT = Path.home() / ".cache/local-llms/qwen3.8-prefix-cache"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
SWIFT = "Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"
OQ4E = "Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
NEW = "mlx-serve-v26.10.2-pre-release.1/mlx-serve"
OLD = "mlx-serve-v26.10.1/mlx-serve"

def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "AB_"))}
    env.update(extra or {})
    return env

def show(cand, ctx="32768", *args, env=None):
    return subprocess.run(["bash", str(RUN_ARM), cand, ctx, *args, "--print"], capture_output=True, text=True,
                          env=_env(env), check=True).stdout

def server(out):
    lines = out.splitlines()
    return lines[[i for i, l in enumerate(lines) if l.startswith("launcher:")][0] + 1]

def test_n2x_is_n2_on_the_prerelease():
    x, ref = show("n2x"), show("n2")
    assert NEW in x and IQ in x and "--runtime-revision v26.10.2-pre-release.1 " in x
    assert server(x).replace(NEW, "BIN") == server(ref).replace(OLD, "BIN")

def test_w1x_and_w1_differ_only_in_binary():
    assert server(show("w1x")).replace(NEW, "BIN") == server(show("w1")).replace(OLD, "BIN")
    assert SWIFT in show("w1x")

def test_512k_arms_use_4bit_kv_with_yarn():
    for cand, binary in (("w1q4", OLD), ("w1xq4", NEW)):
        out = show(cand, "524288", "--yarn", "2.0")
        assert binary in out and SWIFT in out
        assert "--kv-quant 4 " in out and "rope_type" in out and "-yarn2.0-kv4 " in out

def test_ple_arms_and_control_share_the_8gb_prefix_cache():
    c8, p8 = server(show("w1c8", "131072")), server(show("w1p8", "131072"))
    assert "--prefix-cache-mem 8GB" in c8 and "--ple-gpu" not in c8
    assert "--prefix-cache-mem 8GB" in p8 and "--ple-gpu" in p8
    assert p8.replace(" --ple-gpu", "") == c8
    assert NEW in show("w1xp8", "131072")

def test_extra_args_never_leak_into_other_arms():
    out = show("n2", env={"QWEN38_MLX_EXTRA_ARGS": "--bogus 1"})
    assert "--bogus" not in out

def test_n2xd_passes_the_depth_flag():
    out = show("n2xd", env={"FLASHNEXT_MTP_DEPTH_FLAG": "--mtp-depth", "FLASHNEXT_MTP_DEPTH": "2"})
    assert "--mtp-depth 2" in server(out) and "-mtpd2 " in out

def test_oq4e_refit_on_mlx_serve():
    out = show("o1rm")
    assert NEW in out and "Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5" in out

def test_gguf_arms():
    g1 = show("g1")
    assert "llama-b11569/llama-server" in g1 and "--spec-type draft-mtp" in g1 and "--port 8080" in g1
    assert "--parallel 1" in g1 and "--kv-unified" not in g1
    assert "--spec-type" not in show("g0")
    assert NEW in show("g1m") and "--port 11234" in show("g1m")

@pytest.mark.skipif(not (ROOT / OQ4E).is_dir(), reason="needs the oQ4e pack (rig only)")
def test_o1x_is_old_oq4e_on_omlx_0711():
    out = show("o1x")
    assert "omlx-v0.7.1.dev1/bin/omlx" in out and OQ4E in out and "--runtime-revision v0.7.1.dev1 " in out
```

- [ ] **Step 11: Rodar e ver a falha; fixar a linha de base dos testes antigos**

```bash
cd ~/LocalProjects/local-llms
uv run --no-project --with pytest python -m pytest bench/flashnext-next-steps-2026-10/tests/test_arms.py -q 2>&1 | tail -3
uv run --no-project --with pytest python -m pytest bench/engine-updates-2026-10/tests/test_arms.py \
  bench/swift15-flashnext-2026-10/tests/test_arm_w1.py -q 2>&1 | tail -3 | tee /tmp/flashnext-tests-before.txt
```

Expected: `test_arms.py` falha (`candidato desconhecido: n2x`, código 64). A segunda linha de base fica em `/tmp/flashnext-tests-before.txt` para o Step 16.

- [ ] **Step 12: Braços novos no `run-candidate.sh`**

Em `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`:

1. Na string de uso (linha 16), troque `|s27|s27g|s27r> <ctx>` por `|s27|s27g|s27r|n2x|n2xd|w1x|w1q4|w1xq4|w1c8|w1xc8|w1p8|w1xp8|o1rm|s1m|o1x|o1r|x1|g0|g1|g1m> <ctx>`.

2. Depois da linha `OPT="$HOME/.local/opt/qwen38"` (linha 56), acrescente:

```bash
# Campaign flashnext-next-steps-2026-10: runtimes installed by its scripts/install-runtime.sh and packs downloaded
# by its scripts/fetch_pack.py (directory names end in the full revision; pack_dir resolves the prefix).
MLXSERVE_26102="$OPT/mlx-serve-v26.10.2-pre-release.1/mlx-serve"
MLXSERVE_26102_VERSION=26.10.2-pre-release.1
OMLX_0711="$OPT/omlx-v0.7.1.dev1"
LLAMA_B11569="$OPT/llama-b11569/llama-server"
pack_dir() {
  local m=("$MODEL_ROOT/$1"*)
  if [[ -e "${m[0]}" ]]; then echo "${m[0]}"; else echo "$MODEL_ROOT/$1-MISSING"; fi
}
```

3. Depois da linha `unset QWEN38_MLX_OS_RESERVE_GIB` (linha 67), acrescente:

```bash
# Extra mlx-serve flags only for the n2xd arm (flashnext-next-steps-2026-10); a shell value never leaks.
unset QWEN38_MLX_EXTRA_ARGS
```

4. Logo antes da linha `  *) echo "candidato desconhecido: $CAND" >&2; exit 64 ;;`, acrescente:

```bash
  n2x|n2xd|w1x|w1q4|w1xq4|w1c8|w1xc8|w1p8|w1xp8|o1rm|s1m)
      # flashnext-next-steps-2026-10 on mlx-serve. An "x" in the arm = 26.10.2-pre-release.1, no "x" = 26.10.1.
      # n2x/w1x = n2/w1 flags on 26.10.2; n2xd = n2x + MTP depth (FLASHNEXT_MTP_DEPTH_FLAG, FLASHNEXT_MTP_DEPTH);
      # w1q4/w1xq4 = w1 + 4-bit KV with --yarn (the 512k launcher profile); w1c8/w1xc8 = prefix cache 8GB
      # (control of test #9); w1p8/w1xp8 = w1c8 + --ple-gpu; o1rm = Jundot oQ4e refit c4ddfb5 and
      # s1m = scottlowry Swift 1.5 oQ4e e8ed008, oMLX packs that 26.10.2 loads natively.
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
      if [[ "$CAND" == *x* || "$CAND" == o1rm || "$CAND" == s1m ]]; then
        export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102" MLX_SERVE_EXPECTED_VERSION="$MLXSERVE_26102_VERSION"
        REV="v$MLXSERVE_26102_VERSION"
      else
        export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26101" MLX_SERVE_EXPECTED_VERSION=26.10.1; REV=v26.10.1
      fi
      case "$CAND" in
        n2x|n2xd) MODEL_DIR="$IQDIR"; MODEL_REV=dafff5c3d8168c9d13275661153911096499a80a ;;
        w1*) MODEL_DIR="$SWIFTDIR"; MODEL_REV=13839b7191e0973ff9fea58232267c395b76c6c0 ;;
        o1rm) MODEL_DIR="$(pack_dir Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5)"; MODEL_REV="${MODEL_DIR##*-}" ;;
        s1m) MODEL_DIR="$(pack_dir scottlowry-Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp-e8ed008)"; MODEL_REV="${MODEL_DIR##*-}" ;;
      esac
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      unset QWEN38_MLX_PLE_GPU QWEN38_MLX_PREFIX_CACHE_MEM QWEN38_MLX_KV_QUANT QWEN38_MLX_CONFIG_OVERRIDES
      case "$CAND" in
        w1c8|w1xc8) export QWEN38_MLX_PREFIX_CACHE_MEM=8GB; REV="${REV}-pc8" ;;
        w1p8|w1xp8) export QWEN38_MLX_PREFIX_CACHE_MEM=8GB QWEN38_MLX_PLE_GPU=1; REV="${REV}-pc8-plegpu" ;;
        n2xd) export QWEN38_MLX_EXTRA_ARGS="${FLASHNEXT_MTP_DEPTH_FLAG:?n2xd needs FLASHNEXT_MTP_DEPTH_FLAG} ${FLASHNEXT_MTP_DEPTH:?n2xd needs FLASHNEXT_MTP_DEPTH}"
              REV="${REV}-mtpd${FLASHNEXT_MTP_DEPTH}" ;;
      esac
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8
        export QWEN38_MLX_CONFIG_OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${YARN},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"
        REV="${REV}-yarn${YARN}-kv8"
        if [[ "$CAND" == w1q4 || "$CAND" == w1xq4 ]]; then export QWEN38_MLX_KV_QUANT=4; REV="${REV%-kv8}-kv4"; fi
      fi ;;
  o1x|o1r|x1)
      # flashnext-next-steps-2026-10 on oMLX 0.7.1.dev1 (isolated venv): o1x = Jundot oQ4e 2615fc0 (launcher arm FN),
      # o1r = Jundot oQ4e refit c4ddfb5 (FR), x1 = umixer oQ4e-mix6-mtp-v2 (FM). FR and FM enter
      # config/omlx-arms.json after each download (Tasks 5 and 7 of the campaign plan).
      LAUNCHER="$HARNESS/run-omlx.sh"; PORT=8000; RUNTIME=omlx; REV=v0.7.1.dev1
      case "$CAND" in
        o1x) ARM=FN; MODEL_DIR="$OQ4E" ;;
        o1r) ARM=FR; MODEL_DIR="$(pack_dir Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5)" ;;
        x1) ARM=FM; MODEL_DIR="$(pack_dir umixer-Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2-)" ;;
      esac
      MODEL_REV="${MODEL_DIR##*-}"
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=omlx
      PROBE_PY="$OMLX_0711/bin/python"
      export OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_OMLX_BIN="$OMLX_0711/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.1.dev1 ;;
  g0|g1|g1m)
      # flashnext-next-steps-2026-10, test #8: ggml-org GGUF IQ4_NL + MTP head Q8_0. g0 = llama.cpp b11569 without
      # speculative decoding; g1 = --spec-type draft-mtp; g1m = mlx-serve 26.10.2 (embedded llama.cpp), same files.
      LAUNCHER="$REPO/bench/flashnext-next-steps-2026-10/scripts/run-llama-flashnext.sh"
      MODEL_DIR="$(pack_dir ggml-org-Qwen3.8-Flash-Next-GGUF-)"; MODEL_REV="${MODEL_DIR##*-}"
      TOKENIZER=""; METRICS=""; PROBE_PY=python3
      export QWEN38_GGUF_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      if [[ "$CAND" == g1m ]]; then
        ARM=GX; PORT=11234; RUNTIME=mlx-serve; SERVER_NAME=mlx-serve; REV="v$MLXSERVE_26102_VERSION-gguf"
        export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102" MLX_SERVE_EXPECTED_VERSION="$MLXSERVE_26102_VERSION"
      else
        PORT=8080; RUNTIME=llama.cpp; SERVER_NAME=llama-server; MODEL_ID_PREF=flashnext-gguf
        export QWEN38_LLAMA_SERVER_BIN="$LLAMA_B11569"
        if [[ "$CAND" == g0 ]]; then ARM=GN; REV=b11569; else ARM=GM; REV=b11569-mtp; fi
      fi ;;
```

5. Se `results/mlx-serve-26102-version.txt` (Step 6) não for `26.10.2-pre-release.1`, grave a string lida:

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
V="$(cat $C/results/mlx-serve-26102-version.txt)"
[ "$V" = 26.10.2-pre-release.1 ] || sed -i '' "s/^MLXSERVE_26102_VERSION=.*/MLXSERVE_26102_VERSION=$V/" \
  bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh
```

- [ ] **Step 13: `QWEN38_MLX_EXTRA_ARGS` no launcher do mlx-serve**

Em `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh`, logo depois do bloco `if [[ -n "${QWEN38_MLX_PLE_GPU:-}" ]]; then COMMAND+=(--ple-gpu); fi`, acrescente:

```bash
# Extra flags of one diagnostic arm (n2xd: MTP depth sweep on mlx-serve 26.10.2), split on spaces on purpose.
# run-candidate.sh unsets the variable for every other arm.
if [[ -n "${QWEN38_MLX_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  COMMAND+=($QWEN38_MLX_EXTRA_ARGS)
fi
```

Confira a versão gravada no driver:

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
grep -q "^MLXSERVE_26102_VERSION=$(cat $C/results/mlx-serve-26102-version.txt)$" \
  bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh && echo "version pin OK"
```

Expected: `version pin OK`.

- [ ] **Step 14: Arms `FR` e `FM` no launcher do oMLX**

Em `bench/qwen3.8-prefix-cache/scripts/run-omlx.sh`, troque `  I|J|K|L|M|N|O|T|U|W|X|FN) ;;` por `  I|J|K|L|M|N|O|T|U|W|X|FN|FR|FM) ;;` e, na mensagem de uso da linha seguinte, `{I|J|K|L|M|N|O|T|U|W|X}` por `{I|J|K|L|M|N|O|T|U|W|X|FN|FR|FM}`. As entradas de `config/omlx-arms.json` entram nos Tasks 5 e 7, depois do download (o nome do diretório usa a revisão completa).

- [ ] **Step 15: Config `vendor_t1_xhigh` na bateria de loop**

Em `bench/degeneration/scripts/degeneration_sweep.py`, logo depois da linha `    ("ctrl_t0.6",             {"temperature": 0.6}),`, acrescente:

```python
    # --- vendor thinking profile of Qwen3.8-Flash-Next (bench/flashnext-next-steps-2026-10) ---
    ("vendor_t1_xhigh",       {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0,
                               "reasoning_effort": "xhigh"}),
```

```bash
cd ~/LocalProjects/local-llms
python3 -c "import sys; sys.path.insert(0, 'bench/degeneration/scripts'); import degeneration_sweep as d; print([c for c in d.CONFIGS if c[0] == 'vendor_t1_xhigh'])"
```

Expected: `[('vendor_t1_xhigh', {'temperature': 1.0, 'top_p': 0.95, 'top_k': 20, 'presence_penalty': 0.0, 'reasoning_effort': 'xhigh'})]`.

- [ ] **Step 16: Rodar os testes**

```bash
cd ~/LocalProjects/local-llms
uv run --no-project --with pytest python -m pytest bench/flashnext-next-steps-2026-10/tests -q
uv run --no-project --with pytest python -m pytest bench/engine-updates-2026-10/tests/test_arms.py \
  bench/swift15-flashnext-2026-10/tests/test_arm_w1.py -q 2>&1 | tail -3 > /tmp/flashnext-tests-after.txt
diff /tmp/flashnext-tests-before.txt /tmp/flashnext-tests-after.txt && echo "no regression"
bash bench/qwen3.8-prefix-cache/tests/test_launchers.sh >/dev/null 2>&1; echo "launchers rc=$?"
```

Expected: `18 passed` em `tests/` no rig (fora do rig, o teste do `o1x` pula: `17 passed, 1 skipped`); `no regression`; `launchers rc` igual ao de antes da mudança (rode o mesmo comando com `git stash` se precisar comparar).

- [ ] **Step 17: Template de `reasoning_effort`**

```bash
cd ~/.cache/local-llms/qwen3.8-prefix-cache
for d in Dankpaws-Swift1.5-*13839b7* ddalcu-*iQ-MLX-4.7bpw-dafff5c* Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0*; do
  echo "$d: $(grep -o "reasoning_effort|default('[a-z]*')" "$d/chat_template.jinja") $(grep -o "Supported types are [a-z ,()]*" "$d/chat_template.jinja" | head -1)"
done
```

Expected (lido no rig em 2026-10-13): os três packs com `reasoning_effort|default('xhigh')` e `Supported types are xhigh (default), medium, and low`. O default é `xhigh`, como diz o card; a alegação de `medium` do HF #71 não vale para estes packs. Repita o grep nos packs novos depois de cada download (Tasks 5–8).

- [ ] **Step 18: Escrever `results/etapa0-preflight.md`**

Com as saídas dos Steps 4–9 e 17, escreva:

```
# Etapa 0 — pré-voo (<data do rig>)

| item | valor |
| --- | --- |
| disco livre (`df -g /`) | <Available> GB |
| mlx-serve referência | 26.10.1 (`~/.local/opt/qwen38/mlx-serve-v26.10.1`) |
| mlx-serve candidato | <conteúdo de mlx-serve-26102-version.txt>, SHA256 <hash> |
| flag de profundidade MTP | <conteúdo de mlx-serve-26102-depth-flag.txt ou "nenhuma"> |
| oMLX | 0.7.1.dev1, MLX <versão> |
| variáveis OMLX_* do launcher | <resumo de omlx-0711-env.txt> |
| default de reasoning_effort | xhigh nos três packs; aceitos: xhigh, medium, low |
| submódulo local-llm-bench-m4-32gb | <hash> (>= a4a95bb) |
```

Os campos entre `<>` vêm das saídas acima; nenhum fica em branco.

- [ ] **Step 19: Commit**

```bash
cd ~/LocalProjects/local-llms
git add bench/flashnext-next-steps-2026-10/tests/test_arms.py bench/flashnext-next-steps-2026-10/results \
  bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh \
  bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh bench/qwen3.8-prefix-cache/scripts/run-omlx.sh \
  bench/degeneration/scripts/degeneration_sweep.py
git commit -m "bench(flashnext): next-steps arms, 26.10.2-pre and oMLX 0.7.1.dev1 installs, preflight

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 1: mlx-serve 26.10.2-pre-release.1 × 26.10.1 no driver secundário (`n2`)

**Files:**
- Results: `results/n2-{8192,32768,131072}-t1.0-*.jsonl`, `results/n2x-{8192,32768,131072,262144}-t1.0-*.jsonl`, `results/think/*.jsonl`, `results/props/*.json`, `results/etapa1-runtime.md`, `results/driver-arms.env`
- Modify (se o 26.10.2 for adotado): `tools/scripts/serve-flashnext-daily-driver.sh`

**Braços:**

| braço | pesos | runtime | bandas | reps |
| --- | --- | --- | --- | --- |
| `n2` (referência, mesma sessão) | iQ `dafff5c` | 26.10.1 | 32K, 128K | 3 |
| `n2x` (candidato) | iQ `dafff5c` | 26.10.2-pre | 8K (smoke), 32K, 128K, 256K (informativo) | 1 / 3 / 3 / 1 |
| `n2`, `n2x` | iQ | os dois | sonda de thinking reenviado a 32K e 128K | 3 por modo |
| `n2xd` (opcional) | iQ | 26.10.2-pre + profundidade MTP 1/2/3 | 32K | 3 |
| `w1`, `w1x` (só se adotar) | Swift 1.5 | os dois | 32K, 128K | 3 |

Estimativa (não medida): ~1 dia de rig.

- [ ] **Step 1: Parar o driver diário e conferir que nada mede**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && ps -o pid=,command= -p $P && kill $P
sleep 10; lsof -nP -iTCP:11234 -sTCP:LISTEN || echo "port 11234 free"
pgrep -fl 'run-candidate|cache_probe|ab-battery|agent_probes|think_turn_probe' || echo "no run active"
```

Expected: `port 11234 free` e `no run active`. Se outra sessão estiver medindo, pare e espere.

- [ ] **Step 2: Gate térmico**

```bash
cd ~/LocalProjects/local-llms && bash bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh --minutes 0
```

Expected: `idle-gate: ready ... gpu=<menos de 50>C free=<pelo menos 82>GB`. O primeiro gate do dia usa `--minutes 0`; entre bandas use o default de 10 min.

- [ ] **Step 3: Smoke 8K do `n2x`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/run-arm.sh n2x 8192 --scenarios cold,identical,tool_turn --tag smoke
grep -c '\[spec-stats\]' $C/logs/n2x-8192-t1.0-smoke-boot.log
python3 -c "import json; d=json.load(open('$C/results/props/n2x-8192-t1.0-smoke.json')); print(d.get('version'), d.get('mtp'), d.get('kv_quant'))"
```

Expected: `>>> n2x-8192-t1.0-smoke: OK`; contagem de `[spec-stats]` > 0; `/props` com a versão do 26.10.2 e `mtp.loaded=true`. Erro de boot ou de versão: pare e leia `logs/n2x-8192-t1.0-smoke-boot.log`.

- [ ] **Step 4: Banda 32K (ref → cand)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh n2:32768:3:e1 n2x:32768:3:e1 2>&1 | tee $C/logs/etapa1-32k.log
```

Expected: `exit[n2@32768]=0` e `exit[n2x@32768]=0`; 13 registros em cada `results/<braço>-32768-t1.0-e1.jsonl`.

- [ ] **Step 5: Banda 128K (cand → ref)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh n2x:131072:3:e1 n2:131072:3:e1 2>&1 | tee $C/logs/etapa1-128k.log
```

Expected: `exit[...]=0` nos dois; 13 registros por arquivo.

- [ ] **Step 6: 256K informativo do `n2x`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh n2x:262144:1:e1
```

Expected: 5 registros. Referência: `n2@26.10.1` a 256K = 9.8 s (1 rep, `bench/engine-updates-2026-10/results/n2-262144-t1.0-fnx256.jsonl`). Não entra na regra de adoção.

- [ ] **Step 7: Sonda de thinking reenviado e 1º prompt pós-load**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
mkdir -p $C/results/think
for spec in "n2 32768" "n2x 32768" "n2x 131072" "n2 131072"; do
  set -- $spec
  caffeinate -i bash $C/scripts/run-arm.sh $1 $2 --tag think --exec \
    "python3 $C/scripts/think_turn_probe.py --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm $1 --context $2 --repeat 3 --output $C/results/think/$1-$2.jsonl"
  echo "exit[$1@$2]=$?"; sleep 120
done
python3 $C/scripts/think_turn_probe.py --summary $C/results/think/*.jsonl
```

Expected: por arquivo, 1 registro `first_after_load` e 12 registros (`turn1` e `tool_turn`, modos `resend` e `drop`, 3 reps). Leitura: no `n2x`, o `tool_turn` `resend` deve ter `cached` maior que o `drop` (o servidor reaproveita o thinking do `turn1`); no `n2`, os dois modos devem cachear só a base. O TTFT de `first_after_load` do `n2x` contra o do `n2` mede a trava pós-load.

- [ ] **Step 8: Decisão de runtime**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
{ echo "# Etapa 1 — mlx-serve 26.10.2-pre-release.1 × 26.10.1 no n2 ($(date +%F))"; echo
  python3 $C/scripts/decide.py --glob 'n2-*-t1.0-e1.jsonl' --glob 'n2x-*-t1.0-e1.jsonl' \
    --base n2 --cand n2x --ctx 32768,131072 --mode le --threshold 0.97 --title "32K e 128K, 3 reps"
  echo; python3 $C/scripts/decide.py --glob 'n2x-262144-t1.0-e1.jsonl' --title "256K informativo (n2@26.10.1: 9.8 s)"
  echo; echo "## Thinking reenviado e 1º prompt pós-load"; echo
  python3 $C/scripts/think_turn_probe.py --summary $C/results/think/*.jsonl
} > $C/results/etapa1-runtime.md
grep '^VERDICT' $C/results/etapa1-runtime.md
```

Expected: a tabela fixa do modelo de resultados com `n2` e `n2x` a 32K e 128K, a razão por banda e uma linha `VERDICT`. `VERDICT: pass` = adotar o 26.10.2-pre para o `n2` (`≤ 0.97 ×` nas duas bandas e todos os gates). Qualquer `fail` mantém o 26.10.1 (é prerelease; empate de ±3% mantém o incumbente).

- [ ] **Step 9: Se adotado — smoke de gates do `w1` no 26.10.2-pre**

Só se o Step 8 deu `VERDICT: pass`.

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh w1:32768:3:e1w w1x:32768:3:e1w
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh w1x:131072:3:e1w w1:131072:3:e1w
{ echo; python3 $C/scripts/decide.py --glob 'w1-*-t1.0-e1w.jsonl' --glob 'w1x-*-t1.0-e1w.jsonl' \
    --base w1 --cand w1x --ctx 32768,131072 --mode le --threshold 1.03 --title "Smoke de gates do w1 no 26.10.2-pre"
} >> $C/results/etapa1-runtime.md
tail -1 $C/results/etapa1-runtime.md
```

Expected: `VERDICT: pass` = o driver principal migra para o 26.10.2-pre (gates e regra de runtime do repo, `≤ 1.03 ×`). `fail` = o `w1` fica no 26.10.1 mesmo com o `n2` adotado; registre isso no `## Veredito`.

- [ ] **Step 10 (opcional): profundidade da MTP**

Só se `results/mlx-serve-26102-depth-flag.txt` (Task 0 Step 7) não estiver vazio.

```bash
( cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
FLAG="$(cat $C/results/mlx-serve-26102-depth-flag.txt)"
[ -n "$FLAG" ] || { echo "no MTP depth flag in 26.10.2-pre; step skipped"; exit 0; }
bash $C/scripts/idle-gate.sh
for d in 1 2 3; do
  FLASHNEXT_MTP_DEPTH_FLAG="$FLAG" FLASHNEXT_MTP_DEPTH=$d caffeinate -i bash $C/scripts/run-arm.sh n2xd 32768 --repeat 3 --tag d$d
  echo "exit[n2xd d=$d]=$?"; sleep 120
done
{ echo; python3 $C/scripts/decide.py --glob 'n2x-32768-t1.0-e1.jsonl' --glob 'n2xd-32768-t1.0-d*.jsonl' \
    --title "Profundidade da MTP a 32K ($FLAG 1/2/3; n2x = default)"; } >> $C/results/etapa1-runtime.md )
```

Expected: os três runs agrupam no mesmo braço `n2xd`; o `decide.py` imprime o aviso `mistura session_id` e mostra a mediana dos três. Para ler cada profundidade, rode `python3 $C/scripts/decide.py --glob 'n2xd-32768-t1.0-d1.jsonl'` (e `d2`, `d3`) e copie as três linhas para a seção. Informativo: nenhuma decisão depende dele.

- [ ] **Step 11: Fixar os braços do runtime vencedor**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
N=$(grep -c '^VERDICT: pass' $C/results/etapa1-runtime.md)
if [ "$N" -ge 2 ]; then
  printf 'W1=w1x\nN2=n2x\nW1Q4=w1xq4\nW1C8=w1xc8\nW1P8=w1xp8\nRT=26.10.2-pre-release.1\n' > $C/results/driver-arms.env
elif [ "$N" -eq 1 ]; then
  printf 'W1=w1\nN2=n2x\nW1Q4=w1q4\nW1C8=w1c8\nW1P8=w1p8\nRT=26.10.1\n' > $C/results/driver-arms.env
else
  printf 'W1=w1\nN2=n2\nW1Q4=w1q4\nW1C8=w1c8\nW1P8=w1p8\nRT=26.10.1\n' > $C/results/driver-arms.env
fi
cat $C/results/driver-arms.env
```

Expected: `N=2` (n2 e w1 adotam), `N=1` (só o n2 adota; o Step 9 falhou) ou `N=0` (nada muda). `RT` é o runtime do driver principal.

- [ ] **Step 12: Se o `w1` migrou — launcher diário**

Só se `RT=26.10.2-pre-release.1`. Em `tools/scripts/serve-flashnext-daily-driver.sh`, troque a linha do `BIN` por:

```bash
BIN="${FLASHNEXT_BIN:-$HOME/.local/opt/qwen38/mlx-serve-v26.10.2-pre-release.1/mlx-serve}"
```

e a primeira linha do cabeçalho por `# Start the Qwen3.8-Flash-Next daily driver: Swift 1.5 (Dankpaws MLX-4.7bpw) on mlx-serve 26.10.2-pre-release.1.`, com uma linha abaixo: `# Runtime promoted by bench/flashnext-next-steps-2026-10 (Task 1); rollback: FLASHNEXT_BIN=~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve`. O symlink `~/.local/bin/mlx-serve` fica no 26.10.1 até a release estável.

```bash
cd ~/LocalProjects/local-llms && bash tools/scripts/serve-flashnext-daily-driver.sh --print | grep -o 'mlx-serve-v[^/]*'
```

Expected: `mlx-serve-v26.10.2-pre-release.1`.

- [ ] **Step 13: Completar `results/etapa1-runtime.md`**

Acrescente ao arquivo, depois das tabelas geradas: `## Veredito` (adotado ou não, as duas razões de `T_turno`, se o `w1` migrou) e `## Leitura` com quatro pontos: a aceitação da MTP e o decode do `n2x` contra o `n2`; o TTFT do 1º prompt pós-load nos dois runtimes; a diferença de `cached` entre `resend` e `drop` no `n2x`; o 256K do `n2x` contra os 9.8 s do 26.10.1.

- [ ] **Step 14: Relançar o driver diário e fazer o commit**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
sleep 60; curl -fsS http://127.0.0.1:11234/v1/models | head -c 200; echo
du -h $C/results/*.jsonl $C/results/think/*.jsonl | sort -h | tail -3
git add $C/results tools/scripts/serve-flashnext-daily-driver.sh
git commit -m "bench(flashnext): Task 1 - mlx-serve 26.10.2-pre vs 26.10.1 on the secondary driver

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Expected: `/v1/models` responde com o id do Swift; nenhum JSONL acima de ~1 MB.

---

### Task 2: Swift 1.5 a 256K e 512K no runtime vencedor

**Files:**
- Results: `results/<W1>-262144-t1.0-e2.jsonl`, `results/<W1Q4>-524288-t1.0-e2.jsonl`, `results/etapa2-swift-long.md`
- Modify (se falhar): `tools/scripts/serve-flashnext-daily-driver.sh`

**Braços:**

| braço | config | contexto | reps | referência (iQ, 26.10.1) |
| --- | --- | --- | --- | --- |
| `$W1` | perfil diário, KV sem quantização | 262144 | 3 | 9.8 s (1 rep) |
| `$W1Q4` | perfil `512k`: YaRN 2.0 + `--kv-quant 4` | 524288 | 3 | 13.0 s, livre mínimo 0.05 GB, wired 113.9 GB |

Estimativa: ~3 h (o cold de 512K levou ~784 s por rep no iQ).

- [ ] **Step 1: Parar o driver diário e gate térmico**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
cd ~/LocalProjects/local-llms && bash bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh --minutes 0
df -g / | tail -1
```

Expected: `idle-gate: ready`; `Available` ≥ 100 GB (o tier de disco do prefix cache).

- [ ] **Step 2: 256K, 3 reps**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
caffeinate -i bash $C/scripts/run-seq.sh $W1:262144:3:e2 2>&1 | tee $C/logs/etapa2-256k.log
```

Expected: 13 registros em `results/$W1-262144-t1.0-e2.jsonl`.

- [ ] **Step 3: 512K, 3 reps (perfil `512k`)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh $W1Q4:524288:3:e2:2.0 2>&1 | tee $C/logs/etapa2-512k.log
```

Expected: 13 registros em `results/$W1Q4-524288-t1.0-e2.jsonl`.

- [ ] **Step 4: Recusas e telemetria no log**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
for f in $C/logs/$W1-262144-t1.0-e2-boot.log $C/logs/$W1Q4-524288-t1.0-e2-boot.log; do
  echo "$(basename $f): spec-stats=$(grep -c '\[spec-stats\]' $f) refused=$(grep -c -i -E 'PrefillDoesNotFit|prefill refused' $f) oom=$(grep -c -i -E 'OutOfMemory|GenerationOutOfMemory' $f)"
done
```

Expected: `spec-stats` > 0, `refused=0`, `oom=0` nos dois.

- [ ] **Step 5: Escrever `results/etapa2-swift-long.md`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
{ echo "# Etapa 2 — Swift 1.5 a 256K e 512K no mlx-serve $RT ($(date +%F))"; echo
  python3 $C/scripts/decide.py --glob "$W1-262144-t1.0-e2.jsonl" --glob "$W1Q4-524288-t1.0-e2.jsonl" \
    --title "256K (KV sem quantização) e 512K (YaRN 2.0 + KV 4-bit), 3 reps"
  echo; echo "Referência iQ no 26.10.1: 256K 9.8 s (1 rep); 512K 13.0 s, wired 113.9 GB, livre mínimo 0.05 GB (n2q4, 3 reps)."
} > $C/results/etapa2-swift-long.md
cat $C/results/etapa2-swift-long.md
```

Expected: a tabela fixa com as duas linhas e o livre mínimo de cada uma. **Passa** se, nas duas bandas: `HTTP errs` = 0, needles sem falha (`ok + truncados = 13`), `swap Δ` ≤ 0.5 GB, `spec-stats` > 0, `refused=0` e `oom=0` no Step 4.

- [ ] **Step 6: Aplicar a decisão ao perfil `512k`**

Se passou: em `tools/scripts/serve-flashnext-daily-driver.sh`, troque as duas linhas do comentário do `512k` que dizem `measured with the iQ pack ... not measured with Swift 1.5` por `#                    measured with Swift 1.5 in bench/flashnext-next-steps-2026-10 (Task 2, 3 reps): T_turno <valor> s, min free <valor> GB`, com os valores da tabela.

Se falhou: o perfil `512k` volta ao iQ. Logo depois da linha `MODEL="${FLASHNEXT_MODEL:-...}"`, acrescente:

```bash
# 512k keeps the iQ pack: Swift 1.5 failed the 512K gates (bench/flashnext-next-steps-2026-10/results/etapa2-swift-long.md).
if [[ "$PROFILE" == 512k && -z "${FLASHNEXT_MODEL:-}" ]]; then
  MODEL="$HOME/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
fi
```

```bash
cd ~/LocalProjects/local-llms && bash tools/scripts/serve-flashnext-daily-driver.sh 512k --print | grep -o -E 'Dankpaws[^ ]*|ddalcu[^ ]*'
```

Expected: o pack que a decisão escolheu.

- [ ] **Step 7: Veredito, driver diário e commit**

Acrescente `## Veredito` (passa ou falha, com o número que decidiu) e `## Leitura` (wired e livre mínimo do Swift contra o iQ; needles do KV4 como única checagem de qualidade; o YaRN estático degrada texto curto segundo o card, por isso o perfil 512k continua separado do diário).

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
git add $C/results tools/scripts/serve-flashnext-daily-driver.sh
git commit -m "bench(flashnext): Task 2 - Swift 1.5 at 256K and 512K

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Bateria agêntica de regressão sem Docker (3a–3f)

**Files:**
- Results: `results/agent/3{a,b,c,e}-*.jsonl`, `results/e3d/t1/<label>/*.jsonl`, `results/e3f/t1/<label>/*.jsonl`, `results/etapa3-agent.md`

**Braços:**

| probe | o que mede | braços | contexto do servidor | rodadas |
| --- | --- | --- | --- | --- |
| 3a contradição pós-tool | 20 turnos com `ls`/pytest conhecidos; `invented`, `missing`, `empty` | `$W1`, `$N2` | 131072 | 2 |
| 3b loop de contagem | 20 prompts "about N characters" (pt, en, ko); `finish_reason=length` com content vazio | `$W1`, `$N2` | 131072 | 2 |
| 3c degeneração longa | sessão com tool results de ~8K tokens até 200K; sequência de caractere repetido, heurística de loop, código errado | `$W1`, `$N2` | 262144 | 2 |
| 3d sweep de effort | 3a + GPQA 50 + LCB 50 (seed 42) em `xhigh`, `medium`, `low` | `$W1` | 131072 | 2 |
| 3e custo de trocar effort | 128K: `xhigh` → `xhigh` (controle) → `medium`/`low` (troca) → `xhigh` | `$W1` | 131072 | 2 por troca |
| 3f tool-calling com reasoning | jdhodges 40 + Veerman 12, `reasoning_effort xhigh` | `$W1`, `$N2` | 131072 | 2 |

Sampling do vendor em todas; `reasoning_effort` explícito; thinking reenviado entre turnos (preserve_thinking, default do card). Estimativa: ~1,5–2 dias.

Regras de decisão (propostas pelo spec):
- Se `$W1` exceder `$N2` em mais de 1 caso em 20 de loop (3b) ou de contradição (3a: `invented` + `missing` + `empty`), o driver volta a ser candidato a revisão.
- Qualquer `char_run` ("!!!!") no 3c bloqueia o uso em sessão longa até haver fix de runtime.
- O effort default do harness passa a ser o de menor tempo total cujo acerto fica dentro da margem G1 do `xhigh` (GPQA 3, LCB 3; 3a: `ok` ≥ `ok(xhigh)` − 1 por rodada).
- 3e: se o hit da troca ficar abaixo de 0.5, o harness deve fixar o effort por sessão.

- [ ] **Step 1: Parar o driver diário e gate térmico**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
cd ~/LocalProjects/local-llms && bash bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh --minutes 0
```

Expected: `idle-gate: ready`.

- [ ] **Step 2: Dry run das sondas**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
for s in contradiction charcount longsession effortswitch; do python3 $C/scripts/agent_probes.py $s --dry-run | head -c 300; echo; done
```

Expected: um JSON por sonda, com `reasoning_effort` e o sampling do vendor; nenhuma conexão.

- [ ] **Step 3: Smoke de 1 turno no `$W1`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
mkdir -p $C/results/agent
bash $C/scripts/run-arm.sh $W1 131072 --tag a3smoke --exec \
  "python3 $C/scripts/agent_probes.py contradiction --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm $W1 --rounds 1 --turns 2 --output $C/logs/3a-smoke.jsonl"
python3 $C/scripts/agent_probes.py summary $C/logs/3a-smoke.jsonl
```

Expected: 2 turnos com `verdict` registrado e `reasoning_chars` > 0 em pelo menos um. Se todo turno vier `error`, leia o `logs/$W1-131072-t1.0-a3smoke-boot.log` (o template pode recusar o `tools` ou o `reasoning_content` reenviado).

- [ ] **Step 4: 3a, 3b e 3e no `$W1` (uma subida)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
P="python3 $C/scripts/agent_probes.py"; A="--base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm $W1"
caffeinate -i bash $C/scripts/run-arm.sh $W1 131072 --tag a3 --exec \
  "rc=0; $P contradiction $A --rounds 2 --output $C/results/agent/3a-$W1.jsonl || rc=\$?;
   $P charcount $A --rounds 2 --output $C/results/agent/3b-$W1.jsonl || rc=\$?;
   $P effortswitch $A --context 131072 --switch-to medium --rounds 2 --output $C/results/agent/3e-$W1.jsonl || rc=\$?;
   $P effortswitch $A --context 131072 --switch-to low --rounds 2 --output $C/results/agent/3e-$W1.jsonl || rc=\$?; exit \$rc"
```

Expected: `>>> $W1-131072-t1.0-a3: OK`; `3a` com 42 linhas (40 turnos + 2 sessões), `3b` com 40, `3e` com 16.

- [ ] **Step 5: 3a e 3b no `$N2`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
P="python3 $C/scripts/agent_probes.py"; A="--base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm $N2"
caffeinate -i bash $C/scripts/run-arm.sh $N2 131072 --tag a3 --exec \
  "rc=0; $P contradiction $A --rounds 2 --output $C/results/agent/3a-$N2.jsonl || rc=\$?;
   $P charcount $A --rounds 2 --output $C/results/agent/3b-$N2.jsonl || rc=\$?; exit \$rc"
```

Expected: `3a` com 42 linhas e `3b` com 40.

- [ ] **Step 6: 3c (sessão até 200K) nos dois braços**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
for arm in $W1 $N2; do
  bash $C/scripts/idle-gate.sh
  caffeinate -i bash $C/scripts/run-arm.sh $arm 262144 --tag a3c --exec \
    "python3 $C/scripts/agent_probes.py longsession --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm $arm --rounds 2 --targets 150000,200000 --output $C/results/agent/3c-$arm.jsonl"
  echo "exit[3c $arm]=$?"
done
```

Expected: por braço, 2 sessões que terminam com `prompt_tokens` ≥ 200000 (~25 turnos cada). Uma sessão que para com `error` (HTTP 4xx/5xx) é dado: registre o `prompt_tokens` do último turno servido.

- [ ] **Step 7: 3d — GPQA e LCB em três efforts no `$W1`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
for r in r1 r2; do
  for e in xhigh medium low; do
    bash $C/scripts/idle-gate.sh --minutes 2
    caffeinate -i bash $C/scripts/run-battery.sh $W1 e3d --suites "gpqa livecodebench" --effort $e --label $W1-$e-$r
    echo "exit[3d $e $r]=$?"
  done
done
```

Expected: `results/e3d/t1/$W1-<effort>-<rodada>/{gpqa,livecodebench}.jsonl`, 50 linhas cada, nos 6 rótulos.

- [ ] **Step 8: 3d — tarefa multi-turno em `medium` e `low`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
P="python3 $C/scripts/agent_probes.py"; A="--base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm $W1"
caffeinate -i bash $C/scripts/run-arm.sh $W1 131072 --tag a3d --exec \
  "rc=0; $P contradiction $A --rounds 2 --reasoning-effort medium --output $C/results/agent/3a-$W1.jsonl || rc=\$?;
   $P contradiction $A --rounds 2 --reasoning-effort low --output $C/results/agent/3a-$W1.jsonl || rc=\$?; exit \$rc"
```

Expected: `3a-$W1.jsonl` ganha 84 linhas (efforts `medium` e `low`); o `summary` separa por effort.

- [ ] **Step 9: 3f — tool-calling com reasoning, 2 rodadas por braço**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
for r in r1 r2; do
  for arm in $W1 $N2; do
    bash $C/scripts/idle-gate.sh --minutes 2
    caffeinate -i bash $C/scripts/run-battery.sh $arm e3f --suites "jdhodges veerman" --effort xhigh --label $arm-$r
  done
  python3 bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $C/results/e3f/t1 \
    --base $N2-$r --cand $W1-$r --out $C/results/e3f-summary-$r.md
done
grep 'reasoning mediano' $C/results/e3f-summary-r*.md
```

Expected: em todas as linhas `reasoning mediano (chars)`, números > 0 nos dois braços (não `n/d`). **Gate:** `n/d` ou 0 = o runner não mandou ou não gravou o reasoning; pare e confira o submódulo (`a4a95bb`) e o `extra_body` do `tool_call_bench.py` antes de seguir.

- [ ] **Step 10: Consolidar e escrever `results/etapa3-agent.md`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
for r in r1 r2; do for e in medium low; do
  python3 bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $C/results/e3d/t1 \
    --base $W1-xhigh-$r --cand $W1-$e-$r --out $C/results/e3d-summary-$e-$r.md
done; done
{ echo "# Etapa 3 — bateria agêntica sem Docker ($(date +%F), mlx-serve $RT)"; echo
  echo "## 3a, 3b, 3c, 3e"; echo
  python3 $C/scripts/agent_probes.py summary $C/results/agent/*.jsonl
  for f in $C/results/e3f-summary-r1.md $C/results/e3f-summary-r2.md $C/results/e3d-summary-*.md; do
    echo; echo "## $(basename $f .md)"; echo; cat $f
  done
} > $C/results/etapa3-agent.md
```

Depois, acrescente `## Veredito` com uma linha por regra de decisão (3a/3b: diferença `$W1` − `$N2` em casos por 20; 3c: houve `char_run`?; 3d: effort escolhido e o tempo total contra `xhigh`; 3e: hit da troca e se o harness deve fixar o effort) e `## Leitura` (exemplos de `invented` com o turno; tokens até a resposta no 3b; o `prompt_tokens` em que algo degenerou no 3c, se houve).

Expected: as tabelas do `summary`, dois resumos 3f e quatro resumos 3d. Ignore as linhas `G2` dos resumos 3d e 3f: o G2 é o gate de thinking da campanha Swift e não se aplica aqui.

- [ ] **Step 11: Tamanho, driver diário e commit**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
du -h $C/results/agent/*.jsonl $C/results/e3d/t1/*/*.jsonl $C/results/e3f/t1/*/*.jsonl | sort -h | tail -5
nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
git add $C/results
git commit -m "bench(flashnext): Task 3 - agentic regression probes 3a-3f on the two drivers

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Expected: nenhum arquivo acima de ~1 MB. Se algum passar, mova o original para `logs/` e deixe em `results/` uma cópia com `raw_response` e `content` cortados em 500 caracteres.

---

### Task 4: Terminal-Bench 2.0 — adiado (decisão de 2026-10-12: depende de segunda máquina com Docker; script pronto em `bench/terminal-bench/scripts/run-tbench-flashnext.sh`).

---

### Task 5: Jundot oQ4e refit `c4ddfb5` × `2615fc0` no oMLX 0.7.1.dev1, e `c4ddfb5` no mlx-serve 26.10.2-pre × `w1`

**Files:**
- Modify: `bench/qwen3.8-prefix-cache/config/omlx-arms.json` (modelo `flashnext-oq4e-refit`, arm `FR`)
- Results: `results/downloads.json`, `results/{o1x,o1r,o1rm,<W1>}-*-t1.0-e5.jsonl`, `results/e5/t1/<braço>/*.jsonl`, `results/loops/e5-*.jsonl`, `results/etapa5-refit.md`, `results/etapa5-gates.env`

**Braços:**

| braço | pesos | runtime | bandas (reps) | qualidade |
| --- | --- | --- | --- | --- |
| `o1x` | oQ4e `2615fc0` (em disco) | oMLX 0.7.1.dev1 | 8K (1), 32K (3), 128K (3), 256K (1) | bateria t1 + loops |
| `o1r` | oQ4e refit `c4ddfb5` | oMLX 0.7.1.dev1 | 8K (1), 32K (3), 128K (3), 256K (1) | bateria t1 + loops |
| `o1rm` | oQ4e refit `c4ddfb5` | mlx-serve 26.10.2-pre | 8K (1), 32K (3), 128K (3) | bateria t1, só se `≤ 0.97 × $W1` |
| `$W1` | Swift 1.5 | runtime do driver | 32K (3), 128K (3) | bateria t1, só se o `o1rm` passar |

Download: 106.3 GB. Estimativa: ~2 dias (velocidade ~6 h; cada bateria t1 + loops ~8 h).

- [ ] **Step 1: Disco e plano de download**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
df -g / | tail -1
~/LocalProjects/local-llms/.venv/bin/python $C/scripts/fetch_pack.py --repo Jundot/Qwen3.8-Flash-Next-oQ4e-mtp \
  --revision c4ddfb5 --reserve-gb 150 --dry-run \
  --link-from ~/.cache/local-llms/qwen3.8-prefix-cache/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8
```

Expected: `sha=c4ddfb5…` (40 caracteres), `total_gb` ≈ 106, `free_gb` ≥ `to_download_gb` + 150. As linhas `link candidate` só listam arquivos de mesmo tamanho; o hash é conferido no download.

- [ ] **Step 2: Download**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
caffeinate -i ~/LocalProjects/local-llms/.venv/bin/python $C/scripts/fetch_pack.py --repo Jundot/Qwen3.8-Flash-Next-oQ4e-mtp \
  --revision c4ddfb5 --reserve-gb 150 \
  --link-from ~/.cache/local-llms/qwen3.8-prefix-cache/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8 \
  2>&1 | tee $C/logs/download-c4ddfb5.log
grep -o "reasoning_effort|default('[a-z]*')" ~/.cache/local-llms/qwen3.8-prefix-cache/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5*/chat_template.jinja
```

Expected: `DEST=~/.cache/local-llms/qwen3.8-prefix-cache/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5…`, recibo em `results/downloads.json`, e o default `xhigh` no template. `hardlinked:` só aparece para arquivos de hash idêntico.

- [ ] **Step 3: Registrar o arm `FR` no oMLX**

```bash
cd ~/LocalProjects/local-llms
DIR="$(ls -d ~/.cache/local-llms/qwen3.8-prefix-cache/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5* | head -1)"
python3 - "$DIR" FR flashnext-oq4e-refit Jundot/Qwen3.8-Flash-Next-oQ4e-mtp <<'EOF'
import json
import sys
from pathlib import Path

directory, arm, key, repo = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
cfg = Path("bench/qwen3.8-prefix-cache/config/omlx-arms.json")
data = json.loads(cfg.read_text())
sha = directory.name.rsplit("-", 1)[1]
assert directory.name == f"{repo.replace('/', '-')}-{sha}" and len(sha) == 40, directory.name
data["models"][key] = {"repository": repo, "revision": sha}
data["arms"][arm] = {**json.loads(json.dumps(data["arms"]["FN"])), "model_key": key}
cfg.write_text(json.dumps(data, indent=2) + "\n")
print(arm, key, repo, sha)
EOF
bash bench/flashnext-next-steps-2026-10/scripts/run-arm.sh o1r 32768 --print | head -4
bash bench/flashnext-next-steps-2026-10/scripts/run-arm.sh o1rm 32768 --print | sed -n 3p
```

Expected: `FR flashnext-oq4e-refit Jundot/Qwen3.8-Flash-Next-oQ4e-mtp c4ddfb5…`; o `--print` do `o1r` mostra `"qwen4_ple_ssd_offload": true` no profile e `omlx-v0.7.1.dev1/bin/omlx`; o do `o1rm` mostra o binário 26.10.2 e o diretório `c4ddfb5…` (sem `MISSING`).

- [ ] **Step 4: Parar o driver diário e gate térmico**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
cd ~/LocalProjects/local-llms && bash bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh --minutes 0
```

- [ ] **Step 5: Smoke 8K dos três braços novos**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
for arm in o1x o1r o1rm; do
  bash $C/scripts/run-arm.sh $arm 8192 --scenarios cold,identical,tool_turn --tag smoke; echo "exit[$arm]=$?"; sleep 120
done
for a in FN FR; do
  d="$(ls -td bench/qwen3.8-prefix-cache/logs/omlx/*-$a-* | head -1)"
  echo "$a base_path=$d settings=$(ls $d/settings.json 2>/dev/null) ple_ssd=$(grep -rl 'PLE forced to SSD' $d 2>/dev/null | wc -l | tr -d ' ')"
done
grep -c 'PLE forced to SSD' $C/logs/o1x-8192-t1.0-smoke-boot.log $C/logs/o1r-8192-t1.0-smoke-boot.log
grep -c '\[spec-stats\]' $C/logs/o1rm-8192-t1.0-smoke-boot.log
```

Expected: os três `OK`; para `FN` e `FR`, um `settings.json` no base path da sessão (prova de que o oMLX leu `OMLX_BASE_PATH`); a contagem de `PLE forced to SSD` registrada por braço (0 ou mais; é dado, não gate); `[spec-stats]` > 0 no `o1rm`. Se o `o1rm` não subir (o 26.10.2 recusar o pack oMLX), registre o erro do boot log e siga sem o `o1rm`.

- [ ] **Step 6: Banda 32K**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh o1x:32768:3:e5 o1r:32768:3:e5 $W1:32768:3:e5 o1rm:32768:3:e5 2>&1 | tee $C/logs/etapa5-32k.log
```

Expected: `exit[...]=0` nos quatro.

- [ ] **Step 7: Banda 128K (ordem inversa)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh o1rm:131072:3:e5 $W1:131072:3:e5 o1r:131072:3:e5 o1x:131072:3:e5 2>&1 | tee $C/logs/etapa5-128k.log
```

- [ ] **Step 8: 256K no oMLX (swap e PLE)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh o1r:262144:1:e5 o1x:262144:1:e5
grep -c 'PLE forced to SSD' $C/logs/o1r-262144-t1.0-e5-boot.log $C/logs/o1x-262144-t1.0-e5-boot.log
```

Expected: 5 registros por braço; `swap Δ` aparece no Step 10.

- [ ] **Step 9: Bateria t1 e loops no `o1x` e no `o1r`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/run-battery.sh o1r e5 --print | tail -2
for arm in o1x o1r; do
  bash $C/scripts/idle-gate.sh --minutes 2
  caffeinate -i bash $C/scripts/run-battery.sh $arm e5 --loops 2>&1 | tee $C/logs/battery-e5-$arm.log
done
python3 bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $C/results/e5/t1 --base o1x --cand o1r \
  --out $C/results/etapa5-quality-o1x-o1r.md
python3 $C/scripts/agent_probes.py loops $C/results/loops/e5-o1x.jsonl $C/results/loops/e5-o1r.jsonl
```

Expected: 6 arquivos em `results/e5/t1/o1x/` e em `results/e5/t1/o1r/`; 32 linhas (4 prompts × 8 seeds) em cada `loops/e5-<braço>.jsonl`; a tabela com `G1:<suíte>` por suíte. As linhas `G2` não se aplicam aqui.

- [ ] **Step 10: Decisões de velocidade**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
{ echo "# Etapa 5 — Jundot oQ4e refit (c4ddfb5) × 2615fc0 no oMLX 0.7.1.dev1, e c4ddfb5 no mlx-serve 26.10.2-pre ($(date +%F))"; echo
  python3 $C/scripts/decide.py --glob 'o1x-*-t1.0-e5.jsonl' --glob 'o1r-*-t1.0-e5.jsonl' \
    --base o1x --cand o1r --ctx 32768,131072 --mode parity --threshold 0.03 --title "Pesos no oMLX: paridade |r−1| ≤ 0.03"
  echo; python3 $C/scripts/decide.py --glob "$W1-*-t1.0-e5.jsonl" --glob 'o1rm-*-t1.0-e5.jsonl' \
    --base $W1 --cand o1rm --ctx 32768,131072 --mode le --threshold 0.97 --title "Driver: o1rm ≤ 0.97 × $W1"
  echo; python3 $C/scripts/decide.py --glob "$W1-*-t1.0-e5.jsonl" --glob 'o1rm-*-t1.0-e5.jsonl' \
    --base $W1 --cand o1rm --ctx 32768,131072 --mode le --threshold 1.03 --title "Condição do Task 6: o1rm ≤ 1.03 × $W1"
  echo; echo "## Qualidade (t1, reasoning xhigh)"; echo; cat $C/results/etapa5-quality-o1x-o1r.md
  echo; echo "## Taxa de loop (vendor_t1_xhigh, 8 seeds)"; echo
  python3 $C/scripts/agent_probes.py loops $C/results/loops/e5-o1x.jsonl $C/results/loops/e5-o1r.jsonl
} > $C/results/etapa5-refit.md
grep '^VERDICT' $C/results/etapa5-refit.md
V=$(grep '^VERDICT' $C/results/etapa5-refit.md)
printf 'O1RM_DRIVER=%s\nRUN_TASK6=%s\n' \
  "$(echo "$V" | sed -n 2p | grep -q 'pass' && echo 1 || echo 0)" \
  "$(echo "$V" | sed -n 3p | grep -q 'pass' && echo 1 || echo 0)" > $C/results/etapa5-gates.env
cat $C/results/etapa5-gates.env
```

Expected: três linhas `VERDICT` (paridade, driver, condição do Task 6) e `etapa5-gates.env` com `O1RM_DRIVER` e `RUN_TASK6`.

- [ ] **Step 11: Se `O1RM_DRIVER=1` — G1 contra o `$W1`**

```bash
( cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env; . $C/results/etapa5-gates.env
[ "$O1RM_DRIVER" = 1 ] || { echo "o1rm did not reach 0.97 x $W1; step skipped"; exit 0; }
for arm in $W1 o1rm; do
  bash $C/scripts/idle-gate.sh --minutes 2
  caffeinate -i bash $C/scripts/run-battery.sh $arm e5 2>&1 | tee $C/logs/battery-e5-$arm.log
done
python3 bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $C/results/e5/t1 --base $W1 --cand o1rm \
  --out $C/results/etapa5-quality-w1-o1rm.md
{ echo; echo "## Qualidade o1rm × $W1 (t1)"; echo; cat $C/results/etapa5-quality-w1-o1rm.md; } >> $C/results/etapa5-refit.md )
```

Expected: `G1:<suíte>` passa em todas = o `o1rm` vira candidato a driver (decisão final do usuário no Task 10).

- [ ] **Step 12: Veredito, driver diário e commit**

Acrescente `## Veredito` com três decisões: (1) o refit vira pack padrão do oMLX se `G1` passa em todas as suítes de `o1x × o1r` e o `swap Δ` do `o1r` a 256K for 0; (2) o `o1rm` vira driver só com `VERDICT: pass` a 0.97 e `G1` contra `$W1`; (3) `RUN_TASK6`. Em `## Leitura`: a contagem de `PLE forced to SSD` por braço e banda, a paridade de velocidade, as diferenças de loop por prompt e o KLD declarado pelo card (**terceiro**) ao lado do que a bateria mediu.

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
du -h $C/results/e5/t1/*/*.jsonl $C/results/loops/*.jsonl | sort -h | tail -3
nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
git add $C/results bench/qwen3.8-prefix-cache/config/omlx-arms.json
git commit -m "bench(flashnext): Task 5 - Jundot oQ4e refit on oMLX 0.7.1.dev1 and on mlx-serve 26.10.2-pre

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Expected: arquivos de `results/` abaixo de ~1 MB (acima disso, cópia cortada em `results/` e original em `logs/`, como no Task 3).

---

### Task 6: scottlowry Swift 1.5 oQ4e `e8ed008` — condicional ao Task 5

Roda só se `results/etapa5-gates.env` tem `RUN_TASK6=1` (um pack oMLX no mlx-serve a `≤ 1.03 × $W1` nas duas bandas). Com `RUN_TASK6=0`, escreva `results/etapa6-scottlowry.md` com uma linha ("não rodou: o `o1rm` ficou em <razões> × `$W1`, acima de 1.03") e faça o commit do Step 7.

**Files:**
- Results: `results/s1m-*-t1.0-e6.jsonl`, `results/<W1>-*-t1.0-e6.jsonl`, `results/e5/t1/s1m/{gpqa,livecodebench}.jsonl`, `results/etapa6-scottlowry.md`

**Braços:**

| braço | pesos | runtime | bandas (reps) | qualidade |
| --- | --- | --- | --- | --- |
| `s1m` | scottlowry Swift 1.5 oQ4e `e8ed008` | mlx-serve 26.10.2-pre | 8K (1), 32K (3), 128K (3) | GPQA 50 + LCB 50, t1 |
| `$W1` | Swift 1.5 MLX-4.7bpw | runtime do driver | 32K (3), 128K (3) | GPQA 50 + LCB 50, t1 (reusa `e5` se existir) |

Download: 106.3 GB. Estimativa: ~1 dia.

- [ ] **Step 1: Condição, disco e download**

```bash
( cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/etapa5-gates.env; [ "$RUN_TASK6" = 1 ] || { echo "Task 6 skipped (RUN_TASK6=0)"; exit 0; }
df -g / | tail -1
PY=~/LocalProjects/local-llms/.venv/bin/python
$PY $C/scripts/fetch_pack.py --repo scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp --revision e8ed008 --reserve-gb 150 --dry-run
caffeinate -i $PY $C/scripts/fetch_pack.py --repo scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp --revision e8ed008 \
  --reserve-gb 150 2>&1 | tee $C/logs/download-e8ed008.log
grep -o "reasoning_effort|default('[a-z]*')" ~/.cache/local-llms/qwen3.8-prefix-cache/scottlowry-Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp-e8ed008*/chat_template.jinja )
```

Expected: `total_gb` ≈ 106; `DEST=…-e8ed008…`; o default do template registrado.

- [ ] **Step 2: Parar o driver diário e smoke 8K**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh --minutes 0
bash $C/scripts/run-arm.sh s1m 8192 --scenarios cold,identical,tool_turn --tag smoke
grep -c '\[spec-stats\]' $C/logs/s1m-8192-t1.0-smoke-boot.log
```

Expected: `OK` e `[spec-stats]` > 0.

- [ ] **Step 3: Bandas 32K e 128K**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh $W1:32768:3:e6 s1m:32768:3:e6
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh s1m:131072:3:e6 $W1:131072:3:e6
```

- [ ] **Step 4: Tempo até a resposta final (GPQA e LCB)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
[ -s $C/results/e5/t1/$W1/gpqa.jsonl ] || caffeinate -i bash $C/scripts/run-battery.sh $W1 e5 --suites "gpqa livecodebench"
bash $C/scripts/idle-gate.sh --minutes 2
caffeinate -i bash $C/scripts/run-battery.sh s1m e5 --suites "gpqa livecodebench"
python3 bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $C/results/e5/t1 --base $W1 --cand s1m \
  --out $C/results/etapa6-quality-w1-s1m.md
```

Expected: tabela com acertos, tempo mediano e tokens de GPQA e LCB; `G1` por suíte.

- [ ] **Step 5: Escrever `results/etapa6-scottlowry.md`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
{ echo "# Etapa 6 — scottlowry Swift 1.5 oQ4e (e8ed008) no mlx-serve 26.10.2-pre × $W1 ($(date +%F))"; echo
  python3 $C/scripts/decide.py --glob "$W1-*-t1.0-e6.jsonl" --glob 's1m-*-t1.0-e6.jsonl' \
    --base $W1 --cand s1m --ctx 32768,131072 --mode le --threshold 0.97 --title "Driver: s1m ≤ 0.97 × $W1"
  echo; echo "## Tempo até a resposta final e acertos (t1)"; echo; cat $C/results/etapa6-quality-w1-s1m.md
} > $C/results/etapa6-scottlowry.md
grep '^VERDICT' $C/results/etapa6-scottlowry.md
```

Expected: `VERDICT: pass` e `G1` passando nas duas suítes = o `s1m` é candidato a driver; qualquer outro resultado mantém o `$W1`. Acrescente `## Veredito` e `## Leitura` (o pack é anterior ao refit; compare o tempo mediano por questão do `s1m` com o do `$W1`).

- [ ] **Step 6: Driver diário**

```bash
cd ~/LocalProjects/local-llms && nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
```

- [ ] **Step 7: Commit**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
git add $C/results
git commit -m "bench(flashnext): Task 6 - scottlowry Swift 1.5 oQ4e on mlx-serve 26.10.2-pre

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: umixer oQ4e-mix6-mtp v2 × Jundot refit no oMLX 0.7.1.dev1 — depois do Task 5

Pré-condição: o Task 5 terminou e `results/e5/t1/o1r/` tem as 6 suítes e `results/loops/e5-o1r.jsonl` existe.

**Files:**
- Modify: `bench/qwen3.8-prefix-cache/config/omlx-arms.json` (modelo `flashnext-oq4e-mix6-v2`, arm `FM`)
- Results: `results/x1-{8192,262144}-t1.0-*.jsonl`, `results/e5/t1/x1/*.jsonl`, `results/loops/e5-x1.jsonl`, `results/etapa7-mix6.md`

**Braços:**

| braço | pesos | runtime | bandas (reps) | qualidade |
| --- | --- | --- | --- | --- |
| `x1` | umixer oQ4e-mix6-mtp-v2 (HEAD no download) | oMLX 0.7.1.dev1 (`FM`) | 8K (1), 256K (1) | bateria t1 + loops |
| `o1r` | Jundot refit `c4ddfb5` | oMLX 0.7.1.dev1 (`FR`) | 256K do Task 5 | bateria t1 + loops do Task 5 |

Regra (proposta do spec): o mix6 v2 substitui o refit como pack padrão do oMLX se `x1 ≥ o1r − margem G1` em todas as suítes, `x1 > o1r + margem G1` em pelo menos uma, e `swap Δ` 0 a 256K. Download: ~125 GB (v2 não verificado). Estimativa: ~1 dia.

- [ ] **Step 1: Disco e download (hardlink do refit onde o hash bater)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
df -g / | tail -1
PY=~/LocalProjects/local-llms/.venv/bin/python
REFIT="$(ls -d ~/.cache/local-llms/qwen3.8-prefix-cache/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5* | head -1)"
$PY $C/scripts/fetch_pack.py --repo umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2 --revision main --reserve-gb 150 \
  --link-from "$REFIT" --dry-run
caffeinate -i $PY $C/scripts/fetch_pack.py --repo umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2 --revision main \
  --reserve-gb 150 --link-from "$REFIT" 2>&1 | tee $C/logs/download-mix6-v2.log
```

Expected: o `--dry-run` mostra o `sha` completo do HEAD (a revisão fica fixada no nome do diretório e no recibo) e `total_gb` ≈ 125; o download termina com `DEST=…/umixer-Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2-<sha>`.

- [ ] **Step 2: Registrar o arm `FM`**

```bash
cd ~/LocalProjects/local-llms
DIR="$(ls -d ~/.cache/local-llms/qwen3.8-prefix-cache/umixer-Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2-* | head -1)"
python3 - "$DIR" FM flashnext-oq4e-mix6-v2 umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2 <<'EOF'
import json
import sys
from pathlib import Path

directory, arm, key, repo = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
cfg = Path("bench/qwen3.8-prefix-cache/config/omlx-arms.json")
data = json.loads(cfg.read_text())
sha = directory.name.rsplit("-", 1)[1]
assert directory.name == f"{repo.replace('/', '-')}-{sha}" and len(sha) == 40, directory.name
data["models"][key] = {"repository": repo, "revision": sha}
data["arms"][arm] = {**json.loads(json.dumps(data["arms"]["FN"])), "model_key": key}
cfg.write_text(json.dumps(data, indent=2) + "\n")
print(arm, key, repo, sha)
EOF
bash bench/flashnext-next-steps-2026-10/scripts/run-arm.sh x1 32768 --print | head -4
grep -o "reasoning_effort|default('[a-z]*')" "$DIR/chat_template.jinja"
```

Expected: `FM flashnext-oq4e-mix6-v2 umixer/… <sha>`; o `--print` mostra o diretório do mix6 (sem `MISSING`).

- [ ] **Step 3: Parar o driver diário, smoke 8K e 256K**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh --minutes 0
bash $C/scripts/run-arm.sh x1 8192 --scenarios cold,identical,tool_turn --tag smoke
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh x1:262144:1:e7
grep -c 'PLE forced to SSD' $C/logs/x1-8192-t1.0-smoke-boot.log $C/logs/x1-262144-t1.0-e7-boot.log
```

Expected: smoke `OK`; 5 registros a 256K; a contagem de `PLE forced to SSD` registrada.

- [ ] **Step 4: Bateria t1 e loops no `x1`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh --minutes 2
caffeinate -i bash $C/scripts/run-battery.sh x1 e5 --loops 2>&1 | tee $C/logs/battery-e5-x1.log
python3 bench/swift15-flashnext-2026-10/scripts/summarize_ab.py --ab-dir $C/results/e5/t1 --base o1r --cand x1 \
  --out $C/results/etapa7-quality-o1r-x1.md
```

Expected: 6 arquivos em `results/e5/t1/x1/`; 32 linhas em `results/loops/e5-x1.jsonl`.

- [ ] **Step 5: Escrever `results/etapa7-mix6.md`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
{ echo "# Etapa 7 — umixer oQ4e-mix6-mtp v2 × Jundot oQ4e refit no oMLX 0.7.1.dev1 ($(date +%F))"; echo
  python3 $C/scripts/decide.py --glob 'x1-262144-t1.0-e7.jsonl' --glob 'o1r-262144-t1.0-e5.jsonl' --title "256K (1 rep): wired e swap"
  echo; echo "## Qualidade (t1, reasoning xhigh)"; echo; cat $C/results/etapa7-quality-o1r-x1.md
  echo; echo "## Taxa de loop"; echo
  python3 $C/scripts/agent_probes.py loops $C/results/loops/e5-o1r.jsonl $C/results/loops/e5-x1.jsonl
} > $C/results/etapa7-mix6.md
```

Acrescente `## Veredito` aplicando a regra (G1 em todas as suítes, superioridade além da margem em pelo menos uma, `swap Δ` 0 a 256K) e `## Leitura` (residente a mais do mix6 contra o refit; o autor não publicou KLD).

- [ ] **Step 6: Driver diário e commit**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
git add $C/results bench/qwen3.8-prefix-cache/config/omlx-arms.json
git commit -m "bench(flashnext): Task 7 - umixer oQ4e-mix6 v2 vs Jundot refit on oMLX 0.7.1.dev1

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: GGUF com MTP no Metal (llama.cpp ≥ b11569 e mlx-serve 26.10.2-pre) — com smoke gate

**Files:**
- Results: `results/install-runtimes.md`, `results/{g0,g1,g1m}-32768-t1.0-smoke8.jsonl`, `results/{g1,g1m,<W1>}-*-t1.0-e8.jsonl` (só se o smoke passar), `results/etapa8-gguf.md`

**Braços:**

| braço | engine | MTP | smoke 32K (1 rep) | bandas se passar |
| --- | --- | --- | --- | --- |
| `g0` | llama.cpp b11569 | não | sim (referência de decode) | — |
| `g1` | llama.cpp b11569 | `--spec-type draft-mtp`, `--spec-draft-n-max 3`, `--parallel 1`, sem `--kv-unified` | sim | 32K, 128K (3) |
| `g1m` | mlx-serve 26.10.2-pre (llama.cpp embutido) | cabeça MTP pela flag que o `--help` listar | sim | 32K, 128K (3) |
| `$W1` | mlx-serve do driver | nativa | — | 32K, 128K (3) |

**Gate do smoke:** decode quente (coluna `decode` do `decide.py`) ≥ 70 tok/s a 32K no `g1` ou no `g1m`. Sem isso, a campanha apaga os pesos e encerra o teste. Download: ~106 GB. Estimativa: 0,5–1 dia.

- [ ] **Step 1: Instalar o llama.cpp b11569**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/install-runtime.sh llama 2>&1 | tee -a $C/results/install-runtimes.md
~/.local/opt/qwen38/llama-b11569/llama-server --help 2>&1 | grep -E -- '--spec-type|--spec-draft-model|--spec-draft-n-max|--kv-unified|--chat-template-kwargs'
```

Expected: `sha256 check: OK`; `--version` com `build 11569`; o `--help` lista `--spec-type`, `--spec-draft-model`, `--spec-draft-n-max` e `--chat-template-kwargs`. Se uma dessas flags não existir com esse nome, pare e ajuste `scripts/run-llama-flashnext.sh` ao nome listado antes do Step 4.

- [ ] **Step 2: Disco e download (IQ4_NL + cabeça MTP Q8_0)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
df -g / | tail -1
PY=~/LocalProjects/local-llms/.venv/bin/python
$PY $C/scripts/fetch_pack.py --repo ggml-org/Qwen3.8-Flash-Next-GGUF --revision main \
  --include '*IQ4_NL*' --include 'mtp-*Q8_0*.gguf' --include '*/mtp-*Q8_0*.gguf' --reserve-gb 150 --dry-run
caffeinate -i $PY $C/scripts/fetch_pack.py --repo ggml-org/Qwen3.8-Flash-Next-GGUF --revision main \
  --include '*IQ4_NL*' --include 'mtp-*Q8_0*.gguf' --include '*/mtp-*Q8_0*.gguf' --reserve-gb 150 \
  2>&1 | tee $C/logs/download-gguf.log
GG="$(ls -d ~/.cache/local-llms/qwen3.8-prefix-cache/ggml-org-Qwen3.8-Flash-Next-GGUF-* | head -1)"; find "$GG" -name '*.gguf' | sort
```

Expected: o `--dry-run` lista `total_gb` ≈ 106 (102.0 do IQ4_NL + 4.1 da cabeça MTP); `find` mostra os shards `IQ4_NL` e um `mtp-…Q8_0….gguf`. Se o `--dry-run` listar mais de ~110 GB (por exemplo, um `mtp-…IQ4_NL`), troque o primeiro `--include` por `'*IQ4_NL-*'` e confira de novo.

- [ ] **Step 3: Conferir os comandos**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
for arm in g0 g1 g1m; do bash $C/scripts/run-arm.sh $arm 32768 --print | sed -n 3p; done
```

Expected: `g0` sem `--spec-type`; `g1` com `--spec-type draft-mtp --spec-draft-model …mtp…Q8_0….gguf --spec-draft-n-max 3` e `--parallel 1`; `g1m` com o binário 26.10.2 e a flag da cabeça MTP (ou o aviso `GX without an MTP head flag` no stderr). Nenhum caminho com `MISSING`.

- [ ] **Step 4: Parar o driver diário e smoke a 32K**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh --minutes 0
caffeinate -i bash $C/scripts/run-seq.sh g0:32768:1:smoke8 g1:32768:1:smoke8 g1m:32768:1:smoke8
grep -i -E 'draft acceptance|accept' $C/logs/g1-32768-t1.0-smoke8-boot.log | tail -3
grep -c '\[spec-stats\]' $C/logs/g1m-32768-t1.0-smoke8-boot.log
python3 $C/scripts/decide.py --glob '*-32768-t1.0-smoke8.jsonl' --title "Smoke GGUF 32K" | tee $C/logs/etapa8-smoke.txt
```

Expected: as três linhas na tabela. Para cada braço, leia a coluna `decode`. Se o `hit` do `identical` vier 0 no llama.cpp, confira se o `usage` traz `prompt_tokens_details.cached_tokens`; sem o campo, o hit fica `n/d` e o TTFT quente contra o frio mede o reuso.

- [ ] **Step 5: Gate do smoke**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
python3 - $C/results <<'EOF'
import json, statistics, sys
from pathlib import Path
best = {}
for arm in ("g0", "g1", "g1m"):
    f = Path(sys.argv[1]) / f"{arm}-32768-t1.0-smoke8.jsonl"
    rs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []
    warm = [r["decode_tps"] for r in rs if r["scenario"] in ("identical", "append", "tool_turn") and not r.get("error")]
    best[arm] = statistics.median(warm) if warm else 0.0
    print(arm, round(best[arm], 1))
print("SMOKE:", "pass" if max(best["g1"], best["g1m"]) >= 70 else "fail")
EOF
```

Expected: `SMOKE: pass` (decode quente ≥ 70 tok/s no `g1` ou no `g1m`) segue para o Step 6. `SMOKE: fail` encerra o teste: apague os pesos e pule para o Step 8.

```bash
GG="$(ls -d ~/.cache/local-llms/qwen3.8-prefix-cache/ggml-org-Qwen3.8-Flash-Next-GGUF-* | head -1)"; du -sh "$GG" && rm -rf "$GG"; df -g / | tail -1
```

- [ ] **Step 6: Se passou — 32K e 128K contra o `$W1`**

Rode só os braços GGUF com decode ≥ 70 no smoke (o exemplo usa os dois).

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh $W1:32768:3:e8 g1:32768:3:e8 g1m:32768:3:e8
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh g1m:131072:3:e8 g1:131072:3:e8 $W1:131072:3:e8
```

- [ ] **Step 7: Decisão**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
{ echo; for cand in g1 g1m; do
    python3 $C/scripts/decide.py --glob "$W1-*-t1.0-e8.jsonl" --glob "$cand-*-t1.0-e8.jsonl" \
      --base $W1 --cand $cand --ctx 32768,131072 --mode le --threshold 0.97 --title "Driver: $cand ≤ 0.97 × $W1"; echo
  done; } > $C/logs/etapa8-bands.txt
cat $C/logs/etapa8-bands.txt
```

Expected: uma linha `VERDICT` por braço GGUF. `pass` = candidato a driver (qualidade fica para uma campanha própria, porque o GGUF muda runtime e quantizador ao mesmo tempo).

- [ ] **Step 8: Escrever `results/etapa8-gguf.md`, driver diário e commit**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
{ echo "# Etapa 8 — GGUF ggml-org IQ4_NL + MTP Q8_0: llama.cpp b11569 e mlx-serve 26.10.2-pre ($(date +%F))"; echo
  cat $C/logs/etapa8-smoke.txt; echo
  [ -f $C/logs/etapa8-bands.txt ] && cat $C/logs/etapa8-bands.txt
} > $C/results/etapa8-gguf.md
nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
git add $C/results
git commit -m "bench(flashnext): Task 8 - GGUF with MTP on llama.cpp b11569 and mlx-serve 26.10.2-pre

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Acrescente ao arquivo, antes do commit, `## Veredito` (smoke passou ou não, decode de `g0`, `g1`, `g1m`; pesos apagados ou mantidos) e `## Leitura` (aceitação do draft no log do llama.cpp; comparação com os ~36 tok/s sem MTP do `references.md` e os 84.6 tok/s do `w1`).

---

### Task 9: `--ple-gpu` com prefix cache de 8 GB no `w1`, com braço controle

**Files:**
- Results: `results/<W1P8>-32768-t1.0-smoke9.jsonl`, `results/{<W1C8>,<W1P8>}-{32768,131072}-t1.0-e9.jsonl`, `results/etapa9-plegpu.md`

**Braços:**

| braço | prefix cache RAM | `--ple-gpu` | bandas (reps) |
| --- | --- | --- | --- |
| `$W1C8` (controle) | 8 GB | não | 32K, 128K (3) |
| `$W1P8` | 8 GB | sim | smoke 32K (1), 32K, 128K (3) |
| `$W1` (referência das bandas do Task 5, prefix cache 16 GB) | 16 GB | não | lido de `results/` |

Regra do repo: o `--ple-gpu` vira perfil opcional só com `T_turno($W1P8) ≤ 0.95 × T_turno($W1C8)` a 128K, swap Δ ≤ 0.5 GB e nenhum cenário recusado. Estimativa: ~3 h.

- [ ] **Step 1: Parar o driver diário e smoke do `$W1P8`**

```bash
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh --minutes 0
bash $C/scripts/run-arm.sh $W1P8 32768 --scenarios cold,identical,tool_turn --tag smoke9
grep -m1 'ple gather' $C/logs/$W1P8-32768-t1.0-smoke9-boot.log
```

Expected: `ple gather: gpu …`. Se vier `ple gather: cpu (low_memory: …)`, a hipótese do `headroom 16 GB` = prefix cache está errada: copie a linha para `results/etapa9-plegpu.md` com o veredito "recusado de novo com prefix cache de 8 GB", faça o commit do Step 5 e encerre o task.

- [ ] **Step 2: Banda 32K (controle → candidato)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh $W1C8:32768:3:e9 $W1P8:32768:3:e9
```

- [ ] **Step 3: Banda 128K (candidato → controle)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-seq.sh $W1P8:131072:3:e9 $W1C8:131072:3:e9
grep -c -i -E 'PrefillDoesNotFit|prefill refused|OutOfMemory' $C/logs/$W1P8-131072-t1.0-e9-boot.log
```

Expected: `exit[...]=0` e 0 recusas.

- [ ] **Step 4: Escrever `results/etapa9-plegpu.md`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
. $C/results/driver-arms.env
W1TAG=e5; [ -s $C/results/$W1-131072-t1.0-e5.jsonl ] || W1TAG=e1w
{ echo "# Etapa 9 — --ple-gpu com prefix cache de 8 GB ($(date +%F), mlx-serve $RT)"; echo
  grep -m1 'ple gather' $C/logs/$W1P8-32768-t1.0-smoke9-boot.log; echo
  python3 $C/scripts/decide.py --glob "$W1C8-*-t1.0-e9.jsonl" --glob "$W1P8-*-t1.0-e9.jsonl" \
    --base $W1C8 --cand $W1P8 --ctx 131072 --mode le --threshold 0.95 --title "--ple-gpu × controle 8 GB (regra a 128K)"
  echo; python3 $C/scripts/decide.py --glob "$W1C8-*-t1.0-e9.jsonl" --glob "$W1-*-t1.0-$W1TAG.jsonl" \
    --base $W1 --cand $W1C8 --ctx 32768,131072 --mode le --threshold 1.03 --title "Custo do prefix cache de 8 GB contra o diário de 16 GB (informativo)"
} > $C/results/etapa9-plegpu.md
grep '^VERDICT' $C/results/etapa9-plegpu.md
```

Expected: a primeira `VERDICT` decide o perfil opcional. A segunda mostra quanto o cache de 8 GB custa em hit e `T_turno` contra o diário; o `$W1` de referência vem das bandas do Task 5 (`e5`, mesmo runtime) ou, se o Task 5 não rodou, do smoke do Task 1 (`e1w`). Sem nenhum dos dois, a segunda tabela sai só com o `$W1C8`: compare com os 7.9 / 8.6 s do `w1` no 26.10.1. Acrescente `## Veredito` e `## Leitura` (linha `ple gather`, decode a 128K dos dois braços, hit do `append` com 8 GB).

- [ ] **Step 5: Driver diário e commit**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &
git add $C/results
git commit -m "bench(flashnext): Task 9 - --ple-gpu with an 8GB prefix cache and its control arm

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: Card, referências e resumo da campanha

**Files:**
- Create: `bench/flashnext-next-steps-2026-10/results/summary.md`
- Modify: `docs/models/qwen3.8-flash-next.md`, `bench/qwen38-flash-next/references.md`
- Não muda: `reports/README.md` — ele lista dashboards, e nenhuma campanha anterior sem dashboard entrou nele; esta campanha não gera dashboard.

- [ ] **Step 1: Escrever `results/summary.md`**

Comece pelo veredito em duas frases: qual runtime e qual pack servem o driver principal e o secundário depois da campanha. Depois, a tabela de decisões, uma linha por teste:

```
| # | teste | braços | regra | resultado | decisão | fonte |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | mlx-serve 26.10.2-pre × 26.10.1 no n2 | n2, n2x | ≤ 0.97× nas duas bandas | razões 32K / 128K | adotado ou não | etapa1-runtime.md |
| 2 | Swift 1.5 a 256K/512K | W1, W1Q4 | gates padrão | T_turno, livre mínimo | perfil 512k com Swift ou iQ | etapa2-swift-long.md |
| 3 | bateria agêntica | W1, N2 | regras 3a–3f | casos por 20, char_run, effort | effort default, sessão longa | etapa3-agent.md |
| 4 | Terminal-Bench | — | — | adiado | — | — |
| 5 | Jundot refit | o1x, o1r, o1rm, W1 | paridade, G1, ≤ 0.97× | razões, G1 | pack oMLX padrão; driver? | etapa5-refit.md |
| 6 | scottlowry Swift oQ4e | s1m, W1 | ≤ 0.97×, G1 | rodou ou não | — | etapa6-scottlowry.md |
| 7 | mix6 v2 | x1, o1r | G1 + margem, swap 0 a 256K | G1, swap | substitui o refit? | etapa7-mix6.md |
| 8 | GGUF + MTP | g0, g1, g1m | smoke ≥ 70 tok/s | decode | pesos mantidos ou apagados | etapa8-gguf.md |
| 9 | --ple-gpu + 8 GB | W1C8, W1P8 | ≤ 0.95× a 128K | razão, ple gather | perfil opcional? | etapa9-plegpu.md |
```

Substitua cada célula das colunas `resultado` e `decisão` pelos números e decisões dos arquivos de etapa; nenhuma célula fica com o texto do modelo. Termine com `## Limites` (1 rep a 256K; uma bateria t1 por braço no Task 5 e 7; números de terceiros marcados como **terceiro**; Terminal-Bench adiado).

- [ ] **Step 2: Atualizar o card `docs/models/qwen3.8-flash-next.md` (em inglês)**

- Cabeçalho e "Daily driver configuration": runtime do driver principal (26.10.1 ou 26.10.2-pre-release.1) e o `T_turno` medido no Task 1.
- "Measured performance": a linha do Task 1 (26.10.2-pre no iQ) e a do Task 2 (Swift a 256K e 512K).
- "Extended profile: 512K": qual pack o perfil usa e por quê (Task 2).
- "Client sampling": o default de `reasoning_effort` lido no template (Task 0 Step 17: `xhigh`; aceitos `xhigh`, `medium`, `low`) e o effort recomendado pelo 3d.
- "Stacks compared": linhas do `o1r`, `o1rm`, `s1m`, `x1`, `g1`/`g1m` que rodaram, com `T_turno` e veredito.
- "Known issues": troque "256K and 512K with Swift 1.5 are not measured" pelo resultado do Task 2; acrescente o resultado do 3c (degeneração longa) e do 3e (troca de effort); atualize a linha do `--ple-gpu` com o Task 9.
- Toda citação aponta para `bench/flashnext-next-steps-2026-10/results/<arquivo>.md`.

- [ ] **Step 3: Atualizar `bench/qwen38-flash-next/references.md` (pt-BR)**

- Cabeçalho (linhas 3–16): drivers e runtime depois da campanha; acrescente o link desta campanha ao lado das outras.
- "Próximos passos", tabela do item 4: `4b` (pendente "256K e 512K") → resultado do Task 2; `4c` → resultado do Task 6 (ou "não rodou: condição do Task 5 não atingida"); `4d` → resultado do Task 5; `4a` e `4e` → resultado do Task 7; `4f` → resultado do Task 8.
- Cada item resolvido cita o `results/etapa<N>-*.md` correspondente, pela regra do `AGENTS.md` de não deixar rótulos "pendente" vencidos.

- [ ] **Step 4: Conferir links e fazer o commit**

```bash
cd ~/LocalProjects/local-llms && C=bench/flashnext-next-steps-2026-10
for f in docs/models/qwen3.8-flash-next.md bench/qwen38-flash-next/references.md $C/results/summary.md; do
  grep -o 'flashnext-next-steps-2026-10/results/[a-z0-9-]*\.md' $f | sort -u | while read p; do
    [ -f "bench/$p" ] || echo "missing: $p in $f"
  done
done
git add $C/results/summary.md docs/models/qwen3.8-flash-next.md bench/qwen38-flash-next/references.md
git commit -m "docs(flash-next): next-steps 2026-10 results in the model card and references

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push -u origin bench/flashnext-next-steps-2026-10
```

Expected: nenhuma linha `missing:`. Abra o PR só quando o usuário pedir.
