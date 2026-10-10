# MiniCPM5-2B como modelo de suporte — veredito (2026-09-16)

**Decisão: não adotar como suporte residente do driver diário.** O 2B absorve bem as
tarefas curtas (formato e idioma passam), mas a perda de decode no driver é grande quando a
carga não é esparsa — e é **velocidade, não memória**: o s1 **cabe em toda a faixa testada
(32K a 512K)**, sem erro de contexto e sem swap crescente; só que custa +31% a +50% de
`T_turno` sob carga contínua. Quem não coube a 128K foi o s2 (contexto reduzido a ~87K).
Fica registrado como viável apenas num cenário estreito: **contexto ≤32K e turnos curtos
intermitentes (≥1 s entre eles)**.

## Os gates do plano

| gate | resultado |
|---|---|
| 1. Perda do `T_turno` ≤15% (32K e 128K) | **falha** na carga contínua: +42,8% (s1) a +65,5% (s3) a 32K; +31% a +50% a 128K/256K/512K. **Passa a 32K** com gaps ≥1 s (+12,4% a gap 1 s, +0,6% a gap 3 s) |
| 2. Swap = 0 e memória livre mínima >2 GB | o s1 **cabe em toda a faixa** (32K–512K, 5/5 servidos, swap Δ ≈0); `free` fica baixo (aviso no macOS). A 128K o s2 fez swap +1,0 GB e o driver reduziu o contexto para ~87K |
| 3. Formato e idioma ≥90% | **passa**: 30/30 e 30/30 |
| 4. Ganho real de latência | o s1 responde um turno curto em ~0,46 s a 400 tokens, contra ~11 s do driver — o ganho de fila existe |

## Por banda

- **32K:** o s1 saturado custa +42,8%; a cadência realista (gap ≥1 s) volta para ≤12,4%.
  O s3 (gemma-e4b) é o pior (+65,5%) e o s2 fica no meio (+48,1%).
- **128K/256K/512K:** o driver opera a 107–117 GB wired. O **s1 cabe em todas** (5-13/13
  servidos, sem erro de contexto, swap ≈0), pagando **+31,1%** (128K), **+49,7%** (256K) e
  **+34,6%** (512K) sob carga contínua. O s2 a 128K fez o driver **reduzir o contexto para
  ~87K** (HTTP 400) e swap +1,0 GB; o s3 a 128K completou com +48,7% a 117,3 GB. Detalhe em
  `etapa2-maior.md`.

## Mecanismo

A perda não vem dos bytes lidos pelo 2B, e sim da **contenda por banda de memória no
decode do driver**: o decode cai de 57,4 para 32–38 tok/s a 32K. O TTFT do `tool_turn`
(~1,9 s) quase não muda; é o decode que define o `T_turno`.

## Qualidade (s1)

Formato 100%, idioma 100%, conteúdo ~93%. Defeitos: uma classificação trocada
(informação vs pedido), um argumento de tool traduzido para inglês, dois inteiros mandados
como string. Ver `etapa3-s1.md`.

## Confiabilidade do resultado

- Baseline reproduz o arquivado: 10,82 s @32K (arquivado 11,03) e 12,58 s @128K (12,35).
- O controle numa janela sem o agente paralelo reproduziu a perda (+45,8% vs +42,8%) →
  o efeito é físico, não contaminação.
- Higiene: `cold` exige reiniciar o driver (o prefix-cache persiste); o gate de `free` do
  macOS engana (usa `free`+`inactive`).

## Se for para adotar

Só no perfil estreito: s1 (`mlx-community/MiniCPM5-2B-OptiQ-4bit`, `optiq serve`, porta
11235), **contexto de suporte ≤32K**, cadência ≥1 s. Em contexto maior o s1 ainda cabe
(verificado até 512K), mas a perda de `T_turno` sob carga contínua (+31% a +50%) não
recomenda mantê-lo residente junto do driver.

## Arquivos

