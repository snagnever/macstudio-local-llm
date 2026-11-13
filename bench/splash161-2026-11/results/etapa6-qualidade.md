# Task 6: Qualidade (2026-11-12)

**A 1.6.1 passa. A bateria soma 300 de 336, contra 293 e 302 do `k2f` (1.5.0) nas passadas W1 e W2 da campanha de pesos. O G1 passa nas 6 suítes contra as duas passadas. As tool calls ficam em 20/20 no `fp0` e 16/20 no `fp1`, contra 20 e 11 do `k2f`. O contexto longo acerta 16 de 16.**

Braço `k2h` (Splash 1.6.1, PLE `auto`), effort `xhigh`, sampling da campanha. Fila `logs/chain-t6.sh`, das 08:58 às 13:04 (relógio do rig):

| passo | contexto | horário |
|---|---:|---|
| bateria (`run-battery.sh k2h v161`) | 262144 | 08:58–12:11 (3h13; `k2f` W1: 2h53) |
| longctx, bandas 131072 e 262144 num servidor de 262144 | 262144 | 12:23–12:36 |
| tool calls (`toolcall-probe.sh`, 20 sessões por perfil) | 65536 | 12:48–13:04 |

## Bateria

Fonte: `summarize_ab.py --ab-dir <links> --base k2f-w1|k2f-w2 --cand k2h`, em [ab/k2f-w1-vs-k2h.md](ab/k2f-w1-vs-k2h.md) e [ab/k2f-w2-vs-k2h.md](ab/k2f-w2-vs-k2h.md). As referências do `k2f` vêm de `flashnext-weights-2026-11/results/w1/t1/k2f/` e `w2/t1/k2f-r2/`, com os mesmos pesos na 1.5.0.

| suíte | `k2f` W1 | `k2f` W2 | `k2h` | margem do G1 | G1 contra W1 / W2 |
|---|---:|---:|---:|---:|---|
| humaneval /164 | 144 | 144 | 145 | 3 | passa / passa |
| gpqa /50 | 42 | 44 | 43 | 3 | passa / passa |
| livecodebench /50 | 46 | 47 | 46 | 3 | passa / passa |
| if /20 | 19 | 19 | 19 | 2 | passa / passa |
| jdhodges /40 | 35 | 38 | 38 | 2 | passa / passa |
| veerman /12 | 7 | 10 | 9 | 1 | passa / passa |
| **total /336** | 293 | 302 | **300** | | |

Em todas as suítes, o `k2h` fica entre as duas passadas da 1.5.0 ou a no máximo uma questão da melhor delas. No humaneval, ele fica uma questão acima das duas. A diferença entre W1 e W2 do mesmo braço (9 questões) é maior que a diferença entre o `k2h` e qualquer passada.

### Tokens e tempo

| suíte | métrica | `k2f` W1 | `k2f` W2 | `k2h` |
|---|---|---:|---:|---:|
| gpqa | tokens medianos | 2297.5 | 1430.5 | 1279.5 |
| gpqa | tempo mediano | 21.5 s | 14.1 s | 13.1 s |
| gpqa | truncadas | 2 | 2 | 1 |
| livecodebench | tokens medianos | 1376.0 | 1558.5 | 1426.5 |
| livecodebench | tempo mediano | 13.5 s | 16.3 s | 14.0 s |
| humaneval | truncadas | 0 | 0 | 1 |

- **Tokens:** o `k2h` fica dentro da faixa das duas passadas do `k2f` no livecodebench. No gpqa, fica 11% abaixo da W2. As duas passadas da 1.5.0 já diferem 38% entre si no gpqa.
- **G2:** o `summarize_ab.py` marca G2 falha no livecodebench contra as duas passadas e no gpqa contra a W2. O G2 pede tempo mediano ≤ 0.8 × a base. Ele mede uma redução de thinking entre pesos, e a regra desta task decide só pelo G1. Fica como observação.

## Tool calls

Sessões em que todos os turnos acertam, de 20. `fp0` usa `frequency_penalty` 0, e `fp1` usa 1. A referência é o `k2f` da W1, a única passada com tool calls.

| perfil | `k2f` W1 | `k2h` | turnos certos `k2f` / `k2h` | turnos truncados `k2f` / `k2h` |
|---|---:|---:|---|---|
| `fp0` | 20 | **20** | 100/100 / 100/100 | 0 / 0 |
| `fp1` | 11 | **16** | 67/82 / 88/94 | 6 / 2 |

A regra pede ≥ `k2f` − 1, ou seja ≥ 19 no `fp0` e ≥ 10 no `fp1`. **Passa.** Os turnos que faltam no `fp1` (82 e 94 de 100) vêm das sessões que param no primeiro turno errado ou truncado; o `tool_loop.py` encerra a sessão nesse turno.

## Contexto longo

`longctx_probe.py`, 8 perguntas por banda: 3 `lookup`, 3 `sum` e 2 `hop`.

| banda | prompt | acertos |
|---|---:|---:|
| 131072 | 118442–118449 tokens | 8/8 |
| 262144 | 245211–245218 tokens | 8/8 |

**Passa.** A regra pede 8/8.

## Conclusão

Para a regra "Trocar o launcher", a Task 6 **passa**: G1 contra as duas passadas, tool calls ≥ `k2f` − 1 nos dois perfis e longctx 8/8 nas duas bandas. Nenhuma suíte falhou no G1, então não houve repetição. A Task 7 roda.

## Desvios

- **Decisão do usuário:** às 12:45 (relógio do rig), o usuário escolheu manter só tool calls e longctx. A bateria e o longctx já tinham terminado, então nada foi parado, e a bateria fica no relatório.
- **Arquivo da bateria:** o `run-battery.sh` procura `results/k2h-262144-t1.0-q-v161-k2h.jsonl` para anexar memória e não acha o arquivo. A splash16 tem o mesmo traceback. Os JSONL por questão ficam em `v161/t1/k2h/`.
- **Arquivos vazios:** `k2h-262144-t1.0-lc-q.jsonl` e `k2h-65536-t1.0-toolcall-v161.jsonl` ficam vazios, porque o `run-candidate.sh` exige o arquivo. Os dados ficam em `longctx/` e `toolcall/`.

Fontes: `v161/t1/k2h/<suíte>.jsonl`, [longctx/k2h-262144-131072.jsonl](longctx/k2h-262144-131072.jsonl), [longctx/k2h-262144-262144.jsonl](longctx/k2h-262144-262144.jsonl), [toolcall/k2h-fp0-v161.jsonl](toolcall/k2h-fp0-v161.jsonl), [toolcall/k2h-fp1-v161.jsonl](toolcall/k2h-fp1-v161.jsonl). Referências: [etapaW1-fila.md](../../flashnext-weights-2026-11/results/etapaW1-fila.md) e [etapaW2-segunda-passada.md](../../flashnext-weights-2026-11/results/etapaW2-segunda-passada.md).
