# 2026-09-05 — Hermes Agent no Mac Studio: handoff de instalação e smoke por provider

> **Status:** aberto. **Executor:** um agente que roda **no Mac Studio** (shell local, não SSH).
> **Pesquisa de base:** seção [Referências](#referências). **Artefatos:** `bench/harness-matrix/`
> (harness `hermes`), conforme [bench/harness-matrix/plan.md](../harness-matrix/plan.md).

## Pergunta

O Hermes Agent fecha um loop de tool call no rig com cada um dos três providers, e com quanto
trabalho de configuração?

| Provider | Rota | Custo extra | Suporte oficial |
|---|---|---|---|
| Local | `custom` → LM Studio `http://localhost:1234/v1` | zero | sim |
| ChatGPT | `openai-codex` (OAuth device-code) | zero, usa cota da assinatura | sim, cota por plano não documentada |
| Claude | `anthropic` com `ANTHROPIC_API_KEY` | pay-per-token | sim |

A assinatura Claude Pro/Max **fica fora do plano**. O OAuth do Hermes envia para
`api.anthropic.com/v1/messages` e consome só créditos de "extra usage". A Anthropic não permite
que terceiros usem credenciais Pro/Max. O risco é restrição da conta.

## Regras para o agente executor

1. Não digite senhas, tokens ou API keys em nenhum prompt. Quando um passo pedir login no
   browser ou uma key, **pare e peça ao usuário**. Retome depois que ele confirmar.
2. Não instale um segundo servidor de modelos (Ollama, llama.cpp). O rig usa LM Studio + MLX.
3. Não mude o modelo carregado no LM Studio sem registrar em `results/notes.md` o modelo anterior.
4. Registre cada comando que falhou, com a saída, em `bench/hermes-eval/results/notes.md`.
5. Cada fase tem um gate. Não avance com o gate aberto.

## Fase 0 — pré-checagem do rig (10 min)

```bash
hostname                      # esperado: macstudio
git --version                 # único pré-requisito do instalador
curl -s http://localhost:1234/v1/models | head -c 600
```

Registre o `id` exato que `GET /v1/models` retorna. Use esse string nas configs. O alvo é
`qwen/qwen3-coder-next`, o modelo de agente do rig
([docs/local-llm-reference.md](../../docs/local-llm-reference.md), "Recommended Stack").

Se o servidor não responde: `lms server start`, depois `lms load qwen/qwen3-coder-next`. Confirme
no LM Studio que o **Context Length** do modelo está em **≥ 65536**. O Hermes gasta contexto com
memória e skills; 4k–32k quebra o loop.

Se o LM Studio exige API key no servidor, anote isso. A config da Fase 2 recebe a key pelo
usuário.

Gate: `GET /v1/models` retorna o modelo alvo.

## Fase 1 — instalar o Hermes (15 min)

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.zshrc
hermes --version
```

O instalador coloca o código em `~/.hermes/hermes-agent/` e um symlink em
`~/.local/bin/hermes`. Ele instala Python 3.11 (via uv), Node 26, ripgrep e ffmpeg.

Não instale o Hermes Desktop nesta rodada. O CLI basta para o smoke.

Se `hermes` não está no PATH após `source ~/.zshrc`, rode `export PATH="$HOME/.local/bin:$PATH"`
e registre em `notes.md`.

Gate: `hermes --version` imprime uma versão. Registre a versão em `notes.md`.

## Fase 2 — provider local (LM Studio) (15 min)

Escreva `~/.hermes/config.yaml`. Se o arquivo já existe, edite só as chaves abaixo.

```yaml
providers:
  macstudio:
    api: http://localhost:1234/v1
    # key_env: LMSTUDIO_API_KEY   # descomente só se o LM Studio exige key

model:
  provider: custom:macstudio
  default: qwen/qwen3-coder-next   # use o id exato da Fase 0
  context_length: 65536
```

Se a key for necessária, o usuário a grava em `~/.hermes/.env` como `LMSTUDIO_API_KEY=...`.

Smoke (mesmo prompt do plano Qwen3.8, para comparação):

```bash
mkdir -p /tmp/hermes-smoke && cp README.md /tmp/hermes-smoke/ && cd /tmp/hermes-smoke
hermes
```

Envie: `List the files in this directory, then read README.md and tell me its first heading.`

Registre em `notes.md`:

- o Hermes chamou uma ferramenta de shell ou leitura?
- o modelo leu o arquivo e respondeu o heading correto?
- tempo de parede do turno
- `tokens_in` / `tokens_out` do log do LM Studio

Gate: o loop fecha com o heading correto. Se o modelo responde em texto sem chamar ferramenta,
o problema é tool calling. Verifique o Context Length e o template do modelo antes de trocar de
modelo.

## Fase 3 — provider ChatGPT (`openai-codex`) (10 min + login do usuário)

```bash
hermes auth add openai-codex
```

O comando imprime uma URL e um código. **Pare aqui.** Peça ao usuário para abrir a URL, entrar
com a conta ChatGPT e digitar o código. Retome quando ele confirmar. A credencial fica em
`~/.hermes/auth.json`. Se `~/.codex/auth.json` já existe, o Hermes importa sem novo login.

Depois do login, troque de provider em sessão e repita o smoke da Fase 2:

```
/model openai-codex
```

Escolha o modelo que o wizard lista. Registre o modelo e o plano ChatGPT do usuário (Plus, Pro,
Team) em `notes.md`. A doc do Hermes não documenta quais planos são elegíveis nem como o uso conta
na cota do Codex.

Não ative `/codex-runtime codex_app_server` nesta rodada. Esse modo delega o loop ao Codex CLI e
remove as tools `delegate_task`, `memory`, `session_search` e `todo`.

Gate: o loop fecha com o heading correto. Se o login falha com `invalid_grant`, rode
`hermes auth add openai-codex` de novo.

## Fase 4 — provider Claude (`anthropic` + API key) (10 min + key do usuário)

**Pare aqui.** Peça ao usuário para gravar a key em `~/.hermes/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Não peça a key no chat. Retome quando ele confirmar. Depois:

```bash
hermes chat --provider anthropic --model claude-opus-5
```

Repita o smoke da Fase 2. Registre o custo do turno pelo console da Anthropic, se o usuário
fornecer.

Se o usuário prefere não usar API key, marque a Fase 4 como **pulada** em `notes.md` e siga
para a Fase 5. Não tente o OAuth Anthropic. Não use credenciais do Claude Code
(`~/.claude/`).

Gate: o loop fecha com o heading correto, ou a fase está marcada como pulada.

## Fase 5 — registrar no harness-matrix (15 min)

Para cada provider que passou o gate, crie um verdict em
`bench/harness-matrix/results/hermes/<modelo>.md`, seguindo
[bench/harness-matrix/plan.md](../harness-matrix/plan.md). Nome do modelo:

- local: id do LM Studio com `/` → `-` (ex.: `qwen-qwen3-coder-next`)
- ChatGPT: `openai-codex-<modelo>`
- Claude: `anthropic-claude-opus-5`

Cada verdict traz: versão do Hermes, provider, modelo, context_length, prompt do smoke,
resultado, tempo de parede, tokens, e o link para o raw em
`bench/harness-matrix/logs/hermes/<modelo>/`. Copie a sessão do Hermes para o raw dir
(`~/.hermes/` guarda as sessões; localize com `hermes --help` ou `ls ~/.hermes`).

## Saídas

- `bench/hermes-eval/results/notes.md` — log de execução, falhas, versões, decisões.
- `bench/harness-matrix/results/hermes/<modelo>.md` — um verdict por provider aprovado.
- `bench/harness-matrix/logs/hermes/<modelo>/` — raw (gitignorado).

Ao terminar, escreva em `notes.md` um bloco **Resumo** com uma linha por provider:
`passou | falhou | pulado`, e o trabalho gasto em minutos.

## Rollback

```bash
rm -rf ~/.hermes ~/.local/bin/hermes
```

Isso remove o Hermes, a config e as credenciais OAuth. Não remove uv, Node, ripgrep ou ffmpeg.

## Fora de escopo

- Hermes Desktop (app).
- Modo `codex_app_server`.
- OAuth Anthropic (Pro/Max).
- Gateways de mensagem (Telegram, Discord).
- Tarefas T1–T7 do plano Qwen3.8. Só o smoke, nesta rodada.

## Referências

- [LLM and Model Providers | Hermes Agent](https://hermes-agent.nousresearch.com/docs/integrations/providers)
- [Installation | Hermes Agent](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
- [Codex App-Server Runtime | Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/codex-app-server-runtime)
- [Issue #40014 — Claude Max OAuth consome extra usage](https://github.com/NousResearch/hermes-agent/issues/40014)
- [Issue #48320 — provider `claude -p` (fechado como duplicado)](https://github.com/NousResearch/hermes-agent/issues/48320)
- [docs/local-llm-reference.md](../../docs/local-llm-reference.md) — endpoint e modelos do rig
- [bench/qwen3.8-harness-eval/plan.md](../qwen3.8-harness-eval/plan.md) — prompt do smoke (Fase 0)
