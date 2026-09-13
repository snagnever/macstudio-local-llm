# Qwen3.8-Flash-Next — driver diário mais responsivo (M4 Max 128 GB, 2026-09-13)

**Veredito: o incumbente — ddalcu mixed-4/8 no mlx-serve 26.9.2 — é o driver diário mais responsivo.** `T_turno`
(mediana de 3 reps) de **11.03 s a 32K** e **12.35 s a 128K**, 18% à frente do segundo colocado (oQ4e no oMLX
0.7.0.dev2: 13.48 / 15.03 s). A vantagem vem do TTFT: a 128K o turno quente responde em 2.1 s contra 4.8 s e o
primeiro turno em 178 s contra 259 s. O decode empata em ~50 tok/s.

## Candidatos e método

| # | Quant | Runtime | Resultado |
|---|---|---|---|
| c1 | ddalcu mixed-4/8 (`ef5b919`) | mlx-serve 26.9.2 | **vencedor** nas duas bandas |
| c2 | Jundot oQ4e-mtp (`2615fc0`) | oMLX 0.6.4 | fora na Etapa B: dominado pelo c3 nos mesmos pesos |
| c3 | Jundot oQ4e-mtp (`2615fc0`) | oMLX 0.7.0.dev2 | 2º: +18% de `T_turno` |
| c4 | Youssofal MTPLX Optimized-Speed (`6bc2f6e`) | MTPLX 2.11.2 | eliminado: recusa 128K e 256K (HTTP 507) |

Métrica de decisão: `T_turno` = TTFT do `tool_turn` + 512 / mediana do decode dos cenários quentes servidos
(identical, append, tool_turn). Perfil do vendor (`temperature=1.0`, `top_p=0.95`, `top_k=20`, reasoning xhigh,
limite 4096 tokens). Fixture `audit_retrieval`, needles a 10/50/90%.

Gates eliminatórios a 32K e 128K: hit ≥ 0.90 em append e tool_turn; needles corretas (truncado não conta como
falha); swap delta ≤ 0.5 GB; zero erro de servidor. Wired acima de 102 GB é alerta, não gate: o mlx-serve pina
KV e prefix cache em wired por design e opera a 106–108 GB sem swap.

## Veredito por `T_turno`

Etapa B (mediana de 3 reps, valores crus):

| cand | `T_turno` 32K | `T_turno` 128K | TTFT quente tool_turn 32K / 128K | cold TTFT 32K / 128K | decode quente 128K (faixa) | corretos |
|---|---:|---:|---|---|---|---|
| **c1 mlx-serve** | **11.03 s** | **12.35 s** | 1.9 / 2.1 s | 37.0 / 178.1 s | 49.7 (45.7–54.6) | 25/26 (1 truncado) |
| c3 oMLX dev2 | 13.48 s | 15.03 s | 3.9 / 4.8 s | 52.3 / 259.4 s | 49.9 (46.2–51.2) | 24/26 (2 truncados) |

TTFT e cache hit ficaram idênticos nas 3 reps (≤ 0.5%); o decode variou até ±12%. Nenhum miss intermitente de cache.

Etapa A (1 rep) para as quatro bandas:

| cand | 8K ¹ | 32K | 128K | 256K |
|---|---:|---:|---:|---:|
| c1 mlx-serve | 10.1 s | 10.8 s | 11.3 s | 14.2 s |
| c3 oMLX dev2 | 11.7 s | 12.6 s | 15.3 s | 16.7 s |
| c4 MTPLX | ² | 10.6 s | recusa 507 | recusa 507 |
| c2 oMLX 0.6.4 | 16.3 s | 17.1 s | 22.7 s | 28.8 s |

¹ Smoke da Etapa 0 (cold, identical, tool_turn). ² A 8K a telemetria de cache do MTPLX foi incoerente
(hit 1.00 no cold; tool_turn 75 s).

## Teto de contexto

A sonda rodou sem `sudo` (`iogpu.wired_limit_mb` = 0). O c1 alcança 524288 tokens e o follow-up cabe: cold TTFT
844.6 s, decode 42.6 tok/s, identical 0.6 s com hit 1.00, wired 104.3 GB, memória livre mínima 0.01 GB, swap 0.

