# Diagnósticos a temp 0 — 32K (2026-09-13)

Dois controles fora do ranking: lossless c2 vs c3 (mesmo quant oQ4e, oMLX 0.6.4 vs 0.7.0.dev2) e
MTP ligada vs desligada no c4 (MTPLX 2.11.2). `temperature=0`, 1 rep, 5 cenários, 32768.

**Limite do método:** o `greedy_tokens_hash` do `cache_probe.py` cobre só o texto final
(`result.text`), não o reasoning. O hash detecta resposta divergente, não raciocínio divergente.

## c2 vs c3 — mesma resposta, reasoning diferente

| cenário | resposta igual | reasoning chars c2 / c3 | correção c2 / c3 |
|---|---|---|---|
| cold | sim | 3318 / 3354 | ok / ok |
| identical | sim | 2720 / 3122 | ok / ok |
| append | sim | 5442 / 4664 | ok / ok |
| middle_mutation | sim | 4999 / 5761 | ok / ok |
| tool_turn | sim | 2912 / 2771 | ok / ok |

A dev2 chega à mesma resposta correta nos 5 cenários. O reasoning diverge de 2% a 15%: kernels
diferentes seguem outro caminho greedy. É deriva numérica, não perda de correção.

Velocidade no mesmo quant (decode, tok/s): c2 44–47, c3 60–63 (+35%). Cold TTFT: 58.3 s / 53.6 s.
Cache hit idêntico nos dois (identical 0.975, append 0.94, middle 0.45, tool_turn 0.94).

## c4 — MTP ligada vs desligada (`--generation-mode ar`)

| cenário | resposta igual | reasoning chars on / off | correção on / off | decode on / off |
|---|---|---|---|---:|
| cold | sim | 3122 / 3256 | ok / ok | 66.9 / 37.6 |
| identical | sim | 3122 / 3256 | ok / ok | 68.7 / 38.4 |
| append | não | 7183 / 2746 | ok / ok | 67.6 / 37.9 |
| middle_mutation | não | 7210 / 11103 | ok / **truncado** | 69.9 / 37.6 |
| tool_turn | sim | 3769 / 2400 | ok / ok | 69.0 / 38.2 |

- A MTP dá **1.8× de decode** a 32K.
- Com a MTP ligada, o c4 acerta 5/5. Sem a MTP, acerta 4/5; o `middle_mutation` passou de 4096 tokens
  de reasoning e a resposta saiu vazia.
- As duas diferenças de hash não são erro da MTP: no `append` as duas respostas estão corretas com
  texto diferente; no `middle_mutation` quem falhou foi o caminho sem MTP.

**Veredito:** sem evidência de MTP lossy no MTPLX 2.11.2. O caso lossy do 2.11.1 errava 15/15 cenários
com a MTP ligada. O c4 segue candidato.

Critério usado: correção das needles, não identidade de tokens. A identidade de tokens a temp 0 não
vale nem entre dois runtimes com os mesmos pesos (c2 vs c3), então não serve de régua para a MTP.

Dados: `c2-32768-t0.jsonl`, `c3-32768-t0.jsonl`, `c4-32768-t0.jsonl`, `c4-32768-t0-nomtp.jsonl`.
