"""Readers for the two supported input formats: CSV and JSON.

Both readers are strict.  A missing column, an unreadable date or an
amount that is not a number raises :class:`ParseError` with the line (or
record index) where the problem was found.  Nothing is silently skipped.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, TextIO, Union

from ledger.models import Transaction

REQUIRED_COLUMNS: Sequence[str] = ("date", "account", "payee", "amount")
OPTIONAL_COLUMNS: Sequence[str] = ("category", "memo", "subcategory")
KNOWN_COLUMNS = tuple(REQUIRED_COLUMNS) + tuple(OPTIONAL_COLUMNS)

PathLike = Union[str, Path]


class ParseError(ValueError):
    """Raised when an input file is malformed.

    ``location`` is a human readable pointer such as ``"line 12"`` or
    ``"record 3"``; ``source`` is the file name when one is known.
    """

    def __init__(self, message: str, location: str = "", source: str = "") -> None:
        self.message = message
        self.location = location
        self.source = source
        super().__init__(self._format())

    def _format(self) -> str:
        parts = []
        if self.source:
            parts.append(self.source)
        if self.location:
            parts.append(self.location)
        prefix = ": ".join(parts)
        return f"{prefix}: {self.message}" if prefix else self.message


def _build(row: dict, location: str, source: str) -> Transaction:
    try:
        return Transaction(
            date=row.get("date", ""),
            account=row.get("account", ""),
            payee=row.get("payee", ""),
            amount=row.get("amount", ""),
            category=row.get("category", "") or "",
            memo=row.get("memo", "") or "",
            subcategory=row.get("subcategory", "") or "",
        )
    except ValueError as exc:
        raise ParseError(str(exc), location, source) from exc


# --------------------------------------------------------------------------- CSV


def _check_header(header: Sequence[str], source: str) -> None:
    if not header:
        raise ParseError("empty file, expected a header line", "line 1", source)
    names = [h.strip() for h in header]
    missing = [c for c in REQUIRED_COLUMNS if c not in names]
    if missing:
        raise ParseError(f"missing column(s): {', '.join(missing)}", "line 1", source)
    seen = set()
    for name in names:
        if name in seen:
            raise ParseError(f"duplicate column: {name}", "line 1", source)
        seen.add(name)
    unknown = [n for n in names if n not in KNOWN_COLUMNS]
    if unknown:
        raise ParseError(f"unknown column(s): {', '.join(unknown)}", "line 1", source)


def iter_csv(stream: TextIO, source: str = "") -> Iterator[Transaction]:
    """Yield transactions from an open CSV stream, validating as it goes."""
    reader = csv.reader(stream)
    try:
        header = next(reader)
    except StopIteration:
        raise ParseError("empty file, expected a header line", "line 1", source) from None
    _check_header(header, source)
    names = [h.strip() for h in header]
    for lineno, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue  # tolerate blank lines, they carry no data
        if len(row) != len(names):
            raise ParseError(f"expected {len(names)} fields, found {len(row)}", f"line {lineno}", source)
        yield _build(dict(zip(names, row)), f"line {lineno}", source)


def read_csv(path: PathLike) -> List[Transaction]:
    """Read a CSV file with a ``date,account,payee,amount[,category,memo]`` header."""
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8", newline="") as fh:
            return list(iter_csv(fh, source=p.name))
    except FileNotFoundError:
        raise ParseError("file not found", source=str(p)) from None
    except UnicodeDecodeError as exc:
        raise ParseError(f"file is not valid UTF-8: {exc.reason}", source=p.name) from exc


def parse_csv_text(text: str, source: str = "<string>") -> List[Transaction]:
    """Parse CSV content held in memory (mostly for tests)."""
    return list(iter_csv(io.StringIO(text), source=source))


def write_csv(transactions: Iterable[Transaction], stream: TextIO) -> int:
    """Write transactions in the canonical six-column layout; return the row count."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["date", "account", "payee", "amount", "category", "memo"])
    count = 0
    for t in transactions:
        writer.writerow([t.date.isoformat(), t.account, t.payee, str(t.amount), t.category, t.memo])
        count += 1
    return count


# -------------------------------------------------------------------------- JSON


def _records(data: object, source: str) -> List[dict]:
    if isinstance(data, dict):
        if "transactions" not in data:
            raise ParseError("top-level object has no 'transactions' key", source=source)
        data = data["transactions"]
    if not isinstance(data, list):
        raise ParseError("expected a list of transaction objects", source=source)
    return data


def parse_json_text(text: str, source: str = "<string>") -> List[Transaction]:
    """Parse JSON content held in memory.

    Accepts either a bare list of objects or ``{"transactions": [...]}``.
    Amounts may be numbers or strings; strings are preferred because they
    do not lose cents on the way through a float.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"invalid JSON: {exc.msg}", f"line {exc.lineno}", source) from exc
    out: List[Transaction] = []
    for index, record in enumerate(_records(data, source)):
        location = f"record {index}"
        if not isinstance(record, dict):
            raise ParseError("transaction must be an object", location, source)
        missing = [c for c in REQUIRED_COLUMNS if c not in record]
        if missing:
            raise ParseError(f"missing key(s): {', '.join(missing)}", location, source)
        unknown = [k for k in record if k not in KNOWN_COLUMNS]
        if unknown:
            raise ParseError(f"unknown key(s): {', '.join(sorted(unknown))}", location, source)
        row = {k: ("" if v is None else v) for k, v in record.items()}
        for key in ("date", "account", "payee", "category", "memo", "subcategory"):
            if key in row and not isinstance(row[key], str):
                raise ParseError(f"{key} must be a string", location, source)
        out.append(_build(row, location, source))
    return out


def read_json(path: PathLike) -> List[Transaction]:
    """Read a JSON file produced by :func:`write_json` or compatible tools."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ParseError("file not found", source=str(p)) from None
    except UnicodeDecodeError as exc:
        raise ParseError(f"file is not valid UTF-8: {exc.reason}", source=p.name) from exc
    return parse_json_text(text, source=p.name)


def write_json(transactions: Iterable[Transaction], stream: TextIO, indent: int = 2) -> int:
    """Write ``{"transactions": [...]}`` to ``stream``; return the record count."""
    records = [t.to_dict() for t in transactions]
    json.dump({"transactions": records}, stream, indent=indent, sort_keys=True)
    stream.write("\n")
    return len(records)


def read_any(path: PathLike) -> List[Transaction]:
    """Dispatch on the file suffix: ``.json`` goes to JSON, everything else to CSV."""
    p = Path(path)
    if p.suffix.lower() == ".json":
        return read_json(p)
    return read_csv(p)
