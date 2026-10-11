# Flash-Next: A/B Swift 1.5 × n2 com reasoning explícito — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decidir se o Swift 1.5 (pack Dankpaws MLX-4.7bpw) substitui o n2 como driver diário do Flash-Next, com uma comparação de qualidade e de tempo de thinking sob o mesmo modo de reasoning.

**Architecture:** Uma campanha nova, `bench/swift15-flashnext-2026-10/`, reusa o driver `run-candidate.sh` de 2026-09 com um braço novo, `w1`. Os runners do submódulo `tools/local-llm-bench-m4-32gb` (`bench2.py`, `tool_call_bench.py`) ganham `--reasoning-effort`. Uma sonda nova de instruction-following (`if_probe.py`) e um consolidador (`summarize_ab.py`) fecham a bateria. A campanha termina com `T_turno`, Terminal-Bench no vencedor e a atualização dos docs.

**Tech Stack:** bash, Python 3 (stdlib), pytest via `uv run`, mlx-serve 26.10.1, harbor 0.8.0 (Terminal-Bench 2.0).

**Spec:** a conversa de 2026-10-10 e as fontes abaixo. Não há spec separado.
- `research/qwen38-flashnext-derivatives-20261009.md` §3 e §10 (Swift 1.5, critérios do A/B)
- `bench/qwen38-flashnext-daily-driver-2026-09/TODO.md` (correções do harness)
- `bench/engine-updates-2026-10/results/quality-o1-mtplx.md` (o n2 de 07/10 respondeu sem thinking)

## Global Constraints

- Rig: Mac Studio M4 Max 128 GB. Um modelo servido por vez.
- O `run-candidate.sh` mata o que escuta na porta 11234 e apaga `~/.mlx-serve/kv-cache`. Pare o driver diário antes de qualquer run.
- Runtime dos dois braços: mlx-serve **26.10.1** em `~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve` (`MLX_SERVE_EXPECTED_VERSION=26.10.1`).
- Pesos do n2: `ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a`.
- Pesos do w1: `Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0`, em `~/.cache/local-llms/qwen3.8-prefix-cache/`.
- Bateria de qualidade: `reasoning_effort` **xhigh**, janela do servidor 131072, dois perfis de sampling por braço:
  - **t1 (vendor, principal):** `temperature 1.0`, `top_p 0.95`, `top_k 20`, `min_p 0`, `presence_penalty 0`, `repetition_penalty 1.0`. Fonte: `generation_config.json` dos dois packs e card do Swift 1.5 ("temperature 1.0 · top_p 0.95 · top_k 20 · min_p 0 · presence_penalty 0 · repetition_penalty 1"). É o perfil do uso diário.
  - **t0 (controle reproduzível):** `temperature 0`, sem outros parâmetros. É o modo das baterias de qualidade anteriores.
- O `T_turno` (Task 9) já usa o perfil t1: o `run-candidate.sh` passa `--temperature 1.0 --top-p 0.95 --top-k 20` ao `cache_probe.py`.
- `max_tokens`: HumanEval 32768; GPQA e LiveCodeBench 65536; tool-calling 32768 (`TOOLBENCH_MAX_TOKENS`); IF 16384.
- Licença do Swift 1.5: o usuário confirmou em 2026-10-10 que o uso está OK.
- Tudo que vai para `reports/` sai em inglês. Notas da campanha podem ficar em PT.
- Testes: `uv run --no-project --with pytest python -m pytest <caminho> -q`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Nenhum id de modelo em commits ou docs do repo.
- Branch da campanha: `bench/swift15-flashnext-2026-10`, a partir de `main`.

## Review Focus

1. **O mlx-serve ignora `reasoning_effort` em requisição não-streaming.** O esperado: com `xhigh`, o HumanEval passa de ~200 tokens por resposta. O smoke da Task 8 é o gate: `completion_tokens` mediano > 500 ou `reasoning_chars` > 0. Sem isso, a campanha para.
2. **O reasoning chega em campos diferentes** (`reasoning_content`, `reasoning`, ou `<think>…</think>` dentro de `content`). O esperado: o grader do HumanEval nunca vê o texto de thinking, e `reasoning_chars` conta os três casos. Testes na Task 4 e na Task 6.
3. **Resposta truncada em `max_tokens`** (`finish_reason=length`). O esperado: conta como erro e aparece numa coluna própria. Teste na Task 7.
4. **`FLASHNEXT_EXEC` exportado no shell.** O esperado: o `run-candidate.sh` ignora a variável, avisa no stderr e roda o probe. Teste na Task 2.
5. **Os dois braços rodam questões diferentes** (seed ou dataset mudou entre runs). O esperado: o `summarize_ab.py` recusa comparar e diz qual suíte diverge. Teste na Task 7.
6. **O servidor ignora os parâmetros de sampling** (por exemplo, `top_k` fora do schema OpenAI). O esperado: em t0, três respostas iguais ao mesmo prompt; em t1, pelo menos duas diferentes. O `samplecheck` do smoke da Task 8 é o gate. Os runners gravam o sampling enviado em cada registro (Tasks 4-6).

---

## File Structure

| Arquivo | Ação | Responsabilidade |
| --- | --- | --- |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify | braço `w1`; opção `--exec` no lugar de `FLASHNEXT_EXEC`; checagem de diretório do modelo; comentário do m1xq |
| `bench/engine-updates-2026-10/scripts/run-quality.sh` | Modify | passar `--exec` em vez de `FLASHNEXT_EXEC` |
| `bench/engine-updates-2026-10/tests/test_arms.py` | Modify | testes do `--exec` e do env ignorado |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py` | Modify | default de `--data` aponta para os dados de outubro |
| `bench/qwen38-flashnext-daily-driver-2026-09/tests/test_render_perf_lines.py` | Create | teste do default |
| `bench/qwen38-flashnext-daily-driver-2026-09/TODO.md` | Modify | marcar os itens fechados |
| `tools/local-llm-bench-m4-32gb/scripts/bench2.py` | Modify (submódulo) | `--reasoning-effort` e flags de sampling; `split_reasoning`; `reasoning_chars` e `sampling` no registro |
| `tools/local-llm-bench-m4-32gb/scripts/tool_call_bench.py` | Modify (submódulo) | `--reasoning-effort` e flags de sampling (via `extra_body`) |
| `tools/local-llm-bench-m4-32gb/tests/test_reasoning_effort.py` | Create (submódulo) | testes dos dois runners |
| `bench/swift15-flashnext-2026-10/plan.md` | Create | runbook da campanha |
| `bench/swift15-flashnext-2026-10/scripts/run-arm.sh` | Create | wrapper do `run-candidate.sh` com saída na campanha |
| `bench/swift15-flashnext-2026-10/scripts/run-ab.sh` | Create | sobe um braço e roda a bateria |
| `bench/swift15-flashnext-2026-10/scripts/ab-battery.sh` | Create | roda as 6 suítes contra o servidor pronto |
| `bench/swift15-flashnext-2026-10/scripts/if_probe.py` | Create | sonda de instruction-following |
| `bench/swift15-flashnext-2026-10/scripts/summarize_ab.py` | Create | tabela n2 × w1 e gates |
| `bench/swift15-flashnext-2026-10/tests/test_arm_w1.py` | Create | testes do braço w1 e do `run-ab.sh --print` |
| `bench/swift15-flashnext-2026-10/tests/test_if_probe.py` | Create | testes dos checkers |
| `bench/swift15-flashnext-2026-10/tests/test_summarize_ab.py` | Create | testes do consolidador |
| `bench/terminal-bench/scripts/run-tbench-flashnext.sh` | Create | Terminal-Bench do vencedor |
| `docs/superpowers/plans/backlog-uncensored-models.md` | Modify | marcar o ARC4NUM como testado |
| `docs/models/qwen3.8-flash-next.md` | Modify | veredito do A/B e do Terminal-Bench |

---

### Task 1: Branch, download verificado e braço `w1`

**Files:**
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh:6-15,44,93-98,296`
- Create: `bench/swift15-flashnext-2026-10/scripts/run-arm.sh`
- Create: `bench/swift15-flashnext-2026-10/tests/test_arm_w1.py`

**Interfaces:**
- Produces: braço `w1` no `run-candidate.sh` (mesmo bloco do `n2`, outro `MODEL_DIR` e `MODEL_REV`). Wrapper `bench/swift15-flashnext-2026-10/scripts/run-arm.sh <braço> <ctx> [args do run-candidate]`, que grava em `bench/swift15-flashnext-2026-10/{results,logs}`.

- [ ] **Step 1: Criar o branch**

```bash
cd ~/LocalProjects/local-llms
git checkout main && git pull --ff-only origin main
git checkout -b bench/swift15-flashnext-2026-10
```

- [ ] **Step 2: Conferir o download**

O download começou em 2026-10-10 (log `~/.local/opt/qwen38/swift15-download-20261010.log`, PID 47336).

```bash
DIR=~/.cache/local-llms/qwen3.8-prefix-cache/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0
pgrep -f 'hf download Dankpaws' || echo "download terminou"
tail -3 ~/.local/opt/qwen38/swift15-download-20261010.log
find "$DIR" -type f -not -path "$DIR/.cache/*" | wc -l   # esperado: 115 (o próprio $DIR fica sob ~/.cache)
find "$DIR/.cache" -name '*.incomplete' | wc -l          # esperado: 0
stat -f %z "$DIR/ngram_table.bin"                          # esperado: 32000153976
du -sh "$DIR"                                              # esperado: ~100 GB
```

Se a contagem ficar abaixo de 115, rode de novo o mesmo comando. O `hf download` retoma de onde parou:

```bash
~/LocalProjects/local-llms/.venv/bin/hf download Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw \
  --revision 13839b7191e0973ff9fea58232267c395b76c6c0 --local-dir "$DIR"
```

- [ ] **Step 3: Escrever o teste que falha**

`bench/swift15-flashnext-2026-10/tests/test_arm_w1.py`:

```python
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
DRIVER = REPO / "bench" / "qwen38-flashnext-daily-driver-2026-09" / "scripts" / "run-candidate.sh"
SWIFT = "Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "MTPLX_", "OMLX_", "ENGINE_", "AB_"))}
    env.update(extra or {})
    return env


def show(cand, ctx="32768", *args):
    out = subprocess.run(["bash", str(DRIVER), cand, ctx, *args, "--print"],
                         capture_output=True, text=True, env=_env(), check=True)
    return out.stdout


def test_w1_serves_swift_pack_on_26101():
    out = show("w1")
    assert SWIFT in out
    assert IQ not in out
    assert "mlx-serve-v26.10.1/mlx-serve" in out
    assert "--runtime-revision v26.10.1 " in out


def test_w1_keeps_n2_flags():
    # O A/B só muda os pesos: o comando do servidor do w1 é o do n2 com outro --model.
    w1 = show("w1").replace(SWIFT, "MODEL")
    n2 = show("n2").replace(IQ, "MODEL")
    assert w1.replace("w1", "ARM") == n2.replace("n2", "ARM")
```

