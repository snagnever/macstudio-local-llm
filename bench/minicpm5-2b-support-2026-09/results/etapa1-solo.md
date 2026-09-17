# Etapa 1 — solo do suporte (2026-09-15)

Teto de velocidade de cada quant sozinho, sem concorrência. O driver do dia
estava no ar mas idle (não gera durante a medição), então o número é de fato do
2B; a memória wired do driver não interfere no decode.

Método: `scripts/support-load.py` com `:no-think`, `temperature=0.7`,
`top_p=0.95`, respostas até 256 tokens. N ~30–70 turnos por banda, mediana.

| cand | prompt medido | TTFT med | decode med | total med | completion med |
|---|---|---:|---:|---:|---:|
| s1 OptiQ-4bit | ~0,4K | 0,240 s | 159,7 tok/s | 0,46 s | 36 |
| s1 OptiQ-4bit | ~1K | 0,447 s | 153,9 tok/s | 0,69 s | 38 |
| s1 OptiQ-4bit | ~8K | 3,866 s | 117,8 tok/s | 4,01 s | 18 |
| s2 8-bit | ~0,4K | 0,248 s | 130,8 tok/s | 0,44 s | 26 |
| s2 8-bit | ~1K | 0,457 s | 128,5 tok/s | 0,62 s | 22 |
| s2 8-bit | ~8K | 3,874 s | 108,1 tok/s | 4,04 s | 18 |

## Leitura

- **Decode: s1 ~18% à frente do s2** em todas as bandas (160 vs 131 a 400
  tokens), como previsto — a quant mista lê menos bytes por token apesar do 5,34
  bpw. A diferença não é a que decide a campanha, mas confirma que o s1 é o
  candidato de velocidade.
- **TTFT idêntico entre os dois** (0,24 / 0,45 / 3,87 s): o prefill é dominado
  por compute, não por leitura de pesos. A 8K o prefill custa ~3,9 s (~2,1K
  tok/s), o gargalo de um turno longo no suporte.
- **O decode cai ~27% do 400 para o 8K** (160→118), efeito de KV/atenção com o
  cache longo — o mesmo padrão do driver. O papel do suporte (prompts de
  200–800 tokens) fica na banda rápida.
- Completions curtas (mediana 18–38 tokens) confirmam que as tarefas de suporte
  são turnos curtos, não geração longa.

## Limite

Não mede a perda do driver sob concorrência — isso é a Etapa 2. E o número foi
tomado com o driver residente (idle), então serve de teto, não de solo absoluto.

Dados: `results/etapa1-s1-solo.jsonl`, `results/etapa1-s2-solo.jsonl`.
