# Flash-Next driver diário responsivo — plano de execução

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir os 4 candidatos (quant × runtime) do Qwen3.8-Flash-Next no M4 Max e eleger o driver diário mais responsivo pelo `T_turno`, com summary, dashboard e publicação.

**Architecture:** Um driver único (`run-candidate.sh`) sobe cada runtime pelos launchers já existentes do harness `qwen3.8-prefix-cache`, roda o `cache_probe.py` com o perfil do vendor e anexa a telemetria de memória de um sampler novo. Um consolidador (`summarize_driver.py`) aplica os gates e calcula o `T_turno`; o dashboard lê o JSON consolidado sobre `reports/charts-common.js`.

**Tech Stack:** bash (drivers), Python 3 stdlib (sampler, consolidação, testes com `pytest`), `cache_probe.py` (harness existente), Chart.js via `charts-common.js`, git plumbing para a `gh-pages`.

**Spec:** [bench/qwen38-flashnext-daily-driver-2026-09/plan.md](../../../bench/qwen38-flashnext-daily-driver-2026-09/plan.md) — o runbook. Ler antes de qualquer task.

## Global Constraints

- Rig: Mac Studio M4 Max 128 GB. Teto wired do Metal: 107.5 GB (`iogpu.wired_limit_mb` default). Um servidor por vez.
- Runtimes pinados (não instalar nada): mlx-serve 26.9.2 em `~/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve`; oMLX 0.6.4 = `omlx` no PATH (`~/.local/share/uv/tools/omlx/bin/omlx`); oMLX 0.7.0.dev2 em `~/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/omlx`; MTPLX 2.11.2 em `~/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx`.
- Pesos (já em disco, `MODEL_ROOT=~/.cache/local-llms/qwen3.8-prefix-cache`):
  - c1 `ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd`
  - c2/c3 `Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8`
  - c4 `Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6`
