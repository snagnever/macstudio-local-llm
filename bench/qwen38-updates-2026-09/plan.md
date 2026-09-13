# 2026-09-12 — Qwen: testar as atualizações de setembro

> **Status:** aberta. Campanha de teste do lote de atualizações que apareceu depois do
> refresh de 04/09 ([qwen38-flash-next/plan-refresh-20260904.md](../qwen38-flash-next/plan-refresh-20260904.md)).
> Escopo: só Qwen (Flash-Next, densa 27B, MoE 3.6). Inventário e procedência em
> [references.md](references.md); manifesto em [results/update-inventory-20260912.json](results/update-inventory-20260912.json).

## Baseline instalado (do refresh de 04/09)

- mlx-serve **26.9.1** (CLI padrão). Já traz contexto 1M e +10% decode no Flash-Next.
- MTPLX **2.11.1**.
- mlx-dspark **0.18.0**.
- oMLX **0.6.4** (estável).

Os quants do Qwen3.8 em uso estão congelados: `ddalcu/…mixed-4-8bit` (`ef5b919d`) e
`Jundot/…oQ4e-mtp` (`2615fc0e`) têm o mesmo SHA no `main` do HF. Nada a re-baixar nesse caminho.

## Deltas a testar

Ordenados por custo. P1 reusa os pesos já em disco, sem download.

| # | Delta | Baseline → candidato | Baixar? | Prioridade |
|---|---|---|---|---|
| 1 | mlx-serve runtime | 26.9.1 → **26.9.2** | Não | P1 |
| 2 | MTPLX runtime | 2.11.1 → **2.11.2** | Não | P1 |
| 3 | Config de 1M no mlx-serve (feature já na 26.9.1) | — | Não | P1 |
| 4 | oMLX runtime | 0.6.4 → **0.7.0.dev2** | Não | P2 |
| 5 | Trio 27B MTPLX (só `mtplx_runtime.json` mudou em 03/09) | re-pull do runtime json | Parcial | P2 |
| 6 | DFlash2 densa 27B (`incoai/Qwen3.8-27B-DFlash2`, GGUF `z-lab`) | draft head novo | Sim | P3 |
| 7 | ddalcu Qwen3.6-35B-A3B-MLX-Serve-4bit (08/09) | quant MoE 3.6 nova | Sim | P3 |

O que já é sabido e **não** entra: o +10% de decode e o 1M já estão na 26.9.1 instalada. Não
são delta. Qwen4 não saiu.

## O que cada delta declara (a validar, não a assumir)

- **26.9.2:** speculative decoding chega à velocidade cheia já na 1ª request (antes ~15ª); draft
  por shortlist; `--max-mtp-ctx`; `--prefix-cache-disk` (conversa longa de Flash-Next no SSD).
  Parte dos ganhos usa kernels NAX de M5 e **não** se aplica ao M4 Max.
- **MTPLX 2.11.2:** guard de memória recusa antes do swap em máquina de 128 GB; visão no Flash-Next.
  A rota flash-decoding verify é gated para M5+; o M4 Max não a usa.
- **oMLX 0.7.0.dev2:** +8–20% de prefill no Qwen3.8 com PLE via SSD. É pré-release.

## Protocolo

Harness existente [cache_probe.py](../qwen3.8-prefix-cache/scripts/cache_probe.py). Base HTTP
com sufixo `/v1` (sem ele, a tokenização falha com `content is required`). ID real via `/v1/models`.

- Contexto: 32768 para todos os deltas; mais 131072 e 262144 no Flash-Next (P1/P2).
- Cenários: `cold`, `identical`, `append`, `tool_turn`. Adicionar `middle_mutation` no P1.
- Repetições: **3 por cenário** (uma rep é smoke, não sustenta ganho). Temperatura 0, top-p 0.95,
  top-k 20, reasoning xhigh, limite 4096 tokens.
- Um knob por rodada ([[isolate-the-variable-when-measuring]]). Reprobar o baseline instalado na
  mesma sessão antes de declarar ganho ([[runtime-gains-stale-baselines]]).
