import pytest
from unittest.mock import MagicMock
from backend.app.agents import (
    ResearcherAgent,
    CoderAgent,
    ReviewerAgent,
    CriticAgent,
    SynthesizerAgent,
    AgentSystem
)

def test_five_specialized_agents_structured_messaging():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "Specialist Agent Output"

    # Researcher
    researcher = ResearcherAgent(mock_llm)
    r_msg = researcher.conduct_research("Research topic")
    assert r_msg.from_agent == 'researcher'
    assert r_msg.content == "Specialist Agent Output"

    # Coder
    coder = CoderAgent(mock_llm)
    c_msg = coder.implement_code("Implement function")
    assert c_msg.from_agent == 'coder'

    # Reviewer
    reviewer = ReviewerAgent(mock_llm)
    rev_msg = reviewer.review("Task", candidate_outputs="Code draft")
    assert rev_msg.from_agent == 'reviewer'

    # Critic
    critic = CriticAgent(mock_llm)
    cr_msg = critic.criticize("Task", upstream_outputs="Draft with potential flaw")
    assert cr_msg.from_agent == 'critic'

    # Synthesizer
    synth = SynthesizerAgent(mock_llm)
    s_msg = synth.synthesize("Task", all_agent_inputs="Combined inputs")
    assert s_msg.from_agent == 'synthesizer'

def test_agent_system_container():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "Container response"
    system = AgentSystem(mock_llm)

    res = system.call('researcher', 'Analyze dataset')
    assert res == "Container response"

    with pytest.raises(ValueError, match="Unknown agent role"):
        system.call('marketing_guru', 'Sell product')
