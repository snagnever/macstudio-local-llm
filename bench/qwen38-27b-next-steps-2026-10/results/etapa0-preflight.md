# Etapa 0 — preflight 2026-10-13T11:43:46Z

Rig worktree: ~/LocalProjects/local-llms-27b (branch bench/qwen38-27b-next-steps-2026-10). The main checkout ~/LocalProjects/local-llms holds the paused Flash-Next campaign and was not touched.

## Runtimes
- /Users/vitor/.local/opt/qwen38/ds4-fork/
- /Users/vitor/.local/opt/qwen38/ds4-upstream/
- /Users/vitor/.local/opt/qwen38/llama-b11569/
- /Users/vitor/.local/opt/qwen38/llama-v0.2.0-b10566/
- /Users/vitor/.local/opt/qwen38/mlx-dspark-v0.18.0/
- /Users/vitor/.local/opt/qwen38/mlx-dspark-v0.20.3/
- /Users/vitor/.local/opt/qwen38/mlx-serve-v26.10.1/
- /Users/vitor/.local/opt/qwen38/mlx-serve-v26.10.2-pre-release.1/
- /Users/vitor/.local/opt/qwen38/mlx-serve-v26.10.2/
- /Users/vitor/.local/opt/qwen38/mlx-serve-v26.8.11/
- /Users/vitor/.local/opt/qwen38/mlx-serve-v26.8.9/
- /Users/vitor/.local/opt/qwen38/mlx-serve-v26.9.1/
- /Users/vitor/.local/opt/qwen38/mlx-serve-v26.9.2/
- /Users/vitor/.local/opt/qwen38/mtplx-v2.11.1/
- /Users/vitor/.local/opt/qwen38/mtplx-v2.11.2/
- /Users/vitor/.local/opt/qwen38/mtplx-v2.12.2/
- /Users/vitor/.local/opt/qwen38/omlx-v0.7.0.dev2/
- /Users/vitor/.local/opt/qwen38/omlx-v0.7.0/
- /Users/vitor/.local/opt/qwen38/omlx-v0.7.1.dev1/
- /Users/vitor/.local/opt/qwen38/splash-v1.3.1/

## Versions
```
mlx-dspark generate: error: unrecognized arguments: --version
0.7.1.dev1
version: 0.6.0-dev (build 11569, commit 073b74034)
mlx-serve 26.10.2
Splash 1.3.1
macmon 0.7.2
macOS 26.6.2
```

## Disk
/dev/disk3s1s1      1858   11       461     3%  458732 4293796001    0%   /

## Ports
11234: free
8000: free
8080: free
8484: free
8585: free

## Downloads (fetch_pack receipts)
- Jundot/Qwen3.8-27B-oQ4e-mtp 49c1d60367d9 17.0 GB
- Jundot/Qwen3.8-27B-oQ8e-mtp 6c76ddfb82af 30.0 GB
- ddalcu/Qwen3.8-27B-MLX-Serve-8bit 7775059e955f 35.1 GB
- scottlowry/Swift-1.5-Qwen3.8-27b-oQ4e-mtp 881dc1914f65 17.0 GB
- ggml-org/Qwen3.8-27B-GGUF 71bc7b627595 34.4 GB

## Template of the 27B (Jundot oQ4e refit)
```
reasoning_effort = reasoning_effort|default('xhigh') 
reasoning_effort not in ('xhigh', 'medium', 'low') 
reasoning_effort ~ '. Supported types are xhigh (default), medium, and low.') }}
reasoning_effort == 'xhigh' 
Supported types are xhigh (default), medium, and low.') }}
```

## Pack layout
- Jundot-Qwen3.8-27B-oQ8e-mtp-6c76ddfb82afb30413685cee1774de947a3da486: 6 safetensors, index yes, template yes, mtp 0, drafter no
- Jundot-Qwen3.8-27B-oQ4e-mtp-49c1d60367d976a730a725ea3bbed32a8e94b878: 4 safetensors, index yes, template yes, mtp 0, drafter no
- ddalcu-Qwen3.8-27B-MLX-Serve-8bit-7775059e955f60b5a8f5da1b859466390bcad351: 6 safetensors, index yes, template yes, mtp 0, drafter yes
- scottlowry-Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc1914f65e37a51f1e26dc0b6a49995e6cf37: 4 safetensors, index yes, template yes, mtp 0, drafter no
- ggml-org-Qwen3.8-27B-GGUF-71bc7b627595dc8a91039addd9c791ae548d6747: dflash-Qwen3.8-27B-Q8_0.gguf mmproj-Qwen3.8-27B-Q8_0.gguf mtp-Qwen3.8-27B-Q8_0.gguf Qwen3.8-27B-Q8_0.gguf 
