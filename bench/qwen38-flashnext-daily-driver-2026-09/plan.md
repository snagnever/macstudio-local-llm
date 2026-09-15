# 2026-09-13 — Qwen3.8-Flash-Next: driver diário responsivo — quants × runtimes

> **Objetivo:** achar o driver de uso diário **mais responsivo** para o Flash-Next no M4 Max
> 128 GB. Responsividade = TTFT quente, reuso de cache e prefill (o que o usuário sente por turno),
> com decode como desempate. Comparar 3 runtimes sobre os quants MTP-capazes já em disco.
> **Fora de escopo:** Terminal-Bench (qualidade de agente, corrida à parte), ds4 (engine bloqueado,
> [../qwen38-updates-2026-09/results/p4b-ds4-blocked.md](../qwen38-updates-2026-09/results/p4b-ds4-blocked.md)),
> concorrência multi-request (o MoE não faz batched decode — um stream só), GGUF/llama.cpp (sem MTP,
> o path menos responsivo; fica como referência de footprint, não candidato).
>
> Contexto do modelo e das builds: [../qwen38-flash-next/references.md](../qwen38-flash-next/references.md).
> Lições herdadas da campanha da densa 27B: [../qwen3.8-prefix-cache/plan.md](../qwen3.8-prefix-cache/plan.md).
> **Status (2026-09-13): CAMPANHA FECHADA.** Veredito em [results/summary.md](results/summary.md).
> Driver mais responsivo: **ddalcu mixed-4/8 @ mlx-serve 26.9.2** (incumbente), `T_turno` 11.03 s @32K /
> 12.35 s @128K (mediana de 3 reps), 18% à frente do oQ4e @ oMLX 0.7.0.dev2. Dashboard:
> [reports/qwen38-flashnext-driver.html](../../reports/qwen38-flashnext-driver.html).
>
> Plano de execução (tasks, scripts, testes, checkpoints):
> [docs/superpowers/plans/2026-09-13-qwen38-flashnext-daily-driver.md](../../docs/superpowers/plans/2026-09-13-qwen38-flashnext-daily-driver.md).

## O que já está fechado (não re-medir em 3×)

Velocidade, memória e cache do incumbente estão em
[../qwen38-updates-2026-09/results/flashnext-stacks-summary.md](../qwen38-updates-2026-09/results/flashnext-stacks-summary.md):
mlx-serve 26.9.2 + ddalcu é o driver recomendado, decode 67/58/57 tok/s a 32K/128K/262K, teto
prático 512K. Esta campanha compara os candidatos na mesma fixture, com o foco deslocado para
responsividade, e sonda se cada um alcança 512K. **1M fica fora** (decisão de 13/09): no incumbente
é one-shot cold (34.7 tok/s, follow-up recusado) ou multi-turno a ~5 tok/s com `turbo4` — nenhum dos
dois é uso diário.

## Versões da stack (web, 13/09/2026) — nada a baixar

| Runtime | Última | No rig | Nota |
|---|---|---|---|
| mlx-serve | 26.9.2 (09/09) | sim | atual; ganhos **não** gated a M5 |
| oMLX | 0.7.0.dev2 (~11/09) | venv isolado | dev; prefill mais rápido anunciado **para M5** — a validar no M4 |
| oMLX | 0.6.4 (estável) | sim | baseline do runtime oMLX |
| MTPLX | 2.11.2 (06/09) | sim | release de correção M1-M4; a rota verify de flash-decoding é gated a M5 |

O MTPLX **não tem** variante Optimized-Quality para o Flash-Next (só Optimized-Speed e Bare-Speed
no HF). Optimized-Quality existe só para a densa 27B. Os 4 pesos candidatos já estão em disco em
`~/.cache/local-llms/qwen3.8-prefix-cache/`.

## Os 4 candidatos

| # | Quant (SHA) | Runtime | Estado |
|---|---|---|---|
| 1 | ddalcu mixed-4/8 (`ef5b919`) | mlx-serve 26.9.2 | incumbente |
| 2 | Jundot oQ4e-mtp (`2615fc0`) | oMLX 0.6.4 | baseline oMLX |
| 3 | Jundot oQ4e-mtp (`2615fc0`) | oMLX 0.7.0.dev2 | dev — item novo |
| 4 | Youssofal MTPLX Optimized-Speed (`6bc2f6e`) | MTPLX 2.11.2 | nunca medido no rig |

