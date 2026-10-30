"""Command line entry point: ``python3 -m ledger.cli <subcommand> ...``.

Two subcommands exist:

``import``
    Read a CSV or JSON file, fill in missing categories with the rules
    table and write the result as CSV or JSON to stdout or to ``--output``.

``report``
    Read a CSV file and print the summary report as text (default) or JSON.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, TextIO

from ledger.parse import ParseError, read_any, write_csv, write_json
from ledger.report import build_report, render
from ledger.rules import categorize_all
from ledger.store import LedgerStore

FORMATS = ("text", "json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger", description="Personal finance ledger.")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p_import = sub.add_parser("import", help="normalise a CSV/JSON file and categorise its rows")
    p_import.add_argument("path", type=Path, help="input file (.csv or .json)")
    p_import.add_argument("--to", choices=("csv", "json"), default="csv", help="output format (default csv)")
    p_import.add_argument("--output", "-o", type=Path, default=None, help="write here instead of stdout")
    p_import.add_argument("--recategorize", action="store_true", help="replace categories already present")

    p_report = sub.add_parser("report", help="summarise a CSV file")
    p_report.add_argument("path", type=Path, help="CSV with date,account,payee,amount,category,memo columns")
    p_report.add_argument("--format", choices=FORMATS, default="text", help="output format (default text)")
    p_report.add_argument("--account", default=None, help="only this account")
    p_report.add_argument("--category", default=None, help="only this category (after categorisation)")
    p_report.add_argument("--from", dest="start", default=None, metavar="DATE", help="first date, inclusive")
    p_report.add_argument("--to", dest="end", default=None, metavar="DATE", help="last date, inclusive")
    return parser


def _load(path: Path, recategorize: bool = False) -> LedgerStore:
    transactions = read_any(path)
    return LedgerStore(categorize_all(transactions, overwrite=recategorize))


def _select(store: LedgerStore, args: argparse.Namespace) -> LedgerStore:
    if args.start or args.end:
        store = store.between(args.start, args.end)
    if args.account:
        store = store.for_account(args.account)
    if args.category:
        store = store.for_category(args.category)
    return store


def cmd_import(args: argparse.Namespace, out: TextIO) -> int:
    store = _load(args.path, recategorize=args.recategorize)
    rows = store.sorted()
    if args.output is not None:
        with args.output.open("w", encoding="utf-8", newline="") as fh:
            count = write_json(rows, fh) if args.to == "json" else write_csv(rows, fh)
        print(f"wrote {count} transactions to {args.output}", file=sys.stderr)
        return 0
    if args.to == "json":
        write_json(rows, out)
    else:
        write_csv(rows, out)
    return 0


def cmd_report(args: argparse.Namespace, out: TextIO) -> int:
    store = _select(_load(args.path), args)
    report = build_report(store)
    out.write(render(report, args.format))
    out.write("\n")
    return 0


def main(argv: Optional[List[str]] = None, out: Optional[TextIO] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stream = out if out is not None else sys.stdout
    try:
        if args.command == "import":
            return cmd_import(args, stream)
        if args.command == "report":
            return cmd_report(args, stream)
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover - parser.error exits


if __name__ == "__main__":
    sys.exit(main())
