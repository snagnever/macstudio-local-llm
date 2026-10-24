import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from inventory.cli import main


class CliTests(unittest.TestCase):
    def test_text_summary(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "inv.csv"
            p.write_text("name,qty,price\nbolt,4,0.25\nnut,10,0.1\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main([str(p)]), 0)
            self.assertEqual(out.getvalue().strip(), "2 items, total 2.00")
