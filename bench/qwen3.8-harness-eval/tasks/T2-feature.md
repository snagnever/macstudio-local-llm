# T2 — Feature em código existente

**Fixture:** `fixtures/ledger` **com os bugs de T1 já corrigidos** (use a solução de referência
ou o resultado de um run T1 que passou). **Time-box:** 20 min. **Mede:** escopo, testes novos, CLI.

## Prompt

```text
Add a `report` subcommand to this ledger CLI:

    python3 -m ledger report <file.csv> --from YYYY-MM-DD --to YYYY-MM-DD

It prints one line per transaction in the date range, oldest first, in the format
`YYYY-MM-DD  <description left-aligned, padded to 20 chars>  <amount right-aligned in 10 chars, 2 decimals>`
(that is, Python `f"{day}  {description:<20}  {amount:>10.2f}"`),
followed by a final line `total  <sum, 2 decimals>`. Both dates are inclusive.
Reuse the existing `between` and `sorted_by_day` functions. Add tests for the new
subcommand in tests/. Keep the existing tests passing.
```

## Verificação

```bash
python3 -m pytest -q                                   # esperado: todos passam, >= 7 testes
python3 -m ledger report sample.csv --from 2025-01-01 --to 2025-01-31
```

Saída esperada do segundo comando:

```text
2025-01-02  Rent                    -1200.00
2025-01-15  Groceries                -145.30
total  -1345.30
```

`pass` = saída idêntica, testes novos existem em `tests/`, testes antigos intactos.

## Follow-up

```text
The output format does not match the spec exactly. Compare your output against the format
in my first message character by character, fix it, and add a test that pins the format.
```

## Rubrica

- `q_scope`: reutilizou `between` e `sorted_by_day` ou reimplementou?
- `q_tests`: os testes novos cobrem o intervalo inclusivo e o formato?
- `q_clarity`: o parser de argumentos é legível (argparse ou equivalente simples)?
