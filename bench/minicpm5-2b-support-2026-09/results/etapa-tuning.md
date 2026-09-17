# Tuning do s1 — n-gram, saída guiada e KV (2026-09-16/17)

Testa as recomendações dos docs do `mlx-optiq` para o papel de suporte do
MiniCPM5-2B-OptiQ-4bit. Plano: [`plan-tuning.md`](../plan-tuning.md). Script:
`scripts/run-s1-tuning.sh`. 1 rep por ponto.

## 1. n-gram speculative (`--ngram-draft 16`) — ganho forte

| workload (~400 tok) | sem ngram | com ngram | ganho |
|---|---:|---:|---:|
| genérico (título/commit/classificação) | 169,4 tok/s | **216,5 tok/s** | **+28%** |
| copy-heavy (reescrever citando a entrada) | 163,1 tok/s | **713,1 tok/s** | **+337%** |

Config: `optiq serve --model <s1> --ngram-draft 16` (default era 0). Bate o critério
(≥20%) já no genérico; no caso que copia o input — reescrita, citação, tool call nomeando
arquivo — é 4,4×. **Habilitar por padrão.**

## 2. `guided_choice` na classificação — piorou

| passe | acerto |
|---|---:|
| livre (Etapa 3) | 4/5 |
| `guided_choice ["pergunta","pedido","informação"]` | **3/5** |

O guided consertou `intent-03` (`informação` → `pedido`) mas quebrou `intent-01` e
`intent-05`, que são **perguntas** e saíram como `informação`/`pedido`. A confusão
pergunta↔pedido é do modelo, e restringir o conjunto de saída não a resolve.
**Hipótese refutada — não usar.** (Se a classificação importar, é caso de few-shot no prompt,
não de constraint.)

## 3. KV misto (`--kv-config`, plano do quant) — sem ganho claro

| banda | fp16 | `--kv-config` |
|---|---|---|
| 8K | TTFT 3,95 s / 131,1 tok/s | 4,47 s / 164,1 tok/s |
| 32K | TTFT 23,05 s / 118,8 tok/s | 29,44 s / 96,1 tok/s |

n=1–4, direções opostas. Sem ganho consistente. Some com o já medido (uniforme 8-bit piorou o
prefill a 126K em +47%). **Manter fp16** no papel de turno curto; o KV do suporte é ~17 MB.

## 4. Efeito no driver (B@32K, 1 rep)

| arranjo | `T_turno` | decode do driver | wired |
|---|---:|---:|---:|
| B + s1 (fp16, 3 reps) | 15,45 s | 38,4 | 101,0 GB |
| B + s1 controle (3 reps) | 15,60 s | 38,6 | 99,6 GB |
| **B + s1 com ngram** (1 rep) | **15,0 s** | 40,4 | 91,9 GB |

O n-gram acelera o **suporte** sem mexer no `T_turno` do driver (dentro da variância).
Efeito no driver ≈ nulo.

## Configuração recomendada do s1 (papel de suporte, ≤32K)

```bash
optiq serve --model <s1> --host 0.0.0.0 --port 11235 \
  --max-concurrent 2 --max-context 32768 \
  --ngram-draft 16 --idle-timeout 600
```
- Requests: `:no-think`, `temperature=0.7`, `top_p=0.95`.
- KV: **fp16** (default).
- Não usar `guided_choice` para classificação.

## Conclusão

O único ajuste que paga é o **`--ngram-draft 16`**: +28% no uso típico e +337% quando a saída
copia o input — e não piora o driver. `guided_choice` e o KV misto não se sustentaram. A
decisão da campanha (não adotar como suporte residente sob carga contínua) não muda; se
adotado no perfil estreito, use o n-gram.

## Correção de harness

`run_load` do `run-s1-tuning.sh` fazia backup entre duas chamadas no mesmo arquivo (perdeu o
bucket de 8K para os `.bak`); corrigido passando a nomear 8K/32K em arquivos separados. Os
dados de 8K foram recuperados dos `.bak` para `etapa-tuning-kv-*-8k.jsonl`.

Dados: `results/etapa-tuning-{base,ng}-{generic,copy}.jsonl`, `etapa-tuning-guided.jsonl`,
`etapa-tuning-kv-{fp16,kvcfg}-{8k,32k}.jsonl`, `B-32768-t1.0-ng.jsonl`.
