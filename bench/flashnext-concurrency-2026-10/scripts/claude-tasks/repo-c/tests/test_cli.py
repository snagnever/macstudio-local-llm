import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ledger.cli import main

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "transactions.csv"

SMALL_CSV = (
    "date,account,payee,amount,category,memo\n"
    "2025-01-05,Checking,Tesco Stores,-40.00,,\n"
    "2025-01-25,Checking,Acme Ltd Payroll,3000.00,Income,\n"
    "2025-02-03,Visa Card,Netflix.com,-15.99,,\n"
)


def run_main(argv):
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


class ReportCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "small.csv"
        self.csv.write_text(SMALL_CSV, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_text_is_the_default_format(self):
        code, out = run_main(["report", str(self.csv)])
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[:5], [
            "transactions: 3",
            "period: 2025-01-05 to 2025-02-03",
            "income: 3000.00",
            "expenses: -55.99",
            "total: 2944.01",
        ])
        self.assertIn("  Checking   2960.00", out)

    def test_json_format(self):
        code, out = run_main(["report", "--format", "json", str(self.csv)])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["total"], 2944.01)
        self.assertEqual(data["balances"], {"Checking": 2960.0, "Visa Card": -15.99})

    def test_filters(self):
        code, out = run_main(["report", "--format", "json", "--account", "Visa Card", str(self.csv)])
        self.assertEqual(json.loads(out)["count"], 1)
        code, out = run_main(["report", "--format", "json", "--category", "Groceries", str(self.csv)])
        self.assertEqual(json.loads(out)["total"], -40.0)  # category filled in by the rules
        code, out = run_main(["report", "--format", "json", "--from", "2025-02-01", str(self.csv)])
        self.assertEqual(json.loads(out)["count"], 1)

    def test_unknown_format_is_an_argparse_error(self):
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                main(["report", "--format", "yaml", str(self.csv)])
        self.assertEqual(ctx.exception.code, 2)

    def test_parse_error_returns_2(self):
        bad = Path(self.tmp.name) / "bad.csv"
        bad.write_text("date,account,payee,amount\n2025-13-01,A,B,1\n", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = run_main(["report", str(bad)])
        self.assertEqual(code, 2)
        self.assertIn("line 2", err.getvalue())

    def test_fixture_total_matches_the_csv_sum(self):
        from decimal import Decimal
        import csv
        with FIXTURE.open(encoding="utf-8", newline="") as fh:
            expected = sum((Decimal(row["amount"]) for row in csv.DictReader(fh)), Decimal("0"))
        code, out = run_main(["report", "--format", "json", str(FIXTURE)])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(Decimal(str(data["total"])), expected)
        self.assertGreaterEqual(data["count"], 600)

    def test_module_is_runnable(self):
        proc = subprocess.run([sys.executable, "-m", "ledger.cli", "report", str(FIXTURE)],
                              cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.startswith("transactions: "))


class ImportCommandTests(unittest.TestCase):
    def test_import_categorises_and_writes_csv(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.csv"
            src.write_text(SMALL_CSV, encoding="utf-8")
            code, out = run_main(["import", str(src)])
            self.assertEqual(code, 0)
            lines = out.splitlines()
            self.assertEqual(lines[0], "date,account,payee,amount,category,memo")
            self.assertEqual(lines[1], "2025-01-05,Checking,Tesco Stores,-40.00,Groceries,")
            self.assertEqual(lines[3], "2025-02-03,Visa Card,Netflix.com,-15.99,Subscriptions,")

    def test_import_to_json_file(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.csv"
            src.write_text(SMALL_CSV, encoding="utf-8")
            dst = Path(d) / "out.json"
            with contextlib.redirect_stderr(io.StringIO()):
                code, out = run_main(["import", "--to", "json", "--output", str(dst), str(src)])
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            data = json.loads(dst.read_text(encoding="utf-8"))
            self.assertEqual(len(data["transactions"]), 3)
            self.assertEqual(data["transactions"][0]["category"], "Groceries")

    def test_no_subcommand_is_an_error(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                main([])


if __name__ == "__main__":
    unittest.main()
