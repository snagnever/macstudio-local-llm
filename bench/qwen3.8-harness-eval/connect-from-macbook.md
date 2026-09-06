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

| Alvo | Runtime | Porta | Bind atual | Tailscale direto |
|---|---|---:|---|---|
| `27b` (8-bit + DFlash2, arm S) | mlx-dspark 0.18.0 | 8484 | `0.0.0.0` | Sim |
| `fn` Flash-Next (mixed-4/8, arm FS) | mlx-serve 26.9.1 | 11234 | `0.0.0.0` | Sim, no ar desde 2026-09-05 |

O `27B` também já rodou em oMLX 0.6.4 arm T na porta 8000. Os launchers usam a 8484; veja a
"Divergência a resolver" em [plan.md](plan.md).

Os dois runtimes escutam em `0.0.0.0`, logo já são alcançáveis pelo tailnet. O `27B` foi
relançado com `OMLX_HOST=0.0.0.0`; a seção abaixo mostra o comando. `0.0.0.0` também
expõe na LAN; para restringir ao tailnet, use `OMLX_HOST=100.110.87.118`.

Model-ids (confirme sempre com `curl http://mac-studio:<porta>/v1/models` antes de
configurar o harness):

- `27b` (mlx-dspark, 8484): `mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9`
- `27b` (oMLX arm T, 8000): `Jundot-Qwen3.8-27B-oQ8e-mtp-c99e5aad8a478f71c10b9a3dde6709158b690da6`
- `fn` (mlx-serve, 11234): `ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd` — confirmado por `/v1/models` em 2026-09-05

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
curl -s http://mac-studio:8484/v1/models  | python3 -m json.tool   # 27b
curl -s http://mac-studio:11234/v1/models | python3 -m json.tool   # fn
```

## Configuração dos harnesses no MacBook

Os exemplos usam MagicDNS (`mac-studio`). Se o MagicDNS não resolver, troque por
`100.110.87.118`. O endpoint atual do `27B` é `http://mac-studio:8484` (mlx-dspark arm S),
model-id `mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9`.

**Config uma vez, launcher a cada run.** As edições abaixo são feitas uma vez por máquina.
Nos runs, não abra o harness à mão: use [macbook/](macbook/), que injeta o endpoint e o effort
sem tocar na config global. O alvo entra pelo nome do launcher (`run-<h>-27b.sh` ou
`run-<h>-fn.sh`, wrappers de `TARGET` sobre `run-<h>.sh`).
`EFFORT=<none|minimal|low|medium|high|xhigh>` (default `medium`); `RIG_HOST`, `RIG_PORT`,
`RIG_MODEL_ID` e `RIG_PROVIDER` trocam endpoint, modelo e entrada de provider.

| Harness | Binário | Versão instalada | Config persistente |
|---|---|---|---|
| `CC` Claude Code | `claude` | 2.1.236 | nenhuma; o launcher exporta as env |
| `OC` OpenCode | `opencode` | 1.18.20 | providers `rig` e `rigfn` em `~/.config/opencode/opencode.jsonc` |
| `QC` Qwen Code | `qwen` | 0.23.0 | `modelProviders.openai` (uma entrada por alvo) em `~/.qwen/settings.json` |
| `PI` Pi | `pi` | 0.85.1 | providers `rig` e `rigfn` em `~/.pi/agent/models.json` |
| `DSH` DeepSeek Harness | `dsh` | 0.1.0-rc.6 | providers `rig` e `rigfn` em `~/.dsh/settings.yaml` |

Um provider por porta: `rig` aponta para o `27b` (8484) e `rigfn` para o `fn` (11234). Cada modelo
declara as seis variantes de effort.

Instalação dos que faltarem: `npm i -g @earendil-works/pi-coding-agent` (Pi) e
`npm i -g @deepseek-ai/dsh@0.1.0-rc.6` (dsh; fixe a versão, é developer preview).

### OpenCode

