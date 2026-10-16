# Runtimes estáveis que rodaram (registro de 2026-10-16)

`install-runtimes.md` e `mlx-serve-26102-version.txt` registram só o mlx-serve 26.10.2-pre-release.1 e o oMLX 0.7.1.dev1. Os braços abaixo rodaram nas versões seguintes, instaladas com `scripts/install-runtime.sh` e os overrides `MLX_TAG` e `OMLX_TAG`. Este registro foi lido no rig em 2026-10-16.

| runtime | diretório | `--version` | SHA-256 do binário | braços |
| --- | --- | --- | --- | --- |
| mlx-serve 26.10.2 (estável) | `~/.local/opt/qwen38/mlx-serve-v26.10.2/` | `mlx-serve 26.10.2` | `3865ef5e7453ed58390a5accd4697920cec236d04ca7842d4fa1b096700004e1` | `n2x`, `o1rm` |
| oMLX 0.7.1.dev2 | `~/.local/opt/qwen38/omlx-v0.7.1.dev2/` | `0.7.1.dev2` (`omlx-0.7.1.dev2.dist-info`) | — (venv) | `o1x`, `o1r`, `x1` |

O campo `runtime_revision` dos JSONL diz `v26.10.2` e `v0.7.1.dev2`. Ele não separa a estável da pre-release; esta tabela é o registro de qual binário rodou. O smoke `n2x-8192-t1.0-smoke.jsonl` em `results/` é da estável (o smoke da pre-release foi para `logs/prerelease-smoke`).
