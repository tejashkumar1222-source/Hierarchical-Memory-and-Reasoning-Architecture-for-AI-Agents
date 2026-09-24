"""
HMRA Orchestration Message and Context Definitions
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ExecutionTraceStep(BaseModel):
    stage: str
    actor: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None

class OrchestratorResult(BaseModel):
    execution_id: str
    query: str
    answer: str
    retrieved_memories: List[Dict[str, Any]] = Field(default_factory=list)
    strategic_plan: Dict[str, Any] = Field(default_factory=dict)
    agents: Dict[str, str] = Field(default_factory=dict)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    writeback: Optional[Dict[str, Any]] = None
    promotion_decision: Optional[Dict[str, Any]] = None
