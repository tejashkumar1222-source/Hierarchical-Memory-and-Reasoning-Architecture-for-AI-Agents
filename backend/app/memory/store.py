"""
HMRA Persistent Memory Manager

Orchestrates:
- SQLite persistent storage
- Access control verification
- Multi-signal 8-feature retrieval
- Lineage logging
- Lifecycle state transitions
- Promotion & Conflict integration
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..db import connect
from ..config import TOP_K, MAX_CONTEXT_CHARS, RETRIEVAL_WEIGHTS
from .models import MemoryScope, MemoryStatus
from .access_control import can_read_memory, can_write_memory, can_promote_memory
from .retrieval import RetrievalEngine, compute_term_vector
from .lifecycle import log_lineage, mark_superseded, transition_status
from .promotion import PromotionManager
from .conflicts import ConflictManager
from .consolidation import MemoryConsolidator

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def clamp(val: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(val)))
    except Exception:
        return low

class MemoryManager:
    def __init__(self):
        self.retrieval_engine = RetrievalEngine()
        self.promotion_mgr = PromotionManager()
        self.conflict_mgr = ConflictManager()
        self.consolidator = MemoryConsolidator()

    def add(
        self,
        content: str,
        scope: str = 'PRIVATE',
        owner_agent: str = 'system',
        team_id: str = 'default',
        source: str = 'conversation',
        confidence: float = 0.7,
        importance: float = 0.5,
        source_quality: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
        related: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates and persists a new memory record with precomputed vector representation."""
        s = scope.upper()
        if s not in {MemoryScope.GLOBAL.value, MemoryScope.TEAM.value, MemoryScope.PRIVATE.value}:
            raise ValueError(f"Invalid scope: {scope}")

        t = now_iso()
        mid = f"mem_{uuid.uuid4().hex[:12]}"
        vector = compute_term_vector(content)
        vector_json = json.dumps(vector)

        with connect() as c:
            c.execute(
                '''INSERT INTO memories(
                    id, content, scope, owner_agent, team_id, source, source_quality,
                    confidence, importance, access_count, created_at, updated_at,
                    last_accessed, status, version, parent_memory_id, related_memory_ids,
                    embedding_json, metadata_json
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 'ACTIVE', 1, ?, ?, ?, ?)''',
                (
                    mid, content, s, owner_agent, team_id, source,
                    clamp(source_quality), clamp(confidence), clamp(importance),
                    t, t, t, parent_id, json.dumps(related or []),
                    vector_json, json.dumps(metadata or {})
                )
            )

        log_lineage(mid, "CREATED", owner_agent, {"scope": s, "source": source, "confidence": confidence})
        return self.get(mid)

    def get(self, mid: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single memory record by ID."""
        with connect() as c:
            r = c.execute('SELECT * FROM memories WHERE id = ?', (mid,)).fetchone()
            if not r:
                return None
            res = dict(r)
            try:
                res['metadata'] = json.loads(res.get('metadata_json') or '{}')
            except Exception:
                res['metadata'] = {}
            try:
                res['related_memory_ids'] = json.loads(res.get('related_memory_ids') or '[]')
            except Exception:
                res['related_memory_ids'] = []
            return res

    def list(
        self,
        scope: Optional[str] = None,
        owner: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
        requester: Optional[str] = None,
        requester_team: str = 'default'
    ) -> List[Dict[str, Any]]:
        """Lists memories matching filters, applying access control if requester is provided."""
        q = 'SELECT * FROM memories WHERE 1=1'
        p = []
        if scope:
            q += ' AND scope = ?'
            p.append(scope.upper())
        if owner:
            q += ' AND owner_agent = ?'
            p.append(owner)
        if status:
            q += ' AND status = ?'
            p.append(status.upper())
        q += ' ORDER BY created_at DESC LIMIT ?'
        p.append(limit)

        with connect() as c:
            rows = [dict(r) for r in c.execute(q, p).fetchall()]

        out = []
        for r in rows:
            if requester and not can_read_memory(r, requester_agent=requester, requester_team=requester_team):
                continue
            try:
                r['metadata'] = json.loads(r.get('metadata_json') or '{}')
            except Exception:
                r['metadata'] = {}
            try:
                r['related_memory_ids'] = json.loads(r.get('related_memory_ids') or '[]')
            except Exception:
                r['related_memory_ids'] = []
            out.append(r)
        return out

    def count_by_scope(self) -> Dict[str, int]:
        """Returns memory counts broken down by scope for dashboard reporting."""
        with connect() as c:
            rows = c.execute(
                "SELECT scope, COUNT(*) as cnt FROM memories WHERE status = 'ACTIVE' GROUP BY scope"
            ).fetchall()
            counts = {MemoryScope.GLOBAL.value: 0, MemoryScope.TEAM.value: 0, MemoryScope.PRIVATE.value: 0}
            for r in rows:
                counts[r['scope']] = r['cnt']
            return counts

    def retrieve(
        self,
        query: str,
        requester: str = 'orchestrator',
        top_k: Optional[int] = None,
        requester_team: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        Multi-signal scope-filtered retrieval.
        Applies access control rules so agents strictly access only authorized scopes.
        Increments access count and updates last_accessed timestamp.
        """
        k = top_k or TOP_K
        # Get active memories accessible to requester
        all_active = self.list(status='ACTIVE', limit=1000)
        accessible = [m for m in all_active if can_read_memory(m, requester_agent=requester, requester_team=requester_team)]

        ranked, latency_ms = self.retrieval_engine.rank(
            candidate_memories=accessible,
            query=query,
            requester=requester,
            top_k=k
        )

        t = now_iso()
        with connect() as c:
            for item in ranked:
                c.execute(
                    '''UPDATE memories
                       SET access_count = access_count + 1, last_accessed = ?
                       WHERE id = ?''',
                    (t, item['id'])
                )
                item['access_count'] = item.get('access_count', 0) + 1
                item['last_accessed'] = t
                item['retrieval_latency_ms'] = latency_ms

        return ranked

    def promote(
        self,
        memory_id: str,
        target_scope: str,
        approved_by: str = 'reviewer',
        reason: str = 'Promoted via promotion pipeline'
    ) -> Dict[str, Any]:
        """Promotes a memory record to a higher scope with reviewer gating."""
        return self.promotion_mgr.execute_promotion(
            memory_id=memory_id,
            target_scope=target_scope,
            approved_by=approved_by,
            reason=reason
        )

    def detect_conflict(self, content: str, candidate_rows: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Inspects candidate rows for contradiction against new content."""
        v_new = compute_term_vector(content)
        for r in candidate_rows:
            v_old = None
            if r.get('embedding_json'):
                try:
                    v_old = json.loads(r['embedding_json'])
                except Exception:
                    pass
            if not v_old:
                v_old = compute_term_vector(r['content'])

            sim = self.retrieval_engine.rank([r], content, requester='critic')[0]
            sim_score = sim[0]['retrieval_score'] if sim else 0.0
            if self.consolidator.is_contradiction(content, r['content'], sim_score):
                cid = self.conflict_mgr.create_conflict(
                    memory_a_id=r['id'],
                    memory_b_id="PENDING",
                    detected_by="memory_manager",
                    confidence_a=r.get('confidence', 0.7),
                    confidence_b=0.7
                )
                return cid, r
        return None, None

    def consolidate(self, scope: Optional[str] = None):
        """Runs the consolidation pipeline."""
        return self.consolidator.consolidate(scope=scope)

    def mark_superseded(self, old_id: str, new_id: str, actor: str = "system", reason: str = ""):
        """Marks old_id as superseded by new_id."""
        mark_superseded(old_id, new_id, actor=actor, reason=reason)

    def context(self, memories: List[Dict[str, Any]], max_chars: Optional[int] = None) -> str:
        """Builds a formatted context string within the character budget."""
        limit = max_chars or MAX_CONTEXT_CHARS
        parts = []
        total = 0
        for m in memories:
            sig = m.get('signals')
            score_txt = f" | score={m.get('retrieval_score', 0.0):.3f}" if m.get('retrieval_score') is not None else ""
            line = f"[{m['scope']} | Owner:{m['owner_agent']} | Conf:{m.get('confidence', 0.7):.2f}{score_txt}] {m['content']}"
            if total + len(line) > limit:
                break
            parts.append(line)
            total += len(line)
        return '\n'.join(parts)