- [ ] **Step 4: Rodar o teste e ver a falha**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests/test_arm_w1.py -q`
Expected: FAIL. O `run-candidate.sh` sai com código 64 (`opcao desconhecida` ou braço fora do `case`).

- [ ] **Step 5: Implementar o braço**

Em `run-candidate.sh`:

1. Na linha 6 do cabeçalho, depois da linha do `n1/n2/n2p`, acrescente:

```bash
#   w1 = campanha swift15-flashnext-2026-10: Swift 1.5 (Dankpaws MLX-4.7bpw) @ mlx-serve 26.10.1, flags do n2
```

2. Na string de uso (linha 15), troque `n1|n2|n2p|` por `n1|n2|n2p|w1|`.

3. Depois da linha 44 (`IQDIR=...`), acrescente:

```bash
# Campanha swift15-flashnext-2026-10: fine-tune Swift 1.5, mesmo layout e runtime do IQDIR.
SWIFTDIR="$MODEL_ROOT/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"
```

4. No bloco `n1|n2|n2p)` (linhas 93-98), troque o cabeçalho e o `if`:

```bash
  n1|n2|n2p|w1) # flashnext-updates-2026-10: runtime 26.10.1. n1 = pesos do c1; n2/n2p = pack iQ; n2p = + --ple-gpu; w1 = Swift 1.5.
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.1
      if [[ "$CAND" == n1 ]]; then
        MODEL_DIR="$DDALCU"; MODEL_REV=ef5b919d31534faa1997666f1a22d362cd6383cd
      elif [[ "$CAND" == w1 ]]; then
        MODEL_DIR="$SWIFTDIR"; MODEL_REV=13839b7191e0973ff9fea58232267c395b76c6c0
      else
        MODEL_DIR="$IQDIR"; MODEL_REV=dafff5c3d8168c9d13275661153911096499a80a
      fi
```

5. Logo depois do bloco `if [[ -n "$PRINT" ]]; then ... fi` (termina perto da linha 296), acrescente a checagem do diretório. Ela fica fora do `--print`, para os testes rodarem sem os pesos:

```bash
# Um pack ausente ou incompleto faz o servidor morrer no boot com erro pouco claro: recusar antes.
[[ -e "$MODEL_DIR" ]] || { echo "run-candidate: pesos ausentes em $MODEL_DIR" >&2; exit 66; }
```

- [ ] **Step 6: Criar o wrapper da campanha**

`bench/swift15-flashnext-2026-10/scripts/run-arm.sh`:

```bash
#!/usr/bin/env bash
# Roda um braço da campanha swift15-flashnext-2026-10 com o driver de 2026-09, gravando
# results/ e logs/ aqui. Mesmos argumentos do run-candidate.sh.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FLASHNEXT_RESULTS_DIR="$HERE/results" FLASHNEXT_LOGS_DIR="$HERE/logs"
exec bash "$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh" "$@"
```

- [ ] **Step 7: Rodar os testes**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests bench/engine-updates-2026-10/tests -q`
Expected: PASS em tudo. Os testes do engine-updates confirmam que o n2 não mudou.

- [ ] **Step 8: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh \
        bench/swift15-flashnext-2026-10/scripts/run-arm.sh bench/swift15-flashnext-2026-10/tests/test_arm_w1.py
git commit -m "bench(swift15): braço w1 (Swift 1.5 @ mlx-serve 26.10.1) no run-candidate

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `--exec` no lugar de `FLASHNEXT_EXEC`

**Files:**
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh:15-28,141,292-293,398-400`
- Modify: `bench/engine-updates-2026-10/scripts/run-quality.sh:14-15`
- Modify: `bench/engine-updates-2026-10/tests/test_arms.py:281-286`
- Modify: `bench/engine-updates-2026-10/tests/test_band.py:98`

**Interfaces:**
- Consumes: `run-candidate.sh` da Task 1.
- Produces: `run-candidate.sh <braço> <ctx> ... --exec "<comando>"`. O comando roda com `BASE_URL` e `MODEL_ID` no ambiente, e o código de saída dele vira o do braço. A variável `FLASHNEXT_EXEC` passa a ser ignorada.

- [ ] **Step 1: Escrever os testes que falham**

Em `bench/engine-updates-2026-10/tests/test_arms.py`, troque `test_exec_hook_replaces_probe_in_print` por:

```python
def test_exec_option_replaces_probe_in_print():
    out = show("o1", "131072", "--exec", "bash quality.sh")
    assert "exec: bash quality.sh" in out
    assert "\nprobe:" not in out


def test_exported_flashnext_exec_is_ignored():
    # Um FLASHNEXT_EXEC esquecido no shell fazia todo braço pular o probe sem gravar jsonl.
    res = subprocess.run(["bash", str(DRIVER), "o1", "131072", "--print"], capture_output=True, text=True,
                         env=_env({"FLASHNEXT_EXEC": "bash quality.sh"}), check=True)
    assert "\nprobe:" in res.stdout and "exec:" not in res.stdout
    assert "FLASHNEXT_EXEC" in res.stderr
```

- [ ] **Step 2: Rodar e ver a falha**

Run: `uv run --no-project --with pytest python -m pytest bench/engine-updates-2026-10/tests/test_arms.py -q -k exec`
Expected: FAIL. `--exec` dá `opcao desconhecida`, e o env ainda troca o probe.

- [ ] **Step 3: Implementar**

Em `run-candidate.sh`:

1. Na string de uso, acrescente `[--exec CMD]` antes de `[--print]`.
2. Antes do `while` de argumentos, acrescente:

```bash
EXEC_CMD=""
# A bateria troca o probe só quando o chamador passa --exec. Um FLASHNEXT_EXEC herdado do shell é ignorado.
if [[ -n "${FLASHNEXT_EXEC:-}" ]]; then
  echo "run-candidate: FLASHNEXT_EXEC no ambiente é ignorado; use --exec" >&2
  unset FLASHNEXT_EXEC
fi
```

3. No `case` dos argumentos, acrescente `    --exec) EXEC_CMD="$2"; shift 2 ;;`.
4. Nas linhas 292-293 e 398-400, troque `FLASHNEXT_EXEC` por `EXEC_CMD`. O comentário da linha 292 passa a ser `# --exec troca o probe por outro comando contra o servidor (ex.: bateria de qualidade).`
5. Linha 141: mova o comentário `# os dois juntos: a conta do memory plan só chega a 262K assim` da linha do `m1s` para a linha do `m1xq`:

```bash
        m1xq) FIX=memmax-kvq8 ;;  # os dois juntos: a conta do memory plan só chega a 262K assim
        m1s) FIX=qsaprefill ;;  # prefill esparso do indexer QSA, que o auto só liga com NAX (M5)
```

Em `run-quality.sh`, troque as linhas 14-15 por:

```bash
if [[ -n "${ENGINE_BAND_DRY:-}" ]]; then echo "EXEC=$EXEC"; echo "bash run-arm.sh $ARM $CTX --tag qual --exec \"\$EXEC\""; exit 0; fi
exec bash "$HERE/scripts/run-arm.sh" "$ARM" "$CTX" --tag qual --exec "$EXEC"
```

E troque `(FLASHNEXT_EXEC no lugar do probe)` por `(--exec no lugar do probe)` no comentário da linha 3.

Em `bench/engine-updates-2026-10/tests/test_band.py:98`, o teste `test_quality_runs_three_batteries_through_exec_hook` espera o formato antigo. Troque a última asserção por:

```python
    assert out.rstrip().endswith('bash run-arm.sh o1 131072 --tag qual --exec "$EXEC"')
```

- [ ] **Step 4: Rodar os testes**

Run: `uv run --no-project --with pytest python -m pytest bench/engine-updates-2026-10/tests bench/swift15-flashnext-2026-10/tests -q`
Expected: PASS.

- [ ] **Step 5: Marcar o TODO e fazer o commit**

Em `bench/qwen38-flashnext-daily-driver-2026-09/TODO.md`, marque `[x]` em **`FLASHNEXT_EXEC` sem `unset`** e em **Comentário fora do lugar**. Cite o branch `bench/swift15-flashnext-2026-10`.

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh \
        bench/engine-updates-2026-10/scripts/run-quality.sh bench/engine-updates-2026-10/tests/test_arms.py \
        bench/engine-updates-2026-10/tests/test_band.py bench/qwen38-flashnext-daily-driver-2026-09/TODO.md
git commit -m "bench(flashnext-driver): --exec substitui FLASHNEXT_EXEC; env herdado é ignorado

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Default do `render_perf_lines.py`

**Files:**
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py:18-20`
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/tests/test_render_perf_lines.py`

**Interfaces:**
- Produces: `render_perf_lines.py` sem `--data` lê `bench/engine-updates-2026-10/results/reports-2026-10.json`.

- [ ] **Step 1: Escrever o teste que falha**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_perf_lines  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def test_default_data_is_october_profile():
    # A página publicada é a de outubro; o default não pode reescrevê-la com o reports.json de setembro.
    assert render_perf_lines.REPORTS_JSON == REPO / "bench" / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
    assert render_perf_lines.REPORTS_JSON.is_file()
```

- [ ] **Step 2: Rodar e ver a falha**

Run: `uv run --no-project --with pytest python -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests/test_render_perf_lines.py -q`
Expected: FAIL (o caminho atual termina em `qwen38-flashnext-daily-driver-2026-09/results/reports.json`).

- [ ] **Step 3: Implementar**

```python
CAMPAIGN = Path(__file__).resolve().parents[1]
# A página publicada é a de outubro (consolidate_reports.py --profile 2026-10). Para o perfil 2026-09,
# passe --data e --out explícitos.
REPORTS_JSON = CAMPAIGN.parent / "engine-updates-2026-10" / "results" / "reports-2026-10.json"
OUT = CAMPAIGN.parents[1] / "reports" / "qwen38-flashnext-perf-lines.html"
```

- [ ] **Step 4: Rodar o teste e conferir que a página não muda**

```bash
uv run --no-project --with pytest python -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests -q
python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py --out /tmp/perf-lines.html
diff <(sed 's/Generated at <code>[^<]*<\/code>//' reports/qwen38-flashnext-perf-lines.html) \
     <(sed 's/Generated at <code>[^<]*<\/code>//' /tmp/perf-lines.html) && echo "página idêntica"
