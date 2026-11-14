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

## Preflight do rig (2026-11-14)

**Portão.** A regra "Velocidade" da swift-uncensored reprova o `z4h` e o `z2h` com a mesma razão, 1.051 a 128K ([etapa2-um-stream.md](../../swift-uncensored-2026-11/results/etapa2-um-stream.md)). A troca pelo `z2` não melhora a velocidade. O segundo peso fica o `z4`.

**Versões e smoke.** Cada harness roda a tarefa b contra o `k2`, a 131072, dentro do sandbox.

| harness | versão no rig | tarefa b | wall | servidor fora (limite de 120 s) |
|---|---|---|---:|---|
| Claude Code | 2.1.292 | cumprida | 25.3 s | para no limite |
| OpenCode | 1.15.10 | cumprida | 30.8 s | para no limite |
| DeepSeek Harness | 0.1.0-rc.6 | cumprida | 63.3 s | sai com erro em 15.7 s |
| Pi | 0.85.1 | cumprida | 29.8 s | sai com erro em 14.2 s |

Com o servidor fora, nenhuma sessão conta como cumprida nem como `claimed_done`.

**Rede.** `/v1/models`, `/v1/chat/completions` e `/v1/messages` respondem em `127.0.0.1:8585`.

**Ajustes que o smoke pediu.**

- Cada cópia de sessão recebe um `git init`. Sem isso o OpenCode procura a raiz git acima da cópia e tenta gravar `.opencode` no repositório da campanha; o sandbox bloqueia e a sessão sai com erro.
- O `npm i -g @deepseek-ai/dsh@0.1.0-rc.6` no rig resolve dependências mais novas (`cordis` 4.1.0), e o boot falha com "user patch-layer watching requires the Cordis HMR service". A instalação do rig é uma cópia da árvore do MacBook (`cordis` 4.0.2). A árvore do npm fica em `~/.local/lib/node_modules/@deepseek-ai/dsh.npm-floating`.
- O `dsh` abre um `sandbox-exec` próprio para o bash, e o macOS recusa um sandbox dentro de outro. A sessão passa `DSH_PERMISSION_MODE=danger-full-access`; o sandbox da sessão é o limite.
- O `pi` veio do `npm i -g @earendil-works/pi-coding-agent@0.85.1`, sem ajuste.

**Ferramentas.** O virtualenv `logs/toolenv` do rig tem Python 3.13 e pytest 9.2.0. A fila roda com esse Python e com `HARNESS_TOOLS_BIN`.

**Não verificado.** O OpenCode do rig é o 1.15.10; o do MacBook é o 1.18.31. O smoke cobre só a tarefa b.
