# 2026-09-04 — Atualização curta das stacks Qwen3.8

## Escopo

Atualizar os runtimes relevantes preservando as instalações anteriores, sem baixar novos pesos. Smoke de inferência no Flash-Next ddalcu, caminho de maior decode medido nesta campanha. Não equivale a avaliação de qualidade de agente.

## Inventário e fontes

- mlx-serve: CLI padrão 26.8.9; baseline da campanha 26.8.11; candidato [26.9.1](https://github.com/ddalcu/mlx-serve/releases/tag/v26.9.1). Melhorias declaradas em QSA prefill/decode, aquecimento de n-gram e prefix cache.
- MTPLX: 2.10.0 → [2.11.1](https://github.com/youssofal/MTPLX/releases/tag/v2.11.1). Melhorias declaradas em decode e cache entre tool turns. Números upstream de M5 Max não são medições deste M4 Max.
- mlx-dspark: 0.17.2 → [0.18.0](https://github.com/ARahim3/mlx-dspark/releases/tag/v0.18.0). Progresso de prefill, separação de reasoning truncado e robustez do CPU co-prefill.
- oMLX: 0.6.4 instalado e release estável atual; mantido.

Notas oficiais completas: [results/refresh-20260904-releases.json](results/refresh-20260904-releases.json).

## Instalação

Ambientes isolados em `~/.local/opt/qwen38/{mlx-serve-v26.9.1,mtplx-v2.11.1,mlx-dspark-v0.18.0}`. Instalações anteriores preservadas. Arquivo oficial mlx-serve verificado contra SHA256 publicado: `b9bb5178ac2dcfbfa232ffa1e6ce77e87a6408a540cbdaabb66d101d667590b0`.

## Protocolo

Harness existente `bench/qwen3.8-prefix-cache/scripts/cache_probe.py`, contexto 32768, uma repetição por cenário cold/identical/append/tool_turn, temperatura 0, top-p 0.95, top-k 20, reasoning xhigh, limite 4096 tokens. Modelo ddalcu mixed-4/8 na revisão `ef5b919d31534faa1997666f1a22d362cd6383cd`; cache e MTP ligados. Base HTTP `/v1`, ID real retornado por `/v1/models`.

A chamada inicial sem `/v1` falhou na tokenização (`content is required`), antes de gerar resultados. A alternativa já existente no harness resolve o contrato; código do harness não foi alterado.

## Resultados

Flash-Next: **4/4 corretos**, sem erros. Uma repetição é smoke, insuficiente para afirmar ganhos sustentados. Comparações com 31/08 são históricas e não A/B contemporâneo.

Limitações de metadados herdadas: o harness infere `quant=8bit` pelo nome do pack mixed-4/8; o pack real é mixed-4/8. Registros históricos trazem flags cache/MTP falsas apesar do launcher FS usar ambos. Não interpretar esses campos históricos como um A/B de configuração. Telemetria RAM/swap/temperatura não coletada nesta rodada.

| Cenário 32K | Decode tok/s | TTFT s | Cache |
|---|---:|---:|---:|
| cold | 56.81 | 38.994 | 0.00% |
| identical | 62.92 | 0.066 | 100.00% |
| append | 60.22 | 40.170 | 0.00% |
| tool_turn | 64.69 | 2.008 | 96.12% |

Prefill frio: 700.15 tok/s vs 567.69 no registro histórico (+23.3%). Decode tool_turn: 64.69 vs 64.11 (+0.9%). Append continua sem cache. A rodada não estabelece ganho sustentado de decode nem melhor qualidade em agentes.

## Verificação final e ativação

CLI padrão atualizado via symlinks `~/.local/bin/`: mlx-serve 26.9.1, MTPLX 2.11.1 e mlx-dspark 0.18.0. oMLX 0.6.4 mantido. Servidores de teste encerrados após as medições.

- MTPLX 2.11.1: Qwen3.8 27B Optimized-Speed carregada, contexto 8192; `17 * 19` respondeu exatamente `323` em 0.897 s, thinking desligado neste request. Smoke de funcionamento, não benchmark de qualidade ou throughput. [Resultado](../qwen3.8-prefix-cache/results/runtime-refresh/refresh-20260904-mtplx2111-smoke.json).
- mlx-dspark 0.18.0: doctor `ok=true`, sem problemas, Metal disponível no M4 Max. Não houve inferência nesta stack. [Diagnóstico](../qwen3.8-prefix-cache/results/runtime-refresh/refresh-20260904-dspark018-doctor.json).
- Flash-Next: [quatro probes 32K](results/refresh-20260904-v2691-32k.jsonl).

Os guards históricos dos launchers permanecem versionados. Para as instalações atuais usar `QWEN38_MTPLX_EXPECTED_VERSION=2.11.1` e `QWEN38_MLX_DSPARK_EXPECTED_VERSION=0.18.0`; informar a revisão real diretamente ao probe, pois o driver geral ainda contém metadados históricos fixos.

Rollback dos CLIs: mlx-serve aponta antes para `~/.local/opt/qwen38/mlx-serve-v26.8.9/mlx-serve` (baseline Flash-Next 26.8.11 também preservado); MTPLX e mlx-dspark apontavam para `~/.local/share/uv/tools/<runtime>/bin/<runtime>`. Basta restaurar esses symlinks. Não houve alteração nos pesos nem nos resultados anteriores.
