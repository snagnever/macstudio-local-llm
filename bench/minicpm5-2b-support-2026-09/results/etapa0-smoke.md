# Etapa 0 — smoke de runtime e parser (2026-09-15)

Decidir o runtime do modelo de suporte e confirmar que ele fala o suficiente para
a campanha. Sem driver no ar para carga/tempo; o driver do dia estava no ar
(idle) durante a validação funcional.

## Runtime: `optiq serve`, venv isolado

O `mlx_lm.server` 0.31.3 **não** tem parser para o formato de tool call do
MiniCPM5 (`<function name="..."><param name="...">`): `_infer_tool_parser` casa o
chat template por padrão e nenhum ramo reconhece esse formato.

O pacote `mlx-optiq` 0.5.8 (PyPI) resolve: importar `optiq` registra
`optiq/mlx_lm_patches/minicpm5_tools.py`, que estende `_infer_tool_parser` para
detectar `<function name="` + `<param name="` no template e devolver o parser
`minicpm5`. Instalado em:

```
~/.local/opt/minicpm5-support/venv   (Python 3.13.13, uv)
~/.local/opt/minicpm5-support/venv/bin/optiq serve
```

O ambiente do `mlx-serve` que serve o driver **não** foi tocado.

## Resultados funcionais

| Teste | s1 OptiQ-4bit | s2 8-bit |
|---|---|---|
| Carrega e responde | sim | sim |
| Tool call → `tool_calls` OpenAI | sim (`finish_reason: tool_calls`) | sim |
| `:no-think` suprime o reasoning | sim | sim |
| Carga do modelo no 1º request | < 1 s (modelo 1,8 GB) | 0,26 s (2,5 GB) |
| RSS do servidor carregado | 2,8 GB | 2,8 GB |

Tool call observado (idêntico nos dois, prompt em português, `:no-think`):

```json
"tool_calls": [{"id": "call_...", "type": "function",
  "function": {"name": "get_weather", "arguments": "{\"city\": \"Paris\"}"}}],
"finish_reason": "tool_calls"
```

## Achados que afetam o desenho

1. **O thinking vira o campo `reasoning`, não texto em `content`.** Com o modelo
   default ou `:think`, a resposta traz `message.reasoning` (e `content` com a
   resposta final). Com `:no-think` a chave `reasoning` some. Custo medido no
   mesmo prompt: **47 tokens** (`:no-think`) contra **105–112** (default/`:think`).
   Por isso a carga e a Etapa 3 usam sempre `:no-think`.
2. **`content` ainda carrega o XML cru** junto do `tool_calls` populado. Para um
   cliente que concatene `content` + `tool_calls`, isso duplica a chamada. É o
   comportamento do servidor, não um defeito da campanha; registrar como risco se
   o 2B for adotado para tool calls.
3. **`optiq serve` expõe `/v1/messages` (Anthropic) e `/v1/responses` (OpenAI)**
   além de `/v1/chat/completions`, e variantes `:think`/`:no-think`/`:precise`/
   `:creative` como ids de modelo.
4. **`--max-concurrent 1`**: o suporte fica com um slot, igual ao driver. Se o 2B
   fosse adotado com vários clientes, revisar; para esta campanha o interesse é o
   custo que ele impõe ao driver, não a fila dele.

## Reprodução

```
ssh vitor@mac-studio
~/.local/opt/minicpm5-support/venv/bin/optiq serve \
  --model ~/.cache/local-llms/minicpm5-2b-support/mlx-community-MiniCPM5-2B-OptiQ-4bit-d1392929adb5693640daeebe6b45e12a07a60b5a \
  --host 0.0.0.0 --port 11235 --max-concurrent 1
curl http://127.0.0.1:11235/v1/chat/completions -d '{"model":"<id>:no-think", ...}'
```

Launcher: `scripts/serve-support.sh s1|s2|s3`.
