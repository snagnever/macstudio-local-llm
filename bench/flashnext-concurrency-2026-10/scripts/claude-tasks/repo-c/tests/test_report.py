import datetime as dt
import json
import unittest
from decimal import Decimal

from ledger.models import Transaction
from ledger.report import Report, build_report, money, render, render_json, render_text
from ledger.store import LedgerStore


def tx(date, account, payee, amount, category=""):
    return Transaction(date=date, account=account, payee=payee, amount=amount, category=category)


STORE = LedgerStore([
    tx("2025-01-05", "Checking", "Tesco", "-40.00", "Groceries"),
    tx("2025-01-25", "Checking", "Payroll", "3000.00", "Income"),
    tx("2025-02-03", "Visa Card", "Netflix", "-15.99", "Subscriptions"),
    tx("2025-03-01", "Savings", "Interest", "0.75", "Income"),
])


class BuildReportTests(unittest.TestCase):
    def test_figures(self):
        r = build_report(STORE)
        self.assertEqual(r.count, 4)
        self.assertEqual(r.total, Decimal("2944.76"))
        self.assertEqual(r.income, Decimal("3000.75"))
        self.assertEqual(r.expenses, Decimal("-55.99"))
        self.assertEqual(r.net_flow, r.total)
        self.assertEqual(r.balances, {"Checking": Decimal("2960.00"), "Visa Card": Decimal("-15.99"), "Savings": Decimal("0.75")})
        self.assertEqual((r.start, r.end), (dt.date(2025, 1, 5), dt.date(2025, 3, 1)))
        self.assertEqual(r.period, "2025-01-05 to 2025-03-01")

    def test_empty_store(self):
        r = build_report(LedgerStore())
        self.assertEqual(r.count, 0)
        self.assertEqual(r.total, Decimal("0.00"))
        self.assertEqual(r.period, "no transactions")
        self.assertEqual(render_text(r).splitlines()[-1], "total: 0.00")
        self.assertEqual(json.loads(render_json(r))["period"], {"start": None, "end": None})


class RenderTests(unittest.TestCase):
    def test_text_layout(self):
        text = render_text(build_report(STORE))
        self.assertEqual(text.splitlines(), [
            "transactions: 4",
            "period: 2025-01-05 to 2025-03-01",
            "income: 3000.75",
            "expenses: -55.99",
            "total: 2944.76",
            "balances:",
            "  Checking   2960.00",
            "  Savings    0.75",
            "  Visa Card  -15.99",
        ])

    def test_json_payload(self):
        data = json.loads(render_json(build_report(STORE)))
        self.assertEqual(data["count"], 4)
        self.assertEqual(data["total"], 2944.76)
        self.assertEqual(data["income"], 3000.75)
        self.assertEqual(data["expenses"], -55.99)
        self.assertEqual(data["balances"], {"Checking": 2960.0, "Savings": 0.75, "Visa Card": -15.99})
        self.assertEqual(data["period"], {"start": "2025-01-05", "end": "2025-03-01"})
        self.assertIsInstance(data["total"], float)

    def test_render_dispatch(self):
        r = build_report(STORE)
        self.assertEqual(render(r, "text"), render_text(r))
        self.assertEqual(render(r, "json"), render_json(r))
        with self.assertRaises(ValueError):
            render(r, "xml")

    def test_money_formatting(self):
        self.assertEqual(money(Decimal("5")), "5.00")
        self.assertEqual(money(Decimal("-0.5")), "-0.50")
        self.assertEqual(money(Decimal("1234.567")), "1234.57")

    def test_report_dataclass_defaults(self):
        r = Report(count=0, total=Decimal("0"), income=Decimal("0"), expenses=Decimal("0"))
        self.assertEqual(r.balances, {})
        self.assertIsNone(r.start)


if __name__ == "__main__":
    unittest.main()
