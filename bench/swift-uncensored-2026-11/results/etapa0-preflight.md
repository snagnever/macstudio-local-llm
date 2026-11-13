# Task 0 — pré-voo (2026-11-13)

## Acesso e estado do rig

O SSH voltou em 13/11, depois que o usuário reautenticou o Tailscale. Antes disso, o `tailscale ping mac-studio`
respondia `peer's node key has expired`.

| item | valor |
|---|---|
| host, macOS | `macstudio`, 26.6.2 |
| disco livre | 859 GB de 1858 GB |
| Splash | `Splash 1.6.1` em `~/.local/opt/qwen38/splash-v1.6.1/` |
| pack `k2` | `models--ukisai--Swift-1.5-Qwen3.8-Flash-Next-GGUF`, 92 GB |
| cache do Hugging Face | 617 GB em `hub/`, dos quais 438 GB em `hub/blobs` |
| servidor do usuário | porta 8585, Splash 1.6.1, no ar desde 12/11 17:28 |
| worktree da campanha | `~/LocalProjects/macstudio-local-llm-swiftunc` |
| CLI `hf` | não existe no rig; o download usa o `snapshot_download` do Python do Splash 1.6.1 |

## Campanha anterior no rig

O rig tem o worktree `macstudio-local-llm-uncensored`, na branch `bench/swift15-uncensored-2026-11`, com dois
commits de 07/11 que não estão no GitHub. Ela planejou os mesmos packs no Splash 1.6.0, com os braços `h0` a `h3`.
O log `wait-download.log` mostra o download de `h1` (jackjusko), `h2` (SC117) e `h3` (ukisai GSQ-RCO) em 10/11.
A pasta `results/` dela está vazia: nenhum braço rodou. Em 13/11 o cache não tinha mais as pastas `models--jackjusko`
e `models--SC117`; a causa não foi apurada. Esta campanha não mexe naquele worktree.

O que esta campanha reaproveitou dela:

- o `download-packs.sh`, portado para os braços `z`;
- a sonda da Etapa U (`bench/qwen38-flashnext-daily-driver-2026-09/scripts/refusal_probe.py`, conjuntos `legit` e
  `harmful`), que o `refusal-arm.sh` agora roda junto com os conjuntos AdvBench e JBB.

## Cabeçalhos GGUF nas revisões fixadas

`scripts/gguf_header.py check`, em 13/11, pelo MacBook:

| braço | repo | revisão | arquivos | tensores | regra do Splash |
|---|---|---|---:|---:|---|
| `z0` | `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF` | `99bb8f7` | 2 | 1224 | passa |
| `z1` | `jackjusko/Swift-1.5-Flash-Next-Heretic-ReverseEngineer`, `IQ4_XS/` | `bd3bca0` | 6 | 1224 | passa |
| `z2` | `huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF`, `swift-IQ3_S/` | `cbc7fba` | 2 | 1224 | passa |
| `z3` | `SC117/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF`, raiz | `3db919a` | 2 | 1224 | passa |

O `IQ3_S` do `z0` existe na revisão `99bb8f7`, a mesma do `k8`. A regra cobre só os tensores `hc_*_inject`. A carga
no Splash 1.6.1 segue sem verificação até o smoke.

## Testes

- `bench/swift-uncensored-2026-11/tests`: 34 passam no MacBook e no rig.
- Com a mudança no `run-candidate.sh`, no MacBook: splash161 25, flashnext-weights 63, splash16 63,
  flashnext-concurrency 206, claude-code-concurrency 6 e splash-longctx 33 passam.

## Conjuntos da sonda de recusa

Em `logs/datasets/` no rig, fora do git:

| arquivo | origem | commit | linhas | SHA-256 |
|---|---|---|---:|---|
| `advbench.csv` | `llm-attacks/llm-attacks`, `data/advbench/harmful_behaviors.csv` | `098262e` | 520 | `6cd1a5c63c07610d7eb67307772ee5606017ee950b5770ab288a2c487489d3e1` |
| `jbb.csv` | dataset `JailbreakBench/JBB-Behaviors`, `data/harmful-behaviors.csv` | `886acc3` | 100 | `4a8ec6832056b631eb092dccc60d37a61c3d441268268888b3d006288afeffa1` |
