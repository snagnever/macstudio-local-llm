# Qwen3.8-27B denso: resumo e encerramento da campanha (14/10/2026)

## Veredito

- **O Splash 1.3.1 é o stack mais rápido medido para o Qwen3.8-27B denso neste rig.** O braço k27 (mlx-community 8bit + DFlash2) faz `T_turno` de **13.3 / 17.7 s** em `xhigh` a 32K / 128K e **10.4 / 15.9 s** em `medium`. O controle s27r (mlx-dspark 0.20.3 + DFlash2, mesmos pesos) faz 17.0 / 25.7 s em `xhigh`. Razão a 128K: **0.689**.
- **O NO-GO do 27B como driver agêntico continua.** O melhor número do 27B a 128K (k27 `medium`, 15.9 s) é **1.85×** o driver Flash-Next w1 (8.6 s). Em `xhigh`, 2.06×. A regra de reabertura pede ≤ 1.25× nas duas bandas. `P5_GO=0`.
- **O mlx-serve 26.10.2 com drafter DFlash2 não serve para o 27B a 128K.** O r27d decodifica 15.1 tok/s a 128K em `xhigh` e fica em 44.7 s de `T_turno` (1.739× o s27r).
- A campanha fechou depois da P3, a pedido do usuário. P7, P2, P4, P8, P6 e a bateria de qualidade não rodaram.

Página: [reports/qwen38-27b-stacks.html](../../../reports/qwen38-27b-stacks.html). Card do modelo: [docs/models/qwen3.8-27b.md](../../../docs/models/qwen3.8-27b.md). Plano: [plan.md](../plan.md). Spec: [research/qwen38-27b-next-steps-20261013.md](../../../research/qwen38-27b-next-steps-20261013.md).

Etapas: [etapa0-preflight.md](etapa0-preflight.md), [etapa1-smokes.md](etapa1-smokes.md), [etapa1-k27.md](etapa1-k27.md), [etapa3-r27d.md](etapa3-r27d.md), [gates.env](gates.env), [campaign-log.md](campaign-log.md).

## Braços medidos

| Braço | Runtime | Pesos (revisão) | Especulação |
|---|---|---|---|
| s27r (controle) | mlx-dspark 0.20.3, `--prefix-cache-rungs 1024` | `mlx-community/Qwen3.8-27B-8bit` @ `815b83c0` | DFlash2 `incoai/Qwen3.8-27B-DFlash2` @ `dedf8df6` |
| k27 | Splash 1.3.1 | `mlx-community/Qwen3.8-27B-8bit` @ `815b83c0` | DFlash2 @ `dedf8df6` (`--draft-model`) |
| r27d | mlx-serve 26.10.2, `--no-mtp` | `ddalcu/Qwen3.8-27B-MLX-Serve-8bit` @ `7775059e` | drafter DFlash2 embutido no pack |

Referências externas: **w1** = driver Flash-Next (Swift 1.5 MLX-4.7bpw em mlx-serve 26.10.1), **n2** = driver secundário (ddalcu iQ-MLX-4.7bpw, mesmo runtime), ambos de [bench/swift15-flashnext-2026-10/results/tturno-summary.json](../../swift15-flashnext-2026-10/results/tturno-summary.json).

Protocolo: `cache_probe.py`, fixture `audit_retrieval`, needles 10/50/90, `max_tokens` 4096, 3 reps (`middle_mutation` 1 rep), `temperature 1.0`, `top_p 0.95`, `top_k 20`. `T_turno = TTFT(tool_turn) + 512 / mediana(decode quente)`. Números de `summarize_driver.py` por braço, banda e tag.

## T_turno

