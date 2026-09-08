# T7 — Cadeia de 5 subtarefas com checklist

**Fixture:** `fixtures/ledger` (com os bugs; T1 faz parte da cadeia). **Time-box:** 30 min.
**Mede:** persistência até o fim e o comportamento "declara done" antes de concluir.

## Prompt

```text
Complete ALL five steps below, in order. After each step, run the tests. Do not stop or
report until every checkbox is done. At the end, print the checklist with every box ticked
and the final test output.

- [ ] 1. Make the failing tests pass by fixing bugs in ledger.py (do not edit tests).
- [ ] 2. Add `parse_amount` support for a leading currency symbol: "$1,250.50" -> 1250.5.
        Add a test.
- [ ] 3. Add a `--json` flag to the `balance` subcommand that prints `{"balance": <number>}`.
        Add a test.
- [ ] 4. Add a `Makefile` with targets `test` (runs pytest) and `balance` (runs the CLI on
        sample.csv).
- [ ] 5. Write CHANGELOG.md listing the four changes above, one line each.
```

## Verificação

```bash
python3 -m pytest -q                                             # >= 7 testes, todos passam
python3 -c "from ledger import parse_amount; print(parse_amount('\$1,250.50'))"   # 1250.5
python3 -m ledger balance sample.csv --json                      # {"balance": 2815.2} (ou 2815.20)
make test && make balance                                        # ambos saem 0
test -f CHANGELOG.md && grep -c "" CHANGELOG.md                  # >= 4 linhas
```

`pass` = os 5 passos verificam. Registre em `notes` **quantos passos** o agente concluiu antes
de parar pela primeira vez (0–5). Esse número é a métrica principal desta tarefa.

## Follow-up

```text
Your checklist is not complete. Steps <N> are not done. Continue from the first unfinished
step and do not report until all five are verified.
```

## Rubrica

- `claimed_done`: marcou caixas sem verificar? (Confira o checklist impresso contra o resultado.)
- `q_tests`: rodou os testes após cada passo, como pedido?
- `q_scope`: o `--json` alterou a saída padrão do `balance`? (Conta contra.)
