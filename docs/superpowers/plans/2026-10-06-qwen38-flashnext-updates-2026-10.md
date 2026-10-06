# Flash-Next updates 2026-10 (mlx-serve 26.10.1 × pack iQ-MLX-4.7bpw) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir no M4 Max dois A/B de uma variável cada (runtime 26.9.2 → 26.10.1 com os mesmos pesos; pesos `mixed-4-8bit` → `iQ-MLX-4.7bpw` no mesmo runtime) e decidir o que o driver diário do Flash-Next passa a usar.

**Architecture:** A campanha nova `bench/qwen38-flashnext-updates-2026-10/` reaproveita o driver `run-candidate.sh` da campanha de 2026-09. O driver ganha três braços (`n1`, `n2`, `n2p`), um override de diretório de saída, uma checagem de versão do binário e um snapshot do `/props`. Um wrapper `run-arm.sh` aponta a saída para a campanha nova. A consolidação usa o `summarize_driver.py` existente. A qualidade dos pesos usa os runners do submódulo `tools/local-llm-bench-m4-32gb` e um comparador novo por item.

**Tech Stack:** bash, Python 3 stdlib, `pytest` via `uv run --no-project --with pytest`, `cache_probe.py`, mlx-serve, `uvx --from huggingface_hub hf`.

**Spec:** [bench/qwen38-flashnext-updates-2026-10/plan.md](../../../bench/qwen38-flashnext-updates-2026-10/plan.md)

## Global Constraints

- Máquina: o rig `macstudio` (M4 Max 128 GB). Todos os comandos rodam nele, a partir da raiz do worktree `.claude/worktrees/bench+flashnext-updates-2026-10`.
- Branch: `bench/flashnext-updates-2026-10`.
- mlx-serve 26.10.1: asset `mlx-serve-bin-macos-arm64.tar.gz`, SHA256 `e53056e481364ff72188fafea8b3eb0aeb0b5b7cebcd6e6e7d26bf1ce4223873`, instalado em `~/.local/opt/qwen38/mlx-serve-v26.10.1/`.
- Pesos n2: `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw` @ `dafff5c3d8168c9d13275661153911096499a80a`.
- `ngram_table.bin`: SHA256 `c8ab74bc343408cf3923d7d64b3698fbeb3e78c07ce7f85a650a8278731251d2`, 32 000 153 976 bytes, idêntico nos dois packs.
- Pesos c1/n1: `ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit` @ `ef5b919d31534faa1997666f1a22d362cd6383cd`.
- Config de todos os braços: `--mtp`, `--ssm-checkpoint-max 16`, prefix cache `16GB/100GB/64`, KV sem quantização, porta 11234.
- Perfil do probe: `temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning `xhigh`, limite 4096 tokens.
- Gates: hit ≥ 0.90 em `append` e `tool_turn`; needles corretas; swap delta ≤ 0.5 GB; zero HTTP 4xx/5xx; `[spec-stats]` no log.
- Paridade de `T_turno`: ±3%. Ganho de `--ple-gpu`: ≥ 5% a 128K.
- `~/.local/bin/mlx-serve` só muda no Task 9, e só se o veredito promover o 26.10.1.
- O `run-candidate.sh` apaga `~/.mlx-serve/kv-cache` e mata o que escuta na 11234. Parar o daily driver antes de qualquer run.
- Raw (`*.log`, boot logs, amostras de memória) fica em `bench/qwen38-flashnext-updates-2026-10/logs/` (gitignored). JSONL distilado e `.md` ficam em `results/`.
- Notas da campanha em PT. Qualquer coisa em `reports/` sai em inglês.

---

### Task 1: Instalar o mlx-serve 26.10.1 em ambiente isolado

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/results/install-mlx-serve-26.10.1.md`

**Interfaces:**
- Produces: binário `~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve` que imprime `mlx-serve 26.10.1` em `--version`.

- [ ] **Step 1: Baixar o tarball para um diretório vazio**

```bash
D="$(mktemp -d "${TMPDIR:-/tmp}/mlxserve-26.10.1.XXXX")"
curl -fL -o "$D/mlx-serve-bin-macos-arm64.tar.gz" \
  https://github.com/ddalcu/mlx-serve/releases/download/v26.10.1/mlx-serve-bin-macos-arm64.tar.gz
echo "$D"
```

- [ ] **Step 2: Verificar o SHA256 antes de extrair**

```bash
echo "e53056e481364ff72188fafea8b3eb0aeb0b5b7cebcd6e6e7d26bf1ce4223873  $D/mlx-serve-bin-macos-arm64.tar.gz" | shasum -a 256 -c
```

Expected: `…/mlx-serve-bin-macos-arm64.tar.gz: OK`. Se falhar, parar: não extrair.

- [ ] **Step 3: Ver a estrutura do tarball**

```bash
tar -tzf "$D/mlx-serve-bin-macos-arm64.tar.gz" | head -20
```

Expected: `mlx-serve`, `lib/…`, `LICENSE`, como em `~/.local/opt/qwen38/mlx-serve-v26.9.2/`. Se tudo estiver sob um diretório de topo, usar `--strip-components=1` no Step 4.

- [ ] **Step 4: Extrair no diretório isolado**

```bash
mkdir -p ~/.local/opt/qwen38/mlx-serve-v26.10.1
tar -xzf "$D/mlx-serve-bin-macos-arm64.tar.gz" -C ~/.local/opt/qwen38/mlx-serve-v26.10.1
ls ~/.local/opt/qwen38/mlx-serve-v26.10.1
```

Expected: `mlx-serve` e `lib/` direto no diretório.

- [ ] **Step 5: Verificar versão e flags**

```bash
B=~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve
"$B" --version 2>&1 | grep -E '^(mlx-serve|mlx) '
"$B" --help 2>&1 | grep -E -- '--ple-gpu|--mtp-greedy-tail|--kv-quant|--os-reserve-gib|--max-mtp-ctx'
ls -l ~/.local/bin/mlx-serve
```

