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
