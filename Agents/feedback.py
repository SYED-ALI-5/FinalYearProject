# # import json
# # import re


# # class FeedbackAgent:

# #     def __init__(self, llm):
# #         self.llm = llm

# #     async def run(self, state):

# #         FEEDBACK_SYSTEM_PROMPT = """
# # You are a strict JSON generator for a penetration testing pipeline.

# # ABSOLUTE RULES:
# # - Output ONLY valid JSON
# # - No markdown, no backticks, no explanations
# # - No text before or after the JSON

# # Schema:
# # {
# #   "decision": "continue | modify | stop",
# #   "reason": "short explanation",
# #   "updated_steps": []
# # }

# # If decision is "modify", populate updated_steps with corrected step objects like:
# # {
# #   "technique": "directorydiscovery | sqli | fuzzing | bruteforce",
# #   "description": "short explanation",
# #   "params": {}
# # }

# # If decision is "continue" or "stop", updated_steps must be an empty list [].
# # """

# #         prompt = f"""
# # Step result:
# # {state.get('step_result', 'No result available')}

# # Based on this result, decide whether to continue, modify, or stop.
# # """

# #         res = await self.llm.ainvoke([
# #             {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
# #             {"role": "user", "content": prompt}
# #         ])

# #         content = res.content.strip()
# #         print("LLM Feedback Response:", content)

# #         match = re.search(r"\{.*\}", content, re.DOTALL)

# #         if not match:
# #             print("⚠️ Invalid LLM response, defaulting to stop")
# #             return {**state, "done": True}

# #         try:
# #             decision = json.loads(match.group(0))
# #         except Exception as e:
# #             print("⚠️ JSON parse error:", e)
# #             return {**state, "done": True}

# #         action = decision.get("decision", "stop")

# #         if action == "modify":
# #             updated_steps = decision.get("updated_steps", [])

# #             # Guard: only update if attack_plan exists and updated_steps is non-empty
# #             if "attack_plan" not in state:
# #                 print("⚠️ attack_plan missing from state, stopping")
# #                 return {**state, "done": True}

# #             if not updated_steps:
# #                 print("⚠️ updated_steps is empty on modify, stopping")
# #                 return {**state, "done": True}

# #             return {
# #                 **state,
# #                 "attack_plan": {
# #                     **state["attack_plan"],
# #                     "steps": updated_steps
# #                 },
# #                 "current_step": 0
# #             }

# #         elif action == "stop":
# #             return {**state, "done": True}

# #         # "continue" — advance naturally, let execution node handle step index
# #         return {**state}


# # import json
# # import re

# # class FeedbackAgent:

# #     def __init__(self, llm):
# #         self.llm = llm

# #     async def run(self, state):

# #         FEEDBACK_SYSTEM_PROMPT = """
# # You are a penetration testing feedback analyst.

# # ABSOLUTE RULES:
# # - Output ONLY valid JSON
# # - No markdown, no backticks, no explanations

# # VALID STATUS CODES IN PENTESTING (THESE ARE NORMAL, NOT FAILURES):
# # - 200: Success, found something
# # - 301/302: Redirects (normal for web apps)
# # - 403: Forbidden (means path exists but access denied)
# # - 404: Not found (path doesn't exist)
# # - 500: Server error (could indicate a vulnerability)

# # DECISION RULES:
# # - "continue" = tool ran successfully, keep going with NEXT step in plan
# # - "stop" = serious error or vulnerability found
# # - "modify" = ONLY if command syntax error OR tool not found OR truly no useful data

# # Schema:
# # {
# #   "decision": "continue | modify | stop",
# #   "reason": "short explanation (max 1 sentence)",
# #   "updated_steps": []
# # }

# # If decision is "modify", provide corrected steps.
# # Otherwise updated_steps MUST be an empty list [].
# # """

# #         # Get current step and total steps for context
# #         attack_plan = state.get("attack_plan", {})
# #         steps = attack_plan.get("steps", [])
# #         current_idx = state.get("current_step", 0)
# #         total_steps = len(steps)
# #         current_step = steps[current_idx - 1] if current_idx > 0 and steps else None

# #         prompt = f"""
# # Step {current_idx} of {total_steps}
# # Technique used: {current_step.get('technique') if current_step else 'unknown'}
# # Result output:
# # {state.get('step_result', 'No result available')[:1500]}

# # Based on this:
# # - If the tool ran and produced output (even with 403/404/301), that's SUCCESS → continue
# # - Only modify if the command failed entirely or tool not found
# # - Continue moves to the NEXT step in the plan
# # """

# #         res = await self.llm.ainvoke([
# #             {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
# #             {"role": "user", "content": prompt}
# #         ])