Provider `rig` em `~/.config/opencode/opencode.jsonc`, com `reasoning`, `limit` e as três
variantes. O launcher `run-oc.sh` escolhe a variante do run (o TUI não tem `--variant`).

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
          "attachment": true,
          "tool_call": true,
          "modalities": { "input": ["text", "image"], "output": ["text"] },
          "limit": { "context": 131072, "output": 32768 },
          "variants": {
            "none": { "reasoningEffort": "none" },
            "minimal": { "reasoningEffort": "minimal" },
            "low": { "reasoningEffort": "low" },
            "medium": { "reasoningEffort": "medium" },
            "high": { "reasoningEffort": "high" },
            "xhigh": { "reasoningEffort": "xhigh" }
          }
        }
      }
    },
    "rigfn": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Mac Studio rig — Flash-Next (Tailscale)",
      "options": { "baseURL": "http://mac-studio:11234/v1" },
      "models": {
        "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd": {
          "name": "Qwen3.8-Flash-Next mixed-4/8 (rig FN, mlx-serve)",
          "reasoning": true,
          "attachment": true,
          "tool_call": true,
          "modalities": { "input": ["text", "image"], "output": ["text"] },
          "limit": { "context": 131072, "output": 32768 },
          "variants": {
            "none": { "reasoningEffort": "none" },
            "minimal": { "reasoningEffort": "minimal" },
            "low": { "reasoningEffort": "low" },
            "medium": { "reasoningEffort": "medium" },
            "high": { "reasoningEffort": "high" },
            "xhigh": { "reasoningEffort": "xhigh" }
          }
        }
      }
    }
  }
}
```

### Claude Code

O launcher `run-cc.sh` exporta as env, sem tocar em `~/.claude/settings.json`. O effort vai
em `CLAUDE_CODE_EFFORT_LEVEL`, que tem precedência sobre `/effort` e o settings.json. Não use
`/effort` na sessão: ele grava no settings.json do usuário.

Não há chave de capability no Claude Code: imagem é formato de wire, não configuração. O
`/v1/messages` do `fn` aceita blocos `type: "image"` (verificado em 2026-09-06).

### Qwen Code

O Qwen Code não tem "providers" nomeados como o OpenCode: cada endpoint é uma entrada do array
`modelProviders.openai` em `~/.qwen/settings.json`, e a chave da API vem de um nome de variável
declarado em `env` no próprio settings. Uma entrada por alvo, telemetria e usage stats desligadas:

```json
{
  "model": { "reasoningEffort": "medium", "name": "mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9", "baseUrl": "http://mac-studio:8484/v1" },
  "telemetry": { "enabled": false },
  "privacy": { "usageStatisticsEnabled": false },
  "env": {
    "QWEN_CUSTOM_API_KEY_OPENAI_HTTP_MAC_STUDIO_8484_V1_F083E8514C53": "local",
    "QWEN_CUSTOM_API_KEY_OPENAI_HTTP_MAC_STUDIO_11234_V1_FLASHNEXT": "local"
  },
  "modelProviders": {
    "openai": [
      {
        "id": "mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9",
        "baseUrl": "http://mac-studio:8484/v1",
        "envKey": "QWEN_CUSTOM_API_KEY_OPENAI_HTTP_MAC_STUDIO_8484_V1_F083E8514C53",
        "generationConfig": { "contextWindowSize": 131072, "modalities": { "image": true } }
      },
      {
        "id": "%s",
        "baseUrl": "http://mac-studio:11234/v1",
        "envKey": "QWEN_CUSTOM_API_KEY_OPENAI_HTTP_MAC_STUDIO_11234_V1_FLASHNEXT",
        "generationConfig": { "contextWindowSize": 131072, "modalities": { "image": true } }
      }
    ]
  }
}
```

O sufixo do `envKey` da primeira entrada foi gerado pelo próprio `qwen`; o da segunda foi escolhido
à mão. O nome é só uma chave de lookup: com `env` e `envKey` batendo, o `qwen -m <modelo>` resolve o
endpoint e a key sem env externa. Verificado em 2026-09-05 com o `fn` no ar.

O launcher `run-qc.sh` grava um settings de workspace no diretório do run com o effort. Ele
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
          "input": ["text", "image"],
          "contextWindow": 131072,
          "maxTokens": 32768
        }
      ]
    },
    "rigfn": {
      "baseUrl": "http://mac-studio:11234/v1",
      "api": "openai-completions",
      "apiKey": "local",
      "models": [
        {
          "id": "ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd",
          "name": "Qwen3.8 Flash-Next mixed-4/8 (rig FN, mlx-serve)",
          "reasoning": true,
          "input": ["text", "image"],
          "contextWindow": 131072,
          "maxTokens": 32768
        }
      ]
    }
  }
}
```

