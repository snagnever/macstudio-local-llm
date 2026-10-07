# Pesos (2026-10-07)

## Pack MTPLX 27B @ 1d5087d

`Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-1d5087d2062c02b279180a53e4016cf9cd7a3d7e` foi criado por
hardlink do `123db8b`. Só o `mtplx_runtime.json` e o `README.md` foram baixados de novo; o pack antigo não mudou.

Diferença real no `mtplx_runtime.json`: o sampler padrão passa de `temperature 0.6` para `1.0`
(top_p 0.95, top_k 20), e o arquivo ganha `mtp_depth_default: 3` e `source_sha` do trunk. As outras
diferenças são caminhos locais trocados por ids do HF e reordenação de chaves. Os pesos são os mesmos.

## ds4 upstream

- Repositório: `antirez/ds4` @ `0aaea5a`, em `~/.local/opt/qwen38/ds4-upstream`, `make ds4-server`.
- GGUF: `antirez/qwen3.8-flash-next-gguf` / `Qwen3.8-Flash-Next-Q4.gguf` (`download_model.sh qwen38-q4k`),
  177 280 286 720 bytes (165 GiB), em `gguf/`; `ds4flash.gguf` aponta para ele. MTP e tabela n-gram BF16 embutidas.
- O script precisa do CLI `hf` no PATH; o download usou o `hf` do venv `omlx-v0.7.0`.
- Flags usadas no launcher (do `--help`): `-m`, `--metal`, `--mtp-timing` (MTP embutida + contadores),
  `-c`, `--kv-disk-dir` + `--kv-disk-space-mb 102400` (prefix cache em disco), `--host`, `--port`.

## Disco

510 GB livres antes do download; 343 GB depois.

## Packs sem mudança

iQ-MLX-4.7bpw, MTPLX Flash-Next Optimized-Speed (só README no HF), oQ4e-mtp, oQ8e-mtp, mlx-community 27B 8bit,
DFlash2 (só o card no HF).
