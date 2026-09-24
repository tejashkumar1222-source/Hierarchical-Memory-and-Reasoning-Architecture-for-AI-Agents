"""
HMRA Agent 2: Coder

Responsibilities:
- Generate clean, modular, and testable code
- Analyze, explain, and debug software logic
- Store reusable technical knowledge in PRIVATE memory
"""

from typing import Dict, Any, Optional
from .base import BaseAgent, AgentMessage
from ..llm import LLMClient
from ..memory.store import MemoryManager

CODER_PROMPT = """You are the HMRA Coder Agent.
Your duty is technical problem solving, software architecture, code generation, and debugging.
Rules:
1. Provide precise, idiomatic, robust, and commented code implementations.
2. Clearly explain algorithmic decisions and complexity.
3. Validate edge cases and potential runtime errors.
4. Do not pretend to execute code that was not verified."""

class CoderAgent(BaseAgent):
    def __init__(self, llm: LLMClient, memory_mgr: Optional[MemoryManager] = None):
        super().__init__('coder', CODER_PROMPT, llm)
        self.memory_mgr = memory_mgr

    def implement_code(
        self,
        task: str,
        context: str = "",
        extra: str = "",
        task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> AgentMessage:
        msg = self.execute(
            task=task,
            context=context,
            extra=extra,
            task_id=task_id,
            execution_id=execution_id,
            trace_fn=trace_fn
        )
        return msg
