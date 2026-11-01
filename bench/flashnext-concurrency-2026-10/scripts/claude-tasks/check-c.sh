#!/usr/bin/env bash
# check-c.sh REPO -- print "true" when task c is solved in REPO, "false" otherwise.
# Always exits 0; the verdict is the single word on stdout.
#
# Conditions (all run inside REPO):
#   a) the unittest suite passes;
#   b) `report --group-by month --format json fixtures/transactions.csv` prints
#      one JSON object with >= 12 keys shaped YYYY-MM whose values sum to the
#      grand total of the CSV amounts (computed here, not by the package) +-0.01;
#   c) README.md mentions `group-by` at least once.
set -uo pipefail

repo="${1:-}"
if [ -z "$repo" ] || [ ! -d "$repo" ]; then
  echo false
  exit 0
fi
cd "$repo" || { echo false; exit 0; }

# (a) unit tests
if ! python3 -m unittest discover -s tests -t . >/dev/null 2>&1; then
  echo false
  exit 0
fi

# (c) README documents the option
readme_hits="$(grep -c 'group-by' README.md 2>/dev/null || true)"
case "$readme_hits" in
  ''|*[!0-9]*) readme_hits=0 ;;
esac
if [ "$readme_hits" -lt 1 ]; then
  echo false
  exit 0
fi

# (b) grouped JSON output sums to the independently computed CSV total
output="$(python3 -m ledger.cli report --group-by month --format json fixtures/transactions.csv 2>/dev/null)" || {
  echo false
  exit 0
}

verdict="$(LEDGER_GROUPED_JSON="$output" python3 - fixtures/transactions.csv <<'PY'
import csv
import json
import os
import re
import sys
from decimal import Decimal

try:
    data = json.loads(os.environ.get("LEDGER_GROUPED_JSON", ""))
except Exception:
    print("false")
    sys.exit(0)

if not isinstance(data, dict):
    print("false")
    sys.exit(0)

month_re = re.compile(r"^\d{4}-\d{2}$")
keys = [k for k in data if month_re.match(k)]
if len(keys) < 12 or len(keys) != len(data):
    print("false")
    sys.exit(0)

try:
    grouped = sum(Decimal(str(data[k])) for k in keys)
except Exception:
    print("false")
    sys.exit(0)

expected = Decimal("0")
with open(sys.argv[1], newline="", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        expected += Decimal(row["amount"])

print("true" if abs(grouped - expected) <= Decimal("0.01") else "false")
PY
)" || verdict=false

if [ "$verdict" = "true" ]; then
  echo true
else
  echo false
fi
exit 0
