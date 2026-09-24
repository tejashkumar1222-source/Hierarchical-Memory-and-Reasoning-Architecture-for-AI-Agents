"""
HMRA Level 1 Reasoning: Slow Mind (Strategic Planner)

Answers: "WHAT should be done?"
Responsibilities:
- Objective formulation
- Constraint identification
- Task complexity estimation
- Strategic plan decomposition
- Identification of required specialist agents and tools
- Memory requirement mapping
- Success criteria definition

Does NOT execute low-level actions.
"""

import json
import re
from typing import Dict, Any, List, Optional
from ..llm import LLMClient

class StrategicPlan:
    def __init__(
        self,
        objective: str,
        constraints: List[str],
        complexity: str,
        subgoals: List[str],
        required_agents: List[str],
        required_tools: List[str],
        memory_requirements: List[str],
        success_criteria: List[str],
        raw_plan: str
    ):
        self.objective = objective
        self.constraints = constraints
        self.complexity = complexity
        self.subgoals = subgoals
        self.required_agents = required_agents
        self.required_tools = required_tools
        self.memory_requirements = memory_requirements
        self.success_criteria = success_criteria
        self.raw_plan = raw_plan

    def to_dict(self) -> Dict[str, Any]:
        return {
            'objective': self.objective,
            'constraints': self.constraints,
            'complexity': self.complexity,
            'subgoals': self.subgoals,
            'required_agents': self.required_agents,
            'required_tools': self.required_tools,
            'memory_requirements': self.memory_requirements,
            'success_criteria': self.success_criteria,
            'raw_plan': self.raw_plan
        }

SLOW_MIND_SYSTEM_PROMPT = """You are HMRA Slow Mind (Strategic Reasoning Layer).
Your job is high-level strategic reasoning: "WHAT should be done?"
You analyze objectives, constraints, complexity, subgoals, agent requirements, and tools.
You do NOT execute low-level operations or generate final code/tools output.

Respond in valid JSON format with the following keys:
{
  "objective": "Clear statement of what needs to be achieved",
  "constraints": ["constraint 1", "constraint 2"],
  "complexity": "LOW" | "MEDIUM" | "HIGH",
  "subgoals": ["step 1", "step 2", "step 3"],
  "required_agents": ["researcher", "coder", "reviewer", "critic", "synthesizer"],
  "required_tools": ["calculator" | "web_search" | "current_time" | "memory_retrieve"],
  "memory_requirements": ["key facts or document context needed"],
  "success_criteria": ["criteria 1", "criteria 2"]
}"""

class SlowMind:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(
        self,
        query: str,
        retrieved_memory_context: str = "",
        web_search_enabled: bool = False,
        trace_fn: Optional[Any] = None
    ) -> StrategicPlan:
        """Generates the strategic plan for the incoming query."""
        if trace_fn:
            trace_fn('slow_mind_start', 'slow_mind', {'query': query, 'web_search_enabled': web_search_enabled})

        user_content = f"USER QUERY:\n{query}\n\nRELEVANT MEMORY CONTEXT:\n{retrieved_memory_context}\n\nWEB SEARCH ENABLED: {web_search_enabled}"

        raw_response = ""
        try:
            raw_response = self.llm.chat([
                {'role': 'system', 'content': SLOW_MIND_SYSTEM_PROMPT},
                {'role': 'user', 'content': user_content}
            ], temperature=0.1)
        except Exception as e:
            raw_response = f"Strategic reasoning fallback. Query: {query}. Error: {e}"

        parsed = self._parse_json(raw_response, query, web_search_enabled)

        plan = StrategicPlan(
            objective=parsed.get('objective', query),
            constraints=parsed.get('constraints', ['Maintain accuracy', 'Respect scope boundaries']),
            complexity=parsed.get('complexity', 'MEDIUM'),
            subgoals=parsed.get('subgoals', ['Retrieve context', 'Analyze evidence', 'Synthesize response']),
            required_agents=parsed.get('required_agents', ['researcher', 'reviewer', 'critic', 'synthesizer']),
            required_tools=parsed.get('required_tools', []),
            memory_requirements=parsed.get('memory_requirements', []),
            success_criteria=parsed.get('success_criteria', ['Comprehensive and verified answer']),
            raw_plan=raw_response
        )

        if trace_fn:
            trace_fn('slow_mind_end', 'slow_mind', plan.to_dict())

        return plan

    def _parse_json(self, text: str, query: str, web_search_enabled: bool) -> Dict[str, Any]:
        """Safely parses JSON block from model response with intelligent defaults."""
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        candidate = match.group(1) if match else text

        try:
            # First try direct JSON parsing
            return json.loads(candidate.strip())
        except Exception:
            pass

        # Try finding the outermost JSON object braces
        start = candidate.find('{')
        end = candidate.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start:end+1])
            except Exception:
                pass

        # Heuristic fallback if LLM returned non-JSON text
        agents = ['researcher', 'reviewer', 'critic', 'synthesizer']
        tools = []
        lower_q = query.lower()
        if any(k in lower_q for k in ('code', 'python', 'java', 'sql', 'debug', 'script', 'function', 'class', 'bug')):
            agents.append('coder')
        if any(k in lower_q for k in ('calculate', 'math', '+', '*', '/', '^', '%', 'sum', 'solve')):
            tools.append('calculator')
        if any(k in lower_q for k in ('time', 'date', 'today', 'hour')):
            tools.append('current_time')
        if web_search_enabled or any(k in lower_q for k in ('search', 'latest', 'news', 'recent', 'who is', 'current')):
            tools.append('web_search')

        return {
            'objective': query,
            'constraints': ['Ensure empirical verification', 'Strict memory scoping'],
            'complexity': 'MEDIUM',
            'subgoals': ['Analyze query', 'Gather evidence', 'Critically validate', 'Synthesize solution'],
            'required_agents': list(set(agents)),
            'required_tools': tools,
            'memory_requirements': ['Hierarchical knowledge context'],
            'success_criteria': ['Accurate and fact-checked response']
        }
