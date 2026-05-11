import asyncio
import json
import os
import re
import datetime
import requests
from typing import Dict, Any, Optional, List

from Agents.docker_cmds import DockerAgent


# -----------------------------
# CONFIG
# -----------------------------
TARGET = "dvwa"
BASE_URL = f"http://{TARGET}"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-llm:7b"
MAX_STEPS = 15


# -----------------------------
# STATE MEMORY
# -----------------------------
memory = {
    "known_paths": set(),
    "executed_actions": [],
    "last_failure": None,
    "last_success": None
}

session = {
    "cookie": None,
    "token": None
}


# -----------------------------
# LLM CALL
# -----------------------------
def ask_llm(prompt: str) -> str:
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2}
    })
    return r.json()["response"]


# -----------------------------
# PARSING
# -----------------------------
def extract_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except:
        return None


ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|\r')

def clean(text: str) -> str:
    return ANSI.sub('', text)


# -----------------------------
# FAILURE CLASSIFIER
# -----------------------------
def classify_failure(output: str) -> Optional[str]:
    o = output.lower()

    if "404" in o:
        return "NOT_FOUND"
    if "403" in o:
        return "FORBIDDEN"
    if "connection refused" in o:
        return "NETWORK_ERROR"
    if "error" in o:
        return "GENERIC_ERROR"
    return None


# -----------------------------
# FFUF PARSER (dynamic grounding)
# -----------------------------
def parse_ffuf(output: str) -> List[str]:
    output = clean(output)
    paths = []

    for line in output.splitlines():
        if "[Status:" not in line:
            continue
        try:
            path = line.split()[0]
            status = int(line.split("[Status:")[1].split(",")[0])
        except:
            continue

        if status in [200, 301, 302]:
            full = BASE_URL + "/" + path.strip("/")
            paths.append(full)

    return paths


# -----------------------------
# VALIDATION
# -----------------------------
ALLOWED = {"http_request", "fuzz", "sqlmap"}

def validate(action: Dict[str, Any]) -> bool:
    if not isinstance(action, dict):
        return False
    if action.get("action") not in ALLOWED:
        return False
    if "url" in action and not isinstance(action["url"], str):
        return False
    return True


# -----------------------------
# COMPILER
# -----------------------------
def compile_http(a):
    cmd = ["curl", "-sSfL"]

    method = a.get("method", "GET").upper()

    if method == "POST":
        cmd += ["-X", "POST"]

    if session["cookie"]:
        cmd += ["-H", f"Cookie: PHPSESSID={session['cookie']}"]

    for k, v in a.get("headers", {}).items():
        cmd += ["-H", f"{k}: {v}"]

    if "data" in a:
        cmd += ["-d", a["data"]]

    cmd.append(BASE_URL + a["url"])
    return cmd


def compile_fuzz(a):
    return [
        "ffuf",
        "-u", BASE_URL + a["url"],
        "-w", "/usr/share/wordlists/dirb/common.txt"
    ]


def compile_sqlmap(a):
    cmd = [
        "sqlmap",
        "-u", BASE_URL + a["url"],
        "--batch",
        "--forms",
        "--level=3",
        "--risk=2"
    ]

    if session["cookie"]:
        cmd += ["--cookie", f"PHPSESSID={session['cookie']}"]

    return cmd


def compile(action):
    if action["action"] == "http_request":
        return compile_http(action)
    if action["action"] == "fuzz":
        return compile_fuzz(action)
    if action["action"] == "sqlmap":
        return compile_sqlmap(action)


