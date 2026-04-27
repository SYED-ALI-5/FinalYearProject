from pydantic import BaseModel
from typing import List, Literal
import re

class ReconPlan(BaseModel):
    steps: List[Literal[
        "passive_recon",
        "active_scan",
        "service_scan"
    ]]