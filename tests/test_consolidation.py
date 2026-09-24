import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_cons_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.memory.models import MemoryStatus

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_duplicate_detection_and_merging():
    mgr = MemoryManager()
    
    # Add two nearly identical memories
    m1 = mgr.add("The HMRA database engine is SQLite with WAL mode enabled", scope='GLOBAL', confidence=0.8, importance=0.7)
    m2 = mgr.add("The HMRA database engine is SQLite with WAL mode enabled", scope='GLOBAL', confidence=0.9, importance=0.8)

    report = mgr.consolidate()
    assert report.duplicates_found >= 1
    assert report.merged >= 1

    # Check that one is ACTIVE and one is MERGED
    rec1 = mgr.get(m1['id'])
    rec2 = mgr.get(m2['id'])
    statuses = {rec1['status'], rec2['status']}
    assert MemoryStatus.MERGED.value in statuses
    assert MemoryStatus.ACTIVE.value in statuses