| Braço | Esforço | 32K | 128K | ÷ s27r 32K | ÷ s27r 128K | ÷ w1 32K | ÷ w1 128K |
|---|---|---:|---:|---:|---:|---:|---:|
| **k27** | **medium** | **10.4 s** | **15.9 s** | 0.77 | 0.62 ¹ | 1.32 | 1.85 |
| k27 | xhigh | 13.3 s | 17.7 s | 0.78 | **0.689** | 1.68 | 2.06 |
| s27r | medium | 13.5 s | — ² | 1.00 | — | 1.71 | — |
| s27r | xhigh | 17.0 s | 25.7 s | 1.00 | 1.00 | 2.15 | 2.99 |
| r27d | medium | 15.7 s | 34.8 s | 1.16 | 1.35 ¹ | 1.99 | 4.05 |
| r27d | xhigh | 19.9 s | 44.7 s | **1.171** | **1.739** | 2.52 | 5.20 |
| w1 (Flash-Next, driver) | xhigh | 7.9 s | 8.6 s | — | — | 1.00 | 1.00 |
| n2 (Flash-Next, secundário) | xhigh | 8.1 s | 8.9 s | — | — | 1.03 | 1.03 |

¹ Contra o s27r `xhigh`: o s27r `medium` a 128K não foi medido. A razão mistura esforços.
² Cortado em 13/10 15:00: nenhuma decisão lia esse número.

Limite para reabrir o veredito de driver: ≤ 9.9 s a 32K e ≤ 10.8 s a 128K. Nenhum braço chega.

## Outras métricas (bandas de 32K e 128K)

| Braço | Esforço | Banda | Cold TTFT | Warm TTFT identical / append / tool_turn | Hit append / tool_turn | Prefill frio | Decode quente | Aceitação drafter | Wired pico | Swap Δ | Needles |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---|
| s27r | xhigh | 32K | 109.9 s | 0.1 / 8.5 / 5.4 s | 0.94 / 0.96 | 248 tok/s | 44.0 | — | 43.3 GB | 0.00 | 12/13 (1 truncada) |
| s27r | medium | 32K | 109.5 s | 0.1 / 8.3 / 5.5 s | 0.94 / 0.96 | 249 tok/s | 63.8 | — | 41.5 GB | 0.00 | 13/13 |
| s27r | xhigh | 128K | 712.6 s | 0.1 / 31 / 9.8 s | 0.97 / 0.99 | 176 tok/s | 32.3 | — | 55.4 GB | −0.04 | 13/13 |
| k27 | xhigh | 32K | 76.3 s | 0.2 / 3.6 / 3.9 s | 0.96 / 0.96 | 358 tok/s | 54.7 | n/d | 42.2 GB | −0.03 | 12/13 (1 truncada) |
| k27 | medium | 32K | 76.1 s | 0.3 / 3.8 / 3.9 s | 0.96 / 0.96 | 358 tok/s | 79.3 | n/d | 42.1 GB | 0.00 | 13/13 |
| k27 | xhigh | 128K | 535.1 s | 0.4 / 6.9 / 7.4 s | 0.99 / 0.99 | 235 tok/s | 49.8 | n/d | 53.8 GB | −0.03 | 13/13 |
| k27 | medium | 128K | 534.4 s | 0.3 / 6.9 / 7.4 s | 0.99 / 0.99 | 235 tok/s | 60.5 | n/d | 53.5 GB | 0.00 | 13/13 |
| r27d | xhigh | 32K | 109.0 s | 0.7 / 5.7 / 5.8 s | 0.96 / 0.96 | 250 tok/s | 36.3 | 0.461 | 59.3 GB | 0.00 | 13/13 |
| r27d | medium | 32K | 108.4 s | 0.5 / 5.7 / 5.8 s | 0.96 / 0.96 | 252 tok/s | 51.9 | 0.792 | 63.0 GB | 0.00 | 13/13 |
| r27d | xhigh | 128K | 717.8 s | 1.6 / 11 / 11 s | 0.99 / 0.99 | 175 tok/s | 15.1 | 0.538 | 70.4 GB | 0.00 | 13/13 |
| r27d | medium | 128K | 716.8 s | 1.5 / 11 / 11 s | 0.99 / 0.99 | 175 tok/s | 21.3 | 0.767 | 69.5 GB | 0.00 | 13/13 |
| w1 | xhigh | 32K / 128K | 34.5 / 165.5 s | tool_turn 1.8 / 1.9 s | 0.96 / 0.99 | 791 / 759 tok/s | 84.6 / 76.7 | MTP 0.774 / 0.668 | 96.1 / 111.2 GB | 0 | ok |

