# 2026-09-04 — Qwen3.8 × harness: plano de testes manual de coding e agente

> **Status:** aberto. **Executor:** o usuário, à mão, um run por vez.
> **Relatório de base:** [research/qwen3.8-harness-report.md](../../research/qwen3.8-harness-report.md).
> **Templates:** [tasks/](tasks/). **Fixtures:** [fixtures/](fixtures/). **Planilha:** [results/scorecard-template.csv](results/scorecard-template.csv).

## Pergunta

Qual par modelo × harness entrega mais trabalho de coding correto por hora no rig, com
o menor número de intervenções humanas?

Sub-perguntas:

1. O Claude Code (harness das evals oficiais) entrega mais que o OpenCode com o mesmo modelo?
2. O Flash-Next (mais rápido) entrega o mesmo que o 27B (mais denso) em tarefa de agente?
3. `reasoning_effort=medium` reduz o tempo total em tarefa multi-turn, ou aumenta retries?
4. O Flash-Next "declara done" sem concluir em cadeias longas (T7)?

## Matriz

| Eixo | Valores |
|---|---|
| Modelo | `27B` (oMLX, oQ8e-mtp, arm T) · `FN` (mlx-serve v26.8.11, ddalcu mixed-4/8) |
| Harness | `CC` Claude Code · `OC` OpenCode · `QC` Qwen Code · `PI` Pi (opcional) |
| Effort | `medium` (default do plano) · `xhigh` (só na Fase C) |
| Tarefa | T1–T7 em [tasks/](tasks/) |

Um **run** é uma célula modelo × harness × effort × tarefa. Um run usa uma sessão nova do
harness e uma cópia nova do fixture.

## Fases

Rode as fases em ordem. Cada fase tem um gate. Não pule para a próxima fase com o gate aberto.

### Fase 0 — smoke do endpoint (30 min)

Para cada runtime, confirme que o harness fecha um loop de tool call.

1. Suba o runtime com o modelo (seção Setup).
2. Abra o harness e envie: `List the files in this directory, then read README.md and tell me its first heading.`
3. Registre: o harness chamou a ferramenta? O modelo leu o arquivo? A resposta veio em texto?

Gate: os 4 pares `27B×CC`, `27B×OC`, `FN×CC`, `FN×OC` fecham o loop. Um par que falha sai da
matriz e o motivo vai para `results/notes.md`.

### Fase A — triagem (6 runs, ~2 h)

Modelo × OpenCode × effort `medium` × tarefas **T1, T3, T5**.

Gate: pelo menos um modelo passa T1 e T5. Se nenhum passa T5, o problema é runtime ou harness,
não modelo. Volte à Fase 0.

### Fase B — harness (12 runs, ~4 h)

O modelo vencedor da Fase A × {`CC`, `OC`, `QC`} × `medium` × **T1, T2, T5, T7**.
Adicione `PI` só se algum harness ultrapassar 10 min de prefill acumulado numa tarefa.

Gate: um harness tem a maior soma de `pass` com o menor número de intervenções.

### Fase C — effort e cadeia longa (8 runs, ~4 h)

Os dois melhores pares da Fase B × {`medium`, `xhigh`} × **T4, T7**.

Gate: decisão sobre `reasoning_effort` por tipo de tarefa.

### Fase D — cobertura (opcional)

T6 (contexto longo) nos dois melhores pares. Só se o usuário tiver um repositório próprio
com 50+ arquivos para usar como alvo.

## Onde roda cada coisa

Dois papéis. O **Mac Studio** (rig, `mac-studio` / `100.110.87.118`) serve os modelos.
O **MacBook M4** (cliente) roda os harnesses e conecta no rig pelo tailnet. A conexão
detalhada está em [connect-from-macbook.md](connect-from-macbook.md).

