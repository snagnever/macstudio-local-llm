# Task 0 — pré-voo (2026-11-13)

## Acesso ao rig

**Bloqueado.** No MacBook, `ssh -o BatchMode=yes vitor@mac-studio hostname` e o mesmo comando com `100.110.87.118` dão
`Operation timed out`. O `tailscale ping mac-studio` responde `peer's node key has expired`. O usuário precisa
reautenticar o Tailscale no rig. O disco livre, a versão do Splash e o tamanho do snapshot `0142554` não foram lidos.

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

- `bench/swift-uncensored-2026-11/tests`: 33 passam.
- Com a mudança no `run-candidate.sh`: splash161 25, flashnext-weights 63, splash16 63, flashnext-concurrency 206,
  claude-code-concurrency 6 e splash-longctx 33 passam.

## Falta

Steps 1, 8 e 9 da Task 0: estado do rig, downloads (263.1 GB) e smoke.
