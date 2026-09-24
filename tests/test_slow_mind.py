import pytest
from unittest.mock import MagicMock
from backend.app.reasoning.slow_mind import SlowMind

def test_slow_mind_strategic_planning():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = '''```json
    {
      "objective": "Build a secure REST API in Python",
      "constraints": ["Zero trust", "Rate limiting required"],
      "complexity": "HIGH",
      "subgoals": ["Draft architecture", "Implement endpoints", "Review security", "Critic stress-test"],
      "required_agents": ["researcher", "coder", "reviewer", "critic", "synthesizer"],
      "required_tools": ["calculator", "memory_retrieve"],
      "memory_requirements": ["Security policies"],
      "success_criteria": ["All tests pass"]
    }
    ```'''

    slow = SlowMind(mock_llm)
    plan = slow.plan("Build a secure REST API in Python")

    assert plan.objective == "Build a secure REST API in Python"
    assert "Zero trust" in plan.constraints
    assert plan.complexity == "HIGH"
    assert "coder" in plan.required_agents
    assert "calculator" in plan.required_tools