O launcher `run-pi.sh` passa o effort em `--thinking`.

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
          input: [text, image]
          reasoningEfforts:
            { none: none, minimal: minimal, low: low, medium: medium, high: high, xhigh: xhigh }
    rigfn:
      displayName: Mac Studio rig - Flash-Next (Tailscale)
      api: openai-completions
      baseURL: http://mac-studio:11234/v1
      apiKeyEnv: RIG_API_KEY
      models:
        - id: ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd
          input: [text, image]
          reasoningEfforts:
            { none: none, minimal: minimal, low: low, medium: medium, high: high, xhigh: xhigh }
```

O launcher `run-dsh.sh` reescreve a seção `agent-default-model` do settings com o modelo e o
effort do run. Ele fixa o effort na criação da sessão; o dsh não troca no meio. `DSH_PROFILE=web`
(default) abre a UI em `http://127.0.0.1:3080`; `DSH_PROFILE=headless` roda uma tarefa e sai.

## Imagem (visão)

Os dois alvos são vision-language. A capability precisa ser declarada em cada harness, senão
o cliente bloqueia o anexo antes de chamar o rig.

**Evidência.** O `model.safetensors.index.json` de cada build tem 333 tensores de visão:
`vision_tower/*` em `mlx-community/Qwen3.8-27B-8bit`, `model.visual/*` em
`ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit`. Os dois `config.json` trazem
`vision_config` com 27 camadas. A tag `text-generation` no card do `ddalcu` no HuggingFace
está errada.

**Teste no `fn` (2026-09-06).** Um PNG 8×8 vermelho enviado para `mac-studio:11234` voltou
`"red"` nos dois formatos:

```bash
# OpenAI: content[].type = image_url, url = data:image/png;base64,<...>
curl -s http://mac-studio:11234/v1/chat/completions -H 'Content-Type: application/json' -d @payload-openai.json
# Anthropic: content[].type = image, source.type = base64
curl -s http://mac-studio:11234/v1/messages -H 'anthropic-version: 2023-06-01' -d @payload-anthropic.json
```

**Chave por harness:**

| Harness | Onde | Chave |
|---|---|---|
| `OC` OpenCode | `~/.config/opencode/opencode.jsonc` | `attachment: true` + `modalities.input: ["text","image"]` |
| `QC` Qwen Code | `~/.qwen/settings.json` | `generationConfig.modalities.image: true` |
| `PI` Pi | `~/.pi/agent/models.json` | `input: ["text","image"]` |
| `DSH` DeepSeek Harness | `~/.dsh/settings.yaml` | `input: [text, image]` |
| `CC` Claude Code | — | nenhuma; o wire carrega a imagem |

Sem a chave, o Pi responde "[Current model does not support images]" e o Qwen Code encaminha
a imagem ao *vision bridge* (`settings.visionModel`), que transcreve em vez de passar a
imagem. Com a chave, os dois enviam o bloco de imagem direto ao rig.

### Vídeo: não use

O checkpoint anuncia vídeo, mas o runtime descarta. Testei quatro formatos de payload contra
`mac-studio:11234` em 2026-09-06 com um MP4 de 1 s gerado por `ffmpeg`:

| Payload | `prompt_tokens` | Resposta |
|---|---:|---|
| `image_url` com PNG (**controle**) | 27 | `red`, correta |
| `video_url` com `data:video/mp4` | 21 | `Black`, chute |
| `video` com lista de frames PNG | 21 | `Error` |
| `video` com string `data:video/mp4` | 18 | `Blue`, chute |
| `image_url` com `data:video/mp4` | 18 | `White`, chute |

