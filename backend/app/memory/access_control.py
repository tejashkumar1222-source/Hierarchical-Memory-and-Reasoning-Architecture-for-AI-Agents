"""
HMRA Memory Access Control Engine

Implements strict scope-based authorization rules:
- PRIVATE: Strictly isolated to the owning agent. Unrelated agents cannot read or write.
- TEAM: Shared across authorized agents belonging to the specific team.
- GLOBAL: Broadly readable by all authorized agents. Direct write restricted to controlled promotion or orchestrator.
"""

from typing import Optional, Dict, Any
from .models import MemoryScope

SYSTEM_AGENTS = {'orchestrator', 'system', 'admin'}

def can_access_scope(requester_agent: str, target_scope: str, owner_agent: Optional[str] = None, team_id: str = "default", requester_team: str = "default") -> bool:
    """Checks whether requester_agent can interact with a scope."""
    scope = target_scope.upper()
    if scope == MemoryScope.GLOBAL.value:
        return True
    if scope == MemoryScope.TEAM.value:
        return requester_team == team_id or requester_agent in SYSTEM_AGENTS
    if scope == MemoryScope.PRIVATE.value:
        if requester_agent in SYSTEM_AGENTS:
            return True
        return owner_agent is not None and requester_agent == owner_agent
    return False

def can_read_memory(memory: Dict[str, Any], requester_agent: str, requester_team: str = "default") -> bool:
    """
    Evaluates whether requester_agent can read the specified memory record.
    Enforces that PRIVATE memory is strictly accessible only to its owner.
    """
    if not requester_agent:
        return False

    # Orchestrator and system audits have overarching read capability for trace/supervision
    if requester_agent in SYSTEM_AGENTS:
        return True

    scope = (memory.get('scope') or '').upper()
    owner = memory.get('owner_agent', 'system')
    team = memory.get('team_id', 'default')

    if scope == MemoryScope.GLOBAL.value:
        return True

    if scope == MemoryScope.TEAM.value:
        return team == requester_team

    if scope == MemoryScope.PRIVATE.value:
        return owner == requester_agent

    return False

def can_write_memory(scope: str, requester_agent: str, owner_agent: Optional[str] = None, team_id: str = "default", requester_team: str = "default") -> bool:
    """
    Evaluates whether requester_agent can directly write into the target scope.
    Direct GLOBAL writes are forbidden to ordinary agents (must go through promotion).
    """
    scope = scope.upper()
    if requester_agent in SYSTEM_AGENTS:
        return True

    if scope == MemoryScope.GLOBAL.value:
        # Ordinary agents cannot directly write to GLOBAL memory; must be promoted
        return False

    if scope == MemoryScope.TEAM.value:
        return requester_team == team_id

    if scope == MemoryScope.PRIVATE.value:
        # An agent can write to their own private memory
        return owner_agent is None or owner_agent == requester_agent

    return False

def can_promote_memory(memory: Dict[str, Any], target_scope: str, requester_agent: str) -> bool:
    """
    Evaluates whether a memory record can be promoted to target_scope by requester_agent.
    Reviewer agent or orchestrator can approve promotion.
    """
    target = target_scope.upper()
    current = (memory.get('scope') or '').upper()

    order = {MemoryScope.PRIVATE.value: 0, MemoryScope.TEAM.value: 1, MemoryScope.GLOBAL.value: 2}
    if target not in order or current not in order:
        return False

    if order[target] <= order[current]:
        return False  # Promotion must move upward only

    # Reviewer and orchestrator act as quality gatekeepers for promotion
    if requester_agent in {'reviewer', 'orchestrator', 'system'}:
        return True

    return False
