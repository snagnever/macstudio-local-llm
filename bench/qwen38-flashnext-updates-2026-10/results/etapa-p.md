# Etapa P — `--ple-gpu` (não medida: o servidor recusa a flag nesta máquina)

**Decisão: o `--ple-gpu` não vira perfil.** No M4 Max 128 GB, com o pack `iQ-MLX-4.7bpw` e a config
diária, o mlx-serve 26.10.1 aceita a flag mas mantém o gather do PLE na CPU. O braço n2p roda igual ao n2,
então não há A/B a medir.

Linha do boot log do n2p a 32K (os logs não entram no git):

```
[qwen4] ple gather: cpu (low_memory: weights 67.9 GB + table 29.8 GB + headroom 16 GB vs working set 107.5 GB, max buffer 80.6 GB)
```

O n2 sem a flag escreve `ple gather: cpu (--ple-gpu keeps the 29.8 GB table resident for the GPU gather)`.

## Por que não forçar

- A soma pedida é 113.7 GB. O working set do Metal é 107.5 GB. Faltam ~6 GB.
- Não verifiquei de onde vem o `headroom 16 GB`. Se for o prefix cache de 16 GB, baixá-lo para ≤ 10 GB
  admitiria a tabela. Isso muda uma segunda variável e piora o reuso a 128K.
- Subir o `iogpu.wired_limit_mb` pede `sudo` e tira a margem do macOS.
- O n2 já chega a 111.6 GB de wired a 128K. Com mais ~30 GB residentes, o braço passa da RAM física.
- O `--help` do 26.10.1 promete só "a few % faster prefill/decode". O critério do plano pede ≥ 5% a 128K.

## Execução

A rodada começou às 09:02 de 2026-10-07 e parou no boot do n2p a 32K, antes do primeiro request.
Nenhum registro foi gravado. A banda de 128K não rodou.
