"""Summary reports over a :class:`~ledger.store.LedgerStore`.

:func:`build_report` computes the numbers once into a plain :class:`Report`
dataclass; :func:`render_text` and :func:`render_json` turn that into the
two output formats offered by the command line.  Keeping the computation
separate from the rendering means both renderers always agree.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from ledger.store import LedgerStore


@dataclass
class Report:
    """The figures shown by the ``report`` command."""

    count: int
    total: Decimal
    income: Decimal
    expenses: Decimal
    balances: Dict[str, Decimal] = field(default_factory=dict)
    start: Optional[dt.date] = None
    end: Optional[dt.date] = None

    @property
    def net_flow(self) -> Decimal:
        """Income plus expenses; identical to ``total`` but reads better."""
        return self.income + self.expenses

    @property
    def period(self) -> str:
        if self.start is None or self.end is None:
            return "no transactions"
        if self.start == self.end:
            return self.start.isoformat()
        return f"{self.start.isoformat()} to {self.end.isoformat()}"


def build_report(store: LedgerStore) -> Report:
    """Compute the summary figures for ``store``."""
    span = store.date_range()
    return Report(
        count=len(store),
        total=store.total(),
        income=store.total_income(),
        expenses=store.total_expenses(),
        balances=dict(store.balances()),
        start=span[0] if span else None,
        end=span[1] if span else None,
    )


def money(value: Decimal) -> str:
    """Format a Decimal with two decimals and a leading minus for negatives."""
    return f"{value:.2f}"


def as_number(value: Decimal) -> float:
    """Round to cents and return a float for JSON output."""
    return float(round(value, 2))


def render_text(report: Report) -> str:
    """Multi-line human readable summary."""
    lines: List[str] = [
        f"transactions: {report.count}",
        f"period: {report.period}",
        f"income: {money(report.income)}",
        f"expenses: {money(report.expenses)}",
        f"total: {money(report.total)}",
    ]
    if report.balances:
        lines.append("balances:")
        width = max(len(name) for name in report.balances)
        for name in sorted(report.balances):
            lines.append(f"  {name.ljust(width)}  {money(report.balances[name])}")
    return "\n".join(lines)


def render_json(report: Report, indent: Optional[int] = None) -> str:
    """One JSON object; amounts are numbers rounded to cents."""
    payload = {
        "count": report.count,
        "period": {
            "start": report.start.isoformat() if report.start else None,
            "end": report.end.isoformat() if report.end else None,
        },
        "income": as_number(report.income),
        "expenses": as_number(report.expenses),
        "total": as_number(report.total),
        "balances": {name: as_number(value) for name, value in sorted(report.balances.items())},
    }
    return json.dumps(payload, indent=indent, sort_keys=True)


def render(report: Report, fmt: str) -> str:
    """Dispatch on ``fmt`` (``"text"`` or ``"json"``)."""
    if fmt == "text":
        return render_text(report)
    if fmt == "json":
        return render_json(report)
    raise ValueError(f"unknown format: {fmt!r}")
