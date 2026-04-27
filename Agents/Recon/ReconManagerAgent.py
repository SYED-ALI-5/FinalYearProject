import re
from .recon_manager import ReconPlan


class ReconManagerAgent:

    def __init__(self, llm, active_agent, passive_agent):
        self.llm = llm
        self.active_agent = active_agent
        self.passive_agent = passive_agent

    async def plan(self, target: str):

        prompt = f"""
You are a penetration testing planner.

Target: {target}

Choose steps from:
- passive_recon
- active_scan
- service_scan

Return JSON:
{{
  "steps": ["..."]
}}
"""

        response = await self.llm.ainvoke(prompt)
        content = response.content.strip()

        match = re.search(r"\{.*\}", content, re.DOTALL)
        plan = ReconPlan.model_validate_json(match.group(0))

        return plan.steps
    

    async def execute(self, state):

        target = state["target"]
        steps = await self.plan(target)

        print("[ReconManager] Plan:", steps)

        for step in steps:

            if step == "passive_recon":
                state = await self.passive_agent.run(state)

            elif step == "active_scan":
                command = await self.active_agent.plan_recon()
                state["command"] = command

            # elif step == "service_scan":
            #     command = ["nmap", "-sV", "-oX", "-", target]
            #     state["command"] = command

        return state