# Qwen3.8 — harnesses para coding e para agente (relatório)

> **Data:** 2026-09-04. **Escopo:** os dois Qwen3.8 presentes no rig (M4 Max 128 GB):
> `Qwen3.8-27B` (denso) e `Qwen3.8-Flash-Next` (MoE 125B-A6B). Fontes web consultadas
> em 2026-09-04. Números de fabricante estão marcados como *vendor*. Números do rig
> apontam para o arquivo de origem em `bench/`.
>
> **Plano de testes correspondente:** [bench/qwen3.8-harness-eval/plan.md](../bench/qwen3.8-harness-eval/plan.md).

## 1. Resposta curta

Use **Claude Code** para coding interativo e **OpenCode** para trabalho de agente autônomo.
Use **Pi** quando o custo de prefill dominar (contexto longo em runtime com cache fraco).
Trate **Qwen Code** como candidato a testar, não como default.

Motivos, em ordem:

1. A Qwen mediu SWE-bench Pro, DeepSWE e QwenSWEBench do 27B e do Flash-Next **com o harness
   Claude Code** (temp 1.0, top_p 0.95, contexto 256K). O Claude Code é o único harness cujo
   comportamento o vendor validou com estes modelos. Fonte: cards HF do 27B e do Flash-Next.
2. Os dois runtimes recomendados no rig (`mlx-serve` e `oMLX`) expõem o endpoint Anthropic
   `/v1/messages`. O Claude Code funciona sem proxy. O `mlx-serve` honra `output_config.effort`,
   o que permite mapear `reasoning_effort` a partir do Claude Code.
3. O OpenCode é o harness aberto com maior adoção para modelos open-weight (winder.ai, 2026-08-20)
   e já é o harness padrão do rig ([docs/local-llm-reference.md](../docs/local-llm-reference.md)).
   Ele mapeia `reasoning_content`, aceita `limit.context`/`limit.output` por modelo e permite
   variantes com `reasoningEffort`.
4. O Pi usa quatro ferramentas e um system prompt de ~200 tokens. O Claude Code usa ~25.000 tokens
   de system prompt. Em runtime sem reuso de cache após tool call (MTPLX a 128K: `tool_turn` 0.00,
   re-prefill ~870 s), o Pi é o único harness com custo por turno aceitável.
5. O Qwen Code é "o melhor harness para modelos Qwen e o pior para qualquer outro" (winder.ai).
   No teste de Raschka (2026-06-27, Qwen3.6-35B-A3B), o Qwen Code resolveu 4/5 tarefas e o
   Claude Code 5/5 com o mesmo modelo. A versão 0.22.0 documenta o Qwen 3.7 Max; não confirmei
   suporte declarado ao Qwen3.8.

## 2. Os modelos e o que muda para o harness

| Item | Qwen3.8-27B | Qwen3.8-Flash-Next | Fonte |
|---|---|---|---|
| Arquitetura | denso 27B, VL | MoE 125B-A6B, preview Qwen4, só 12/48 camadas com KV crescente | HF |
| Contexto nativo | 262.144 | 262.144 (1M com YaRN) | HF |
| `reasoning_effort` | `xhigh` default; `medium`, `low` | idem | HF |
| `preserve_thinking` | ON por default | ON por default | HF |
| Sampling thinking (*vendor*) | temp 1.0, top_p 0.95, top_k 20, min_p 0, presence 0 | idem | HF |
| Sampling instruct (*vendor*) | temp 0.7, top_p 0.80, top_k 20, presence 1.5 | idem | HF |
| SWE-bench Pro (*vendor*) | 61.7 | 62.5 | HF |
| DeepSWE 1.1 (*vendor*) | 42.2 | 58.7 | HF |
| Terminal-Bench 2.1 (*vendor*) | 73.0 | não publicado | codersera |
| Decode no rig @32K | 32–42 tok/s (oMLX oQ8e, dspark 8bit) | **60–64 tok/s** (mlx-serve ddalcu) | `bench/qwen3.8-prefix-cache/results/`, `bench/qwen38-flash-next/results/` |
| Decode no rig @128K | ~25 | ~33 (oMLX) | idem |
| Cache `tool_turn` no rig | oMLX 0.94–0.99; MTPLX 0.00 @128K | mlx-serve 0.961 @32K; oMLX 0.986 @128K | idem |
| Fraqueza declarada | "overthinks" no default; ~2× tokens vs 3.6 | declara "done" sem concluir em cadeias longas | codersera; `bench/qwen38-flash-next/plan.md` |