Os itens 2 e 3 isolam **só o runtime** (mesmo quant oQ4e). É a regra de
[[isolate-the-variable-when-measuring]]. Todos re-rodam na mesma fixture e sessão; não reuso número
arquivado de outra fixture.

## Protocolo

Harness [cache_probe.py](../qwen3.8-prefix-cache/scripts/cache_probe.py). Base HTTP com sufixo `/v1`
(sem ele a tokenização falha com `content is required`). ID real via `/v1/models`.

### Por que 1-shot fecha TTFT, prefill e cache

Os dados do P1 (medidos a temp 0) mostram que TTFT, prefill e cache hit são determinísticos entre
reps (`cold` @32K: TTFT 37.3/37.3/37.3 s, prefill 732/732/732; hit igual nas 3 reps). Só o decode
varia: ±4% @32K, até ±12% @128K. Sob o perfil do vendor a variância do decode cresce; TTFT, prefill
e hit continuam determinísticos, porque não dependem da amostragem. Uma rep basta para as métricas primárias. As reps 2–3 servem
para o decode (desempate) e para pegar **miss intermitente de cache** (MTPLX 27B `tool_turn`:
5.8/5.7/18.8 s, hit 0.96/0.96/0.87 — 1 miss em 3). Um miss intermitente é resultado, não ruído.

### Três etapas

- **Etapa 0 — smoke a 8K (dia 1).** Os 4 candidatos, `cold/identical/tool_turn`, 1 rep. Objetivo:
  provar que cada um carrega e responde (a dev2 depende do offload; o pack MTPLX de 112 GB nunca
  rodou aqui), e medir o custo fixo por turno (page-in do n-gram de ~32 GB, warmup da MTP).
  Custa minutos por candidato. Candidato que não carrega sai antes de qualquer banda cara.
- **Etapa A — triagem 1-shot.** Sobreviventes, bandas 8K/32K/128K/256K, 1 rep. 8K/32K/128K com os 5
  cenários; 256K só `cold/identical/tool_turn` (o `middle_mutation` a 256K é re-prefill cheio de
  380–1185 s e não informa responsividade; `append` ≈ `tool_turn` em cache). Mais a sonda de
  capacidade a 512K. Produz o ranking e aplica os gates.
- **Etapa B — veredito.** 3 reps a **32K** para todos que passaram nos gates; 3 reps a **128K** só
  para os 2 finalistas por `T_turno`. As reps 2–3 mantêm `cold` (é o primer do cache) e pulam
  `middle_mutation`.

### Ordem de execução

Rodar por **banda**, não por candidato: os 4 a 32K, depois os 4 a 128K, depois 256K. A comparação
de cada banda fecha na mesma sessão e no mesmo estado térmico ([[runtime-gains-stale-baselines]]).
Custo: mais restarts de servidor (~2–3 min cada); aceito.

### Higiene entre candidatos e bandas

- **`cold` tem que ser frio.** A rodada 1 do P1 foi descartada porque o disco de prefix-cache
  sobreviveu ao restart e o `cold` acertou o cache. Antes de cada `cold`, limpar `~/.mlx-serve/kv-cache`,
  o `--paged-ssd-cache-dir` do oMLX e o `--ssd-session-cache-dir` do MTPLX. Registrar a limpeza no log.
- Esperar memória livre ≥ 82 GB antes de subir o próximo servidor (as páginas mmap demoram a
  voltar; `wait_mem_free` do driver P1). Esperar GPU < 50 °C entre bandas.
- Ordem dos cenários fixa: `cold → identical → append → middle_mutation → tool_turn`. Não rodar
  subconjunto sem `cold` (o 1º cenário não prima o cache e dá falso 0.00).

### Bandas e cenários

