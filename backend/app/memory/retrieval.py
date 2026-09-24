"""
HMRA 8-Signal Memory Retrieval Engine

Implements multi-signal scoring:
1. Semantic similarity (Cosine similarity over vector representation with lexical fallback)
2. Lexical similarity (Jaccard token overlap / BM25-like token match)
3. Recency (Exponential decay: exp(-delta_days / 30))
4. Importance (Normalized importance 0.0 - 1.0)
5. Confidence (Normalized confidence 0.0 - 1.0)
6. Frequency (Access saturation: 1 - exp(-access_count / 5))
7. Scope relevance (Private match: 1.0, Team: 0.9, Global: 0.8)
8. Source quality (Normalized source quality 0.0 - 1.0)

Centrally configurable via RETRIEVAL_WEIGHTS.
Tracks latency for performance validation (<100ms benchmark).
"""

import math
import re
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

from ..config import RETRIEVAL_WEIGHTS

STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'were', 'will', 'with'
}

def tokenize(text: str) -> List[str]:
    """Extracts lowercase tokens, removing common noise."""
    tokens = re.findall(r"[a-zA-Z0-9_\u0080-\uffff]+", (text or '').lower())
    return [t for t in tokens if t not in STOPWORDS]

def compute_term_vector(text: str) -> Dict[str, float]:
    """
    Computes a normalized term-frequency vector.
    Used for fast, robust local cosine similarity without external dependencies.
    """
    tokens = tokenize(text)
    if not tokens:
        return {}
    tf: Dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    # Add bigrams for local semantic context
    for i in range(len(tokens) - 1):
        bg = f"{tokens[i]}_{tokens[i+1]}"
        tf[bg] = tf.get(bg, 0.0) + 0.5
    # Normalize vector to unit length
    norm = math.sqrt(sum(v * v for v in tf.values()))
    if norm > 0:
        for k in tf:
            tf[k] /= norm
    return tf

def cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """Computes cosine similarity between two normalized sparse term vectors."""
    if not v1 or not v2:
        return 0.0
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    dot = sum(val * v2.get(k, 0.0) for k, val in v1.items())
    return max(0.0, min(1.0, dot))

def lexical_similarity(query: str, text: str) -> float:
    """Computes Jaccard keyword overlap between query and text tokens."""
    q_toks = set(tokenize(query))
    m_toks = set(tokenize(text))
    if not q_toks or not m_toks:
        return 0.0
    intersection = q_toks & m_toks
    union = q_toks | m_toks
    return len(intersection) / float(len(union))

def recency_score(iso_timestamp: str) -> float:
    """Calculates exponential decay based on days elapsed since timestamp."""
    try:
        clean = (iso_timestamp or '').replace('Z', '+00:00')
        ts = datetime.fromisoformat(clean)
        age_days = (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0
        if age_days < 0:
            age_days = 0.0
        return math.exp(-age_days / 30.0)
    except Exception:
        return 0.5

def frequency_score(access_count: int) -> float:
    """Saturates access frequency towards 1.0 as access count grows."""
    cnt = max(0, int(access_count or 0))
    return 1.0 - math.exp(-cnt / 5.0)

def scope_score(scope: str, requester: str) -> float:
    """Assigns priority based on scope specificity for the requesting context."""
    s = (scope or '').upper()
    if s == 'PRIVATE':
        return 1.0 if requester else 0.4
    if s == 'TEAM':
        return 0.9
    if s == 'GLOBAL':
        return 0.8
    return 0.5

def score_memory(
    memory: Dict[str, Any],
    query: str,
    requester: str = 'orchestrator',
    context: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    Computes component scores and the final weighted HMRA retrieval score.
    Returns:
    {
        "semantic": ...,
        "lexical": ...,
        "recency": ...,
        "importance": ...,
        "confidence": ...,
        "frequency": ...,
        "scope": ...,
        "source_quality": ...,
        "final_score": ...
    }
    """
    w = weights or RETRIEVAL_WEIGHTS
    content = memory.get('content', '')

    # 1. Semantic similarity
    mem_vec = None
    emb_raw = memory.get('embedding_json')
    if emb_raw:
        try:
            mem_vec = json.loads(emb_raw)
        except Exception:
            mem_vec = None
    if mem_vec is None:
        mem_vec = compute_term_vector(content)

    q_vec = compute_term_vector(query)
    sem = cosine_similarity(q_vec, mem_vec)

    # 2. Lexical similarity
    lex = lexical_similarity(query, content)

    # If semantic vector is empty, graceful fallback to lexical
    if sem == 0.0 and lex > 0:
        sem = lex * 0.85

    # 3. Recency
    last_act = memory.get('last_accessed') or memory.get('created_at') or ''
    rec = recency_score(last_act)

    # 4. Importance & 5. Confidence
    imp = max(0.0, min(1.0, float(memory.get('importance', 0.5))))
    conf = max(0.0, min(1.0, float(memory.get('confidence', 0.7))))

    # 6. Frequency
    freq = frequency_score(memory.get('access_count', 0))

    # 7. Scope relevance
    scp = scope_score(memory.get('scope', 'GLOBAL'), requester)

    # 8. Source quality
    sq = max(0.0, min(1.0, float(memory.get('source_quality', 0.7))))

    # Weighted final score
    final_score = (
        w.get('semantic', 0.30) * sem +
        w.get('lexical', 0.10) * lex +
        w.get('recency', 0.10) * rec +
        w.get('importance', 0.15) * imp +
        w.get('confidence', 0.15) * conf +
        w.get('frequency', 0.05) * freq +
        w.get('scope', 0.10) * scp +
        w.get('source_quality', 0.05) * sq
    )

    return {
        'semantic': round(sem, 4),
        'lexical': round(lex, 4),
        'recency': round(rec, 4),
        'importance': round(imp, 4),
        'confidence': round(conf, 4),
        'frequency': round(freq, 4),
        'scope': round(scp, 4),
        'source_quality': round(sq, 4),
        'final_score': round(final_score, 4),
    }

class RetrievalEngine:
    """Manages multi-signal candidate scoring and ranking."""
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or RETRIEVAL_WEIGHTS

    def rank(
        self,
        candidate_memories: List[Dict[str, Any]],
        query: str,
        requester: str = 'orchestrator',
        top_k: int = 6
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Ranks candidate memories using 8-signal scoring.
        Requires relevance (semantic or lexical overlap) before ranking.
        Returns (ranked_memories_with_signals, latency_ms).
        """
        start_time = time.perf_counter()
        scored: List[Tuple[float, Dict[str, Any], Dict[str, float]]] = []

        for mem in candidate_memories:
            scores = score_memory(mem, query, requester=requester, weights=self.weights)
            # Must have query relevance
            if scores['semantic'] > 0.05 or scores['lexical'] > 0.05:
                scored.append((scores['final_score'], mem, scores))

        scored.sort(key=lambda item: item[0], reverse=True)
        ranked: List[Dict[str, Any]] = []

        for final_score, m_dict, signals in scored[:top_k]:
            item = dict(m_dict)
            item['retrieval_score'] = final_score
            item['signals'] = signals
            ranked.append(item)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return ranked, round(latency_ms, 2)