- Harness: `bench/qwen3.8-prefix-cache/scripts/cache_probe.py`. Base HTTP sempre com sufixo `/v1`. `--temperature 1.0 --top-p 0.95 --top-k 20 --reasoning-effort xhigh` é o canônico; `--temperature 0` só nos diagnósticos.
- Cenários na ordem canônica `cold → identical → append → middle_mutation → tool_turn`; nunca um subconjunto sem `cold`.
- Contextos: 8192, 32768, 131072, 262144 (bandas); 524288 (sonda). 1M e `kv-quant turbo4` não rodam.
- Resultados em `bench/qwen38-flashnext-daily-driver-2026-09/results/` (≤ 1 MB por arquivo, versionados); logs em `logs/` (gitignored por `bench/**/logs/**`).
- Commits em português, mensagem `bench(flashnext-driver): …`, terminados com `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Não fazer push sem pedido explícito.
- Prosa dos documentos em português, estilo direto (uma ideia por frase).

---

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `bench/qwen38-flashnext-daily-driver-2026-09/plan.md` | runbook (já existe) |
| `…/scripts/mem-sampler.sh` | amostra wired/free/swap/RSS a cada 5 s em JSONL |
| `…/scripts/attach_memory.py` | anexa pico wired e swap delta da sessão a cada registro do JSONL do probe |
| `…/scripts/run-candidate.sh` | driver único: candidato × contexto × cenários × reps × temperatura |
| `…/scripts/compare_hashes.py` | lossless c2 vs c3 e MTP on/off do c4 (hash dos tokens de saída a temp 0) |
| `…/scripts/summarize_driver.py` | consolida `results/*.jsonl` → `results/summary.json` + tabelas markdown; aplica gates; calcula `T_turno` |
| `…/tests/test_attach_memory.py`, `test_summarize_driver.py`, `test_compare_hashes.py` | testes com registros sintéticos |
| `…/results/etapa0-smoke.md`, `etapa-a.md`, `sonda-512k.md`, `quant-fidelity.md`, `summary.md` | distilados por etapa e veredito |
| `bench/qwen3.8-prefix-cache/scripts/run-mtplx.sh` | ganha o arm `FX` (pack Flash-Next) |
| `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh` | ganha passthrough de `--config-overrides`, `--ssm-checkpoint-max`, `--max-mtp-ctx` |
| `reports/qwen38-flashnext-driver.html` | dashboard; `reports/README.md` ganha a linha |

---

### Task 0: Branch e esqueleto da campanha

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/{scripts,results,tests}/.gitkeep`
- Commit: `bench/qwen38-flashnext-daily-driver-2026-09/plan.md`, este plano

**Interfaces:**
- Produces: branch `bench/qwen38-flashnext-daily-driver-2026-09` a partir de `docs/flashnext-card-refresh` (essa branch contém o `run-mlx-serve.sh` com os defaults 16GB/100GB/64 no arm FS e o card atualizado; `main` ainda não).

- [ ] **Step 1: Criar a branch**

```bash
cd /Users/vitor/LocalProjects/local-llms
git checkout docs/flashnext-card-refresh
git checkout -b bench/qwen38-flashnext-daily-driver-2026-09
mkdir -p bench/qwen38-flashnext-daily-driver-2026-09/{scripts,results,tests,logs}
touch bench/qwen38-flashnext-daily-driver-2026-09/{scripts,results,tests}/.gitkeep
```

- [ ] **Step 2: Confirmar que `logs/` é ignorado e que o FS tem os defaults de cache**

Run: `git check-ignore -v bench/qwen38-flashnext-daily-driver-2026-09/logs/x.log && grep -n 'QWEN38_MLX_PREFIX_CACHE_MEM:-16GB' bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh`
Expected: uma linha do `.gitignore` (`bench/**/logs/**`) e uma linha do driver com `16GB`.

- [ ] **Step 3: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09 docs/superpowers/plans/2026-09-13-qwen38-flashnext-daily-driver.md
git commit -m "bench(flashnext-driver): abrir campanha — runbook e plano de execucao

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1: Sampler de memória

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/mem-sampler.sh`

**Interfaces:**
- Produces: JSONL com uma linha a cada 5 s: `{"t": <epoch>, "free_gb", "wired_gb", "compressor_gb", "swap_used_gb", "server_rss_gb", "server": "<nome>"}` — mesmo contrato do `mem-sampler.jsonl` da campanha anterior. Task 2 consome `wired_gb` e `swap_used_gb`.

- [ ] **Step 1: Escrever o sampler**

```bash
#!/usr/bin/env bash
# Amostra memoria do rig a cada N s em JSONL. Uso:
#   mem-sampler.sh <saida.jsonl> <nome-do-processo-servidor> [intervalo_s]
# Para com SIGTERM/SIGINT. Wired e o que o Metal pina; e o numero do gate de memoria.
set -euo pipefail
OUT="${1:?uso: $0 <saida.jsonl> <server-name> [intervalo]}"
SERVER="${2:?uso: $0 <saida.jsonl> <server-name> [intervalo]}"
INTERVAL="${3:-5}"
trap 'exit 0' TERM INT
mkdir -p "$(dirname "$OUT")"
while :; do
  python3 - "$OUT" "$SERVER" <<'PY'
import json, re, subprocess, sys, time
out, server = sys.argv[1], sys.argv[2]
vm = subprocess.check_output(["vm_stat"]).decode()
page = int(re.search(r"page size of (\d+)", vm).group(1))
def pages(label):
    m = re.search(label + r":\s+(\d+)\.", vm)
    return int(m.group(1)) * page / 1e9 if m else 0.0
swap = subprocess.check_output(["sysctl", "-n", "vm.swapusage"]).decode()
used = re.search(r"used = ([\d.]+)M", swap)
rss = 0.0
try:
    ps = subprocess.check_output(["ps", "-axo", "rss=,comm="]).decode()
    for line in ps.splitlines():
        kb, comm = line.strip().split(None, 1)
        if server in comm:
            rss += int(kb) / 1e6
except Exception:
    pass
rec = {
    "t": int(time.time()),
    "free_gb": round(pages("Pages free"), 2),
    "wired_gb": round(pages("Pages wired down"), 2),
    "compressor_gb": round(pages("Pages occupied by compressor"), 2),
    "swap_used_gb": round(float(used.group(1)) / 1024, 2) if used else 0.0,
    "server_rss_gb": round(rss, 2),
    "server": server,
}
with open(out, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(rec) + "\n")
PY
  sleep "$INTERVAL"
done
```

- [ ] **Step 2: Rodar 12 s e verificar o formato**

Run:
```bash
chmod +x bench/qwen38-flashnext-daily-driver-2026-09/scripts/mem-sampler.sh
bench/qwen38-flashnext-daily-driver-2026-09/scripts/mem-sampler.sh /tmp/mem-test.jsonl python3 5 & SP=$!; sleep 12; kill $SP; wc -l /tmp/mem-test.jsonl; head -1 /tmp/mem-test.jsonl | python3 -c 'import json,sys; r=json.load(sys.stdin); assert {"t","free_gb","wired_gb","swap_used_gb","server_rss_gb"} <= r.keys(); print("ok", r["wired_gb"])'
```
Expected: 2–3 linhas; `ok <wired em GB>`.

- [ ] **Step 3: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/mem-sampler.sh
git commit -m "bench(flashnext-driver): sampler de memoria wired/swap em JSONL

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Anexar memória aos registros do probe

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/attach_memory.py`
- Test: `bench/qwen38-flashnext-daily-driver-2026-09/tests/test_attach_memory.py`

**Interfaces:**
- Consumes: JSONL do sampler (Task 1) e JSONL do `cache_probe.py` (campos `ram_peak_gb`, `swap_delta_gb` chegam `null`).
- Produces: `attach_memory(records, samples) -> list[dict]` que preenche `ram_peak_gb` = pico de `wired_gb` e `swap_delta_gb` = último `swap_used_gb` − primeiro, mais `mem_free_min_gb`. CLI: `attach_memory.py --results X.jsonl --sampler Y.jsonl` (reescreve X in-place).

- [ ] **Step 1: Escrever o teste que falha**

```python
# bench/qwen38-flashnext-daily-driver-2026-09/tests/test_attach_memory.py
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from attach_memory import attach_memory  # noqa: E402


def test_attach_fills_peak_and_swap_delta():
    records = [{"run_id": "a", "ram_peak_gb": None, "swap_delta_gb": None}]
    samples = [
        {"t": 1, "wired_gb": 70.0, "free_gb": 30.0, "swap_used_gb": 1.7},
        {"t": 6, "wired_gb": 105.2, "free_gb": 0.4, "swap_used_gb": 1.7},
        {"t": 11, "wired_gb": 90.0, "free_gb": 5.0, "swap_used_gb": 2.2},
    ]
    out = attach_memory(records, samples)
    assert out[0]["ram_peak_gb"] == 105.2
    assert out[0]["swap_delta_gb"] == 0.5
    assert out[0]["mem_free_min_gb"] == 0.4


def test_attach_without_samples_keeps_null():
    out = attach_memory([{"run_id": "a", "ram_peak_gb": None, "swap_delta_gb": None}], [])
    assert out[0]["ram_peak_gb"] is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests/test_attach_memory.py -q`
Expected: FAIL com `ModuleNotFoundError: attach_memory`.

- [ ] **Step 3: Implementar**

```python
#!/usr/bin/env python3
"""Anexa pico de memoria wired e delta de swap (sampler) aos registros do cache_probe."""
import argparse, json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def attach_memory(records: list[dict], samples: list[dict]) -> list[dict]:
    if not samples:
        return records
    wired = [s["wired_gb"] for s in samples]
    free = [s["free_gb"] for s in samples]
    swap_delta = round(samples[-1]["swap_used_gb"] - samples[0]["swap_used_gb"], 2)
    for r in records:
        r["ram_peak_gb"] = max(wired)
        r["swap_delta_gb"] = swap_delta
        r["mem_free_min_gb"] = min(free)
        r["mem_samples"] = len(samples)
    return records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, type=Path)
    ap.add_argument("--sampler", required=True, type=Path)
    a = ap.parse_args()
    records = attach_memory(load_jsonl(a.results), load_jsonl(a.sampler) if a.sampler.exists() else [])
    a.results.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    print(f"{a.results}: {len(records)} registros, pico wired {records[0].get('ram_peak_gb') if records else None} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests/test_attach_memory.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/attach_memory.py bench/qwen38-flashnext-daily-driver-2026-09/tests/test_attach_memory.py
git commit -m "bench(flashnext-driver): anexar pico wired e swap delta aos registros

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Arm `FX` no `run-mtplx.sh` e passthrough no `run-mlx-serve.sh`

**Files:**
- Modify: `bench/qwen3.8-prefix-cache/scripts/run-mtplx.sh:14-24` (case dos arms) e o bloco `COMMAND=(` (linhas ~36–55)
- Modify: `bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh` (após o bloco `QWEN38_MLX_PREFILL_CHUNK`)

**Interfaces:**
- Produces: `run-mtplx.sh FX` sobe o pack Flash-Next; env novos `QWEN38_MTPLX_PROFILE` (default `turbo`), `QWEN38_MTPLX_DEPTH` (default `3`), `QWEN38_MTPLX_GENERATION_MODE` (default `mtp`); para FX o `--ssd-session-cache` default vira `on`. `run-mlx-serve.sh` aceita `QWEN38_MLX_CONFIG_OVERRIDES`, `QWEN38_MLX_SSM_CHECKPOINT_MAX`, `QWEN38_MLX_MAX_MTP_CTX`.

- [ ] **Step 1: Adicionar o arm FX ao `run-mtplx.sh`**

No `case "$ARM"`, antes do `*)`:

```bash
  FX) MODEL_REVISION="6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6"
      MODEL_NAME="Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed" ;;
```

Atualizar a mensagem de uso para `{V|Y|Z|FX}`. No bloco `COMMAND=(`, trocar as linhas fixas por env:

```bash
  --profile "${QWEN38_MTPLX_PROFILE:-turbo}"
  ...
  --depth "${QWEN38_MTPLX_DEPTH:-3}"
  --generation-mode "${QWEN38_MTPLX_GENERATION_MODE:-mtp}"
  --context-window "$CONTEXT_WINDOW"
  --ssd-session-cache "${QWEN38_MTPLX_SSD_SESSION_CACHE:-$MTPLX_SSD_DEFAULT}"
```

e, antes do `COMMAND=(`, definir o default por arm:

```bash
# FX (Flash-Next, pack MTPLX): o vendor roda SSD session cache ON e e o caminho seguro de memoria
# na linha 2.10+. Os arms da densa (V/Y/Z) mantem OFF para nao mudar a comparacao historica.
MTPLX_SSD_DEFAULT=off
[[ "$ARM" == "FX" ]] && MTPLX_SSD_DEFAULT=on
```

- [ ] **Step 2: Conferir o perfil recomendado pelo pack**

Run: `python3 -c "import json;d=json.load(open('$HOME/.cache/local-llms/qwen3.8-prefix-cache/Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6/mtplx_runtime.json'));print({k:d[k] for k in d if 'profile' in k or 'depth' in k or 'recommend' in k or 'serve' in k})"`
Expected: um dicionário. Se ele indicar perfil ou depth diferentes de `turbo`/`3`, registrar os valores em `results/etapa0-smoke.md` (Task 6) e exportá-los via `QWEN38_MTPLX_PROFILE`/`QWEN38_MTPLX_DEPTH` no driver da Task 4. Se vazio, ficam `turbo`/`3` e isso é registrado.

- [ ] **Step 3: Descobrir o nome do modo autoregressivo do MTPLX (para o controle `--no-mtp` do c4)**

Run: `~/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx serve --help 2>&1 | grep -A3 -- '--generation-mode'`
Expected: a lista de valores aceitos (um deles é `mtp`; outro é o modo sem especulação — o controle da campanha anterior chamou-o de "AR"). Anotar o valor exato; ele vai em `QWEN38_MTPLX_GENERATION_MODE` na Task 8.

- [ ] **Step 4: Passthrough no `run-mlx-serve.sh`**

Após o bloco `QWEN38_MLX_PREFILL_CHUNK`:

```bash
# Contexto estendido via YaRN (sonda 512K): JSON de --config-overrides, igual ao driver
# run-p1-mlxserve-extended.sh da campanha qwen38-updates-2026-09.
if [[ -n "${QWEN38_MLX_CONFIG_OVERRIDES:-}" ]]; then
  COMMAND+=(--config-overrides "$QWEN38_MLX_CONFIG_OVERRIDES")
fi
# Checkpoint do estado DeltaNet (a config de 1M da comunidade usa 16) e teto de contexto da MTP.
if [[ -n "${QWEN38_MLX_SSM_CHECKPOINT_MAX:-}" ]]; then
  COMMAND+=(--ssm-checkpoint-max "$QWEN38_MLX_SSM_CHECKPOINT_MAX")
fi
if [[ -n "${QWEN38_MLX_MAX_MTP_CTX:-}" ]]; then
  COMMAND+=(--max-mtp-ctx "$QWEN38_MLX_MAX_MTP_CTX")
fi
```

- [ ] **Step 5: Verificar os dois drivers com `--print`**

Run:
```bash
QWEN38_MTPLX_BIN=~/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx QWEN38_MTPLX_EXPECTED_VERSION=2.11.2 QWEN38_CTX_SIZE=8192 bash bench/qwen3.8-prefix-cache/scripts/run-mtplx.sh FX --print
QWEN38_MLX_SERVE_BIN=~/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve QWEN38_MLX_MODEL_DIR=$HOME/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd QWEN38_CTX_SIZE=524288 QWEN38_MLX_KV_QUANT=8 QWEN38_MLX_CONFIG_OVERRIDES='{"text_config":{"rope_parameters":{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":262144},"max_position_embeddings":524288}}' bash bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh FS --print
```
Expected: a 1ª linha mostra `Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e…`, `--ssd-session-cache on`, `--context-window 8192`; a 2ª mostra `--config-overrides {…yarn…}`, `--kv-quant 8`, `--prefix-cache-mem 16GB`. Nenhum servidor sobe.

- [ ] **Step 6: Commit**

```bash
git add bench/qwen3.8-prefix-cache/scripts/run-mtplx.sh bench/qwen3.8-prefix-cache/scripts/run-mlx-serve.sh
git commit -m "bench(flashnext-driver): arm FX (pack Flash-Next) no run-mtplx e YaRN/ssm/mtp-ctx no run-mlx-serve

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Driver único `run-candidate.sh`

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh`

**Interfaces:**
- Consumes: launchers `run-mlx-serve.sh FS`, `run-omlx.sh FN`, `run-mtplx.sh FX`; `mem-sampler.sh`; `attach_memory.py`; `cache_probe.py`.
- Produces: `results/<cand>-<ctx>-t<temp>[-<tag>].jsonl` (probe + memória), `logs/<cand>-<ctx>-<tag>-boot.log`, `logs/<cand>-<ctx>-<tag>-mem.jsonl`. CLI:
  `run-candidate.sh <c1|c2|c3|c4> <ctx> [--scenarios a,b] [--repeat N] [--temperature T] [--tag X] [--yarn F] [--generation-mode M] [--print]`.

- [ ] **Step 1: Escrever o driver**

```bash
#!/usr/bin/env bash
# Driver unico da campanha flashnext-daily-driver: sobe UM candidato, roda o cache_probe com o
# perfil do vendor, amostra memoria e derruba o servidor. Um candidato por vez.
#   c1 = ddalcu mixed-4/8 @ mlx-serve 26.9.2      c2 = Jundot oQ4e @ oMLX 0.6.4
#   c3 = Jundot oQ4e @ oMLX 0.7.0.dev2            c4 = MTPLX Optimized-Speed @ MTPLX 2.11.2
set -euo pipefail

CAND="${1:?uso: $0 <c1|c2|c3|c4> <ctx> [--scenarios a,b] [--repeat N] [--temperature T] [--tag X] [--yarn F] [--generation-mode M] [--print]}"
CTX="${2:?ctx obrigatorio}"; shift 2
SCENARIOS=""; REPEAT=1; TEMP=1.0; TAG=""; YARN=""; GENMODE=""; PRINT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenarios) SCENARIOS="$2"; shift 2 ;;
    --repeat) REPEAT="$2"; shift 2 ;;
    --temperature) TEMP="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --yarn) YARN="$2"; shift 2 ;;
    --generation-mode) GENMODE="$2"; shift 2 ;;
    --print) PRINT=1; shift ;;
    *) echo "opcao desconhecida: $1" >&2; exit 64 ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
HERE="$REPO/bench/qwen38-flashnext-daily-driver-2026-09"
RESULTS="$HERE/results"; LOGS="$HERE/logs"
MODEL_ROOT="$HOME/.cache/local-llms/qwen3.8-prefix-cache"
DDALCU="$MODEL_ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
OQ4E="$MODEL_ROOT/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
MTPLXPACK="$MODEL_ROOT/Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6"

# Por candidato: launcher, arm, porta, binario, python do probe, tokenizer, metrics.
case "$CAND" in
  c1) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.9.2
      MODEL_DIR="$DDALCU"; MODEL_REV=ef5b919d31534faa1997666f1a22d362cd6383cd
      PROBE_PY=python3; TOKENIZER=""; METRICS="http://127.0.0.1:$PORT/metrics"; SERVER_NAME=mlx-serve
      export QWEN38_MLX_SERVE_BIN="$HOME/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve"
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8
        export QWEN38_MLX_CONFIG_OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${YARN},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"
        REV="v26.9.2-yarn${YARN}-kv8"
      fi ;;
  c2|c3)
      LAUNCHER="$HARNESS/run-omlx.sh"; ARM=FN; PORT=8000; RUNTIME=omlx
      MODEL_DIR="$OQ4E"; MODEL_REV=2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=omlx
      export OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      if [[ "$CAND" == c2 ]]; then
        REV=v0.6.4; PROBE_PY="$HOME/.local/share/uv/tools/omlx/bin/python"
        export QWEN38_OMLX_BIN="$HOME/.local/share/uv/tools/omlx/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.6.4
      else
        REV=v0.7.0.dev2; PROBE_PY="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/python"
        export QWEN38_OMLX_BIN="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2
      fi ;;
  c4) LAUNCHER="$HARNESS/run-mtplx.sh"; ARM=FX; PORT=8000; RUNTIME=MTPLX; REV=v2.11.2
      MODEL_DIR="$MTPLXPACK"; MODEL_REV=6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6
      PROBE_PY="$HOME/.local/opt/qwen38/mtplx-v2.11.2/bin/python"; TOKENIZER="$MODEL_DIR"
      METRICS="http://127.0.0.1:$PORT/metrics"; SERVER_NAME=mtplx
      export QWEN38_MTPLX_BIN="$HOME/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx" QWEN38_MTPLX_EXPECTED_VERSION=2.11.2
      export QWEN38_CTX_SIZE="$CTX"
      [[ -n "$GENMODE" ]] && export QWEN38_MTPLX_GENERATION_MODE="$GENMODE"
      [[ -n "$GENMODE" && "$GENMODE" != mtp ]] && REV="v2.11.2-${GENMODE}" ;;
  *) echo "candidato desconhecido: $CAND" >&2; exit 64 ;;
esac
export QWEN38_MODEL_ROOT="$MODEL_ROOT"
BASE="http://127.0.0.1:$PORT"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="${CAND}-${CTX}-t${TEMP}${TAG:+-$TAG}"
OUT="$RESULTS/$NAME.jsonl"; BOOT="$LOGS/$NAME-boot.log"; MEM="$LOGS/$NAME-mem.jsonl"

if [[ -n "$PRINT" ]]; then
  echo "launcher: $LAUNCHER $ARM"; bash "$LAUNCHER" "$ARM" --print; echo
  echo "probe: $PROBE_PY cache_probe.py --base-url $BASE/v1 --runtime $RUNTIME --runtime-revision $REV --context $CTX --repeat $REPEAT --temperature $TEMP ${SCENARIOS:+--scenarios $SCENARIOS} ${TOKENIZER:+--tokenizer-path $TOKENIZER} ${METRICS:+--metrics-url $METRICS}"
  echo "saida: $OUT"; exit 0
fi

mkdir -p "$RESULTS" "$LOGS"
SERVER_PID=""; SAMPLER_PID=""
cleanup() {
  [[ -n "$SAMPLER_PID" ]] && kill "$SAMPLER_PID" 2>/dev/null || true
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

wait_port_free() { for _ in $(seq 1 30); do lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1 || return 0; sleep 1; done; echo "porta $PORT nao liberou" >&2; return 1; }
wait_mem_free() {
  local need="${1:-82}" free
  for _ in $(seq 1 24); do
    free="$(python3 -c 'import re,subprocess;o=subprocess.check_output(["vm_stat"]).decode();ps=int(re.search(r"page size of (\d+)",o).group(1));m=re.search(r"Pages free:\s+(\d+)\.",o);print(int(m.group(1))*ps/1e9)')"
    awk "BEGIN{exit !($free >= $need)}" && { echo "    memoria livre ~${free} GB (>= $need)"; return 0; }
    sleep 5
  done
  echo "    aviso: memoria nao assentou em 120s; seguindo" >&2
}
server_ready() { curl -fsS --max-time 3 "$BASE/v1/models" >/dev/null 2>&1; }

wait_port_free; wait_mem_free 82
# cold tem que ser frio: o disco de prefix-cache do mlx-serve persiste entre restarts (rodada 1 do P1
# foi descartada por isso). oMLX e MTPLX gravam sob logs/<run-id>, novo a cada subida.
if [[ -d "$HOME/.mlx-serve/kv-cache" ]]; then echo "    limpando ~/.mlx-serve/kv-cache"; rm -rf "$HOME/.mlx-serve/kv-cache/"* 2>/dev/null || true; fi

echo ">>> $NAME: sampler + servidor ($LAUNCHER $ARM)"
bash "$HERE/scripts/mem-sampler.sh" "$MEM" "$SERVER_NAME" 5 & SAMPLER_PID=$!
nohup bash "$LAUNCHER" "$ARM" >"$BOOT" 2>&1 & SERVER_PID=$!
ready=""
for _ in $(seq 1 200); do
  server_ready && { ready=1; break; }
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "servidor morreu no boot; ver $BOOT" >&2; exit 69; }
  sleep 3
done
[[ -n "$ready" ]] || { echo "servidor nao ficou pronto em 10 min; ver $BOOT" >&2; exit 69; }
MODEL_ID="$(curl -fsS "$BASE/v1/models" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])')"
echo ">>> $NAME: pronto. model_id=$MODEL_ID -> $OUT"

"$PROBE_PY" "$HARNESS/cache_probe.py" \
  --base-url "$BASE/v1" --model "$MODEL_ID" --api-model "$MODEL_ID" \
  --runtime "$RUNTIME" --runtime-revision "$REV" --model-revision "$MODEL_REV" \
  --arm "$CAND" --session-id "${TS}-${NAME}" \
  --context "$CTX" --content-class audit_retrieval --repeat "$REPEAT" \
  --temperature "$TEMP" --top-p 0.95 --top-k 20 --reasoning-effort xhigh \
  ${SCENARIOS:+--scenarios "$SCENARIOS"} \
  ${TOKENIZER:+--tokenizer-path "$TOKENIZER"} \
  ${METRICS:+--metrics-url "$METRICS"} \
  --output "$OUT" --cache-enabled $([[ "$GENMODE" == "" || "$GENMODE" == mtp ]] && echo --mtp-enabled)

kill "$SAMPLER_PID" 2>/dev/null || true; SAMPLER_PID=""
python3 "$HERE/scripts/attach_memory.py" --results "$OUT" --sampler "$MEM"
kill "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""; wait_port_free
echo ">>> $NAME: OK"
```

Nota: o `run-omlx.sh` não tem flag de contexto (o oMLX dimensiona por request); `QWEN38_CTX_SIZE` é ignorado por ele e serve só ao mlx-serve e ao MTPLX. O contexto do oMLX é o `--context` do probe.

- [ ] **Step 2: Dry-run dos 4 candidatos**

Run: `for c in c1 c2 c3 c4; do bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh $c 8192 --scenarios cold,identical,tool_turn --print; echo ---; done`
Expected: 4 blocos sem erro; c1 mostra `--prefix-cache-mem 16GB --ssm-checkpoint-max 16`; c2/c3 mostram binários diferentes; c4 mostra o pack Flash-Next e `--ssd-session-cache on`; nenhuma linha "unknown"/"missing".

- [ ] **Step 3: Confirmar que os pythons dos probes têm `transformers`**

Run: `for p in ~/.local/share/uv/tools/omlx/bin/python ~/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/python ~/.local/opt/qwen38/mtplx-v2.11.2/bin/python; do $p -c "import transformers; print('$p ok')"; done`
Expected: três `ok`.

- [ ] **Step 4: Commit**

```bash
chmod +x bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh
git commit -m "bench(flashnext-driver): driver unico por candidato (launcher + sampler + probe + memoria)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Aceitação da MTP nos `/metrics`

**Files:**
- Modify: `bench/qwen3.8-prefix-cache/scripts/cache_probe.py:235-250` (`mtp_acceptance_from_snapshots`)
- Test: `bench/qwen3.8-prefix-cache/tests/test_mtp_acceptance_aliases.py`

**Interfaces:**
- Consumes: `_metric_by_suffix(metrics, suffix)` já existente.
- Produces: `mtp_acceptance_from_snapshots(before, after)` que aceita também os sufixos reais do mlx-serve 26.9.2 (descobertos no Step 1). Campo `mtp_acceptance` deixa de ser `null` para o c1.

- [ ] **Step 1: Descobrir os nomes no mlx-serve (no rig, 8K, ~3 min)**

Run:
```bash
bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh c1 8192 --scenarios cold --tag metrics-probe &
sleep 240; curl -s http://127.0.0.1:11234/metrics | grep -i -E 'draft|mtp|spec|accept' | grep -v '^#' | head -20
wait
```
Expected: linhas Prometheus com contadores de draft/aceitação (nomes a copiar). Se nenhuma linha aparecer, o mlx-serve não expõe aceitação: registrar em `results/etapa0-smoke.md` e pular os Steps 2–4 (o campo fica `null` e o summary marca "n/d").

- [ ] **Step 2: Teste que falha com os nomes descobertos**

```python
# bench/qwen3.8-prefix-cache/tests/test_mtp_acceptance_aliases.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cache_probe import mtp_acceptance_from_snapshots  # noqa: E402


def test_mlx_serve_names_are_accepted():
    # Substituir pelos nomes reais do Step 1 (exemplo abaixo).
    before = {"mlx_serve_mtp_draft_accepted_total": 10.0, "mlx_serve_mtp_draft_proposed_total": 20.0}
    after = {"mlx_serve_mtp_draft_accepted_total": 40.0, "mlx_serve_mtp_draft_proposed_total": 60.0}
    assert mtp_acceptance_from_snapshots(before, after) == 0.75


def test_legacy_names_still_work():
    before = {"x_draft_tokens_accepted_total": 0.0, "x_draft_tokens_generated_total": 0.0}
    after = {"x_draft_tokens_accepted_total": 3.0, "x_draft_tokens_generated_total": 4.0}
    assert mtp_acceptance_from_snapshots(before, after) == 0.75
```

Run: `python3 -m pytest bench/qwen3.8-prefix-cache/tests/test_mtp_acceptance_aliases.py -q`
Expected: 1 FAIL (nomes novos), 1 PASS.

- [ ] **Step 3: Implementar os aliases**

```python
ACCEPTED_SUFFIXES = ("draft_tokens_accepted_total", "<sufixo real de aceitos do Step 1>")
GENERATED_SUFFIXES = ("draft_tokens_generated_total", "<sufixo real de propostos do Step 1>")


def _first_by_suffixes(metrics, suffixes):
    for suffix in suffixes:
        value = _metric_by_suffix(metrics, suffix)
        if value is not None:
            return value
    return None


def mtp_acceptance_from_snapshots(before, after):
    accepted_before = _first_by_suffixes(before, ACCEPTED_SUFFIXES) or 0.0
    generated_before = _first_by_suffixes(before, GENERATED_SUFFIXES) or 0.0
    accepted_after = _first_by_suffixes(after, ACCEPTED_SUFFIXES)
    generated_after = _first_by_suffixes(after, GENERATED_SUFFIXES)
    if accepted_after is None or generated_after is None:
        return None
    accepted = accepted_after - accepted_before
    generated = generated_after - generated_before
    if generated <= 0:
        return None
    return min(1.0, max(0.0, accepted / generated))
```

Os dois `<sufixo real …>` são os nomes copiados do Step 1 (sem o prefixo que varia). Não deixar o texto entre `<>` no código.

- [ ] **Step 4: Rodar os testes e commit**

Run: `python3 -m pytest bench/qwen3.8-prefix-cache/tests -q -k mtp_acceptance`
Expected: `2 passed`.

```bash
git add bench/qwen3.8-prefix-cache/scripts/cache_probe.py bench/qwen3.8-prefix-cache/tests/test_mtp_acceptance_aliases.py
git commit -m "bench(flashnext-driver): aceitacao da MTP a partir dos contadores do mlx-serve 26.9.2

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Offload de PLE na oMLX 0.7.0.dev2 (pré-requisito do c3)

**Files:**
- Modify: `bench/qwen3.8-prefix-cache/scripts/omlx_config.py` (ou o gerador que o `run-omlx.sh` chama para escrever `model_settings.json`)
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/results/c3-dev2-ple-config.md`

**Interfaces:**
- Produces: `run-omlx.sh FN` com `QWEN38_OMLX_BIN` da dev2 sobe o oQ4e com PLE em mmap (wired < 80 GB antes da 1ª request).

- [ ] **Step 1: Achar como a 0.7 lê `qwen4_ple_ssd_offload`**

Run: `grep -rn "qwen4_ple_ssd_offload\|OMLX_QWEN4_PLE_MODE\|def configure_ple_runtime" ~/.local/opt/qwen38/omlx-v0.7.0.dev2/lib/python*/site-packages/omlx/ | head -20`
Expected: os arquivos e linhas onde o setting por-modelo é lido (`model_settings.py` / `model_profiles.py`) e o formato do arquivo (chave por `model_key` ou por caminho). Anotar o formato em `results/c3-dev2-ple-config.md`.

- [ ] **Step 2: Ver o que o launcher gera hoje**

Run: `OMLX_MODEL_ROOT=$HOME/.cache/local-llms/qwen3.8-prefix-cache QWEN38_OMLX_BIN=~/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/omlx QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2 QWEN38_OMLX_RUN_ID=dev2-print bash bench/qwen3.8-prefix-cache/scripts/run-omlx.sh FN --print; cat bench/qwen3.8-prefix-cache/logs/omlx/dev2-print/model_settings.json 2>/dev/null`
Expected: o comando e o `model_settings.json` gerado a partir de `config/omlx-arms.json` (arm FN tem `qwen4_ple_ssd_offload: true`). Comparar a chave/estrutura com o formato do Step 1.

- [ ] **Step 3: Ajustar o gerador para o formato da 0.7**

Alterar `omlx_config.py` para emitir a chave no formato que a 0.7 lê quando `omlx_version` começa com `0.7` (manter o formato da 0.6.x para a 0.6.4). Se a 0.7 usa um arquivo de perfil separado, gerar esse arquivo no mesmo `OMLX_BASE_PATH`. Registrar o diff em `results/c3-dev2-ple-config.md`.

- [ ] **Step 4: Validar residente no boot (rig)**

Run: `bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh c3 8192 --scenarios cold --tag ple-check; grep -i "PLE mode" bench/qwen38-flashnext-daily-driver-2026-09/logs/c3-8192-t1.0-ple-check-boot.log; python3 -c "import json;s=[json.loads(l) for l in open('bench/qwen38-flashnext-daily-driver-2026-09/logs/c3-8192-t1.0-ple-check-mem.jsonl')];print('wired max',max(x['wired_gb'] for x in s))"`
Expected: log com `PLE mode … : mmap` (não `resident`); wired max < 85 GB; a request `cold` responde com needle correta. Se o wired passar de 95 GB, o offload não pegou: voltar ao Step 1 e registrar o bloqueio; o c3 sai da campanha com o motivo em `results/c3-dev2-ple-config.md`.

- [ ] **Step 5: Commit**

```bash
git add bench/qwen3.8-prefix-cache/scripts/omlx_config.py bench/qwen38-flashnext-daily-driver-2026-09/results/c3-dev2-ple-config.md
git commit -m "bench(flashnext-driver): offload de PLE por modelo na oMLX 0.7 (c3)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Etapa 0 — smoke a 8K dos 4 candidatos

