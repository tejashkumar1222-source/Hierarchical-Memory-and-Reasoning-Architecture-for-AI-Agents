"""
HMRA Level 3 Reasoning: Executor (Operational Execution Layer)

Answers: "DO it."
Responsibilities:
- Operational tool execution
- Structured execution returns
- Latency and telemetry recording
- Execution error logging
- Interaction with ToolRegistry
"""

from typing import Dict, Any, List, Optional
from ..tools.registry import GLOBAL_TOOL_REGISTRY

class Executor:
    def __init__(self, registry=None):
        self.registry = registry or GLOBAL_TOOL_REGISTRY

    def run_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Executes a tool operation and logs the event."""
        if trace_fn:
            trace_fn('executor_tool_start', 'executor', {'tool': tool_name, 'args': arguments})

        result = self.registry.execute(tool_name, arguments, execution_id=execution_id)

        if trace_fn:
            trace_fn('executor_tool_end', 'executor', result)

        return result

    def batch_run(
        self,
        tool_calls: List[Dict[str, Any]],
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Executes multiple tool calls sequentially, recording outputs."""
        outputs = []
        for call in tool_calls:
            name = call.get('name') or call.get('tool')
            args = call.get('arguments') or call.get('args') or {}
            out = self.run_tool(name, args, execution_id=execution_id, trace_fn=trace_fn)
            outputs.append(out)
        return outputs