- Plano: `plan.md`
- Runtime/parser: `etapa0-smoke.md`
- Solo: `etapa1-solo.md`
- Concorrência (matriz, controle, duty cycle): `etapa2.md`
- Contexto maior (256K/512K): `etapa2-maior.md`
- Qualidade: `etapa3-s1.md`
- Scripts: `scripts/` (`serve-support.sh`, `support-load.py`, `run-arrangement.sh`,
  `run-etapa2.sh`, `run-control-32k.sh`, `run-s1-followup.sh`, `verdict_etapa2.py`,
  `quality-run.py`, `report_quality.py`)

## Próximos passos (revisão de 2026-10-09)

A premissa da campanha era que o driver não faz batched decode no MoE, então turnos curtos
entram na fila dele. Dois fatos novos mudam essa premissa e o baseline:

- **O oMLX 0.7.0 (2026-09-30) faz decode concorrente no Flash-Next.** O 0.7.0.dev4 trouxe o
  Lightning MTP multi-request: com 2 requests, o Flash-Next-oQ4e-mtp passa de 71,7 para
  96,3 tok/s agregados (+34%, M3 Ultra 512 GB). O 0.7.0 adicionou kernels fundidos de MoE,
  DeltaNet e atenção para decode e verify do MTP. Fontes:
  [release 0.7.0](https://github.com/jundot/omlx/releases/tag/v0.7.0),
  [notas do 0.7.0.dev4](https://newreleases.io/project/github/jundot/omlx/release/v0.7.0.dev4).
- **O driver mudou.** O n2 (mlx-serve 26.10.1 + iQ-MLX-4.7bpw) faz 8,2 s a 32K e 8,8 s a
  128K, contra 10,8 s e 12,6 s do driver medido aqui. As perdas de `T_turno` desta campanha
  são relativas ao driver antigo. Ver
  [engine-updates-2026-10](../../engine-updates-2026-10/results/summary.md).

Em batched decode, as linhas do mesmo step leem os pesos uma vez. Um turno curto no próprio
driver não paga a contenda de banda que o s1 causa como processo separado. O ganho por linha
é menor no MoE que no denso (o mlxcel mediu 1,55× a B=4 no qwen3-30b-a3b, contra ~3,2× no
denso: [mlxcel#1616](https://github.com/lablup/mlxcel/issues/1616)).

| # | passo | métrica e gate | custo |
|---|---|---|---|
| 1 | **Turnos curtos no próprio driver, oMLX 0.7.0 (braço o1).** `support-load.py` aponta para o driver, com `max_concurrent_requests` ≥2, a 32K e 128K. Mesma fixture e cenários do `cache_probe.py`. | `T_turno` do driver sob carga, contra o o1 solo (10,1 / 12,1 s) e contra o n2 solo (8,2 / 8,8 s). Latência do turno curto contra os ~0,46 s do s1. Adotar se o `T_turno` sob carga ficar ≤ n2 solo × 1,15. | ~1 h |
| 2 | **Refazer o arranjo B a 32K com o n2 + s1.** `run-arrangement.sh` com o launcher atual do driver. | Perda de `T_turno` do n2 com o s1 em carga contínua e com gap 1 s. Confirma ou revisa o NO-GO contra o driver atual. | ~30 min |
| 3 | **Ler o changelog do mlx-serve 26.10.x** para batched decode no MoE do Flash-Next. | Se existir, repetir o passo 1 no n2. Se não existir, o card do driver continua com "parallel requests queue on one slot". | ~10 min |
| 4 | **Checar se o vllm-metal 0.30.0 carrega o Flash-Next** (`qwen4_exp`). O blog cita a família Qwen3.8 com paged KV e batching packed, sem nomear o Flash-Next. MTP batched no Metal só existe para Gemma 4. | Smoke 8K. Se carregar, vira braço do passo 1. Fontes: [blog do vllm-metal](https://vllm.ai/blog/2026-09-22-vllm-metal-v0-28-0). | ~30 min |

Sem novidade no MiniCPM5-2B depois do lançamento (2026-09-07). Os passos 1 e 3 decidem se o
slot de suporte ainda faz sentido. Se o driver absorver os turnos curtos com perda ≤15%, o
slot sai do plano.
