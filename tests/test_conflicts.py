import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_conf_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.memory.models import MemoryStatus

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_contradiction_detection_and_resolution():
    mgr = MemoryManager()
    
    # Opposing memories with clear confidence difference
    m1 = mgr.add("Python release version target is 3.11", scope='GLOBAL', confidence=0.90, source_quality=0.95)
    m2 = mgr.add("Python release version target is 3.12", scope='GLOBAL', confidence=0.40, source_quality=0.40)

    # Trigger consolidation to detect contradiction
    report = mgr.consolidate()
    assert report.conflicts_found >= 1

    conflicts = mgr.conflict_mgr.get_conflicts()
    assert len(conflicts) >= 1
    conf = conflicts[0]
    assert conf['status'] in ('OPEN', 'RESOLVED')

    # Test manual resolution if open
    if conf['status'] == 'OPEN':
        success = mgr.conflict_mgr.resolve_conflict(
            conf['id'],
            resolution='RESOLVE_A',
            note='Decisive confidence in 3.11',
            resolved_by='reviewer'
        )
        assert success
        resolved_conf = mgr.conflict_mgr.get_conflict(conf['id'])
        assert resolved_conf['status'] == 'RESOLVED'
        assert mgr.get(m1['id'])['status'] == MemoryStatus.ACTIVE.value
        assert mgr.get(m2['id'])['status'] == MemoryStatus.SUPERSEDED.value
