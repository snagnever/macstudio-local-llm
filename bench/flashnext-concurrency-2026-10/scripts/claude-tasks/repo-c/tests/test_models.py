import datetime as dt
import unittest
from decimal import Decimal

from ledger.models import Account, Budget, Transaction, latest, to_amount, to_date, total


def tx(amount, date="2025-03-04", account="Checking", payee="Tesco", category=""):
    return Transaction(date=date, account=account, payee=payee, amount=amount, category=category)


class AmountTests(unittest.TestCase):
    def test_float_and_string_round_to_cents(self):
        self.assertEqual(to_amount(0.1), Decimal("0.10"))
        self.assertEqual(to_amount("12.345"), Decimal("12.35"))
        self.assertEqual(to_amount("-7"), Decimal("-7.00"))
        self.assertEqual(to_amount("1,234.50"), Decimal("1234.50"))

    def test_garbage_is_rejected(self):
        for bad in ("", "abc", "nan", True, None, object()):
            with self.assertRaises(ValueError, msg=repr(bad)):
                to_amount(bad)

    def test_date_parsing(self):
        self.assertEqual(to_date("2025-01-31"), dt.date(2025, 1, 31))
        self.assertEqual(to_date(dt.datetime(2025, 1, 31, 10, 0)), dt.date(2025, 1, 31))
        with self.assertRaises(ValueError):
            to_date("31/01/2025")


class TransactionTests(unittest.TestCase):
    def test_fields_are_normalised(self):
        t = Transaction(date="2025-02-01", account=" Checking ", payee=" Lidl ", amount="-3.5", category=None)
        self.assertEqual(t.account, "Checking")
        self.assertEqual(t.payee, "Lidl")
        self.assertEqual(t.amount, Decimal("-3.50"))
        self.assertEqual(t.category, "")
        self.assertEqual(t.month, "2025-02")
        self.assertTrue(t.is_expense)
        self.assertFalse(t.is_income)

    def test_requires_account_and_payee(self):
        with self.assertRaises(ValueError):
            tx("-1", account="")
        with self.assertRaises(ValueError):
            tx("-1", payee="   ")

    def test_ordering_is_by_date_first(self):
        a = tx("-5", date="2025-01-10", account="Zeta")
        b = tx("-5", date="2025-01-02", account="Alpha")
        self.assertEqual(sorted([a, b]), [b, a])

    def test_with_category_keeps_everything_else(self):
        t = tx("-9.99", payee="Netflix")
        u = t.with_category("Subscriptions", "Streaming")
        self.assertEqual((u.date, u.account, u.payee, u.amount, u.memo), (t.date, t.account, t.payee, t.amount, t.memo))
        self.assertEqual((u.category, u.subcategory), ("Subscriptions", "Streaming"))
        self.assertEqual(t.category, "")

    def test_to_dict_uses_strings_for_amounts(self):
        d = tx("-2.5", category="Groceries").to_dict()
        self.assertEqual(d["amount"], "-2.50")
        self.assertEqual(d["date"], "2025-03-04")
        self.assertNotIn("subcategory", d)


class AccountAndBudgetTests(unittest.TestCase):
    def test_account_validation(self):
        acc = Account(name=" Main ", kind="savings", opening_balance="100")
        self.assertEqual(acc.name, "Main")
        self.assertEqual(acc.opening_balance, Decimal("100.00"))
        with self.assertRaises(ValueError):
            Account(name="x", kind="piggy-bank")

    def test_budget_remaining_and_exceeded(self):
        budget = Budget(category="Groceries", limit="100")
        spent = [tx("-60", category="Groceries"), tx("-30", category="Groceries"), tx("-500", category="Travel")]
        self.assertEqual(budget.remaining(spent), Decimal("10.00"))
        self.assertFalse(budget.is_exceeded(spent))
        spent.append(tx("-20.01", category="Groceries"))
        self.assertTrue(budget.is_exceeded(spent))
        with self.assertRaises(ValueError):
            Budget(category="Groceries", limit="0")


class HelperTests(unittest.TestCase):
    def test_total_and_latest(self):
        items = [tx("-1.10", date="2025-01-01"), tx("2.20", date="2025-05-01"), tx("-0.05", date="2025-03-01")]
        self.assertEqual(total(items), Decimal("1.05"))
        self.assertEqual(latest(items).date, dt.date(2025, 5, 1))
        self.assertEqual(total([]), Decimal("0.00"))
        self.assertIsNone(latest([]))


if __name__ == "__main__":
    unittest.main()
