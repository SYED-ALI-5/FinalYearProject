#!/usr/bin/env bash
set -euo pipefail
ALLOW="$(dirname "$0")/allowlist.json"
prog="$1"; shift
if ! command -v jq >/dev/null 2>&1; then echo "jq required"; exit 1; fi
if ! jq -e --arg p "$prog" '.[$p]' "$ALLOW" >/dev/null; then echo "not allowed"; exit 2; fi
ALLOWED=($(jq -r --arg p "$prog" '.[$p].allowed_flags[]?' "$ALLOW"))
MAX=$(jq -r --arg p "$prog" '.[$p].max_args // 20' "$ALLOW")
if [ "$#" -gt "$MAX" ]; then echo "too many args"; exit 3; fi
for a in "$@"; do
  if [[ "$a" == -* ]]; then
    ok=false
    for f in "${ALLOWED[@]}"; do
      if [[ "$a" == "$f" ]] || [[ "$a" == $f* ]]; then ok=true; break; fi
    done
    $ok || { echo "flag not allowed: $a"; exit 4; }
  fi
done
exec "$prog" "$@"