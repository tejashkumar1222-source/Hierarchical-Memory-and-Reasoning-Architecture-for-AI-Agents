import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_ret_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.memory.retrieval import score_memory, compute_term_vector, cosine_similarity

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_eight_signal_scoring_breakdown():
    memory_dict = {
        'content': 'Hierarchical memory enables controlled information sharing across agents',
        'scope': 'GLOBAL',
        'owner_agent': 'system',
        'last_accessed': '2026-09-22T10:00:00+00:00',
        'importance': 0.8,
        'confidence': 0.9,
        'source_quality': 0.85,
        'access_count': 3
    }
    query = 'hierarchical memory sharing'
    scores = score_memory(memory_dict, query, requester='orchestrator')

    required_signals = [
        'semantic', 'lexical', 'recency', 'importance',
        'confidence', 'frequency', 'scope', 'source_quality', 'final_score'
    ]
    for sig in required_signals:
        assert sig in scores
        assert 0.0 <= scores[sig] <= 1.0

    assert scores['final_score'] > 0.4

def test_cosine_similarity_computation():
    v1 = compute_term_vector("hierarchical memory architecture")
    v2 = compute_term_vector("hierarchical memory architecture")
    v3 = compute_term_vector("quantum baking recipe")

    assert cosine_similarity(v1, v2) > 0.95
    assert cosine_similarity(v1, v3) < 0.1

def test_retrieval_ranking_and_latency():
    mgr = MemoryManager()
    mgr.add("FastAPI is an asynchronous Python web framework", scope='GLOBAL', importance=0.9, confidence=0.95)
    mgr.add("Weather forecast in Madrid is sunny", scope='GLOBAL', importance=0.2, confidence=0.5)

    results = mgr.retrieve("FastAPI framework", requester='coder', top_k=5)
    assert len(results) >= 1
    assert "FastAPI" in results[0]['content']
    assert 'retrieval_latency_ms' in results[0]
    assert results[0]['retrieval_latency_ms'] < 100.0  # Requirement: <100ms retrieval
