# Etapa 8 — GGUF ggml-org IQ4_NL + MTP Q8_0: llama.cpp b11609 (2026-10-14)

## Smoke GGUF 32K

| braço | contexto | T_turno | cold TTFT | warm TTFT | hit | decode | MTP acc | wired peak | swap Δ | HTTP errs | needles |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| g0 | 32K | 16.5 s | 51.8 s | 2.20 s | 0.96/0.96 | 36.0 | — | 78.2 GB | 0.00 GB | 0 | 5/5 |
| g1 | 32K | 12.2 s | 54.3 s | 2.40 s | 0.96/0.96 | 52.1 | — | 82.4 GB | 0.00 GB | 0 | 5/5 |

- g0 @ 32K: livre mínimo 6.66 GB; gates passa; alertas —
- g1 @ 32K: livre mínimo 0.07 GB; gates passa; alertas —

```
g0 36.0
g1 52.1
SMOKE: fail
```

## Veredito

- **Smoke falhou.** O decode quente do `g1` (b11609 com `--spec-type draft-mtp`, `--spec-draft-n-max 3`) é 52.1 tok/s a 32K, abaixo do gate de 70. O `g0` (sem MTP) faz 36.0 tok/s. A Task 8 termina aqui: as bandas de 32K e 128K contra o `w1` não rodaram.
- O braço `g1m` (GGUF no mlx-serve) saiu antes do smoke: o llama.cpp embutido (b11429) não tem o fix de `mul_mat_id` do b11569 nem o fix do PLE do b11600 (`research/qwen38-flashnext-updates-20261014.md`).
- Os pesos (99 GB) ficaram no rig até 2026-10-16, quando o usuário os apagou.
- O pin `052beea` mede os mesmos bytes do HEAD `0a61d2b` (`gguf-pin-receipt.md`).

## Leitura

- A aceitação do draft MTP no log do llama.cpp fica entre 0.54 e 0.64 (comprimento médio 2.6–2.9 com n-max 3). A MTP dá +45% de decode sobre o `g0`, mas parte de uma base baixa.
- O `g0` repete os ~36 tok/s sem MTP que o plano cita do `references.md`. O plano dá 84.6 tok/s de decode para o `w1` no mlx-serve, 1.6× o `g1`.
- O `g1` chega a 0.07 GB de memória livre mínima já a 32K (wired 82.4 GB), contra 6.66 GB do `g0`. O wired sobe 4.2 GB com a cabeça MTP. A 128K o `g1` ficaria sem folga.
- O `T_turno` do `g1` (12.2 s, 1 rep) é 1.5× o do `n2` a 32K na Task 1 (7.9 s). O GGUF não é candidato a driver neste rig.