# #         content = res.content.strip()
# #         print("LLM Feedback Response:", content[:500])

# #         # Extract JSON
# #         match = re.search(r"\{.*\}", content, re.DOTALL)
# #         if not match:
# #             print("⚠️ Invalid LLM response, defaulting to continue")
# #             # Check if there are more steps
# #             if current_idx < total_steps:
# #                 return {**state}
# #             else:
# #                 return {**state, "done": True}

# #         try:
# #             decision = json.loads(match.group(0))
# #         except Exception as e:
# #             print("⚠️ JSON parse error:", e)
# #             if current_idx < total_steps:
# #                 return {**state}
# #             else:
# #                 return {**state, "done": True}

# #         action = decision.get("decision", "continue")

# #         # For "continue": just let the graph proceed naturally
# #         if action == "continue":
# #             # Check if we've completed all steps
# #             if current_idx >= total_steps:
# #                 return {**state, "done": True}
# #             return {**state}  # Don't modify attack_plan

# #         elif action == "modify":
# #             updated_steps = decision.get("updated_steps", [])
# #             if not updated_steps:
# #                 print("⚠️ updated_steps empty on modify, treating as continue")
# #                 return {**state}
            
# #             return {
# #                 **state,
# #                 "attack_plan": {
# #                     **state["attack_plan"],
# #                     "steps": updated_steps
# #                 },
# #                 "current_step": 0  # Reset to start of new plan
# #             }

# #         elif action == "stop":
# #             return {**state, "done": True}

# #         return {**state}


# import json
# import re

# class FeedbackAgent:

#     def __init__(self, llm):
#         self.llm = llm

#     async def run(self, state):

#         FEEDBACK_SYSTEM_PROMPT = """
# You are a penetration testing feedback analyst.

# ABSOLUTE RULES:
# - Output ONLY valid JSON
# - No markdown, no backticks, no explanations

# STEP OBJECT FORMAT (MUST FOLLOW EXACTLY):
# {
#   "technique": "directorydiscovery | sqli | fuzzing | bruteforce",
#   "description": "string describing what to do",
#   "params": {}
# }

# VALID STATUS CODES IN PENTESTING (THESE ARE NORMAL, NOT FAILURES):
# - 200: Success, found something
# - 301/302: Redirects (normal for web apps)
# - 403: Forbidden (means path exists but access denied)
# - 404: Not found (path doesn't exist)

# DECISION RULES:
# - "continue" = tool ran successfully, keep going with NEXT step in plan
# - "stop" = serious error or vulnerability found
# - "modify" = ONLY if command syntax error OR tool not found OR truly no useful data

# When modifying, updated_steps MUST be an array of step objects with the EXACT format above.

# Schema:
# {
#   "decision": "continue | modify | stop",
#   "reason": "short explanation (max 1 sentence)",
#   "updated_steps": []  # Array of step objects, NOT strings
# }
# """

#         # Get current context
#         attack_plan = state.get("attack_plan", {})
#         steps = attack_plan.get("steps", [])
#         current_idx = state.get("current_step", 0)
#         total_steps = len(steps)
#         current_step = steps[current_idx - 1] if current_idx > 0 and steps else None

#         prompt = f"""
# Current step index: {current_idx} of {total_steps}
# Current technique: {current_step.get('technique') if current_step else 'unknown'}
# Result output:
# {state.get('step_result', 'No result available')[:1500]}

# Based on this:
# - If the tool produced valid output (even with 403/404/301), that's SUCCESS → continue
# - Only modify if the command failed entirely
# - If modifying, provide COMPLETE step objects with technique, description, and params
# """

#         res = await self.llm.ainvoke([
#             {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt}
#         ])

#         content = res.content.strip()
#         print("LLM Feedback Response:", content[:500])

#         # Extract JSON
#         match = re.search(r"\{.*\}", content, re.DOTALL)
#         if not match:
#             print("⚠️ Invalid LLM response, defaulting to continue")
#             if current_idx < total_steps:
#                 return {**state}
#             else:
#                 return {**state, "done": True}

#         try:
#             decision = json.loads(match.group(0))
#         except Exception as e:
#             print("⚠️ JSON parse error:", e)
#             if current_idx < total_steps:
#                 return {**state}
#             else:
#                 return {**state, "done": True}

#         action = decision.get("decision", "continue")

#         if action == "continue":
#             if current_idx >= total_steps:
#                 return {**state, "done": True}
#             return {**state}

#         elif action == "modify":
#             updated_steps = decision.get("updated_steps", [])
            
#             # VALIDATE updated_steps are proper step objects
#             if not updated_steps:
#                 print("⚠️ updated_steps empty on modify, treating as continue")
#                 return {**state}
            
