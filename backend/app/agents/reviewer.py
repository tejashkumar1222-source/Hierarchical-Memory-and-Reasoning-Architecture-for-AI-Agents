"""
HMRA Agent 3: Reviewer

Responsibilities:
- Validate outputs against task requirements and constraints
- Quality gatekeeper: identify gaps, missing requirements, and inconsistencies
- Gate memory promotions (approve or reject graduation across scopes)
"""

from typing import Dict, Any, Optional
from .base import BaseAgent, AgentMessage
from ..llm import LLMClient
from ..memory.store import MemoryManager

REVIEWER_PROMPT = """You are the HMRA Reviewer Agent (Quality Gate).
Your job is to validate upstream agent outputs against task requirements, constraints, and factual consistency.
Rules:
1. Objectively evaluate whether all requirements are satisfied.
2. Flag missing components, unaddressed edge cases, or gaps in explanation.
3. Assess factual fidelity to the retrieved memory and verified evidence.
4. Output a clear verdict: APPROVED or REVISE, accompanied by specific constructive notes."""

class ReviewerAgent(BaseAgent):
    def __init__(self, llm: LLMClient, memory_mgr: Optional[MemoryManager] = None):
        super().__init__('reviewer', REVIEWER_PROMPT, llm)
        self.memory_mgr = memory_mgr

    def review(
        self,
        task: str,
        context: str = "",
        candidate_outputs: str = "",
        task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> AgentMessage:
        return self.execute(
            task=task,
            context=context,
            extra=candidate_outputs,
            task_id=task_id,
            execution_id=execution_id,
            trace_fn=trace_fn
        )
