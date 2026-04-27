# import json
# import re


# class PlanningAgent:

#     def __init__(self, llm):
#         self.llm = llm

#     async def run(self, state):

#         prompt = f"""
# You are an offensive security planner.

# Target: {state['target']}
# Services:
# {state.get('services')}

# DO NOT use escape characters like \_ or \n or \t
# Return ONLY JSON:

# {{
#   "attack_plan": {{
#     "steps": [
#       {{
#         "technique": "directory_discovery | sql_injection | fuzzing | brute_force",
#         "description": "short explanation",
#         "params": {{}}
#       }}
#     ]
#   }}
# }}

# Rules:
# - MUST include "technique"
# - Steps must be executable
# - No vague steps like "find vulnerabilities"
# """

#         res = await self.llm.ainvoke(prompt)

#         content = res.content.strip()

#         match = re.search(r"\{.*\}", content, re.DOTALL)

#         if not match:
#             print("⚠️ Invalid planning response:", content)
#             return {**state, "done": True, "error": "Invalid planning JSON"}
        
#         print("LLM Planning Raw Response:", content)
#         try:
#             plan = json.loads(match.group(0))
#         except Exception as e:
#             print("⚠️ JSON parse error:", e)
#             return {**state, "done": True, "error": "Malformed planning JSON"}

#         print("LLM Planning Response:", plan)

#         steps = plan.get("attack_plan", {}).get("steps", [])

#         if not steps:
#             return {**state, "done": True, "error": "Empty attack plan"}

#         for step in steps:
#             if "technique" not in step:
#                 return {**state, "done": True, "error": f"Invalid step: {step}"}

#         return {
#             **state,
#             "attack_plan": plan["attack_plan"],  # ✅ FIXED
#             "current_step": 0
#         }


from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Literal

class Step(BaseModel):
    technique: Literal[
        "directory_discovery",
        "sql_injection",
        "fuzzing",
        "brute_force"
    ]
    description: str
    params: Dict = Field(default_factory=dict)

class AttackPlan(BaseModel):
    steps: List[Step]

class PlanningOutput(BaseModel):
    attack_plan: AttackPlan




import json

class PlanningAgent:

    def __init__(self, llm):
        self.llm = llm

    async def run(self, state):

        PLANNING_SYSTEM_PROMPT = """
You are a strict JSON generator.

ABSOLUTE RULES:
- Output ONLY valid JSON
- No markdown
- No backticks
- No explanations
- No extra characters before or after JSON
- DO NOT use escape characters like \_ or \n or \t


Schema:
{
  "attack_plan": {
    "steps": [
      {
        "technique": "directorydiscovery | sqli | fuzzing | bruteforce",
        "description": "short explanation",
        "params": {}
      }
    ]
  }
}
"""

        prompt = f"""
Target: {state['target']}
Services:
{state.get('services')}
"""

        res = await self.llm.ainvoke([
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        content = res.content.strip()

        try:
            raw = json.loads(content)  # 🔥 direct parse (no regex)

            validated = PlanningOutput.model_validate(raw)

            print("Validated Planning Output:", validated)

        except Exception as e:
            return {
                **state,
                "error": f"invalid_plan_json: {str(e)}",
                "done": True
            }

        return {
            **state,
            "attack_plan": validated.attack_plan.model_dump(),
            "current_step": 0
        }