#             # Check if steps are strings (bad) or dicts (good)
#             if isinstance(updated_steps[0], str):
#                 print("⚠️ FeedbackAgent returned string steps instead of dicts. Ignoring modify.")
#                 return {**state}
            
#             # Validate each step has required fields
#             valid_steps = []
#             for step in updated_steps:
#                 if isinstance(step, dict) and "technique" in step:
#                     valid_steps.append(step)
#                 else:
#                     print(f"⚠️ Invalid step format: {step}")
            
#             if not valid_steps:
#                 print("⚠️ No valid steps in modify, treating as continue")
#                 return {**state}
            
#             return {
#                 **state,
#                 "attack_plan": {
#                     "steps": valid_steps
#                 },
#                 "current_step": 0,
#                 "done": False
#             }

#         elif action == "stop":
#             return {**state, "done": True}

#         return {**state}


import json
import re
from typing import Dict, Any

class FeedbackAgent:
    def __init__(self, llm):
        self.llm = llm

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # ---------- DETERMINISTIC SUCCESS DETECTION ----------
        step_result = state.get("step_result", "")
        attack_plan = state.get("attack_plan", {})
        steps = attack_plan.get("steps", [])
        current_idx = state.get("current_step", 0)

        # If there's no current step, just continue
        if current_idx == 0 or not steps or current_idx > len(steps):
            return {**state}

        current_step = steps[current_idx - 1]
        technique = current_step.get("technique")

        # --- SUCCESS if we got ANY parseable ffuf output ---
        if technique == "directorydiscovery":
            # Quick parse to see if we got results
            if self._has_ffuf_results(step_result):
                print("[Feedback] 🟢 Directory discovery found results → continue")
                # Move to next step automatically
                return {**state}

        # --- For SQLMap: success if no critical error ---
        if technique == "sqli" and step_result:
            if "error" not in step_result.lower() or "vulnerable" in step_result.lower():
                print("[Feedback] 🟢 SQLMap ran without fatal error → continue")
                return {**state}

        # --- If no deterministic success, ask LLM (but with strong guardrails) ---
        return await self._llm_feedback(state)

    def _has_ffuf_results(self, output: str) -> bool:
        """Return True if output contains any status line (200/301/403 etc.)"""
        if not output:
            return False
        # Look for typical ffuf line pattern
        return bool(re.search(r'\[Status:\s*\d+', output))

    async def _llm_feedback(self, state: Dict[str, Any]) -> Dict[str, Any]:
        FEEDBACK_SYSTEM_PROMPT = """
You are a penetration testing feedback analyst. Output ONLY valid JSON.

STEP OBJECT FORMAT:
{"technique": "directorydiscovery|sqli|fuzzing|bruteforce", "description": "...", "params": {}}

VALID STATUS CODES ARE NORMAL: 200, 301, 302, 403, 404 → means tool worked.

DECISION RULES:
- "continue" → tool ran successfully (move to next step)
- "stop" → tool failed completely (command not found, invalid flags)
- "modify" → ONLY if command syntax error or missing tool.

MODIFY EXAMPLE (rare):
  If tool = "ffuf" fails because wordlist missing → update command.

OUTPUT SCHEMA:
{"decision": "continue|modify|stop", "reason": "short", "updated_steps": []}
"""
        attack_plan = state.get("attack_plan", {})
        steps = attack_plan.get("steps", [])
        current_idx = state.get("current_step", 0)
        current_step = steps[current_idx - 1] if steps and current_idx > 0 else None

        prompt = f"""
Current technique: {current_step.get('technique') if current_step else 'unknown'}
Result snippet:
{state.get('step_result', '')[:1000]}

Decide: continue (most cases), only modify if command invalid.
"""

        res = await self.llm.ainvoke([
            {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        try:
            content = res.content.strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("No JSON found")
            decision = json.loads(match.group(0))
        except Exception as e:
            print(f"[Feedback] LLM parse error: {e}, defaulting to continue")
            return {**state}

        action = decision.get("decision", "continue")

        if action == "continue":
            return {**state}

        if action == "modify":
            updated_steps = decision.get("updated_steps", [])
            # Validate that updated steps are properly formatted
            valid_techniques = {"directorydiscovery", "sqli", "fuzzing", "bruteforce"}
            valid = True
            for step in updated_steps:
                if not isinstance(step, dict) or step.get("technique") not in valid_techniques:
                    valid = False
                    break
            if not valid:
                print("[Feedback] Invalid modify steps – ignoring modify")
                return {**state}
            return {
                **state,
                "attack_plan": {"steps": updated_steps},
                "current_step": 0,
                "done": False
            }

        if action == "stop":
            return {**state, "done": True}

        return {**state}