```

Expected: PASS e `página idêntica`. Se o `diff` mostrar outra diferença, pare: a página publicada não veio desse JSON.

- [ ] **Step 5: Marcar o TODO e fazer o commit**

Marque `[x]` em **Default do renderer reescreve a página publicada** no `TODO.md`.

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/render_perf_lines.py \
        bench/qwen38-flashnext-daily-driver-2026-09/tests/test_render_perf_lines.py \
        bench/qwen38-flashnext-daily-driver-2026-09/TODO.md
git commit -m "bench(flashnext-driver): render_perf_lines lê os dados de outubro por default

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `--reasoning-effort` e sampling no `bench2.py` (submódulo)

**Files:**
- Modify: `tools/local-llm-bench-m4-32gb/scripts/bench2.py:30-95,700-715,820-830`
- Create: `tools/local-llm-bench-m4-32gb/tests/test_reasoning_effort.py`

**Interfaces:**
- Produces:
  - `bench2.REASONING_EFFORT: str | None`. O default é `None`, e o payload fica igual ao de hoje.
  - `bench2.SAMPLING: dict`. O default é `{}`. As chaves possíveis são `top_p`, `top_k`, `min_p`, `presence_penalty` e `repetition_penalty`, e vão direto para o payload.
  - `bench2.sampling_from_args(**kw) -> dict`, que descarta os valores `None`.
  - `bench2.split_reasoning(message: dict) -> tuple[str, str]`, que devolve `(content, reasoning)`.
  - `api_call(...)` devolve também `"reasoning_chars": int`.
  - Cada registro JSONL ganha `reasoning_effort`, `reasoning_chars` e `sampling`. O campo `temperature` já existe.
  - CLI: `bench2.py <suite> ... --reasoning-effort {none,low,medium,high,xhigh} --temperature F --top-p F --top-k N --min-p F --presence-penalty F --repetition-penalty F`. Sem flags, o payload fica igual ao de hoje (`temperature 0`).

- [ ] **Step 1: Criar o branch no submódulo**

O submódulo está em HEAD destacado (`7a37fe1`). Ele também tem runs de 07/10 e 09/10 não versionados em `benchmarks/runs/`. Não mexa neles neste task.

```bash
cd ~/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
git checkout -b feat/reasoning-effort
mkdir -p tests
```

- [ ] **Step 2: Escrever os testes que falham**

`tools/local-llm-bench-m4-32gb/tests/test_reasoning_effort.py`:

```python
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bench2  # noqa: E402


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen(body, seen):
    def _urlopen(req, timeout=None):
        seen.append(json.loads(req.data))
        return _Resp(json.dumps(body).encode())
    return _urlopen


def _body(message):
    return {"choices": [{"message": message, "finish_reason": "stop"}],
            "usage": {"completion_tokens": 10, "prompt_tokens": 5}}


def test_payload_carries_effort_when_set(monkeypatch):
    seen = []
    monkeypatch.setattr(bench2, "REASONING_EFFORT", "xhigh")
    monkeypatch.setattr(bench2, "urlopen", _fake_urlopen(_body({"content": "ok", "reasoning_content": "abc"}), seen))
    r = bench2.api_call([{"role": "user", "content": "x"}], model="m")
    assert seen[0]["reasoning_effort"] == "xhigh"
    assert r["content"] == "ok"
    assert r["reasoning_chars"] == 3


def test_payload_unchanged_by_default(monkeypatch):
    seen = []
    monkeypatch.setattr(bench2, "REASONING_EFFORT", None)
    monkeypatch.setattr(bench2, "SAMPLING", {})
    monkeypatch.setattr(bench2, "urlopen", _fake_urlopen(_body({"content": "ok"}), seen))
    r = bench2.api_call([{"role": "user", "content": "x"}], model="m")
    assert set(seen[0]) == {"model", "messages", "temperature", "max_tokens"}
    assert seen[0]["temperature"] == 0
    assert r["reasoning_chars"] == 0


