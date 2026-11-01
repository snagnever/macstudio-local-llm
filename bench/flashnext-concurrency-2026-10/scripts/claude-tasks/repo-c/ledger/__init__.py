"""ledger -- a small personal finance ledger.

The package reads transactions from CSV or JSON files, assigns categories
with a merchant rules table, keeps them in an in-memory store and renders
summary reports as text or JSON.  It depends on the standard library only.
"""

from ledger.models import Account, Budget, Transaction
from ledger.parse import ParseError, read_csv, read_json
from ledger.rules import categorize
from ledger.store import LedgerStore
from ledger.report import build_report, render_json, render_text

__all__ = [
    "Account",
    "Budget",
    "Transaction",
    "ParseError",
    "read_csv",
    "read_json",
    "categorize",
    "LedgerStore",
    "build_report",
    "render_json",
    "render_text",
]

__version__ = "0.4.1"
