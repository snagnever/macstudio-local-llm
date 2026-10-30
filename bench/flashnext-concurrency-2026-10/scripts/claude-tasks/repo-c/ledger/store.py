"""An in-memory store of transactions with simple filtering and totals.

The store is a thin layer over a list.  It keeps insertion order, exposes
filters that return new stores (so they can be chained) and computes exact
Decimal totals.  It is deliberately small: a personal ledger has thousands
of rows, not millions, and a list is the right tool for that.
"""

from __future__ import annotations

import datetime as dt
from collections import OrderedDict
from decimal import Decimal
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Union

from ledger.models import CENT, Transaction, to_date

DateLike = Union[dt.date, str, None]


class LedgerStore:
    """A collection of transactions."""

    def __init__(self, transactions: Optional[Iterable[Transaction]] = None) -> None:
        self._items: List[Transaction] = []
        if transactions is not None:
            self.extend(transactions)

    # ---- container protocol -------------------------------------------------

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Transaction]:
        return iter(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __repr__(self) -> str:
        return f"LedgerStore({len(self._items)} transactions, total {self.total()})"

    # ---- mutation -----------------------------------------------------------

    def add(self, transaction: Transaction) -> None:
        if not isinstance(transaction, Transaction):
            raise TypeError(f"expected Transaction, got {type(transaction).__name__}")
        self._items.append(transaction)

    def extend(self, transactions: Iterable[Transaction]) -> int:
        """Add many transactions; return how many were added."""
        before = len(self._items)
        for t in transactions:
            self.add(t)
        return len(self._items) - before

    def clear(self) -> None:
        self._items.clear()

    def map(self, func: Callable[[Transaction], Transaction]) -> "LedgerStore":
        """Return a new store with ``func`` applied to every transaction."""
        return LedgerStore(func(t) for t in self._items)

    # ---- views --------------------------------------------------------------

    def all(self) -> List[Transaction]:
        """A copy of the transactions in insertion order."""
        return list(self._items)

    def sorted(self) -> List[Transaction]:
        """Transactions ordered by date (then account, payee, amount)."""
        return sorted(self._items)

    def filter(self, predicate: Callable[[Transaction], bool]) -> "LedgerStore":
        return LedgerStore(t for t in self._items if predicate(t))

    def between(self, start: DateLike = None, end: DateLike = None) -> "LedgerStore":
        """Transactions with ``start <= date <= end``; either bound may be ``None``."""
        lo = to_date(start) if start is not None else None
        hi = to_date(end) if end is not None else None
        if lo is not None and hi is not None and lo > hi:
            raise ValueError(f"start {lo} is after end {hi}")

        def keep(t: Transaction) -> bool:
            if lo is not None and t.date < lo:
                return False
            if hi is not None and t.date > hi:
                return False
            return True

        return self.filter(keep)

    def in_month(self, month: str) -> "LedgerStore":
        """Transactions whose ``YYYY-MM`` label equals ``month``."""
        if len(month) != 7 or month[4] != "-":
            raise ValueError(f"month must look like YYYY-MM, got {month!r}")
        return self.filter(lambda t: t.month == month)

    def for_account(self, account: str) -> "LedgerStore":
        return self.filter(lambda t: t.account == account)

    def for_category(self, category: str) -> "LedgerStore":
        return self.filter(lambda t: t.category == category)

    def for_payee(self, payee: str) -> "LedgerStore":
        needle = payee.lower()
        return self.filter(lambda t: needle in t.payee.lower())

    def expenses(self) -> "LedgerStore":
        return self.filter(lambda t: t.is_expense)

    def incomes(self) -> "LedgerStore":
        return self.filter(lambda t: t.is_income)

    # ---- aggregates ---------------------------------------------------------

    def total(self) -> Decimal:
        """Exact sum of all amounts, as Decimal cents."""
        return sum((t.amount for t in self._items), Decimal("0")).quantize(CENT)

    def total_expenses(self) -> Decimal:
        """Sum of the negative amounts (a negative number or zero)."""
        return self.expenses().total()

    def total_income(self) -> Decimal:
        return self.incomes().total()

    def accounts(self) -> List[str]:
        """Distinct account names in first-seen order."""
        return _distinct(t.account for t in self._items)

    def categories(self) -> List[str]:
        return _distinct(t.category for t in self._items)

    def months(self) -> List[str]:
        """Distinct ``YYYY-MM`` labels, oldest first."""
        return sorted(set(t.month for t in self._items))

    def balances(self) -> "OrderedDict[str, Decimal]":
        """Per-account totals keyed by account name, in first-seen order."""
        out: "OrderedDict[str, Decimal]" = OrderedDict()
        for t in self._items:
            out[t.account] = (out.get(t.account, Decimal("0")) + t.amount).quantize(CENT)
        return out

    def date_range(self) -> Optional[tuple]:
        """``(earliest, latest)`` dates, or ``None`` when the store is empty."""
        if not self._items:
            return None
        dates = [t.date for t in self._items]
        return (min(dates), max(dates))

    def count_by(self, key: Callable[[Transaction], str]) -> Dict[str, int]:
        """Number of transactions per ``key(t)``, in first-seen order."""
        out: "OrderedDict[str, int]" = OrderedDict()
        for t in self._items:
            label = key(t)
            out[label] = out.get(label, 0) + 1
        return out

    def largest(self, n: int = 5) -> List[Transaction]:
        """The ``n`` transactions with the largest absolute amount."""
        if n < 0:
            raise ValueError("n must not be negative")
        return sorted(self._items, key=lambda t: abs(t.amount), reverse=True)[:n]


def _distinct(values: Iterable[str]) -> List[str]:
    seen: "OrderedDict[str, None]" = OrderedDict()
    for v in values:
        seen.setdefault(v, None)
    return list(seen)