def test_payload_carries_vendor_sampling(monkeypatch):
    seen = []
    vendor = {"top_p": 0.95, "top_k": 20, "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}
    monkeypatch.setattr(bench2, "TEMPERATURE", 1.0)
    monkeypatch.setattr(bench2, "SAMPLING", vendor)
    monkeypatch.setattr(bench2, "urlopen", _fake_urlopen(_body({"content": "ok"}), seen))
    bench2.api_call([{"role": "user", "content": "x"}], model="m")
    assert seen[0]["temperature"] == 1.0
    assert {k: seen[0][k] for k in vendor} == vendor


def test_sampling_from_args_drops_unset():
    assert bench2.sampling_from_args(top_p=None, top_k=20, min_p=0.0, presence_penalty=None,
                                     repetition_penalty=None) == {"top_k": 20, "min_p": 0.0}


def test_split_reasoning_reads_reasoning_alias():
    assert bench2.split_reasoning({"content": "ok", "reasoning": "zz"}) == ("ok", "zz")


def test_split_reasoning_strips_inline_think():
    content, reasoning = bench2.split_reasoning({"content": "<think>abcd</think>\n```python\nx = 1\n```"})
    assert content == "```python\nx = 1\n```"
    assert reasoning == "abcd"


def test_split_reasoning_handles_null_content():
    assert bench2.split_reasoning({"content": None, "reasoning_content": "r"}) == ("", "r")


def test_error_path_reports_zero_reasoning(monkeypatch):
    def _boom(req, timeout=None):
        raise OSError("down")
    monkeypatch.setattr(bench2, "urlopen", _boom)
    r = bench2.api_call([{"role": "user", "content": "x"}], model="m")
    assert r["finish_reason"] == "error" and r["reasoning_chars"] == 0
```

- [ ] **Step 3: Rodar e ver a falha**

Run: `uv run --no-project --with pytest python -m pytest tests/test_reasoning_effort.py -q`
Expected: FAIL (`AttributeError: ... REASONING_EFFORT`, `SAMPLING`, `sampling_from_args` e `split_reasoning`).

- [ ] **Step 4: Implementar**

1. Depois de `TIMEOUT = ...` (linha 39), acrescente:

```python
# None keeps the payload as before (each server applies its own default, which on
# mlx-serve 26.10.1 produced answers with no thinking). Set by --reasoning-effort.
REASONING_EFFORT = None
# Extra sampling keys sent as-is (top_p, top_k, min_p, presence_penalty, repetition_penalty).
# Empty keeps the payload as before. Set by the sampling flags; --temperature sets TEMPERATURE.
SAMPLING = {}


def sampling_from_args(**kw):
    return {k: v for k, v in kw.items() if v is not None}


def split_reasoning(message):
    """Return (content, reasoning) from a chat message.

    Servers put the thinking in `reasoning_content`, in `reasoning`, or inline as
    <think>...</think> at the start of `content`. Graders must only see the content."""
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    if "</think>" in content:
        head, _, tail = content.partition("</think>")
        reasoning += head.replace("<think>", "", 1)
        content = tail.lstrip()
    return content, reasoning
```

2. Em `api_call`, troque a montagem do payload por:

```python
    body = {
        "model": model,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
    }
    body.update(SAMPLING)
    if REASONING_EFFORT:
        body["reasoning_effort"] = REASONING_EFFORT
    payload = json.dumps(body).encode()
```

3. No ramo de sucesso, troque `"content": choice["message"].get("content", ""),` por:

```python
        content, reasoning = split_reasoning(choice["message"])
        return {
            "content": content,
            "reasoning_chars": len(reasoning),
```

   Mantenha o resto do dict. No ramo `except`, acrescente `"reasoning_chars": 0,` ao dict.

4. No registro JSONL (bloco com `'reasoning_tokens': r['think_tokens'],`), acrescente:

```python
                'reasoning_effort': REASONING_EFFORT,
                'reasoning_chars': r['reasoning_chars'],
                'sampling': SAMPLING,
```

5. No CLI, depois do `--lcb-version`, acrescente:

```python
    parser.add_argument("--reasoning-effort", choices=["none", "low", "medium", "high", "xhigh"], default=None,
                        help="Send reasoning_effort in every request (default: omit, server default applies)")
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--min-p", type=float, default=None)
    parser.add_argument("--presence-penalty", type=float, default=None)
    parser.add_argument("--repetition-penalty", type=float, default=None)
```

   Depois de `args = parser.parse_args()`, acrescente:

```python
    REASONING_EFFORT = args.reasoning_effort
    TEMPERATURE = args.temperature
    SAMPLING = sampling_from_args(top_p=args.top_p, top_k=args.top_k, min_p=args.min_p,
                                  presence_penalty=args.presence_penalty,
                                  repetition_penalty=args.repetition_penalty)
```

   As atribuições ficam no nível do módulo, então mudam as globais que `api_call` e o registro leem.

6. Na linha de `max_tokens` do pre-flight, acrescente o effort e o sampling:
   `print(f"  max_tokens: {args.max_tokens}  reasoning_effort: {REASONING_EFFORT}  temperature: {TEMPERATURE}  sampling: {SAMPLING}")`.

- [ ] **Step 5: Rodar os testes**

Run: `uv run --no-project --with pytest python -m pytest tests/test_reasoning_effort.py -q`
Expected: PASS (8 testes).

- [ ] **Step 6: Commit no submódulo**

```bash
git add scripts/bench2.py tests/test_reasoning_effort.py
git commit -m "bench2: --reasoning-effort, sampling flags and reasoning_chars per question

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `--reasoning-effort` e sampling no `tool_call_bench.py` e bump do submódulo

**Files:**
- Modify: `tools/local-llm-bench-m4-32gb/scripts/tool_call_bench.py:39-58,200-210,292-302,704,792,837-840`
- Modify: `tools/local-llm-bench-m4-32gb/tests/test_reasoning_effort.py`
- Modify: ponteiro do submódulo em `local-llms`

**Interfaces:**
- Consumes: branch `feat/reasoning-effort` da Task 4.
- Produces:
  - `tool_call_bench.REASONING_EFFORT: str | None`.
  - `tool_call_bench.SAMPLING_EXTRA: dict`, com as chaves fora do schema OpenAI (`top_k`, `min_p`, `presence_penalty`, `repetition_penalty`).
  - `tool_call_bench.extra_body() -> dict | None`, que junta `SAMPLING_EXTRA` e `reasoning_effort`.
  - CLI: `--reasoning-effort`, `--temperature`, `--top-p`, `--top-k`, `--min-p`, `--presence-penalty`, `--repetition-penalty`. `--temperature` e `--top-p` trocam as globais `TEMPERATURE` (0.0) e `TOP_P` (1.0). Sem flags, as requisições ficam iguais às de hoje.
  - Os registros e o summary ganham `reasoning_effort` e `sampling_extra`. Os campos `temperature` e `top_p` já existem.

- [ ] **Step 1: Escrever o teste que falha**

Acrescente ao `tests/test_reasoning_effort.py`:

```python
import tool_call_bench  # noqa: E402


def test_tool_bench_extra_body(monkeypatch):
    monkeypatch.setattr(tool_call_bench, "REASONING_EFFORT", None)
    monkeypatch.setattr(tool_call_bench, "SAMPLING_EXTRA", {})
    assert tool_call_bench.extra_body() is None
    monkeypatch.setattr(tool_call_bench, "REASONING_EFFORT", "xhigh")
    assert tool_call_bench.extra_body() == {"reasoning_effort": "xhigh"}
    monkeypatch.setattr(tool_call_bench, "SAMPLING_EXTRA", {"top_k": 20, "min_p": 0.0})
    assert tool_call_bench.extra_body() == {"top_k": 20, "min_p": 0.0, "reasoning_effort": "xhigh"}
```

- [ ] **Step 2: Rodar e ver a falha**

Run: `uv run --no-project --with pytest --with openai --with pyyaml python -m pytest tests/test_reasoning_effort.py -q`
Expected: FAIL (`AttributeError: ... extra_body`).

- [ ] **Step 3: Implementar**

1. Depois de `MAX_COMPLETION_TOKENS = ...` (linha 58):

```python
# None/empty keep requests as before. Set by --reasoning-effort and the sampling flags.
REASONING_EFFORT = None
SAMPLING_EXTRA = {}


def extra_body():
    body = dict(SAMPLING_EXTRA)
    if REASONING_EFFORT:
        body["reasoning_effort"] = REASONING_EFFORT
    return body or None
```

2. Nas duas chamadas `client.chat.completions.create(` (linhas ~200 e ~292), acrescente `extra_body=extra_body(),` depois de `max_tokens=MAX_COMPLETION_TOKENS,`.
3. Nos dicts que têm `"temperature": TEMPERATURE,` (registro por caso perto da linha 704 e summary perto da linha 792), acrescente:

```python
            "reasoning_effort": REASONING_EFFORT,
            "sampling_extra": SAMPLING_EXTRA,
```

4. No CLI, depois de `--run-prefix`:

```python
    p.add_argument("--reasoning-effort", choices=["none", "low", "medium", "high", "xhigh"], default=None,
                   help="Send reasoning_effort in every request (default: omit)")
    p.add_argument("--temperature", type=float, default=TEMPERATURE)
    p.add_argument("--top-p", type=float, default=TOP_P)
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--min-p", type=float, default=None)
    p.add_argument("--presence-penalty", type=float, default=None)
    p.add_argument("--repetition-penalty", type=float, default=None)
```

   Depois de `args = p.parse_args()`, acrescente:

```python
    REASONING_EFFORT = args.reasoning_effort
    TEMPERATURE, TOP_P = args.temperature, args.top_p
    SAMPLING_EXTRA = {k: v for k, v in {"top_k": args.top_k, "min_p": args.min_p,
                                        "presence_penalty": args.presence_penalty,
                                        "repetition_penalty": args.repetition_penalty}.items() if v is not None}
```

   O `seed=SEED` (42) continua em toda requisição. Em t1, ele só torna o sampling reproduzível se o servidor respeitar `seed`.

- [ ] **Step 4: Rodar os testes**

Run: `uv run --no-project --with pytest --with openai --with pyyaml python -m pytest tests -q`
Expected: PASS (9 testes).

- [ ] **Step 5: Commit, push e bump do ponteiro**

```bash
git add scripts/tool_call_bench.py tests/test_reasoning_effort.py
git commit -m "tool_call_bench: --reasoning-effort and sampling flags via extra_body

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin feat/reasoning-effort
cd ~/LocalProjects/local-llms
git add tools/local-llm-bench-m4-32gb
git commit -m "chore: bump local-llm-bench-m4-32gb (--reasoning-effort e sampling nos runners)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Sonda de instruction-following (`if_probe.py`)

**Files:**
- Create: `bench/swift15-flashnext-2026-10/scripts/if_probe.py`
- Create: `bench/swift15-flashnext-2026-10/tests/test_if_probe.py`

**Interfaces:**
- Produces:
  - `if_probe.CASES: list[dict]`, com 20 casos `{"id", "prompt", "checks": [(nome, *args)]}`.
  - `if_probe.CHECKERS: dict[str, Callable[..., bool]]`.
  - `if_probe.grade(case, content) -> dict[str, bool]`.
  - `if_probe.split_reasoning(message) -> tuple[str, str]`, a mesma regra do `bench2.py`.
  - `if_probe.build_body(model, prompt, effort, max_tokens, temperature, sampling) -> dict`.
  - `if_probe.select_cases(only: str | None) -> list[dict]`. Recusa um id desconhecido.
  - CLI: `if_probe.py --base-url URL --model ID --arm ARM [--reasoning-effort xhigh] [--max-tokens 16384] [--temperature F] [--top-p F] [--top-k N] [--min-p F] [--presence-penalty F] [--repetition-penalty F] [--only if07,...] [--repeat N] --output PATH`.
  - JSONL, um registro por caso e repetição: `arm, id, rep, passed, checks, elapsed_s, completion_tokens, reasoning_chars, finish_reason, reasoning_effort, temperature, sampling, content_preview`.
  - O `samplecheck` da Task 8 usa `--only if07 --repeat 3` para conferir se o sampling chega ao servidor.

O card do Swift declara −3 no IFBench. Esta sonda é uma checagem de sanidade no estilo IFEval (instruções verificáveis por código). Ela não reproduz o IFBench.

- [ ] **Step 1: Escrever os testes que falham**

`bench/swift15-flashnext-2026-10/tests/test_if_probe.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import if_probe  # noqa: E402

C = if_probe.CHECKERS


@pytest.mark.parametrize("name,args,good,bad", [
    ("all_lowercase", (), "soft rain falls.", "Soft rain falls."),
    ("all_uppercase", (), "GO FOR IT!", "Go for it!"),
    ("no_commas", (), "a b c", "a, b"),
    ("word_count_max", (5,), "one two three four", "one two three four five"),
    ("word_count_min", (3,), "one two three", "one two"),
    ("bullet_count", (2,), "- a\n- b", "- a\n- b\n- c"),
    ("json_keys", (["name", "age"],), '```json\n{"name": "A", "age": 3}\n```', '{"name": "A"}'),
    ("json_array_len", (3,), "[2, 3, 5]", "[2, 3]"),
    ("ends_with", ("Bye.",), "Hello. Bye.", "Bye. Hello."),
    ("starts_with", ("Absolutely",), "Absolutely, yes.", "Yes, absolutely."),
    ("includes", (["sunrise", "ritual"],), "A Sunrise ritual.", "A sunrise."),
    ("excludes", (["tree"],), "Tall pines.", "A tree."),
    ("paragraphs_by_divider", (2,), "One.\n***\nTwo.", "One.\n\nTwo."),
    ("has_title", (), "<<The Sea>>\nwaves", "The Sea\nwaves"),
    ("placeholder_min", (2,), "Dear [name], at [company]", "Dear [name]"),
    ("wrapped_in_quotes", (), '"Mars is red."', "Mars is red."),
    ("section_count", (2,), "SECTION 1\na\nSECTION 2\nb", "SECTION 1\na"),
    ("has_postscript", ("P.S.",), "Poem.\nP.S. bye", "Poem. bye"),
])
def test_checker(name, args, good, bad):
    assert C[name](good, *args) is True
    assert C[name](bad, *args) is False


def test_cases_use_known_checkers_and_unique_ids():
    assert len(if_probe.CASES) == 20
    assert len({c["id"] for c in if_probe.CASES}) == 20
    for case in if_probe.CASES:
        for name, *_ in case["checks"]:
            assert name in C, (case["id"], name)


def test_grade_reports_each_check():
    case = {"id": "x", "prompt": "", "checks": [("no_commas",), ("word_count_max", 3)]}
    assert if_probe.grade(case, "a b") == {"no_commas": True, "word_count_max": True}
    assert if_probe.grade(case, "a, b c d") == {"no_commas": False, "word_count_max": False}


def test_split_reasoning_inline_think():
    assert if_probe.split_reasoning({"content": "<think>ab</think> ok"}) == ("ok", "ab")


def test_build_body_vendor_sampling():
    body = if_probe.build_body("m", "p", "xhigh", 100, 1.0, {"top_p": 0.95, "top_k": 20})
    assert body == {"model": "m", "messages": [{"role": "user", "content": "p"}], "temperature": 1.0,
                    "max_tokens": 100, "top_p": 0.95, "top_k": 20, "reasoning_effort": "xhigh"}


def test_build_body_t0_has_no_extras():
    body = if_probe.build_body("m", "p", None, 100, 0.0, {})
    assert set(body) == {"model", "messages", "temperature", "max_tokens"}


def test_select_cases():
    assert [c["id"] for c in if_probe.select_cases("if07,if01")] == ["if01", "if07"]
    assert len(if_probe.select_cases(None)) == 20
    with pytest.raises(SystemExit):
        if_probe.select_cases("if99")
```

- [ ] **Step 2: Rodar e ver a falha**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests/test_if_probe.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'if_probe'`).

- [ ] **Step 3: Implementar**

`bench/swift15-flashnext-2026-10/scripts/if_probe.py`:

```python
#!/usr/bin/env python3
"""Sonda de instruction-following no estilo IFEval: 20 prompts com instruções verificáveis por código.

Mede, por caso, se todas as instruções passaram (strict) e o tempo e os tokens da resposta. Não reproduz o
IFBench do card do Swift 1.5; é uma checagem de sanidade para o A/B n2 × w1."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


def split_reasoning(message: dict) -> tuple[str, str]:
    """(content, reasoning): mesma regra do bench2.split_reasoning."""
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    if "</think>" in content:
        head, _, tail = content.partition("</think>")
        reasoning += head.replace("<think>", "", 1)
        content = tail.lstrip()
    return content, reasoning


def _words(t: str) -> list[str]:
    return re.findall(r"\b\w+\b", t)


def _json_payload(t: str):
    t = t.strip()
    fence = re.match(r"^```(?:json)?\s*\n(.*)\n```$", t, re.S)
    try:
        return json.loads(fence.group(1) if fence else t)
    except (json.JSONDecodeError, TypeError):
        return None


def _json_keys(t: str, keys: list[str]) -> bool:
    d = _json_payload(t)
    return isinstance(d, dict) and all(k in d for k in keys)


def _json_array_len(t: str, n: int) -> bool:
    d = _json_payload(t)
    return isinstance(d, list) and len(d) == n


CHECKERS = {
    "all_lowercase": lambda t: t == t.lower() and any(c.isalpha() for c in t),
    "all_uppercase": lambda t: t == t.upper() and any(c.isalpha() for c in t),
    "no_commas": lambda t: "," not in t,
    "word_count_max": lambda t, n: len(_words(t)) < n,
    "word_count_min": lambda t, n: len(_words(t)) >= n,
    "bullet_count": lambda t, n: len(re.findall(r"^\s*[-*]\s+\S", t, re.M)) == n,
    "json_keys": _json_keys,
    "json_array_len": _json_array_len,
    "ends_with": lambda t, s: t.strip().endswith(s),
    "starts_with": lambda t, s: t.strip().startswith(s),
    "includes": lambda t, ws: all(w.lower() in t.lower() for w in ws),
    "excludes": lambda t, ws: not any(re.search(rf"\b{re.escape(w)}\b", t, re.I) for w in ws),
    "paragraphs_by_divider": lambda t, n: len([p for p in re.split(r"\n\s*\*\*\*\s*\n", t.strip()) if p.strip()]) == n,
    "has_title": lambda t: re.search(r"<<[^<>\n]+>>", t) is not None,
    "placeholder_min": lambda t, n: len(re.findall(r"\[[^\[\]\n]+\]", t)) >= n,
    "wrapped_in_quotes": lambda t: len(t.strip()) > 1 and t.strip()[0] == '"' and t.strip()[-1] == '"',
    "section_count": lambda t, n: len(re.findall(r"\bSECTION\s+\d+", t)) == n,
    "has_postscript": lambda t, s: re.search(rf"^\s*{re.escape(s)}", t, re.M) is not None,
}

CASES = [
    {"id": "if01", "prompt": "Write a haiku about rain. Use only lowercase letters.", "checks": [("all_lowercase",)]},
    {"id": "if02", "prompt": "Describe the water cycle in fewer than 50 words.", "checks": [("word_count_max", 50)]},
    {"id": "if03", "prompt": "List exactly 4 benefits of unit tests as a markdown bullet list, and nothing else.",
     "checks": [("bullet_count", 4)]},
    {"id": "if04", "prompt": "Explain what a hash map is without using any commas.", "checks": [("no_commas",)]},
    {"id": "if05", "prompt": "Return a JSON object with the keys \"name\" and \"age\" for a fictional person. "
                             "Output only the JSON.", "checks": [("json_keys", ["name", "age"])]},
    {"id": "if06", "prompt": "Write a short product description for a desk lamp. End your response with the exact "
                             "phrase \"Is there anything else I can help with?\"",
     "checks": [("ends_with", "Is there anything else I can help with?")]},
    {"id": "if07", "prompt": "Write one motivational sentence in ALL CAPITAL LETTERS.", "checks": [("all_uppercase",)]},
    {"id": "if08", "prompt": "Write a two-paragraph story about a cat. Separate the paragraphs with the markdown "
                             "divider ***.", "checks": [("paragraphs_by_divider", 2)]},
    {"id": "if09", "prompt": "Write a short poem about the sea. Give it a title wrapped in double angular brackets, "
                             "like <<title>>.", "checks": [("has_title",)]},
    {"id": "if10", "prompt": "Write a cover letter template with at least 3 placeholders in square brackets, such as "
                             "[name].", "checks": [("placeholder_min", 3)]},
    {"id": "if11", "prompt": "Explain recursion to a beginner in at least 120 words.", "checks": [("word_count_min", 120)]},
    {"id": "if12", "prompt": "Write a tweet about coffee that includes the keywords \"sunrise\" and \"ritual\".",
     "checks": [("includes", ["sunrise", "ritual"])]},
    {"id": "if13", "prompt": "Describe a forest without using the words \"tree\" or \"green\".",
     "checks": [("excludes", ["tree", "trees", "green"])]},
    {"id": "if14", "prompt": "Wrap your entire response in double quotation marks. Tell me one fact about Mars.",
     "checks": [("wrapped_in_quotes",)]},
    {"id": "if15", "prompt": "Write a weekend plan with exactly 3 sections. Mark the start of each section with "
                             "\"SECTION X\", where X is the section number.", "checks": [("section_count", 3)]},
    {"id": "if16", "prompt": "Start your answer with the word \"Absolutely\" and explain in two sentences why sleep "
                             "matters.", "checks": [("starts_with", "Absolutely")]},
    {"id": "if17", "prompt": "Name the three primary colors. Use only lowercase letters and no commas.",
     "checks": [("all_lowercase",), ("no_commas",)]},
    {"id": "if18", "prompt": "Write a limerick about a programmer. After it, add a postscript that starts with "
                             "\"P.S.\"", "checks": [("has_postscript", "P.S.")]},
    {"id": "if19", "prompt": "Summarize the plot of Romeo and Juliet in fewer than 40 words, and include the "
                             "keyword \"feud\".", "checks": [("word_count_max", 40), ("includes", ["feud"])]},
    {"id": "if20", "prompt": "Output a JSON array of exactly 5 prime numbers and nothing else.",
     "checks": [("json_array_len", 5)]},
]


def grade(case: dict, content: str) -> dict[str, bool]:
    return {name: bool(CHECKERS[name](content, *args)) for name, *args in case["checks"]}


def build_body(model: str, prompt: str, effort: str | None, max_tokens: int, temperature: float,
               sampling: dict) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens, **sampling}
    if effort:
        body["reasoning_effort"] = effort
    return body


def select_cases(only: str | None) -> list[dict]:
    if not only:
        return CASES
    wanted = {x.strip() for x in only.split(",")}
    unknown = wanted - {c["id"] for c in CASES}
    if unknown:
        raise SystemExit(f"if_probe: casos desconhecidos: {sorted(unknown)}")
    return [c for c in CASES if c["id"] in wanted]


def chat(base_url: str, body: dict, timeout: int) -> dict:
    req = Request(f"{base_url}/chat/completions", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    elapsed = time.time() - t0
    choice = data["choices"][0]
    content, reasoning = split_reasoning(choice["message"])
    return {"content": content, "reasoning_chars": len(reasoning), "finish_reason": choice.get("finish_reason"),
            "completion_tokens": data.get("usage", {}).get("completion_tokens"), "elapsed_s": round(elapsed, 2)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--reasoning-effort", default="xhigh")
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--min-p", type=float, default=None)
    ap.add_argument("--presence-penalty", type=float, default=None)
    ap.add_argument("--repetition-penalty", type=float, default=None)
    ap.add_argument("--only", default=None, help="ids separados por vírgula (ex.: if07)")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    sampling = {k: v for k, v in {"top_p": a.top_p, "top_k": a.top_k, "min_p": a.min_p,
                                  "presence_penalty": a.presence_penalty,
                                  "repetition_penalty": a.repetition_penalty}.items() if v is not None}
    cases = select_cases(a.only)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    passed = total = 0
    with out.open("w", encoding="utf-8") as f:
        for rep in range(1, a.repeat + 1):
            for case in cases:
                body = build_body(a.model, case["prompt"], a.reasoning_effort, a.max_tokens, a.temperature, sampling)
                try:
                    r = chat(a.base_url, body, a.timeout)
                    checks = grade(case, r["content"])
                    err = None
                except OSError as e:  # URLError e timeouts: o caso conta como erro, a sonda segue
                    r = {"content": "", "reasoning_chars": 0, "finish_reason": "error", "completion_tokens": None,
                         "elapsed_s": None}
                    checks = {name: False for name, *_ in case["checks"]}
                    err = str(e)
                ok = all(checks.values())
                passed += ok
                total += 1
                rec = {"arm": a.arm, "id": case["id"], "rep": rep, "passed": ok, "checks": checks, "error": err,
                       "reasoning_effort": a.reasoning_effort, "temperature": a.temperature, "sampling": sampling,
                       "content_preview": r["content"][:300],
                       **{k: r[k] for k in ("elapsed_s", "completion_tokens", "reasoning_chars", "finish_reason")}}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"{case['id']} r{rep}: {'PASS' if ok else 'FAIL'} {checks} {r['elapsed_s']}s", flush=True)
    print(f"strict {passed}/{total} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar os testes**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests/test_if_probe.py -q`
Expected: PASS (24 testes).

- [ ] **Step 5: Commit**

```bash
git add bench/swift15-flashnext-2026-10/scripts/if_probe.py bench/swift15-flashnext-2026-10/tests/test_if_probe.py
git commit -m "bench(swift15): sonda de instruction-following (20 casos verificáveis)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Consolidador do A/B (`summarize_ab.py`)

**Files:**
- Create: `bench/swift15-flashnext-2026-10/scripts/summarize_ab.py`
- Create: `bench/swift15-flashnext-2026-10/tests/test_summarize_ab.py`

**Interfaces:**
- Consumes: `results/ab/<perfil>/<braço>/<suíte>.jsonl`, gravados pela Task 8, com perfil `t0` ou `t1`. O consolidador roda uma vez por perfil, com `--ab-dir results/ab/<perfil>`. As suítes são `humaneval`, `gpqa`, `livecodebench`, `jdhodges`, `veerman` e `if`. Os campos vêm do `bench2.py` (Task 4), do `tool_call_bench.py` e do `if_probe.py` (Task 6).
- Produces:
  - `view(suite, rec) -> dict`, com `id, passed, elapsed_s, completion_tokens, reasoning_chars, truncated`.
  - `suite_stats(views) -> dict`, com `n, passed, truncated, total_s, median_s, median_completion, median_reasoning_chars`.
  - `load_arm(path) -> dict[str, list[dict]]`.
  - `gates(base, cand) -> dict[str, bool]`.
  - `render(stats, gate_result, base, cand) -> str` (markdown).
  - CLI: `summarize_ab.py --ab-dir DIR --base n2 --cand w1 [--out PATH]`.

**Gates (proposta; o usuário confirma na revisão do plano):**
- **G1 qualidade:** para cada suíte, `passed(w1) ≥ passed(n2) − margem`. Margens: humaneval 3, gpqa 3, livecodebench 3, jdhodges 2, veerman 1, if 2.
- **G2 thinking:** `median_s(w1) ≤ 0,8 × median_s(n2)` em gpqa e em livecodebench.
- O G3 (velocidade, `T_turno ≤ 1,03 × n2`) fica na Task 9, porque vem de outro harness.
- G1 e G2 são calculados separadamente para t0 e para t1. A regra de decisão que junta os dois perfis fica na Task 9.

- [ ] **Step 1: Escrever os testes que falham**

`bench/swift15-flashnext-2026-10/tests/test_summarize_ab.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import summarize_ab as S  # noqa: E402


def b2(idx, ok, s, fin="stop", comp=100, rc=0):
    return {"dataset_idx": idx, "lcb_question_id": None, "correct": ok, "elapsed_s": s,
            "finish_reason": fin, "completion_tokens": comp, "reasoning_chars": rc}


def test_view_bench2_truncation_is_failure_and_flagged():
    v = S.view("gpqa", b2(7, False, 12.5, fin="length"))
    assert v == {"id": "7", "passed": False, "elapsed_s": 12.5, "completion_tokens": 100,
                 "reasoning_chars": 0, "truncated": True}


def test_view_accepts_string_booleans_and_numbers():
    v = S.view("humaneval", {"dataset_idx": "3", "correct": "True", "elapsed_s": "2.5",
                             "finish_reason": "stop", "completion_tokens": "163"})
    assert v["passed"] is True and v["elapsed_s"] == 2.5 and v["completion_tokens"] == 163


def test_view_tool_suite_sums_both_turns():
    v = S.view("jdhodges", {"case_id": "c1", "score_pass": True, "turn_1_elapsed_s": 1.0,
                            "turn_2_elapsed_s": 2.0, "turn_1_finish_reason": "tool_calls", "completion_tokens": 50})
    assert v["elapsed_s"] == 3.0 and v["passed"] is True and v["truncated"] is False


def test_view_lcb_uses_question_id():
    v = S.view("livecodebench", {"dataset_idx": 1, "lcb_question_id": "abc123", "correct": True,
                                 "elapsed_s": 1, "finish_reason": "stop"})
    assert v["id"] == "abc123"


def test_suite_stats():
    st = S.suite_stats([S.view("gpqa", b2(1, True, 10)), S.view("gpqa", b2(2, False, 30, fin="length")),
                        S.view("gpqa", b2(3, True, 20))])
    assert st["n"] == 3 and st["passed"] == 2 and st["truncated"] == 1
    assert st["total_s"] == 60.0 and st["median_s"] == 20.0


def _arm(tmp_path, arm, suites):
    d = tmp_path / arm
    d.mkdir()
    for suite, recs in suites.items():
        (d / f"{suite}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    return S.load_arm(d)


def test_mismatched_question_sets_are_refused(tmp_path):
    base = _arm(tmp_path, "n2", {"gpqa": [b2(1, True, 10)]})
    cand = _arm(tmp_path, "w1", {"gpqa": [b2(2, True, 10)]})
    with pytest.raises(ValueError, match="gpqa"):
        S.compare(base, cand)


def test_gates(tmp_path):
    base = _arm(tmp_path, "n2", {"gpqa": [b2(i, True, 100) for i in range(10)],
                                 "livecodebench": [b2(i, True, 100) for i in range(10)]})
    cand = _arm(tmp_path, "w1", {"gpqa": [b2(i, i > 2, 70) for i in range(10)],
                                 "livecodebench": [b2(i, True, 90) for i in range(10)]})
    stats = S.compare(base, cand)
    g = S.gates(stats["base"], stats["cand"])
    assert g["G1:gpqa"] is True            # 7 >= 10 - 3
    assert g["G1:livecodebench"] is True
    assert g["G2:gpqa"] is True            # 70 <= 0.8 * 100
    assert g["G2:livecodebench"] is False  # 90 > 80
```

- [ ] **Step 2: Rodar e ver a falha**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests/test_summarize_ab.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'summarize_ab'`).

- [ ] **Step 3: Implementar**

`bench/swift15-flashnext-2026-10/scripts/summarize_ab.py`:

```python
#!/usr/bin/env python3
"""Consolida o A/B n2 × w1: nota, truncamentos, tempo e tokens por suíte, e os gates G1 (qualidade) e G2 (thinking)."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

SUITES = ("humaneval", "gpqa", "livecodebench", "jdhodges", "veerman", "if")
TOOL_SUITES = {"jdhodges", "veerman"}
QUALITY_MARGIN = {"humaneval": 3, "gpqa": 3, "livecodebench": 3, "jdhodges": 2, "veerman": 1, "if": 2}
TIME_SUITES = ("gpqa", "livecodebench")
TIME_RATIO = 0.8


def _true(v) -> bool:
    return v is True or str(v) == "True"


def _num(v, cast=float):
    if v in (None, "None", ""):
        return cast(0)
    return cast(float(v))


def view(suite: str, r: dict) -> dict:
    if suite in TOOL_SUITES:
        rid, ok = r["case_id"], _true(r.get("score_pass"))
        elapsed = _num(r.get("turn_1_elapsed_s")) + _num(r.get("turn_2_elapsed_s"))
        fin = r.get("turn_1_finish_reason")
    elif suite == "if":
        rid, ok, elapsed, fin = r["id"], _true(r.get("passed")), _num(r.get("elapsed_s")), r.get("finish_reason")
    else:
        rid = r.get("lcb_question_id") if suite == "livecodebench" else r.get("dataset_idx")
        ok, elapsed, fin = _true(r.get("correct")), _num(r.get("elapsed_s")), r.get("finish_reason")
    return {"id": str(rid), "passed": ok, "elapsed_s": elapsed,
            "completion_tokens": _num(r.get("completion_tokens"), int),
            "reasoning_chars": _num(r.get("reasoning_chars"), int), "truncated": fin == "length"}


def suite_stats(views: list[dict]) -> dict:
    med = lambda k: round(statistics.median(v[k] for v in views), 1) if views else None  # noqa: E731
    return {"n": len(views), "passed": sum(v["passed"] for v in views),
            "truncated": sum(v["truncated"] for v in views),
            "total_s": round(sum(v["elapsed_s"] for v in views), 1), "median_s": med("elapsed_s"),
            "median_completion": med("completion_tokens"), "median_reasoning_chars": med("reasoning_chars")}


def load_arm(path: Path) -> dict[str, list[dict]]:
    out = {}
    for suite in SUITES:
        f = Path(path) / f"{suite}.jsonl"
        if f.is_file():
            out[suite] = [view(suite, json.loads(l)) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


def compare(base: dict[str, list[dict]], cand: dict[str, list[dict]]) -> dict:
    """Estatísticas das suítes presentes nos dois braços. Recusa questões diferentes."""
    stats = {"base": {}, "cand": {}}
    for suite in SUITES:
        if suite not in base or suite not in cand:
            continue
        ids_b, ids_c = {v["id"] for v in base[suite]}, {v["id"] for v in cand[suite]}
        if ids_b != ids_c:
            raise ValueError(f"{suite}: questões diferentes entre os braços "
                             f"(só na base: {sorted(ids_b - ids_c)[:5]}, só no candidato: {sorted(ids_c - ids_b)[:5]})")
        stats["base"][suite], stats["cand"][suite] = suite_stats(base[suite]), suite_stats(cand[suite])
    return stats


def gates(base: dict, cand: dict) -> dict[str, bool]:
    g = {}
    for suite in base:
        g[f"G1:{suite}"] = cand[suite]["passed"] >= base[suite]["passed"] - QUALITY_MARGIN[suite]
    for suite in TIME_SUITES:
        if suite in base:
            g[f"G2:{suite}"] = cand[suite]["median_s"] <= TIME_RATIO * base[suite]["median_s"]
    return g


def render(stats: dict, gate_result: dict, base: str, cand: str) -> str:
    lines = [f"| suíte | métrica | {base} | {cand} |", "| --- | --- | ---: | ---: |"]
    for suite, b in stats["base"].items():
        c = stats["cand"][suite]
        for key, label in (("passed", "acertos"), ("truncated", "truncadas"), ("median_s", "tempo mediano (s)"),
                           ("total_s", "tempo total (s)"), ("median_completion", "tokens medianos"),
                           ("median_reasoning_chars", "reasoning mediano (chars)")):
            val_b = f"{b[key]}/{b['n']}" if key == "passed" else b[key]
            val_c = f"{c[key]}/{c['n']}" if key == "passed" else c[key]
            lines.append(f"| {suite} | {label} | {val_b} | {val_c} |")
    lines += ["", "| gate | resultado |", "| --- | --- |"]
    lines += [f"| {k} | {'passa' if v else 'falha'} |" for k, v in gate_result.items()]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ab-dir", default=str(Path(__file__).resolve().parents[1] / "results" / "ab" / "t1"),
                    help="results/ab/<perfil>; default t1 (sampling do vendor)")
    ap.add_argument("--base", default="n2")
    ap.add_argument("--cand", default="w1")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    stats = compare(load_arm(Path(a.ab_dir) / a.base), load_arm(Path(a.ab_dir) / a.cand))
    md = render(stats, gates(stats["base"], stats["cand"]), a.base, a.cand)
    print(md)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar os testes**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bench/swift15-flashnext-2026-10/scripts/summarize_ab.py bench/swift15-flashnext-2026-10/tests/test_summarize_ab.py
git commit -m "bench(swift15): consolidador do A/B com gates de qualidade e thinking

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Runbook, bateria e smoke de reasoning

**Files:**
- Create: `bench/swift15-flashnext-2026-10/plan.md`
- Create: `bench/swift15-flashnext-2026-10/scripts/run-ab.sh`
- Create: `bench/swift15-flashnext-2026-10/scripts/ab-battery.sh`
- Modify: `bench/swift15-flashnext-2026-10/tests/test_arm_w1.py`

**Interfaces:**
- Consumes: `w1` e `--exec` (Tasks 1-2); `--reasoning-effort` (Tasks 4-5); `if_probe.py` (Task 6).
- Produces:
  - `run-ab.sh <n2|w1> [--profiles "t1 t0"] [--smoke] [--print]`. Ele sobe o braço uma vez, a 131072, e roda os perfis na ordem dada. O default é `"t1 t0"`: o perfil principal roda primeiro, e um run interrompido já deixa os dados de t1. A saída fica em `results/ab/<perfil>/<braço>/<suíte>.jsonl`.
  - Com `--smoke`, as suítes são `humaneval` (questões 1, 2 e 3) e `samplecheck` (`if07` três vezes). A saída fica em `results/ab-smoke/<perfil>/<braço>/`.
  - `ab-battery.sh --lib` só define `profile_flags <t0|t1>`, que imprime as flags de sampling do perfil.
  - Variáveis do `ab-battery.sh`: `AB_ARM`, `AB_PROFILES`, `AB_SUITES`, `AB_ONLY`, `AB_OUT_SUBDIR`, `AB_EFFORT`, `AB_BENCH`.

- [ ] **Step 1: Escrever o teste que falha**

Acrescente ao `test_arm_w1.py`:

```python
RUN_AB = HERE / "scripts" / "run-ab.sh"


def test_run_ab_print_wires_battery_through_exec():
    out = subprocess.run(["bash", str(RUN_AB), "w1", "--smoke", "--print"], capture_output=True, text=True,
                         env=_env(), check=True).stdout
    assert "exec: bash " in out and "ab-battery.sh" in out
    assert SWIFT in out
    assert "131072" in out


BATTERY = HERE / "scripts" / "ab-battery.sh"


def test_profile_flags_match_vendor_sampling():
    out = subprocess.run(["bash", "-c", f'source "{BATTERY}" --lib && profile_flags t1 && profile_flags t0'],
                         capture_output=True, text=True, env=_env(), check=True).stdout.splitlines()
    assert out == ["--temperature 1.0 --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0",
                   "--temperature 0"]


def test_profile_flags_refuses_unknown_profile():
    res = subprocess.run(["bash", "-c", f'source "{BATTERY}" --lib && profile_flags t2'],
                         capture_output=True, text=True, env=_env())
    assert res.returncode != 0 and "t2" in res.stderr


def test_run_ab_without_print_flag_survives_bash32_nounset():
    # O bash do rig é o 3.2: "${arr[@]}" de um array vazio com set -u aborta com "unbound variable".
    res = subprocess.run(["bash", "-n", str(RUN_AB)], capture_output=True, text=True)
    assert res.returncode == 0
    assert '${PRINT[@]+"${PRINT[@]}"}' in RUN_AB.read_text()
```

- [ ] **Step 2: Rodar e ver a falha**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests/test_arm_w1.py -q`
Expected: FAIL (`run-ab.sh` não existe).

- [ ] **Step 3: Criar `run-ab.sh`**

```bash
#!/usr/bin/env bash
# A/B de qualidade com reasoning explícito: sobe o braço (131072) pelo run-candidate.sh uma vez e roda
# ab-battery.sh contra ele, um perfil de sampling após o outro (default "t1 t0").
# --smoke roda só as questões 1-3 do HumanEval e o samplecheck (gate de reasoning e de sampling).
# uso: run-ab.sh <n2|w1> [--profiles "t1 t0"] [--smoke] [--print]
set -euo pipefail
ARM="${1:?uso: $0 <n2|w1> [--profiles \"t1 t0\"] [--smoke] [--print]}"; shift
SMOKE=""; PRINT=(); PROFILES="t1 t0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke) SMOKE=1; shift ;;
    --print) PRINT=(--print); shift ;;
    --profiles) PROFILES="$2"; shift 2 ;;
    *) echo "opcao desconhecida: $1" >&2; exit 64 ;;
  esac
done
case "$ARM" in n2|w1) ;; *) echo "braço fora do A/B: $ARM" >&2; exit 64 ;; esac
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AB_ARM="$ARM" AB_PROFILES="$PROFILES"
TAG=ab
if [[ -n "$SMOKE" ]]; then export AB_SUITES="humaneval samplecheck" AB_ONLY=1,2,3 AB_OUT_SUBDIR=ab-smoke; TAG=ab-smoke; fi
# bash 3.2 (o do rig): um array vazio com set -u precisa da forma ${arr[@]+...}.
exec bash "$HERE/scripts/run-arm.sh" "$ARM" 131072 --tag "$TAG" --exec "bash $HERE/scripts/ab-battery.sh" \
  ${PRINT[@]+"${PRINT[@]}"}
```

- [ ] **Step 4: Criar `ab-battery.sh`**

```bash
#!/usr/bin/env bash
# Roda as suítes do A/B contra o servidor pronto do run-candidate.sh (BASE_URL, MODEL_ID no ambiente), um
# perfil de sampling após o outro, e copia cada saída para results/<AB_OUT_SUBDIR>/<perfil>/<braço>/<suíte>.jsonl.
# `source ab-battery.sh --lib` só define profile_flags (para os testes).

# t1 = sampling recomendado pelo vendor (generation_config.json dos dois packs + card do Swift 1.5).
# t0 = greedy, o modo das baterias de qualidade anteriores.
profile_flags() {
  case "$1" in
    t1) echo "--temperature 1.0 --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0" ;;
    t0) echo "--temperature 0" ;;
    *) echo "ab-battery: perfil desconhecido: $1" >&2; return 64 ;;
  esac
}
[[ "${1:-}" == --lib ]] && return 0

set -euo pipefail
: "${BASE_URL:?}" "${MODEL_ID:?}" "${AB_ARM:?}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH="${AB_BENCH:-$HOME/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb}"
RUNS="$BENCH/benchmarks/runs"
EFFORT="${AB_EFFORT:-xhigh}"
PROFILES="${AB_PROFILES:-t1 t0}"
SUITES="${AB_SUITES:-humaneval gpqa livecodebench jdhodges veerman if}"
# 65K tokens a ~80 tok/s passam de 800 s: o timeout default (1800 s) fica curto com fila.
export BENCH_TIMEOUT="${BENCH_TIMEOUT:-3600}" TOOLBENCH_MAX_TOKENS="${TOOLBENCH_MAX_TOKENS:-32768}"
newest() { ls -t $RUNS/$1 2>/dev/null | grep -v '_summary\.json$' | head -1; }
rc=0
for p in $PROFILES; do
  FLAGS="$(profile_flags "$p")"
  OUT="$HERE/results/${AB_OUT_SUBDIR:-ab}/$p/$AB_ARM"; mkdir -p "$OUT"
  for s in $SUITES; do
    echo ">>> ab-battery: $AB_ARM $p $s (reasoning_effort=$EFFORT; $FLAGS)"
    case "$s" in
      humaneval|gpqa|livecodebench)
        if [[ "$s" == humaneval ]]; then n=164; mt=32768; else n=50; mt=65536; fi
        (cd "$BENCH" && LMSTUDIO_URL="$BASE_URL" .venv/bin/python scripts/bench2.py "$s" --examples "$n" \
          --model "$MODEL_ID" --max-tokens "$mt" --reasoning-effort "$EFFORT" $FLAGS \
          ${AB_ONLY:+--only "$AB_ONLY"}) || rc=$?
        cp "$(newest "${s}_*.jsonl")" "$OUT/$s.jsonl" ;;
      jdhodges|veerman)
        (cd "$BENCH" && uv run --no-project --with openai --with pyyaml python scripts/tool_call_bench.py \
          --model "$MODEL_ID" --suite "$s" --base-url "$BASE_URL" --run-prefix "toolcall_ab_${p}_$AB_ARM" \
          --no-cooldown --force --reasoning-effort "$EFFORT" $FLAGS) || rc=$?
        cp "$(newest "toolcall_ab_${p}_${AB_ARM}_${s}_*.jsonl")" "$OUT/$s.jsonl" ;;
      if)
        python3 "$HERE/scripts/if_probe.py" --base-url "$BASE_URL" --model "$MODEL_ID" --arm "$AB_ARM" \
          --reasoning-effort "$EFFORT" $FLAGS --output "$OUT/if.jsonl" || rc=$? ;;
      samplecheck)
        # Mesmo prompt 3 vezes: em t0 as respostas devem sair iguais; em t1, ao menos duas diferentes.
        python3 "$HERE/scripts/if_probe.py" --base-url "$BASE_URL" --model "$MODEL_ID" --arm "$AB_ARM" \
          --reasoning-effort "$EFFORT" $FLAGS --only if07 --repeat 3 --output "$OUT/samplecheck.jsonl" || rc=$? ;;
      *) echo "suíte desconhecida: $s" >&2; exit 64 ;;
    esac
  done
done
exit "$rc"
```

- [ ] **Step 5: Escrever o runbook**

`bench/swift15-flashnext-2026-10/plan.md`, com estas seções:

1. **Pergunta.** O Swift 1.5 (w1) mantém a qualidade do n2 e chega à resposta final mais rápido com thinking livre?
2. **Braços.** Copie as linhas do n2 e do w1 da seção Global Constraints deste plano.
3. **Por que o run de 07/10 não serve.** O `bench2.py` não enviava `reasoning_effort`. O n2 respondeu com 201 tokens por questão e 0 `<think>`.
4. **Bateria.** A tabela de suítes, `n`, `max_tokens` e a fonte de cada uma:

| suíte | n | max_tokens | runner |
| --- | ---: | ---: | --- |
| HumanEval | 164 | 32768 | `bench2.py humaneval` |
| GPQA-Diamond (amostra seed 42) | 50 | 65536 | `bench2.py gpqa` |
| LiveCodeBench v6 (amostra seed 42) | 50 | 65536 | `bench2.py livecodebench` |
| jdhodges | 40 | 32768 | `tool_call_bench.py` |
| Veerman | 12 | 32768 | `tool_call_bench.py` |
| IF (estilo IFEval) | 20 | 16384 | `if_probe.py` |

5. **Perfis de sampling.** Copie t1 e t0 da seção Global Constraints deste plano. Cada braço roda a bateria nos dois perfis, numa só subida do servidor, com t1 primeiro.
6. **Gates.** Copie G1 e G2 da Task 7, e G3 e a regra de decisão da Task 9.
7. **Ordem dos runs.** Smoke n2, smoke w1, bateria n2 (t1, t0), bateria w1 (t1, t0), `T_turno` (Task 9).
8. **Limites conhecidos.** Uma rodada por braço e perfil. Em t1, a amostragem tem variância: 1 a 3 questões de diferença ficam dentro do ruído. O t0 é o controle reproduzível. A sonda IF não é o IFBench.

- [ ] **Step 6: Rodar os testes e fazer o commit**

Run: `uv run --no-project --with pytest python -m pytest bench/swift15-flashnext-2026-10/tests -q`
Expected: PASS.

```bash
chmod +x bench/swift15-flashnext-2026-10/scripts/*.sh
git add bench/swift15-flashnext-2026-10/
git commit -m "bench(swift15): runbook, run-ab.sh e ab-battery.sh

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Smoke de reasoning no rig (gate)**

Pare o driver diário. Depois rode:

```bash
lsof -nP -iTCP:11234 -sTCP:LISTEN   # deve vir vazio
bash bench/swift15-flashnext-2026-10/scripts/run-ab.sh n2 --smoke
bash bench/swift15-flashnext-2026-10/scripts/run-ab.sh w1 --smoke
python3 - <<'EOF'
import json, statistics
base = "bench/swift15-flashnext-2026-10/results/ab-smoke"
for prof in ("t1", "t0"):
    for arm in ("n2", "w1"):
        R = [json.loads(l) for l in open(f"{base}/{prof}/{arm}/humaneval.jsonl")]
        comp = statistics.median(int(r["completion_tokens"]) for r in R)
        rc = max(int(r.get("reasoning_chars") or 0) for r in R)
        S = [json.loads(l) for l in open(f"{base}/{prof}/{arm}/samplecheck.jsonl")]
        distinct = len({s["content_preview"] for s in S})
        print(prof, arm, "n", len(R), "median completion", comp, "max reasoning_chars", rc,
              "temp", {r.get("temperature") for r in R}, "sampling", R[0].get("sampling"),
              "samplecheck distinct", distinct, "of", len(S))
EOF
```

Expected, para cada braço e perfil:
- `n 3`, e `median completion` > 500 ou `max reasoning_chars` > 0;
- t1: `temp {1.0}`, `sampling` com `top_p 0.95` e `top_k 20`, e `samplecheck distinct` ≥ 2 de 3;
- t0: `temp {0.0}`, `sampling {}`, e `samplecheck distinct` = 1 de 3.

**Pare a campanha** em dois casos:
- **O n2 continua com ~200 tokens e `reasoning_chars` 0.** Investigue como o mlx-serve 26.10.1 aceita o reasoning em requisição não-streaming. Compare com o `cache_probe.py`, que manda `reasoning_effort` por streaming e recebe `reasoning_content`.
- **O t1 dá 1 resposta distinta em 3.** O servidor provavelmente ignora a temperatura ou o sampling. Confira no `results/props/<nome>.json` e no log de boot quais parâmetros o mlx-serve aplica.

Um t0 com 2 ou 3 respostas distintas não para a campanha. Ele indica que o greedy do servidor não é determinístico, e esse fato vai para os limites do runbook.

- [ ] **Step 8: Commit do smoke**

```bash
git add bench/swift15-flashnext-2026-10/results/ab-smoke bench/swift15-flashnext-2026-10/results/props
git commit -m "bench(swift15): smoke de reasoning do n2 e do w1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Bateria completa e `T_turno`

**Files:**
- Create: `bench/swift15-flashnext-2026-10/results/ab/{t1,t0}/{n2,w1}/*.jsonl`
- Create: `bench/swift15-flashnext-2026-10/results/ab-summary-t1.md`, `ab-summary-t0.md`
- Create: `bench/swift15-flashnext-2026-10/results/{n2,w1}-{32768,131072}-t1.0-fn.jsonl`
- Create: `bench/swift15-flashnext-2026-10/results/summary.md`

**Interfaces:**
- Consumes: `run-ab.sh` (Task 8), `summarize_ab.py` (Task 7), `run-arm.sh` (Task 1), `summarize_driver.py` (existente).
- Produces: `results/summary.md` com o veredito G1, G2 e G3.

O tempo não foi medido. A estimativa usa ~80 tok/s e os tokens do card: ~6 a 8 h por braço e perfil, ou seja, ~12 a 16 h por braço com os dois perfis. O `T_turno` leva ~2 h. Se o tempo apertar, rode `--profiles t1` nos dois braços primeiro e o t0 depois.

- [ ] **Step 1: Bateria do n2 (t1, depois t0)**

```bash
caffeinate -i bash bench/swift15-flashnext-2026-10/scripts/run-ab.sh n2 \
  2>&1 | tee bench/swift15-flashnext-2026-10/logs/ab-n2.log
```

Expected: `>>> n2-131072-t1.0-ab: OK` no fim, e 6 arquivos em `results/ab/t1/n2/` e em `results/ab/t0/n2/`. O `t1.0` no nome vem do `--temperature` default do `run-candidate.sh`, que só vale para o probe; a bateria aplica o perfil próprio.

- [ ] **Step 2: Bateria do w1 (t1, depois t0)**

```bash
caffeinate -i bash bench/swift15-flashnext-2026-10/scripts/run-ab.sh w1 \
  2>&1 | tee bench/swift15-flashnext-2026-10/logs/ab-w1.log
```

Expected: `>>> w1-131072-t1.0-ab: OK` e 6 arquivos em `results/ab/t1/w1/` e em `results/ab/t0/w1/`.

- [ ] **Step 3: Consolidar o A/B por perfil**

```bash
du -h bench/swift15-flashnext-2026-10/results/ab/*/*/*.jsonl   # guideline: <= ~1 MB por arquivo
for p in t1 t0; do
  python3 bench/swift15-flashnext-2026-10/scripts/summarize_ab.py \
    --ab-dir bench/swift15-flashnext-2026-10/results/ab/$p \
    --out bench/swift15-flashnext-2026-10/results/ab-summary-$p.md
done
```

Expected: duas tabelas, cada uma com as 6 suítes e os gates `G1:*` e `G2:*`. Um `ValueError` de questões diferentes significa que um runner amostrou outro conjunto. Nesse caso, rode de novo a suíte do braço afetado com `AB_SUITES=<suíte>` e `--profiles <perfil>`.

Se um arquivo passar de ~1 MB, mova o original para `logs/`. Em `results/`, deixe uma cópia com `raw_response` cortado em 500 caracteres.

- [ ] **Step 4: `T_turno` dos dois braços na mesma sessão**

O baseline do n2 é medido de novo na mesma sessão, para não comparar com um baseline velho. A ordem a 128K é a inversa da de 32K.

```bash
R=bench/swift15-flashnext-2026-10/scripts/run-arm.sh
for spec in "n2 32768" "w1 32768" "w1 131072" "n2 131072"; do
  set -- $spec; rc=0
  bash "$R" "$1" "$2" --repeat 3 --tag fn || rc=$?
  echo "exit[$1@$2]=$rc"; sleep 120
done
python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py \
  --results-dir bench/swift15-flashnext-2026-10/results --glob '*-t1.0-fn.jsonl'
```

**G3 velocidade:** `T_turno(w1) ≤ 1,03 × T_turno(n2)` a 32K e a 128K. O `T_turno` já roda no perfil t1.

- [ ] **Step 5: Escrever `results/summary.md`**

Comece pelo veredito numa frase. Depois:
- as tabelas de `ab-summary-t1.md` e `ab-summary-t0.md`;
- a tabela de `T_turno`;
- o resultado de G1, G2 e G3 por perfil;
- a leitura: onde o w1 ganhou tempo, em que suíte perdeu nota, e se t0 e t1 concordam;
- os limites, copiados do runbook.

Regra de decisão (proposta; o t1 decide porque é o perfil do uso diário):
- **Promover o w1** se G1 e G2 passarem em t1, G1 passar em t0, e G3 passar.
- **Desempate:** se G1 de uma suíte passar num perfil e falhar no outro, rode de novo essa suíte em t1 nos dois braços (`AB_SUITES=<suíte> run-ab.sh <braço> --profiles t1`). Use a média das duas rodadas de t1.
- **Manter o n2** se G2 falhar em t1, porque não há ganho, ou se G1 falhar depois do desempate. Registre o trade-off.

- [ ] **Step 6: Commit**

```bash
git add bench/swift15-flashnext-2026-10/results
git commit -m "bench(swift15): A/B n2 × w1 com reasoning xhigh em t1 e t0, e T_turno; veredito

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Terminal-Bench no vencedor

**Files:**
- Create: `bench/terminal-bench/scripts/run-tbench-flashnext.sh`
- Modify: `bench/terminal-bench/plan.md` (linha do Flash-Next no placar)

**Interfaces:**
- Consumes: o veredito da Task 9 (`n2` ou `w1`) e `tools/scripts/serve-flashnext-daily-driver.sh` (perfil `daily`, override `FLASHNEXT_MODEL`).
- Produces: `bench/terminal-bench/logs/tbench-runs/flashnext-<braço>/`, com a nota no placar do `plan.md`.

O Terminal-Bench roda **só no perfil t1** (sampling do vendor). São 89 tarefas e várias horas por run, e t1 é o perfil do uso diário. Um run em t0 fica fora deste plano.

- [ ] **Step 1: Conferir quais kwargs o terminus-2 aceita**

```bash
harbor run --help | sed -n '/agent-kwarg/,/agent-env/p'
HP="$(python3 -c 'import harbor,pathlib;print(pathlib.Path(harbor.__file__).parent)' 2>/dev/null)"
grep -rn -E "reasoning_effort|temperature|top_p|top_k|extra_body|model_kwargs" "$HP" | grep -i terminus | head -20
```

Procure kwargs para `reasoning_effort`, `temperature`, `top_p` e para parâmetros extras do LiteLLM (`top_k`, `min_p`, `presence_penalty`, `repetition_penalty`).
- Passe com `--ak` todos os parâmetros do perfil t1 que o agente aceitar.
- Registre no `bench/terminal-bench/plan.md` cada parâmetro que o agente **não** aceita. Esse parâmetro fica no default do mlx-serve, e a nota vale para essa configuração.
- O card do Swift 1.5 rodou o Terminal-Bench com `temperature 1` e `top_p 1`. Essa nota não é comparável à nossa se o `top_p` diferir.

- [ ] **Step 2: Criar o script**

`bench/terminal-bench/scripts/run-tbench-flashnext.sh`:

```bash
#!/usr/bin/env bash
# Terminal-Bench 2.0 (89 tarefas, terminus-2) no driver Flash-Next servido pelo launcher diário.
# uso: run-tbench-flashnext.sh <n2|w1> [ak=valor ...]   (ex.: reasoning_effort=xhigh)
set -u
ARM="${1:?uso: $0 <n2|w1> [kwarg=valor ...]}"; shift
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
ROOT="$HOME/.cache/local-llms/qwen3.8-prefix-cache"
case "$ARM" in
  n2) MODEL="$ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a" ;;
  w1) MODEL="$ROOT/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0" ;;
  *) echo "braço fora do plano: $ARM" >&2; exit 64 ;;
