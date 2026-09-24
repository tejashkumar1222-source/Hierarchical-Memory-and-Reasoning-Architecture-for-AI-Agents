"""
HMRA Base Agent & Structured Message Passing Protocol
"""

import time
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..llm import LLMClient
from ..db import connect

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class AgentMessage(BaseModel):
    task_id: str
    from_agent: str
    to_agent: str
    message_type: str = "agent_output"
    content: str
    memory_refs: List[str] = Field(default_factory=list)
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.75
    requires_review: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseAgent:
    def __init__(self, name: str, role_prompt: str, llm: LLMClient):
        self.name = name
        self.role_prompt = role_prompt
        self.llm = llm

    def execute(
        self,
        task: str,
        context: str = "",
        extra: str = "",
        task_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> AgentMessage:
        """Executes the agent role, measuring latency and capturing telemetry."""
        tid = task_id or f"task_{uuid.uuid4().hex[:10]}"
        start_time = time.perf_counter()

        if trace_fn:
            trace_fn('agent_start', self.name, {'task': task, 'task_id': tid})

        messages = [
            {'role': 'system', 'content': self.role_prompt},
            {'role': 'user', 'content': f"TASK:\n{task}\n\nRETRIEVED MEMORY CONTEXT:\n{context}\n\nUPSTREAM AGENT INPUTS:\n{extra}"}
        ]

        try:
            output_text = self.llm.chat(messages)
        except Exception as e:
            output_text = f"[{self.name}] Error during execution: {e}"

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Log into agent_runs
        if execution_id:
            try:
                with connect() as c:
                    run_id = f"arun_{uuid.uuid4().hex[:10]}"
                    c.execute(
                        '''INSERT INTO agent_runs(id, execution_id, agent_name, status, input_summary, output_summary, latency_ms, created_at)
                           VALUES(?, ?, ?, 'SUCCESS', ?, ?, ?, ?)''',
                        (run_id, execution_id, self.name, task[:300], output_text[:500], latency_ms, now_iso())
                    )
            except Exception:
                pass

        msg = AgentMessage(
            task_id=tid,
            from_agent=self.name,
            to_agent="orchestrator",
            message_type=f"{self.name}_output",
            content=output_text,
            confidence=0.80,
            requires_review=self.name not in ('synthesizer',),
            metadata={'latency_ms': latency_ms}
        )

        if trace_fn:
            trace_fn('agent_end', self.name, {'chars': len(output_text), 'latency_ms': latency_ms})

        return msg