Expected: `mlx-serve 26.10.1`; as cinco flags listadas; o symlink ainda aponta para `mlx-serve-v26.9.2`. Se `--ple-gpu` não aparecer, anotar o nome real no install md e usar esse nome no Task 3.

- [ ] **Step 6: Registrar a instalação**

Escrever `bench/qwen38-flashnext-updates-2026-10/results/install-mlx-serve-26.10.1.md` com: data, URL do asset, SHA256 verificado, saída de `--version` (versão do mlx-serve e do MLX), as linhas de `--help` do Step 5 e a frase "symlink `~/.local/bin/mlx-serve` mantido em 26.9.2".

- [ ] **Step 7: Commit**

```bash
git add bench/qwen38-flashnext-updates-2026-10/results/install-mlx-serve-26.10.1.md
git commit -m "bench(flashnext-updates): instala mlx-serve 26.10.1 isolado"
```

---

### Task 2: Baixar o pack iQ-MLX-4.7bpw reaproveitando a tabela n-gram

**Files:**
- Modify: `bench/qwen38-flashnext-updates-2026-10/results/install-mlx-serve-26.10.1.md` (seção "Pesos n2")

**Interfaces:**
- Produces: diretório `~/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a` com `config.json`, `model.safetensors.index.json`, shards e `ngram_table.bin`.

- [ ] **Step 1: Checar o disco**

```bash
df -h /
```

Expected: ≥ 60 GB livres (o download é ~43 GB). Se não houver, parar ([[check-disk-before-model-downloads]]).

- [ ] **Step 2: Criar o diretório e fazer hardlink da tabela n-gram**

```bash
ROOT=~/.cache/local-llms/qwen3.8-prefix-cache
SRC="$ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
DST="$ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
mkdir -p "$DST"
ln "$SRC/ngram_table.bin" "$DST/ngram_table.bin"
ls -li "$SRC/ngram_table.bin" "$DST/ngram_table.bin"
```

Expected: o mesmo inode nas duas linhas. O hardlink não ocupa espaço novo. Nenhum dos dois packs pode editar o arquivo no lugar; o mlx-serve só faz mmap de leitura.

- [ ] **Step 3: Baixar o resto do pack com a revisão pinada**

```bash
uvx --from huggingface_hub hf download ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw \
  --revision dafff5c3d8168c9d13275661153911096499a80a \
  --local-dir "$DST" --exclude ngram_table.bin
```

- [ ] **Step 4: Verificar o pack contra o HF**

```bash
shasum -a 256 "$DST/ngram_table.bin"
python3 - "$DST" <<'EOF'
import json, sys, urllib.request
from pathlib import Path
dst = Path(sys.argv[1])
url = ("https://huggingface.co/api/models/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw"
       "/revision/dafff5c3d8168c9d13275661153911096499a80a?blobs=true")
sib = json.load(urllib.request.urlopen(url))["siblings"]
bad = [(s["rfilename"], s.get("size"), (dst / s["rfilename"]).stat().st_size if (dst / s["rfilename"]).exists() else None)
       for s in sib if not (dst / s["rfilename"]).exists() or (dst / s["rfilename"]).stat().st_size != s.get("size")]
print(f"{len(sib)} arquivos no HF; divergentes: {bad}")
sys.exit(1 if bad else 0)
EOF
```

Expected: `c8ab74bc343408cf3923d7d64b3698fbeb3e78c07ce7f85a650a8278731251d2`; `divergentes: []`.

- [ ] **Step 5: Registrar e commitar**

Acrescentar ao install md uma seção "Pesos n2" com: repo, revisão, caminho local, "ngram_table.bin por hardlink do pack ef5b919 (mesmo SHA256)", saída do Step 4.

```bash
git add bench/qwen38-flashnext-updates-2026-10/results/install-mlx-serve-26.10.1.md
git commit -m "bench(flashnext-updates): baixa pack iQ-MLX-4.7bpw @ dafff5c"
```

---

### Task 3: Braços n1/n2/n2p no driver, wrapper da campanha e orquestrador da Etapa 1

**Files:**
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`
- Modify: `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh`
- Create: `bench/qwen38-flashnext-updates-2026-10/scripts/run-arm.sh`
- Create: `bench/qwen38-flashnext-updates-2026-10/scripts/run-etapa1.sh`
- Test: `bench/qwen38-flashnext-updates-2026-10/tests/test_run_arm.py`

**Interfaces:**
- Consumes: binário do Task 1, diretório de pesos do Task 2 (só em runtime; o `--print` não precisa deles).
- Produces:
  - `bash bench/qwen38-flashnext-updates-2026-10/scripts/run-arm.sh <c1|n1|n2|n2p> <ctx> [opções do run-candidate.sh]` grava `results/<arm>-<ctx>-t1.0[-tag].jsonl` e `results/props/<nome>.json` desta campanha.
  - `bash bench/qwen38-flashnext-updates-2026-10/scripts/run-etapa1.sh <32768|131072>` roda os três braços na ordem do plano, `--repeat 3 --tag ab`. Com `ETAPA1_DRY=1`, só imprime os comandos.
  - env `FLASHNEXT_RESULTS_DIR`, `FLASHNEXT_LOGS_DIR` (override de saída do `run-candidate.sh`), `MLX_SERVE_EXPECTED_VERSION` (checagem do binário), `QWEN38_MLX_PLE_GPU=1` (adiciona `--ple-gpu` no launcher).

- [ ] **Step 1: Escrever os testes**

`bench/qwen38-flashnext-updates-2026-10/tests/test_run_arm.py`:

```python
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
RUN_ARM = HERE / "scripts" / "run-arm.sh"
ETAPA1 = HERE / "scripts" / "run-etapa1.sh"
OLD_DRIVER = REPO / "bench" / "qwen38-flashnext-daily-driver-2026-09" / "scripts" / "run-candidate.sh"
DDALCU = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
IQ = "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "ETAPA1_"))}
    env.update(extra or {})
    return env