esac
AK=(); for kv in "$@"; do AK+=(--ak "$kv"); done
LOGDIR="$REPO/bench/terminal-bench/logs"; mkdir -p "$LOGDIR/tbench-runs"
export OPENAI_API_BASE="http://127.0.0.1:11234/v1" OPENAI_API_KEY="local" DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

FLASHNEXT_MODEL="$MODEL" nohup bash tools/scripts/serve-flashnext-daily-driver.sh >"$LOGDIR/tbench-flashnext-$ARM-server.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; kill $(lsof -nP -tiTCP:11234 -sTCP:LISTEN) 2>/dev/null' EXIT
for _ in $(seq 1 200); do curl -fsS --max-time 3 "$OPENAI_API_BASE/models" >/dev/null 2>&1 && break; sleep 3; done
MODEL_ID="$(curl -fsS "$OPENAI_API_BASE/models" | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"][0]["id"])')"
echo "=== start $(date -Iseconds) arm=$ARM model=$MODEL_ID kwargs=$* ===" >> "$LOGDIR/tbench-flashnext-$ARM-driver.log"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL_ID" \
  --env docker -n 1 -y --quiet \
  --agent-timeout-multiplier 0.5 \
  ${AK[@]+"${AK[@]}"} \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name "flashnext-$ARM" \
  > "$LOGDIR/tbench-flashnext-$ARM.log" 2>&1
