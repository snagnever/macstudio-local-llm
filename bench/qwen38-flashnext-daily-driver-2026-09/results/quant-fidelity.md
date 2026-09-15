# Fidelidade publicada dos 3 packs Flash-Next MLX (não medido no rig)

| pack | bpw efetivo | disco | PPL Δ% publicado | KLD publicado | referência (bf16?) | fonte (URL + data) |
|---|---|---|---|---|---|---|
| ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit | 4.85 (calculado) | 107.3 GB | card não publica | card não publica | — | https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit/raw/main/README.md, 2026-09-13 |
| Jundot/Qwen3.8-Flash-Next-oQ4e-mtp | 5.97 (calculado) | 132.2 GB | card não publica | card não publica | — | https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp/raw/main/README.md, 2026-09-13 |
| Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed | 5.43 (calculado) | 120.2 GB | card não publica | card não publica | — | https://huggingface.co/Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed/raw/main/README.md, 2026-09-13 |

Notas:

- Nenhum dos três cards publica PPL, KLD ou um bpw efetivo agregado — só
  detalham a política de bits por tipo de tensor (ex.: "experts 4-bit,
  atenção 8-bit"), sem uma comparação numérica contra bf16/fp16. Por isso
  as colunas PPL/KLD/referência ficam "card não publica".
- bpw efetivo aqui é sempre **calculado** = tamanho em disco (bytes) × 8 /
  177e9 parâmetros, medido com `du -sk` sobre o diretório de cache local de
  cada pack (`~/.cache/local-llms/qwen3.8-prefix-cache/`), não um valor do
  autor do quant.
- O disco do ddalcu inclui a tabela n-gram de 32 GB (armazenada à parte,
  `ngram_table.bin`, 4-bit); o do Youssofal inclui os 32 GB do
  `ngram-table.safetensors` sidecar; o do Jundot (oQ) não documenta a
  tabela n-gram separadamente no card.

**Publicado pelo autor do quant, não medido no rig. Não entra no ranking.
Contexto: seção "Fidelidade por bpw" em `bench/qwen38-flash-next/references.md`.**
