#!/usr/bin/env bash
# Pull full available trade tape per market via curl (offset pagination).
set -e
cd "$(dirname "$0")"
fetch_market () {
  local name="$1" cid="$2" offset=0 page n total=0
  : > "pages_${name}.ndjson"
  while [ "$offset" -lt 120000 ]; do
    page=$(curl -s -m 30 -A "Mozilla/5.0" "https://data-api.polymarket.com/trades?market=${cid}&limit=1000&offset=${offset}")
    n=$(printf '%s' "$page" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
    [ "$n" -eq 0 ] && break
    printf '%s\n' "$page" >> "pages_${name}.ndjson"
    total=$((total+n)); offset=$((offset+1000))
    [ "$n" -lt 1000 ] && break
    sleep 0.2
  done
  echo "$name: fetched $total trades across pages"
}
FR=$(python3 -c "import json;print(json.load(open('targets.json',encoding='utf-8'))['france']['conditionId'])")
SP=$(python3 -c "import json;print(json.load(open('targets.json',encoding='utf-8'))['spain']['conditionId'])")
fetch_market france "$FR"
fetch_market spain "$SP"
