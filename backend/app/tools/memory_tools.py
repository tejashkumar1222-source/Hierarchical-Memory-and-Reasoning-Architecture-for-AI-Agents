"""
HMRA Memory Tools Module

Wraps memory retrieval, addition, consolidation, and promotion
as formal tools executable by the Executor level.
"""

from typing import Dict, Any, Optional
from ..memory.store import MemoryManager

_MEM_MGR = MemoryManager()

def tool_retrieve_memory(query: str, requester: str = "executor", top_k: int = 5) -> Dict[str, Any]:
    """Retrieves memories relevant to the query respecting requester scope authorization."""
    results = _MEM_MGR.retrieve(query=query, requester=requester, top_k=top_k)
    return {
        "count": len(results),
        "results": results
    }

def tool_write_memory(
    content: str,
    scope: str = "PRIVATE",
    owner_agent: str = "executor",
    source: str = "tool_execution",
    confidence: float = 0.7,
    importance: float = 0.5
) -> Dict[str, Any]:
    """Writes a new fact into memory."""
    mem = _MEM_MGR.add(
        content=content,
        scope=scope,
        owner_agent=owner_agent,
        source=source,
        confidence=confidence,
        importance=importance
    )
    return {"created": True, "memory": mem}

def tool_consolidate_memory(scope: Optional[str] = None) -> Dict[str, Any]:
    """Runs memory consolidation to deduplicate and resolve conflicts."""
    report = _MEM_MGR.consolidate(scope=scope)
    return report.model_dump()
