# Backlog: modelos uncensored para testar

Candidatos abliterated/uncensored a avaliar depois. Ainda não agendados.
Fonte: refresh HF + r/LocalLLaMA em 2026-09-12.

## Candidatos

### 1. Qwen3.8-Flash-Next-Uncensored — build MLX-Serve 4-bit

- **Repo:** https://huggingface.co/ARC4NUM/Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit
- **Base:** Qwen3.8-Flash-Next, MoE ~125B armazenados / ~6B ativos.
- **Tamanho:** ~75 GB (pack ~107 GB).
- **Runtime:** exige `mlx-serve` v26.8.11-pre-release.1 ou mais novo (primeiro
  com `qwen4_exp`). Rig roda 26.9.1; confirmar antes.
- **Recursos:** inclui vision tower e cabeça MTP (`--mtp` opt-in).
- **Método:** remoção da direção de recusa (recusa ~94% → ~0-2%).
- **Números de terceiros:** 55.7 tok/s serial, 60.3 tok/s com MTP, ~68 GB
  residentes.
- **Cabe só no rig M4 Max 128 GB.** Não cabe no MacBook M5 Pro 24 GB.

### 2. orcarouter — 27B denso uncensored

- **Coleção:** https://huggingface.co/orcarouter
- **Por que:** vencedor da comparação de 8 variantes do Qwen3.8-27B
  (167 GPU-horas, r/LocalLLaMA), HarmBench ASR 82.2%. Único card verificado
  como honesto (4 de 4 claims). Melhor unlock de copyright do painel (39%).
  Método: Arditi single-direction na camada 38. Mantém vision.
- **Alternativa mais próxima do base:** `apostate` (ASR 78.7%, KL mais baixo
  0.0439), mas sem vision, sem MTP, FP16.
- **Evitar:** `obliteratus` (edição agressiva demais, ~45% das respostas não
  fecham o bloco de raciocínio, "ficou burro").
- Relatório completo citado na thread: `abliterlitics.dev/models/qwen38-27b`.

## Ponto de atenção comum

Abliteração agressiva quebra o loop de "thinking": até 45% das respostas não
fecham o `<think>` dentro do orçamento de tokens. Medir isso ao avaliar, não só
a taxa de recusa.

## Status

- [ ] Testar ARC4NUM Flash-Next MLX-Serve 4-bit no rig M4 Max 128 GB.
- [ ] Testar orcarouter 27B (qualidade + vision).
- [ ] Confirmar se os repos carregam sem erro no `mlx-serve` 26.9.1.
