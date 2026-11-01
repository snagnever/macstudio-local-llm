"""Core data types of the ledger.

Everything money-related is a :class:`decimal.Decimal` quantised to cents.
Floats are never used for amounts: they are accepted at construction time
for convenience but converted through their string form so that ``0.1``
becomes exactly ``Decimal("0.10")``.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, Optional, Union

CENT = Decimal("0.01")

AmountLike = Union[Decimal, int, float, str]


def to_amount(value: AmountLike) -> Decimal:
    """Convert ``value`` to a Decimal rounded to cents.

    Raises ``ValueError`` when the value cannot be interpreted as a number.
    """
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, bool):
        raise ValueError("booleans are not amounts")
    elif isinstance(value, (int, float, str)):
        text = str(value).strip().replace(",", "")
        if not text:
            raise ValueError("empty amount")
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"invalid amount: {value!r}") from exc
    else:
        raise ValueError(f"unsupported amount type: {type(value).__name__}")
    if not amount.is_finite():
        raise ValueError(f"amount is not finite: {value!r}")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def to_date(value: Union[dt.date, str]) -> dt.date:
    """Convert an ISO ``YYYY-MM-DD`` string (or a date) to a date."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if not isinstance(value, str):
        raise ValueError(f"unsupported date type: {type(value).__name__}")
    text = value.strip()
    try:
        return dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid date: {value!r} (expected YYYY-MM-DD)") from exc


@dataclass(frozen=True)
class Account:
    """A bank account, card or wallet that transactions are posted to."""

    name: str
    kind: str = "checking"
    currency: str = "EUR"
    opening_balance: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("account name must not be empty")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "opening_balance", to_amount(self.opening_balance))
        if self.kind not in ACCOUNT_KINDS:
            raise ValueError(f"unknown account kind: {self.kind!r}")


ACCOUNT_KINDS = ("checking", "savings", "credit", "cash", "investment")


@dataclass(frozen=True, order=True)
class Transaction:
    """One movement of money on an account.

    ``amount`` is negative for expenses and positive for income.  ``category``
    may be empty; the rules engine fills it in later.  Instances are ordered
    by date first, which makes sorted output stable across accounts.
    """

    date: dt.date
    account: str
    payee: str
    amount: Decimal
    category: str = ""
    memo: str = ""
    subcategory: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", to_date(self.date))
        object.__setattr__(self, "amount", to_amount(self.amount))
        for name in ("account", "payee", "category", "memo", "subcategory"):
            value = getattr(self, name)
            if value is None:
                value = ""
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a string, got {type(value).__name__}")
            object.__setattr__(self, name, value.strip())
        if not self.account:
            raise ValueError("transaction account must not be empty")
        if not self.payee:
            raise ValueError("transaction payee must not be empty")

    @property
    def month(self) -> str:
        """The ``YYYY-MM`` label of the transaction date."""
        return self.date.strftime("%Y-%m")

    @property
    def year(self) -> int:
        return self.date.year

    @property
    def is_expense(self) -> bool:
        return self.amount < 0

    @property
    def is_income(self) -> bool:
        return self.amount > 0

    def with_category(self, category: str, subcategory: str = "") -> "Transaction":
        """Return a copy with a new category (and optional subcategory)."""
        return Transaction(
            date=self.date,
            account=self.account,
            payee=self.payee,
            amount=self.amount,
            category=category,
            memo=self.memo,
            subcategory=subcategory,
        )

    def to_dict(self) -> dict:
        """Plain-data representation used by the JSON writer."""
        data = {
            "date": self.date.isoformat(),
            "account": self.account,
            "payee": self.payee,
            "amount": str(self.amount),
            "category": self.category,
            "memo": self.memo,
        }
        if self.subcategory:
            data["subcategory"] = self.subcategory
        return data


@dataclass(frozen=True)
class Budget:
    """A monthly spending limit for one category.

    ``limit`` is stored as a positive amount; spending is compared against it
    by absolute value so that the usual negative-expense convention works.
    """

    category: str
    limit: Decimal
    period: str = "monthly"

    def __post_init__(self) -> None:
        if not self.category or not self.category.strip():
            raise ValueError("budget category must not be empty")
        object.__setattr__(self, "category", self.category.strip())
        limit = to_amount(self.limit)
        if limit <= 0:
            raise ValueError("budget limit must be positive")
        object.__setattr__(self, "limit", limit)
        if self.period not in ("monthly", "yearly"):
            raise ValueError(f"unknown budget period: {self.period!r}")

    def remaining(self, transactions: Iterable[Transaction]) -> Decimal:
        """Return the amount left after the given spending in this category."""
        spent = sum((-t.amount for t in transactions if t.category == self.category and t.is_expense), Decimal("0"))
        return (self.limit - spent).quantize(CENT)

    def is_exceeded(self, transactions: Iterable[Transaction]) -> bool:
        return self.remaining(transactions) < 0


def total(transactions: Iterable[Transaction]) -> Decimal:
    """Sum the amounts of ``transactions`` exactly (as Decimal cents)."""
    return sum((t.amount for t in transactions), Decimal("0")).quantize(CENT)


def latest(transactions: Iterable[Transaction]) -> Optional[Transaction]:
    """Return the most recent transaction, or ``None`` for an empty input."""
    best: Optional[Transaction] = None
    for t in transactions:
        if best is None or t.date > best.date:
            best = t
    return best