# -----------------------------
# PROMPT BUILDER (SELF-CORRECTING CORE)
# -----------------------------
def build_prompt(step: int) -> str:
    return f"""
You are an autonomous adaptive penetration testing agent.

TARGET: {BASE_URL}
STEP: {step}

KNOWN PATHS:
{list(memory["known_paths"])}

LAST FAILURE:
{memory["last_failure"]}

LAST SUCCESS:
{memory["last_success"]}

RULES:
- You MUST learn from failures
- If NOT_FOUND → change endpoint (add .php, try variations)
- Never repeat identical actions
- Prefer known paths but can explore new ones
- Always adapt strategy based on feedback

TOOLS:
1. http_request
2. fuzz
3. sqlmap

OUTPUT FORMAT:
Return ONLY JSON:
{{
  "action": "...",
  "method": "...",
  "url": "...",
  "headers": {{}},
  "data": "..."
}}
"""


# -----------------------------
# MAIN LOOP
# -----------------------------
async def main():

    docker = DockerAgent()

    if not await docker.is_kali_running():
        await docker.start_lab()

    await docker.install_tool("ffuf")
    await docker.install_tool("sqlmap")
    await docker.install_tool("curl")

    for step in range(MAX_STEPS):

        print(f"\n=== STEP {step} ===")

        prompt = build_prompt(step)
        raw = ask_llm(prompt)

        print("[LLM]:", raw)

        action = extract_json(raw)

        if not validate(action):
            print("[!] Invalid action")
            continue

        cmd = compile(action)
        print("[CMD]:", cmd)

        try:
            output = await docker.run_in_kali(cmd)
            success = True
        except Exception as e:
            output = str(e)
            success = False

        print("[OUTPUT]:\n", output[:800])

        # -----------------------------
        # LEARNING LOOP (CORE)
        # -----------------------------
        failure = classify_failure(output)

        if failure:
            memory["last_failure"] = failure
            memory["last_success"] = False
        else:
            memory["last_failure"] = None
            memory["last_success"] = True

        # -----------------------------
        # GROUNDING UPDATE
        # -----------------------------
        if action["action"] == "fuzz":
            paths = parse_ffuf(output)
            for p in paths:
                memory["known_paths"].add(p)

        # -----------------------------
        # COOKIE / TOKEN EXTRACTION
        # -----------------------------
        if "Set-Cookie" in output:
            m = re.search(r"PHPSESSID=([^;]+)", output)
            if m:
                session["cookie"] = m.group(1)

        # -----------------------------
        # HISTORY
        # -----------------------------
        memory["executed_actions"].append({
            "action": action,
            "success": success,
            "failure": failure
        })

        os.makedirs("history", exist_ok=True)
        with open(f"history/step_{step}.json", "w") as f:
            json.dump(memory, f, indent=2)

        # -----------------------------
        # STOP CONDITION
        # -----------------------------
        if "vulnerable" in output.lower():
            print("[+] VULNERABILITY FOUND")
            break

    print("\n[+] Done")


# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main())



# import asyncio
# import json
# import os
# import re
# import datetime
# import requests
# from typing import Dict, Any, Optional, List, Tuple
# from dataclasses import dataclass
# from pathlib import Path

# from Agents.docker_cmds import DockerAgent


# # -----------------------------
# # CONFIG
# # -----------------------------
# TARGET = "dvwa"
# BASE_URL = f"http://{TARGET}"
# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL = "deepseek-llm:7b"
# MAX_STEPS = 15
# MAX_RETRIES = 1  # Exactly as recommended


# # -----------------------------
# # RAG STORE (Tool Documentation)
# # -----------------------------
# class ToolRAG:
#     """Simple RAG store for tool documentation"""
    
#     def __init__(self):
#         self.docs = {
#             "ffuf_dir_fuzz": """
#             ffuf command for directory fuzzing:
#             -u: Target URL with FUZZ keyword
#             -w: Wordlist path
#             -fc: Filter out status codes (comma separated)
#             -fs: Filter by response size
#             -t: Threads (default 40)
#             -o: Output file
#             Example: ffuf -u http://example.com/FUZZ -w /usr/share/wordlists/dirb/common.txt -fc 404
#             """,
            
