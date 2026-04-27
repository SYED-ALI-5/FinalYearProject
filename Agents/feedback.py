import json
import re


class FeedbackAgent:

    def __init__(self, llm):
        self.llm = llm

    async def run(self, state):

        prompt = f"""
You are a penetration testing agent.

Step result:
{state.get('step_result')}

Return ONLY valid JSON:

{{
  "decision": "continue | modify | stop",
  "reason": "short explanation",
  "updated_steps": []
}}
"""

        res = await self.llm.ainvoke(prompt)

        content = res.content.strip()

        match = re.search(r"\{.*\}", content, re.DOTALL)

        print("LLM Feedback Response:", content)

        if not match:
            print("⚠️ Invalid LLM response:", content)
            return {**state, "done": True}

        try:
            decision = json.loads(match.group(0))
        except Exception as e:
            print("⚠️ JSON parse error:", e)
            return {**state, "done": True}

        action = decision.get("decision")

        if action == "modify":
            state["attack_plan"]["steps"] = decision.get("updated_steps", [])
            state["current_step"] = 0

        elif action == "stop":
            state["done"] = True

        return state