RC=$?
echo "=== done $(date -Iseconds) rc=$RC ===" >> "$LOGDIR/tbench-flashnext-$ARM-driver.log"
exit $RC
```

- [ ] **Step 3: Dry check e commit**

```bash
bash -n bench/terminal-bench/scripts/run-tbench-flashnext.sh && echo sintaxe-ok
chmod +x bench/terminal-bench/scripts/run-tbench-flashnext.sh
git add bench/terminal-bench/scripts/run-tbench-flashnext.sh
git commit -m "bench(terminal-bench): driver do Flash-Next (n2 ou w1) via launcher diário

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Rodar no rig**

Abra o Docker Desktop e pare o driver diário. Depois rode:

```bash
caffeinate -i bash bench/terminal-bench/scripts/run-tbench-flashnext.sh <vencedor> \
  reasoning_effort=xhigh temperature=1.0 top_p=0.95
```

Use os nomes de kwargs que o Step 1 encontrou. Acrescente `top_k=20`, `min_p=0`, `presence_penalty=0` e `repetition_penalty=1.0` se o agente aceitar parâmetros extras. Omita o kwarg que o agente não aceitar. O run leva várias horas; o 27B denso levou ~30 h.

- [ ] **Step 5: Registrar a nota**

Leia o resultado em `bench/terminal-bench/logs/tbench-runs/flashnext-<braço>/` (resolvidas / 89). Acrescente a linha ao placar do `bench/terminal-bench/plan.md`, com data, runtime, pesos e modo de reasoning. As referências são Qwen3.6-27B 31,5% e Qwen3.8-27B 21,3%.