- Contextos: **8192, 32768, 131072, 262144**.
- Cenários: `cold`, `identical`, `append`, `middle_mutation`, `tool_turn` (256K: só os 3 citados).
- **Amostragem canônica = perfil do vendor:** `temperature=1.0`, `top_p=0.95`, `top_k=20`,
  reasoning xhigh, limite 4096 tokens. É o que o uso diário roda. A MTP aceita mais drafts a
  temp 0 (verificação greedy casa mais), então o decode a temp 0 é otimista — e o decode é o único
  termo do `T_turno` que a amostragem afeta. Mesma regra da densa: vendor é canônico, temp 0 é
  diagnóstico. **Consequência:** os números arquivados do Flash-Next (P1, stacks-summary, YaRN)
  foram medidos a temp 0 e não são comparáveis com esta campanha; por isso os 4 re-rodam aqui.
- Sob amostragem o tamanho do reasoning varia por rep, então o E2E vira ruído. O `T_turno` usa
  decode tok/s (taxa por token), que sofre menos; as 3 reps da Etapa B cobrem o resto.
- Correção: needles `{10, 50, 90}` — sinal de sanidade, não avaliação de qualidade de agente.
  `finish_reason=length` (o harness grava) conta como **truncado**, não como erro. A needle a
  `temperature=1.0` funcionou na densa (braço L 3/3); correção não exige temp 0.
- MTP on nos 4.
- **Diagnóstico a temp 0 (duas reps baratas a 32K, fora do ranking):**
  - **Lossless da dev2:** os itens 2 e 3 têm o mesmo quant. A temp 0 devem produzir os mesmos
    tokens de saída. Comparar o hash por cenário (a densa fez isso no Gate 8). Divergência =
    correção suspeita na dev2, mesmo com needle ok.
  - **Controle `--no-mtp` do item 4:** MTP on vs off a temp 0, dado o histórico de MTP lossy da
    linha MTPLX ([[mtplx-2111-mtp-lossy]]). Tokens diferentes entre on e off = MTP lossy.

### Sonda de capacidade (512K)

Separada das bandas diárias. Por candidato: `cold` one-shot (decode + needle) a **524288**, mais
`identical` para confirmar que o follow-up cabe; **uma tentativa**; recusa é dado, não erro. KV em
**kv-quant 8** (a config do teto no incumbente: decode 51, cache reusa, needle ok, wired 111 GB,
minFree 0.1 GB); `turbo4` não entra (decode −66% a 256K, ~5 tok/s a 1M). Registrar o teto por stack
e o estado de `iogpu.wired_limit_mb` (default 107.5 GB; `sudo sysctl iogpu.wired_limit_mb=124518`
sobe para ~119 GB — anotar quando um candidato depender dele). 1M não é medido nesta campanha.

**Pré-requisito por runtime:** o mlx-serve estende o rope via `--config-overrides` (YaRN; driver
[run-p1-mlxserve-extended.sh](../qwen38-updates-2026-09/scripts/run-p1-mlxserve-extended.sh)).
Como oMLX e MTPLX estendem além de 262K não está mapeado. Pesquisar antes da sonda; se um runtime
não expõe YaRN, o teto dele é 262K e isso é o dado.

### Telemetria por rodada

Prefill tok/s, cold TTFT, **warm TTFT** por cenário (`identical`, `append`, `tool_turn`), cache hit
por cenário, decode tok/s, `finish_reason`, aceitação da MTP, memória wired (pico), swap delta,
disk-spill, temperatura.

**Lacuna a fechar antes de medir:** o `cache_probe.py` grava `ram_peak_gb: null`; só o
`run-omlx.sh` amostra wired. Um sampler único (`vm_stat` "Pages wired down" + swap, a 5 s) para os
4 candidatos, anexado ao JSONL por `run_id`. Sem isso o gate de memória não fecha nos itens 1 e 4.

**Segunda lacuna: aceitação da MTP.** Nos JSONL do P1 (mlx-serve), `mtp_acceptance`,
`speculation_mode` e `accept_length` são `null` em todas as bandas. A 26.9.2 trouxe `--max-mtp-ctx`;
sem telemetria não dá para saber se a MTP está ativa a 256K/512K. Ler a aceitação do `/metrics` ou
do log de cada runtime e registrar o `--max-mtp-ctx` resolvido. Decode alto em contexto longo sem
MTP ativa é sinal de outra causa, e o `T_turno` precisa saber qual.

### Borda a 256K (registrar, não tratar como erro)

