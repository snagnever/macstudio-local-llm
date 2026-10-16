| suíte | métrica | n2 | w1 |
| --- | --- | ---: | ---: |
| humaneval | acertos | 144/164 | 147/164 |
| humaneval | truncadas | 0 | 1 |
| humaneval | tempo mediano (s) | 6.8 | 5.7 |
| humaneval | tempo total (s) | 3237.1 | 2306.0 |
| humaneval | tokens medianos | 468.5 | 403.0 |
| humaneval | reasoning mediano (chars) | 1338.5 | 1041.5 |
| gpqa | acertos | 45/50 | 43/50 |
| gpqa | truncadas | 4 | 2 |
| gpqa | tempo mediano (s) | 63.9 | 22.3 |
| gpqa | tempo total (s) | 9487.4 | 5674.0 |
| gpqa | tokens medianos | 5124.0 | 1689.0 |
| gpqa | reasoning mediano (chars) | 19040.5 | 4237.5 |
| livecodebench | acertos | 41/50 | 42/50 |
| livecodebench | truncadas | 3 | 1 |
| livecodebench | tempo mediano (s) | 39.1 | 19.1 |
| livecodebench | tempo total (s) | 8648.8 | 4853.7 |
| livecodebench | tokens medianos | 2984.5 | 1448.5 |
| livecodebench | reasoning mediano (chars) | 9172.5 | 3940.0 |
| jdhodges | acertos | 35/40 | 36/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 2.4 | 2.5 |
| jdhodges | tempo total (s) | 162.5 | 129.8 |
| jdhodges | tokens medianos | 113.5 | 109.0 |
| jdhodges | reasoning mediano (chars) | n/d | n/d |
| veerman | acertos | 10/12 | 10/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 3.1 | 3.0 |
| veerman | tempo total (s) | 68.4 | 74.1 |
| veerman | tokens medianos | 141.5 | 164.0 |
| veerman | reasoning mediano (chars) | n/d | n/d |
| if | acertos | 20/20 | 19/20 |
| if | truncadas | 0 | 0 |
| if | tempo mediano (s) | 1.9 | 2.2 |
| if | tempo total (s) | 53.7 | 48.3 |
| if | tokens medianos | 128.0 | 150.5 |
| if | reasoning mediano (chars) | 361.0 | 370.0 |

| gate | resultado |
| --- | --- |
| G1:humaneval | passa |
| G1:gpqa | passa |
| G1:livecodebench | passa |
| G1:jdhodges | passa |
| G1:veerman | passa |
| G1:if | passa |
| G2:gpqa | passa |
| G2:livecodebench | passa |

LiveCodeBench reavaliado (2026-10-16): n2 45/50, w1 47/50. A tabela acima traz o avaliador antigo (41 e 42), que rodava sem o preâmbulo de imports do LiveCodeBench oficial. Ver [lcb-regrade.json](lcb-regrade.json) e [lcb-regrade-published.md](../../flashnext-next-steps-2026-10/results/lcb-regrade-published.md).
