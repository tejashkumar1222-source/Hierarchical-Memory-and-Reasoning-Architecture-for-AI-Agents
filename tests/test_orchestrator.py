import os
import tempfile
import uuid
import pytest
from unittest.mock import MagicMock

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_orch_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.orchestration.orchestrator import Orchestrator

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_orchestrator_end_to_end_flow():
    mock_llm = MagicMock()
    # Mock chat responses for Slow mind, Researcher, Reviewer, Critic, Synthesizer
    mock_llm.chat.side_effect = [
        # Slow mind plan
        '{"objective": "Test task", "constraints": [], "complexity": "LOW", "subgoals": ["step1"], "required_agents": ["researcher", "reviewer", "critic", "synthesizer"], "required_tools": [], "memory_requirements": [], "success_criteria": []}',
        # Researcher
        'Researcher findings on the topic',
        # Reviewer
        'Reviewer approval: looks solid',
        # Critic
        'Critic objections: consider corner cases',
        # Synthesizer
        'Synthesizer final response: Complete synthesized analysis of the problem.'
    ]

    mem_mgr = MemoryManager()
    trace_events = []
    def trace(stage, actor, data):
        trace_events.append((stage, actor))

    orch = Orchestrator(mock_llm, mem_mgr, trace_fn=trace)
    result = orch.run("Explain how hierarchical memory works in AI agents", requester='orchestrator')

    assert result['execution_id'] is not None
    assert "Synthesizer" in result['answer']
    assert 'researcher' in result['agents']
    assert 'reviewer' in result['agents']
    assert 'critic' in result['agents']
    assert 'synthesizer' in result['agents']
    assert len(trace_events) >= 5
