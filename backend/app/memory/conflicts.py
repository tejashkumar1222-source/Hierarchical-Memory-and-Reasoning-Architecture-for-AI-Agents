"""
HMRA Conflict Management Engine

Tracks, investigates, and resolves memory contradictions.
Maintains conflict groups and provides evidence comparison without silently overwriting data.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..db import connect
from .models import MemoryStatus
from .lifecycle import log_lineage, mark_conflict

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ConflictManager:
    def create_conflict(
        self,
        memory_a_id: str,
        memory_b_id: str,
        detected_by: str = "critic",
        confidence_a: float = 0.7,
        confidence_b: float = 0.7
    ) -> str:
        """Records a conflict between two memories and marks them in the database."""
        cid = f"conf_{uuid.uuid4().hex[:10]}"
        t = now_iso()
        with connect() as c:
            c.execute(
                '''INSERT INTO conflicts(id, memory_a_id, memory_b_id, status, detected_by, confidence_a, confidence_b, created_at)
                   VALUES(?, ?, ?, 'OPEN', ?, ?, ?, ?)''',
                (cid, memory_a_id, memory_b_id, detected_by, confidence_a, confidence_b, t)
            )
        mark_conflict(memory_a_id, cid, actor=detected_by)
        mark_conflict(memory_b_id, cid, actor=detected_by)
        return cid

    def get_conflicts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves conflict records enriched with memory text and metadata."""
        query = "SELECT * FROM conflicts WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        with connect() as c:
            rows = [dict(r) for r in c.execute(query, params).fetchall()]
            for r in rows:
                mem_a = c.execute("SELECT * FROM memories WHERE id = ?", (r['memory_a_id'],)).fetchone()
                mem_b = c.execute("SELECT * FROM memories WHERE id = ?", (r['memory_b_id'],)).fetchone()
                r['memory_a'] = dict(mem_a) if mem_a else None
                r['memory_b'] = dict(mem_b) if mem_b else None
        return rows

    def get_conflict(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single conflict record with enriched memory details."""
        with connect() as c:
            row = c.execute("SELECT * FROM conflicts WHERE id = ?", (conflict_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            mem_a = c.execute("SELECT * FROM memories WHERE id = ?", (res['memory_a_id'],)).fetchone()
            mem_b = c.execute("SELECT * FROM memories WHERE id = ?", (res['memory_b_id'],)).fetchone()
            res['memory_a'] = dict(mem_a) if mem_a else None
            res['memory_b'] = dict(mem_b) if mem_b else None
            return res

    def evaluate_conflict(self, conflict_id: str) -> Dict[str, Any]:
        """
        Analyzes evidence differences between conflicting memories:
        confidence delta, source quality delta, and recency delta.
        """
        conf = self.get_conflict(conflict_id)
        if not conf or not conf.get('memory_a') or not conf.get('memory_b'):
            return {'resolvable': False, 'reason': 'Conflicting records not found'}

        ma = conf['memory_a']
        mb = conf['memory_b']

        evidence_a = ma.get('confidence', 0.5) * 0.6 + ma.get('source_quality', 0.5) * 0.4
        evidence_b = mb.get('confidence', 0.5) * 0.6 + mb.get('source_quality', 0.5) * 0.4
        delta = evidence_a - evidence_b

        recommendation = "PRESERVE_UNCERTAINTY"
        if delta >= 0.25:
            recommendation = "RESOLVE_A"
        elif delta <= -0.25:
            recommendation = "RESOLVE_B"

        return {
            'conflict_id': conflict_id,
            'evidence_score_a': round(evidence_a, 3),
            'evidence_score_b': round(evidence_b, 3),
            'delta': round(delta, 3),
            'recommendation': recommendation,
            'can_auto_resolve': recommendation != "PRESERVE_UNCERTAINTY"
        }

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        note: str = "",
        resolved_by: str = "reviewer"
    ) -> bool:
        """
        Applies resolution:
        - RESOLVE_A: Memory A kept ACTIVE; Memory B marked SUPERSEDED.
        - RESOLVE_B: Memory B kept ACTIVE; Memory A marked SUPERSEDED.
        - DISMISSED / UNRESOLVED: Preserves both memories with conflict status or reset.
        """
        conf = self.get_conflict(conflict_id)
        if not conf:
            return False

        t = now_iso()
        mem_a_id = conf['memory_a_id']
        mem_b_id = conf['memory_b_id']

        with connect() as c:
            c.execute(
                '''UPDATE conflicts
                   SET status = 'RESOLVED', resolution = ?, resolution_note = ?, resolved_by = ?, resolved_at = ?
                   WHERE id = ?''',
                (resolution, note, resolved_by, t, conflict_id)
            )

            if resolution == "RESOLVE_A":
                c.execute("UPDATE memories SET status = 'ACTIVE', updated_at = ? WHERE id = ?", (t, mem_a_id))
                c.execute("UPDATE memories SET status = 'SUPERSEDED', updated_at = ? WHERE id = ?", (t, mem_b_id))
            elif resolution == "RESOLVE_B":
                c.execute("UPDATE memories SET status = 'SUPERSEDED', updated_at = ? WHERE id = ?", (t, mem_a_id))
                c.execute("UPDATE memories SET status = 'ACTIVE', updated_at = ? WHERE id = ?", (t, mem_b_id))

        # Log lineage after the database connection block closes to prevent nested locks
        if resolution == "RESOLVE_A":
            log_lineage(mem_a_id, "CONFLICT_RESOLVED_FAVORED", resolved_by, {"conflict_id": conflict_id})
            log_lineage(mem_b_id, "CONFLICT_RESOLVED_SUPERSEDED", resolved_by, {"conflict_id": conflict_id})
        elif resolution == "RESOLVE_B":
            log_lineage(mem_b_id, "CONFLICT_RESOLVED_FAVORED", resolved_by, {"conflict_id": conflict_id})
            log_lineage(mem_a_id, "CONFLICT_RESOLVED_SUPERSEDED", resolved_by, {"conflict_id": conflict_id})
        elif resolution in ("DISMISSED", "PRESERVE_UNCERTAINTY"):
            log_lineage(mem_a_id, "CONFLICT_UNCERTAINTY_PRESERVED", resolved_by, {"conflict_id": conflict_id})
            log_lineage(mem_b_id, "CONFLICT_UNCERTAINTY_PRESERVED", resolved_by, {"conflict_id": conflict_id})

        return True
