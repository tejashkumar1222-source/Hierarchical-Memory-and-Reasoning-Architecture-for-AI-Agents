import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_scopes_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.memory.models import MemoryScope

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_scope_creation_and_retrieval():
    mgr = MemoryManager()
    
    # 1. Global Memory
    gm = mgr.add("Global principle: Safety first", scope='GLOBAL', owner_agent='system')
    assert gm['scope'] == MemoryScope.GLOBAL.value

    # 2. Team Memory
    tm = mgr.add("Team sprint deliverable: API endpoints", scope='TEAM', owner_agent='researcher', team_id='backend')
    assert tm['scope'] == MemoryScope.TEAM.value

    # 3. Private Memory
    pm = mgr.add("Private thought: check edge cases", scope='PRIVATE', owner_agent='coder')
    assert pm['scope'] == MemoryScope.PRIVATE.value

    # Check list filtering by scope
    global_list = mgr.list(scope='GLOBAL')
    assert any(m['id'] == gm['id'] for m in global_list)
    assert not any(m['id'] == pm['id'] for m in global_list)

def test_scope_counts():
    mgr = MemoryManager()
    mgr.add("Global fact 1", scope='GLOBAL')
    mgr.add("Team fact 1", scope='TEAM')
    mgr.add("Private fact 1", scope='PRIVATE', owner_agent='agent_a')
    
    counts = mgr.count_by_scope()
    assert counts[MemoryScope.GLOBAL.value] >= 1
    assert counts[MemoryScope.TEAM.value] >= 1
    assert counts[MemoryScope.PRIVATE.value] >= 1
