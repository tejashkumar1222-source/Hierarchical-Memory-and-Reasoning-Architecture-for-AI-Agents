import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_life_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db, connect
from backend.app.memory.store import MemoryManager
from backend.app.memory.lifecycle import transition_status, mark_superseded, check_expiration
from backend.app.memory.models import MemoryStatus

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_lifecycle_transition_and_lineage():
    mgr = MemoryManager()
    mem = mgr.add("Temporary hypothesis for sprint", scope='PRIVATE', owner_agent='researcher')
    assert mem['status'] == MemoryStatus.ACTIVE.value

    # Transition to PENDING_REVIEW
    transition_status(mem['id'], MemoryStatus.PENDING_REVIEW.value, actor='researcher', reason='Ready for review')
    updated = mgr.get(mem['id'])
    assert updated['status'] == MemoryStatus.PENDING_REVIEW.value

    # Verify audit lineage
    with connect() as c:
        rows = c.execute("SELECT * FROM memory_lineage WHERE memory_id = ?", (mem['id'],)).fetchall()
        assert len(rows) >= 2  # CREATED + TRANSITION

def test_mark_superseded():
    mgr = MemoryManager()
    old_mem = mgr.add("Python target version is 3.10", scope='TEAM')
    new_mem = mgr.add("Python target version is 3.11", scope='TEAM')

    mgr.mark_superseded(old_mem['id'], new_mem['id'], actor='reviewer', reason='Upgraded runtime')

    assert mgr.get(old_mem['id'])['status'] == MemoryStatus.SUPERSEDED.value
    assert mgr.get(new_mem['id'])['status'] == MemoryStatus.ACTIVE.value