Três consequências para a escolha do harness:

- **`reasoning_effort` é o controle mais importante.** O default `xhigh` gerou 22.276 tokens de
  raciocínio e 21 minutos numa tarefa simples (relato codersera). Mas a Qwen avisa que em
  tarefas agentic multi-turn um effort menor "nem sempre reduz o tempo total", porque o modelo
  erra e refaz. O harness precisa expor esse knob. O plano de testes mede `medium` contra `xhigh`.
- **Reuso de cache após tool call decide o custo por turno.** Um agente faz 20–50 tool calls por
  tarefa. Sem reuso, cada turno re-prefila o contexto inteiro. Escolha o runtime pelo cache antes
  de escolher o harness.
- **O Flash-Next é o modelo de agente; o 27B é o modelo de qualidade por token.** O rig mediu
  1,5× o decode do 27B e cache melhor. O gate de qualidade (Terminal-Bench) do Flash-Next
  ainda não rodou no rig.

## 3. Runtimes do rig e endpoints

| Runtime | OpenAI `/v1/chat/completions` | Anthropic `/v1/messages` | Modelo recomendado no rig | Porta usada nas campanhas |
|---|---|---|---|---|
| mlx-serve v26.8.11 (ddalcu) | sim | sim | Flash-Next ddalcu mixed-4/8 (75 GB, 60–64 tok/s, swap 0) | 11234 (default do projeto) |
| oMLX 0.6.4 | sim | sim | 27B oQ8e-mtp (arm T); Flash-Next oQ4e com `qwen4_ple_ssd_offload: true` | 8000 |
| MTPLX 2.10.0 | sim | não verificado | 27B; **evitar em agente acima de 64K** (`tool_turn` 0.00 @128K) | — |
| mlx-dspark 0.17.2 | sim | não verificado | 27B 8bit + DFlash2 (41.8 tok/s @32K); sem suporte a `qwen4_exp` | — |
| llama.cpp mainline | sim | não verificado | Flash-Next GGUF com `--override-tensor per_layer_token_embd.weight=CPU` (~36 tok/s, terceiro) | 8080 |
| LM Studio | sim | sim | qualquer; caminho documentado no rig | 1234 |

