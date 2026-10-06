# Instalação do mlx-serve 26.10.1 (2026-10-06)

- Asset: `https://github.com/ddalcu/mlx-serve/releases/download/v26.10.1/mlx-serve-bin-macos-arm64.tar.gz`
- SHA256 verificado: `e53056e481364ff72188fafea8b3eb0aeb0b5b7cebcd6e6e7d26bf1ce4223873` (OK)
- O tarball tem o diretório de topo `mlx-serve-macos-arm64/`; extraído com `--strip-components=1` em
  `~/.local/opt/qwen38/mlx-serve-v26.10.1/` (`mlx-serve`, `lib/`, licenças).
- `--version`: `mlx-serve 26.10.1`, `mlx 0.32.3` (o 26.9.2 usa MLX 0.32.2).
- Symlink `~/.local/bin/mlx-serve` mantido em 26.9.2.

Flags conferidas no `--help`:

```
--os-reserve-gib <n>  Free RAM left out of every memory plan so macOS keeps
                      room (default: an eighth of RAM, 2 to 8 GB). 0 turns it off
--ple-gpu             Qwen3.8-Flash-Next: gather the n-gram table on the GPU. Keeps the whole
                      ~30 GB table resident beside the weights for a few % faster prefill/decode;
                      off = rows read from the mmapped file on demand.
--mtp-greedy-tail     Sampled requests draft only the first MTP token
--max-mtp-ctx <n>     Keep MTP speculative decoding OFF past <n> context tokens (default: 0 = no ceiling)
--kv-quant <mode>     KV-cache quantization scheme
```

Nota: o `--os-reserve-gib` (desde 26.9.5) reserva 8 GB por default num Mac de 128 GB. O 26.9.2 não
tem essa reserva. Os braços n1/n2 rodam com o default do binário; se um cenário a 128K for recusado
por memória, esse é o primeiro suspeito.
