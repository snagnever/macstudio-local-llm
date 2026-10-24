# Etapa 0 — plano de memória do Splash a 1M (`k2a`, 1000000 tokens) (2026-10-24)

O `k2a` sobe com `--max-context 1000000` em 4 s depois do load. Dados do `/status` (`memory_plan`) e do boot log:

| item | valor |
|---|---|
| YaRN | ligado, fator 3.8147 sobre 262144 nativos |
| KV | int8 simétrico, 12 camadas de atenção, 2 cabeças de KV de 256, página de 32 tokens = 423936 bytes (~13.2 KB por token) |
| pesos do alvo | 97.70 GB (PLE 27465 MiB e experts 62402 MiB em memória) |
| pesos do draft | 0.52 GB |
| orçamento rígido | 113.14 GB (recomendado pelo Metal: 115.45 GB, menos 2.31 GB de margem) |
| KV residente | 9.39 GB, ou seja, **860153 tokens** cabem na memória |
| acima disso | o KV vai para o cache em SSD (até 32 GiB de arquivos temporários) |

Leituras:
- A 512K, todo o KV int8 fica na memória.
- A 1M, os últimos ~140K tokens ficam no SSD. A velocidade a 1M mede também esse caminho.
- Com `--kv-format bf16`, cada token ocupa o dobro. O limite residente cai para ~430K tokens, e então o `k2ab` a 512K já usa o SSD. A varredura do Task 2 mede esse custo.