| cand | teto | mecanismo |
|---|---|---|
| c1 | **512K com follow-up** (na borda de memória) | YaRN 2.0 via `--config-overrides`, KV 8-bit |
| c2, c3 | 262K | oMLX não tem YaRN (o rope do `qwen4_exp` ignora o tipo) |
| c4 | 114.688 tokens no default | fit do memory plan do MTPLX 2.11.2 |

## Achados

1. **O c4 não é drop-in a 128K neste Mac.** O MTPLX 2.11.2 calcula o fit como (engine budget 96 GiB − pesos
   77.3 GiB − 4 GiB) / custo por token, incluindo o transiente de prefill QSA, e recusa o prompt de 131K com
   HTTP 507 antes de entrar em swap. O session bank não entra no fit. Com `MTPLX_MEMORY_LIMIT_BYTES=102G` o fit
   cobre 128K: cold/identical/append servem, mas o cold leva 494 s e `middle_mutation`/`tool_turn` falham por
   alocação (`allocation_failure_shed`). A 32K o c4 tem o maior decode (~70 tok/s).
2. **A dev2 não estava bloqueada.** O offload de PLE funciona com `qwen4_ple_ssd_offload: true` no
   `model_settings.json` (log `PLE mode … : mmap`). Nos mesmos pesos, a dev2 decodifica +35% a 32K e dobra a
   0.6.4 a 256K (cold 578 contra 1187 s; decode 47.5 contra 23.6).
3. **A MTP do MTPLX 2.11.2 não é lossy** pelas needles: 5/5 com MTP e 1.8× de decode; sem MTP, 4/5 (um truncado).
4. **O c1 faz multi-turno a 256K sem `sudo`.** O follow-up foi servido com hit 1.00 (identical 0.6 s,
   tool_turn 2.6 s); wired 108.5 GB, swap 0.
5. **O TTFT é determinístico entre reps; o decode não.** c1 @32K: cold 37.0 s nas três reps, tool_turn 1.9 s nas
   três; decode quente de 52.1 a 63.1.

## Diagnósticos a temp 0 (32K)

- c2 × c3: mesma resposta final nos 5 cenários; o reasoning diverge 2–15% (deriva numérica de kernel).
- c4 MTP ligada × desligada: 5/5 × 4/5; as diferenças de hash são texto diferente com resposta certa ou
  truncamento do caminho sem MTP. Critério usado: needles, não identidade de tokens.

## Defeitos do harness encontrados e corrigidos durante a campanha

| Defeito | Efeito se não corrigido |
|---|---|
| `/metrics` do mlx-serve sem contador de MTP | aceitação da MTP nula (agora lida do log `[spec-stats]`) |
| reset de conexão no `/metrics` | benchmark abortado antes do 1º cenário |
| oMLX serve 14 modelos; probe pegava `data[0]` | c2 medido no modelo errado |
| overlay de YaRN reusado com fator errado; `.cache` do overlay apontando para o pack | rótulo errado; escrita no pack original |
| recusa HTTP (507/400) sem registro | JSONL vazio e servidor órfão |
| identidade e hash do cenário anterior em registro de erro | registro de recusa com identidade errada |
| erro entregue no stream sem `error` | lido como resposta errada |
| medianas com registros que falharam | c4 com cold TTFT de 0.2 s "melhor" no dashboard |
| hit arredondado antes do gate; truncado contado como erro HTTP | gate aprovando 0.86; c1 reprovado por engano |
| saída em append ao re-rodar | sessões misturadas num resultado |

## Limites

- Qualidade de agente não foi medida (Terminal-Bench fica fora do escopo).
- `greedy_tokens_hash` cobre só o texto final; o lossless foi julgado pelas needles.
- Uma fixture (`audit_retrieval`); cargas de código ou chat podem mudar o decode com MTP.
- 256K e 512K com 1 rep.

Arquivos: `etapa0-smoke.md`, `diag-temp0.md`, `etapa-a.md`, `quant-fidelity.md`, `c3-dev2-ple-config.md`, `etapa-b.md`, `sonda-512k.md`.
