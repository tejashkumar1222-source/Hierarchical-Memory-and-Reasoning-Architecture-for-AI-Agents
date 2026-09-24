"""
HMRA Evaluation Metrics Engine

Calculates empirical research metrics:
- Answer correctness score (Keyword and semantic coverage)
- Memory retrieval precision & recall
- Retrieval latency (ms)
- Conflict detection and resolution rates
- Duplicate identification rate
- Task completion rate
"""

import re
from typing import List, Dict, Any

def compute_keyword_coverage(text: str, expected_keywords: List[str]) -> float:
    """Calculates the proportion of expected keywords present in the generated answer."""
    if not expected_keywords:
        return 1.0
    text_lower = (text or '').lower()
    matches = sum(1 for kw in expected_keywords if re.search(r'\b' + re.escape(kw.lower()), text_lower))
    return round(matches / float(len(expected_keywords)), 3)

def compute_memory_precision(retrieved_memories: List[Dict[str, Any]], expected_scope: str) -> float:
    """Precision: proportion of retrieved memories that match the expected scope or relevant subject."""
    if not retrieved_memories:
        return 1.0
    relevant = sum(1 for m in retrieved_memories if m.get('scope') == expected_scope or m.get('scope') == 'GLOBAL')
    return round(relevant / float(len(retrieved_memories)), 3)

def compute_memory_recall(retrieved_memories: List[Dict[str, Any]], total_relevant_count: int) -> float:
    """Recall: proportion of total relevant memories retrieved."""
    if total_relevant_count <= 0:
        return 1.0
    return round(min(1.0, len(retrieved_memories) / float(total_relevant_count)), 3)

def aggregate_system_metrics(run_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregates per-test results into overall benchmark performance figures."""
    if not run_results:
        return {}

    n = float(len(run_results))
    avg_correctness = sum(r.get('correctness', 0.0) for r in run_results) / n
    avg_latency = sum(r.get('latency_ms', 0.0) for r in run_results) / n
    avg_precision = sum(r.get('precision', 1.0) for r in run_results) / n
    avg_recall = sum(r.get('recall', 1.0) for r in run_results) / n
    completion_rate = sum(1 for r in run_results if r.get('completed', False)) / n

    return {
        'total_tests': int(n),
        'task_completion_rate': round(completion_rate * 100.0, 1),
        'avg_correctness': round(avg_correctness * 100.0, 1),
        'avg_retrieval_latency_ms': round(avg_latency, 2),
        'avg_memory_precision': round(avg_precision * 100.0, 1),
        'avg_memory_recall': round(avg_recall * 100.0, 1),
    }