#             "ffuf_ext_fuzz": """
#             ffuf for file extension fuzzing:
#             Use -e .php,.asp,.txt for extensions
#             Example: ffuf -u http://example.com/adminFUZZ -w wordlist.txt -e .php,.html
#             """,
            
#             "sqlmap_get": """
#             sqlmap for GET parameter injection:
#             -u: Full URL with parameter
#             --batch: Never ask for user input
#             --level: Testing level (1-5, default 1)
#             --risk: Risk level (1-3, default 1)
#             --dbs: Enumerate databases
#             --tables: Enumerate tables
#             Example: sqlmap -u "http://example.com/page?id=1" --batch --dbs
#             """,
            
#             "sqlmap_post": """
#             sqlmap for POST parameter injection:
#             --data: POST body data
#             --forms: Parse forms automatically
#             Example: sqlmap -u "http://example.com/login" --data "user=1&pass=2" --batch
#             """,
            
#             "curl_get": """
#             curl for HTTP GET requests:
#             -s: Silent mode
#             -Sf: Show errors, fail on HTTP errors
#             -L: Follow redirects
#             -H: Add header
#             Example: curl -sSfL http://example.com/api
#             """,
            
#             "curl_post": """
#             curl for HTTP POST requests:
#             -X POST: Specify POST method
#             -d: Data payload
#             -H "Content-Type: application/json": JSON header
#             Example: curl -sSfL -X POST http://example.com/login -d "user=admin"
#             """
#         }
        
#         # Query → doc mapping
#         self.query_map = {
#             "fuzz directories": "ffuf_dir_fuzz",
#             "fuzz extensions": "ffuf_ext_fuzz", 
#             "sql injection get": "sqlmap_get",
#             "sql injection post": "sqlmap_post",
#             "http get": "curl_get",
#             "http post": "curl_post"
#         }
    
#     def search(self, query: str) -> str:
#         """Simple keyword search - upgrade to embeddings for production"""
#         query_lower = query.lower()
        
#         for keyword, doc_id in self.query_map.items():
#             if keyword in query_lower:
#                 return self.docs[doc_id]
        
#         # Default fallback
#         return self.docs.get("curl_get", "No docs found")


# # -----------------------------
# # AGENT 1: Query Strategist
# # -----------------------------
# class QueryStrategist:
#     """Decides what documentation to retrieve"""
    
#     def __init__(self, rag: ToolRAG):
#         self.rag = rag
    
#     def get_query(self, user_request: str, step_context: str, last_error: Optional[str] = None) -> str:
#         prompt = f"""
# You are a Query Strategist for penetration testing.

# USER REQUEST: {user_request}
# CURRENT STEP CONTEXT: {step_context}
# LAST ERROR (if any): {last_error}

# Your job: Output a search query that will retrieve the RIGHT documentation
# for building a command to accomplish this task.

# Available query types:
# - "fuzz directories" (use ffuf to find hidden paths)
# - "fuzz extensions" (use ffuf with file extensions)  
# - "sql injection get" (use sqlmap on GET parameters)
# - "sql injection post" (use sqlmap on POST data)
# - "http get" (curl GET request)
# - "http post" (curl POST request)

# Output ONLY the query string, nothing else.
# Example output: fuzz directories
# """
        
#         response = self._call_llm(prompt)
#         query = response.strip().lower()
        
#         # Validate query exists
#         if query not in self.rag.query_map:
#             query = "http get"  # default fallback
        
#         return query
    
#     def _call_llm(self, prompt: str) -> str:
#         r = requests.post(OLLAMA_URL, json={
#             "model": MODEL,
#             "prompt": prompt,
#             "stream": False,
#             "options": {"temperature": 0.1}
#         })
#         return r.json()["response"]


# # -----------------------------
# # AGENT 2: Command Builder
# # -----------------------------
# class CommandBuilder:
#     """Generates commands using retrieved documentation"""
    
