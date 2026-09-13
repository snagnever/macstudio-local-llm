# P2 item 4 — oMLX 0.7.0.dev2: DEFERIDO (incompatibilidade de PLE offload em pre-release)

Instalado: omlx v0.7.0.dev2 em venv isolado (git+https://github.com/jundot/omlx.git@v0.7.0.dev2).
Serve 0.7 e multi-modelo (--model-dir descobre subpastas); flags: --memory-guard {off,safe,
balanced,aggressive}, --paged-ssd-cache-dir, etc.

Bloqueio: o Flash-Next oQ4e carrega **PLE residente (~104 GB model_memory / ~98 GB footprint)**.
- memory-guard balanced: rejeita ate prompt minimo (cap 96.77 GB = 90% do teto Metal 107.52 GB).
- memory-guard aggressive: carrega e responde, mas deixa **~0.1 GB livres** (swap) — inseguro para benchmark.

Causa: o modo PLE vem do setting por-modelo `qwen4_ple_ssd_offload` (default False -> "resident").
`configure_ple_runtime` usa `mode or OMLX_QWEN4_PLE_MODE`, mas o caller passa o setting explicito,
entao **o env `OMLX_QWEN4_PLE_MODE=mmap` e sobreposto** (log: "PLE mode ... : resident"). O mmap
(equivalente ao qwen4_ple_ssd_offload:true da 0.6.x, que baixava residente 99.6->69.6 GB) exige
setar o setting por-modelo pela maquina de config da 0.7 (model_settings.py / model_profiles.py),
diferente do arm-config da 0.6.x.

Proximo passo (quando retomar): achar como a 0.7 le `qwen4_ple_ssd_offload=True` por modelo
(settings file / profile), validar residente ~70 GB, entao rodar o A/B 32K vs baseline historico
0.6.4 (refresh-flashnext-32k-v064-ssdple.jsonl) + drift. Ate la, item 4 fica DEFERIDO.
