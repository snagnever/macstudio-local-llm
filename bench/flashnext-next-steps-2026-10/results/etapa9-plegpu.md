# Etapa 9 — --ple-gpu com prefix cache de 8 GB (2026-10-15, mlx-serve 26.10.1)

```
[qwen4] ple gather: cpu (low_memory: weights 68.2 GB + table 29.8 GB + headroom 16 GB vs working set 107.5 GB, max buffer 80.6 GB)
```

## Veredito

**Recusado de novo com prefix cache de 8 GB.** O mlx-serve 26.10.1 manteve o gather da tabela PLE na CPU no smoke de 32K do `w1p8` (`--ple-gpu`, `--prefix-cache-mem 8192`). As bandas de 32K e 128K não rodaram. O `--ple-gpu` não vira perfil opcional.

## Leitura

- A hipótese do plano era que o `headroom 16 GB` do log viesse do prefix cache de 16 GB do driver. Não vem: com `--prefix-cache-mem 8192` (o boot log confirma o orçamento de 8192 MB idle), o headroom continua 16 GB. É uma reserva fixa do runtime.
- A conta do runtime: 68.2 GB de pesos + 29.8 GB da tabela + 16 GB de headroom = 114 GB, acima do working set de 107.5 GB do Metal. Com o Swift 1.5 neste rig de 128 GB, o `--ple-gpu` só ligaria com uma tabela ou pesos ~6.5 GB menores ou com um headroom configurável.
- O smoke serviu os 3 cenários sem erro com o gather na CPU (`results/w1p8-32768-t1.0-smoke9.jsonl`).
