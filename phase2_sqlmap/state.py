from typing import TypedDict, Optional, List, Dict, Any
from typing_extensions import NotRequired


class AgentState(TypedDict):
    docker_status: NotRequired[str]
    target: str
    command: NotRequired[List[str]]
    docker_result: NotRequired[str]
    message: NotRequired[str]
    sqlmap_commands: NotRequired[List[str]]
    sqlmap_results: NotRequired[List[Dict[str, Any]]]
    web_targets: NotRequired[List[Dict[str, Any]]]
    neo4j_data: NotRequired[Dict[str, Any]]