#     def __init__(self, rag: ToolRAG):
#         self.rag = rag
    
#     def build_command(self, user_request: str, doc: str, last_error: Optional[str] = None) -> Dict[str, Any]:
#         prompt = f"""
# You are a Command Builder for penetration testing.

# USER REQUEST: {user_request}

# TOOL DOCUMENTATION:
# {doc}

# LAST ERROR (if any): {last_error}

# Your job: Generate a JSON action using the documentation above.
# Available actions: http_request, fuzz, sqlmap

# Output ONLY valid JSON:
# {{
#   "action": "fuzz",
#   "url": "/path/FUZZ",
#   "method": "GET",
#   "data": null,
#   "headers": {{}}
# }}

# Or for http_request:
# {{
#   "action": "http_request",
#   "url": "/path",
#   "method": "POST",
#   "data": "param=value",
#   "headers": {{"Content-Type": "application/x-www-form-urlencoded"}}
# }}

# Or for sqlmap:
# {{
#   "action": "sqlmap",
#   "url": "/page?id=1",
#   "method": "GET",
#   "data": null
# }}
# """
        
#         response = self._call_llm(prompt)
#         return self._extract_json(response)
    
#     def _call_llm(self, prompt: str) -> str:
#         r = requests.post(OLLAMA_URL, json={
#             "model": MODEL,
#             "prompt": prompt,
#             "stream": False,
#             "format": "json",
#             "options": {"temperature": 0.2}
#         })
#         return r.json()["response"]
    
#     def _extract_json(self, text: str) -> Optional[Dict]:
#         try:
#             return json.loads(text)
#         except:
#             # Try to find JSON in text
#             match = re.search(r'\{.*\}', text, re.DOTALL)
#             if match:
#                 try:
#                     return json.loads(match.group())
#                 except:
#                     pass
#             return None


# # -----------------------------
# # VALIDATOR (with specific checks)
# # -----------------------------
# class CommandValidator:
#     """Validates commands before execution"""
    
#     def validate(self, action: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
#         """Returns (is_valid, error_message)"""
        
#         if not isinstance(action, dict):
#             return False, "Action is not a dictionary"
        
#         # Check required fields
#         if "action" not in action:
#             return False, "Missing 'action' field"
        
#         if action["action"] not in ["http_request", "fuzz", "sqlmap"]:
#             return False, f"Invalid action: {action['action']}"
        
#         # Action-specific validation
#         if action["action"] == "fuzz":
#             if "url" not in action:
#                 return False, "Missing 'url' for fuzzing"
#             if "FUZZ" not in action["url"]:
#                 return False, "Fuzz URL must contain 'FUZZ' keyword"
#             return True, None
        
#         elif action["action"] == "sqlmap":
#             if "url" not in action:
#                 return False, "Missing 'url' for sqlmap"
#             # SQLMap needs either a parameter or --data
#             if "?" not in action["url"] and not action.get("data"):
#                 return False, "SQLMap needs either URL parameters or POST data"
#             return True, None
        
#         elif action["action"] == "http_request":
#             if "url" not in action:
#                 return False, "Missing 'url' for HTTP request"
#             if action.get("method") not in ["GET", "POST", None]:
#                 return False, f"Invalid method: {action.get('method')}"
#             return True, None
        
#         return True, None
    
#     def quick_fix(self, action: Dict[str, Any], error: str) -> Optional[Dict]:
#         """Attempt to auto-fix common issues"""
        
#         if "must contain 'FUZZ'" in error:
#             # Add FUZZ keyword to URL
#             if action["url"].endswith("/"):
#                 action["url"] += "FUZZ"
#             else:
#                 action["url"] += "/FUZZ"
#             return action
        
#         if "needs either URL parameters or POST data" in error:
#             # Add a test parameter
#             if "?" not in action["url"]:
#                 action["url"] += "?id=1"
#             return action
        
#         return None  # Can't auto-fix


