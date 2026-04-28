# import json
# import re


# class FeedbackAgent:

#     def __init__(self, llm):
#         self.llm = llm

#     async def run(self, state):

#         prompt = f"""
# You are a penetration testing agent.

# Step result:
# {state.get('step_result')}

# Return ONLY valid JSON:

# {{
#   "decision": "continue | modify | stop",
#   "reason": "short explanation",
#   "updated_steps": []
# }}
# """

#         res = await self.llm.ainvoke(prompt)

#         content = res.content.strip()

#         match = re.search(r"\{.*\}", content, re.DOTALL)

#         print("LLM Feedback Response:", content)

#         if not match:
#             print("⚠️ Invalid LLM response:", content)
#             return {**state, "done": True}

#         try:
#             decision = json.loads(match.group(0))
#         except Exception as e:
#             print("⚠️ JSON parse error:", e)
#             return {**state, "done": True}

#         action = decision.get("decision")

#         if action == "modify":
#             state["attack_plan"]["steps"] = decision.get("updated_steps", [])
#             state["current_step"] = 0

#         elif action == "stop":
#             state["done"] = True

#         return state


import json
import re


class FeedbackAgent:

    def __init__(self, llm):
        self.llm = llm

    async def run(self, state):

        FEEDBACK_SYSTEM_PROMPT = """
You are a strict JSON generator for a penetration testing pipeline.

ABSOLUTE RULES:
- Output ONLY valid JSON
- No markdown, no backticks, no explanations
- No text before or after the JSON

Schema:
{
  "decision": "continue | modify | stop",
  "reason": "short explanation",
  "updated_steps": []
}

If decision is "modify", populate updated_steps with corrected step objects like:
{
  "technique": "directorydiscovery | sqli | fuzzing | bruteforce",
  "description": "short explanation",
  "params": {}
}

If decision is "continue" or "stop", updated_steps must be an empty list [].
"""

        prompt = f"""
Step result:
{state.get('step_result', 'No result available')}

Based on this result, decide whether to continue, modify, or stop.
"""

        res = await self.llm.ainvoke([
            {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        content = res.content.strip()
        print("LLM Feedback Response:", content)

        match = re.search(r"\{.*\}", content, re.DOTALL)

        if not match:
            print("⚠️ Invalid LLM response, defaulting to stop")
            return {**state, "done": True}

        try:
            decision = json.loads(match.group(0))
        except Exception as e:
            print("⚠️ JSON parse error:", e)
            return {**state, "done": True}

        action = decision.get("decision", "stop")

        if action == "modify":
            updated_steps = decision.get("updated_steps", [])

            # Guard: only update if attack_plan exists and updated_steps is non-empty
            if "attack_plan" not in state:
                print("⚠️ attack_plan missing from state, stopping")
                return {**state, "done": True}

            if not updated_steps:
                print("⚠️ updated_steps is empty on modify, stopping")
                return {**state, "done": True}

            return {
                **state,
                "attack_plan": {
                    **state["attack_plan"],
                    "steps": updated_steps
                },
                "current_step": 0
            }

        elif action == "stop":
            return {**state, "done": True}

        # "continue" — advance naturally, let execution node handle step index
        return {**state}