def print_cmd(script, arm, ctx="32768", extra_env=None):
    out = subprocess.run(["bash", str(script), arm, ctx, "--print"],
                         capture_output=True, text=True, env=_env(extra_env), check=True)
    return out.stdout


def test_n1_new_binary_incumbent_weights():
    out = print_cmd(RUN_ARM, "n1")
    assert "mlx-serve-v26.10.1/mlx-serve" in out
    assert DDALCU in out
    for flag in ("--mtp", "--prefix-cache-mem 16GB", "--prefix-cache-disk 100GB",
                 "--prefix-cache-entries 64", "--ssm-checkpoint-max 16", "--ctx-size 32768"):
        assert flag in out
    assert "--ple-gpu" not in out
    assert "--kv-quant" not in out
    assert "--runtime-revision v26.10.1 " in out


def test_n2_new_binary_iq_weights():
    out = print_cmd(RUN_ARM, "n2")
    assert "mlx-serve-v26.10.1/mlx-serve" in out
    assert IQ in out
    assert DDALCU not in out
    assert "--ple-gpu" not in out


def test_n2p_adds_ple_gpu_only():
    out = print_cmd(RUN_ARM, "n2p")
    assert IQ in out
    assert "--ple-gpu" in out
    assert "--runtime-revision v26.10.1-plegpu " in out


def test_c1_keeps_incumbent_binary():
    out = print_cmd(RUN_ARM, "c1")
    assert "mlx-serve-v26.9.2/mlx-serve" in out
    assert DDALCU in out
    assert "--ple-gpu" not in out


def test_run_arm_writes_to_this_campaign():
    out = print_cmd(RUN_ARM, "n1")
    assert f"saida: {HERE}/results/n1-32768-t1.0.jsonl" in out


def test_old_driver_default_output_unchanged():
    out = print_cmd(OLD_DRIVER, "c1")
    assert "qwen38-flashnext-daily-driver-2026-09/results/c1-32768-t1.0.jsonl" in out


def _dry(ctx):
    out = subprocess.run(["bash", str(ETAPA1), ctx], capture_output=True, text=True,
                         env=_env({"ETAPA1_DRY": "1"}), check=True)
    return [l.split()[2] for l in out.stdout.splitlines() if l.startswith("bash ")]


def test_etapa1_order_32k():
    assert _dry("32768") == ["c1", "n1", "n2"]


def test_etapa1_order_128k_reversed():
    assert _dry("131072") == ["n2", "n1", "c1"]


def test_etapa1_rejects_other_band():
    r = subprocess.run(["bash", str(ETAPA1), "262144"], capture_output=True, text=True,
                       env=_env({"ETAPA1_DRY": "1"}))
    assert r.returncode == 64
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest -q bench/qwen38-flashnext-updates-2026-10/tests/test_run_arm.py`
Expected: FAIL. `run-arm.sh` e `run-etapa1.sh` não existem.

- [ ] **Step 2b: Capturar o comando do c1 antes de editar**

```bash
bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh c1 131072 --print > "${TMPDIR:-/tmp}/c1-before.txt"
bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh u1 131072 --print > "${TMPDIR:-/tmp}/u1-before.txt"
```

O Step 8 compara contra estes arquivos.

- [ ] **Step 3: `--ple-gpu` no launcher**

Em `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh`, logo depois do bloco `QWEN38_MLX_MAX_MTP_CTX`, inserir:

```bash
# --ple-gpu (mlx-serve >= 26.10.1): tabela n-gram inteira na memória da GPU (~32 GB a mais).
# Off por default no binário; só o braço n2p da campanha flashnext-updates-2026-10 liga.
if [[ -n "${QWEN38_MLX_PLE_GPU:-}" ]]; then
  COMMAND+=(--ple-gpu)
fi
```

Se o Task 1 Step 5 mostrou outro nome de flag, usar esse nome.

- [ ] **Step 4: Override de saída, braços novos, checagem de versão e `/props` no `run-candidate.sh`**

4a. Na linha de uso (`CAND="${1:?uso: …`), trocar `<c1|c2|c3|c4|u1|u2>` por `<c1|c2|c3|c4|u1|u2|n1|n2|n2p>`. No comentário de cabeçalho, acrescentar a linha:

```bash
#   n1/n2/n2p = campanha flashnext-updates-2026-10 (mlx-serve 26.10.1; n2 = pack iQ-MLX-4.7bpw; n2p = n2 + --ple-gpu)
```

4b. Trocar a linha `RESULTS="$HERE/results"; LOGS="$HERE/logs"` por:

```bash
# Outra campanha pode reusar este driver apontando a saída para o próprio diretório.
RESULTS="${FLASHNEXT_RESULTS_DIR:-$HERE/results}"; LOGS="${FLASHNEXT_LOGS_DIR:-$HERE/logs}"
```

4c. Depois da linha `U2DIR=…`, acrescentar:

```bash
# Campanha flashnext-updates-2026-10: pack calibrado (mesmo layout do DDALCU) e runtime 26.10.1.
IQDIR="$MODEL_ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
MLXSERVE_26101="$HOME/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve"
```

4d. No case `c1)`, na linha `export QWEN38_MLX_SERVE_BIN=…v26.9.2/mlx-serve"`, acrescentar ` MLX_SERVE_EXPECTED_VERSION=26.9.2` ao mesmo `export`.

4e. Antes do case `c2|c3)`, inserir:

