from langgraph.graph import StateGraph, END
from state import AgentState
from orchestrator import OrchestratorAgent
from network_scan import ReconAgent
from services.neo4j_retriever import Neo4jRetriever
from agents.sqlmap_agent import SQLMapAgent
from tools.sqlmap_executor import SQLMapExecutor
from langchain_ollama import ChatOllama
from models.sqlmap_models import SQLMapCommand, HTTPMethod
import subprocess


def build_graph(llm: ChatOllama, mode: str = "full"):

    graph = StateGraph(AgentState)

    orchestrator = OrchestratorAgent()
    neo4j = Neo4jRetriever()
    sqlmap_agent = SQLMapAgent(llm=llm, neo4j=neo4j)
    sqlmap_executor = SQLMapExecutor()

    async def docker_check_node(state: AgentState):
        return await orchestrator.ensure_lab_ready(state)
    
    async def dvwa_login_node(state: AgentState):
        print("[Graph] Setting up DVWA security level...")
        
        result = subprocess.run(
            ["curl", "-s", "-c", "/tmp/dvwa_cookies.txt", 
             "-d", "username=admin&password=password&Login=Login",
             "http://localhost:8081/login.php"],
            capture_output=True, text=True
        )
        
        result2 = subprocess.run(
            ["curl", "-s", "-b", "/tmp/dvwa_cookies.txt",
             "http://localhost:8081/security.php"],
            capture_output=True, text=True
        )
        
        print("[Graph] DVWA login attempted")
        
        return state

    async def recon_plan_node(state: AgentState):
        recon_agent = ReconAgent(target=state["target"], llm=llm)
        return await recon_agent.request_command(state)

    async def execute_node(state: AgentState):
        return await orchestrator.execute_command(state)

    async def recon_parse_node(state: AgentState):
        recon_agent = ReconAgent(target=state["target"], llm=llm)
        return await recon_agent.parse_and_store(state)

    async def fetch_neo4j_node(state: AgentState):
        await neo4j.connect()
        web_targets = await neo4j.get_web_targets()
        await neo4j.close()
        
        if not web_targets:
            print("[Graph] No web targets in Neo4j. Using default lab targets...")
            web_targets = [
                {"url": "http://localhost:8081/vulnerabilities/sqli/", "parameter": "id", "ip": "localhost", "port": 8081, "auth_required": True},
                {"url": "http://localhost:3000/rest/products/search", "parameter": "q", "ip": "localhost", "port": 3000, "auth_required": False}
            ]
        
        print(f"[Graph] Found {len(web_targets)} web targets from Neo4j")
        
        return {
            **state,
            "web_targets": web_targets,
            "neo4j_data": {"web_targets": web_targets}
        }

    async def sqlmap_plan_node(state: AgentState):
        web_targets = state.get("web_targets", [])
        
        use_llm = True
        commands = await sqlmap_agent.generate_commands_for_targets(web_targets, use_llm=use_llm)
        
        command_strings = [cmd.command for cmd in commands]
        
        print(f"[Graph] Generated {len(command_strings)} SQLMap commands:")
        for i, cmd in enumerate(command_strings):
            print(f"  [{i+1}] {cmd}")
        
        return {
            **state,
            "sqlmap_commands": command_strings
        }

    async def sqlmap_execute_node(state: AgentState):
        commands = state.get("sqlmap_commands", [])
        
        results = []
        
        for cmd in commands:
            try:
                result = await sqlmap_executor.execute_sqlmap(cmd)
                results.append(result)
                
                if result.get("vulnerability_found"):
                    print(f"[Graph] VULNERABILITY FOUND: {result.get('vulnerable_parameter')}")
                
                await neo4j.connect()
                await neo4j.store_sqlmap_workflow(
                    endpoint_url=result.get("command_executed", "").split(" -u ")[1].split(" ")[0] if " -u " in result.get("command_executed", "") else "",
                    sqlmap_command=result.get("command_executed", ""),
                    result_summary=result.get("stdout", "")[:500],
                    vulnerability_found=result.get("vulnerability_found", False)
                )
                await neo4j.close()
                
            except Exception as e:
                print(f"[Graph] Error executing SQLMap: {e}")
                results.append({
                    "command_executed": cmd,
                    "error": str(e),
                    "vulnerability_found": False
                })
        
        return {
            **state,
            "sqlmap_results": results,
            "message": f"SQLMap scan completed. {sum(1 for r in results if r.get('vulnerability_found'))} vulnerabilities found."
        }

    if mode == "recon":
        graph.add_node("docker_check", docker_check_node)
        graph.add_node("recon_plan", recon_plan_node)
        graph.add_node("execute", execute_node)
        graph.add_node("recon_parse", recon_parse_node)
        
        graph.set_entry_point("docker_check")
        graph.add_edge("docker_check", "recon_plan")
        graph.add_edge("recon_plan", "execute")
        graph.add_edge("execute", "recon_parse")
        graph.add_edge("recon_parse", END)
    
    elif mode == "sqlmap":
        graph.add_node("docker_check", docker_check_node)
        graph.add_node("fetch_neo4j", fetch_neo4j_node)
        graph.add_node("sqlmap_plan", sqlmap_plan_node)
        graph.add_node("sqlmap_execute", sqlmap_execute_node)
        
        graph.set_entry_point("docker_check")
        graph.add_edge("docker_check", "fetch_neo4j")
        graph.add_edge("fetch_neo4j", "sqlmap_plan")
        graph.add_edge("sqlmap_plan", "sqlmap_execute")
        graph.add_edge("sqlmap_execute", END)
    
    else:
        graph.add_node("docker_check", docker_check_node)
        graph.add_node("recon_plan", recon_plan_node)
        graph.add_node("execute", execute_node)
        graph.add_node("recon_parse", recon_parse_node)
        graph.add_node("fetch_neo4j", fetch_neo4j_node)
        graph.add_node("sqlmap_plan", sqlmap_plan_node)
        graph.add_node("sqlmap_execute", sqlmap_execute_node)
        
        graph.set_entry_point("docker_check")
        graph.add_edge("docker_check", "recon_plan")
        graph.add_edge("recon_plan", "execute")
        graph.add_edge("execute", "recon_parse")
        graph.add_edge("recon_parse", "fetch_neo4j")
        graph.add_edge("fetch_neo4j", "sqlmap_plan")
        graph.add_edge("sqlmap_plan", "sqlmap_execute")
        graph.add_edge("sqlmap_execute", END)

    return graph.compile()
