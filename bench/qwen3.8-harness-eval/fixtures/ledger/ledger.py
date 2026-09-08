"""Minimal ledger: parse a CSV of transactions and report on them."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Transaction:
    day: date
    description: str
    amount: float


def parse_amount(raw: str) -> float:
    """Parse an amount such as '-145.30' into a float."""
    return float(raw.strip())


def load(path: str) -> list[Transaction]:
    """Load transactions from a CSV file with columns date,description,amount."""
    rows: list[Transaction] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                Transaction(
                    day=date.fromisoformat(row["date"]),
                    description=row["description"],
                    amount=parse_amount(row["amount"]),
                )
            )
    return rows


def balance(rows: list[Transaction]) -> float:
    """Sum of all amounts. Expenses are negative."""
    total = 0.0
    for row in rows:
        total += abs(row.amount)
    return round(total, 2)


def between(rows: list[Transaction], start: date, end: date) -> list[Transaction]:
    """Transactions with start <= day <= end (both inclusive)."""
    return [row for row in rows if start <= row.day < end]


def sorted_by_day(rows: list[Transaction]) -> list[Transaction]:
    """Rows ordered from oldest to newest."""
    return sorted(rows, key=lambda row: row.day.strftime("%d-%m-%Y"))


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "balance":
        print("usage: python3 -m ledger balance <file.csv>", file=sys.stderr)
        return 2
    rows = load(argv[1])
    print(f"{balance(rows):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
