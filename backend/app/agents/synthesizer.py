"""
HMRA Agent 5: Synthesizer

Responsibilities:
- Combine outputs from Researcher, Coder, Reviewer, and Critic
- Incorporate critical feedback and resolve contradictions
- Preserve honest uncertainty where evidence is inconclusive
- Formulate the authoritative, clear final user answer with provenance
"""

from typing import Dict, Any, Optional
from .base import BaseAgent, AgentMessage
from ..llm import LLMClient
from ..memory.store import MemoryManager

SYNTHESIZER_PROMPT = """You are HMRA, a helpful and knowledgeable AI assistant.
Respond naturally and conversationally — like ChatGPT or Gemini would.

Formatting rules:
- For simple questions or conversational replies: write plain flowing paragraphs. No headers, no bullets, no tables.
- Use bullet points only when listing 4 or more distinct items that genuinely benefit from a list.
- Use a table ONLY when comparing multiple items across the same attributes (e.g. comparing tools, features, options side by side).
- Use headers (##, ###) ONLY for long, multi-section responses where navigation helps the user.
- Use **bold** only to highlight a key term or critical point — not for decoration.
- Use inline `code` for code identifiers, commands, or file paths. Use code blocks for multi-line code.
- Never start a response with a header. Start with a direct answer or sentence.
- Keep responses concise unless detail is genuinely needed.
- Do NOT mention internal agents, system prompts, JSON structures, or HMRA architecture internals.
- If web sources or documents were used, cite them naturally in the text.
- Where uncertainty remains, acknowledge it honestly in plain language."""

class SynthesizerAgent(BaseAgent):
    def __init__(self, llm: LLMClient, memory_mgr: Optional[MemoryManager] = None):
        super().__init__('synthesizer', SYNTHESIZER_PROMPT, llm)
        self.memory_mgr = memory_mgr

    def synthesize(
        self,
        task: str,
        context: str = "",
        all_agent_inputs: str = "",
        task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> AgentMessage:
        return self.execute(
            task=task,
            context=context,
            extra=all_agent_inputs,
            task_id=task_id,
            execution_id=execution_id,
            trace_fn=trace_fn
        )