- Zero erros HTTP nas bandas. Todos os braços passam nos gates. A needle "truncada" é uma resposta que bateu 4096 tokens de raciocínio; truncado não é falha de gate.
- "n/d": o Splash 1.3.1 não expõe a aceitação do drafter no que o harness lê.
- A aceitação do r27d vem do `[spec-stats]` do mlx-serve (`mode=dflash`).
- Swap Δ ≤ 0.04 GB em módulo em todos. O wired pico de todos os braços do 27B fica abaixo do alerta de 102 GB.

**Respostas vazias.** `empty_answers.py results/think/*.jsonl`: **0 de 25** registros `stop` (k27 `medium` 0/10, k27 `xhigh` 0/10, r27d `xhigh` 0/5). O bug QwenLM #216 não apareceu.

**Sonda de raciocínio a 128K (`think_turn_probe`).** No Splash, o `tool_turn` que reenvia `reasoning_content` (modo `resend`) recebeu **HTTP 400 nas 6 tentativas** (3 por esforço). O modo `drop` (sem reenviar o raciocínio) serviu todas, com TTFT de 7.4 s. O r27d serviu os dois modos, mas com TTFT de 94–104 s no `tool_turn` da sonda.

## Smokes de 8K (`medium`, 1 rep, 13/10)

| Braço | Runtime e pesos | Decode mediano (5 cenários) | Decode quente | T_turno 8K | Warm TTFT tool_turn | Prefill | Aceitação | reasoning_chars mín. | Wired pico |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| k27 | Splash 1.3.1, mlx-community 8bit + DFlash2 | 86.5 | 92.3 | 8.6 s | 3.1 s | 398 tok/s | n/d | 847 | 37.0 GB |
| r27d | mlx-serve 26.10.2, ddalcu 8bit, drafter | 83.6 | 80.6 | 10.8 s | 4.5 s | 273 tok/s | 0.788 (dflash) | 1724 | 40.2 GB |
| o27q4 | oMLX 0.7.1.dev1, Jundot oQ4e-mtp `49c1d603` | 81.4 | 84.8 | 10.7 s | 4.4 s | 256 tok/s | — | 825 | 26.1 GB |
| r27m | mlx-serve 26.10.2, ddalcu 8bit, só MTP prof. 3 | 51.5 | 51.5 | 14.5 s | 4.5 s | 277 tok/s | 0.888 (mtp) | 1543 | 39.3 GB |
| l27 | llama.cpp b11569, ggml-org Q8_0 + draft-mtp | 35.3 | 35.3 | 19.0 s | 4.5 s | 242 tok/s | — | 983 | 37.2 GB |

"Decode mediano" é a mediana dos 5 cenários (a coluna de [etapa1-smokes.md](etapa1-smokes.md)). "Decode quente" é a mediana de identical, append e tool_turn (a do `summarize_driver.py`). Todos os smokes têm rc 0, `reasoning_chars > 0` e `cached_tokens` presente. O hit a 8K fica em ≈ 0.71, como esperado: o turno novo tem ~1K tokens de um prompt de 3.7K.

## Decisões por fase

