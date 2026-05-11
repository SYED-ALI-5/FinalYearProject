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


# from curses import raw
# from pydantic import BaseModel, Field, field_validator
# from typing import List, Dict, Literal

# class Step(BaseModel):
#     technique: Literal[
#         "directorydiscovery",
#         "sqli",
#         "fuzzing",
#         "bruteforce"
#     ]
#     description: str
#     params: Dict = Field(default_factory=dict)

# class AttackPlan(BaseModel):
#     steps: List[Step]

# class PlanningOutput(BaseModel):
#     attack_plan: AttackPlan




# import json

# class PlanningAgent:

#     def __init__(self, llm):
#         self.llm = llm

#     async def run(self, state):

#         PLANNING_SYSTEM_PROMPT = """
# You are a strict JSON generator.

# ABSOLUTE RULES:
# - Output ONLY valid JSON
# - No markdown
# - No backticks
# - No explanations
# - No extra characters before or after JSON
# - DO NOT use escape characters like \_ or \n or \t


# Schema:
# {
#   "attack_plan": {
#     "steps": [
#       {
#         "technique": "directorydiscovery [EXAMPLE]",
#         "description": "short explanation",
#         "params": {}
#       }
#     ]
#   }
# }
# YOU SHOULD ONLY USE: directorydiscovery | sqli | fuzzing | bruteforce
# """

#         prompt = f"""
# Target: {state['target']}
# Services:
# {state.get('services')}
# """

#         res = await self.llm.ainvoke([
#             {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt}
#         ])

#         content = res.content.strip()
#         print("LLM Planning Raw Response:", content)

#         try:
#             raw = json.loads(content)

#             validated = PlanningOutput.model_validate(raw)

#             print("Validated Planning Output:", validated)

#         except Exception as e:
#             return {
#                 **state,
#                 "error": f"invalid_plan_json: {str(e)}",
#                 "done": True
#             }

#         return {
#             **state,
#             "attack_plan": validated.attack_plan.model_dump(),
#             "current_step": 0
#         }


from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Literal
import json

class Step(BaseModel):
    technique: Literal["spidering", "sqli"]
    description: str
    params: Dict = Field(default_factory=dict)

    @field_validator("technique")
    @classmethod
    def validate_technique(cls, v):
        # Normalise common LLM mistakes
        v = v.lower().strip()
        if v in ["sql injection", "sqli"]:
            return "sqli"
        if v not in {"spidering", "sqli"}:
            raise ValueError(f"Invalid technique: {v}")
        return v

class AttackPlan(BaseModel):
    steps: List[Step]

class PlanningOutput(BaseModel):
    attack_plan: AttackPlan

class PlanningAgent:
    def __init__(self, llm):
        self.llm = llm

    async def run(self, state):
        PLANNING_SYSTEM_PROMPT = """
You are a strict JSON generator. Output ONLY the exact JSON object described below.

IMPORTANT: Use ONLY these two technique values exactly: "spidering" or "sqli"
         No other words, no variations like "SQL injection" or "spider".

Schema:
{
  "attack_plan": {
    "steps": [
      {
        "technique": "spidering",
        "description": "short explanation",
        "params": {}
      }
    ]
  }
}
"""
        prompt = f"""
Target: {state['target']}
Services: {state.get('services')}

Create an attack plan with EXACTLY these steps:
1. "spidering" – crawl the web app to discover all endpoints
2. "sqli" – run sqlmap on the most promising endpoint found by spidering
"""
        res = await self.llm.ainvoke([
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        content = res.content.strip()
        print("LLM Planning Raw Response:", content)

        try:
            raw = json.loads(content)
            # Force the plan to exactly match spidering then sqli
            validated = PlanningOutput.model_validate(raw)
        except Exception as e:
            # If LLM still messes up, use a deterministic fallback
            print(f"[Planning] Fallback due to error: {e}")
            validated = PlanningOutput(attack_plan=AttackPlan(steps=[
                Step(technique="spidering", description="Crawl target for endpoints"),
                Step(technique="sqli", description="Test SQL injection on discovered endpoints")
            ]))

        print("Validated / Fallback Plan:", validated)
        return {
            **state,
            "attack_plan": validated.attack_plan.model_dump(),
            "current_step": 0
        }