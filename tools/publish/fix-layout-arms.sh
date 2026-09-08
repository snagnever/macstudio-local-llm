#!/usr/bin/env bash
# Apply publish-time path fixes to the built layout arms.
# Usage: fix-layout-arms.sh <site-dir>
# <site-dir>/demos/layout/{design-skill,taste-skill,taste2} must already exist.
set -euo pipefail
SITE="${1:?usage: fix-layout-arms.sh <site-dir>}"
L="$SITE/demos/layout"

# design-skill: absolute "/1/".."/5/" links -> relative.
# The index sits one level above the page dirs; each page dir links to siblings.
sed -i.bak -E 's#href="/([1-5])/"#href="\1/"#g' "$L/design-skill/index.html"
for n in 1 2 3 4 5; do
  sed -i.bak -E 's#href="/([1-5])/"#href="../\1/"#g' "$L/design-skill/$n/index.html"
done
find "$L/design-skill" -name '*.bak' -delete

# taste2: extensionless "href=\"1\"" was resolved by its Node server; make it static.
for n in 1 2 3 4 5; do
  sed -i.bak -E 's#href="([1-5])"#href="\1.html"#g' "$L/taste2/$n.html"
done
find "$L/taste2" -name '*.bak' -delete

# taste2 shipped no index page; generate one listing the five.
cat > "$L/taste2/index.html" <<'HTML'
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>taste2 — five iterations</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1.5rem}
li{margin:.4rem 0}</style></head><body>
<h1>taste2 — five iterations</h1>
<p>Five landing-page iterations generated in one session. This index is added at
publish time; the run itself served these pages from a small Node server.</p>
<ol><li><a href="1.html">Iteration 1</a></li><li><a href="2.html">Iteration 2</a></li>
<li><a href="3.html">Iteration 3</a></li><li><a href="4.html">Iteration 4</a></li>
<li><a href="5.html">Iteration 5</a></li></ol>
</body></html>
HTML

# taste-skill: history-API routing needs a fallback for deep links.
cp "$L/taste-skill/index.html" "$L/taste-skill/404.html"

echo "layout arms fixed under $L"
