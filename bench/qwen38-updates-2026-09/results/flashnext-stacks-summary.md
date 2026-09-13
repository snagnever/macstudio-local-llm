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
| mlx-serve YaRN @1M      | 17.3 | 502 | 2079 s | — | 105.2G | 1.6G | 26.5G | cold ok** |
| ds4 (fork) @32K         | 40.4 | 577 | 47 s   | **0.00** | 80.6G | 1.8G | — | ok*** |
| ds4 (fork) @128K        | 39.2 | 572 | 220 s  | **0.00** | 83.8G | 1.7G | — | ok |
| ds4 (fork) @256K        | 36.1 | 561 | 458 s  | **0.00** | 88.1G | 1.7G | — | ok |

\* 262K tool_turn truncou em max_tokens (não é erro). \** 1M: o cold gerou needles corretas; a 2ª
request (identical) deu erro transitório. \*** ds4 32K append falhou (1 cenário).

## Veredito

**mlx-serve 26.9.2 é a melhor stack do Flash-Next no M4 Max, em todo o range.** Ganha decode em
todo contexto (67/58/57/51 vs ds4 40/39/36), ganha prefill, e **reusa prefix-cache** (ds4 não reusa
neste harness — todo turno re-prefila). Estende via YaRN a **512K com decode ainda forte (51)** e
alcança **1M com needle correta** (decode cai a 17, cold ~35 min — teto prático ~512K).

**ds4 (fork ivanfioravanti):** footprint menor (80–88G wired vs 105–111G), mas **mais lento em tudo**
no M4 Max e **sem reuso de cache**. Os números do card (M3 Ultra: decode 45–56, prefill ~1100) NÃO
se sustentam aqui (40 / 580) — gap de banda/compute. A hipótese "footprint menor → ganho em contexto
longo" **não se confirmou**: a 256K o mlx-serve entrega 57 tok/s vs 36 do ds4, e vai além (512K/1M).
Ressalva: o "sem reuso" do ds4 pode ser flag ausente (`--kv-disk-dir`); decode/prefill/footprint são
comparações limpas, a de cache pode estar desfavorável ao ds4.

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
