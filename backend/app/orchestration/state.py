"""
HMRA Agent and System Runtime State Tracker

Maintains live runtime status for:
- Orchestrator
- Slow Mind
- Fast Mind
- Executor
- Researcher
- Coder
- Reviewer
- Critic
- Synthesizer

Statuses: IDLE, RUNNING, WAITING, SUCCESS, FAILED, REVIEW, CONFLICT
"""

import time
from typing import Dict, Any, Optional

AGENT_NAMES = [
    'orchestrator',
    'slow_mind',
    'fast_mind',
    'executor',
    'researcher',
    'coder',
    'reviewer',
    'critic',
    'synthesizer'
]

class AgentStateManager:
    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {
            name: {
                'name': name,
                'status': 'IDLE',
                'current_task': '',
                'last_active': time.time(),
                'run_count': 0
            }
            for name in AGENT_NAMES
        }

    def set_status(self, name: str, status: str, task: str = ""):
        if name in self._states:
            self._states[name]['status'] = status
            if task:
                self._states[name]['current_task'] = task
            self._states[name]['last_active'] = time.time()
            if status == 'RUNNING':
                self._states[name]['run_count'] += 1

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._states)

    def reset_all_to_idle(self):
        for name in self._states:
            self._states[name]['status'] = 'IDLE'
            self._states[name]['current_task'] = ''

GLOBAL_STATE_TRACKER = AgentStateManager()