| Fase | Braço | Regra aplicada | Resultado | Decisão |
|---|---|---|---|---|
| P0 | s27r | Controle. Reproduzir a referência de 08/10 (16.7 / 25.7 s) | 17.0 / 25.7 s | Reproduz em 2% (32K) e exato (128K) |
| P1 | k27 | `T_turno ≤ 0.75 × s27r` a 128K e todos os gates (hit ignorado por regra) | 0.689 | **PASS** (`P1_PASS=1`, `P1_BEST=k27`) |
| P3 | r27d | `T_turno ≤ 1.00 × s27r` a 32K e 128K e todos os gates | 1.171 / 1.739 | **FAIL** (`P3_PASS=0`) |
| P7 | w27d | `≤ 1.03 × r27d` | não rodou | `P7_PASS=not_run`; cancelada pelo usuário em 14/10 |
| P5 | qualquer | `T_turno ≤ 1.25 × w1` nas duas bandas (≤ 9.9 / 10.8 s) e todos os gates | melhor: k27 `medium` 10.4 / 15.9 s | **`P5_GO=0`**. Nenhum braço chega a 1.25× o driver. A P5 não roda. O NO-GO como driver continua |

O `driver_gate.py` rodou no MacBook (commit 8bc9fe0), porque o Python 3.9 do rig não aceita a sintaxe do script.

## Configuração recomendada do 27B hoje

Use o **Splash 1.3.1** com os pesos `mlx-community/Qwen3.8-27B-8bit` e o drafter DFlash2, em `reasoning_effort` **`medium`**.

