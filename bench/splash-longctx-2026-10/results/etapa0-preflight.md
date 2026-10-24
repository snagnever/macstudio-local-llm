# Etapa 0 — pré-voo (2026-10-24)

## Rig

- Mac Studio M4 Max, 128 GB (`hw.memsize` 137438953472). Disco livre: 787 GB antes do download do GSQ-RCO-Coder (58.4 GB).
- O driver diário (mlx-serve 26.10.3, Swift 1.5, 262144) servia na porta 11234. O `idle-gate.sh` recusa com o driver no ar. Cada fila para o driver antes e o religa no fim.

## Versões

| componente | versão | onde |
|---|---|---|
| Splash | 1.4.0 (`splash --version`) | rig, `~/.local/opt/qwen38/splash-v1.4.0/` |
| mlx-serve | 26.10.3 | rig, `~/.local/opt/qwen38/mlx-serve-v26.10.3/` |
| Draft DFlash2 | `incoai/Qwen3.8-Flash-Next-DFlash2` `a22a174` | rig, cache do HF; igual ao HF em 24/10 |
| openai (bateria) | 2.37.0 | rig, resolvido pelo `uv run --with openai` |
| pyyaml (bateria) | 6.0.3 | rig, idem |
| harbor | 0.24.0 (`uv tool install --force harbor==0.24.0`; antes 0.18.0) | laptop |
| terminus-2 | 2.0.0 (`Terminus2.version()`); os runs antigos do repo usaram 0.8.0 | laptop, dentro do harbor |
| Terminal-Bench | `terminal-bench/terminal-bench-2-1@latest`, 89 tarefas baixadas | laptop |
| Docker | 29.6.1, 20.9 GB de RAM, 18 CPUs | laptop |
| Disco do laptop | 1.3 TB livres | laptop |
| Chrome | presente | laptop, para o `render_m4max_guide.py --png` |

Em 24/10, as releases fixadas eram as últimas: Splash 1.4.0 (20/10), mlx-serve 26.10.3 (22/10) e harbor 0.24.0 (05/10). O `main` do Splash tinha 29 commits depois da 1.4.0. Entre eles está a #561, que serve um GGUF com menos experts que a família. Os pesos fixados no plano tinham a mesma revisão no Hugging Face.

## Download

O `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` `bba8885` (`IQ1_M/`, `README.md` e `tensor-allocation/`, sem o `mmproj`) foi baixado com o `snapshot_download` do Python do Splash, direto para o cache do HF que o Splash lê com `--offline`.