- Reúso de histórico: só quando o baseline foi medido no mesmo protocolo e o runtime/quant não mudou
  desde então. Vale para o item 4 (baseline oMLX 0.6.4 de 04/09) com um re-probe de drift a 32K. Não
  vale para A/B de versão de runtime recente (itens 1 e 2): o histórico é 1-rep ou de runtime mais
  antigo, então os dois braços rodam juntos na mesma sessão.
- Coletar telemetria RAM/swap/temperatura (faltou no refresh de 04/09).

### Troca de versão

Ambientes isolados em `~/.local/opt/qwen38/{mlx-serve-v26.9.2,mtplx-v2.11.2,omlx-v0.7.0.dev2}`,
preservando os instalados. CLI padrão via symlink em `~/.local/bin/`. Rollback: restaurar o
symlink para `mlx-serve-v26.9.1` / `mtplx-v2.11.1` / oMLX 0.6.4. Verificar o arquivo baixado
contra o SHA256 publicado antes de ativar.

## Procedimentos por delta

Um por delta. Instalar/trocar versão no env isolado, rodar o comando, comparar contra o baseline.
Onde o nome do pacote não está confirmado, verificar antes de instalar.

### 1 — mlx-serve 26.9.2 (P1)

Instalado em `~/.local/opt/qwen38/mlx-serve-v26.9.2` (SHA256 `f2dd5f80…`, canal verificado). A/B pronto:

```
bash bench/qwen38-updates-2026-09/scripts/run-p1-mlxserve-ab.sh both 32768
```

Depois repetir com `131072` e `262144`. Comparar decode/TTFT/cache por cenário, 26.9.2 vs 26.9.1,
na mesma sessão. Saída em `results/p1-mlxserve-v26.9.{1,2}-<ctx>.jsonl`.

### 2 — MTPLX 2.11.2 (P1)

Instalar 2.11.2 no env `~/.local/opt/qwen38/mtplx-v2.11.2` pelo mesmo método do refresh de 04/09
(uv tool; confirmar o nome do pacote). Subir o servidor 27B pelo launcher, porta 8000:

```
QWEN38_MTPLX_BIN=~/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx \
QWEN38_MTPLX_EXPECTED_VERSION=2.11.2 \
  bash bench/qwen3.8-prefix-cache/scripts/run-mtplx.sh V
```

Probe: `cache_probe.py --base-url http://127.0.0.1:8000/v1 --runtime mtplx --runtime-revision v2.11.2
--arm V … --cache-enabled --mtp-enabled`. Baseline: repetir com o bin 2.11.1. Validar o gate de
memória: forçar 128K e confirmar recusa (HTTP 507) antes do swap, sem crash.

### 3 — Config de 1M no mlx-serve (P1) — PULADO por ora (2026-09-12)

Adiado a pedido: o prefill de 1M é caro (~15–25 min/cold) e não bloqueia os demais itens. Retomar
depois. Procedimento preservado abaixo.

Sem A/B de versão. Exercitar a feature já na 26.9.1, no build ddalcu, com a config da comunidade:

```
~/.local/opt/qwen38/mlx-serve-v26.9.1/mlx-serve \
  --model ~/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd \
  --serve --host 127.0.0.1 --port 11234 \
  --ctx-size 1048576 --kv-quant 8 --mtp \
  --prefix-cache-mem 10GB --prefix-cache-entries 1 --ssm-checkpoint-max 16 --metrics
```

Medir: sobe sem estourar 128 GB? TTFT/decode a 262144 e além; needle no `cold`. Coletar RAM/swap.
Comparar contra a config FS atual (prefix-cache 16GB, entries 64).

### 4 — oMLX 0.7.0.dev2 (P2)

Instalar o pré-release no env `~/.local/opt/qwen38/omlx-v0.7.0.dev2` (pip `--pre`; confirmar o
pacote). A/B isola só o offload de PLE-SSD: mesma config, modelo `Jundot oQ4e-mtp`, arm FN nas duas
versões (0.6.4 e dev2):

```
QWEN38_OMLX_BIN=~/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/omlx \
QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2 \
OMLX_MODEL_ROOT=~/.cache/local-llms/qwen3.8-prefix-cache \
  bash bench/qwen3.8-prefix-cache/scripts/run-omlx.sh FN
```

