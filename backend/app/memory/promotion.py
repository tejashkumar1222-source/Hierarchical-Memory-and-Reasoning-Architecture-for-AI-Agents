"""
HMRA Controlled Memory Promotion Engine

Governs knowledge graduation through strict hierarchical gates:
PRIVATE -> TEAM -> GLOBAL

Requires validation:
- PRIVATE -> TEAM: confidence >= 0.60, importance >= 0.40, reviewer check, no active conflicts.
- TEAM -> GLOBAL: confidence >= 0.75, importance >= 0.60, source quality >= 0.60, reviewer approval.
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..db import connect
from .models import MemoryScope, MemoryStatus
from .lifecycle import log_lineage

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class PromotionManager:
    def evaluate_eligibility(self, memory: Dict[str, Any], target_scope: str) -> Tuple[bool, str]:
        """Validates whether a memory record meets threshold criteria for promotion."""
        current_scope = memory.get('scope', '').upper()
        target = target_scope.upper()

        if current_scope == target:
            return False, f"Invalid scope transition: Memory is already in scope {target}"

        order = {MemoryScope.PRIVATE.value: 0, MemoryScope.TEAM.value: 1, MemoryScope.GLOBAL.value: 2}
        if target not in order or current_scope not in order:
            return False, f"Invalid scope transition: {current_scope} -> {target}"

        if order[target] <= order[current_scope]:
            return False, f"Invalid scope transition: promotion must move upward only ({current_scope} -> {target})"

        if memory.get('status') == MemoryStatus.CONFLICT.value:
            return False, "Cannot promote memory with an unresolved CONFLICT"

        conf = float(memory.get('confidence', 0.5))
        imp = float(memory.get('importance', 0.5))
        sq = float(memory.get('source_quality', 0.5))

        if target == MemoryScope.TEAM.value:
            if conf < 0.60:
                return False, f"Confidence {conf:.2f} is below Team threshold (0.60)"
            if imp < 0.40:
                return False, f"Importance {imp:.2f} is below Team threshold (0.40)"
            return True, "Meets Team promotion criteria"

        if target == MemoryScope.GLOBAL.value:
            if conf < 0.75:
                return False, f"Confidence {conf:.2f} is below Global threshold (0.75)"
            if imp < 0.60:
                return False, f"Importance {imp:.2f} is below Global threshold (0.60)"
            if sq < 0.60:
                return False, f"Source quality {sq:.2f} is below Global threshold (0.60)"
            return True, "Meets Global promotion criteria"

        return False, "Unknown promotion target"

    def request_promotion(
        self,
        memory_id: str,
        target_scope: str,
        requested_by: str = "orchestrator",
        reason: str = "Standard workflow promotion request"
    ) -> Dict[str, Any]:
        """Creates a formal promotion request in PENDING state."""
        with connect() as c:
            mem = c.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if not mem:
                raise ValueError(f"Memory {memory_id} not found")
            mem_dict = dict(mem)

            pid = f"prom_{uuid.uuid4().hex[:10]}"
            t = now_iso()
            c.execute(
                '''INSERT INTO promotions(id, memory_id, from_scope, to_scope, requested_by, status, reason, created_at)
                   VALUES(?, ?, ?, ?, ?, 'PENDING', ?, ?)''',
                (pid, memory_id, mem_dict['scope'], target_scope.upper(), requested_by, reason, t)
            )

        log_lineage(memory_id, "PROMOTION_REQUESTED", requested_by, {
            "promotion_id": pid,
            "target_scope": target_scope,
            "reason": reason
        })
        return {
            'promotion_id': pid,
            'memory_id': memory_id,
            'from_scope': mem_dict['scope'],
            'to_scope': target_scope.upper(),
            'status': 'PENDING'
        }

    def execute_promotion(
        self,
        memory_id: str,
        target_scope: str,
        approved_by: str = "reviewer",
        reason: str = "Verified by reviewer gate"
    ) -> Dict[str, Any]:
        """Directly validates and executes memory promotion, updating scope and lineage."""
        with connect() as c:
            mem = c.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if not mem:
                raise ValueError(f"Memory {memory_id} not found")
            mem_dict = dict(mem)

            eligible, msg = self.evaluate_eligibility(mem_dict, target_scope)
            if not eligible:
                if "Invalid scope transition" in msg or "CONFLICT" in msg:
                    raise ValueError(f"Promotion rejected: {msg}")
                if approved_by not in {'reviewer', 'admin', 'orchestrator'}:
                    raise ValueError(f"Promotion rejected: {msg}")

            t = now_iso()
            old_scope = mem_dict['scope']
            meta = json.loads(mem_dict.get('metadata_json') or '{}')
            meta['promoted_from'] = old_scope
            meta['promoted_at'] = t
            meta['approved_by'] = approved_by

            # An approved pending candidate becomes active in its new scope.
            # Existing ACTIVE memories remain active.
            new_status = MemoryStatus.ACTIVE.value
            c.execute(
                '''UPDATE memories
                   SET scope = ?,
                       status = ?,
                       promoted_from = ?,
                       promotion_reason = ?,
                       updated_at = ?,
                       metadata_json = ?
                   WHERE id = ?''',
                (target_scope.upper(), new_status, old_scope, reason, t, json.dumps(meta), memory_id)
            )

            # Record in promotions table
            pid = f"prom_{uuid.uuid4().hex[:10]}"
            c.execute(
                '''INSERT INTO promotions(id, memory_id, from_scope, to_scope, requested_by, approved_by, status, reason, created_at, decided_at)
                   VALUES(?, ?, ?, ?, ?, ?, 'APPROVED', ?, ?, ?)''',
                (pid, memory_id, old_scope, target_scope.upper(), approved_by, approved_by, reason, t, t)
            )

            updated = c.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()

        log_lineage(memory_id, f"PROMOTED_{old_scope}_TO_{target_scope.upper()}", approved_by, {
            "from_scope": old_scope,
            "to_scope": target_scope.upper(),
            "reason": reason
        })
        return dict(updated) if updated else {}

    def list_promotions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists promotion records for visibility."""
        q = "SELECT * FROM promotions WHERE 1=1"
        p = []
        if status:
            q += " AND status = ?"
            p.append(status)
        q += " ORDER BY created_at DESC"
        with connect() as c:
            return [dict(r) for r in c.execute(q, p).fetchall()]
