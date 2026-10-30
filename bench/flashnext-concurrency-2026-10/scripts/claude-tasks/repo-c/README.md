# ledger

A small personal finance ledger written in Python 3.9 with the standard
library only. It reads transactions from CSV or JSON, assigns categories with
a merchant rules table and prints summary reports as text or JSON.

## Layout

```
ledger/
  models.py   Transaction, Account and Budget dataclasses (Decimal amounts)
  parse.py    strict CSV and JSON readers/writers, ParseError
  rules.py    the categorisation rules table and categorize()
  store.py    LedgerStore: in-memory filters and totals
  report.py   build_report(), render_text(), render_json()
  cli.py      the command line
fixtures/
  transactions.csv   15 months of sample data across four accounts
tests/        unittest suite
```

## Input format

CSV files need a header with at least `date,account,payee,amount`; the
columns `category` and `memo` are optional. Dates are `YYYY-MM-DD`, amounts
have two decimals, expenses are negative and incomes positive:

```
date,account,payee,amount,category,memo
2025-01-05,Checking,Tesco Stores,-42.10,Groceries,weekly shop
2025-01-25,Checking,Acme Ltd Payroll,3250.00,Income,
```

JSON files hold either a list of objects with the same keys or an object
`{"transactions": [...]}`. Rows without a category are categorised with the
rules table when they are loaded.

## Command line

Run the tool from the repository root with `python3 -m ledger.cli`.

### `report`

```
python3 -m ledger.cli report [--format text|json] [--account NAME]
                             [--category NAME] [--from DATE] [--to DATE] CSV
```

Prints the transaction count, the covered period, income, expenses, the
grand total and one balance per account. `--format text` is the default:

```
$ python3 -m ledger.cli report fixtures/transactions.csv
transactions: 660
period: 2025-01-01 to 2026-03-28
income: 75359.22
expenses: -80234.06
total: -4874.84
balances:
  Cash Wallet  -88.58
  Checking     7919.70
  Savings      4608.67
  Visa Card    -17314.63
```

`--format json` prints one JSON object with the keys `count`, `period`,
`income`, `expenses`, `total` and `balances`; amounts are numbers rounded to
cents. The filters `--account`, `--category`, `--from` and `--to` restrict
the rows before the figures are computed.

### `import`

```
python3 -m ledger.cli import [--to csv|json] [--output FILE] [--recategorize] FILE
```

Reads a CSV or JSON file, fills in missing categories and writes the rows,
sorted by date, as CSV (default) or JSON to stdout or to `--output`.
`--recategorize` replaces categories that are already present.

## Tests

```
python3 -m unittest discover -s tests -t .
```
