import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_prom_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_controlled_promotion_pipeline():
    mgr = MemoryManager()
    
    # 1. Start with PRIVATE memory
    mem = mgr.add(
        "Validated research: agent communication must be structured",
        scope='PRIVATE',
        owner_agent='researcher',
        confidence=0.85,
        importance=0.80,
        source_quality=0.90
    )
    assert mem['scope'] == 'PRIVATE'

    # 2. Promote PRIVATE -> TEAM
    team_mem = mgr.promote(mem['id'], target_scope='TEAM', approved_by='reviewer', reason='Reviewed by QA')
    assert team_mem['scope'] == 'TEAM'
    assert team_mem['promoted_from'] == 'PRIVATE'

    # 3. Promote TEAM -> GLOBAL
    global_mem = mgr.promote(mem['id'], target_scope='GLOBAL', approved_by='reviewer', reason='Approved for organization-wide use')
    assert global_mem['scope'] == 'GLOBAL'
    assert global_mem['promoted_from'] == 'TEAM'

def test_invalid_demotion_rejected():
    mgr = MemoryManager()
    mem = mgr.add("Global principle", scope='GLOBAL')
    
    with pytest.raises(ValueError, match="Invalid scope transition"):
        mgr.promote(mem['id'], target_scope='PRIVATE')
