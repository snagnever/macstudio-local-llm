# Instalação dos runtimes (2026-10-07)

Venvs isolados em `~/.local/opt/qwen38/`, criados com `uv venv --python 3.13` (mesmo padrão de 2026-09).

| runtime | comando | versão reportada | MLX | transformers |
| --- | --- | --- | --- | --- |
| MTPLX | `uv pip install 'mtplx==2.12.2'` | `mtplx 2.12.2` | 0.32.2 | 5.16.1 |
| oMLX | `uv pip install 'omlx @ git+https://github.com/jundot/omlx.git@v0.7.0'` | `0.7.0` | 0.32.2 | 5.17.0 |
| mlx-dspark | `uv pip install 'mlx-dspark==0.20.3'` | `0.20.3` (`doctor --json`) | 0.32.3 | 5.19.0 |

- O `mtplx serve --help` lista `--memory-limit`, `--context-window`, `--ssd-session-cache`, `--depth`,
  `--generation-mode` e `--preserve-thinking`.
- O `mlx-dspark serve --help` não tem flag de YaRN nem de rope. O s27 não é elegível para 512K.
- `~/.local/bin` não mudou.
