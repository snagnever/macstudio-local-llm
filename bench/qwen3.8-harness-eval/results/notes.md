# Notas de execução

## 2026-09-05 — Fase 0 (smoke do endpoint), modelo 27B

### Desvio de runtime em relação ao plano

O plano previa o `27B` no **oMLX arm T (oQ8e-mtp) porta 8000**. No momento do teste o rig
servia o `27B` no **mlx-dspark arm S (MLX 8-bit + DFlash2) porta 8484**. Não dá para subir
os dois modelos ao mesmo tempo (128 GB), então rodamos o `27B` primeiro, no runtime que
estava de pé. Registrar `runtime=mlx-dspark`, `arm=S` no scorecard, não oMLX.

| Item | Valor |
|---|---|
| Endpoint | `http://mac-studio:8484` (Tailscale) |
| model-id | `mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9` |
| Quant | MLX 8-bit + DFlash2 (drafter) |
| OpenAI `/v1/chat/completions` | tool call OK (`finish: tool_calls`) |
| Anthropic `/v1/messages` | tool call OK (`stop: tool_use`, com bloco `thinking`) |

### Resultado do smoke (listar arquivos → ler README → primeiro cabeçalho)

| Par | Resultado | Wall | Observação |
|---|---|---|---|
| `27B × OC` (OpenCode) | **passa** | ~44 s | chamou `Read` + `ls`, respondeu o cabeçalho certo |
| `27B × CC` (Claude Code) | **passa** | ~95 s | via launcher `run-cc-27b.sh`; aviso de janela corrigido com `CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072` |
| `FN × *` | pendente | — | `FN` não está de pé (um modelo por vez); roda depois de trocar no rig |

### Ferramentas do cliente (MacBook)

- OpenCode 1.17.15 — provider `rig` adicionado ao `~/.config/opencode/opencode.jsonc` (backup salvo).
- Claude Code 2.1.228 — não altera `~/.claude/settings.json`; usa `macbook/run-cc-27b.sh`.
- Qwen Code (`qwen`): AUSENTE no MacBook. Instalar antes da Fase B (par `QC`).
- Pi (`pi`): AUSENTE. Opcional; instalar só se o prefill dominar.

### Gate da Fase 0

Os pares do `27B` (CC e OC) fecham o loop de tool call. Gate aberto só para o `FN`, que
depende de trocar o modelo no rig. Seguimos a Fase A com o `27B` no OpenCode.

## 2026-09-05 — thinking budget (effort) em todos os harnesses

Decisão: todo harness da matriz seleciona o effort do run pela env `EFFORT` do launcher em
`macbook/`. O Qwen Code (`QC`) e o DeepSeek Harness (`DSH`) entraram na matriz.

### Versões instaladas (MacBook)

- Claude Code 2.1.236 · OpenCode 1.18.20 · Qwen Code 0.23.0 · Pi 0.85.1 · dsh 0.1.0-rc.6.
- `qwen`, `pi` e `dsh` foram instalados via npm. O `dsh` fica fixo em `0.1.0-rc.6` (developer
  preview com breaking changes).

### Campo de effort no wire (verificado com servidor de captura, `EFFORT=low`)

| Harness | Campo no corpo | Honrado pelo mlx-dspark? |
|---|---|---|
| `CC` | `output_config.effort` (+ `thinking: adaptive`) | sim (sonda `/v1/messages`) |
| `OC` | `reasoning_effort` | sim (sonda `/v1/chat/completions`) |
| `QC` | `reasoning.effort` nativo **+** `reasoning_effort` via `extra_body` | só o segundo |
| `PI` | `reasoning_effort` | sim |
| `DSH` | `reasoning_effort` | sim |

Duas descobertas que mudaram a config:

- **O rig ignora `reasoning.effort` aninhado.** Sonda direta ao mlx-dspark: `reasoning:{effort:low}`
  gerou 5.907 tokens (igual ao default `xhigh`), enquanto `reasoning_effort:low` deu 345. Por isso
  `run-qc-27b.sh` escreve `generationConfig.extra_body.reasoning_effort` além de `model.reasoningEffort`.
- **O Claude Code envia `output_config.effort` mesmo com model-id local desconhecido.** O aviso
  `unrecognized_model` não bloqueia o campo. Responde à dúvida original sobre gating por nome.
- Baseline sem campo = default `xhigh` (o `prompt_tokens` bate). "Não configurar" é o effort caro.

### Configs persistentes alteradas (MacBook, fora do repo)

- `~/.config/opencode/opencode.jsonc`: modelo `rig` ganhou `reasoning`, `limit` e variantes
  `low/medium/xhigh`. Backup `opencode.jsonc.bak-<ts>`.
- `~/.qwen/settings.json`: criado com telemetria e usage stats off, `contextWindowSize` 131072.
- `~/.pi/agent/models.json`: criado com o provider `rig` (`baseUrl` `mac-studio:8484`).
- `~/.dsh/settings.yaml`: seção `llm-pi-ai` com o provider `rig`. Backup `settings.yaml.bak-<ts>`.

### Launchers

`macbook/run-{cc,oc,qc,pi,dsh}-27b.sh` sobre `macbook/lib.sh`. Contrato travado em
`tests/test_macbook_launchers.sh` (passa). Cada launcher rejeita `EFFORT` fora de low/medium/xhigh.
