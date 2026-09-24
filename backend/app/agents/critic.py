"""
HMRA Agent 4: Critic

Responsibilities:
- Stress-test claims and conclusions
- Uncover hidden assumptions and logical fallacies
- Detect contradictions and potential hallucinations
- Flag weak evidence or over-generalizations
- Does NOT merely re-write the answer; provides rigorous critical objections
"""

from typing import Dict, Any, Optional
from .base import BaseAgent, AgentMessage
from ..llm import LLMClient
from ..memory.store import MemoryManager

CRITIC_PROMPT = """You are the HMRA Critic Agent.
Your responsibility is critical skepticism: challenging conclusions, detecting contradictions, uncovering unwarranted assumptions, and flagging potential hallucinations.
Rules:
1. Do NOT rewrite the final answer yourself.
2. Probe for weaknesses, unsupported leaps of logic, or edge cases.
3. Identify if any claim contradicts known facts in the memory context.
4. Distinguish between verified empirical facts and speculative claims.
5. Provide concise, numbered objections that the Synthesizer must resolve."""

class CriticAgent(BaseAgent):
    def __init__(self, llm: LLMClient, memory_mgr: Optional[MemoryManager] = None):
        super().__init__('critic', CRITIC_PROMPT, llm)
        self.memory_mgr = memory_mgr

    def criticize(
        self,
        task: str,
        context: str = "",
        upstream_outputs: str = "",
        task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> AgentMessage:
        return self.execute(
            task=task,
            context=context,
            extra=upstream_outputs,
            task_id=task_id,
            execution_id=execution_id,
            trace_fn=trace_fn
        )