**Files:**
- Create: `results/c{1,2,3,4}-8192-t1.0.jsonl`, `results/etapa0-smoke.md`

**Interfaces:**
- Consumes: `run-candidate.sh` (Task 4).
- Produces: lista de sobreviventes para a Etapa A.

- [ ] **Step 1: Rodar os 4 (sequencial, ~30 min)**

Run: `for c in c1 c2 c3 c4; do bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh $c 8192 --scenarios cold,identical,tool_turn --repeat 1 2>&1 | tee -a bench/qwen38-flashnext-daily-driver-2026-09/logs/etapa0.driver.log; done`
Expected: 4 arquivos `results/c*-8192-t1.0.jsonl` com 3 registros cada. Um candidato que morre no boot deixa o `*-boot.log` e o driver sai com 69.

- [ ] **Step 2: Extrair a tabela**

Run:
```bash
python3 - <<'PY'
import json,glob
for f in sorted(glob.glob("bench/qwen38-flashnext-daily-driver-2026-09/results/c*-8192-t1.0.jsonl")):
    for l in open(f):
        r=json.loads(l)
        print(f.split('/')[-1][:2], r['scenario'], f"ttft={r['ttft_ms']/1000:.1f}s prefill={r.get('prompt_tps') or 0:.0f} decode={r['decode_tps']:.1f} hit={r.get('cache_hit_ratio')} ok={r['correct']} fin={r.get('finish_reason')} wired={r.get('ram_peak_gb')} swap={r.get('swap_delta_gb')} mtp={r.get('mtp_acceptance')}")
PY
```
Expected: 12 linhas. Registrar em `results/etapa0-smoke.md`: tabela por candidato, wired de pico, se carregou, perfil/depth usado no c4 (Task 3 Step 2), nomes dos contadores de MTP (Task 5), decisão "segue / sai" por candidato com o motivo.

