# Preflight

Data: 2026-11-13. MacBook `VitorMBPro2026`; rig Mac Studio M4 Max 128 GB.

## Versões (MacBook)

| harness | versão | modo não interativo |
|---|---|---|
| Claude Code | 2.1.302 | `claude -p` |
| OpenCode | 1.18.31 | `opencode run` |
| DeepSeek Harness | 0.1.0-rc.6 | `dsh --profile headless` |
| Pi | 0.85.1 | `pi -p` |

## Isolamento

Cada harness rodou `--version` com `HOME`, `XDG_*`, `CLAUDE_CONFIG_DIR` e `DSH_HOME` apontando para um diretório temporário e sem as variáveis do shell.

- Os 4 respondem com a versão.
- O OpenCode cria `.config/opencode`, `.local/share/opencode`, `.local/state/opencode` e `.cache/opencode` dentro do `HOME` temporário.
- O `dsh` e o `pi` iniciam por um shim do `mise`, que cria `.cache/mise` e `.local/state/mise` dentro do `HOME` temporário.
- O `mtime` de `~/.claude`, `~/.config/opencode`, `~/.dsh` e `~/.pi` não mudou.

## Ferramentas das sessões

O `python3` do MacBook não tem `pytest`. As tarefas T1 e T7 pedem ao modelo que rode os testes. As 4 sessões recebem no começo do `PATH` um virtualenv compartilhado, `logs/toolenv`, com `pytest`. Criação: `uv venv logs/toolenv && uv pip install --python logs/toolenv/bin/python pytest`. A fila roda com `HARNESS_TOOLS_BIN=<campanha>/logs/toolenv/bin`.

## Mudança de 13/11: os harnesses rodam no rig

As seções acima descrevem o MacBook. O rig tem `claude` 2.1.292 e `opencode` 1.15.10; `pi` e `dsh` ainda não estão instalados lá. O preflight do rig repete as versões, o isolamento e o virtualenv de ferramentas.

## Sandbox

Com o perfil do `sandbox-exec`, os 4 harnesses respondem `--version` no MacBook, e o check de T5 (cria o virtualenv e roda `make check`) passa dentro do sandbox.

## Pendente (precisa do rig livre)

- Portão: veredito de velocidade do `z4h`.
- Instalar `pi` e `dsh` no rig.
- Rede: `/v1/models`, `/v1/chat/completions` e `/v1/messages` em `127.0.0.1`.
- Smoke: cada harness fecha a tarefa b contra o `k2`.
- Servidor fora: cada harness termina no limite.
