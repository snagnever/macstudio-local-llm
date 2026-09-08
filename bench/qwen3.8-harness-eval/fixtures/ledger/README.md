# ledger — fixture for tasks T1, T2 and T4

A small command-line ledger. It reads transactions from a CSV file and prints
balances and reports.

This fixture ships with **three seeded bugs**. The tests in `tests/` expose them.
Do not fix the bugs in this directory. Copy the directory to a scratch
location before you give it to an agent (see `../../plan.md`).

## Run

```bash
python3 -m pytest -q
python3 -m ledger balance sample.csv
```

Requires Python 3.10+ and `pytest`.