```bash
  n1|n2|n2p) # flashnext-updates-2026-10: runtime 26.10.1. n1 = pesos do c1; n2/n2p = pack iQ; n2p = + --ple-gpu.
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.1
      if [[ "$CAND" == n1 ]]; then
        MODEL_DIR="$DDALCU"; MODEL_REV=ef5b919d31534faa1997666f1a22d362cd6383cd
      else
        MODEL_DIR="$IQDIR"; MODEL_REV=dafff5c3d8168c9d13275661153911096499a80a
      fi
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve
      METRICS=""
      export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26101" MLX_SERVE_EXPECTED_VERSION=26.10.1
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      if [[ "$CAND" == n2p ]]; then
        export QWEN38_MLX_PLE_GPU=1; REV=v26.10.1-plegpu
      fi ;;
```

4f. Logo depois do bloco `if [[ -n "$PRINT" ]]; then … exit 0; fi`, inserir:

```bash
# O binário errado invalida o A/B inteiro: conferir a versão antes de subir o servidor.
if [[ -n "${MLX_SERVE_EXPECTED_VERSION:-}" ]]; then
  GOT_VERSION="$("$QWEN38_MLX_SERVE_BIN" --version 2>&1 | grep '^mlx-serve ' || true)"
  if [[ "$GOT_VERSION" != "mlx-serve $MLX_SERVE_EXPECTED_VERSION" ]]; then
    echo "run-candidate: $QWEN38_MLX_SERVE_BIN reporta '$GOT_VERSION', esperado 'mlx-serve $MLX_SERVE_EXPECTED_VERSION'" >&2
    exit 65
  fi
fi
```

4g. Depois da linha `echo ">>> $NAME: pronto. model_id=$MODEL_ID -> $OUT"`, inserir:

```bash
# /props (mlx-serve >= 26.9.4) mostra MTP, KV quant e PLD em vigor. O 26.9.2 não tem o endpoint.
if [[ "$RUNTIME" == mlx-serve ]]; then
  mkdir -p "$RESULTS/props"
  if curl -fsS --max-time 10 "$BASE/props" >"$RESULTS/props/$NAME.json" 2>/dev/null \
     || curl -fsS --max-time 10 "$BASE/v1/props" >"$RESULTS/props/$NAME.json" 2>/dev/null; then
    echo "    /props -> $RESULTS/props/$NAME.json"
  else
    rm -f "$RESULTS/props/$NAME.json"; echo "    /props indisponivel neste binario"
  fi
fi
```

- [ ] **Step 5: Wrapper da campanha**

`bench/qwen38-flashnext-updates-2026-10/scripts/run-arm.sh`:

```bash
#!/usr/bin/env bash
# Roda um braço da campanha flashnext-updates-2026-10 com o driver da campanha de 2026-09,
# gravando results/ e logs/ aqui. Mesmos argumentos do run-candidate.sh.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FLASHNEXT_RESULTS_DIR="$HERE/results" FLASHNEXT_LOGS_DIR="$HERE/logs"
exec bash "$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh" "$@"
```

- [ ] **Step 6: Orquestrador da Etapa 1**

`bench/qwen38-flashnext-updates-2026-10/scripts/run-etapa1.sh`:

```bash
#!/usr/bin/env bash
# Etapa 1: c1, n1 e n2 numa banda, 3 reps (plan.md, "Protocolo"). A ordem a 128K é a
# inversa da de 32K, para diluir deriva térmica e de page cache. ETAPA1_DRY=1 só imprime.
set -euo pipefail
CTX="${1:?uso: $0 <32768|131072>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "$CTX" in
  32768) ORDER=(c1 n1 n2) ;;
  131072) ORDER=(n2 n1 c1) ;;
  *) echo "banda fora do plano: $CTX" >&2; exit 64 ;;
esac
for arm in "${ORDER[@]}"; do
  cmd=(bash "$HERE/scripts/run-arm.sh" "$arm" "$CTX" --repeat 3 --tag ab)
  if [[ -n "${ETAPA1_DRY:-}" ]]; then
    echo "bash run-arm.sh $arm $CTX --repeat 3 --tag ab"; continue
  fi
  rc=0; "${cmd[@]}" || rc=$?
  [[ "$rc" -eq 0 ]] || echo ">>> $arm@$CTX saiu com $rc; ver results/ e logs/" >&2
done
```

O dry-run imprime `bash run-arm.sh <arm> …`; o teste lê o terceiro campo.

```bash
chmod +x bench/qwen38-flashnext-updates-2026-10/scripts/*.sh
```

- [ ] **Step 7: Rodar os testes novos e os da campanha de 2026-09**

Run:
```bash
uv run --no-project --with pytest python -m pytest -q bench/qwen38-flashnext-updates-2026-10/tests bench/qwen38-flashnext-daily-driver-2026-09/tests
```
Expected: todos PASS (os 70 antigos e os 9 novos).

- [ ] **Step 8: Conferir que os comandos do c1 e do u1 da campanha antiga não mudaram**

```bash
for a in c1 u1; do
  bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh $a 131072 --print > "${TMPDIR:-/tmp}/$a-after.txt"
  diff "${TMPDIR:-/tmp}/$a-before.txt" "${TMPDIR:-/tmp}/$a-after.txt" && echo "$a: igual"
done
```

Expected: `c1: igual` e `u1: igual`. O `export` de `MLX_SERVE_EXPECTED_VERSION` não aparece no `--print`.

- [ ] **Step 9: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh \
        bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh \
        bench/qwen38-flashnext-updates-2026-10/scripts bench/qwen38-flashnext-updates-2026-10/tests
git commit -m "bench(flashnext-updates): braços n1/n2/n2p, wrapper e orquestrador da Etapa 1"
```

---

### Task 4: Comparador de qualidade por item

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/scripts/compare_quality.py`
- Test: `bench/qwen38-flashnext-updates-2026-10/tests/test_compare_quality.py`

