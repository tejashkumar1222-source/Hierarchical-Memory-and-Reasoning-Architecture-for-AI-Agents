import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_api_{uuid.uuid4().hex}.sqlite')

from backend.app.main import (
    system_status,
    get_memories,
    create_memory,
    get_single_memory,
    search_memories,
    get_agents,
    list_conflicts,
    seed_demo_data,
    MemoryAddRequest
)

def test_api_system_status():
    res = system_status()
    assert 'llm' in res
    assert 'database' in res
    assert 'memory' in res
    assert 'agents' in res
    assert 'tools' in res

def test_api_memory_crud_and_search():
    # 1. Add memory
    req = MemoryAddRequest(
        content='Test direct API memory entry',
        scope='TEAM',
        owner_agent='tester',
        source='unit_test',
        confidence=0.85,
        importance=0.75
    )
    added = create_memory(req)
    assert added['id'] is not None
    assert added['content'] == 'Test direct API memory entry'

    # 2. Get single memory
    fetched = get_single_memory(added['id'])
    assert fetched['id'] == added['id']

    # 3. List memories
    listing = get_memories(scope='TEAM')
    assert listing['count'] >= 1
    assert any(m['id'] == added['id'] for m in listing['memories'])

    # 4. Search memories
    searched = search_memories(q='Test direct API')
    assert searched['count'] >= 1

def test_api_agents_and_conflicts():
    agent_res = get_agents()
    assert 'agents' in agent_res
    assert 'researcher' in agent_res['agents']
    assert 'synthesizer' in agent_res['agents']

    conflict_res = list_conflicts()
    assert 'conflicts' in conflict_res

def test_api_seed_data():
    seed_res = seed_demo_data()
    assert seed_res['ok'] is True
    assert 'seeded' in seed_res
