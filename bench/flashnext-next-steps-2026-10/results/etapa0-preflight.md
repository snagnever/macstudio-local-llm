# Etapa 0 — pré-voo (2026-10-13)

| item | valor |
| --- | --- |
| disco livre (`df -g /`) | 749 GB |
| mlx-serve referência | 26.10.1 (`~/.local/opt/qwen38/mlx-serve-v26.10.1`), llama.cpp embutido b10809 |
| mlx-serve candidato | 26.10.2-pre-release.1, SHA256 `be81f9c8c903c3fa621880ffde21ee4ddc40aa840927add44dfc5794e75cb2bf` (digest do GitHub), llama.cpp embutido b11429 |
| flag de profundidade MTP | `--mtp-max-depth` (o 26.10.2 trocou `--mtp-depth` por `--mtp-min-depth` e `--mtp-max-depth`) |
| oMLX | 0.7.1.dev1 (tag `c0b1056`), MLX 0.32.3 |
| variáveis OMLX_* do launcher | `OMLX_BASE_PATH`, `OMLX_MODEL_DIR`, `OMLX_PORT` e `OMLX_CACHE_ENABLED` presentes no pacote; `OMLX_MOE_EXPERT_OFFLOAD` ausente e sem uso nos scripts; `SETTINGS_VERSION 1`; `qwen4_ple_ssd_offload` conhecido |
| default de reasoning_effort | xhigh nos três packs; aceitos: xhigh, medium, low |
| submódulo local-llm-bench-m4-32gb | `a4a95bb` (>= a4a95bb) |

## Leitura

O `gh` do rig não tem login por SSH (401). Os assets do GitHub são baixados no laptop com `gh`, conferidos contra o digest publicado e copiados por `scp`. As tasks 8 (llama.cpp) e o download de packs seguem a mesma regra quando precisarem do `gh`.

Flags novas do 26.10.2-pre relevantes para a campanha: `--mtp-min-depth`/`--mtp-max-depth`, `--no-prefix-cache-ram`, `--llama-mtp-drafts` (default 2) e `--llama-ubatch` para GGUF. O memory guard `auto` passa a usar o limite de working set da GPU em vez de 80% do wired. O llama.cpp embutido é b11429, abaixo do b11569 recomendado para Metal; isso vale para o braço `g1m` do Task 8.

Testes: `tests/` 18 passed no rig; testes das campanhas engine-updates e swift15 sem regressão (50 passed, 1 skipped antes e depois); `test_launchers.sh` sai com 65 antes e depois da mudança.