- [ ] **Step 3: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/results/
git commit -m "bench(flashnext-driver): etapa 0 — smoke a 8K dos 4 candidatos

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Diagnósticos a temp 0 (lossless c2 vs c3; MTP on/off do c4)

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/compare_hashes.py`
- Test: `bench/qwen38-flashnext-daily-driver-2026-09/tests/test_compare_hashes.py`
- Create: `results/c2-32768-t0.jsonl`, `c3-32768-t0.jsonl`, `c4-32768-t0.jsonl`, `c4-32768-t0-nomtp.jsonl`, `results/diag-temp0.md`

**Interfaces:**
- Consumes: campo `greedy_tokens_hash` que o `cache_probe.py` grava por registro (hash sha256 dos tokens de saída).
- Produces: `compare(a: list[dict], b: list[dict]) -> list[dict]` com uma linha por cenário `{scenario, same: bool, hash_a, hash_b}`.

- [ ] **Step 1: Teste que falha**

```python
# tests/test_compare_hashes.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_hashes import compare  # noqa: E402


def test_compare_pairs_scenarios_by_name():
    a = [{"scenario": "cold", "repeat": 1, "greedy_tokens_hash": "h1"}, {"scenario": "identical", "repeat": 1, "greedy_tokens_hash": "h2"}]
    b = [{"scenario": "identical", "repeat": 1, "greedy_tokens_hash": "h2"}, {"scenario": "cold", "repeat": 1, "greedy_tokens_hash": "hX"}]
    rows = compare(a, b)
    assert rows == [
        {"scenario": "cold", "same": False, "hash_a": "h1", "hash_b": "hX"},
        {"scenario": "identical", "same": True, "hash_a": "h2", "hash_b": "h2"},
    ]
