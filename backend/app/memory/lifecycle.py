"""
HMRA Memory Lifecycle Engine

Handles lifecycle states and transitions:
ACTIVE -> SUPERSEDED / MERGED / CONFLICT / DEPRECATED / EXPIRED / PENDING_REVIEW
Logs all transitions in memory_lineage for verifiable lineage tracking.
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from ..db import connect
from .models import MemoryStatus

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def log_lineage(memory_id: str, action: str, actor: str, details: Optional[Dict[str, Any]] = None) -> str:
    """Records an immutable lineage event in the memory_lineage table."""
    lineage_id = f"lin_{uuid.uuid4().hex[:12]}"
    created_at = now_iso()
    with connect() as c:
        c.execute(
            '''INSERT INTO memory_lineage(id, memory_id, action, actor, details_json, created_at)
               VALUES(?, ?, ?, ?, ?, ?)''',
            (lineage_id, memory_id, action, actor, json.dumps(details or {}), created_at)
        )
    return lineage_id

def transition_status(memory_id: str, new_status: str, actor: str = "lifecycle_engine", reason: str = "") -> bool:
    """Transitions a memory record to a new status with an audit trail."""
    valid_statuses = {s.value for s in MemoryStatus}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid memory status: {new_status}")

    t = now_iso()
    with connect() as c:
        c.execute(
            '''UPDATE memories SET status = ?, updated_at = ? WHERE id = ?''',
            (new_status, t, memory_id)
        )
    log_lineage(memory_id, f"TRANSITION_TO_{new_status}", actor, {"reason": reason, "timestamp": t})
    return True

def mark_superseded(old_memory_id: str, new_memory_id: str, actor: str = "system", reason: str = ""):
    """Marks an older memory as superseded by a newer version while preserving history."""
    t = now_iso()
    with connect() as c:
        c.execute(
            '''UPDATE memories SET status = ?, updated_at = ? WHERE id = ?''',
            (MemoryStatus.SUPERSEDED.value, t, old_memory_id)
        )
    log_lineage(old_memory_id, "SUPERSEDED", actor, {"superseded_by": new_memory_id, "reason": reason})
    log_lineage(new_memory_id, "SUPERSEDES", actor, {"superseded_memory_id": old_memory_id, "reason": reason})

def mark_conflict(memory_id: str, conflict_group_id: str, actor: str = "critic"):
    """Marks memory status as CONFLICT and records conflict group."""
    t = now_iso()
    with connect() as c:
        c.execute(
            '''UPDATE memories SET status = ?, contradiction_group_id = ?, updated_at = ? WHERE id = ?''',
            (MemoryStatus.CONFLICT.value, conflict_group_id, t, memory_id)
        )
    log_lineage(memory_id, "FLAG_CONFLICT", actor, {"conflict_group_id": conflict_group_id})

def check_expiration(expiration_days: float = 90.0) -> int:
    """Finds old low-confidence or temporary memories and transitions them to EXPIRED."""
    t = now_iso()
    expired_count = 0
    with connect() as c:
        rows = c.execute(
            '''SELECT id, created_at, confidence, importance, scope, status
               FROM memories
               WHERE status = 'ACTIVE' AND scope = 'PRIVATE' '''
        ).fetchall()
        for r in rows:
            try:
                created = datetime.fromisoformat(r['created_at'].replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created).total_seconds() / 86400.0
                # Expire old private memories with low confidence and importance
                if age_days > expiration_days and r['confidence'] < 0.4 and r['importance'] < 0.4:
                    c.execute(
                        '''UPDATE memories SET status = ?, updated_at = ? WHERE id = ?''',
                        (MemoryStatus.EXPIRED.value, t, r['id'])
                    )
                    log_lineage(r['id'], "EXPIRED", "lifecycle_engine", {"age_days": age_days})
                    expired_count += 1
            except Exception:
                continue
    return expired_count