A 262144, a 2ª request sobre o contexto cheio pode ser recusada por memória (mlx-serve responde
HTTP 400; diagnóstico em [../qwen38-flash-next/references.md](../qwen38-flash-next/references.md)).
A needle do `cold` one-shot é o sinal principal ali.

## Config por candidato (armadilhas fixadas)

1. **ddalcu / mlx-serve 26.9.2** — `--mtp` mais prefix-cache **16GB/100GB/64** (o default de 2 GB
   não retém um prefixo de 128K e zera o reuso). Registrar também `--ssm-checkpoint-max` (checkpoint
   do estado DeltaNet; a config de 1M da comunidade usa 16 — pode afetar o reuso de `append` no
   híbrido) e o `--max-mtp-ctx` resolvido. Drivers:
   [../qwen38-updates-2026-09/scripts/run-p1-mlxserve-ab.sh](../qwen38-updates-2026-09/scripts/run-p1-mlxserve-ab.sh)
   e [run-p1-mlxserve-extended.sh](../qwen38-updates-2026-09/scripts/run-p1-mlxserve-extended.sh).
2. **oQ4e / oMLX 0.6.4** — setting `qwen4_ple_ssd_offload: true` na arm. Sem ele o oQ4e carrega
   99.6 GB residente e satura os 128 GB com swap.
3. **oQ4e / oMLX 0.7.0.dev2** — **pré-requisito:** achar como a 0.7 lê `qwen4_ple_ssd_offload` por
   modelo (settings/profile, não o arm-config da 0.6.x). O env `OMLX_QWEN4_PLE_MODE=mmap` é
   sobreposto e o PLE carrega residente (~98 GB), saturando a memória
   ([p4-item4](../qwen38-updates-2026-09/results/p4-item4-omlx-dev2-blocked.md)). Validar residente
   ~70 GB no smoke de 8K antes de medir. Confirmar **empiricamente** se o ganho de prefill
   (anunciado p/ M5) aparece no M4 — é o motivo de incluir a dev2.
4. **MTPLX Optimized-Speed / MTPLX 2.11.2** — não a 2.11.1 (MTP lossy a 32K). Fixar e registrar:
   - `--context-window` igual à banda;
   - o estado de `--ssd-session-cache` (o harness da densa usava `off`; o vendor usa `on`). Escolher
     `on` — é o que o usuário roda e é o caminho seguro de memória na linha 2.10+;
   - o cap do session-bank: a heurística auto (24G/sessão) quebrou o reuso a ≥128K na densa
     ([[mtplx-session-bank-cap]]). O KV do Flash-Next é pequeno (~3.6 GB a 128K), então o cap pode
     bastar. Registrar a linha `session-bank budget` do log; se `append` reusa e `tool_turn` dá
     0.00 no mesmo run, é cap — subir via `MTPLX_SESSION_BANK_*` e re-rodar;
   - o perfil e a depth do pack Flash-Next (`mtplx_runtime.json` do pack), não o `turbo --depth 3`
     herdado do 27B;
   - o n-gram do pack faz stream do SSD segundo as notas da 2.10 — não verificado na 2.11.2 no M4.
     O smoke de 8K responde.

## Critério de decisão (responsividade)

**Métrica de manchete por banda:** `T_turno = TTFT do tool_turn + 512 / mediana do decode dos
cenários quentes servidos (identical, append, tool_turn)` — o que o usuário espera num turno de
agente com resposta de 512 tokens. Incumbente hoje (a temp 0, referência apenas): 9.8 s @32K, 11.6 s
@128K.
**Primeiro turno:** cold TTFT.

Gates eliminatórios (herdados da densa, ajustados ao rig):

- Cache: hit ≥ 0.90 em `append` e `tool_turn` a 32K e 128K.
- Correção: needle 3/3 a 32K e 128K; truncado não conta como erro, mas fica na tabela.
- Memória: swap delta ≤ 0.5 GB.
- Zero HTTP 4xx/5xx nas bandas diárias. A recusa a 256K é dado, fora do gate.

Pico wired acima de 102 GB (5 GB abaixo do teto de 107.5) é alerta, não elimina: é o ponto de
operação normal do mlx-serve (KV + prefix cache de 16 GB fixados em wired) quando não há
crescimento de swap.