Probe idem, `--runtime omlx --runtime-revision v0.7.0.dev2`. Comparar prefill (validar +8–20%) e
custo de decode. Pré-release: não promover a estável.

**Reúso de histórico (baseline 0.6.4):** o braço 0.6.4 já foi medido em 04/09 no mesmo protocolo
(arm FN, oQ4e, cache_probe): `../qwen38-flash-next/results/refresh-flashnext-{32k,128k,262k}-v064-ssdple.jsonl`.
Rodar **só a 0.7.0.dev2** nos três contextos e comparar contra esses arquivos, em vez de re-rodar a
0.6.4 inteira. Guarda contra drift: um **re-probe da 0.6.4 só a 32K** na mesma sessão; se casar com o
histórico dentro do ruído, a comparação cross-session dos contextos longos vale ([[runtime-gains-stale-baselines]]).
Se divergir, re-rodar a 0.6.4 nos contextos longos também.

### 5 — Trio 27B MTPLX, só runtime json (P2)

Pesos inalterados; mudou só `mtplx_runtime.json` (03/09). Re-baixar o json das revisões novas
(Speed/Quality/Bare) por cima dos snapshots pinados. Rodar `run-mtplx.sh V` (e `Y`) com o json novo
vs o pinado, **mesma versão de runtime**, isolando o tuning. Comparar decode/estabilidade. Sem
download de pesos.

### 6 — DFlash2 densa 27B (P3)

Gate de disco primeiro (`df -h`). Baixar `incoai/Qwen3.8-27B-DFlash2` (MLX) ou
`z-lab/Qwen3.8-27B-DFlash2-GGUF` para o MODEL_ROOT, na revisão pinada. Rodar no runtime que suporta
a draft head (mlx-serve para MLX; llama.cpp para GGUF), MTP ligado. **Gate de qualidade:**
Terminal-Bench (protocolo do 27B) antes do veredito. Comparar contra a densa 27B sem DFlash2.

### 7 — ddalcu Qwen3.6-35B-A3B 4bit (P3) — PULADO por ora (2026-09-12)

Adiado a pedido. Procedimento preservado abaixo.

Gate de disco. Baixar `ddalcu/Qwen3.6-35B-A3B-MLX-Serve-4bit` (revisão pinada) para o MODEL_ROOT.
Rodar em mlx-serve. Medir decode vs densa 27B; **Terminal-Bench** para qualidade antes do veredito.

## Gates

- **Disco antes de qualquer pull** ([[check-disk-before-model-downloads]]): rodar `df -h`; o volume
  de boot já chegou a 0 livre. Vale para os itens 6 e 7.
- **Correção é eliminatória; velocidade sozinha não promove.** Um build que muda pesos ou qualidade
  (itens 6 e 7) passa pelo **Terminal-Bench** antes de qualquer veredito — foi o gate que deu NO-GO
  na densa 27B ([[qwen38-27b-nogo-verdict]]).
- P1/P2 são só runtime/config sobre os mesmos pesos: o gate é decode/prefill/cache + estabilidade,
  não qualidade.

## Fases

1. **P1 (sem download):** bump 26.9.2, bump MTPLX 2.11.2, config de 1M. Cada um isolado, A/B contra
   o baseline instalado. Saída: `results/p1-*.jsonl`. Driver do bump mlx-serve:
   [scripts/run-p1-mlxserve-ab.sh](scripts/run-p1-mlxserve-ab.sh) `<v26.9.1|v26.9.2|both> [ctx]`.
   Ele isola só o binário (mesmo modelo, mesma config FS) e reusa o `cache_probe.py`.
2. **P2:** oMLX 0.7.0.dev2 — A/B isolado do PLE-SSD (prefill). Re-pull do runtime json do trio 27B.
3. **P3 (com download, atrás do gate de disco + T-Bench):** DFlash2 27B e ddalcu 3.6-35B.
4. **Veredito por delta:** promover, descartar ou adiar.

## Saídas

- Distilados em `results/` (≤ ~1 MB/arquivo); logs crus em `logs/` (ignorados pelo git).
- Scores canônicos por modelo continuam no submódulo `tools/local-llm-bench/results/`.
