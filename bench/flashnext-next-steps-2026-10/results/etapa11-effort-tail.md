# Etapa 11 — instrução de effort no fim do prompt (`w1t`) (2026-10-17, mlx-serve 26.10.1)

Runbook: [plan-effort-needles.md](../plan-effort-needles.md), Task 11. `w1t` = Swift 1.5 `13839b7` servido de um overlay de hardlinks com o template [swift15-effort-tail.jinja](../../../fixes/qwen3.8-flash-next/swift15-effort-tail.jinja) (MD5 `fe68e582…`). `w1` = o mesmo pack com o template oficial; os dados do `w1` vêm da Task 3 (3d, 3e e 3f, 2026-10-13/14). O LCB do `w1` está no avaliador corrigido ([e3d-lcb-regrade.md](e3d-lcb-regrade.md)); o do `w1t` saiu do bench2 `2403125`, que já tem a correção.

## 3e — troca de effort a 128K

| probe | braço | effort | n | resultado |
|---|---|---|---:|---|
| 3e | w1 | low | 2 | switch TTFT 166.87 s hit 0.00 |
| 3e | w1 | medium | 2 | switch TTFT 167.13 s hit 0.00 |
| 3e | w1 | xhigh | 12 | prime TTFT 83.48 s hit 0.50; control TTFT 1.34 s hit 1.00; back TTFT 0.88 s hit 1.00 |
| 3e | w1t | low | 2 | switch TTFT 0.81 s hit 1.00 |
| 3e | w1t | medium | 2 | switch TTFT 5.73 s hit 0.97 |
| 3e | w1t | xhigh | 12 | prime TTFT 83.69 s hit 0.50; control TTFT 3.04 s hit 0.98; back TTFT 0.31 s hit 1.00 |

## Obediência ao effort (GPQA + LCB, 100 questões, 2 rodadas)

| effort | questões | reasoning `w1t` / `w1` (IC 90%) | dentro de ×1.25? |
|---|---:|---|---|
| xhigh | 100 | ×1.04 (0.97–1.11) | sim |
| medium (A/A) | 100 | ×0.98 (0.92–1.03) | sim |
| low | 100 | ×0.90 (0.86–0.94) | sim |

| braço | medium / xhigh (IC 90%) | low / xhigh (IC 90%) |
|---|---|---|
| w1 | ×0.62 (0.54–0.72) | ×0.45 (0.38–0.53) |
| w1t | ×0.59 (0.50–0.69) | ×0.39 (0.33–0.46) |

OBEDIENCE: pass (xhigh e low dentro de ×0.80–×1.25; suítes gpqa, livecodebench; rodadas r1, r2)

## Acerto e custo (GPQA 50 + LCB 50, seed 42)

| effort | rodada | GPQA `w1` → `w1t` | LCB `w1` → `w1t` | tempo GPQA+LCB (s) | tokens | truncadas |
| --- | --- | --- | --- | --- | --- | --- |
| xhigh | r1 | 42 → 42 | 47 → 48 | 8711 → 10197 | 662K → 739K | 1 → 3 |
| xhigh | r2 | 43 → 43 | 47 → 46 | 10144 → 9919 | 731K → 757K | 3 → 4 |
| medium | r1 | 40 → 41 | 41 → 44 | 2588 → 2438 | 217K → 206K | 0 → 0 |
| medium | r2 | 43 → 42 | 40 → 41 | 2462 → 3024 | 207K → 233K | 0 → 0 |
| low | r1 | 39 → 38 | 42 → 40 | 1575 → 1481 | 128K → 117K | 0 → 0 |
| low | r2 | 36 → 38 | 41 → 41 | 1505 → 1508 | 123K → 120K | 0 → 0 |

Somas das 2 rodadas (margem G1 × 2 = 6): GPQA `xhigh` 85 → 85, `medium` 83 → 83, `low` 75 → 76; LCB `xhigh` 94 → 94, `medium` 81 → 85, `low` 83 → 81.

## 3f — tool-calling em `xhigh` (1 rodada)

