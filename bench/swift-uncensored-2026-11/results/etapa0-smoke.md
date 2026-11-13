# Task 0 — downloads e smoke (2026-11-13)

**Dois dos três packs sobem no Splash 1.6.1.** O `z2h` e o `z3h` passam no smoke. O Splash recusa o `z1h` por um
tipo de tensor que a regra do cabeçalho não cobria. Um recast sem perda desses tensores gera o braço `z4h`, que ainda
não rodou.

## Downloads

`scripts/download-packs.sh z1 z2 z3`, com o `snapshot_download` do Python do Splash 1.6.1. Horas do relógio do rig.

| pack | início | fim | arquivos GGUF | tamanho (`du -skL`) |
|---|---|---|---:|---:|
| `z1` jackjusko `IQ4_XS/` | 11:11:14 | 11:27:21 | 6 | 92 509 060 KiB |
| `z2` huihui-ai `swift-IQ3_S/` | 11:27:21 | 11:41:08 | 2 | 81 781 004 KiB |
| `z3` SC117 `IQ3_S` | 11:41:08 | 11:54:59 | 2 | 81 591 128 KiB |

Disco livre: 859 GB antes e 615 GB depois.

## Smoke a 32768

`logs/chain-t0.sh`: um boot por braço, 1 rep do `cache_probe`.

| braço | carga | `Loading` → `Ready` | needles | hit `append` / `tool_turn` | decode (tok/s) | cold TTFT | warm TTFT `tool_turn` | swap Δ |
|---|---|---:|---|---|---|---:|---:|---:|
| `z1h` | **recusado** | – | – | – | – | – | – | – |
| `z2h` | passa | 30 s | 5/5 | 0.963 / 0.962 | 106.6 a 113.8 | 33.5 s | 1.48 s | 0.0 GB |
| `z3h` | passa | 17 s | 5/5 | 0.963 / 0.962 | 108.6 a 112.1 | 33.5 s | 1.47 s | 0.0 GB |

- O `z2h` resolve a variante `swift-IQ3_S` pela pasta. O `z3h` resolve `IQ3_S` pelos arquivos da raiz. O Step 10 do
  plano (snapshot de symlinks) não foi preciso.
- O boot do `z2h` foi o primeiro de um pack GSQ-RCO `IQ3_S` nesta instalação e inclui o aquecimento dos kernels.
- O snapshot `0142554` do `k2` ficou com 96 278 696 KiB antes e depois de cada boot.
- O servidor do usuário voltou na porta 8585 no fim da fila.
- Um smoke tem 1 rep por cenário. Os números de velocidade não dão veredito; a Task 2 mede com controle.

## `z1h`: recusa do Splash

```
error: GGUF tensors this build cannot load: indexer.q_proj.weight (F16) in 12 layers, indexer.k_proj.weight (F16) in 12 layers
```

O pack do jackjusko guarda as 24 projeções do indexer da QSA em `F16`. Os packs que carregam (`k2`, `k8`, `z2`, `z3`)
guardam esses tensores em `BF16`. A regra do `gguf_header.py check` cobria só os `hc_*_inject`; ela agora também
recusa `indexer.q_proj` e `indexer.k_proj` em `F16`, com teste.

## `z4h`: o `z1` com o indexer em BF16

`scripts/gguf_recast.py` copia os 6 shards do `z1` e regrava só esses 24 tensores como `BF16`.

- A conversão para se um valor `F16` não couber exato em `BF16`. Nenhum valor falhou: os 24 tensores têm os mesmos
  valores nos dois arquivos.
- `F16` e `BF16` têm 2 bytes, então só mudam o campo de tipo e os bytes desses tensores. Os outros 1200 tensores e os
  metadados não mudam.
- A cópia usa `cp -c` (clone do APFS). O disco livre ficou em 615 GB.
- O resultado fica só no rig, em `~/.cache/huggingface/hub/models--rig-local--Swift-1.5-Flash-Next-Heretic-V2-IQ4_XS-plus-bf16idx/`,
  com a revisão `bd3bca0` do `z1`. Os arquivos do jackjusko no cache não mudaram.

| pack | tensores | `indexer.*_proj` |
|---|---:|---|
| `z1` (jackjusko) | 1224 | 24 em `F16` |
| `z4` (recast) | 1224 | 24 em `BF16` |

O `z4h` ainda não subiu no Splash. O smoke dele roda depois da fila da Task 1.
