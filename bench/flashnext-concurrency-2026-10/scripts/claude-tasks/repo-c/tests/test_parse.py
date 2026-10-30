import io
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from ledger.parse import ParseError, parse_csv_text, parse_json_text, read_any, read_csv, read_json, write_csv, write_json

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transactions.csv"

GOOD_CSV = (
    "date,account,payee,amount,category,memo\n"
    "2025-01-05,Checking,Tesco Stores,-42.10,Groceries,weekly shop\n"
    "2025-01-25,Checking,Acme Ltd Payroll,3250.00,Income,\n"
    "\n"
    "2025-02-01,Visa Card,Netflix.com,-15.99,,\n"
)


class CsvTests(unittest.TestCase):
    def test_parses_rows_and_skips_blank_lines(self):
        rows = parse_csv_text(GOOD_CSV)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].amount, Decimal("-42.10"))
        self.assertEqual(rows[0].memo, "weekly shop")
        self.assertEqual(rows[1].amount, Decimal("3250.00"))
        self.assertEqual(rows[2].category, "")

    def test_optional_columns_may_be_absent(self):
        rows = parse_csv_text("date,account,payee,amount\n2025-01-01,A,B,1\n")
        self.assertEqual(rows[0].category, "")
        self.assertEqual(rows[0].amount, Decimal("1.00"))

    def test_missing_required_column(self):
        with self.assertRaises(ParseError) as ctx:
            parse_csv_text("date,account,amount\n2025-01-01,A,1\n")
        self.assertIn("payee", str(ctx.exception))
        self.assertEqual(ctx.exception.location, "line 1")

    def test_unknown_and_duplicate_columns(self):
        with self.assertRaises(ParseError):
            parse_csv_text("date,account,payee,amount,colour\n")
        with self.assertRaises(ParseError):
            parse_csv_text("date,account,payee,amount,amount\n")

    def test_bad_amount_and_date_report_the_line(self):
        with self.assertRaises(ParseError) as ctx:
            parse_csv_text("date,account,payee,amount\n2025-01-01,A,B,1.0\n2025-01-02,A,B,twelve\n")
        self.assertEqual(ctx.exception.location, "line 3")
        with self.assertRaises(ParseError) as ctx:
            parse_csv_text("date,account,payee,amount\n01/02/2025,A,B,1\n")
        self.assertEqual(ctx.exception.location, "line 2")

    def test_wrong_field_count(self):
        with self.assertRaises(ParseError) as ctx:
            parse_csv_text("date,account,payee,amount\n2025-01-01,A,B\n")
        self.assertIn("expected 4 fields", str(ctx.exception))

    def test_empty_file(self):
        with self.assertRaises(ParseError):
            parse_csv_text("")

    def test_missing_file(self):
        with self.assertRaises(ParseError):
            read_csv("/nonexistent/path/to/ledger.csv")

    def test_fixture_loads_with_many_months_and_accounts(self):
        rows = read_csv(FIXTURE)
        self.assertGreaterEqual(len(rows), 600)
        months = {t.month for t in rows}
        self.assertGreaterEqual(len(months), 14)
        self.assertGreaterEqual(len({t.account for t in rows}), 3)

    def test_round_trip_through_write_csv(self):
        rows = parse_csv_text(GOOD_CSV)
        buf = io.StringIO()
        self.assertEqual(write_csv(rows, buf), 3)
        again = parse_csv_text(buf.getvalue())
        self.assertEqual(again, rows)


class JsonTests(unittest.TestCase):
    def test_bare_list_and_wrapped_object(self):
        text = '[{"date": "2025-01-01", "account": "A", "payee": "Lidl", "amount": "-3.50"}]'
        self.assertEqual(parse_json_text(text)[0].amount, Decimal("-3.50"))
        wrapped = '{"transactions": [{"date": "2025-01-01", "account": "A", "payee": "Lidl", "amount": -3.5}]}'
        self.assertEqual(parse_json_text(wrapped)[0].amount, Decimal("-3.50"))

    def test_invalid_json_and_bad_shapes(self):
        with self.assertRaises(ParseError):
            parse_json_text("{not json")
        with self.assertRaises(ParseError):
            parse_json_text('{"rows": []}')
        with self.assertRaises(ParseError):
            parse_json_text("[1, 2]")
        with self.assertRaises(ParseError) as ctx:
            parse_json_text('[{"date": "2025-01-01", "account": "A", "payee": "B", "amount": 1, "extra": 2}]')
        self.assertEqual(ctx.exception.location, "record 0")

    def test_missing_key_and_non_string_field(self):
        with self.assertRaises(ParseError):
            parse_json_text('[{"date": "2025-01-01", "payee": "B", "amount": 1}]')
        with self.assertRaises(ParseError):
            parse_json_text('[{"date": "2025-01-01", "account": 7, "payee": "B", "amount": 1}]')

    def test_write_and_read_json_file(self):
        rows = parse_csv_text(GOOD_CSV)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "out.json"
            with path.open("w", encoding="utf-8") as fh:
                self.assertEqual(write_json(rows, fh), 3)
            self.assertEqual(read_json(path), rows)
            self.assertEqual(read_any(path), rows)
        with self.assertRaises(ParseError):
            read_json("/nonexistent/ledger.json")


if __name__ == "__main__":
    unittest.main()
