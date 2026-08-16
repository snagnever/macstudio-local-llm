# Design: prevenção de segredos no repositório

Data: 2026-08-15
Status: aprovado (aguardando revisão do spec)

## Problema

O repositório é público (`github.com/snagnever/macstudio-local-llm`). Um segredo
commitado (chave de API, token, credencial) fica exposto e permanece no
histórico git mesmo após remoção. É preciso bloquear segredos antes que entrem
no histórico local e no remoto.

## Objetivo

Impedir que segredos cheguem ao histórico git, com verificação em dois pontos:
o commit local e o servidor (push/PR).

## Não-objetivo

- Remover segredos do histórico existente (só entra em escopo se o scan inicial
  achar algo; nesse caso, para e reporta).
- Escanear pesos de modelo ou logs de benchmark (já ignorados no `.gitignore`).

## Decisões

- **Scanner:** `gitleaks`. Binário único, rápido, mesmo motor no hook e no CI.
- **Cobertura:** hook local (`pre-commit`) + GitHub Actions.
- **Mecanismo do hook:** framework `pre-commit` com `.pre-commit-config.yaml`
  versionado.

## Componentes

| Componente | Arquivo | Função |
| --- | --- | --- |
| Config do scanner | `.gitleaks.toml` | Regras e allowlist de falsos-positivos |
| Hook local | `.pre-commit-config.yaml` | Roda `gitleaks` nos arquivos em stage |
| CI | `.github/workflows/secret-scan.yml` | Escaneia cada `push` e `pull_request` |
| Doc | `README.md` / `AGENTS.md` | Instrui `pre-commit install` após clone |

## Fluxo

1. **Local:** `git commit` dispara o `pre-commit`, que roda `gitleaks` apenas
   nos arquivos em stage. Se achar um segredo, o commit falha com arquivo e
   linha.
2. **Remoto:** cada `push`/`pull_request` dispara o Actions, que escaneia o
   diff. Serve de rede de segurança contra `git commit --no-verify`.

## Escopo do scan

- Hook local: apenas arquivos em stage (rápido).
- CI: diff do push/PR.
- Scan inicial único do histórico atual, antes de ligar tudo, para confirmar
  que o repo já está limpo. Se achar algo, para e reporta o achado; não reescreve
  histórico sem decisão do usuário.

## Allowlist de falsos-positivos

`gitleaks` marca strings de alta entropia. Este repo contém tokens de modelo de
ML, que não são segredos. A allowlist em `.gitleaks.toml` isenta, no mínimo:

- `fixes/**/tokenizer_config.json`
- `docs/models/**/channel-token-leak-writeup.md`

Novos caminhos entram conforme o scan inicial apontar.

## Critérios de sucesso

1. Um commit com um segredo de teste (ex.: `AKIA...` fake) é bloqueado
   localmente.
2. O mesmo segredo, empurrado com `--no-verify`, falha no GitHub Actions.
3. Um commit normal do repositório passa sem falso-positivo.
4. O scan do histórico atual retorna limpo (ou o achado é reportado).
