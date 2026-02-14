from typing import Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
import subprocess
from langchain_ollama import ChatOllama
import re
from docker_cmds import run_shell_command, run_docker_compose
from neo4j import GraphDatabase
import xml.etree.ElementTree as ET


llm = ChatOllama(model="deepseek-llm:7b")


class AgentState(TypedDict):
    docker_image: str = "OFF"
    website: str = ""
    message: str = ""


workflow = StateGraph(AgentState)

def docker_agent(state: AgentState):
    docker_image_status = state.get("docker_image", "OFF")

    if docker_image_status == "OFF":
        return {
            "docker_image": "OFF",
            "website": state.get("website", ""),
            "message": "Docker image is turned OFF. No action taken.",
            "__end__": True
        }

    output = run_docker_compose()

    return {
        "docker_image": "ON",
        "website": state.get("website", ""),
        "message": output,
    }

    ## todo: checking the initial status of docker image
def llm_agent(state: AgentState):
    user_input = input("Enter website URL: ").strip()
    # response = llm.invoke(user_input)
    # text = response.content.strip()

    # extracting URL from user input
    found_urls = re.findall(r'(https?://\S+|http://\S+)', user_input)
    if found_urls:
        return {
            "docker_image": state.get("docker_image", "OFF"),
            "website": found_urls[0],
            "message": f"Got website: {found_urls[0]}"
        }

    # No URL → keep asking
    return {
        "docker_image": state.get("docker_image", "OFF"),
        "website": "",
        "message": "No valid URL found in input. Please provide a valid website URL."
    }

def website_agent(state: AgentState):
    website = state.get("website", "")
    if not website:
        return {
            "docker_image": state["docker_image"],
            "website": "",
            "message": "No website provided.",
            "__end__": True
        }

    # command = f"curl -I {website}"
    # output = run_shell_command(command)

    return {
        "docker_image": state["docker_image"],
        "website": website,
        "message": "Url provided"
    }
    

def sqlmap_agent(state: AgentState):
    website = state.get("website", "")
    if not website:
        return {
            "docker_image": state["docker_image"],
            "website": "",
            "message": "No website provided for SQLMap scan.",
            "__end__": True
        }


    command = [
        "docker", "exec", "kali",
        "/root/scripts/run_allowed.sh",
        "sqlmap",
        "-u", f"{website}/vulnerabilities/sqli/?id=1&Submit=Submit",
        "--cookie", "PHPSESSID=jqfr7435v2lml5a54ip1jgmco7; security=low"
    ]

    output = run_shell_command(command)

    return {
        "docker_image": state["docker_image"],
        "website": website,
        "message": output
    }


#-----------------------------------------------------------------------------



class NmapGraphAgent:
    def __init__(self, uri="neo4j://127.0.0.1:7687", user="neo4j", password="12341234"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def run_nmap_in_docker(self, target_ip):
        # Run nmap inside the 'kali' container and get XML output
        # -oX - tells nmap to output XML to stdout
        cmd = ["docker", "exec", "kali", "nmap", "-sV", "-oX", "-", target_ip]
        xml_data = run_shell_command(cmd) # Using your existing function
        return xml_data

    def parse_and_store(self, xml_string):
        root = ET.fromstring(xml_string)
        with self.driver.session() as session:
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
                
                session.run(query, ip=ip, status=status, ports=ports_list)

# Integration into your LangGraph
def nmap_recon_node(state: AgentState):
    target = state.get("website", "dvwa") # 'dvwa' is a hostname in your labnet
    agent = NmapGraphAgent()
    
    xml_results = agent.run_nmap_in_docker(target)
    agent.parse_and_store(xml_results)
    
    return {**state, "message": f"Graph updated for {target}"}







#-----------------------------------------------------------------------------

workflow.add_node(
    "Nmap Graph Agent",
    nmap_recon_node,
)
workflow.add_node(
    "Docker Agent",
    docker_agent,
)
workflow.add_node(
    "LLM Agent",
    llm_agent,
)
workflow.add_node(
    "Website Agent",
    website_agent,
)
workflow.add_node(
    "SQLMap Agent",
    sqlmap_agent,
)
# workflow.set_entry_point("Docker Agent")
# workflow.add_edge("Docker Agent", "LLM Agent")
# workflow.add_edge("LLM Agent", "Website Agent")
# workflow.add_edge("Website Agent", "SQLMap Agent")

def router(state: AgentState):
    # Logic: Look at state or query Neo4j
    if not state.get("website"):
        return "LLM Agent"
    if "nmap" not in state.get("message", "").lower():
        return "Nmap Graph Agent"
    return "SQLMap Agent"

# 1. Start with Docker
workflow.set_entry_point("Docker Agent")
workflow.add_edge("Docker Agent", "LLM Agent")

# 2. LLM Agent handles the user input AND analyzes tool results
# 3. Router decides where to go NEXT based on the latest state
workflow.add_conditional_edges(
    "LLM Agent",
    router,
    {
        "LLM Agent": "LLM Agent",           # If no URL yet, stay here
        "Nmap Graph Agent": "Nmap Graph Agent", 
        "SQLMap Agent": "SQLMap Agent",
        "END": END                          # Add a stop condition
    }
)

# 4. Tools always report back to the "Brain" for analysis
workflow.add_edge("Nmap Graph Agent", "LLM Agent")
workflow.add_edge("SQLMap Agent", "LLM Agent")


app = workflow.compile()
result = app.invoke({
    "docker_image": "ON",
    "website": ""
})
print(result)

