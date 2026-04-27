class ExecutionAgent:

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def run(self, state):

        if "attack_plan" not in state:
            return {**state, "done": True, "error": "Missing attack_plan"}

        plan = state.get("attack_plan", {})
        steps = plan.get("steps", [])

        idx = state.get("current_step", 0)

        if idx >= len(steps):
            return {**state, "done": True}

        step = steps[idx]

        command = self.build_command(step, state["target"])

        if not command:
            return {**state, "done": True, "error": f"Unsupported step: {step}"}

        result = await self.orchestrator.execute_command({
            **state,
            "command": command
        })

        return {
            **result,
            "step_result": result.get("docker_result"),
            "current_step": idx + 1
        }

    def build_command(self, step, target):

        technique = step.get("technique")

        if technique == "directorydiscovery":
            return ["ffuf", "-u", f"http://{target}/FUZZ", "-w", "common.txt"]

        if technique == "sqli":
            return ["sqlmap", "-u", f"http://{target}/login.php", "--batch"]

        return None