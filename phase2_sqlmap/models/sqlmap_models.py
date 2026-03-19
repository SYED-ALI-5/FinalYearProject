from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class ScanLevel(str, Enum):
    LEVEL_1 = "1"
    LEVEL_2 = "2"
    LEVEL_3 = "3"
    LEVEL_4 = "4"
    LEVEL_5 = "5"


class RiskLevel(str, Enum):
    RISK_0 = "0"
    RISK_1 = "1"
    RISK_2 = "2"
    RISK_3 = "3"


class SQLInjectionTechnique(str, Enum):
    BOOLEAN_BASED_BLIND = "boolean-based blind"
    ERROR_BASED = "error-based"
    UNION_QUERY = "union query"
    STACKED_QUERIES = "stacked queries"
    TIME_BASED_BLIND = "time-based blind"
    INLINE_QUERY = "inline query"


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"


class SQLMapCommand(BaseModel):
    url: str = Field(..., description="Target URL to test for SQL injection")
    parameter: str = Field(..., description="Parameter name to test")
    method: HTTPMethod = Field(default=HTTPMethod.GET, description="HTTP method")
    command: str = Field(..., description="Generated SQLMap command")
    risk: int = Field(default=1, ge=0, le=3, description="Risk level 0-3")
    level: int = Field(default=1, ge=1, le=5, description="Test level 1-5")
    techniques: Optional[List[SQLInjectionTechnique]] = Field(
        default=None, description="SQL injection techniques to use"
    )
    batch: bool = Field(default=True, description="Run in batch mode")
    verbose: int = Field(default=1, ge=0, le=6, description="Verbose level")


class ReconEndpoint(BaseModel):
    url: str = Field(..., description="Discovered endpoint URL")
    method: str = Field(default="GET", description="HTTP method")
    parameter: Optional[str] = Field(None, description="Parameter name")
    port: Optional[int] = Field(None, description="Port number")
    service: Optional[str] = Field(None, description="Service name (http/https)")
    host_ip: Optional[str] = Field(None, description="Host IP address")


class SQLMapResult(BaseModel):
    command_executed: str = Field(..., description="SQLMap command that was executed")
    stdout: str = Field(..., description="Standard output from SQLMap")
    stderr: str = Field(default="", description="Standard error from SQLMap")
    return_code: int = Field(..., description="Return code from execution")
    vulnerability_found: bool = Field(..., description="Was vulnerability found")
    vulnerable_parameter: Optional[str] = Field(None, description="Vulnerable parameter")
    database_type: Optional[str] = Field(None, description="Detected database type")
    injection_point: Optional[str] = Field(None, description="Injection point")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")


class WorkflowNode(BaseModel):
    name: str = Field(..., description="Node name in workflow")
    node_type: str = Field(..., description="Type of node")
    properties: dict = Field(default_factory=dict, description="Node properties")


class WorkflowRelationship(BaseModel):
    from_node: str = Field(..., description="Source node")
    to_node: str = Field(..., description="Target node")
    relationship_type: str = Field(..., description="Relationship type")


class AttackWorkflow(BaseModel):
    recon_agent: str = Field(default="ReconAgent", description="Recon agent identifier")
    sqlmap_agent: str = Field(default="SQLMapAgent", description="SQLMap agent identifier")
    docker_agent: str = Field(default="DockerAgent", description="Docker agent identifier")
    endpoints: List[ReconEndpoint] = Field(default_factory=list, description="Discovered endpoints")
    generated_queries: List[SQLMapCommand] = Field(default_factory=list, description="Generated SQLMap commands")
    execution_results: List[SQLMapResult] = Field(default_factory=list, description="Execution results")