**Interfaces:**
- Consumes: JSONL do `bench2.py` (chave `question_num`, campo `correct`) e do `tool_call_bench.py` (chave `case_id`, campo `score_pass`).
- Produces: `python3 compare_quality.py --title T --name-a n1 --name-b n2 --key K --field F --a A.jsonl [...] --b B.jsonl [...]` imprime uma seção markdown. Funções `load(paths, key, field) -> dict`, `compare(a, b) -> dict`, `markdown(title, name_a, name_b, c) -> str`.

- [ ] **Step 1: Escrever os testes**

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_quality import load, compare, markdown  # noqa: E402


def write(tmp_path, name, rows):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p


def test_load_last_occurrence_wins(tmp_path):
    p1 = write(tmp_path, "a1.jsonl", [{"question_num": 1, "correct": False}])
    p2 = write(tmp_path, "a2.jsonl", [{"question_num": 1, "correct": True}])
    assert load([p1, p2], "question_num", "correct") == {1: True}


def test_load_skips_rows_without_key_or_field(tmp_path):
    p = write(tmp_path, "a.jsonl", [{"question_num": 1}, {"correct": True}, {"question_num": 2, "correct": True}])
    assert load([p], "question_num", "correct") == {2: True}


def test_compare_counts_and_discordant():
    a = {1: True, 2: True, 3: False, 4: True}
    b = {1: True, 2: False, 3: True, 5: True}
    c = compare(a, b)
    assert c["n"] == 3
    assert c["pass_a"] == 2 and c["pass_b"] == 2
    assert c["only_a"] == [2] and c["only_b"] == [3]
    assert c["missing_a"] == [5] and c["missing_b"] == [4]