```bash
git add bench/terminal-bench/plan.md
git commit -m "bench(terminal-bench): Flash-Next <braço> — <nota>% (89 tarefas)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Docs, backlog e memória

**Files:**
- Modify: `docs/models/qwen3.8-flash-next.md` (cabeçalho, "Stacks compared", "Known issues")
- Modify: `docs/superpowers/plans/backlog-uncensored-models.md`
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/TODO.md` (item "Qualidade do n2 com a mesma config")

**Interfaces:**
- Consumes: `results/summary.md` (Task 9) e a nota do Terminal-Bench (Task 10).

- [ ] **Step 1: Atualizar o card do modelo (em inglês)**

- Em "Stacks compared", acrescente a linha do Swift 1.5 @ mlx-serve 26.10.1, com `T_turno` 32K/128K e o veredito.
- Em "Known issues", troque "Agent quality is unmeasured" pela nota do Terminal-Bench, com data e modo de reasoning.
- Se o w1 for promovido, troque também o cabeçalho, a tabela de config e o default de `FLASHNEXT_MODEL` em `tools/scripts/serve-flashnext-daily-driver.sh`. Mencione a licença Swift Open License v1.0.

- [ ] **Step 2: Atualizar o backlog uncensored**

Em `docs/superpowers/plans/backlog-uncensored-models.md`, troque a linha do ARC4NUM por:

