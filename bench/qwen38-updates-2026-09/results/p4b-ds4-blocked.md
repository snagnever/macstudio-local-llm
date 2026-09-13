# item 4b — ds4 Flash-Next: DEFERIDO (engine incompativel no rig)

Modelo baixado e completo: base+MTP gguf 74.9 GB + sidecar PLE 32 GB (ivanfioravanti DS4-Q4).

O ds4 **embutido no mlx-serve 26.9.2 e a variante DeepSeek-V4**: ao servir o gguf do Flash-Next
(--engine ds4) ele mapeia ~70 GiB (footprint confirmado) mas falha:
- `unsupported GGUF type 39` em ffn_down_exps (MXFP4 do down-projection),
- fatal `required metadata key is missing: deepseek4.block_count` (espera schema deepseek4, nao qwen4exp).

--engine llama tambem nao serve: o base gguf nao tem PLE inline (fica no sidecar externo), e a
llama.cpp nao conhece o --ple. Logo nenhum engine embutido do mlx-serve roda este build.

Runner correto: **ds4 fork ivanfioravanti/ds4 branch qwen3.8-flash-next** (git clone + make). Mas e
CLI standalone (`./ds4 --model ... --ple ... --metal --ctx --mtp`), NAO expoe OpenAI /v1 — o
cache_probe nao consegue dirigi-lo. Head-to-head via cache_probe fica INVIAVEL sem um servidor.

Opcoes p/ retomar: (a) buildar o fork e usar o bench nativo do ds4 (numeros nao comparaveis ao
cache_probe/mixed-4-8); (b) esperar suporte a qwen4exp+MXFP4 no ds4 embutido do mlx-serve ou na oMLX.

Referencia do card (M3 Ultra 512GB): prefill 1063-1171, decode 42-45 plain / 45-56 MTP, top-1 96.6%.
Modelo em disco (~107 GB total) fica como candidato a limpeza se o teste nao for retomado.
