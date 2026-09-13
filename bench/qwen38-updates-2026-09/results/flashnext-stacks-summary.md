# Flash-Next por stack no M4 Max 128 GB (2026-09-13)

Medido com `cache_probe` (fixture audit_retrieval, temp 0, reasoning xhigh, max 4096 tok).
Footprint = **memória wired** (o RSS via ps subconta buffers Metal). Swap e disk-spill amostrados a 5s.

## Velocidade + memória

| stack / ctx | decode | prefill | cold TTFT | cache reuse | wired | swap | kv-disk | correção |
|---|---:|---:|---:|---|---:|---:|---:|---|
| mlx-serve 26.9.2 @32K   | **67.1** | 732 | 37 s   | 1.00 | ~105G | ~1.7G | 0 | ok |
| mlx-serve 26.9.2 @128K  | 57.8 | 703 | 179 s  | 1.00 | ~105G | ~1.7G | — | ok |
| mlx-serve 26.9.2 @262K  | 56.8 | 676 | 380 s  | 1.00 | ~105G | ~1.7G | ~8G | ok* |
| mlx-serve YaRN @512K    | 51.4 | 615 | 844 s  | 1.00 | 111.4G | 1.7G | 19.8G | ok |
| mlx-serve YaRN @1M      | 34.7 | 502 | 2079 s | n/d | 105.2G | 1.6G | 26.5G | cold ok** |
| ds4 (fork) @32K         | 40.4 | 577 | 47 s   | 0.00† | 80.6G | 1.8G | — | ok*** |
| ds4 (fork) @128K        | 39.2 | 572 | 220 s  | 0.00† | 83.8G | 1.7G | — | ok |
| ds4 (fork) @256K        | 36.1 | 561 | 458 s  | 0.00† | 88.1G | 1.7G | — | ok |
| ds4 (fork) @32K +kv-disk| 40.6 | 580 | 47 s   | **0.98/0.94** | ~81G | 1.8G | — | ok |

\* 262K tool_turn truncou em max_tokens (não é erro). \** 1M: só o **cold** rodou (decode 34.7,
needles ok). A 2ª request (identical) foi **recusada por memória** (`PrefillDoesNotFit`): com a KV do
1º prompt pinada (~15.6G), o working set de prefill do 2º (~28G) não cabe nos ~23G restantes, nem no
chunk mais estreito. **Com kv-quant `turbo4` o follow-up CABE** (KV ~metade): identical cache 1.00,
TTFT 1.6s, needle ok — cache a 1M é possível. **Mas o decode desaba a ~5 tok/s** (vs 34.7 kv8 no cold).
1M = "one-shot ~35 tok/s (kv8)" OU "multi-turno viável mas ~5 tok/s (turbo4)". Teto prático utilizável =
**512K** (decode 51, cache reusa, needle ok). \*** ds4 32K append falhou (1 cenário).
† ds4 SEM `--kv-disk-dir` (default): não persiste/reusa. **Com `--kv-disk-dir` o ds4 REUSA** o prefixo:
identical TTFT 2.0s (cache 0.98), tool_turn 3.3s (0.94) — ver linha "+kv-disk". Decode inalterado (40.6).

## Veredito

**mlx-serve 26.9.2 é a melhor stack do Flash-Next no M4 Max, em todo o range.** Ganha decode em
todo contexto (67/58/57/51 vs ds4 40/39/36) e ganha prefill. Ambos reusam prefix-cache — mlx-serve
por default (identical 0.1s), o **ds4 só com `--kv-disk-dir`** (identical 2.0s/0.98, tool_turn 3.3s/0.94);
o caminho quente do mlx-serve é um pouco mais rápido. Estende via YaRN a **512K com decode ainda forte
(51)** e alcança **1M no cold** (decode 34.7, needle ok, ~35 min), mas a 2ª request a 1M é recusada por
memória — **1M = one-shot cold em 128 GB; teto prático utilizável = 512K**.

**ds4 (fork ivanfioravanti):** footprint menor (80–88G wired vs 105–111G), mas **mais lento em decode
e prefill** no M4 Max. Reusa prefix-cache com `--kv-disk-dir` (sem ele, default, não reusa). Os números
do card (M3 Ultra: decode 45–56, prefill ~1100) NÃO se sustentam aqui (40 / 580) — gap de banda/compute.
A hipótese "footprint menor → ganho em contexto longo" **não se confirmou**: a 256K o mlx-serve entrega
57 tok/s vs 36 do ds4, e vai além (512K/1M). Ganho do ds4 fica só no footprint.

## Spill (resposta direta)

- **Swap involuntário: nenhum relevante** — plano em ~1.7G (baseline) em todos os contextos, até 1M.
- **Disk-spill voluntário (mlx-serve `--prefix-cache-disk`):** a KV longa vai para `~/.mlx-serve/kv-cache`
  por design — ~20G @512K, ~26G @1M. É assim que a RAM fica limitada (kv-quant 8 + tier de disco) e o
  512K/1M cabem sem swap. minFree tocou 0.1G a 512K (borda), mas sem thrash.
- **ds4:** a PLE fica sempre no sidecar em disco (CPU, demand-paged); por isso o wired menor.

## Setup do ds4 (para retomar)

Fork `ivanfioravanti/ds4` branch `qwen3.8-flash-next`, `make ds4-server ds4-bench`. Rodar **do
diretório do repo** (compila `metal/*.metal` em runtime), `--ple <sidecar>` obrigatório, `--tokenizer-path`
no cache_probe (ds4-server não tem `/tokenize`). Driver: `scripts/run-p4c-ds4server-flashnext.sh`.
