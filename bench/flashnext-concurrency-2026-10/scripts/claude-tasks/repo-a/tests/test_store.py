import tempfile
import unittest
from pathlib import Path

from inventory.models import Item
from inventory.store import load_csv, total_value


class StoreTests(unittest.TestCase):
    def test_item_value(self):
        self.assertEqual(Item("bolt", 4, 0.25).value, 1.0)

    def test_total_value_rounds_to_cents(self):
        self.assertEqual(total_value([Item("a", 3, 0.333), Item("b", 1, 2.0)]), 3.0)

    def test_load_csv_reads_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "inv.csv"
            p.write_text("name,qty,price\nbolt,4,0.25\nnut,10,0.1\n", encoding="utf-8")
            self.assertEqual(load_csv(p), [Item("bolt", 4, 0.25), Item("nut", 10, 0.1)])
