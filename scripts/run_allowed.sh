#!/usr/bin/env bash
set -euo pipefail

ALLOW="$(dirname "$0")/allowlist.json"
prog="$1"; shift

if ! command -v jq >/dev/null 2>&1; then
echo "jq required"
exit 1
fi

if ! jq -e --arg p "$prog" '.[$p]' "$ALLOW" >/dev/null; then
echo "not allowed"
exit 2
fi

ALLOWED=($(jq -r --arg p "$prog" '.[$p].allowed_flags[]?' "$ALLOW"))
MAX=$(jq -r --arg p "$prog" '.[$p].max_args // 20' "$ALLOW")

if [ "$#" -gt "$MAX" ]; then
echo "too many args"
exit 3
fi

for a in "$@"; do
# Only check flags that start with "-"
if [[ "$a" == -* ]]; then
ok=false
for f in "${ALLOWED[@]}"; do
# Allow:
# --flag
# --flag=value
# --flag
# --flag123
if [[ "$a" == "$f" ]] || [[ "$a" == "$f"* ]]; then
ok=true
break
fi
done

    # If still not allowed, reject
    if [[ "$ok" == "false" ]]; then
        echo "flag not allowed: $a"
        exit 4
    fi
fi

done

exec "$prog" "$@"