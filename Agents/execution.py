import datetime
import json
import os
import re
from neo4j import AsyncGraphDatabase


class ExecutionAgent:

    def __init__(self,
                orchestrator,
                uri: str = "neo4j://127.0.0.1:7687",
                user: str = "neo4j",
                password: str = "12341234",
                ):
        self.orchestrator = orchestrator
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def run(self, state):

        print("\n[ExecutionAgent] Running...")

        plan = state.get("attack_plan")
        if not plan or "steps" not in plan:
            return {**state, "done": True, "error": "Invalid attack_plan"}

        if "attack_plan" not in state:
            print("\n[ExecutionAgent] Missing attack_plan")
            return {**state, "done": True, "error": "Missing attack_plan"}

        print("\n[ExecutionAgent] Attack plan:", state["attack_plan"])
        
        steps = plan.get("steps", [])

        idx = state.get("current_step", 0)

        if idx >= len(steps):
            return {**state, "done": True}

        step = steps[idx]
        print("\n[ExecutionAgent] Current step:", step, '\n')

        command = self.build_command(step, state["target"])
        print("\n[ExecutionAgent] Built command:", command, '\n')

        if not command:
            return {**state, "done": True, "error": f"Unsupported step: {step}"}

        result = await self.orchestrator.execute_command({
            **state,
            "command": command
        })

        technique = step.get("technique")
        target = state["target"]

        output_file = None

        raw_output = result.get("docker_result", "")
        parsed_output = None

        if technique == "directorydiscovery":
            parsed_output = self.parse_ffuf_terminal_output(raw_output)
            await self._store_directorydiscovery(target, parsed_output)

            output_file = f"docker/kali-home/output/ffuf_{target}.json"

        elif technique == "sqli":
            output_file = f"docker/kali-home/output/sqlmap"

        # Try reading output
        parsed_output = None

        if output_file and os.path.exists(output_file):
            try:
                print("Reading output from:", output_file)
                if output_file.endswith(".json"):
                    print("writing in history")
                    with open(output_file) as f:
                        parsed_output = json.load(f)
                else:
                    parsed_output = "sqlmap results stored"

                os.makedirs("history", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                history_file = f"history/{technique}_{target}_{timestamp}.json"

                with open(history_file, "w") as f:
                    json.dump({
                        "timestamp": timestamp,
                        "technique": technique,
                        "target": target,
                        "command": command,
                        "result": result.get("docker_result")
                    }, f, indent=2)

                print(f"[ExecutionAgent] History written to: {history_file}")
            except Exception as e:
                parsed_output = f"parse_error: {str(e)}"

        return {
            **result,
            "step_result": result.get("docker_result"),
            "parsed_output": parsed_output,
            "current_step": idx + 1
        }

    def build_command(self, step, target):

        technique = step.get("technique")

        if technique == "directorydiscovery":
            return [
                "ffuf",
                "-u", f"http://{target}/FUZZ",
                "-w", "/usr/share/wordlists/dirb/common.txt",
                "-o", f"/root/output/ffuf_{target}.json",
                "-of", "json"
            ]

        if technique == "sqli":
            return [
                "sqlmap",
                "-u", f"http://{target}/login.php",
                "--batch",
                "--output-dir=/root/output/sqlmap"
            ]

        return None
    
    def parse_ffuf_terminal_output(self, raw: str) -> list:
        ansi_escape = re.compile(r'\r?\x1b\[[0-9;]*[A-Za-z]|\x1b\[[0-9]*K')
        clean = ansi_escape.sub('', raw)

        results = []
        pattern = re.compile(
            r'(\S+)?\s+\[Status:\s*(\d+),\s*Size:\s*(\d+),\s*Words:\s*(\d+),\s*Lines:\s*(\d+),\s*Duration:\s*(\S+)\]'
        )

        for match in pattern.finditer(clean):
            path, status, size, words, lines, duration = match.groups()
            results.append({
                "path": path.strip() if path else "/",
                "status": int(status),
                "size": int(size),
                "words": int(words),
                "lines": int(lines),
                "duration": duration
            })

        return results

    def parse_curl_output(self, raw: str, path: str) -> dict:
        clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', raw).strip()
        return {
            "path": path,
            "content": clean,
            "length": len(clean)
        }

    # -----------------------------
    # Neo4j Store Methods
    # -----------------------------

    async def _store_directorydiscovery(self, target: str, results: list):
        """
        Graph: (Host)-[:HAS_PATH]->(DiscoveredPath)
        """
        query = """
        MERGE (h:Host {ip: $target})
        WITH h
        UNWIND $results AS r
        MERGE (p:DiscoveredPath {path: r.path, host: $target})
        SET p.status   = r.status,
            p.size     = r.size,
            p.words    = r.words,
            p.lines    = r.lines,
            p.duration = r.duration
        MERGE (h)-[:HAS_PATH]->(p)
        """
        await self._run_query(query, {"target": target, "results": results})
        print(f"[Neo4j] Stored {len(results)} discovered paths for {target}")

    async def _run_query(self, query: str, params: dict):
        try:
            async with self.driver.session() as session:
                await session.run(query, **params)
        except Exception as e:
            print(f"[Neo4j] Query failed: {e}")

    
    async def close(self):
        await self.driver.close()
