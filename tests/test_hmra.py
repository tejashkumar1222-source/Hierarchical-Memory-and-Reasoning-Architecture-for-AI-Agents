import os
import tempfile
import uuid
import pytest
from backend.app.db import init_db
from backend.app.memory import MemoryManager

@pytest.fixture(autouse=True)
def setup_test_db():
    os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_hmra_{uuid.uuid4().hex}.sqlite')
    init_db()

def test_scope_and_promotion():
    m = MemoryManager()
    x = m.add('private research fact about HMRA', scope='PRIVATE', owner_agent='researcher')
    # Private memory must NOT be retrievable by coder
    assert not any(item['id'] == x['id'] for item in m.retrieve('private research fact', requester='coder'))
    # Private memory MUST be retrievable by owning researcher
    assert any(item['id'] == x['id'] for item in m.retrieve('private research fact', requester='researcher'))
    
    # After promotion to TEAM, coder CAN retrieve it
    y = m.promote(x['id'], 'TEAM', 'reviewer')
    assert y['scope'] == 'TEAM'
    assert any(item['id'] == x['id'] for item in m.retrieve('private research fact', requester='coder'))

def test_persistent_memory():
    m = MemoryManager()
    x = m.add('persistent database fact', scope='GLOBAL')
    assert m.get(x['id'])['content'] == 'persistent database fact'
