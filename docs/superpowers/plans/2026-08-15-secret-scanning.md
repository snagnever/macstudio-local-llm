# Secret Scanning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bloquear segredos antes que entrem no histórico git, com verificação no commit local e no GitHub Actions.

**Architecture:** `gitleaks` é o scanner único. O framework `pre-commit` o executa nos arquivos em stage antes do commit. Um workflow do GitHub Actions o executa a cada `push`/`pull_request` como rede de segurança. Um `.gitleaks.toml` versionado guarda regras e a allowlist de falsos-positivos.

**Tech Stack:** gitleaks (Go binary via brew), pre-commit (Python), GitHub Actions (`gitleaks/gitleaks-action@v2`).

## Global Constraints

- Repositório público: `github.com/snagnever/macstudio-local-llm`.
- Não reescrever histórico git sem decisão explícita do usuário.
- Não commitar arquivos de bench modificados que já estão na árvore; cada task commita só os arquivos que cria.
- Config do gitleaks fica em `.gitleaks.toml` na raiz (auto-detectado).
- Mensagens de commit em português, terminadas com a linha `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

| Arquivo | Responsabilidade |
| --- | --- |
| `.gitleaks.toml` | Regras (default + entropia) e allowlist de falsos-positivos |
| `.pre-commit-config.yaml` | Registra o hook `gitleaks` no estágio de commit |
| `.github/workflows/secret-scan.yml` | Escaneia cada push/PR no servidor |
| `README.md` | Seção curta: rodar `pre-commit install` após clone |

---

### Task 1: Instalar ferramentas e escanear o histórico atual

Confirma que o repo já está limpo **antes** de ligar os hooks. Se achar um segredo, para e reporta; não reescreve histórico.

**Files:**
- Nenhum arquivo criado. Task de verificação (gate).

- [ ] **Step 1: Instalar gitleaks e pre-commit via brew**

```bash
brew install gitleaks pre-commit
```

- [ ] **Step 2: Confirmar as versões**

```bash
gitleaks version && pre-commit --version
```
Expected: imprime uma versão do gitleaks (>= 8.18) e do pre-commit, sem erro.

- [ ] **Step 3: Escanear todo o histórico git**

```bash
gitleaks git --no-banner .
```
Expected: `no leaks found`. Se aparecer `leaks found: N`, PARE. Copie o achado (arquivo, regra, commit) e reporte ao usuário antes de continuar. Não avance nas próximas tasks.

---

### Task 2: Config do gitleaks com allowlist

**Files:**
- Create: `.gitleaks.toml`

**Interfaces:**
- Produces: `.gitleaks.toml` na raiz, auto-detectado pelo hook (Task 3) e pelo CI (Task 4).

- [ ] **Step 1: Criar `.gitleaks.toml`**

```toml
# Config do gitleaks. Estende as regras padrão e isenta falsos-positivos
# conhecidos: tokens de modelo de ML (não são segredos) e o writeup sobre
# vazamento de "channel token" de modelo.
title = "gitleaks config — local-llms"

[extend]
useDefault = true

[allowlist]
description = "Falsos-positivos conhecidos (tokens de modelo de ML, não segredos)"
paths = [
  '''fixes/.*/tokenizer_config\.json''',
  '''docs/models/.*/channel-token-leak-writeup\.md''',
]
```

- [ ] **Step 2: Verificar que a árvore atual passa com a config**

```bash
gitleaks git --no-banner .
```
Expected: `no leaks found`.

- [ ] **Step 3: Commit**

```bash
git add .gitleaks.toml
git commit -m "$(cat <<'EOF'
chore(security): config do gitleaks com allowlist de tokens de modelo

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Hook local via pre-commit

**Files:**
- Create: `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: `.gitleaks.toml` (Task 2).
- Produces: hook `gitleaks` instalado em `.git/hooks/pre-commit`.

- [ ] **Step 1: Descobrir a tag de release mais recente do gitleaks**

```bash
gitleaks version
```
Use essa versão com prefixo `v` no campo `rev` do próximo passo (ex.: saída `8.21.2` → `rev: v8.21.2`).

- [ ] **Step 2: Criar `.pre-commit-config.yaml`**

Substitua `v8.21.2` pela versão do Step 1.

```yaml
# Hooks locais. Rode `pre-commit install` uma vez após clonar.
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
```

- [ ] **Step 3: Instalar o hook**

```bash
pre-commit install
```
Expected: `pre-commit installed at .git/hooks/pre-commit`.

- [ ] **Step 4: Teste — um segredo falso deve bloquear o commit**

Cria um arquivo com um token falso no formato de GitHub PAT (dispara a regra padrão do gitleaks).

```bash
printf 'token = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"\n' > /tmp/leak-test.txt
cp /tmp/leak-test.txt ./leak-test.txt
git add leak-test.txt
git commit -m "test: deve falhar"
```
Expected: o commit FALHA; a saída do gitleaks mostra `leak-test.txt` e a regra do GitHub PAT.

- [ ] **Step 5: Limpar o arquivo de teste**

```bash
git reset HEAD leak-test.txt && rm -f leak-test.txt ./leak-test.txt /tmp/leak-test.txt
```
Expected: `git status` não lista `leak-test.txt`.

- [ ] **Step 6: Teste — um arquivo normal deve passar**

```bash
echo "ok" >> README.md
git add README.md
pre-commit run gitleaks --files README.md
```
Expected: hook `gitleaks` reporta `Passed`. Depois desfaça: `git restore --staged README.md && git checkout README.md`.

- [ ] **Step 7: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "$(cat <<'EOF'
chore(security): hook pre-commit com gitleaks

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: GitHub Actions

**Files:**
- Create: `.github/workflows/secret-scan.yml`

**Interfaces:**
- Consumes: `.gitleaks.toml` (Task 2).
- Produces: workflow `secret-scan` que roda em cada push/PR.

- [ ] **Step 1: Criar `.github/workflows/secret-scan.yml`**

```yaml
name: secret-scan
on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Validar a sintaxe YAML**

```bash
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/secret-scan.yml')); print('yaml ok')"
```
Expected: `yaml ok`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/secret-scan.yml
git commit -m "$(cat <<'EOF'
ci(security): workflow de secret-scan com gitleaks-action

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Documentar o setup para quem clona

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `.pre-commit-config.yaml` (Task 3).

- [ ] **Step 1: Ler o README para achar o ponto de inserção**

```bash
grep -n "^## " README.md
```
Escolha um ponto após a seção de introdução (ou o fim do arquivo se não houver seção clara de setup).

- [ ] **Step 2: Adicionar a seção de setup**

Insere no ponto escolhido:

```markdown
## Verificação de segredos

Este repositório é público. Um hook `pre-commit` roda `gitleaks` e bloqueia
commits que contenham segredos. Após clonar, instale o hook uma vez:

```bash
brew install gitleaks pre-commit
pre-commit install
```

O GitHub Actions repete a verificação em cada push como rede de segurança.
```

- [ ] **Step 3: Verificar a árvore**

```bash
gitleaks git --no-banner .
```
Expected: `no leaks found`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs(security): instruções de pre-commit install no README

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notas de execução

- Task 1 é um gate: se o histórico tiver um segredo, o restante do plano espera a decisão do usuário sobre limpeza de histórico.
- O `push` que subir a Task 4 é o primeiro a exercitar o CI; confira a aba Actions no GitHub depois.
