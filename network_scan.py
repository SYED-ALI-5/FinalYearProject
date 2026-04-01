import xml.etree.ElementTree as ET
from typing import List, Optional
import re
import json
from distro import name
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field, ValidationError, field_validator

from state import AgentState


# -----------------------------
# Pydantic Models
# -----------------------------

class ReconCommand(BaseModel):
    """LLM command schema"""

    tool: str = Field(..., description="Tool to run")
    args: List[str] = Field(..., description="Arguments for the tool")

    @field_validator("tool")
    @classmethod
    def validate_tool(cls, v: str) -> str:
        allowed_tools = {"nmap"}
        if v not in allowed_tools:
            raise ValueError(f"Unauthorized tool requested: {v}")
        return v


class PortModel(BaseModel):
    """Port information extracted from Nmap"""

    portid: int
    protocol: str
    service_name: str = "unknown"
    product: Optional[str] = ""
    version: Optional[str] = ""


class HostModel(BaseModel):
    """Host representation"""

    ip: str
    status: str
    ports: List[PortModel]

# -----------------------------
# Recon Agent
# -----------------------------

class ReconAgent:

    def __init__(
        self,
        target: str,
        llm,
        uri: str = "neo4j://127.0.0.1:7687",
        user: str = "neo4j",
        password: str = "testpassword",
    ):
        self.target = target
        self.llm = llm
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))


    # -----------------------------
    # LLM Recon Planning
    # -----------------------------

    async def plan_recon(self, history: str = "") -> List[str]:

        prompt = f"""
You are an autonomous penetration testing agent.

Target: {self.target}

Respond ONLY in valid JSON.

Format:
{{
    "tool": "nmap",
    "args": ["-p-", "-oX", "-", "{self.target}"]
}}
"""

        response = await self.llm.ainvoke(prompt)

        content = response.content.strip()

        print("LLM Response:", content)

        try:

            # Remove markdown code fences if present
            content = content.strip()

            # Extract JSON block
            match = re.search(r"\{.*\}", content, re.DOTALL)

            if not match:
                raise ValueError(f"No JSON found in LLM response:\n{content}")

            json_text = match.group(0)

            # Validate JSON using Pydantic
            command = ReconCommand.model_validate_json(json_text)

            print("Validated Command:", command)

            return [command.tool] + command.args

        except ValidationError as e:
            raise RuntimeError(
                f"Invalid LLM response format:\n{content}\n\nValidation error:\n{e}"
            )


    # -----------------------------
    # Request Command
    # -----------------------------

    async def request_command(self, state: AgentState):

        print("[ReconAgent] Planning recon...")

        try:
            command = await self.plan_recon()
            print("[ReconAgent] Command generated:", command)

        except Exception as e:
            print("[ReconAgent] Planning failed:", e)
            return {**state, "error": str(e)}

        return {**state, "command": command}


    # -----------------------------
    # Parse Nmap XML
    # -----------------------------

    def _parse_nmap_xml(self, xml_string: str) -> List[HostModel]:

        if not xml_string or not xml_string.strip().startswith("<?xml"):
            raise ValueError("Invalid XML returned from nmap")

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            raise ValueError(f"Nmap XML parsing failed: {e}")

        hosts: List[HostModel] = []

        for host in root.findall("host"):

            address_node = host.find("address[@addrtype='ipv4']")
            status_node = host.find("status")

            if address_node is None or status_node is None:
                continue

            ip = address_node.get("addr")
            status = status_node.get("state")

            ports: List[PortModel] = []

            for port in host.findall(".//port"):

                service = port.find("service")

                ports.append(
                    PortModel(
                        portid=int(port.get("portid")),
                        protocol=port.get("protocol"),
                        service_name=service.get("name") if service is not None else "unknown",
                        product=service.get("product") if service is not None else "",
                        version=service.get("version") if service is not None else "",
                    )
                )

            hosts.append(
                HostModel(
                    ip=ip,
                    status=status,
                    ports=ports
                )
            )

        return hosts


    # -----------------------------
    # Store Results in Neo4j
    # -----------------------------

    async def generate_cypher(self, hosts: List[HostModel]):

        hosts_json = json.dumps([h.model_dump() for h in hosts], indent=2)

        prompt = f"""
                    You are an expert Neo4j Cypher engineer.

                    Data example:
                    __DATA__

                    Your task is to generate a valid Cypher query to store Nmap scan results in a Neo4j graph database.

                    IMPORTANT RULES (must be followed strictly):

                    1. The query will receive the following parameters:
                       $ip      → string
                       $status  → string
                       $ports   → list of objects

                    2. Each port object inside $ports contains:
                       portid
                       protocol
                       service_name
                       product
                       version

                    3. The query MUST start by creating or updating the Host node:

                    MERGE (h:Host {{ip: $ip}})
                    SET h.status = $status

                    4. Because Cypher requires variable scoping, you MUST include:

                    WITH h

                    before using UNWIND.

                    5. Ports must be processed using:

                    UNWIND $ports AS p

                    6. Graph schema:

                    Nodes:
                    Host(ip, status)
                    Port(number, protocol)
                    Service(name, product, version)

                    Relationships:
                    Host-[:HAS_PORT]->Port
                    Port-[:RUNS]->Service

                    7. Port fields must be accessed ONLY like this:
                    p.portid
                    p.protocol
                    p.service_name
                    p.product
                    p.version

                    8. The query must create the following structure:

                    Host → HAS_PORT → Port → RUNS → Service

                    9. Do NOT create parameters like:
                    $portid
                    $protocol
                    $service_name

                    Only use values from `p`.

                    10. The output must be ONLY a valid Cypher query.

                    Do NOT include:
                    - explanations
                    - markdown
                    - ``` fences
                    - comments

                    Data example:
                    {hosts_json}

                    11. Some service fields may be null.

                    NEVER use nullable properties in MERGE.

                    Service nodes MUST be created using ONLY the service name:

                    MERGE (s:Service {{name: p.service_name}})

                    Optional properties must be assigned using SET with coalesce():

                    SET s.product = coalesce(p.product, "unknown"),
                    s.version = coalesce(p.version, "unknown")

                    EXAMPLE:
                    MERGE (h:Host {{ip: $ip}})
                    SET h.status = $status

                    WITH h
                    UNWIND $ports AS p

                    MERGE (port:Port {{number:p.portid, protocol:p.protocol}})
                    MERGE (h)-[:HAS_PORT]->(port)

                    MERGE (s:Service {{name:p.service_name}})
                    SET s.product = coalesce(p.product,"unknown"),
                    s.version = coalesce(p.version,"unknown")

                    MERGE (port)-[:RUNS]->(s)
        """
        prompt = prompt.replace("__DATA__", hosts_json)

        response = await self.llm.ainvoke(prompt)

        return response.content.strip()
    
    def clean_cypher(self, query: str) -> str:
        query = query.strip()

        query = re.sub(r"```cypher", "", query, flags=re.IGNORECASE)
        query = re.sub(r"```", "", query)

        return query.strip()
    
    def validate_cypher(self, query: str) -> str:

        banned = ["DELETE", "DETACH", "DROP", "REMOVE", "CALL", "LOAD CSV"]

        upper_query = query.upper()

        for word in banned:
            if word in upper_query:
                raise ValueError(f"Dangerous Cypher detected: {word}")

        return query

    async def _store_hosts(self, hosts: List[HostModel]):

        query = await self.generate_cypher(hosts)
        query = self.clean_cypher(query)
        query = self.validate_cypher(query)

        async with self.driver.session() as session:

            for host in hosts:

                await session.run(
                    query,
                    ip=host.ip,
                    status=host.status,
                    ports=[p.model_dump() for p in host.ports],
                )

    # -----------------------------
    # Parse + Store Pipeline
    # -----------------------------

    async def parse_and_store(self, state: AgentState) -> AgentState:

        xml_string = state.get("docker_result")

        if not xml_string:
            return {
                **state,
                "error": "No scan result found"
            }

        try:

            hosts = self._parse_nmap_xml(xml_string)

            await self._store_hosts(hosts)

        except Exception as e:

            print("Parsing error:", e)

            return {
                **state,
                "error": str(e)
            }

        return {
            **state,
            "message": f"Recon completed for {self.target}"
        }


    # -----------------------------
    # Close Database Connection
    # -----------------------------

    async def close(self):
        await self.driver.close()