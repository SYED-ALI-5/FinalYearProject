from langgraph.graph import StateGraph, END
from state import AgentState
from orchestrator import OrchestratorAgent
from network_scan import ReconAgent


def build_graph(llm):

    graph = StateGraph(AgentState)

    orchestrator = OrchestratorAgent()
    recon_agent = ReconAgent(target="", llm=llm)

    # ---- Nodes ----

    async def docker_check_node(state: AgentState):
        return await orchestrator.ensure_lab_ready(state)

    async def recon_plan_node(state: AgentState):
        recon_agent.target = state["target"]
        return await recon_agent.request_command(state)

    async def execute_node(state: AgentState):
        return await orchestrator.execute_command(state)

    async def recon_parse_node(state: AgentState):
        return await recon_agent.parse_and_store(state)
    
    

    # ---- Add Nodes ----
    graph.add_node("docker_check", docker_check_node)
    graph.add_node("recon_plan", recon_plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("recon_parse", recon_parse_node)

    # ---- Edges ----
    graph.set_entry_point("docker_check")
    graph.add_edge("docker_check", "recon_plan")
    graph.add_edge("recon_plan", "execute")
    graph.add_edge("execute", "recon_parse")
    graph.add_edge("recon_parse", END)

    return graph.compile()