Os suportes "sim" do mlx-serve e do oMLX vêm dos READMEs dos projetos (mlx-serve: "implements the
full Anthropic Messages API"; oMLX: "/v1/messages, drop-in for Claude Code"). Não testei
`/v1/messages` no rig com thinking + tools em streaming.

## 4. Harnesses avaliados

| Harness | Licença | Protocolo local | Overhead de prompt | Ponto forte com Qwen3.8 | Risco com Qwen3.8 local |
|---|---|---|---|---|---|
| **Claude Code** | proprietário | Anthropic | alto (~25K tokens de system prompt) | harness das evals oficiais; config oficial da Qwen publicada; `effort` mapeável no mlx-serve | sem controle de sampling; prefill caro sem cache; modelos alias (`ANTHROPIC_DEFAULT_*`) precisam apontar para o mesmo modelo local |
| **OpenCode** | MIT | OpenAI-compatible | médio | harness padrão do rig; `reasoning` + `limit` por modelo; variantes com `reasoningEffort`; LSP; MCP | default de privacidade antigo (naming via serviço externo, corrigível na config); prompt maior que o Pi |
| **Qwen Code** | Apache-2.0 | OpenAI-compatible (`OPENAI_BASE_URL`) | médio | formato de tool call afinado para Qwen; Auto-Skills, subagents, Plan Mode | 4/5 vs 5/5 do Claude Code no teste de Raschka; telemetria ON (`~/.qwen/settings.json`); suporte ao 3.8 não declarado na 0.22.0 |
| **Pi** | MIT | OpenAI-compatible | mínimo (~200 tokens, 4 ferramentas) | único harness viável quando o cache não reusa; `contextWindow` explícito | feito para sessões curtas supervisionadas; endpoints locais podem rejeitar `reasoning_effort`/`developer` role |
| **Codex CLI** | Apache-2.0 | OpenAI (Responses; `wire_api = "chat"` para locais) | baixo (menor uso de tokens no teste de Raschka) | sandbox de shell; config oficial da Qwen para o Codex (cloud) | afinado para modelos OpenAI; Responses API em runtime local não verificada |
| **Cline** | Apache-2.0 | OpenAI-compatible / LM Studio | médio | IDE; já documentado no rig | menos controle de `reasoning_effort`; fluxo VS Code, não terminal |
| **Aider** | Apache-2.0 | OpenAI-compatible | baixo | edição por diff, git nativo | não é loop de agente; sem shell autônomo |
| **Goose** | Apache-2.0 | OpenAI-compatible, MCP | médio | governança neutra (Linux Foundation); on-device | roadmap lento; menos adoção em coding |
| **OpenHands** | MIT | OpenAI-compatible | alto | sandbox Docker; tarefas longas | loops de custo em problemas ambíguos; Docker no Mac |
| **DeepSeek Harness (dsh)** | MIT | OpenAI-compatible (provider custom via Settings → Models) | não publicado | tudo é plugin (modelo, tools, sandbox, sessão); modo `Minimal` (bash + editor) para benchmark; relatos no Reddit com Qwen3.8-27B | developer preview 0.1.0-rc.7 (2026-08-13) com breaking changes anunciados; agente para no meio da tarefa sem aviso (DataCamp); config só pela web UI |
| **OpenClaw** | — | OpenAI Responses | médio | config oficial da Qwen; já documentado no rig | agente geral, não harness de coding |

Fontes por linha: winder.ai (2026-08-20), Raschka (2026-06-27), bradAGI/awesome-cli-coding-agents,
opencode.ai/docs, QwenLM/qwen-code, ravsau pi-qwen-local-agent, apidog, codersera, deepseek.com/harness,
DataCamp (dsh tutorial).

**Sobre o DeepSeek Harness.** Ele não entra na recomendação por ser developer preview. A arquitetura
interessa por um motivo: o modo `Minimal` (só bash e editor de texto) dá um harness de overhead
mínimo, comparável ao Pi, dentro do mesmo runtime que também tem o modo `Standard` completo. Isso
permite medir o custo do prompt do harness com o modelo fixo. Reavaliar quando sair a 0.1.0 estável
e quando a config por arquivo for documentada.

## 5. Recomendação por uso

### Coding interativo (pair programming, uma tarefa por vez)

1. **Claude Code + mlx-serve + Flash-Next** para velocidade. Configurar `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "local",
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:11234",
    "ANTHROPIC_MODEL": "<model-id do /v1/models>",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "<mesmo model-id>",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "<mesmo model-id>",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "<mesmo model-id>",
    "CLAUDE_CODE_SUBAGENT_MODEL": "<mesmo model-id>"
  }
}
```

   O bloco segue a config oficial da QwenCloud para o Claude Code, com o endpoint trocado
   para o local. Todos os alias apontam para o mesmo modelo porque o rig serve um modelo por vez.

2. **Claude Code + oMLX + 27B oQ8e** quando a qualidade por token importar mais que o decode.
   Trocar `ANTHROPIC_BASE_URL` para `http://127.0.0.1:8000`.

### Agente autônomo (tarefa multi-passo, sem supervisão)

1. **OpenCode + mlx-serve + Flash-Next.** Config em `~/.config/opencode/opencode.json`,
   provider `openai-compatible`, `limit.context` 131072, `limit.output` 32768, `reasoning: true`,
   variante `medium` com `reasoningEffort`. Manter `preserve_thinking` no default (ON).
2. **Qwen Code** como segunda opção, apenas para comparar formato de tool call e Plan Mode.
3. **Pi** quando o runtime for MTPLX ou o contexto passar de 64K com cache fraco.

### Configuração comum a todos os harnesses

| Knob | Valor | Motivo |
|---|---|---|
| `reasoning_effort` | `medium` para agente; `xhigh` só para tarefa única difícil | default `xhigh` dobra tokens; Qwen avisa que `low` pode aumentar retries |
| `preserve_thinking` | ON (default) | continuidade de raciocínio entre turnos de agente |
| Sampling | temp 1.0, top_p 0.95, top_k 20, min_p 0 | recomendação do card para thinking |
| Contexto no harness | 65.536 mínimo; 131.072 para Flash-Next | um turno de agente consome 8–16K antes de raciocinar; 65.536 é o valor do rig para loops |
| Output máximo | 32.768 | reserva espaço para raciocínio longo sem cortar a resposta |
| Runtime | com reuso de cache em `tool_turn` (mlx-serve, oMLX) | evita re-prefill a cada tool call |

## 6. O que não verifiquei

- **Terminal-Bench do Qwen3.8-27B no rig.** Os docs de `bench/qwen38-flash-next/` dizem que o
  T-Bench "deu NO-GO no 27B". Não encontrei script `run-tbench-qwen3.8*` nem arquivo de resultado.
  Trate a frase como hipótese até existir o dado.
- **Terminal-Bench do Flash-Next.** Pendente no rig e não publicado pelo vendor.
- **`/v1/messages` com thinking + tools em streaming** no mlx-serve e no oMLX. Os READMEs
  afirmam suporte. O plano de testes começa com um smoke desse caminho.
- **Suporte declarado do Qwen Code ao Qwen3.8.** A doc da 0.22.0 cita o 3.7 Max.
- **Codex CLI com Responses API em runtime local.** Nenhuma das fontes testou isso com Qwen3.8.
- **Mapeamento de `reasoning_content`** no OpenCode contra oMLX e mlx-serve. O OpenCode documenta
  o campo; os runtimes não documentam o nome que emitem.
- Todos os números de benchmark de SWE-bench, DeepSWE e Terminal-Bench são *vendor*. Nenhum tem
  verificação independente publicada.

## 7. Fontes

- Qwen3.8-27B card: https://huggingface.co/Qwen/Qwen3.8-27B
- Qwen3.8-Flash-Next card: https://huggingface.co/Qwen/Qwen3.8-Flash-Next
- QwenLM/Qwen3.8: https://github.com/QwenLM/Qwen3.8
- QwenLM/qwen-code: https://github.com/QwenLM/qwen-code
- QwenCloud, Claude Code settings: https://docs.qwencloud.com/developer-guides/clients-and-developer-tools/claude-code
- winder.ai, "A Comparison of AI Agent Harnesses in 2026" (2026-08-20): https://winder.ai/ai-agent-harness-comparison/
- Raschka, "Using Local Coding Agents" (2026-06-27): https://magazine.sebastianraschka.com/p/using-local-coding-agents
- codersera, Qwen3.8-27B as local Claude Code replacement: https://codersera.com/blog/qwen-3-8-27b-local-claude-code-replacement-2026/
- zachrattner, Qwen 3.8 on a Mac: https://zachrattner.com/projects/ai-mac-cluster/agentic-coding
- DataCamp, Flash-Next + OpenCode: https://www.datacamp.com/tutorial/run-qwen3-8-flash-next-locally
- apidog, Qwen 3.8 for coding: https://apidog.com/blog/qwen-3-8-for-coding/
- OpenCode models docs: https://opencode.ai/v2/docs/models/
- Pi + Qwen local: https://github.com/ravsau/ai-tutorials/tree/main/pi-qwen-local-agent
- awesome-cli-coding-agents: https://github.com/bradAGI/awesome-cli-coding-agents
- oMLX: https://github.com/jundot/omlx · mlx-serve: https://github.com/ddalcu/mlx-serve
- DeepSeek Harness: https://deepseek.com/harness/en/ · https://github.com/deepseek-ai/deepseek-harness · https://www.datacamp.com/tutorial/deepseek-harness
- Rig: [bench/qwen3.8-prefix-cache/](../bench/qwen3.8-prefix-cache/plan.md), [bench/qwen38-flash-next/](../bench/qwen38-flash-next/references.md)
