import datetime as dt
import unittest
from decimal import Decimal

from ledger.models import Transaction
from ledger.store import LedgerStore


def tx(date, account, payee, amount, category=""):
    return Transaction(date=date, account=account, payee=payee, amount=amount, category=category)


SAMPLE = [
    tx("2025-01-05", "Checking", "Tesco", "-40.00", "Groceries"),
    tx("2025-01-25", "Checking", "Payroll", "3000.00", "Income"),
    tx("2025-02-03", "Visa Card", "Netflix", "-15.99", "Subscriptions"),
    tx("2025-02-14", "Visa Card", "Nando's", "-24.50", "Dining"),
    tx("2025-03-01", "Savings", "Interest", "0.75", "Income"),
    tx("2025-03-09", "Checking", "Lidl", "-12.30", "Groceries"),
]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = LedgerStore(SAMPLE)

    def test_len_iter_and_total(self):
        self.assertEqual(len(self.store), 6)
        self.assertEqual(list(self.store), SAMPLE)
        self.assertEqual(self.store.total(), Decimal("2907.96"))
        self.assertEqual(self.store.total_income(), Decimal("3000.75"))
        self.assertEqual(self.store.total_expenses(), Decimal("-92.79"))

    def test_empty_store(self):
        empty = LedgerStore()
        self.assertFalse(empty)
        self.assertEqual(empty.total(), Decimal("0.00"))
        self.assertIsNone(empty.date_range())
        self.assertEqual(empty.balances(), {})

    def test_add_rejects_non_transactions(self):
        with self.assertRaises(TypeError):
            self.store.add({"payee": "x"})

    def test_between_is_inclusive(self):
        sub = self.store.between("2025-01-25", "2025-03-01")
        self.assertEqual([t.payee for t in sub], ["Payroll", "Netflix", "Nando's", "Interest"])
        self.assertEqual(len(self.store.between(start="2025-03-01")), 2)
        self.assertEqual(len(self.store.between(end=dt.date(2025, 1, 31))), 2)
        with self.assertRaises(ValueError):
            self.store.between("2025-03-01", "2025-01-01")

    def test_in_month_and_months(self):
        self.assertEqual([t.payee for t in self.store.in_month("2025-02")], ["Netflix", "Nando's"])
        self.assertEqual(self.store.months(), ["2025-01", "2025-02", "2025-03"])
        with self.assertRaises(ValueError):
            self.store.in_month("2025/02")

    def test_filters_chain(self):
        sub = self.store.for_account("Checking").for_category("Groceries")
        self.assertEqual(sub.total(), Decimal("-52.30"))
        self.assertEqual(len(self.store.for_payee("netflix")), 1)
        self.assertEqual(len(self.store.expenses()), 4)
        self.assertEqual(len(self.store.incomes()), 2)

    def test_balances_and_accounts_keep_first_seen_order(self):
        self.assertEqual(self.store.accounts(), ["Checking", "Visa Card", "Savings"])
        balances = self.store.balances()
        self.assertEqual(list(balances), ["Checking", "Visa Card", "Savings"])
        self.assertEqual(balances["Checking"], Decimal("2947.70"))
        self.assertEqual(balances["Visa Card"], Decimal("-40.49"))
        self.assertEqual(balances["Savings"], Decimal("0.75"))
        self.assertEqual(sum(balances.values()), self.store.total())

    def test_date_range_count_by_and_largest(self):
        self.assertEqual(self.store.date_range(), (dt.date(2025, 1, 5), dt.date(2025, 3, 9)))
        self.assertEqual(self.store.count_by(lambda t: t.category), {"Groceries": 2, "Income": 2, "Subscriptions": 1, "Dining": 1})
        self.assertEqual([t.payee for t in self.store.largest(2)], ["Payroll", "Tesco"])

    def test_map_returns_new_store(self):
        upper = self.store.map(lambda t: t.with_category(t.category.upper()))
        self.assertEqual(upper.categories(), ["GROCERIES", "INCOME", "SUBSCRIPTIONS", "DINING"])
        self.assertEqual(self.store.categories(), ["Groceries", "Income", "Subscriptions", "Dining"])


if __name__ == "__main__":
    unittest.main()