```markdown
- [x] Testar ARC4NUM Flash-Next MLX-Serve 4-bit no rig M4 Max 128 GB — Etapa U, braço u1
  (`bench/qwen38-flashnext-daily-driver-2026-09/results/etapa-u.md`): responsividade igual ao c1;
  0/50 over-refusal; 0/24 recusas em prompts nocivos (c1: 7/24). Alternativo, não upgrade.
```

E marque `[x]` em "Confirmar se os repos carregam sem erro no `mlx-serve`" só para o ARC4NUM (26.9.2). Deixe o orcarouter 27B aberto.

- [ ] **Step 3: Fechar o item do TODO**

Marque `[x]` em **Qualidade do n2 com a mesma config** e cite `bench/swift15-flashnext-2026-10/results/ab-summary-t1.md` e `ab-summary-t0.md`.

- [ ] **Step 4: Commit e PR**

```bash
git add docs/models/qwen3.8-flash-next.md docs/superpowers/plans/backlog-uncensored-models.md \
        bench/qwen38-flashnext-daily-driver-2026-09/TODO.md tools/scripts/serve-flashnext-daily-driver.sh
git commit -m "docs(flash-next): veredito do A/B Swift 1.5 e nota do Terminal-Bench; backlog uncensored

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin bench/swift15-flashnext-2026-10
```

Abra o PR só quando o usuário pedir.

- [ ] **Step 5: Memória**

Crie `swift15-ab-verdict.md` (type project) com o veredito, os números de G1/G2/G3 e a nota do Terminal-Bench. Se o w1 for promovido, atualize `flashnext-mlxserve-current-driver.md`. Acrescente as linhas no `MEMORY.md`.
