# Task 6: Qualidade — resultado parcial

**Estado: pulada pelo usuário em 08/11, às 06:20 (relógio do rig).** O peso é o mesmo, e só a release muda, então o usuário considera que a qualidade não muda. A bateria do `k2g` completou 5 de 6 suítes. O veerman, o longctx e o probe de tool calls não rodaram.

`k2g` (Swift 1.5 `IQ4_XS`, Splash 1.6.0) contra `k2a` (mesmo peso, Splash 1.4.0), a 262144, effort `xhigh`. Fonte: `swift15-flashnext-2026-10/scripts/summarize_ab.py --base k2a --cand k2g`, com o `k2a` de `splash-longctx-2026-10/results/q262/t1/`.

| suíte | `k2a` acertos | `k2g` acertos | truncadas `k2a` / `k2g` | tempo total `k2a` / `k2g` |
|---|---:|---:|---|---|
| humaneval | 147/164 | 144/164 | 1 / 1 | 1240 / 1359 s |
| gpqa | 41/50 | 44/50 | 3 / 1 | 4125 / 3907 s |
| livecodebench | 47/50 | 46/50 | 1 / 1 | 3705 / 3329 s |
| jdhodges | 37/40 | 35/40 | 0 / 0 | 96 / 95 s |
| if | 19/20 | 20/20 | 0 / 0 | 40 / 44 s |

Gates: G1 passa nas 5 suítes. G2 passa em gpqa e livecodebench. No livecodebench, o `k2g` usa menos tokens medianos (1182 contra 1548).

## Conclusão

- Nas 5 suítes completas, a 1.6.0 não mostra perda de qualidade contra a 1.4.0. Uma passada por versão.
- Para a regra "Trocar o launcher", a Task 6 conta como **sem regressão observada**. A regra já falha na Task 4.

## O que não rodou

- veerman (12 perguntas).
- `longctx_probe.py` a 131072 e 262144.
- `toolcall-probe.sh k2g --sessions 20`.
