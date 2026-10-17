from __future__ import annotations

import csv
from pathlib import Path

from inventory.models import Item


def load_csv(path: Path) -> list[Item]:
    """Read rows of name,qty,price (with a header line) into items."""
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [Item(row["name"], int(row["qty"]), float(row["price"])) for row in reader]


def total_value(items: list[Item]) -> float:
    return round(sum(item.value for item in items), 2)
