import os
import tempfile
import uuid

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_prom_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.memory.lifecycle import transition_status


def test_pending_memory_activates_on_approved_promotion():
    init_db()
    mgr = MemoryManager()
    mem = mgr.add('The project uses Global, Team, and Private memory scopes.', scope='PRIVATE', owner_agent='researcher')
    transition_status(mem['id'], 'PENDING_REVIEW', actor='memory_extractor', reason='Needs review')

    updated = mgr.promote(mem['id'], 'TEAM', approved_by='reviewer', reason='Reviewer approved')
    assert updated['scope'] == 'TEAM'
    assert updated['status'] == 'ACTIVE'
