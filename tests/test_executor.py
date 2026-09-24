import pytest
from backend.app.reasoning.executor import Executor

def test_executor_run_tool():
    executor = Executor()
    calc_out = executor.run_tool('calculator', {'expression': '15 * 6'})
    assert calc_out['status'] == 'SUCCESS'
    assert calc_out['result'] == 90.0
    assert 'latency_ms' in calc_out

    time_out = executor.run_tool('current_time', {})
    assert time_out['status'] == 'SUCCESS'
    assert 'utc_iso' in time_out['result']

def test_executor_batch_run():
    executor = Executor()
    batch = [
        {'name': 'calculator', 'args': {'expression': '25 * 4'}},
        {'name': 'current_time', 'args': {}}
    ]
    results = executor.batch_run(batch)
    assert len(results) == 2
    assert results[0]['result'] == 100.0
