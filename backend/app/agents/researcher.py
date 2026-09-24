"""
HMRA Agent 1: Researcher

Responsibilities:
- Retrieve and organize evidence from memory and web search
- Attach source provenance and attribution
- Store findings into PRIVATE memory
- Request promotion when findings are validated
"""

from typing import Dict, Any, List, Optional
from .base import BaseAgent, AgentMessage
from ..llm import LLMClient
from ..memory.store import MemoryManager

RESEARCHER_PROMPT = """You are the HMRA Researcher Agent.
Your core duty is to gather, verify, and organize empirical evidence from supplied memories, documents, and web findings.
Rules:
1. Ground your statements strictly in provided context and verified data.
2. State sources, citations, and provenance explicitly when available.
3. If information is uncertain or missing, declare that uncertainty honestly.
4. Do not invent sources or fabricate facts.
5. Write naturally and concisely. Use bullet points or lists only when presenting multiple distinct findings. Do not force structure onto simple answers."""

class ResearcherAgent(BaseAgent):
    def __init__(self, llm: LLMClient, memory_mgr: Optional[MemoryManager] = None):
        super().__init__('researcher', RESEARCHER_PROMPT, llm)
        self.memory_mgr = memory_mgr

    def conduct_research(
        self,
        query: str,
        context: str = "",
        search_results: Optional[List[Dict[str, Any]]] = None,
        task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> AgentMessage:
        extra_info = ""
        if search_results:
            extra_info = "WEB SEARCH FINDINGS:\n" + "\n".join(
                f"- [{r.get('source', 'Web')}] {r.get('title')}: {r.get('snippet')} ({r.get('url')})"
                for r in search_results
            )

        msg = self.execute(
            task=f"Research evidence for: {query}",
            context=context,
            extra=extra_info,
            task_id=task_id,
            execution_id=execution_id,
            trace_fn=trace_fn
        )

        # Record private observation into memory
        if self.memory_mgr and msg.content:
            try:
                mem = self.memory_mgr.add(
                    content=f"Researcher Finding: {msg.content[:400]}...",
                    scope='PRIVATE',
                    owner_agent='researcher',
                    source='researcher_analysis',
                    confidence=0.75,
                    importance=0.60,
                    metadata={'query': query, 'task_id': task_id}
                )
                msg.memory_refs.append(mem['id'])
            except Exception:
                pass

        return msg