| suíte | métrica | w1-r1 | w1t-r1 |
| --- | --- | ---: | ---: |
| jdhodges | acertos | 36/40 | 37/40 |
| jdhodges | truncadas | 0 | 0 |
| jdhodges | tempo mediano (s) | 2.2 | 3.6 |
| jdhodges | tempo total (s) | 134.4 | 187.6 |
| jdhodges | tokens medianos | 110.5 | 107.5 |
| jdhodges | reasoning mediano (chars) | 155.5 | 149.5 |
| veerman | acertos | 10/12 | 10/12 |
| veerman | truncadas | 0 | 0 |
| veerman | tempo mediano (s) | 3.1 | 4.0 |
| veerman | tempo total (s) | 65.2 | 57.3 |
| veerman | tokens medianos | 174.0 | 191.5 |
| veerman | reasoning mediano (chars) | 399.5 | 387.5 |

| gate | resultado |
| --- | --- |
| G1:jdhodges | passa |
| G1:veerman | passa |

| suíte | turno 1 mediano `w1` → `w1t` | prompt mediano | requisições com prefixo reaproveitado (boot log) |
| --- | --- | --- | --- |
| jdhodges | 2.21 s → 3.61 s | 1227 → 1231 tokens | `w1` 53/55, `w1t` 0/55 (as duas suítes juntas) |
| veerman | 3.07 s → 4.01 s | 615 → 619 tokens | |

## Veredito

As quatro regras do plano passam: troca de effort com hit 0.97–1.00 (TTFT 0.8–5.7 s contra 167 s); obediência dentro de ×0.80–×1.25 em `xhigh` (×1.04) e `low` (×0.90); GPQA e LCB dentro da margem nos três efforts; jdhodges e Veerman dentro da margem. **Mesmo assim, o template não vira default:** a investigação do 3f achou uma regressão que as regras não cobriam. Com o `w1t`, o mlx-serve deixa de reaproveitar o system prompt entre conversas curtas, e cada requisição de ~600–1200 tokens paga o prefill inteiro (+0.9 a +1.4 s no turno 1). O template fica como perfil opcional para sessões longas com troca de effort. Não alterei o launcher diário; o perfil `FLASHNEXT_TEMPLATE=efftail` fica para quando a regressão tiver solução.

## Leitura

- **Por que o cache curto quebra.** No modelo híbrido (GDN), o mlx-serve só restaura um prefixo num checkpoint de estado SSM. No `w1`, o log mostra `inherited N checkpoints (<= 1207 tokens) from a shared prefix` e `reused 1198/1227 tokens`: existe um checkpoint perto do fim do trecho comum (system + tools). No `w1t`, todas as requisições do 3f dizem `hybrid miss (no checkpoint ≤ 555 of 618 …); cold prefill`. O trecho comum termina no mesmo lugar, mas não há checkpoint ali. Inferência (não confirmada no código do mlx-serve): o servidor grava um checkpoint no começo da última mensagem do prompt. No `w1`, essa mensagem é a pergunta do usuário, logo depois do trecho comum. No `w1t`, a última mensagem é o bloco de effort, depois da pergunta, e o checkpoint fica fora do trecho comum.
- **Em prompts longos o problema não aparece.** No 3e (128K), o servidor guardou 16 checkpoints espaçados ao longo do prompt, e a troca de effort reaproveitou 122880 de ~126K tokens. O custo do `w1t` numa sessão longa no mesmo effort é o turno de controle: 3.0 s contra 1.3 s, porque o servidor reprocessa o trecho desde o último checkpoint antes do bloco de effort.
- **Obediência.** O modelo segue a instrução no fim do prompt. No `w1t`, `low` gasta ×0.39 do reasoning do `xhigh` e `medium` ×0.59; no `w1`, ×0.45 e ×0.62. O `medium` (prompt idêntico nos dois braços) dá ×0.98, então o piso de ruído é ~±5% com 2 rodadas. O `low` do `w1t` fica 10% mais curto que o do `w1` (IC 0.86–0.94), fora do ruído mas dentro da margem.
- **Custo por tarefa.** Sem as truncadas, os tempos e tokens ficam dentro do ruído do A/A. O `xhigh` do `w1t` truncou 7 respostas em 65536 tokens nas duas rodadas, contra 4 do `w1`; cada truncada soma ~1000 s.
- **Próximos testes possíveis** (não rodados): `--ssm-checkpoint-stride` menor no `w1t`, para criar checkpoints dentro de prompts curtos (o `--help` avisa que cada checkpoint força uma fronteira de chunk e reprocessa os pesos dos experts); ou um template com o bloco de effort antes da última pergunta do usuário, que mantém o checkpoint depois do trecho comum, mas na troca de pergunta reprocessa a pergunta anterior e as respostas de tool dela.
