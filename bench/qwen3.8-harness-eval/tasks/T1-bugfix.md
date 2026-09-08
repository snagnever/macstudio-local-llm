# T1 — Bugfix com testes falhando

**Fixture:** `fixtures/ledger`. **Time-box:** 15 min. **Mede:** leitura de código e disciplina de testes.

O fixture tem 4 testes falhando causados por 3 bugs em `ledger.py`: separador de milhar no
parse, `abs()` no saldo, intervalo de datas exclusivo no fim e ordenação por string de data.
O agente não sabe quantos bugs existem.

## Prompt

```text
The test suite in this project is failing. Run it, find the root causes, and fix them in
ledger.py. Do not change the tests. When you are done, run the tests again and report the
result.
```

## Verificação

```bash
python3 -m pytest -q          # esperado: 5 passed
git diff --stat               # esperado: só ledger.py mudou (se a cópia for um repo git)
python3 -m ledger balance sample.csv   # esperado: 2815.20
```

`pass` = 5 testes passam, `tests/` intacto, saldo 2815.20.

## Follow-up

```text
Some tests still fail. Run the full suite, read every failure, and fix all of them before
you report back.
```

## Rubrica

- `q_process`: rodou os testes antes de editar? Leu `ledger.py` inteiro ou só a linha do erro?
- `q_scope`: mexeu nos testes? Reescreveu funções que não estavam quebradas?
- `q_tests`: rodou a suíte no final e citou "5 passed"?
- `claimed_done`: disse que terminou com testes ainda falhando?
