import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_access_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.memory.access_control import (
    can_read_memory,
    can_write_memory,
    can_promote_memory,
    can_access_scope
)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_private_memory_isolation():
    mgr = MemoryManager()
    # Researcher adds private finding
    priv_mem = mgr.add("Confidential researcher note: API key rotated", scope='PRIVATE', owner_agent='researcher')

    # Researcher CAN retrieve it
    retrieved_by_owner = mgr.retrieve("Confidential researcher note", requester='researcher')
    assert any(m['id'] == priv_mem['id'] for m in retrieved_by_owner)

    # Coder CANNOT retrieve Researcher's private memory
    retrieved_by_coder = mgr.retrieve("Confidential researcher note", requester='coder')
    assert not any(m['id'] == priv_mem['id'] for m in retrieved_by_coder)

def test_team_memory_access():
    mgr = MemoryManager()
    # Team memory for 'backend' team
    team_mem = mgr.add("Backend architectural plan", scope='TEAM', owner_agent='researcher', team_id='backend')

    # Member of backend team can read
    assert can_read_memory(team_mem, requester_agent='coder', requester_team='backend')

    # Member of foreign team cannot read
    assert not can_read_memory(team_mem, requester_agent='sales_agent', requester_team='frontend')

def test_global_memory_read_and_write_restrictions():
    # Ordinary agents can read Global
    glob_mem = {'scope': 'GLOBAL', 'owner_agent': 'system', 'team_id': 'default'}
    assert can_read_memory(glob_mem, requester_agent='coder')
    assert can_read_memory(glob_mem, requester_agent='researcher')

    # Ordinary agents cannot directly write to GLOBAL scope (must go through promotion)
    assert not can_write_memory('GLOBAL', requester_agent='coder')
    assert not can_write_memory('GLOBAL', requester_agent='researcher')

    # Orchestrator and system CAN write to GLOBAL scope
    assert can_write_memory('GLOBAL', requester_agent='orchestrator')
    assert can_write_memory('GLOBAL', requester_agent='system')
