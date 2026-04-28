from Agents.analysis import AnalysisAgent
from Agents.execution import ExecutionAgent
from Agents.feedback import FeedbackAgent
from Agents.plan import PlanningAgent
from state import AgentState
from langgraph.graph import StateGraph, END
from state import AgentState
from Agents.orchestrator import OrchestratorAgent
from Agents.Recon.network_scan import ReconAgent


def build_graph(llm):

    graph = StateGraph(AgentState)

    orchestrator = OrchestratorAgent()
    recon_agent = ReconAgent(target="", llm=llm)
    analysis_agent = AnalysisAgent(llm)
    planning_agent = PlanningAgent(llm)
    execution_agent = ExecutionAgent(orchestrator)
    feedback_agent = FeedbackAgent(llm)

    # ---- Nodes ----

    async def docker_check_node(state: AgentState):
        print("[DockerCheck] Ensuring lab is ready...")
        return await orchestrator.ensure_lab_ready(state)

    async def recon_plan_node(state: AgentState):
        print("[ReconPlan] Planning recon...")
        recon_agent.target = state["target"]
        return await recon_agent.request_command(state)

    ## for recon
    async def execute_node(state: AgentState):
        print("[Execute] Executing command...")
        return await orchestrator.execute_command(state)

    async def recon_parse_node(state: AgentState):
        print("[ReconParse] Parsing Nmap XML...")
        return await recon_agent.parse_and_store(state)
    
    async def analysis_node(state):
        print("[Analysis] Analyzing results...")
        # print('current state',state)
        return await analysis_agent.run(state)

    async def planning_node(state):
        print("[Planning] Creating attack plan...")
        print('current state',state)
        return await planning_agent.run(state)

    ## for planned execution
    async def execution_node(state):
        print("[Execution] Executing command...")
        # print('current state',state)
        return await execution_agent.run(state)

    async def feedback_node(state):
        print("[Feedback] Gathering feedback...")
        return await feedback_agent.run(state)

    # ---- Add Nodes ----
    graph.add_node("docker_check", docker_check_node)
    graph.add_node("recon_plan", recon_plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("recon_parse", recon_parse_node)

    # ---- Edges ----
    graph.add_node("analysis", analysis_node)
    graph.add_node("planning", planning_node)
    graph.add_node("execution", execution_node)
    graph.add_node("feedback", feedback_node)

    # ---- Edges ----
    graph.set_entry_point("docker_check")

    graph.add_edge("docker_check", "recon_plan")
    graph.add_edge("recon_plan", "execute")
    graph.add_edge("execute", "recon_parse")

    # NEW FLOW
    graph.add_edge("recon_parse", "analysis")
    graph.add_edge("analysis", "planning")
    graph.add_edge("planning", "execution")
    graph.add_edge("execution", "feedback")

    # LOOP
    graph.add_conditional_edges(
        "feedback",
        lambda state: "end" if state.get("done") else "execution",
        {
            "execution": "execution",
            "end": END
        }
    )

    return graph.compile()


    # graph.set_entry_point("docker_check")
    # graph.add_edge("docker_check", "recon_plan")
    # graph.add_edge("recon_plan", "execute")
    # graph.add_edge("execute", "recon_parse")
    # graph.add_edge("recon_parse", END)

    # return graph.compile()
