# T4 — Refactor multi-arquivo sem mudar comportamento

**Fixture:** `fixtures/ledger` com T1 e T2 já aplicados. **Time-box:** 25 min. **Mede:** edição
coordenada em vários arquivos com os testes como rede.

## Prompt

```text
Refactor this project into a package without changing behaviour:

- Create `ledger/` with `__init__.py`, `model.py` (Transaction, parse_amount, load),
  `queries.py` (balance, between, sorted_by_day) and `cli.py` (main, subcommands).
- `python3 -m ledger ...` must keep working with the same commands and output.
- `from ledger import Transaction, balance` must keep working.
- Move the tests so each test module matches one source module.
- Delete the old top-level ledger.py once nothing imports it.

Run the tests before and after. Report the file tree at the end.
```

## Verificação

```bash
python3 -m pytest -q                                          # todos passam
python3 -m ledger balance sample.csv                          # 2815.20
python3 -m ledger report sample.csv --from 2025-01-01 --to 2025-01-31   # mesma saída de T2
python3 -c "from ledger import Transaction, balance; print('ok')"
test ! -f ledger.py && echo "old module removed"
```

`pass` = os cinco comandos passam.

## Follow-up

```text
The public import path or a CLI command broke. Run every command in the spec, find the one
that fails, and fix it without touching behaviour.
```

## Rubrica

- `q_process`: rodou os testes antes de mover arquivos?
- `q_scope`: mudou lógica junto com a movimentação? (Conta contra.)
- `q_clarity`: `__init__.py` reexporta de forma explícita?
