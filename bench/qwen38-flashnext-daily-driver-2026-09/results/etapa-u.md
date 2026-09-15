# Etapa U — variante uncensored (2026-09-15)

Pergunta: uma variante uncensored do Flash-Next serve como driver diário sem perder responsividade
nem recusar de menos/menos? Variável isolada: mesmo runtime, mesmo layout de quant, mesmos flags do c1.

- **u1** = `ARC4NUM/Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit` @ `9ebf999`, mlx-serve 26.9.2.
  Abliteration do orcarouter sobre o BF16. O `config.json` é idêntico ao do ddalcu (c1): 94 chaves,
  0 diferenças. Só os pesos mudam.
- u2 (heretic-2 oQ4e) não rodou: só entraria se o u1 falhasse um gate de responsividade.

## Responsividade — u1 contra c1

| banda | `T_turno` c1 | `T_turno` u1 | tool TTFT c1/u1 | decode c1/u1 | aceitação MTP c1/u1 |
|---|---:|---:|---:|---:|---:|
| 32K | 11.03 s | 11.13 s | 1.87 / 1.87 s | 55.9 / 55.3 | 0.62 / 0.58 |
| 128K | 12.35 s | 12.46 s | 2.05 / 2.03 s | 49.7 / 49.1 | 0.50 / 0.58 |

- `T_turno` dentro de 1% nas duas bandas. Passa o gate de responsividade (limite 5%).
- Aceitação da MTP: 0.58 no u1, dentro do limite (c1 − 0.05). A 128K fica até acima do c1.
- Needles 3/3, zero falha de stream, zero HTTP 5xx. **A hipótese do crash de MTP no reload não
  reproduziu na 26.9.2 upstream** (o card da yomie4343 relatava o crash num engine antigo).

## Sonda de recusa — 40 prompts legítimos + 10 controles

| categoria | c1 | u1 |
|---|---:|---:|
| segurança autorizada | 0/10 | 0/10 |
| farmacologia factual | 0/10 | 0/10 |
| redução de danos | 0/10 | 0/10 |
| ficção adulta (não sexual) | 0/10 | 0/10 |
| controles neutros | 0/10 | 0/10 |
| **total** | **0/50** | **0/50** |

**O Flash-Next base já não recusa nenhum desses prompts legítimos.** Como o piso já é 0, a variante
uncensored não compra permissividade mensurável neste conjunto; o custo (aceitação da MTP um pouco
menor) não traz benefício aqui. O ganho de uma variante uncensored só apareceria em conteúdo de fato
recusado, que esta sonda legítima não inclui de propósito.

## Veredito

**u1 é um driver alternativo viável, não um upgrade.** Casa a responsividade do c1 e não recusa mais
nem menos nos prompts legítimos testados. Sem motivo para trocar o c1 pelo u1 como default. A sonda
grava só o veredito e 200 caracteres por resposta (`results/refusal-c1.jsonl`, `results/refusal-u1.jsonl`);
a resposta completa não entra no repo.

Dados: `u1-8192-t1.0.jsonl`, `u1-32768-t1.0-b.jsonl`, `u1-131072-t1.0-b.jsonl`, `refusal-c1.jsonl`,
`refusal-u1.jsonl`.
