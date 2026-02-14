from state import AgentState
from docker_cmds import DockerAgent

class OrchestratorAgent:
    def __init__(self):
        self.docker_agent = DockerAgent()

    # --------------------------------
    # Ensure lab + Kali running
    # --------------------------------
    async def ensure_lab_ready(self, state):

        print("[Orchestrator] Checking Kali container...")

        running = await self.docker_agent.is_kali_running()

        if not running:
            await self.docker_agent.start_lab()

        return {**state, "docker_status": "ON"}

    # --------------------------------
    # Ensure required tools exist
    # --------------------------------
    async def ensure_tools(self, command: list[str]):
        tool_name = command[0]

        installed = await self.docker_agent.is_tool_installed(tool_name)

        if not installed:
            await self.docker_agent.install_tool(tool_name)

    # --------------------------------
    # Execute command safely
    # --------------------------------
    async def execute_command(self, state):

        command = state.get("command")

        if not command:
            raise ValueError("No command provided")

        print(f"[Orchestrator] Preparing command: {command}")

        # Ensure tool exists
        await self.ensure_tools(command)

        print("[Orchestrator] Executing inside Kali...")

        result = await self.docker_agent.run_in_kali(command)

        return {
            **state,
            "docker_result": result
        }