O controle de imagem soma 6 tokens de visão ao prompt. Nenhuma forma de vídeo soma nada: o
mlx-serve 26.9.1 remove a parte e responde só com o texto. Declarar vídeo no harness faz o
cliente mandar bytes que o rig joga fora, e a resposta parece válida — pior que uma recusa.

Nenhum dos harnesses da matriz ajuda aqui, de qualquer modo:

| Harness | Modalidade de vídeo |
|---|---|
| `OC` OpenCode | campo existe (`modalities.input: ["video"]`), mas não achei caminho que anexe vídeo; o paste só trata `image/png` e texto |
| `QC` Qwen Code | campo existe (`generationConfig.modalities.video`) |
| `PI` Pi | não; o schema aceita só `text` e `image` |
| `DSH` DeepSeek Harness | não; `MODALITIES` do plugin é `{text, image}` |
| `CC` Claude Code | não; o wire Anthropic não tem bloco de vídeo |

**Não verificado.** O endpoint do `27b` (mlx-dspark, 8484) estava fora em 2026-09-06, então o
caminho de imagem dele não foi testado — só os pesos confirmam a visão. Não testei vídeo no
`27b` nem em outro runtime além do mlx-serve.

## O harness travou: o servidor está gerando ou o socket morreu?

Rode a sonda no MacBook. Ela amostra as métricas do runtime e os sockets das duas
pontas em paralelo, e responde em uma linha:

```bash
TARGET=fn bench/qwen3.8-harness-eval/scripts/rig-probe.sh
```

```
endpoint  mac-studio:11234 (fn)
state     GENERATING   running=1 prefilling=0 cancelled_total=3
rate      decode 64 tok/s   prefill 0 tok/s   (over 6s)
sockets   client [65429]  server [65429]
log       +0 lines in 6s
last        <- 44284+123 tokens streamed [... decode: 45.5 tok/s] [tool_calls]
verdict   server is working — the client display is behind
```

Os quatro estados:

| `state` | Significado | Ação |
|---|---|---|
| `GENERATING` | O contador `generation_tokens_live` sobe. O modelo emite tokens (o bloco de raciocínio conta). | Esperar. O "prefill" do harness só atrasou. |
| `PREFILLING` | `requests_prefilling` > 0 e `prefill_tokens_live` sobe. | Esperar; 38k tokens a 270 tok/s levam ~140 s. |
| `STALLED` | O servidor segura a requisição mas nenhum token saiu na janela. | Observar; o `--timeout` do mlx-serve aborta em 300 s sem token. |
| `IDLE` + `HALF-OPEN` | O cliente tem um socket que o servidor não tem mais. | Cancelar e reenviar. O cliente esperaria para sempre. |

Use `--no-ssh` quando não houver acesso ao rig; a sonda então mostra só as métricas e o
socket local, e não detecta o meio-aberto.

### Por que trava

O caminho TCP entre MacBook e rig quebra no meio do stream. O servidor percebe na próxima
escrita, encerra a requisição com `[client_disconnect]` e libera o slot. O cliente só lê,
não tem read timeout nem keepalive, e fica bloqueado exibindo "prefill" indefinidamente.
Em 2026-09-06 o log do `fn` acusava 15 `[client_disconnect]` em ~300 requisições (5%).

### O log do servidor

O mlx-serve já grava tudo em `~/.mlx-serve/logs/mlx-serve-<porta>.log` por padrão. Não é
preciso ligar debug. O que interessa:

```bash
ssh vitor@mac-studio "grep -o 'tokens streamed .*' ~/.mlx-serve/logs/mlx-serve-11234.log | grep -o '\[[a-z_]*\]$' | sort | uniq -c"
```

`[stop]`, `[tool_calls]` e `[length]` são finais normais; `[client_disconnect]` e
`[scheduler] prefill aborted: client disconnected` são a quebra de caminho. `Request
timeout: 300s` no log é a linha de banner do startup, não um evento — não confunda.

O log não tem timestamp por linha. Para correlacionar com o relógio, use o crescimento do
arquivo que a sonda reporta, ou relance o servidor com a saída passando por `ts`.

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
