import json
from neo4j import AsyncGraphDatabase
import xml.etree.ElementTree as ET
from state import AgentState

class ReconAgent:
    def __init__(self, target, llm, uri="neo4j://127.0.0.1:7687",
                 user="neo4j", password="12341234"):
        
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.target = target
        self.llm = llm

    async def plan_recon(self, history="") -> list[str]:

        prompt = f"""
    You are an autonomous penetration testing agent.

    Target: {self.target}

    Respond ONLY in valid JSON.

    Format:
    {{
        "tool": "nmap",
        "args": ["-p-", "80,443", "-oX", "-", "{self.target}"]
    }}
    """
        
        response = await self.llm.ainvoke(prompt)

        print("LLM Response:", response.content)

        content = response.content.strip()

        try:
            parsed = json.loads(content)

            tool = parsed["tool"]
            args = parsed["args"]

            print("Parsed LLM Response:", parsed)
            print(f'\n {[tool]} {args}')

            return [tool] + args

        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON from LLM:\n{content}")



    async def request_command(self, state: AgentState) -> AgentState:
        # command = await self.plan_recon()
        command = ["nmap", "-p-", "-oX", "-", self.target]

        return {
            **state,
            "command": command
        }

    async def parse_and_store(self, state: AgentState) -> AgentState:
        xml_string = state.get("docker_result")

        if not xml_string or not xml_string.strip().startswith("<?xml"):
            print("Invalid or non-XML output from nmap:")
            print(xml_string)
            return {**state, "error": "Nmap did not return XML output"}

        root = ET.fromstring(xml_string)

        async with self.driver.session() as session:
            for host in root.findall('host'):
                ip = host.find("address[@addrtype='ipv4']").get('addr')
                status = host.find('status').get('state')
                
                # Cypher query to build the graph
                query = """
                MERGE (h:Host {ip: $ip})
                SET h.status = $status
                WITH h
                UNWIND $ports AS p
                MERGE (port:Port {number: p.portid, protocol: p.protocol})
                MERGE (h)-[:HAS_PORT]->(port)
                MERGE (s:Service {name: p.service_name})
                SET s.product = p.product, s.version = p.version
                MERGE (port)-[:RUNS]->(s)
                """
                
                ports_list = []
                for port in host.findall('.//port'):
                    service = port.find('service')
                    ports_list.append({
                        "portid": int(port.get('portid')),
                        "protocol": port.get('protocol'),
                        "service_name": service.get('name') if service is not None else "unknown",
                        "product": service.get('product') if service is not None else "",
                        "version": service.get('version') if service is not None else ""
                    })
                
                await session.run(query, ip=ip, status=status, ports=ports_list)
        return {
            **state,
            "message": f"Recon completed for {self.target}"
        }