| Passo | Máquina | O que roda |
|---|---|---|
| Subir os runtimes (oMLX `27B`:8000, mlx-serve `FN`:11234) | Mac Studio | `run-omlx.sh`, `run-mlx-serve.sh` |
| Confirmar o `model-id` (`curl /v1/models`) | Mac Studio ou MacBook | `curl http://mac-studio:<porta>/v1/models` |
| Configurar os harnesses (CC, OC, QC) | MacBook | edições em `~/.claude`, `~/.config/opencode`, env do `qwen` |
| Copiar o fixture e abrir a sessão do harness | MacBook | Protocolo de um run |
| Rodar o bloco Verificação e preencher o scorecard | MacBook | testes da tarefa |

Os dois runtimes bindam `0.0.0.0`, alcançáveis pelo tailnet em `mac-studio` (MagicDNS)
ou `100.110.87.118`.

## Setup por runtime (no Mac Studio)

Os caminhos de modelo e as portas seguem as campanhas anteriores. Suba os runtimes no rig
e confirme o `model-id` com `curl http://mac-studio:<porta>/v1/models` antes de configurar
o harness no MacBook.

| Modelo | Runtime | Launcher existente | Porta |
|---|---|---|---|
| `27B` | oMLX 0.6.4, arm T (oQ8e-mtp, `mtp_enabled: true`) | `bench/qwen3.8-prefix-cache/scripts/` (arm T) | 8000 |
| `FN` | mlx-serve v26.8.11, build ddalcu mixed-4/8 | `bench/qwen38-flash-next/` (arm FS) | 11234 |

Sampling em todos os runs: temp 1.0, top_p 0.95, top_k 20, min_p 0 (thinking mode do card).
Contexto do runtime: 131072. Não use MTPLX nem mlx-dspark nesta campanha; o MTPLX perde o
cache em `tool_turn` acima de 64K e o mlx-dspark não carrega o Flash-Next.

## Setup por harness (no MacBook)

Estas edições são no MacBook. Os `baseURL` usam o nome Tailscale do rig `mac-studio`;
se o MagicDNS não resolver, troque por `100.110.87.118`. Blocos prontos e adaptados à
versão instalada de cada harness em [connect-from-macbook.md](connect-from-macbook.md).

### Claude Code (`CC`)

`~/.claude/settings.json` (no MacBook):

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "local",
    "ANTHROPIC_BASE_URL": "http://mac-studio:11234",
    "ANTHROPIC_MODEL": "<model-id>",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "<model-id>",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "<model-id>",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "<model-id>",
    "CLAUDE_CODE_SUBAGENT_MODEL": "<model-id>"
  }
}
```

Para o `27B` troque a URL para `http://mac-studio:8000`. Effort: use o controle de effort do
Claude Code (`/effort` ou `CLAUDE_CODE_EFFORT_LEVEL`, conforme a versão instalada). Registre
no scorecard se o runtime honrou o effort (o mlx-serve documenta suporte a `output_config.effort`;
o oMLX não documenta).

### OpenCode (`OC`)

`~/.config/opencode/opencode.json` (formato v2 da doc; se a versão instalada usar `provider`
em vez de `providers`, adapte):

```json
{
  "providers": {
    "rig": {
      "name": "Mac Studio rig",
      "package": "@opencode-ai/ai/providers/openai-compatible",
      "settings": { "baseURL": "http://mac-studio:11234/v1", "apiKey": "local" },
      "models": {
        "fn": {
          "modelID": "<model-id>",
          "capabilities": { "tools": true, "input": ["text"], "output": ["text"] },
          "limit": { "context": 131072, "output": 32768 },
          "reasoning": true,
          "variants": {
            "medium": { "reasoningEffort": "medium" },
            "xhigh": { "reasoningEffort": "xhigh" }
          }
        }
      }
    }
  },
  "model": "rig/fn"
}
```

Duplique o bloco com `baseURL` `http://mac-studio:8000/v1` para o `27B`.

### Qwen Code (`QC`)

```bash
export OPENAI_BASE_URL=http://mac-studio:11234/v1
export OPENAI_API_KEY=local
export OPENAI_MODEL=<model-id>
qwen
```

Desligue a telemetria em `~/.qwen/settings.json` antes do primeiro run. Registre a versão
(`qwen --version`).

### Pi (`PI`, opcional)

