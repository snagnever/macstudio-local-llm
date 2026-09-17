# Etapa 2 — concorrência: penalidade de `T_turno` do driver (2026-09-15/16)

Quanto o modelo de suporte tira do driver quando gera ao mesmo tempo. A métrica de
decisão é o `T_turno` do driver (TTFT do `tool_turn` + 512 / mediana do decode quente),
medido na mesma fixture (`audit_retrieval`), perfil do vendor (`temperature=1.0`,
`top_p=0.95`, `top_k=20`, reasoning xhigh, limite 4096), 3 repetições, driver reiniciado
antes de cada arranjo para o `cold` ser frio.

## Arranjos

| # | composição | modelo | tamanho |
|---|---|---|---|
| A | só o driver | Qwen3.8-Flash-Next ddalcu mixed-4/8 | — |
| B | driver + s1 | MiniCPM5-2B-**OptiQ-4bit** | 1,8 GB |
| C | driver + s2 | MiniCPM5-2B-8bit | 2,5 GB |
| D | driver + s3 | gemma-4-E4B-it-MLX-8bit | 8,97 GB |

O suporte gera turnos curtos em laço (`scripts/support-load.py`, ~400 tokens de
entrada, `:no-think`) durante todo o probe.

## 32K

| arranjo | `T_turno` | Δ vs A | decode | prefill | cold TTFT | wired | swap Δ | gate (≤15%) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A | 10,82 s | — | 57,4 tok/s | 737,7 | 37,0 s | 97,4 GB | 0 | passa |
| B (+s1) contínuo | 15,45 s | **+42,8%** | 38,4 | 663,0 | 41,2 s | 101,0 GB | 0 | **falha** |
| B gap 1 s | 12,16 s | +12,4% | 50,7 | — | — | 96,1 GB | 0 | passa |
| B gap 3 s | 10,89 s | +0,6% | 57,5 | — | — | 95,3 GB | 0 | passa |
| B gap 5 s | 11,32 s | +4,6% | 55,4 | — | — | 96,9 GB | −0,02 | passa |
| C (+s2) | 16,02 s | **+48,1%** | 37,1 | 643,3 | 42,4 s | 101,7 GB | 0 | **falha** |
| D (+s3) | 17,91 s | **+65,5%** | 32,8 | 634,9 | 43,0 s | 106,9 GB | −0,02 | **falha** |

O custo é **contenção de banda de memória no decode do driver**, não os bytes do 2B:
decodificar cai de 57,4 para 32–38 tok/s. O `tool_turn` (TTFT ~1,9 s) quase não muda;
quem estoura o gate é o decode.

## 128K

| arranjo | `T_turno` | Δ vs A | decode | cold TTFT | wired | swap Δ | gate |
|---|---:|---:|---:|---:|---:|---:|---|
| A | 12,58 s | — | 48,6 tok/s | 178,1 s | 107,6 GB | 0 | passa |
| B (+s1) | 16,49 s | **+31,1%** | 36,5 | 203,5 s | 111,2 GB | −0,01 | **falha** |
| C (+s2) | — | — | — | 477,3 s | 100,2 GB | **+1,0** | **falha** |
| D (+s3) | 18,71 s | **+48,7%** | 31,6 | 203,6 s | **117,3 GB** | −0,05 | **falha** |

A 128K o driver já opera a ~107,6 GB wired. O **s1 cabe** (13/13, wired 111,2 GB, sem erro de
contexto, swap Δ −0,01), mas paga **+31,1%**. O que não cabe é o **s2**: o driver **reduz o
contexto para ~87K** ao alocar, o probe leva HTTP 400
`"Prompt exceeds maximum context length: 86123 requested, 1024 available"` e swap +1,0 GB.
O **s3** sobreviveu com wired **117,3 GB** e +48,7%. (Numa primeira tentativa o B@128K caiu
com `Connection refused`; o retry limpo completou — é intermitência de alocação na borda,
não teto do s1.)

Contexto maior: medido em `etapa2-maior.md` — o **s1 cabe** a 256K (+49,7%) e a 512K (+34,6%),
sem erro de contexto; o perfil 512k usa KV 8-bit.

## Controle (dúvida do agente paralelo)

Havia um segundo agente rodando a mesma campanha no rig; o controle re-mediu A e B @32K
numa janela sem ele:

| 32K | `T_turno` | decode | Δ |
|---|---:|---:|---:|
| A principal | 10,82 s | 57,4 | — |
| A controle | 10,70 s | 58,0 | — |
| B principal | 15,45 s | 38,4 | +42,8% |
| B controle | 15,60 s | 38,6 | **+45,8%** |

A perda reproduz → **não era o agente paralelo**, é efeito físico. Os números também
batem com o baseline arquivado da campanha do driver (11,03 s @32K / 12,35 s @128K).

## Leitura

1. Com o suporte **saturado**, nenhum quant paga: +43% (s1) a +66% (s3) a 32K.
2. Com turnos curtos **intermitentes**, a 32K o s1 fica dentro do gate: +12,4% a gap 1 s,
   +0,6% a gap 3 s. O ponto de virada entre 100% e ~50% de duty cycle.
3. O s1 **cabe em toda a faixa (32K–512K)**; o que reprova é a perda de velocidade (+31% a
   +50% sob carga contínua). Quem não cabe é o s2 a 128K (contexto reduzido a ~87K).

## Limites

- Uma fixture (`audit_retrieval`); cargas de código/chat podem mudar o decode com MTP.
- `swap` é medido como delta dentro da rodada (o rig carrega ~0,95 GB de swap de base,
  constante).
- O duty cycle foi varrido só a 32K e só no s1; gaps a 128K não foram medidos porque a
  banda já falha por memória.