| Item | Valor |
|---|---|
| Runtime | Splash 1.3.1, `~/.local/opt/qwen38/splash-v1.3.1/bin/splash` |
| Alvo | `mlx-community/Qwen3.8-27B-8bit` @ `815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9` (Hub ID; o Splash recusa diretório local para o alvo; pré-baixar no cache do HF e usar `--offline`) |
| Drafter | `incoai/Qwen3.8-27B-DFlash2` @ `dedf8df68adfb1afeaf7b7480c0a0243108177b4`, diretório local via `--draft-model` |
| KV | int8, o padrão do Splash 1.3.1 (`--kv-format`) |
| Contexto | `--max-context 131072` |
| Flags extras | `--idle-release off --language-only --no-webui --offline` |
| Esforço | `medium` (o Splash aceita `reasoning_effort` no topo do corpo). Nunca `high` (HTTP 500, QwenLM #217) |
| Histórico | Não reenviar `reasoning_content` nas mensagens de assistente: o Splash responde HTTP 400 |
| Launcher | [bench/qwen3.8-prefix-cache/scripts/run-splash.sh](../../qwen3.8-prefix-cache/scripts/run-splash.sh) `K`, flags em [config/splash-flags.env](../../qwen3.8-prefix-cache/config/splash-flags.env), bloco `k27` de [run-candidate.sh](../../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh) |

Comando que o bloco `k27` monta:

```bash
# once: pre-fill the HF cache (Splash refuses a local target dir)
~/.local/opt/qwen38/splash-v1.3.1/python/bin/hf download mlx-community/Qwen3.8-27B-8bit --revision 815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9
~/.local/opt/qwen38/splash-v1.3.1/bin/splash serve \
  --model mlx-community/Qwen3.8-27B-8bit --host 0.0.0.0 --port 8585 \
  --max-context 131072 \
  --revision 815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9 \
  --draft-model ~/.cache/local-llms/qwen3.8-prefix-cache/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4 \
  --idle-release off --language-only --no-webui --offline
```

`--idle-release off` mantém o modelo carregado (o padrão o libera após 10 min ociosos). `--language-only` pula a torre de visão; tire esta flag para usar imagens.

**Por que `medium`.** O esforço muda o decode, não só o tamanho do raciocínio. Com `medium`, o k27 decodifica 79.3 tok/s a 32K (contra 54.7 em `xhigh`, +45%) e 60.5 a 128K (contra 49.8, +21%). O warm TTFT não muda (3.9 / 7.4 s). O `T_turno` cai de 13.3 / 17.7 s para 10.4 / 15.9 s. O ganho real é maior que o `T_turno` mostra: o `T_turno` fixa 512 tokens, mas `medium` também gera cerca de metade dos tokens (mediana 637 contra 1542 a 32K, 704 contra 1209 a 128K).

## Aprendizados

1. **O esforço muda o decode pela aceitação do drafter.** Raciocínio `medium` é mais previsível, e o drafter acerta mais. Evidência no r27d, o único braço que expõe a aceitação: 0.461 → 0.792 a 32K e 0.538 → 0.767 a 128K, com decode 36.3 → 51.9 e 15.1 → 21.3 tok/s. O s27r sobe de 44.0 para 63.8 tok/s a 32K; o k27 de 54.7 para 79.3. Comparar braços exige o mesmo esforço.
2. **A cabeça MTP sozinha é lenta no mlx-serve.** O r27m (só MTP, profundidade 3) decodifica 51.5 tok/s a 8K, 38% abaixo do r27d (83.6) com o mesmo pack, apesar da aceitação maior (0.888 contra 0.788). A P8 foi cortada por isso.
3. **O mlx-serve 26.10.2 com DFlash2 desaba a 128K no 27B.** O decode cai de 36.3 (32K) para 15.1 tok/s (128K) em `xhigh`. O r27 de 08/10 (mlx-serve 26.10.1, mlx-community 8bit + DFlash2) fez 15.5 tok/s a 128K: a versão nova não corrigiu. O r27d também usa o maior wired do 27B (59–70 GB).
4. **O Splash reporta `cached_tokens`.** O plano supôs o contrário (`SPLASH_HAS_CACHED_TOKENS=unknown`; a regra da P1 ignorava os gates de hit). O k27 devolveu `cached_tokens` em todos os cenários quentes (27232–27296 a 32K, 125568–125600 a 128K) e passou os gates de hit por conta própria: 0.96 / 0.99.
5. **O Splash tem o prefill mais rápido do 27B.** Prefill frio de 358 tok/s a 32K e 235 a 128K, contra 248 e 176 do s27r com os mesmos pesos (+44% e +33%). O TTFT frio a 128K cai de 713 para 535 s. O warm TTFT do `tool_turn` cai de 5.4 / 9.8 s para 3.9 / 7.4 s. O fornecedor atribui o ganho ao prefill dividido entre GPU e ANE; o harness não registra se o ANE rodou (`ane_prefill_enabled` não é preenchido para o Splash).
6. **O warm TTFT ainda decide o veredito.** Para ficar a 1.25× do w1 a 128K, o 27B precisa de warm TTFT ≤ ~3 s e decode ≥ ~65 tok/s ao mesmo tempo. O k27 `medium` tem 7.4 s e 60.5 tok/s. O decode quase chega; o TTFT fica a 2.5× do necessário.
7. **O Splash recusa `reasoning_content` reenviado.** A sonda de raciocínio recebeu HTTP 400 em todo `tool_turn` com `resend`. Um cliente que preserva o raciocínio no histórico quebra no Splash. Configure o cliente para não reenviar.
8. **O `idle-gate.sh` media memória livre errado.** Contava só `Pages free`. Depois dos downloads, havia 2.6 GB em `free` e 86 GB de cache em páginas speculative, e o gate travou (exit 75). O primeiro conserto (9293a42) somou free + speculative + purgeable, mas ainda perdeu o cache em páginas inactive (40.9 GB vistos, 122 GB reais) e travou o P0 por 38 min. A medida final (5c60abb) é total − wired − anônima − compressor.
9. **Reiniciar a campanha disputa a porta do driver diário.** Às 11:33 de 13/10, o `trap EXIT` da campanha antiga religou o driver Flash-Next (70 GB, porta 11234) enquanto a campanha nova já tinha rodado o `stop_driver`. O gate viu 46.7 GB livres por 38 min. Regra: parar a campanha, esperar ~60 s, parar o que ouvir em 11234 e só então iniciar.
10. **O Python do rig é 3.9.** O `driver_gate.py` usa `X | None` e não roda lá. O `P5_GO` foi calculado no MacBook. Scripts que rodam no rig não podem usar sintaxe acima de 3.9 sem `from __future__ import annotations`.
11. **O s27r reproduziu a referência de 08/10.** 17.0 / 25.7 s contra 16.7 / 25.7 s (Etapa F): +1.8% a 32K, igual a 128K. O decode também bate (44.0 / 32.3 contra 45.4 / 32.1). O controle da sessão é confiável.
12. **Uma banda de 128K levou ~3 h, não ~45 min.** s27r `xhigh` 128K: 2 h 47 min. r27d: 3 h 06 min (`xhigh`) e 2 h 51 min (`medium`). As requisições somam só 56–67 min; o resto ficou fora delas (reinícios entre reps e gates), e a causa não foi isolada. O k27 levou 44–47 min por esforço. Com esse ritmo, as fases de velocidade passariam de 60 h, contra ~32 h estimadas. Isso levou ao corte de 13/10.

## O que não foi medido

| Item | Por quê |
|---|---|
| s27r `medium` a 128K | Corte de 13/10 15:00: nenhuma decisão lia o número |
| P7, w27d (Swift 1.5 oQ4e no mlx-serve + DFlash2) | Cancelada em 14/10. A P3 mostrou que o mlx-serve com DFlash2 desaba a 128K no 27B; o w27d usa o mesmo caminho |
| P2, o27q4 e o27q8 (oMLX 0.7.1.dev1, packs refit) | Escopo B: a campanha só seguia se o P1 passasse, e depois parou na P3. O o27q8 (repin `6c76ddfb82af`) ficou sob demanda para corrigir o `27b-summary.md`. Só o smoke de 8K do o27q4 rodou |
| P4, o27sw (Swift no oMLX) | Depende do o27q4 da P2 |
| P8, r27m e w27m (só MTP) | Corte de 13/10: o r27m decodifica 51.5 tok/s a 8K |
| P6, l27 e l27n (llama.cpp GGUF) | Corte de 13/10: o l27 decodifica 35.3 tok/s a 8K |
| Bateria de qualidade (Task 7: HumanEval, GPQA, LiveCodeBench, jdhodges, Veerman, IF, loops) | Não rodou. Nenhuma leitura de qualidade do Splash ou de outro braço nesta campanha |
| 256K | Fora do escopo do plano |
| P5 (qualidade agêntica com OpenCode) | `P5_GO=0`: nenhum braço chegou a 1.25× o driver |
| Aceitação do drafter no Splash | O Splash não a expõe ao harness |

## Próximos passos se o 27B voltar à pauta

1. **Bateria de qualidade no Splash (k27, `medium`), ~11 h.** É a lacuna principal: o stack mais rápido não tem nenhuma medida de qualidade no rig. Rodar `run-battery.sh` com o k27 antes de usá-lo para trabalho real.
2. **Repin do o27q8 para o `27b-summary.md`.** `run-campaign.sh --only P2` com o o27q8 (`Jundot/Qwen3.8-27B-oQ8e-mtp` @ `6c76ddfb82af`, já no disco). A linha o27 de 08/10 usa o pin obsoleto `c99e5aad`.
3. **Splash com o pack Swift 1.5 do Splash.** `SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash` @ `44c96f13` (17.4 GB, 4-bit + DFlash2 do base). O Swift 1.5 pensa menos, e o 4-bit deve decodificar mais rápido que o 8bit. Medir `T_turno`, aceitação e qualidade contra o k27.
4. **w27d só se um runtime corrigir o decode do drafter a 128K.** Enquanto o mlx-serve fizer ~15 tok/s a 128K com DFlash2 no 27B, o w27d não tem chance.
5. **Reabrir o veredito de driver só com warm TTFT ≤ ~3 s a 128K.** Nenhum runtime medido chega perto (melhor: 7.4 s no Splash).
