import pytest
from backend.app.reasoning.fast_mind import FastMind
from backend.app.reasoning.slow_mind import StrategicPlan

def test_fast_mind_tactical_step_organization():
    plan = StrategicPlan(
        objective="Design microservice",
        constraints=["Latency < 50ms"],
        complexity="MEDIUM",
        subgoals=["Research", "Code", "Review", "Criticize", "Synthesize"],
        required_agents=["researcher", "coder", "reviewer", "critic", "synthesizer"],
        required_tools=["calculator"],
        memory_requirements=[],
        success_criteria=["Complete"],
        raw_plan=""
    )
    fast = FastMind()
    steps = fast.organize_tactical_steps(plan)

    assert len(steps) >= 4
    agents_in_order = [s['agent'] for s in steps]
    assert 'researcher' in agents_in_order
    assert 'coder' in agents_in_order
    assert 'reviewer' in agents_in_order
    assert 'critic' in agents_in_order
    assert 'synthesizer' in agents_in_order

def test_fast_mind_local_retry_recovery():
    fast = FastMind()
    # Calculator with dirty input that fast_mind sanitizes on retry
    res = fast.execute_with_retry('calculator', {'expression': '$$ 100 + 50 $$'}, max_retries=1)
    assert res['status'] == 'SUCCESS'
    assert res['result'] == 150.0
