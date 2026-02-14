from typing import TypedDict, Optional, List
from typing_extensions import NotRequired

class AgentState(TypedDict):
    docker_status: NotRequired[str]   # "ON" | "OFF"
    target: str
    command: Optional[List[str]]
    docker_result: Optional[str]
    message: Optional[str]