Entre os que passam, vence o menor `T_turno` a 32K e 128K. Decode só desempata. O teto de contexto
entra como capacidade, não como critério diário. Qualidade de agente não entra — depende do
Terminal-Bench, corrida à parte.

**Fidelidade do quant não é critério.** A compilação PPL/KLD dos quants GGUF/EXL3
([references.md, "Fidelidade por bpw"](../qwen38-flash-next/references.md)) mostra o joelho da curva
em ~4.0–4.3 bpw e uma parte plana acima disso. Os três quants MLX candidatos ficam na parte plana
(~4.5–5.5 bpw efetivos); a diferença esperada de fidelidade entre eles é de ~1–2 pp de PPL. Uma
needle errada na Etapa A é sintoma de runtime (MTP lossy, cache), não do quant.

## Etapa C — contexto longo com reps (adicionada em 14/09)

Motivo: a 256K a Etapa A tem 1 rep sem `append`, e a 512K a sonda não tem `tool_turn`, então as duas
bandas não têm `T_turno` comparável. A Etapa C não muda o veredito; ela dá `T_turno` a 256K e 512K.

- **c1, c3, c2 @ 262144:** `cold, identical, append, tool_turn` × 3 reps. Arquivo `<cand>-262144-t1.0-c.jsonl`.
- **c1 @ 524288:** YaRN 2.0 + KV 8-bit, `cold, identical, tool_turn` × 2 reps. Arquivo `c1-524288-t1.0-yarn2-c.jsonl`.
- **Fora:** c4 a 256K (HTTP 507 já registrado); c2/c3/c4 a 512K (oMLX sem YaRN; MTPLX recusa já a 128K).
- Ordem: c1 256K → c1 512K → c3 256K → c2 256K; o daily driver fica parado durante a etapa.
- No `consolidate_reports.py` o estágio `C` tem o mesmo peso da Etapa B: substitui a Etapa A e a sonda
  na mesma banda.

## Etapa U — variantes uncensored (adicionada em 14/09)

Pergunta: uma variante uncensored do Flash-Next serve como driver diário **sem perder responsividade**
nem capacidade? A variável isolada é o peso ([[isolate-the-variable-when-measuring]]): mesmo runtime,
mesmo layout de quant e mesmos flags do candidato de referência.

### Braços

| braço | pesos | runtime | referência | tamanho | método |
|---|---|---|---|---:|---|
| **u1** | `ARC4NUM/Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit` @ `9ebf999` | mlx-serve 26.9.2 | c1 | 107.3 GB | abliteration (orcarouter, BF16 `8336e61`) |
| u2 (opcional) | `latent-variable/Qwen3.8-Flash-Next-heretic-2-oQ4e-mtp` @ `65b0cd6` | oMLX 0.7.0.dev2 | c3 | 106.3 GB | Heretic 1.3 (card: KL 0.082, recusas 0/100) |

- **u1 é o braço principal.** O `config.json` do pack é idêntico ao do ddalcu (94 chaves, 0 diferenças):
  mixed 4/8, n-gram 4-bit mmap, cabeça MTP incluída. O `yomie4343/...-MLX-Serve-mixed-4-8bit` é um
  mirror byte a byte do mesmo pack (102/102 SHA-256); não baixar os dois.
- u2 roda só se u1 perder no gate de responsividade ou de correção. O MTPLX (`grant-ai/...-Abliterated-MTPLX-4bit`)
  fica fora: o runtime recusa 128K ([[mtplx-flashnext-128k-fit]]). GGUF fica fora: não roda nos stacks da campanha.
- O 27B denso (`OBLITERATUS/Qwen3.8-27B-OBLITERATED`) fica fora desta campanha: a densa 3.8-27B já é NO-GO
  ([[qwen38-27b-nogo-verdict]]).

### Hipóteses a medir

1. **Aceitação da MTP cai.** A abliteration edita o modelo principal, mas a cabeça MTP não foi re-treinada.
   Se a distribuição do principal muda, a MTP aceita menos drafts e o decode cai. Medir `mtp_acceptance`
   do log contra o c1 na mesma banda.
