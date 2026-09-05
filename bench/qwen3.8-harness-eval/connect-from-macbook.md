# Conectar o MacBook ao Mac Studio para os testes de harness

Este documento explica como o MacBook M4 (cliente) conecta no Mac Studio (rig) para
rodar os harnesses da campanha [plan.md](plan.md). O rig serve os modelos. O MacBook
roda o OpenCode, o Claude Code e o Qwen Code, e aponta cada um para um endpoint do rig.

O caminho recomendado é o **Tailscale**, porque o MacBook é móvel e o Tailscale funciona
em qualquer rede, com tráfego cifrado e sem expor os modelos na LAN.

## Topologia

| Papel | Máquina | Tailscale | LAN |
|---|---|---|---|
| Rig | Mac Studio (`mac-studio`) | `100.110.87.118` / MagicDNS `mac-studio` | `192.168.68.123` |
| Cliente | MacBook M4 32 GB (`vitormbpro2026`) | no mesmo tailnet `snagnever@` | — |

Usuário de login no rig: `vitor`. Tailnet: `mac-studio.tail8b1572.ts.net`.

## Endpoints no rig

| Modelo | Runtime | Porta | Bind atual | Tailscale direto |
|---|---|---:|---|---|
| `27B` denso (oQ8e-mtp, arm T) | oMLX 0.6.4 | 8000 | `0.0.0.0` | Sim, agora |
| `FN` Flash-Next (mixed-4/8, arm FS) | mlx-serve 26.8.11 | 11234 | `0.0.0.0` | Sim, agora |

Os dois runtimes escutam em `0.0.0.0`, logo já são alcançáveis pelo tailnet. O `27B` foi
relançado com `OMLX_HOST=0.0.0.0`; a seção abaixo mostra o comando. `0.0.0.0` também
expõe na LAN; para restringir ao tailnet, use `OMLX_HOST=100.110.87.118`.

Model-ids (confirme sempre com `curl http://mac-studio:<porta>/v1/models` antes de
configurar o harness):

- `27B`: `Jundot-Qwen3.8-27B-oQ8e-mtp-c99e5aad8a478f71c10b9a3dde6709158b690da6`
- `FN`: retornado por `/v1/models` na porta 11234. Repositório
  `ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit`. Confirme o id exato com o `FN` no ar.

## Pré-requisitos

1. **Tailscale nas duas máquinas.** O rig está online. Confirme o MacBook com
   `tailscale status` (procure `mac-studio` na lista, estado online).
2. **MagicDNS.** O nome `mac-studio` resolve dentro do tailnet. Se não resolver, use o IP
   `100.110.87.118`.

Não é preciso ligar o Login Remoto nem abrir o firewall da LAN para o método Tailscale.

## Expor o `27B` no tailnet

O oMLX lê a variável `OMLX_HOST`. O `27B` já foi relançado no rig com `OMLX_HOST=0.0.0.0`,
que escuta em todas as interfaces (Tailscale e LAN). Comando usado:

```bash
OMLX_HOST=0.0.0.0 \
OMLX_MODEL_ROOT="$HOME/.cache/local-llms/qwen3.8-prefix-cache" \
QWEN38_OMLX_EXPECTED_VERSION=0.6.4 \
bash bench/qwen3.8-prefix-cache/scripts/run-omlx.sh T
```

Para restringir o `27B` ao tailnet e não expô-lo na LAN, troque por
`OMLX_HOST=100.110.87.118`.

O `FN` já binda `0.0.0.0` no `run-mlx-serve.sh`. Para restringi-lo ao tailnet, troque
`--host 0.0.0.0` por `--host 100.110.87.118` no launcher.

## Smoke da conexão (no MacBook)

Confirme que cada endpoint responde pelo tailnet antes de abrir o harness.

```bash
curl -s http://mac-studio:8000/v1/models  | python3 -m json.tool   # 27B
curl -s http://mac-studio:11234/v1/models | python3 -m json.tool   # FN
```

## Configuração dos harnesses no MacBook

Os exemplos usam MagicDNS (`mac-studio`). Se o MagicDNS não resolver, troque por
`100.110.87.118`. O endpoint atual do `27B` é `http://mac-studio:8484` (mlx-dspark arm S),
model-id `mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9`.

**Config uma vez, launcher a cada run.** As edições abaixo são feitas uma vez por máquina.
Nos runs, não abra o harness à mão: use [macbook/](macbook/), que injeta o endpoint e o effort
sem tocar na config global. `EFFORT=<low|medium|xhigh>`, `RIG_HOST`/`RIG_PORT` trocam o endpoint.

| Harness | Binário | Versão instalada | Config persistente |
|---|---|---|---|
| `CC` Claude Code | `claude` | 2.1.236 | nenhuma; o launcher exporta as env |
| `OC` OpenCode | `opencode` | 1.18.20 | provider `rig` em `~/.config/opencode/opencode.jsonc` |
| `QC` Qwen Code | `qwen` | 0.23.0 | `~/.qwen/settings.json` (telemetria off) |
| `PI` Pi | `pi` | 0.85.1 | provider `rig` em `~/.pi/agent/models.json` |
| `DSH` DeepSeek Harness | `dsh` | 0.1.0-rc.6 | provider `rig` em `~/.dsh/settings.yaml` |