def test_markdown_reports_delta():
    c = compare({1: True, 2: True}, {1: True, 2: False})
    md = markdown("HumanEval", "n1", "n2", c)
    assert "## HumanEval" in md
    assert "| n1 | 2/2 |" in md and "| n2 | 1/2 |" in md
    assert "n2 − n1: **-1**" in md
    assert "só n1 passa: 2" in md
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run --no-project --with pytest python -m pytest -q bench/qwen38-flashnext-updates-2026-10/tests/test_compare_quality.py`
Expected: FAIL com `ModuleNotFoundError: No module named 'compare_quality'`.

- [ ] **Step 3: Implementar**

```python
#!/usr/bin/env python3
"""Compara dois braços item a item (HumanEval ou tool-calling): totais, delta e itens discordantes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(paths, key: str, field: str) -> dict:
    out = {}
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if key in r and field in r:
                out[r[key]] = bool(r[field])  # a última ocorrência vence (re-run com --only)
    return out


def compare(a: dict, b: dict) -> dict:
    keys = sorted(a.keys() & b.keys(), key=str)
    return {
        "n": len(keys),
        "pass_a": sum(a[k] for k in keys),
        "pass_b": sum(b[k] for k in keys),
        "only_a": [k for k in keys if a[k] and not b[k]],
        "only_b": [k for k in keys if b[k] and not a[k]],
        "missing_a": sorted(b.keys() - a.keys(), key=str),
        "missing_b": sorted(a.keys() - b.keys(), key=str),
    }


def markdown(title: str, name_a: str, name_b: str, c: dict) -> str:
    fmt = lambda xs: ", ".join(str(x) for x in xs) or "—"
    return "\n".join([
        f"## {title}",
        "",
        "| braço | passa |",
        "|---|---:|",
        f"| {name_a} | {c['pass_a']}/{c['n']} |",
        f"| {name_b} | {c['pass_b']}/{c['n']} |",
        "",
        f"{name_b} − {name_a}: **{c['pass_b'] - c['pass_a']:+d}**".replace("+0", "0"),
        "",
        f"- só {name_a} passa: {fmt(c['only_a'])}",
        f"- só {name_b} passa: {fmt(c['only_b'])}",
        f"- faltam em {name_a}: {fmt(c['missing_a'])}; faltam em {name_b}: {fmt(c['missing_b'])}",
        "",
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--name-a", required=True)
    ap.add_argument("--name-b", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--a", nargs="+", required=True, type=Path)
    ap.add_argument("--b", nargs="+", required=True, type=Path)
    x = ap.parse_args(argv)
    c = compare(load(x.a, x.key, x.field), load(x.b, x.key, x.field))
    print(markdown(x.title, x.name_a, x.name_b, c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

O teste `n2 − n1: **-1**` espera o sinal de menos ASCII que o `%+d` produz.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run --no-project --with pytest python -m pytest -q bench/qwen38-flashnext-updates-2026-10/tests`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add bench/qwen38-flashnext-updates-2026-10/scripts/compare_quality.py bench/qwen38-flashnext-updates-2026-10/tests/test_compare_quality.py
git commit -m "bench(flashnext-updates): comparador de qualidade por item"
```

---

### Task 5: Etapa 0 — smoke a 8K de n1 e n2

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/results/n1-8192-t1.0-smoke.jsonl`, `…/n2-8192-t1.0-smoke.jsonl`, `…/props/n1-8192-t1.0-smoke.json`, `…/props/n2-8192-t1.0-smoke.json`, `…/etapa0-smoke.md`
- Modify (só se o Step 4 falhar): `bench/qwen38-flashnext-daily-driver-2026-09/scripts/attach_mtp.py`, `bench/qwen38-flashnext-daily-driver-2026-09/tests/test_attach_mtp.py`

**Interfaces:**
- Consumes: Tasks 1, 2 e 3.

- [ ] **Step 1: Parar o daily driver**

```bash
lsof -nP -iTCP:11234 -sTCP:LISTEN
```

Se houver processo, pará-lo de propósito (`kill <pid>`) e esperar a porta liberar.

- [ ] **Step 2: Rodar os dois smokes**

```bash
bash bench/qwen38-flashnext-updates-2026-10/scripts/run-arm.sh n1 8192 --scenarios cold,identical,tool_turn --tag smoke
bash bench/qwen38-flashnext-updates-2026-10/scripts/run-arm.sh n2 8192 --scenarios cold,identical,tool_turn --tag smoke
```

Expected: `>>> n1-8192-t1.0-smoke: OK` e `>>> n2-8192-t1.0-smoke: OK`. Exit 65 = binário errado (voltar ao Task 1). Exit 69 = servidor não subiu (ler `logs/<nome>-boot.log`).

- [ ] **Step 3: Conferir registros e `/props`**

```bash
cd bench/qwen38-flashnext-updates-2026-10
for a in n1 n2; do
  python3 -c "import json,sys;[print(r['scenario'],r['correct'],r['error'],r['cache_hit_ratio'],r['decode_tps'],r.get('mtp_acceptance')) for r in map(json.loads,open(sys.argv[1]))]" results/$a-8192-t1.0-smoke.jsonl
  python3 -m json.tool results/props/$a-8192-t1.0-smoke.json | grep -i -E 'mtp|kv|pld|ple' | head
done
cd -
```

Expected: 3 linhas por braço, `correct` True, `error` None, hit ≥ 0.90 em `identical` e `tool_turn`; o `/props` mostra MTP ligada e KV sem quantização. Se o `/props` não existir nos dois paths, registrar no `etapa0-smoke.md` e seguir.

- [ ] **Step 4: Conferir a telemetria de MTP**

```bash
grep -c '\[spec-stats\]' bench/qwen38-flashnext-updates-2026-10/logs/n1-8192-t1.0-smoke-boot.log
grep -c '\[spec-stats\]' bench/qwen38-flashnext-updates-2026-10/logs/n2-8192-t1.0-smoke-boot.log
```

Expected: ≥ 1 em cada, e `mtp_acceptance` não nulo no Step 3. Se der 0 ou nulo, o 26.10.1 mudou o formato do log:
1. `grep -i -m5 -E 'spec|accept|draft' <boot.log>` para achar a linha nova.
2. Em `test_attach_mtp.py`, acrescentar um teste que passa essa linha literal para `parse_spec_stats` e espera os valores dela.
3. Rodar e ver falhar; ajustar `SPEC_STATS_RE`/regexes em `attach_mtp.py` para aceitar os dois formatos; rodar todos os testes da campanha de 2026-09 e ver passar.
4. Re-anexar: `python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/attach_mtp.py --results <jsonl> --log <boot.log>` nos dois smokes.

- [ ] **Step 5: Registrar e commitar**

Escrever `results/etapa0-smoke.md`: por braço, load ok, cold TTFT, decode, hit, needles, `[spec-stats]` presente, campos relevantes do `/props`, pico wired do sampler.

```bash
git add bench/qwen38-flashnext-updates-2026-10/results
git commit -m "bench(flashnext-updates): Etapa 0 — smoke 8K de n1 e n2"
```

Checkpoint: se n1 ou n2 falhou no smoke, parar e diagnosticar com superpowers:systematic-debugging antes da Etapa 1.

---

### Task 6: Etapa 1 — banda 32K (c1 → n1 → n2)

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/results/{c1,n1,n2}-32768-t1.0-ab.jsonl`, `…/props/{n1,n2}-32768-t1.0-ab.json`

- [ ] **Step 1: Pré-condições**

Porta 11234 livre; `pmset -g therm` sem throttling; GPU < 50 °C (`sudo powermetrics` se disponível, senão esperar 10 min ocioso).

- [ ] **Step 2: Rodar a banda**

```bash
nohup bash bench/qwen38-flashnext-updates-2026-10/scripts/run-etapa1.sh 32768 \
  > bench/qwen38-flashnext-updates-2026-10/logs/etapa1-32768.log 2>&1 &
```

Duração esperada: ~1 h. Acompanhar com `tail -f` no log.

- [ ] **Step 3: Consolidar**

```bash
python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py \
  --results-dir bench/qwen38-flashnext-updates-2026-10/results --glob '*-32768-t1.0-ab.jsonl'
grep -c '\[spec-stats\]' bench/qwen38-flashnext-updates-2026-10/logs/{c1,n1,n2}-32768-t1.0-ab-boot.log
```

Expected: uma linha por braço com `T_turno`, sem gate falho. Nos três logs, contagem ≥ 1.

- [ ] **Step 4: Commit**

```bash
git add bench/qwen38-flashnext-updates-2026-10/results
git commit -m "bench(flashnext-updates): Etapa 1 — banda 32K (c1, n1, n2)"
```

Checkpoint: se um braço falhou num gate a 32K, parar e diagnosticar antes do Task 7.

---

### Task 7: Etapa 1 — banda 128K (n2 → n1 → c1)

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/results/{c1,n1,n2}-131072-t1.0-ab.jsonl`, `…/props/{n1,n2}-131072-t1.0-ab.json`

- [ ] **Step 1: Pré-condições**

As mesmas do Task 6, Step 1.

- [ ] **Step 2: Rodar a banda**

```bash
nohup bash bench/qwen38-flashnext-updates-2026-10/scripts/run-etapa1.sh 131072 \
  > bench/qwen38-flashnext-updates-2026-10/logs/etapa1-131072.log 2>&1 &
```

Duração esperada: ~2–3 h (cold de ~180 s por braço, `middle_mutation` a 128K).

- [ ] **Step 3: Consolidar as duas bandas**

```bash
python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py \
  --results-dir bench/qwen38-flashnext-updates-2026-10/results --glob '*-t1.0-ab.jsonl' \
  --out bench/qwen38-flashnext-updates-2026-10/results/summary-etapa1.json
```

Expected: seis linhas (3 braços × 2 bandas).

- [ ] **Step 4: Commit**

```bash
git add bench/qwen38-flashnext-updates-2026-10/results
git commit -m "bench(flashnext-updates): Etapa 1 — banda 128K (n2, n1, c1)"
```

---

### Task 8: Etapa 2 — qualidade barata de n1 × n2

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/results/quality-n1-n2.md`

**Interfaces:**
- Consumes: `compare_quality.py` (Task 4); runners `tools/local-llm-bench-m4-32gb/scripts/bench2.py` e `tool_call_bench.py`; launcher `tools/scripts/serve-flashnext-daily-driver.sh` (aceita `FLASHNEXT_BIN` e `FLASHNEXT_MODEL`).

Os dois braços rodam no mesmo runtime 26.10.1, perfil `daily` (128K, mesmos flags), temp 0 (fixa nos runners). O `bench2.py` não manda `reasoning_effort`; o mlx-serve ≥ 26.9.5 trata isso como `low` com budget de 2048 tokens. É igual nos dois braços.

- [ ] **Step 1: Subir o n1**

```bash
ROOT=~/.cache/local-llms/qwen3.8-prefix-cache
export FLASHNEXT_BIN=~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve
FLASHNEXT_MODEL="$ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd" \
  nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily \
  > bench/qwen38-flashnext-updates-2026-10/logs/quality-n1-server.log 2>&1 &
until curl -fsS http://127.0.0.1:11234/v1/models >/dev/null 2>&1; do sleep 5; done
MID="$(curl -fsS http://127.0.0.1:11234/v1/models | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"][0]["id"])')"; echo "$MID"
```

- [ ] **Step 2: Smoke dos runners (2 problemas, 1 caso)**

```bash
cd tools/local-llm-bench-m4-32gb
LMSTUDIO_URL=http://127.0.0.1:11234/v1 python3 scripts/bench2.py humaneval --examples 2 --model "$MID"
uv run --no-project --with openai --with pyyaml python scripts/tool_call_bench.py \
  --model "$MID" --suite jdhodges --base-url http://127.0.0.1:11234/v1 --run-prefix toolcall_fnupd_smoke --no-cooldown \
  --only sel_weather_portland
cd -
```

Expected: o `bench2.py` grava `benchmarks/runs/humaneval_<MID>_<ts>.jsonl` com 2 linhas e `correct` preenchido. O `tool_call_bench.py` grava `benchmarks/runs/toolcall_fnupd_smoke_jdhodges_<slug>_<ts>.jsonl` com um caso e `score_pass`. `sel_weather_portland` é o primeiro id de `results/tool_calling/test_cases.yaml`. O prefixo `toolcall_fnupd_smoke` fica fora dos globs do Step 5. Se um runner quebrar por falta de módulo, acrescentar `--with <módulo>` ao `uv run`.

- [ ] **Step 3: Rodar a bateria do n1**

```bash
cd tools/local-llm-bench-m4-32gb
LMSTUDIO_URL=http://127.0.0.1:11234/v1 python3 scripts/bench2.py humaneval --examples 164 --model "$MID"
for s in jdhodges veerman; do
  uv run --no-project --with openai --with pyyaml python scripts/tool_call_bench.py \
    --model "$MID" --suite "$s" --base-url http://127.0.0.1:11234/v1 --run-prefix toolcall_fnupd_n1 --no-cooldown --force
done
cd -
```

Duração esperada: 2–3 h.

- [ ] **Step 4: Trocar para o n2 e repetir**

```bash
kill "$(lsof -nP -tiTCP:11234 -sTCP:LISTEN)"; while lsof -nP -iTCP:11234 -sTCP:LISTEN >/dev/null 2>&1; do sleep 1; done
FLASHNEXT_MODEL="$ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a" \
  nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily \
  > bench/qwen38-flashnext-updates-2026-10/logs/quality-n2-server.log 2>&1 &
until curl -fsS http://127.0.0.1:11234/v1/models >/dev/null 2>&1; do sleep 5; done
MID="$(curl -fsS http://127.0.0.1:11234/v1/models | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"][0]["id"])')"; echo "$MID"
```

Repetir o Step 3 com `--run-prefix toolcall_fnupd_n2`. Depois, parar o servidor.

- [ ] **Step 5: Comparar**

```bash
R=tools/local-llm-bench-m4-32gb/benchmarks/runs
C=bench/qwen38-flashnext-updates-2026-10/scripts/compare_quality.py
OUT=bench/qwen38-flashnext-updates-2026-10/results/quality-n1-n2.md
{
  echo "# Qualidade barata n1 × n2 (mlx-serve 26.10.1, temp 0, $(date +%F))"; echo
  python3 "$C" --title "HumanEval (164)" --name-a n1 --name-b n2 --key question_num --field correct \
    --a $R/humaneval_*mixed-4-8bit*.jsonl --b $R/humaneval_*iQ-MLX-4.7bpw*.jsonl
  for s in jdhodges veerman; do
    python3 "$C" --title "Tool-calling $s" --name-a n1 --name-b n2 --key case_id --field score_pass \
      --a $R/toolcall_fnupd_n1_${s}_*.jsonl --b $R/toolcall_fnupd_n2_${s}_*.jsonl
  done
} > "$OUT"
cat "$OUT"
```

Os globs excluem os arquivos `_summary.json` porque terminam em `.jsonl`. Se o smoke do Step 2 gravou um arquivo do n1, ele entra no glob do n1; o `load` deixa a última ocorrência vencer, então o resultado da bateria completa (mais recente) prevalece.

- [ ] **Step 6: Acrescentar a leitura ao md e commitar**

No fim do `quality-n1-n2.md`, uma seção "Leitura" com: o delta de cada bateria contra os limites do plano (HumanEval ≥ −2, tool-calling ≥ −1 caso somando jdhodges e Veerman), e a frase "164 problemas não separam a diferença publicada de 0.7 pp de top-1; este teste só pega regressão grande".

Os JSONL brutos ficam no submódulo e não entram nesta branch.

```bash
git add bench/qwen38-flashnext-updates-2026-10/results/quality-n1-n2.md
git commit -m "bench(flashnext-updates): Etapa 2 — qualidade barata n1 × n2"
```

---

### Task 9: Veredito e promoção

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/results/summary.md`
- Modify: `bench/qwen38-flashnext-updates-2026-10/plan.md` (linha de status no topo)
- Modify (se promovido): `tools/scripts/serve-flashnext-daily-driver.sh`, `docs/models/qwen3.8-flash-next.md`, symlink `~/.local/bin/mlx-serve`, memória `flashnext-mlxserve-current-driver.md`

- [ ] **Step 1: Escrever o `summary.md` em prosa**

Primeira frase = veredito das duas perguntas. Depois: tabela por banda (braço, `T_turno`, cold TTFT, warm TTFT do `tool_turn`, hit append/tool_turn, decode quente com faixa, wired pico, needles); a razão `T_turno` n1/c1 e n2/n1 por banda; o resultado do `quality-n1-n2.md`; os gates; o que não foi medido (efeito do thinking do 26.9.6 em agente real; fidelidade do pack; contexto > 128K).

- [ ] **Step 2: Aplicar os critérios do plano**

- Runtime: n1 passa nos gates e `T_turno(n1) ≤ 1.03 × T_turno(c1)` a 32K e 128K → promover 26.10.1.
- Pesos: n2 passa nos gates, `|T_turno(n2)/T_turno(n1) − 1| ≤ 0.03` nas duas bandas, HumanEval ≥ n1 − 2, tool-calling ≥ n1 − 1 → adotar o `iQ`.

- [ ] **Step 3 (se o runtime foi promovido): trocar o binário padrão**

```bash
ln -sfn ~/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve ~/.local/bin/mlx-serve
mlx-serve --version 2>&1 | grep '^mlx-serve '
```

Expected: `mlx-serve 26.10.1`. Rollback: o mesmo `ln -sfn` apontando para `mlx-serve-v26.9.2`.

- [ ] **Step 4 (se promovido): atualizar o launcher**

Em `tools/scripts/serve-flashnext-daily-driver.sh`, trocar o default de `BIN` para `$HOME/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve` (se o runtime foi promovido) e o de `MODEL` para o diretório do `iQ` (se os pesos foram adotados). Atualizar a linha 2 do cabeçalho com o par vigente. Conferir:

```bash
bash tools/scripts/serve-flashnext-daily-driver.sh --print
bash tools/scripts/serve-flashnext-daily-driver.sh 512k --print
```

Expected: os caminhos novos nos dois perfis; o 512k mantém `--kv-quant 8` e o YaRN. O perfil 512k não foi re-medido no 26.10.1: acrescentar ao cabeçalho a nota "512k medido no 26.9.2".

- [ ] **Step 5 (se promovido): atualizar o card**

Em `docs/models/qwen3.8-flash-next.md`: linhas Runtime e Weights da tabela, o comando do bloco de exemplo, e uma linha no histórico apontando para `bench/qwen38-flashnext-updates-2026-10/results/summary.md`. O checkout principal tem edições não commitadas neste arquivo: antes de editar, `git -C /Users/vitor/LocalProjects/local-llms diff -- docs/models/qwen3.8-flash-next.md` e avisar o usuário do conflito provável no merge.

- [ ] **Step 6: Status no plano da campanha e commit**

No topo de `bench/qwen38-flashnext-updates-2026-10/plan.md`, acrescentar `> **Status (AAAA-MM-DD): …** Veredito em [results/summary.md](results/summary.md).`

```bash
git add bench/qwen38-flashnext-updates-2026-10 tools/scripts/serve-flashnext-daily-driver.sh docs/models/qwen3.8-flash-next.md
git commit -m "bench(flashnext-updates): veredito runtime × pesos do driver diário"
```

- [ ] **Step 7: Atualizar a memória**

Atualizar `~/.claude/projects/-Users-vitor-LocalProjects-local-llms/memory/flashnext-mlxserve-current-driver.md` com o par vigente, a data e os `T_turno`, e a linha do índice em `MEMORY.md`.

---

### Task 10 (opcional): Etapa P — `--ple-gpu`

Rodar só depois do Task 9, e só se n2 foi adotado (senão, trocar n2p por um braço n1 + `--ple-gpu` e comparar contra o n1).

**Files:**
- Create: `bench/qwen38-flashnext-updates-2026-10/results/n2p-{32768,131072}-t1.0-ab.jsonl`, `…/etapa-p.md`

- [ ] **Step 1: Rodar as duas bandas**

```bash
bash bench/qwen38-flashnext-updates-2026-10/scripts/run-arm.sh n2p 32768 --repeat 3 --tag ab
bash bench/qwen38-flashnext-updates-2026-10/scripts/run-arm.sh n2p 131072 --repeat 3 --tag ab
grep -i -m3 'ple' bench/qwen38-flashnext-updates-2026-10/logs/n2p-131072-t1.0-ab-boot.log
```

Expected: o log confirma o PLE na GPU; o wired pico sobe ~32 GB em relação ao n2.

- [ ] **Step 2: Consolidar contra o n2**

```bash
python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py \
  --results-dir bench/qwen38-flashnext-updates-2026-10/results --glob 'n2*-t1.0-ab.jsonl'
```

- [ ] **Step 3: Decidir e registrar**

Vira perfil opcional só se `T_turno(n2p) ≤ 0.95 × T_turno(n2)` a 128K, swap delta ≤ 0.5 GB e nenhum cenário recusado. Escrever `results/etapa-p.md` com a tabela e a decisão. Se aprovado, acrescentar ao launcher um perfil `daily-plegpu` (mesmos flags do `daily` + `--ple-gpu`) e conferir com `--print`.

```bash
git add bench/qwen38-flashnext-updates-2026-10 tools/scripts/serve-flashnext-daily-driver.sh
git commit -m "bench(flashnext-updates): Etapa P — --ple-gpu"
```
