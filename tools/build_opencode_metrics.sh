#!/usr/bin/env bash
# Regenera o dashboard autocontido reports/opencode-metrics.html.
# Uso: tools/build_opencode_metrics.sh [--days N] [--project SUBSTR]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/reports/opencode-metrics.template.html"
OUT="$ROOT/reports/opencode-metrics.html"
DATA="$(mktemp)"
trap 'rm -f "$DATA"' EXIT

python3 "$ROOT/tools/opencode_metrics.py" --out "$DATA" "$@"

# Injeta o JSON entre os marcadores /*__DATA__*/ ... /*__END__*/
python3 - "$TEMPLATE" "$DATA" "$OUT" <<'PY'
import re, sys
tpl, data, out = sys.argv[1], sys.argv[2], sys.argv[3]
html = open(tpl).read()
payload = open(data).read()
html = re.sub(r"/\*__DATA__\*/.*?/\*__END__\*/",
              lambda _: "/*__DATA__*/" + payload + "/*__END__*/",
              html, count=1, flags=re.S)
open(out, "w").write(html)
print(f"wrote {out}")
PY
