"""
HMRA Modular Tool Registry

Provides a unified interface for registering, discovering, executing, and logging tools.
Logs all tool executions into tool_runs table for complete trace observability.
"""

import time
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional, List

from ..db import connect
from .calculator import safe_calculate
from .current_time import get_current_time
from .web_search import BraveSearchProvider, fetch_web_page
from .memory_tools import tool_retrieve_memory, tool_write_memory, tool_consolidate_memory

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ToolSpec:
    def __init__(self, name: str, description: str, func: Callable, schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.func = func
        self.schema = schema

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self.search_provider = BraveSearchProvider()
        self._register_default_tools()

    def register(self, name: str, description: str, func: Callable, schema: Optional[Dict[str, Any]] = None):
        self._tools[name] = ToolSpec(name, description, func, schema or {})

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {'name': spec.name, 'description': spec.description, 'schema': spec.schema}
            for spec in self._tools.values()
        ]

    def _register_default_tools(self):
        # 1. Calculator
        self.register(
            'calculator',
            'Evaluates mathematical expressions safely using Python AST.',
            lambda args: safe_calculate(args.get('expression', '')),
            {'type': 'object', 'properties': {'expression': {'type': 'string'}}, 'required': ['expression']}
        )

        # 2. Current Time
        self.register(
            'current_time',
            'Returns current UTC and local timestamps.',
            lambda args: get_current_time(),
            {'type': 'object', 'properties': {}}
        )

        # 3. Web Search
        self.register(
            'web_search',
            'Searches the live web using Brave Search API with safe parsing.',
            lambda args: self.search_provider.search(args.get('query', ''), count=args.get('count', 5)),
            {'type': 'object', 'properties': {'query': {'type': 'string'}, 'count': {'type': 'integer'}}, 'required': ['query']}
        )

        # 4. Fetch Web Page
        self.register(
            'fetch_url',
            'Safely extracts text content from a verified external URL.',
            lambda args: fetch_web_page(args.get('url', '')),
            {'type': 'object', 'properties': {'url': {'type': 'string'}}, 'required': ['url']}
        )

        # 5. Memory Retrieval
        self.register(
            'memory_retrieve',
            'Retrieves memories matching a query within requester scope.',
            lambda args: tool_retrieve_memory(args.get('query', ''), requester=args.get('requester', 'executor'), top_k=args.get('top_k', 5)),
            {'type': 'object', 'properties': {'query': {'type': 'string'}, 'top_k': {'type': 'integer'}}, 'required': ['query']}
        )

        # 6. Memory Write
        self.register(
            'memory_write',
            'Persists a validated finding into memory.',
            lambda args: tool_write_memory(
                content=args.get('content', ''),
                scope=args.get('scope', 'PRIVATE'),
                owner_agent=args.get('owner_agent', 'executor'),
                source=args.get('source', 'tool_execution'),
                confidence=args.get('confidence', 0.7),
                importance=args.get('importance', 0.5)
            ),
            {'type': 'object', 'properties': {'content': {'type': 'string'}, 'scope': {'type': 'string'}}, 'required': ['content']}
        )

        # 7. Memory Consolidate
        self.register(
            'memory_consolidate',
            'Runs deduplication and contradiction detection across memories.',
            lambda args: tool_consolidate_memory(scope=args.get('scope')),
            {'type': 'object', 'properties': {'scope': {'type': 'string'}}}
        )

    def execute(self, name: str, args: Dict[str, Any], execution_id: Optional[str] = None) -> Dict[str, Any]:
        """Executes a registered tool, tracks latency, and logs run in database."""
        spec = self.get_tool(name)
        if not spec:
            raise ValueError(f"Unknown tool: '{name}'. Available: {list(self._tools.keys())}")

        start_time = time.perf_counter()
        run_id = f"trun_{uuid.uuid4().hex[:10]}"
        t = now_iso()
        status = "SUCCESS"
        error_msg = None
        result = None

        try:
            result = spec.func(args)
        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            result = {"error": str(e)}

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Log into database if execution_id is supplied
        if execution_id:
            try:
                with connect() as c:
                    c.execute(
                        '''INSERT INTO tool_runs(id, execution_id, tool_name, input_json, output_json, status, latency_ms, created_at)
                           VALUES(?, ?, ?, ?, ?, ?, ?, ?)''',
                        (
                            run_id,
                            execution_id,
                            name,
                            json.dumps(args),
                            json.dumps(result if status == "SUCCESS" else {"error": error_msg}),
                            status,
                            latency_ms,
                            t
                        )
                    )
            except Exception:
                pass  # Non-blocking logging

        return {
            'tool': name,
            'status': status,
            'result': result,
            'latency_ms': latency_ms,
            'error': error_msg
        }

# Global registry instance
GLOBAL_TOOL_REGISTRY = ToolRegistry()

def execute(name: str, args: Dict[str, Any], execution_id: Optional[str] = None) -> Dict[str, Any]:
    """Top-level convenience execution function."""
    return GLOBAL_TOOL_REGISTRY.execute(name, args, execution_id=execution_id)