# # -----------------------------
# # STATE MEMORY (enhanced)
# # -----------------------------
# memory = {
#     "known_paths": set(),
#     "executed_actions": [],
#     "last_failure": None,
#     "last_success": None,
#     "last_error_detail": None  # Track specific error messages
# }

# session = {
#     "cookie": None,
#     "token": None
# }


# # -----------------------------
# # EXISTING HELPERS (keep your existing functions)
# # -----------------------------
# def clean(text: str) -> str:
#     ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|\r')
#     return ANSI.sub('', text)

# def classify_failure(output: str) -> Optional[str]:
#     o = output.lower()
#     if "404" in o:
#         return "NOT_FOUND"
#     if "403" in o:
#         return "FORBIDDEN"
#     if "connection refused" in o:
#         return "NETWORK_ERROR"
#     if "error" in o:
#         return "GENERIC_ERROR"
#     if "invalid option" in o or "unrecognized" in o:
#         return "SYNTAX_ERROR"  # New classification
#     return None

# def parse_ffuf(output: str) -> List[str]:
#     output = clean(output)
#     paths = []
#     for line in output.splitlines():
#         if "[Status:" not in line:
#             continue
#         try:
#             path = line.split()[0]
#             status = int(line.split("[Status:")[1].split(",")[0])
#         except:
#             continue
#         if status in [200, 301, 302]:
#             full = BASE_URL + "/" + path.strip("/")
#             paths.append(full)
#     return paths


# # -----------------------------
# # COMPILERS (keep your existing compilers)
# # -----------------------------
# def compile_http(a):
#     cmd = ["curl", "-sSfL"]
#     method = a.get("method", "GET").upper()
#     if method == "POST":
#         cmd += ["-X", "POST"]
#     if session["cookie"]:
#         cmd += ["-H", f"Cookie: PHPSESSID={session['cookie']}"]
#     for k, v in a.get("headers", {}).items():
#         cmd += ["-H", f"{k}: {v}"]
#     if "data" in a and a["data"]:
#         cmd += ["-d", a["data"]]
#     cmd.append(BASE_URL + a["url"])
#     return cmd

# def compile_fuzz(a):
#     cmd = [
#         "ffuf",
#         "-u", BASE_URL + a["url"],
#         "-w", "/usr/share/wordlists/dirb/common.txt",
#         "-fc", "404"  # Filter common not-found
#     ]
#     return cmd

# def compile_sqlmap(a):
#     cmd = ["sqlmap", "-u", BASE_URL + a["url"], "--batch"]
#     if "data" in a and a["data"]:
#         cmd += ["--data", a["data"]]
#     if session["cookie"]:
#         cmd += ["--cookie", f"PHPSESSID={session['cookie']}"]
#     return cmd

# def compile_action(action):
#     if action["action"] == "http_request":
#         return compile_http(action)
#     if action["action"] == "fuzz":
#         return compile_fuzz(action)
#     if action["action"] == "sqlmap":
#         return compile_sqlmap(action)
#     return None


# # -----------------------------
# # MAIN AGENT LOOP (with two-agent RAG + validator + retry)
# # -----------------------------
# async def main():
    
#     docker = DockerAgent()
    
#     if not await docker.is_kali_running():
#         await docker.start_lab()
    
#     await docker.install_tool("ffuf")
#     await docker.install_tool("sqlmap")
#     await docker.install_tool("curl")
    
#     # Initialize the two-agent system
#     rag = ToolRAG()
#     strategist = QueryStrategist(rag)
#     builder = CommandBuilder(rag)
#     validator = CommandValidator()
    
#     for step in range(MAX_STEPS):
#         print(f"\n{'='*50}")
#         print(f"STEP {step}")
#         print(f"{'='*50}")
        
#         # Build context for agents
#         step_context = f"Known paths: {list(memory['known_paths'])[:5]}"
#         last_error = memory.get("last_error_detail")
        
