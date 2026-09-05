from datetime import date

from ledger import Transaction, balance, between, parse_amount, sorted_by_day


def tx(day: str, amount: float) -> Transaction:
    return Transaction(day=date.fromisoformat(day), description="x", amount=amount)


def test_parse_amount_plain():
    assert parse_amount("-145.30") == -145.30


def test_parse_amount_with_thousands_separator():
    assert parse_amount("3,000.00") == 3000.0
    assert parse_amount("1,250.50") == 1250.5


def test_balance_keeps_sign_of_expenses():
    rows = [tx("2025-01-01", 100.0), tx("2025-01-02", -40.0)]
    assert balance(rows) == 60.0


def test_between_is_inclusive_on_both_ends():
    rows = [tx("2025-01-01", 1), tx("2025-01-15", 1), tx("2025-01-31", 1)]
    got = between(rows, date(2025, 1, 1), date(2025, 1, 31))
    assert len(got) == 3


def test_sorted_by_day_orders_across_years():
    rows = [tx("2025-01-02", 1), tx("2024-12-30", 1), tx("2025-02-01", 1)]
    got = [row.day.isoformat() for row in sorted_by_day(rows)]
    assert got == ["2024-12-30", "2025-01-02", "2025-02-01"]
