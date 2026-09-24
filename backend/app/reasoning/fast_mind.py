"""
HMRA Level 2 Reasoning: Fast Mind (Tactical Reasoning Layer)

Answers: "HOW should the plan be organized and adapted?"
Responsibilities:
- Converts strategic subgoals into tactical execution steps
- Coordinates specialist agents (Researcher, Coder, Reviewer, Critic, Synthesizer)
- Evaluates tool results and performs local tactical retry on failures
- Manages agent dependencies and information hand-offs
- Adapts workflow dynamically without restarting the strategic plan
"""

import json
import re
from typing import Dict, Any, List, Optional
from .slow_mind import StrategicPlan
from .executor import Executor

class FastMind:
    def __init__(self, executor: Optional[Executor] = None):
        self.executor = executor or Executor()

    def organize_tactical_steps(self, plan: StrategicPlan) -> List[Dict[str, Any]]:
        """Decomposes the strategic plan into prioritized sequential tactical stages."""
        steps = []
        # Stage 1: Evidence & Tool Gathering
        steps.append({
            'stage': 'evidence_gathering',
            'agent': 'researcher',
            'goal': 'Gather verifiable empirical evidence and facts',
            'requires_tools': plan.required_tools
        })

        # Stage 2: Technical/Implementation (if coder is required)
        if 'coder' in plan.required_agents:
            steps.append({
                'stage': 'code_implementation',
                'agent': 'coder',
                'goal': 'Implement, analyze, or debug technical code artifacts',
                'requires_tools': []
            })

        # Stage 3: Quality Gate & Validation
        steps.append({
            'stage': 'review_validation',
            'agent': 'reviewer',
            'goal': 'Validate correctness, check requirements, and gate quality',
            'requires_tools': []
        })

        # Stage 4: Critical Stress-Testing
        steps.append({
            'stage': 'critical_challenge',
            'agent': 'critic',
            'goal': 'Challenge assumptions, detect contradictions, and identify weaknesses',
            'requires_tools': []
        })

        # Stage 5: Final Synthesis
        steps.append({
            'stage': 'synthesis',
            'agent': 'synthesizer',
            'goal': 'Resolve disagreements conservatively and produce the final integrated response',
            'requires_tools': []
        })

        return steps

    def execute_with_retry(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        max_retries: int = 1,
        execution_id: Optional[str] = None,
        trace_fn: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Executes an operational tool with local tactical retry on failure."""
        attempt = 0
        last_result = None

        while attempt <= max_retries:
            attempt += 1
            last_result = self.executor.run_tool(tool_name, arguments, execution_id=execution_id, trace_fn=trace_fn)
            if last_result.get('status') == 'SUCCESS':
                return last_result

            # Local tactical adaptation: attempt to sanitize or modify parameters
            if trace_fn:
                trace_fn('tactical_retry', 'fast_mind', {
                    'tool': tool_name,
                    'attempt': attempt,
                    'error': last_result.get('error'),
                    'action': 'Adapting tool parameters locally without restarting strategic plan'
                })

            if tool_name == 'calculator' and 'expression' in arguments:
                # Clean extra math symbols
                cleaned = re.sub(r'[^0-9+\-*/().]', '', arguments['expression'])
                arguments['expression'] = cleaned

        return last_result
