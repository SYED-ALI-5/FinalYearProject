import json
import re


class AnalysisAgent:

    def __init__(self, llm):
        self.llm = llm


    async def run(self, state):

        ANALYSIS_SYSTEM_PROMPT = """
You are a security analysis engine.

You MUST:
- Only output JSON
- Never include explanations
- Extract structured attack surface from scan data

SCHEMA:
{
  "services": [
    {
      "ip": "",
      "status": "up|down",
      "ports": [
        {
          "port": 0,
          "service": "",
          "product": "",
          "version": ""
        }
      ]
    }
  ]
}
"""

        res = await self.llm.ainvoke([
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": state["docker_result"]}
        ])

        content = res.content.strip()

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return {**state, "error": "analysis_failed"}

        data = json.loads(match.group(0))

        print("LLM Analysis Response:", data)

        return {
            **state,
            "services": data["services"]
        }

#     async def run(self, state):

#         services = state.get("services")

#         prompt = f"""
# Analyze the attack surface:
# {services}
# """

#         res = await self.llm.ainvoke(prompt)

#         print("LLM Analysis Response:", res.content)

#         return {
#             **state,
#             "analysis": res.content
#         }
    