2. **Velocidade de prefill e cache não mudam** (mesmas shapes). Diferença acima do ruído é sinal de pack diferente.
3. **Crash de MTP no reload do cache.** O card da yomie4343 relata um crash de shape na quantização
   ao recarregar a MTP num engine antigo e publica um patch. Verificar se a 26.9.2 upstream já cobre
   isso: `stream_failures` e HTTP 5xx nas 3 reps contam como falha.

### Protocolo

- **Download após a Etapa C** (I/O de disco perturba o page-in do n-gram durante as runs). `df` antes:
  ≥ 150 GB livres por pack ([[check-disk-before-model-downloads]]). Pinar a revisão.
- `run-candidate.sh` ganha `u1` (e `u2`): cópia do case `c1` (`c3`) com outro `MODEL_DIR`/`MODEL_REV`.
- **Smoke 8K** (`cold/identical/tool_turn`, 1 rep): carrega, MTP ativa no log, needles ok.
- **32K e 128K × 3 reps**, mesmo protocolo da Etapa B. Arquivos `u1-<ctx>-t1.0-b.jsonl`.
- **Sonda de recusa (nova, `scripts/refusal_probe.py`):** 40 prompts legítimos que modelos alinhados
  costumam recusar, em 4 categorias de 10: segurança ofensiva em contexto autorizado (pentest, CTF),
  dose e interação de medicamentos, redução de danos, e ficção com tema adulto ou violento. Mais 10
  controles neutros. Perfil do vendor, 1 amostra por prompt, no c1 e no u1 em sequência no mesmo
  servidor de cada braço. Classificação: regex de recusa + revisão manual das divergências. Saída:
  `results/refusal-<cand>.jsonl`, só com o veredito e os primeiros 200 caracteres da resposta
  (a resposta completa não entra no repo).

### Critério

- **u1 vira driver alternativo** (não substitui o c1 por padrão) se: `T_turno` a 32K e 128K dentro de 5%
  do c1, aceitação da MTP ≥ c1 − 0.05, needles 3/3, zero falhas de stream/HTTP, e recusas nas 4
  categorias abaixo do c1.
- Qualidade de agente não entra no ranking (mesma regra do plano). Referência publicada, não medida:
  o card da yomie4343 dá 21/25 no uncensored contra 22/25 no original, 1 trial.
- Resultado em `results/etapa-u.md`; as páginas do Flash-Next ganham os braços u1/u2.

## Entregáveis

- `results/*.jsonl` — telemetria por candidato e banda (distilado, ≤1 MB por arquivo), com o
  sampler de memória anexado.
- `results/summary.md` — veredito **em prosa** (não uma tabela de gates gerada: o `summary.md` da
  densa marcou 13/15 braços como FAIL por telemetria ausente e ficou ilegível). Contém: tabela
  head-to-head por banda com `T_turno`, cold TTFT, warm TTFT, hit, decode, wired; célula de
  correção com três estados (`ok` / `truncado` / `falha`); tabela de teto de contexto; resultado
  do lossless 2 vs 3.
- `reports/qwen38-flashnext-driver.html` — dashboard self-contained sobre `charts-common.js`
  (modelo `MODELS + RESULTS`, ver [../../reports/README.md](../../reports/README.md)), não o
  `render_overview.py` da densa. Conteúdo: tabela head-to-head por banda; linhas de warm TTFT
  (`tool_turn`), cold TTFT e decode vs contexto; heatmap de cache hit cenário × candidato; barras de
  wired; tabela de teto a 512K; veredito em prosa espelhado do `summary.md`. O dashboard da densa
  não tinha warm TTFT por cenário — só `identical`, o melhor caso sintético.
- `results/quant-fidelity.md` — tabela dos 3 packs MLX (ddalcu mixed-4/8, Jundot oQ4e, MTPLX
  Optimized-Speed) com bpw efetivo, tamanho em disco, PPL/KLD **publicados no card HF** e a fonte.
  Mesmo método da compilação do Reddit, rotulado "publicado, não medido". Serve para situar os
  candidatos na curva de fidelidade; não entra no ranking.
- Publicação na branch `gh-pages`, ao lado do dashboard do 27B ([[qwen38-pages-site]]).