#         # ----- TWO-AGENT RAG PROCESS -----
#         # Agent 1: Decide what to retrieve
#         query = strategist.get_query(
#             user_request="Find vulnerabilities in the target",
#             step_context=step_context,
#             last_error=last_error
#         )
#         print(f"[Agent 1 - Query Strategist] → {query}")
        
#         # Retrieve documentation
#         doc = rag.search(query)
#         print(f"[RAG] Retrieved doc for: {query}")
        
#         # Agent 2: Build command with retry loop
#         action = None
#         for retry_count in range(MAX_RETRIES + 1):  # 0, 1 (total 2 attempts)
            
#             if retry_count > 0:
#                 print(f"[Retry {retry_count}] Re-building command with error feedback")
            
#             action = builder.build_command(
#                 user_request="Find vulnerabilities",
#                 doc=doc,
#                 last_error=memory.get("last_error_detail") if retry_count > 0 else None
#             )
            
#             if not action:
#                 print("[!] Failed to parse action JSON")
#                 continue
            
#             # Validate the action
#             is_valid, error_msg = validator.validate(action)
            
#             if is_valid:
#                 print(f"[Validator] ✓ Action valid")
#                 break
#             else:
#                 print(f"[Validator] ✗ Invalid: {error_msg}")
                
#                 # Try to auto-fix
#                 fixed = validator.quick_fix(action, error_msg)
#                 if fixed:
#                     action = fixed
#                     print(f"[Validator] Auto-fixed action")
#                     # Validate again
#                     is_valid, error_msg = validator.validate(action)
#                     if is_valid:
#                         break
                
#                 # Store error for retry
#                 memory["last_error_detail"] = error_msg
        
#         if not action or not validator.validate(action)[0]:
#             print("[!] Could not generate valid action after retries")
#             continue
        
#         print(f"[Agent 2 - Command Builder] → {action}")
        
#         # Compile and execute
#         cmd = compile_action(action)
#         print(f"[CMD] {' '.join(cmd)}")
        
#         try:
#             output = await docker.run_in_kali(cmd)
#             success = True
#             print(f"[OUTPUT]\n{output[:500]}")
#         except Exception as e:
#             output = str(e)
#             success = False
#             print(f"[ERROR] {output}")
        
#         # Classify and store failure
#         failure = classify_failure(output)
        
#         if failure:
#             memory["last_failure"] = failure
#             memory["last_success"] = False
#             if not memory.get("last_error_detail"):
#                 memory["last_error_detail"] = failure
#         else:
#             memory["last_failure"] = None
#             memory["last_success"] = True
#             memory["last_error_detail"] = None
        
#         # Update grounding
#         if action.get("action") == "fuzz":
#             paths = parse_ffuf(output)
#             for p in paths:
#                 memory["known_paths"].add(p)
        
#         # Extract cookies
#         if "Set-Cookie" in output:
#             m = re.search(r"PHPSESSID=([^;]+)", output)
#             if m:
#                 session["cookie"] = m.group(1)
#                 print(f"[Session] Cookie set")
        
#         # History
#         memory["executed_actions"].append({
#             "step": step,
#             "query": query,
#             "action": action,
#             "success": success,
#             "failure": failure,
#             "retries": retry_count
#         })
        
#         os.makedirs("history", exist_ok=True)
#         with open(f"history/step_{step}.json", "w") as f:
#             # Convert set to list for JSON
#             mem_copy = {k: list(v) if isinstance(v, set) else v for k, v in memory.items()}
#             json.dump(mem_copy, f, indent=2)
        
#         # Stop condition
#         if "vulnerable" in output.lower() or "identified" in output.lower():
#             print("\n[+] VULNERABILITY FOUND!")
#             break
        
#         # Respectful delay
#         await asyncio.sleep(1)
    
#     print("\n[+] Pentest completed")


# if __name__ == "__main__":
#     asyncio.run(main())