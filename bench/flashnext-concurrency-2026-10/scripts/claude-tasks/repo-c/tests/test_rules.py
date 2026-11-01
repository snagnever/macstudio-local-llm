import unittest
from pathlib import Path

from ledger.models import Transaction
from ledger.parse import read_csv
from ledger.rules import CATEGORIES, RULES, UNCATEGORIZED, categorize, categorize_all, match, normalize, rule_count

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transactions.csv"


def tx(payee, memo="", category=""):
    return Transaction(date="2025-06-01", account="Checking", payee=payee, amount="-1.00", category=category, memo=memo)


class TableTests(unittest.TestCase):
    def test_table_is_large_and_well_formed(self):
        self.assertGreaterEqual(rule_count(), 450)
        self.assertEqual(rule_count(), len(RULES))
        for pattern, category, subcategory in RULES:
            self.assertTrue(pattern.strip(), pattern)
            self.assertIn(category, CATEGORIES)
            self.assertIsInstance(subcategory, str)

    def test_patterns_are_unique_after_normalisation(self):
        keys = [normalize(p).strip() for p, _, _ in RULES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_normalize(self):
        self.assertEqual(normalize("  McDonald's   #1234 "), " mcdonald's 1234 ")
        self.assertEqual(normalize("H&M Online"), " h&m online ")
        self.assertEqual(normalize("DISNEY+"), " disney+ ")


class MatchTests(unittest.TestCase):
    def test_first_matching_rule_wins(self):
        self.assertEqual(match("Shell Energy Direct Debit")[1], "Utilities")
        self.assertEqual(match("Shell Petrol Station")[1], "Fuel")
        self.assertEqual(match("Uber Eats London")[1], "Dining")
        self.assertEqual(match("Uber Trip Help.uber.com")[1], "Transport")
        self.assertEqual(match("Amazon Prime Membership")[1], "Subscriptions")
        self.assertEqual(match("Amazon Marketplace")[1], "Shopping")

    def test_matching_is_case_insensitive_and_tolerates_punctuation(self):
        self.assertEqual(match("TESCO STORES 2041")[1], "Groceries")
        self.assertEqual(match("tesco petrol filling station")[1], "Fuel")
        self.assertEqual(match("Netflix.com")[1], "Subscriptions")
        self.assertEqual(match("B&Q Warehouse")[1], "Home")

    def test_word_anchors_avoid_false_positives(self):
        self.assertEqual(match("Espresso Bar")[1], "Dining")  # not Esso
        self.assertEqual(match("Travis Perkins")[1], "Home")  # not Avis
        self.assertEqual(match("Free Mobile")[1], "Telecom")  # not EE
        self.assertEqual(match("Current Account Fee")[1], "Fees")  # not "rent"
        self.assertEqual(match("Esso Hemel")[1], "Fuel")

    def test_memo_is_searched_when_payee_matches_nothing(self):
        self.assertIsNone(match("Card payment 4471"))
        self.assertEqual(match("Card payment 4471", memo="council tax march")[1], "Taxes")

    def test_no_match(self):
        self.assertIsNone(match("Totally Unknown Merchant 123"))


class CategorizeTests(unittest.TestCase):
    def test_fills_category_and_subcategory(self):
        t = categorize(tx("Spotify AB"))
        self.assertEqual((t.category, t.subcategory), ("Subscriptions", "Music"))

    def test_existing_category_is_kept_unless_overwrite(self):
        t = tx("Spotify AB", category="Gifts")
        self.assertEqual(categorize(t).category, "Gifts")
        self.assertEqual(categorize(t, overwrite=True).category, "Subscriptions")

    def test_unknown_payee_becomes_uncategorized(self):
        t = categorize(tx("Totally Unknown Merchant 123"))
        self.assertEqual(t.category, UNCATEGORIZED)
        self.assertEqual(t.subcategory, "")

    def test_fixture_payees_all_match_a_rule(self):
        rows = categorize_all(read_csv(FIXTURE), overwrite=True)
        self.assertTrue(rows)
        self.assertFalse([t.payee for t in rows if t.category == UNCATEGORIZED])


if __name__ == "__main__":
    unittest.main()
