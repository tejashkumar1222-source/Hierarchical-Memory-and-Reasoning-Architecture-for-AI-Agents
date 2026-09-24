"""
HMRA Memory Consolidation Engine

Periodically or on-demand processes active memories to:
1. Identify duplicate memories and merge them into primary records.
2. Link semantically related memories.
3. Detect factual contradictions and group them into conflict clusters.
4. Auto-resolve conflicts where evidence delta is decisive; otherwise preserve uncertainty.
5. Compress repetitive information and maintain lineage.
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..db import connect
from .models import MemoryStatus, ConsolidationReport
from .retrieval import compute_term_vector, cosine_similarity, lexical_similarity
from .lifecycle import log_lineage, mark_superseded, mark_conflict
from .conflicts import ConflictManager

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

NEGATION_PATTERNS = re.compile(
    r"\b(not|never|no|cannot|can't|isn't|aren't|doesn't|does not|false|incorrect|untrue|refuted|opposite)\b",
    re.IGNORECASE
)

class MemoryConsolidator:
    def __init__(self):
        self.conflict_mgr = ConflictManager()

    def is_contradiction(self, text_a: str, text_b: str, sim: float) -> bool:
        """
        Determines if two texts with high subject similarity exhibit contradicting claims.
        Heuristics:
        1. Asymmetric negation polarity with shared topical vocabulary.
        2. Conflicting numeric/attribute values (e.g. 'version = 3.11' vs 'version = 3.12').
        """
        if sim < 0.40:
            return False

        has_neg_a = bool(NEGATION_PATTERNS.search(text_a))
        has_neg_b = bool(NEGATION_PATTERNS.search(text_b))

        if has_neg_a != has_neg_b:
            return True

        # Check for numeric or property conflicts (e.g. key = value differences)
        nums_a = set(re.findall(r"\b\d+(?:\.\d+)?\b", text_a))
        nums_b = set(re.findall(r"\b\d+(?:\.\d+)?\b", text_b))
        if nums_a and nums_b and nums_a != nums_b and sim >= 0.55:
            return True

        return False

    def consolidate(self, scope: Optional[str] = None) -> ConsolidationReport:
        """Runs the consolidation pipeline across active memories."""
        report = ConsolidationReport()

        query = "SELECT * FROM memories WHERE status = 'ACTIVE'"
        params = []
        if scope:
            query += " AND scope = ?"
            params.append(scope.upper())
        query += " ORDER BY created_at ASC"

        with connect() as c:
            rows = [dict(r) for r in c.execute(query, params).fetchall()]

        if len(rows) < 2:
            return report

        # Precompute vectors
        vectors = []
        for r in rows:
            v = None
            if r.get('embedding_json'):
                try:
                    v = json.loads(r['embedding_json'])
                except Exception:
                    pass
            if not v:
                v = compute_term_vector(r['content'])
            vectors.append(v)

        processed_ids = set()

        for i in range(len(rows)):
            id_a = rows[i]['id']
            if id_a in processed_ids:
                continue

            for j in range(i + 1, len(rows)):
                id_b = rows[j]['id']
                if id_b in processed_ids:
                    continue

                text_a = rows[i]['content']
                text_b = rows[j]['content']
                sim = cosine_similarity(vectors[i], vectors[j])
                lex = lexical_similarity(text_a, text_b)

                # Check for Duplicate: very high semantic and lexical match
                if sim >= 0.85 or (sim >= 0.75 and lex >= 0.75):
                    report.duplicates_found += 1
                    # Primary record is the one with higher confidence/importance
                    score_a = rows[i]['confidence'] + rows[i]['importance']
                    score_b = rows[j]['confidence'] + rows[j]['importance']
                    primary, secondary = (rows[i], rows[j]) if score_a >= score_b else (rows[j], rows[i])

                    # Merge secondary into primary
                    t = now_iso()
                    new_count = primary['access_count'] + secondary['access_count']
                    # Link related ids
                    rel = json.loads(primary.get('related_memory_ids') or '[]')
                    if secondary['id'] not in rel:
                        rel.append(secondary['id'])

                    with connect() as c:
                        c.execute(
                            '''UPDATE memories
                               SET access_count = ?, related_memory_ids = ?, updated_at = ?
                               WHERE id = ?''',
                            (new_count, json.dumps(rel), t, primary['id'])
                        )
                        c.execute(
                            '''UPDATE memories
                               SET status = 'MERGED', parent_memory_id = ?, updated_at = ?
                               WHERE id = ?''',
                            (primary['id'], t, secondary['id'])
                        )

                    log_lineage(primary['id'], "MERGED_WITH", "consolidation_engine", {"merged_memory_id": secondary['id']})
                    log_lineage(secondary['id'], "MERGED_INTO", "consolidation_engine", {"primary_memory_id": primary['id']})

                    report.merged += 1
                    report.details.append(f"Merged duplicate {secondary['id']} into {primary['id']}")
                    processed_ids.add(secondary['id'])
                    continue

                # Check for Contradiction
                if self.is_contradiction(text_a, text_b, sim):
                    report.conflicts_found += 1
                    cid = self.conflict_mgr.create_conflict(
                        memory_a_id=id_a,
                        memory_b_id=id_b,
                        detected_by="consolidation_engine",
                        confidence_a=rows[i]['confidence'],
                        confidence_b=rows[j]['confidence']
                    )
                    report.details.append(f"Conflict {cid} detected between {id_a} and {id_b}")

                    # Evaluate if conflict can be auto-resolved based on decisive evidence delta
                    eval_res = self.conflict_mgr.evaluate_conflict(cid)
                    if eval_res.get('can_auto_resolve'):
                        rec = eval_res['recommendation']
                        self.conflict_mgr.resolve_conflict(
                            cid,
                            resolution=rec,
                            note="Auto-resolved by consolidation engine based on decisive evidence delta",
                            resolved_by="consolidation_engine"
                        )
                        report.conflicts_resolved += 1
                        report.details.append(f"Conflict {cid} auto-resolved with {rec}")
                        if rec == "RESOLVE_A":
                            processed_ids.add(id_b)
                        elif rec == "RESOLVE_B":
                            processed_ids.add(id_a)
                    else:
                        report.details.append(f"Conflict {cid} preserved as OPEN for review")

        # Check pending promotions count
        with connect() as c:
            p_row = c.execute("SELECT COUNT(*) AS cnt FROM promotions WHERE status = 'PENDING'").fetchone()
            if p_row:
                report.promotions_pending = p_row['cnt']

        return report
