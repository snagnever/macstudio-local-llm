from __future__ import annotations

import argparse
import sys
from pathlib import Path

from inventory.store import load_csv, total_value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inventory", description="Summarize an inventory CSV.")
    parser.add_argument("path", type=Path, help="CSV with name,qty,price columns")
    args = parser.parse_args(argv)
    items = load_csv(args.path)
    print(f"{len(items)} items, total {total_value(items):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