```

Run: `python3 -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests/test_compare_hashes.py -q`
Expected: FAIL (módulo ausente).

- [ ] **Step 2: Implementar**

```python
#!/usr/bin/env python3
"""Compara o hash dos tokens de saida (temp 0) entre dois JSONL do cache_probe, por cenario."""
import argparse, json
from pathlib import Path

ORDER = ("cold", "identical", "append", "middle_mutation", "tool_turn")


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def compare(a: list[dict], b: list[dict]) -> list[dict]:
    ha = {(r["scenario"], r.get("repeat", 1)): r.get("greedy_tokens_hash") for r in a}
    hb = {(r["scenario"], r.get("repeat", 1)): r.get("greedy_tokens_hash") for r in b}
    rows = []
    for key in sorted(ha.keys() & hb.keys(), key=lambda k: (ORDER.index(k[0]) if k[0] in ORDER else 99, k[1])):
        rows.append({"scenario": key[0], "same": ha[key] == hb[key], "hash_a": ha[key], "hash_b": hb[key]})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path); ap.add_argument("b", type=Path)
    args = ap.parse_args()
    rows = compare(load(args.a), load(args.b))
    print("| cenário | iguais | hash A | hash B |\n|---|---|---|---|")
    for r in rows:
        print(f"| {r['scenario']} | {'sim' if r['same'] else '**não**'} | `{(r['hash_a'] or '')[:12]}` | `{(r['hash_b'] or '')[:12]}` |")
    return 0 if all(r["same"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `python3 -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests/test_compare_hashes.py -q`
Expected: `1 passed`.

- [ ] **Step 3: Rodar os diagnósticos no rig (32K, temp 0, 1 rep; ~1 h)**

Run:
```bash
D=bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh
bash $D c2 32768 --temperature 0 --repeat 1
bash $D c3 32768 --temperature 0 --repeat 1
bash $D c4 32768 --temperature 0 --repeat 1
bash $D c4 32768 --temperature 0 --repeat 1 --tag nomtp --generation-mode <modo AR do Task 3 Step 3>
```
(Substituir `<modo AR …>` pelo valor descoberto; c3 só se sobreviveu à Task 7.)

- [ ] **Step 4: Comparar e registrar**

Run:
```bash
R=bench/qwen38-flashnext-daily-driver-2026-09/results
python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/compare_hashes.py $R/c2-32768-t0.jsonl $R/c3-32768-t0.jsonl
python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/compare_hashes.py $R/c4-32768-t0.jsonl $R/c4-32768-t0-nomtp.jsonl
```
Expected: duas tabelas. Escrever `results/diag-temp0.md` com as tabelas e a leitura: c2≠c3 em algum cenário = correção suspeita na dev2 (não elimina, mas entra no summary); c4 MTP≠AR = MTP lossy → c4 eliminado (mesma regra do MTPLX 2.11.1).

- [ ] **Step 5: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/compare_hashes.py bench/qwen38-flashnext-daily-driver-2026-09/tests/test_compare_hashes.py bench/qwen38-flashnext-daily-driver-2026-09/results/
git commit -m "bench(flashnext-driver): diagnosticos a temp 0 — lossless dev2 e MTP on/off do MTPLX

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Consolidador `summarize_driver.py` (gates + `T_turno`)

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py`
- Test: `bench/qwen38-flashnext-daily-driver-2026-09/tests/test_summarize_driver.py`

**Interfaces:**
- Consumes: `results/c*-<ctx>-t1.0*.jsonl` (registros do probe com memória anexada).
- Produces: `summarize(records) -> dict` com chave `(cand, ctx)` → `{cold_ttft_s, warm_ttft_s: {identical, append, tool_turn}, hit: {...}, prefill_tps, decode_tps, t_turno_s, correctness: "ok"|"truncado"|"falha", wired_peak_gb, swap_delta_gb, mtp_acceptance, n}`; `apply_gates(row, ctx) -> list[str]` (lista de gates falhados, vazia = passou); CLI escreve `results/summary.json` e imprime a tabela markdown por banda.

- [ ] **Step 1: Teste que falha**

```python
# tests/test_summarize_driver.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_driver import summarize, apply_gates, t_turno  # noqa: E402


def rec(cand, ctx, scen, ttft_s, decode, hit, correct=True, fin="stop", rep=1, wired=100.0, swap=0.1):
    return {"arm": cand, "context_target": ctx, "scenario": scen, "repeat": rep, "ttft_ms": ttft_s * 1000,
            "decode_tps": decode, "prompt_tps": 700.0, "cache_hit_ratio": hit, "correct": correct,
            "finish_reason": fin, "ram_peak_gb": wired, "swap_delta_gb": swap, "mtp_acceptance": 0.8}


def test_t_turno_formula():
    assert t_turno(2.0, 64.0) == 10.0  # 2.0 + 512/64


def test_summarize_medians_and_correctness():
    rs = [rec("c1", 32768, "cold", 37.0, 66.0, 0.0), rec("c1", 32768, "tool_turn", 2.0, 60.0, 0.96),
          rec("c1", 32768, "tool_turn", 2.2, 68.0, 0.96, rep=2), rec("c1", 32768, "append", 1.9, 64.0, 0.96),
          rec("c1", 32768, "identical", 0.1, 65.0, 1.0, correct=False, fin="length")]
    s = summarize(rs)[("c1", 32768)]
    assert s["cold_ttft_s"] == 37.0
    assert s["warm_ttft_s"]["tool_turn"] == 2.1
    assert s["decode_tps"] == 64.5  # mediana dos cenarios quentes (60, 68, 64, 65)
    assert s["t_turno_s"] == round(2.1 + 512 / 64.5, 1)
    assert s["correctness"] == "truncado"


def test_gates():
    row = {"hit": {"append": 0.85, "tool_turn": 0.96}, "correctness": "ok", "wired_peak_gb": 104.0, "swap_delta_gb": 0.1, "errors": 0}
    assert apply_gates(row, 32768) == ["hit_append<0.90", "wired>102"]
```

Run: `python3 -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests/test_summarize_driver.py -q`
Expected: FAIL (módulo ausente).

- [ ] **Step 2: Implementar**

```python
#!/usr/bin/env python3
"""Consolida os JSONL da campanha flashnext-daily-driver: medianas, T_turno, gates."""
import argparse, glob, json, statistics
from pathlib import Path

WARM = ("identical", "append", "tool_turn")
GATE_CTX = (32768, 131072)


def t_turno(ttft_tool_turn_s: float, decode_tps: float, reply_tokens: int = 512) -> float:
    return round(ttft_tool_turn_s + reply_tokens / decode_tps, 1)


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def summarize(records: list[dict]) -> dict:
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        groups.setdefault((r["arm"], int(r["context_target"])), []).append(r)
    out = {}
    for key, rs in groups.items():
        by = {}
        for r in rs:
            by.setdefault(r["scenario"], []).append(r)
        warm_ttft = {s: _median([r["ttft_ms"] / 1000 for r in by.get(s, [])]) for s in WARM}
        hit = {s: _median([r.get("cache_hit_ratio") for r in by.get(s, [])]) for s in WARM}
        warm_decode = [r["decode_tps"] for s in WARM for r in by.get(s, [])]
        decode = _median(warm_decode) or _median([r["decode_tps"] for r in rs])
        fins = [r.get("finish_reason") for r in rs]
        if all(r.get("correct") for r in rs):
            correctness = "ok"
        elif all(r.get("correct") or f == "length" for r, f in zip(rs, fins)):
            correctness = "truncado"
        else:
            correctness = "falha"
        row = {
            "cold_ttft_s": _median([r["ttft_ms"] / 1000 for r in by.get("cold", [])]),
            "warm_ttft_s": warm_ttft, "hit": hit,
            "prefill_tps": _median([r.get("prompt_tps") for r in by.get("cold", [])]),
            "decode_tps": decode,
            "t_turno_s": t_turno(warm_ttft["tool_turn"], decode) if warm_ttft["tool_turn"] is not None and decode else None,
            "correctness": correctness,
            "wired_peak_gb": max((r.get("ram_peak_gb") or 0) for r in rs) or None,
            "swap_delta_gb": max((r.get("swap_delta_gb") or 0) for r in rs),
            "mtp_acceptance": _median([r.get("mtp_acceptance") for r in rs]),
            "errors": sum(1 for r in rs if r.get("error")),
            "n": len(rs),
        }
        row["gates_failed"] = apply_gates(row, key[1])
        out[key] = row
    return out


def apply_gates(row: dict, ctx: int) -> list[str]:
    failed = []
    if ctx in GATE_CTX:
        for s in ("append", "tool_turn"):
            h = row["hit"].get(s)
            if h is not None and h < 0.90:
                failed.append(f"hit_{s}<0.90")
        if row["correctness"] == "falha":
            failed.append("needle")
    if row.get("wired_peak_gb") and row["wired_peak_gb"] > 102:
        failed.append("wired>102")
    if row.get("swap_delta_gb", 0) > 0.5:
        failed.append("swap>0.5")
    if row.get("errors", 0) and ctx in GATE_CTX:
        failed.append("http_errors")
    return failed


def markdown(summary: dict) -> str:
    lines = []
    for ctx in sorted({k[1] for k in summary}):
        lines.append(f"\n### {ctx // 1024}K\n\n| cand | T_turno s | cold TTFT s | warm TTFT id/app/tool s | hit id/app/tool | prefill | decode | MTP acc | correção | wired GB | swap Δ | gates |")
        lines.append("|---|---:|---:|---|---|---:|---:|---:|---|---:|---:|---|")
        for (cand, c), r in sorted(summary.items()):
            if c != ctx:
                continue
            w = r["warm_ttft_s"]; h = r["hit"]
            f = lambda d: "/".join("—" if d[s] is None else f"{d[s]:.2f}" if d[s] < 10 else f"{d[s]:.0f}" for s in WARM)
            lines.append(f"| {cand} | {r['t_turno_s']} | {r['cold_ttft_s']} | {f(w)} | {f(h)} | {r['prefill_tps']} | {r['decode_tps']} | {r['mtp_acceptance']} | {r['correctness']} | {r['wired_peak_gb']} | {r['swap_delta_gb']} | {', '.join(r['gates_failed']) or 'passa'} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="bench/qwen38-flashnext-daily-driver-2026-09/results")
    ap.add_argument("--glob", default="c*-*-t1.0*.jsonl")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    records = []
    for f in sorted(glob.glob(str(Path(a.results_dir) / a.glob))):
        records += [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    summary = summarize(records)
    out = Path(a.out or Path(a.results_dir) / "summary.json")
    out.write_text(json.dumps({f"{k[0]}@{k[1]}": v for k, v in summary.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Rodar os testes**

Run: `python3 -m pytest bench/qwen38-flashnext-daily-driver-2026-09/tests -q`
Expected: todos passam (attach_memory 2, compare_hashes 1, summarize_driver 3).

- [ ] **Step 4: Rodar contra a Etapa 0 e commit**

Run: `python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py --glob 'c*-8192-t1.0.jsonl' --out /tmp/summary-8k.json`
Expected: uma tabela `### 8K` com uma linha por candidato que rodou.

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py bench/qwen38-flashnext-daily-driver-2026-09/tests/test_summarize_driver.py
git commit -m "bench(flashnext-driver): consolidador com T_turno, correcao em tres estados e gates

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Etapa A — bandas 32K, 128K, 256K (1-shot, por banda)

**Files:**
- Create: `results/c*-32768-t1.0.jsonl`, `c*-131072-t1.0.jsonl`, `c*-262144-t1.0.jsonl`, `results/etapa-a.md`

- [ ] **Step 1: 32K, os sobreviventes, 5 cenários (~1 h)**

Run: `for c in <sobreviventes da Task 7>; do bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh $c 32768 --repeat 1 2>&1 | tee -a bench/qwen38-flashnext-daily-driver-2026-09/logs/etapa-a.driver.log; done`
Expected: um JSONL por candidato com 5 registros.

- [ ] **Step 2: 128K, os mesmos, 5 cenários (~1.5 h)**

Run: idem com `131072`.

- [ ] **Step 3: 256K, os mesmos, 3 cenários (~1.5 h)**

Run: idem com `262144 --scenarios cold,identical,tool_turn`.
Expected: um 400/recusa na 2ª request é registrado como `error` no registro, não interrompe o driver. Se um servidor morrer (OOM hard), o `*-boot.log` guarda o motivo; anotar e seguir.

- [ ] **Step 4: Consolidar e escrever `results/etapa-a.md`**

Run: `python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py | tee /tmp/etapa-a.md`
Expected: tabelas 8K/32K/128K/256K. `results/etapa-a.md` = as tabelas + gates por candidato + ranking por `T_turno` (32K e 128K) + lista dos que vão à Etapa B (passam nos gates) e dos 2 finalistas (menor `T_turno` médio de 32K e 128K).

- [ ] **Step 5: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/results/
git commit -m "bench(flashnext-driver): etapa A — triagem 1-shot a 32K/128K/256K

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Sonda de capacidade a 512K

**Files:**
- Create: `results/c1-524288-t1.0-yarn2.jsonl` (+ os de c2/c3/c4 se houver YaRN), `results/sonda-512k.md`

- [ ] **Step 1: Mapear o YaRN no oMLX e no MTPLX**

Run:
```bash
~/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx serve --help 2>&1 | grep -i -E 'rope|yarn|context-window|max-position' 
grep -rn -i "yarn\|rope_scaling\|rope_parameters" ~/.local/share/uv/tools/omlx/lib/python*/site-packages/omlx/ 2>/dev/null | grep -v test | head -10
```
Expected: ou um flag/setting que estende o rope, ou nada. Registrar em `results/sonda-512k.md`. Sem flag = teto do runtime é 262K (dado da campanha); a sonda roda só no c1.

- [ ] **Step 2: Registrar o estado do `wired_limit` e rodar o c1 (~20 min)**

Run:
```bash
sysctl iogpu.wired_limit_mb | tee -a bench/qwen38-flashnext-daily-driver-2026-09/logs/sonda-512k.driver.log
bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh c1 524288 --yarn 2.0 --scenarios cold,identical --repeat 1 --tag yarn2 2>&1 | tee -a bench/qwen38-flashnext-daily-driver-2026-09/logs/sonda-512k.driver.log
```
Expected: 2 registros; `cold` com needle e decode ~50; `identical` hit ~1.0. Se o `identical` for recusado, é dado ("512K one-shot").

- [ ] **Step 3: Rodar os demais que tiverem YaRN (Step 1)**

Para cada runtime com mecanismo mapeado: adicionar o env correspondente no `case` do candidato em `run-candidate.sh` (mesmo padrão do `--yarn` do c1) e rodar `--scenarios cold,identical --tag yarn2`. Sem mecanismo: pular e registrar.

- [ ] **Step 4: Escrever `results/sonda-512k.md` e commit**

Tabela: candidato | alcança 512K | follow-up cabe | decode | cold TTFT | needle | wired | kv-disk | `wired_limit` | mecanismo de YaRN.

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/results/ bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh
git commit -m "bench(flashnext-driver): sonda de capacidade a 512K

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Etapa B — 3× a 32K (todos que passaram) e a 128K (2 finalistas)

**Files:**
- Create: `results/c*-32768-t1.0-b.jsonl`, `results/c*-131072-t1.0-b.jsonl`, `results/etapa-b.md`

- [ ] **Step 1: 32K, 3 reps, `middle_mutation` só 1 (~2 h)**

Run: `for c in <passaram nos gates, Task 10 Step 4>; do bash bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh $c 32768 --repeat 3 --tag b 2>&1 | tee -a bench/qwen38-flashnext-daily-driver-2026-09/logs/etapa-b.driver.log; done`
Nota: o `cache_probe.py` aceita `--scenario-repeats middle_mutation=1`; adicionar `--scenario-repeats "middle_mutation=1"` ao comando do probe no `run-candidate.sh` quando `REPEAT > 1` (uma linha: `$([[ "$REPEAT" -gt 1 ]] && echo --scenario-repeats middle_mutation=1)`).

- [ ] **Step 2: 128K, 3 reps, os 2 finalistas (~2 h)**

Run: idem com `131072` para os 2 finalistas.

- [ ] **Step 3: Consolidar a Etapa B**

Run: `python3 bench/qwen38-flashnext-daily-driver-2026-09/scripts/summarize_driver.py --glob 'c*-*-t1.0-b.jsonl' --out bench/qwen38-flashnext-daily-driver-2026-09/results/summary-b.json | tee /tmp/etapa-b.md`
Expected: tabelas 32K e 128K com `n` = 13 (32K) e 13 (128K). `results/etapa-b.md` = tabelas + variação entre reps do `tool_turn` (miss intermitente = listar) + ranking final por `T_turno`.

- [ ] **Step 4: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/results/ bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh
git commit -m "bench(flashnext-driver): etapa B — 3x a 32K e 128K nos finalistas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: `results/quant-fidelity.md` (publicado, não medido)

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/results/quant-fidelity.md`

- [ ] **Step 1: Ler os cards HF dos 3 packs**

Run:
```bash
for r in ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit Jundot/Qwen3.8-Flash-Next-oQ4e-mtp Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed; do echo "== $r"; curl -sL "https://huggingface.co/$r/raw/main/README.md" | grep -i -E 'kl|ppl|perplex|bpw|bits' | head -12; done
du -sh ~/.cache/local-llms/qwen3.8-prefix-cache/{ddalcu-Qwen3.8-Flash-Next*,Jundot-Qwen3.8-Flash-Next*,Youssofal-Qwen3.8-Flash-Next*}
```
Expected: as linhas com KLD/PPL/bpw de cada card (ou nenhuma — registrar "card não publica").

- [ ] **Step 2: Escrever a tabela**

Colunas: pack | bpw efetivo (card ou calculado = tamanho em disco × 8 / 177B params) | disco | PPL Δ% publicado | KLD publicado | referência (bf16?) | fonte (URL + data). Rodapé: "Publicado pelo autor do quant, não medido no rig. Não entra no ranking. Contexto: seção 'Fidelidade por bpw' em `bench/qwen38-flash-next/references.md`."

- [ ] **Step 3: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/results/quant-fidelity.md
git commit -m "bench(flashnext-driver): fidelidade publicada dos 3 packs MLX

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: `results/summary.md` — veredito em prosa

**Files:**
- Create: `bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md`
- Modify: `bench/qwen38-flashnext-daily-driver-2026-09/plan.md` (bloco `> **Status**` no topo)

- [ ] **Step 1: Escrever o summary**

Estrutura fixa:
1. Veredito em uma frase: qual candidato é o driver diário mais responsivo e por quê (`T_turno` a 32K e 128K).
2. Tabela head-to-head por banda (colar a saída da Task 12 Step 3 para 32K/128K e da Task 10 para 8K/256K).
3. Gates por candidato (passou / falhou em quê).
4. Tabela de teto de contexto (Task 11).
5. Diagnósticos a temp 0 (Task 8): lossless dev2, MTP do MTPLX.
6. Miss intermitente de cache (reps da Etapa B).
7. Lacunas e não-verificados (aceitação da MTP por runtime, YaRN ausente, candidato eliminado e motivo).
8. Ponteiros: `quant-fidelity.md`, `etapa0-smoke.md`, `etapa-a.md`, `etapa-b.md`, `sonda-512k.md`.

Regras de escrita: uma ideia por frase; número sempre com unidade; "não medido" dito uma vez por item.

- [ ] **Step 2: Status no runbook**

No topo de `plan.md`, adicionar após o bloco de objetivo:

```markdown
> **Status (AAAA-MM-DD): CAMPANHA FECHADA.** Veredito em [results/summary.md](results/summary.md).
> Driver mais responsivo: <candidato>, `T_turno` <x> s @32K / <y> s @128K. Dashboard:
> [reports/qwen38-flashnext-driver.html](../../reports/qwen38-flashnext-driver.html).
```

- [ ] **Step 3: Commit**

```bash
git add bench/qwen38-flashnext-daily-driver-2026-09/results/summary.md bench/qwen38-flashnext-daily-driver-2026-09/plan.md
git commit -m "bench(flashnext-driver): veredito — driver diario mais responsivo

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: Dashboard `reports/qwen38-flashnext-driver.html`

**Files:**
- Create: `reports/qwen38-flashnext-driver.html`
- Modify: `reports/README.md` (tabela de dashboards)

**Interfaces:**
- Consumes: `reports/charts-common.js` (`createFilterState`, `createFilterBar`, `buildGroupedChart`, `buildScoreboard`, `setupSortableTable`, `highlightBestPerColumn`), `results/summary.json` e `summary-b.json` (valores copiados para `RESULTS` inline — a página é self-contained, sem fetch).
- Produces: página com `MODELS` = 4 candidatos e `RESULTS` = registros `{model, metric, context, scenario?, value}`.

- [ ] **Step 1: Gerar os arrays `MODELS`/`RESULTS` a partir do summary**

```bash
python3 - <<'PY'
import json
s = json.load(open("bench/qwen38-flashnext-daily-driver-2026-09/results/summary.json"))
sb = json.load(open("bench/qwen38-flashnext-daily-driver-2026-09/results/summary-b.json"))
s.update(sb)  # Etapa B sobrescreve 32K/128K
models = {"c1": ("ddalcu mixed-4/8 @ mlx-serve 26.9.2", "#2563eb"), "c2": ("oQ4e @ oMLX 0.6.4", "#16a34a"),
          "c3": ("oQ4e @ oMLX 0.7.0.dev2", "#65a30d"), "c4": ("MTPLX Opt-Speed @ 2.11.2", "#dc2626")}
print("const MODELS = " + json.dumps([{"id": k, "tier": "local", "label": v[0], "chartLabel": v[0], "color": v[1], "provider": "Alibaba (Qwen)", "family": "Qwen3.8-Flash-Next", "arch": "moe"} for k, v in models.items()], ensure_ascii=False, indent=1) + ";")
rows = []
for key, r in s.items():
    cand, ctx = key.split("@"); ctx = int(ctx)
    for m in ("t_turno_s", "cold_ttft_s", "decode_tps", "prefill_tps", "wired_peak_gb", "mtp_acceptance"):
        rows.append({"model": cand, "metric": m, "context": ctx, "value": r[m]})
    for sc in ("identical", "append", "tool_turn"):
        rows.append({"model": cand, "metric": "warm_ttft_s", "context": ctx, "scenario": sc, "value": r["warm_ttft_s"][sc]})
        rows.append({"model": cand, "metric": "hit", "context": ctx, "scenario": sc, "value": r["hit"][sc]})
print("const RESULTS = " + json.dumps(rows, ensure_ascii=False) + ";")
PY
```
Expected: dois arrays JS válidos para colar na página.

- [ ] **Step 2: Escrever a página**

Seguir `reports/README.md`: `<script src="charts-common.js">` clássico; `<title>Qwen3.8-Flash-Next — driver responsivo</title>`; cards: (1) veredito em prosa (copiar de `summary.md`); (2) scoreboard `#scoreboardDriver` via `buildScoreboard` com colunas `T_turno @32K`, `T_turno @128K`, `cold TTFT @128K`, `decode @128K`, `wired`; (3) `buildGroupedChart('chartTturno', …)` com `seriesFor` por contexto `[8192,32768,131072,262144]`; (4) `chartWarmTtft` (metric `warm_ttft_s`, scenario `tool_turn`) e `chartColdTtft`; (5) `chartDecode`; (6) tabela HTML de hit cenário × candidato por banda, células com classe `hit-ok` (≥0.90) / `hit-bad`; (7) `chartWired` barras; (8) tabela de teto 512K; (9) card de lacunas. Sem heatmap por biblioteca — a tabela colorida cumpre o papel.

- [ ] **Step 3: Verificar no browser**

Abrir `reports/qwen38-flashnext-driver.html` no Browser pane (`file://`), tirar screenshot e ler o console.
Expected: os 5 gráficos renderizam, o scoreboard ordena ao clicar, zero erros no console, filtro por candidato esconde a série.

- [ ] **Step 4: Linha no `reports/README.md`**

Adicionar à tabela do topo: `| qwen38-flashnext-driver.html | Flash-Next: T_turno, TTFT quente/frio, cache hit, wired, teto 512K por quant × runtime | Campanha bench/qwen38-flashnext-daily-driver-2026-09 |`.

- [ ] **Step 5: Commit**

```bash
git add reports/qwen38-flashnext-driver.html reports/README.md
git commit -m "reports: dashboard do driver responsivo do Flash-Next

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: Publicar na `gh-pages` (pedir confirmação antes do push)

**Files:**
- Branch órfã `gh-pages`: `index.html` (link novo), `qwen38-flashnext-driver.html`, `charts-common.js`

- [ ] **Step 1: Montar a árvore por plumbing (sem tocar o working tree)**

```bash
git fetch origin gh-pages
PARENT=$(git rev-parse origin/gh-pages)
git show origin/gh-pages:index.html > /tmp/index.html
# inserir o link antes do </ul> (ou lista equivalente) do index:
python3 - <<'PY'
p="/tmp/index.html"; s=open(p).read()
link='<li><a href="qwen38-flashnext-driver.html">Qwen3.8-Flash-Next — driver diário responsivo (quants × runtimes)</a></li>\n'
assert "</ul>" in s; s=s.replace("</ul>", link+"</ul>",1); open(p,"w").write(s)
PY
B_INDEX=$(git hash-object -w /tmp/index.html)
B_PAGE=$(git hash-object -w reports/qwen38-flashnext-driver.html)
B_JS=$(git hash-object -w reports/charts-common.js)
git ls-tree origin/gh-pages | grep -v -E 'index.html|qwen38-flashnext-driver.html|charts-common.js' > /tmp/tree.txt
printf '100644 blob %s\tindex.html\n100644 blob %s\tqwen38-flashnext-driver.html\n100644 blob %s\tcharts-common.js\n' "$B_INDEX" "$B_PAGE" "$B_JS" >> /tmp/tree.txt
TREE=$(git mktree < /tmp/tree.txt)
COMMIT=$(git commit-tree "$TREE" -p "$PARENT" -m "pages: dashboard do driver responsivo do Flash-Next")
git update-ref refs/heads/gh-pages "$COMMIT"
git ls-tree gh-pages
```
Expected: a árvore lista `index.html`, `overview.html`, `perf-lines.html`, `.nojekyll`, `charts-common.js`, `qwen38-flashnext-driver.html`.

- [ ] **Step 2: Confirmar com o usuário e só então fazer push**

Perguntar: "Publico a `gh-pages` com o dashboard novo em https://snagnever.github.io/macstudio-local-llm/qwen38-flashnext-driver.html?". Só após um sim:

```bash
git push origin gh-pages
```
Se a página der 404 após ~1 min: `gh api -X POST /repos/snagnever/macstudio-local-llm/pages/builds` e esperar.

- [ ] **Step 3: Verificar a URL no browser e registrar o link no `summary.md`** (commit `docs: link publicado`).

---

### Task 17: Memória e PR

- [ ] **Step 1: Memória**

Escrever `~/.claude/projects/-Users-vitor-LocalProjects-local-llms/memory/flashnext-responsive-driver-verdict.md` (type `project`): veredito, `T_turno` dos finalistas, gates falhados, lacunas; atualizar `flashnext-mlxserve-current-driver.md` se o driver mudou; adicionar a linha no `MEMORY.md`.

- [ ] **Step 2: PR para `main`**

```bash
git push -u origin bench/qwen38-flashnext-daily-driver-2026-09
gh pr create --base main --title "bench(flashnext-driver): driver diario mais responsivo do Flash-Next (quants x runtimes)" --body "$(cat <<'EOF'
Campanha bench/qwen38-flashnext-daily-driver-2026-09: 4 candidatos (ddalcu/mlx-serve 26.9.2, oQ4e/oMLX 0.6.4, oQ4e/oMLX 0.7.0.dev2, MTPLX Optimized-Speed/2.11.2), bandas 8K-256K, sonda 512K, T_turno como metrica. Veredito em results/summary.md; dashboard em reports/qwen38-flashnext-driver.html. Inclui a branch docs/flashnext-card-refresh (card do Flash-Next atualizado).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
(Só após pedido explícito de push/PR.)

---

## Self-review

- **Cobertura do runbook:** Etapa 0 → Task 7; Etapa A → Task 10; Etapa B → Task 12; sonda 512K → Task 11; higiene (cold frio, memória, ordem) → Task 4; amostragem vendor + diagnósticos temp 0 → Tasks 4 e 8; telemetria wired → Tasks 1–2; aceitação da MTP → Task 5; config c3 (dev2) → Task 6; config c4 (FX, ssd on, perfil do pack) → Task 3; `--ssm-checkpoint-max`/`--max-mtp-ctx` → Task 3/4; gates e `T_turno` → Task 9; entregáveis (summary, quant-fidelity, dashboard, gh-pages) → Tasks 13–16.
- **Descobertas em vez de placeholders:** três valores são lidos do rig e não podem ser escritos antes: nomes dos contadores de MTP (Task 5 Step 1), modo AR do MTPLX (Task 3 Step 3) e formato do setting da oMLX 0.7 (Task 6 Step 1). Cada um tem o comando que os revela e o lugar onde ficam registrados.
- **Consistência de nomes:** `run-candidate.sh <c1..c4> <ctx> --scenarios --repeat --temperature --tag --yarn --generation-mode --print`; arquivos `results/<cand>-<ctx>-t<temp>[-<tag>].jsonl`; funções `attach_memory`, `compare`, `summarize`, `apply_gates`, `t_turno`; chaves `cold_ttft_s`, `warm_ttft_s`, `hit`, `t_turno_s`, `correctness`, `wired_peak_gb`, `swap_delta_gb`, `gates_failed` — iguais na Task 9 e na Task 15.
