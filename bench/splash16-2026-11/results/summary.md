# Splash 1.6.0 contra 1.5.0 — resumo da campanha (2026-11-06 a 08)

**O launcher do rig fica na 1.5.0.** A regra "Trocar o launcher" falha na Task 4: duas sessões de 256K ficam até 65% mais lentas na 1.6.0 pela espera por memória. Sob limite de memória, a 1.6.0 fica claramente melhor. Nas sessões do Claude Code, o tempo total e o TTFT ficam melhores, mas o tok/s mínimo fica pior, e o `k2c2a` a 128K teve um stall de mais de 60 s. A queda de decode da #644 não aconteceu no rig em nenhuma release.

Pesos: `k2` = Swift 1.5 `IQ4_XS` `0142554`. Sufixo `f` = 1.5.0, `g` = 1.6.0. Regras de decisão: [plan.md](../plan.md#regras-de-decisão).

## Respostas

| # | pergunta | veredito | resultado | fonte |
|---|---|---|---|---|
| 1 | Os packs carregam, e algum cliente quebra? | **passa** | C1 a C6 passam. A 1.6.0 não manda mais a API key ao proxy. O restart do engine volta em 24.3 s com 503 documentados. Na C7, as releases se comportam igual. | [etapa1](etapa1-contrato.md) |
| 2 | A 1.6.0 mantém o `T_turno` e o cache de um stream? | **passa** | Razão de 0.98 a 1.00 a 32K, 128K e 256K. 512K empata. 1M sobe sem `capacity_exhausted`, com razão 1.031 numa rep, só como observação. | [etapa2](etapa2-um-stream.md) |
| 3 | A queda da #644 acontece aqui, e a 1.6.0 a remove? | **sem regressão observada, sem veredito** | Pulada pelo usuário. Perfil `a` completo nas duas releases, estável (razão 1.00 e 0.92). | [etapa3](etapa3-envelhecimento.md) |
| 4 | O scheduler novo muda o custo da segunda sessão? | **falha** | `k2c2LL` a 256K: pior stream de 14.8 s na 1.5.0 e 24.4 s na 1.6.0, com `claim_wait` de até 30 s. As sessões do Claude Code a 131072 ficam mais rápidas na 1.6.0. | [etapa4](etapa4-concorrencia.md) |
| 5 | O ledger de memória tira os stalls sob limite? | **passa** | Com `--max-memory 64G`, o maior gap cai de 48.8 s para 2.5 s, e a 1.6.0 faz cerca de 30% mais requests. | [etapa5](etapa5-pressao.md) |
| 6 | A qualidade continua igual? | **sem regressão observada** | Pulada pelo usuário. G1 passa nas 5 suítes completas. | [etapa6](etapa6-qualidade.md) |
| 7 | Uma carga de agente de 4 h continua estável? | **sem regressão; fix sem prova** | Estável nas duas releases, com o pool no teto. A 1.6.0 conclui 43 pares contra 38, com warm TTFT p50 de 1.1 s contra cerca de 2.0 s. | [etapa7](etapa7-agente-4h.md) |

## Regra "Trocar o launcher"

| condição | resultado |
|---|---|
| Tasks 1, 2, 4, 5 e 6 passam | **não**: a Task 4 falha; a Task 6 só tem resultado parcial |
| Tasks 3 e 7 sem regressão | sim |
| **Decisão** | **o launcher fica na 1.5.0** |

O driver diário não muda nesta campanha. Se o usuário aceitar a regressão de duas sessões de 256K, a 1.6.0 traz ganhos em pressão de memória, em sessões de agente a 131072 e na proteção da API key. Antes de trocar, faltam medir na 1.6.0: o probe de tool calls, o `longctx_probe.py` e o veerman (Task 6), e os perfis `p` e `q` da Task 3. A campanha de pesos rodou só na 1.5.0.

A Task 4 também mostra uma queda de 2 vezes no decode somado do `k2c2LL` entre dias, sem causa encontrada. Por isso, os números absolutos comparados entre dias têm pouca força. A Task 7 rodou a 1.6.0 primeiro e a 1.5.0 depois, com um boot cada, então os 43 contra 38 pares podem ter efeito de ordem e de hora.

## Queda de decode (#644)

Nenhum perfil reproduziu a queda. Pelas regras do plano, o resultado é **fix sem prova**: a 1.5.0 e a 1.6.0 ficam estáveis em todos os perfis que rodaram.

| perfil | 1.5.0 fim / antes | 1.6.0 fim / antes | pool no teto |
|---|---:|---:|---|
| Task 3, perfil `a` | 1.00 | 0.92 | sim |
| Task 7, agente 4 h | 0.96 | 0.91 | sim |

Com o pool no teto, a 1.6.0 recusa de 6 a 18 vezes menos reservas de memória que a 1.5.0.

## O que não rodou

- Task 3: o perfil `p` na 1.5.0 a partir da rodada 5, o perfil `q` e a repetição em ordem invertida. O usuário pulou a task.
- Task 6: veerman, `longctx_probe.py` e o probe de tool calls. O usuário pulou a task, porque os pesos não mudam.
- Terminal-Bench 2.1 do `k2g`: fora da fila, como o plano prevê.

## Desvios do plano

- **Task 1:** a C7 ganhou um controle `C7b` e 3 reps por release, para separar o corte com tools de um limite geral de reuso.
- **Task 2:** a 1.5.0 a 1M rodou no mesmo dia como controle, porque a referência `k2a` era de outro dia e de outra release.
- **Task 4:** o `k2c2LL` e as sessões do Claude Code ganharam um controle da 1.5.0 no mesmo dia. A queda de decode da primeira leitura veio do dia, não da release.
- **Task 4:** as sessões do Claude Code passam apesar do tok/s mínimo pior. O mínimo vem de um único request por perfil, e o tempo das sessões e os percentis medem o uso real.
- **Task 5:** as respostas 400 `context_length_exceeded` da 1.6.0 vêm do gerador de carga e não contam como falha do servidor.
- **Task 7:** a tabela por hora foi calculada ad hoc dos JSONL, sem script em `scripts/`.
- **Ordem:** o usuário pôs a [flashnext-weights-2026-11](../../flashnext-weights-2026-11/plan.md) na fila depois da Task 7. Com o launcher na 1.5.0, os pesos rodam com o sufixo `f`.

## Relato upstream

O rascunho da regressão da Task 4 está em [etapa4-relato-upstream.md](etapa4-relato-upstream.md). Nada foi publicado.