Instalação dos que faltarem: `npm i -g @earendil-works/pi-coding-agent` (Pi) e
`npm i -g @deepseek-ai/dsh@0.1.0-rc.6` (dsh; fixe a versão, é developer preview).

### OpenCode

Provider `rig` em `~/.config/opencode/opencode.jsonc`, com `reasoning`, `limit` e as três
variantes. O launcher `run-oc-27b.sh` escolhe a variante do run (o TUI não tem `--variant`).

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "rig": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Mac Studio rig (Tailscale)",
      "options": { "baseURL": "http://mac-studio:8484/v1" },
      "models": {
        "mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9": {
          "name": "Qwen3.8-27B 8bit (rig, dspark)",
          "reasoning": true,
          "limit": { "context": 131072, "output": 32768 },
          "variants": {
            "low": { "reasoningEffort": "low" },
            "medium": { "reasoningEffort": "medium" },
            "xhigh": { "reasoningEffort": "xhigh" }
          }
        }
      }
    }
  }
}
```

### Claude Code

O launcher `run-cc-27b.sh` exporta as env, sem tocar em `~/.claude/settings.json`. O effort vai
em `CLAUDE_CODE_EFFORT_LEVEL`, que tem precedência sobre `/effort` e o settings.json. Não use
`/effort` na sessão: ele grava no settings.json do usuário.

### Qwen Code

`~/.qwen/settings.json` com telemetria e usage stats desligadas:

```json
{
  "model": { "reasoningEffort": "medium", "generationConfig": { "contextWindowSize": 131072 } },
  "telemetry": { "enabled": false },
  "privacy": { "usageStatisticsEnabled": false }
}
```

O launcher `run-qc-27b.sh` grava um settings de workspace no diretório do run com o effort. Ele
escreve `model.reasoningEffort` **e** `generationConfig.extra_body.reasoning_effort`. O segundo é
necessário: o rig ignora o `reasoning.effort` aninhado que o Qwen Code envia por padrão.

### Pi

`~/.pi/agent/models.json`. Para servidor local só o `id` é obrigatório por modelo:

```json
{
  "providers": {
    "rig": {
      "baseUrl": "http://mac-studio:8484/v1",
      "api": "openai-completions",
      "apiKey": "local",
      "models": [
        {
          "id": "mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9",
          "name": "Qwen3.8 27B 8bit (rig, dspark)",
          "reasoning": true,
          "contextWindow": 131072,
          "maxTokens": 32768
        }
      ]
    }
  }
}
```

O launcher `run-pi-27b.sh` passa o effort em `--thinking`.

### DeepSeek Harness

Provider `rig` na seção `llm-pi-ai` de `~/.dsh/settings.yaml`. A key vem da env `RIG_API_KEY`
(o launcher exporta `local`):

```yaml
llm-pi-ai:
  providers:
    rig:
      displayName: Mac Studio rig (Tailscale)
      api: openai-completions
      baseURL: http://mac-studio:8484/v1
      apiKeyEnv: RIG_API_KEY
      models:
        - id: mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9
          reasoningEfforts: { low: low, medium: medium, xhigh: xhigh }
```

O launcher `run-dsh-27b.sh` reescreve a seção `agent-default-model` do settings com o modelo e o
effort do run. Ele fixa o effort na criação da sessão; o dsh não troca no meio. `DSH_PROFILE=web`
(default) abre a UI em `http://127.0.0.1:3080`; `DSH_PROFILE=headless` roda uma tarefa e sai.

## Alternativa — túnel SSH (rede sem Tailscale)

Se o MacBook não estiver no tailnet, use um túnel SSH. Exige Login Remoto ligado no rig
(Ajustes do Sistema → Geral → Compartilhamento → Login Remoto; hoje está desligado).

```bash
ssh -N -L 8000:127.0.0.1:8000 -L 11234:127.0.0.1:11234 vitor@192.168.68.123
```

Com o túnel aberto, os endpoints no MacBook são `http://127.0.0.1:8000` e `:11234`.
Este método dispensa relançar o oMLX, porque tunela o loopback.

## Segurança

O token é `local`. Ligar ao IP Tailscale (`OMLX_HOST=100.110.87.118`) mantém o modelo
dentro do tailnet. `OMLX_HOST=0.0.0.0` também expõe na LAN. O `FN` hoje binda `0.0.0.0`;
restrinja ao tailnet se a LAN não for confiável.

## Follow-ups

1. Confirmar o model-id do `FN` com `/v1/models` na porta 11234 quando o `FN` subir.
2. Opcional: restringir `27B` e `FN` ao tailnet (`OMLX_HOST=100.110.87.118` no oMLX,
   `--host 100.110.87.118` no `run-mlx-serve.sh`) se a LAN não for confiável.