`~/.pi/settings.json`: provider OpenAI-compatible, `baseUrl` do runtime, `model` = `<model-id>`,
`contextWindow` 131072. Se o runtime rejeitar o campo `reasoning_effort`, registre e siga sem ele.

## Protocolo de um run (no MacBook)

Um run inteiro roda no MacBook, contra o runtime que está de pé no Mac Studio.

1. Copie o fixture: `cp -R fixtures/<nome> <scratch>/<nome>-<run-id>`. O `run-id` é
   `<modelo>-<harness>-<effort>-<tarefa>-<n>`, por exemplo `FN-OC-medium-T1-1`.
2. Abra uma sessão nova do harness dentro da cópia.
3. Cole o bloco **Prompt** da tarefa sem alteração. Inicie o cronômetro.
4. Não intervenha até o harness parar. Se o harness pedir aprovação de comando, aprove e conte
   como `approvals`, não como intervenção.
5. Quando o harness parar, rode o bloco **Verificação** da tarefa. Registre `pass`/`fail`.
6. Se `fail` e o tempo total estiver abaixo do time-box, envie **uma** mensagem de correção com o
   texto do bloco **Follow-up** da tarefa. Conte `interventions += 1`. Máximo de 2 follow-ups.
7. Pare no time-box da tarefa mesmo com o agente rodando. Registre `timeout`.
8. Preencha uma linha no scorecard. Salve o transcript da sessão em `logs/<run-id>/`.

## Métricas por run

| Coluna | Como medir |
|---|---|
| `pass` | resultado do bloco Verificação após o último follow-up: `pass`, `fail`, `timeout` |
| `first_try` | `pass` sem nenhum follow-up |
| `wall_min` | minutos do primeiro prompt ao último token |
| `interventions` | follow-ups enviados (0–2) |
| `approvals` | aprovações de comando pedidas pelo harness |
| `tool_calls` | contagem no transcript (ou no log do runtime) |
| `tokens_out` | tokens gerados, incluindo raciocínio, pelo log do runtime |
| `prefill_hit` | reuso de cache reportado pelo runtime (média ou "n/a") |
| `claimed_done` | o agente disse que terminou com a verificação ainda falhando (`yes`/`no`) |
| `q_correct`, `q_scope`, `q_tests`, `q_clarity`, `q_process` | rubrica 1–5 abaixo |

Rubrica de qualidade (1 = ruim, 5 = ótimo):

- `q_correct`: o comportamento pedido está correto além do que os testes cobrem.
- `q_scope`: o agente mudou só o necessário. Mudanças fora do escopo tiram pontos.
- `q_tests`: o agente rodou os testes e leu o resultado antes de declarar conclusão.
- `q_clarity`: código e mensagem final são legíveis. Sem explicação inflada.
- `q_process`: o agente leu o código antes de editar, e usou as ferramentas em vez de adivinhar.

## Regra de decisão

Correção é eliminatória: um par sem `pass` em T1 e T5 sai. Entre os que passam, ordene por:

1. Soma de `first_try` nas tarefas T1, T2, T5, T7.
2. Menor `interventions` total.
3. Menor `wall_min` mediano.
4. Maior média de `q_process` e `q_scope`.
5. `claimed_done = yes` em qualquer run conta contra o par no desempate.

Não some as colunas num score único. Registre o veredito por sub-pergunta em `results/verdict.md`.

## Saídas

- `results/scorecard.csv` (uma linha por run, a partir do template).
- `results/notes.md` (falhas de setup, versões, anomalias).
- `results/verdict.md` (resposta às quatro sub-perguntas).
- `logs/<run-id>/` (transcripts; ignorado pelo git).

## Fora de escopo

- Benchmarks numéricos (LCB, T-Bench). Eles vivem nas campanhas próprias.
- Comparação de quantizações. O modelo × runtime está fixo por célula.
- Cline, Aider, Goose, OpenHands, Codex CLI. Entram só se um resultado das Fases A–C exigir.
- DeepSeek Harness. Developer preview com breaking changes; reavaliar na 0.1.0 estável. Se entrar,
  use o modo `Minimal` como par do Pi e o modo `Standard` como par do OpenCode.
