# from typing import TypedDict, Optional, List
# from typing_extensions import NotRequired

# class AgentState(TypedDict):
#     docker_status: NotRequired[str]   # "ON" | "OFF"
#     target: str
#     command: Optional[List[str]]
#     docker_result: Optional[str]
#     message: Optional[str]


from typing import TypedDict, Optional, List, Dict, Any
from typing_extensions import NotRequired


class AgentState(TypedDict):

    # --- Core ---
    target: str
    docker_status: NotRequired[str]

    # --- Execution ---
    command: Optional[List[str]]
    docker_result: Optional[str]

    # --- Recon Data ---
    services: NotRequired[List[Dict[str, Any]]]   # from Neo4j

    # --- LLM Reasoning ---
    analysis: NotRequired[str]

    # --- Planning ---
    attack_plan: NotRequired[Dict[str, Any]]
    current_step: NotRequired[int]

    # --- Step Execution ---
    step_result: NotRequired[Any]
    # step_completed: NotRequired[bool]

    # --- Control ---
    done: NotRequired[bool]
    message: Optional[str]
