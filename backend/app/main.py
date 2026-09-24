"""
HMRA Live - FastAPI Application & REST API Endpoints

Implements:
- Chat with multi-agent orchestration, web search toggle, and memory toggle
- Hierarchical memory operations (GLOBAL, TEAM, PRIVATE) with access control
- Real-time agent status telemetry (IDLE, RUNNING, SUCCESS, REVIEW, CONFLICT)
- Conflict inspection and resolution
- Memory consolidation engine
- Document ingestion (TXT, MD, CSV, JSON, PDF)
- Empirical evaluation benchmark runner
- Comprehensive system status & live health checks
"""

import json
import uuid
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .db import init_db, connect
from .config import (
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_API_KEY,
    UPLOAD_DIR,
    BRAVE_API_KEY,
    RETRIEVAL_WEIGHTS
)
from .llm import LLMClient, LLMError
from .memory import (
    MemoryManager,
    SCOPES,
    MemoryScope,
    MemoryStatus,
    can_read_memory,
    can_write_memory
)
from .orchestration import Orchestrator, GLOBAL_STATE_TRACKER
from .tools import GLOBAL_TOOL_REGISTRY, process_and_ingest_document, BraveSearchProvider
from .evaluation import EvaluationRunner

ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(
    title='HMRA - Hierarchical Memory and Reasoning Architecture',
    description='Research Prototype for Multi-Agent Systems with Hierarchical Memory and 3-Level Reasoning',
    version='2.0.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)

# Initialize subsystems
init_db()
llm = LLMClient()
memory = MemoryManager()
eval_runner = EvaluationRunner(llm, memory)
search_provider = BraveSearchProvider()

ACTIVE_TRACES: Dict[str, List[Dict[str, Any]]] = {}

def trace_factory(exid: str):
    ACTIVE_TRACES[exid] = []
    def trace(stage: str, actor: str, data: Dict[str, Any]):
        ACTIVE_TRACES[exid].append({
            'stage': stage,
            'actor': actor,
            'data': data
        })
    return trace

# -------------------------------------------------------------
# PYDANTIC REQUEST SCHEMAS
# -------------------------------------------------------------
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    requester: str = 'orchestrator'
    use_memory: bool = True
    use_web_search: bool = False

class MemoryAddRequest(BaseModel):
    content: str = Field(..., min_length=1)
    scope: str = 'PRIVATE'
    owner_agent: str = 'system'
    team_id: str = 'default'
    source: str = 'manual'
    confidence: float = 0.8
    importance: float = 0.5
    source_quality: float = 0.8
    metadata: Optional[Dict[str, Any]] = None

class PromotionRequest(BaseModel):
    target_scope: str
    approved_by: str = 'reviewer'
    reason: str = 'Manually initiated promotion'

class ConflictResolveRequest(BaseModel):
    resolution: str = Field(..., description="RESOLVE_A, RESOLVE_B, or DISMISSED")
    note: str = ""
    resolved_by: str = "reviewer"

# -------------------------------------------------------------
# CORE APPLICATION ROUTES
# -------------------------------------------------------------
@app.get('/')
def root():
    return FileResponse(ROOT / 'frontend' / 'index.html')

@app.get('/api/status')
@app.get('/api/system/status')
def system_status():
    """Returns comprehensive runtime health and configuration checks."""
    mem_counts = memory.count_by_scope()
    total_memories = sum(mem_counts.values())

    return {
        'llm': {
            'status': 'CONNECTED' if llm.configured else 'NOT CONFIGURED',
            'provider': LLM_PROVIDER,
            'model': LLM_MODEL,
            'mode': 'REAL LLM' if llm.configured else 'OFFLINE / NOT CONFIGURED'
        },
        'database': {
            'status': 'CONNECTED',
            'engine': 'SQLite persistent',
            'total_active_memories': total_memories,
            'memory_scopes': mem_counts
        },
        'web_search': {
            'status': 'CONNECTED' if search_provider.is_configured else 'NOT CONFIGURED',
            'provider': 'Brave Search API' if search_provider.is_configured else 'None'
        },
        'embeddings': {
            'status': 'AVAILABLE',
            'type': 'Normalized Term Vectors + Cosine Similarity (Fallback: Lexical Jaccard)'
        },
        'memory': {
            'status': 'READY',
            'scopes': list(SCOPES),
            'retrieval_weights': RETRIEVAL_WEIGHTS
        },
        'agents': {
            'status': 'READY',
            'count': 5,
            'specialists': ['Researcher', 'Coder', 'Reviewer', 'Critic', 'Synthesizer']
        },
        'tools': {
            'status': 'READY',
            'tools': [t['name'] for t in GLOBAL_TOOL_REGISTRY.list_tools()]
        }
    }

@app.post('/api/chat')
def chat(req: ChatRequest):
    """Processes chat query through the full HMRA multi-agent reasoning hierarchy."""
    if not llm.configured:
        raise HTTPException(
            status_code=503,
            detail='Real LLM is not configured. Add LLM_API_KEY to your .env file and restart.'
        )

    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    trace_fn = trace_factory(execution_id)

    try:
        orchestrator = Orchestrator(llm, memory, trace_fn=trace_fn)
        result = orchestrator.run(
            query=req.query,
            requester=req.requester,
            execution_id=execution_id,
            use_memory=req.use_memory,
            use_web_search=req.use_web_search
        )
        result['trace'] = ACTIVE_TRACES.pop(execution_id, [])
        return result
    except LLMError as e:
        ACTIVE_TRACES.pop(execution_id, None)
        raise HTTPException(status_code=502, detail=f"LLM Provider Error: {e}")
    except Exception as e:
        ACTIVE_TRACES.pop(execution_id, None)
        raise HTTPException(status_code=500, detail=f"HMRA Execution Failure: {e}")

# -------------------------------------------------------------
# MEMORY HIERARCHY & RETRIEVAL ENDPOINTS
# -------------------------------------------------------------
@app.get('/api/memory')
def get_memories(
    scope: Optional[str] = None,
    owner: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    requester: Optional[str] = None
):
    """Lists memories with optional filtering and scope-based access control."""
    items = memory.list(scope=scope, owner=owner, status=status, limit=limit, requester=requester)
    counts = memory.count_by_scope()
    return {
        'count': len(items),
        'scope_counts': counts,
        'memories': items
    }

@app.get('/api/memory/search')
def search_memories(q: str, requester: str = 'orchestrator', top_k: int = 6):
    """Performs 8-signal weighted retrieval across authorized memory scopes."""
    results = memory.retrieve(query=q, requester=requester, top_k=top_k)
    return {'count': len(results), 'results': results}

@app.get('/api/memory/{memory_id}')
def get_single_memory(memory_id: str):
    mem = memory.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
    return mem

@app.post('/api/memory')
def create_memory(req: MemoryAddRequest):
    """Creates a new memory record, enforcing scope validation."""
    if req.scope.upper() not in SCOPES:
        raise HTTPException(status_code=400, detail=f"Scope must be one of {SCOPES}")

    # Access control verification: check if requester can write to scope
    if not can_write_memory(req.scope, req.owner_agent, req.owner_agent, req.team_id):
        raise HTTPException(status_code=403, detail=f"Agent '{req.owner_agent}' cannot write directly to '{req.scope}' scope.")

    return memory.add(
        content=req.content,
        scope=req.scope,
        owner_agent=req.owner_agent,
        team_id=req.team_id,
        source=req.source,
        confidence=req.confidence,
        importance=req.importance,
        source_quality=req.source_quality,
        metadata=req.metadata
    )

@app.post('/api/memory/consolidate')
def consolidate_memory(scope: Optional[str] = None):
    """Runs deduplication, merging, and contradiction grouping."""
    report = memory.consolidate(scope=scope)
    return report.model_dump()

@app.post('/api/memory/{memory_id}/promote')
def promote_memory(memory_id: str, req: PromotionRequest):
    """Graduates a memory record to a higher scope through the reviewer gate."""
    try:
        updated = memory.promote(
            memory_id=memory_id,
            target_scope=req.target_scope,
            approved_by=req.approved_by,
            reason=req.reason
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Promotion failed: {e}")

# -------------------------------------------------------------
# CONFLICT MANAGEMENT ENDPOINTS
# -------------------------------------------------------------
@app.get('/api/conflicts')
def list_conflicts(status: Optional[str] = None):
    """Retrieves all detected contradiction records with enriched evidence."""
    conflicts = memory.conflict_mgr.get_conflicts(status=status)
    return {'count': len(conflicts), 'conflicts': conflicts}

@app.post('/api/conflicts/{conflict_id}/resolve')
def resolve_conflict(conflict_id: str, req: ConflictResolveRequest):
    """Resolves an open memory conflict."""
    valid_resolutions = {'RESOLVE_A', 'RESOLVE_B', 'DISMISSED'}
    if req.resolution not in valid_resolutions:
        raise HTTPException(status_code=400, detail=f"Resolution must be one of {valid_resolutions}")

    success = memory.conflict_mgr.resolve_conflict(
        conflict_id=conflict_id,
        resolution=req.resolution,
        note=req.note,
        resolved_by=req.resolved_by
    )
    if not success:
        raise HTTPException(status_code=404, detail="Conflict record not found")
    return {'ok': True, 'conflict_id': conflict_id, 'resolution': req.resolution}

# -------------------------------------------------------------
# DOCUMENT INGESTION (CHAT "+" BUTTON & DOCUMENT PAGE)
# -------------------------------------------------------------
@app.post('/api/ingest')
async def ingest_document(
    file: UploadFile = File(...),
    scope: str = 'TEAM',
    owner_agent: str = 'system'
):
    """
    Ingests TXT, MD, CSV, JSON, and PDF files.
    Chunks text, extracts structured semantics, and creates searchable memory records.
    """
    if scope.upper() not in SCOPES:
        raise HTTPException(status_code=400, detail=f"Invalid scope '{scope}'. Allowed: {SCOPES}")

    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        res = process_and_ingest_document(
            filename=file.filename or 'unnamed_upload',
            data=content_bytes,
            scope=scope,
            owner_agent=owner_agent,
            memory_mgr=memory
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {e}")

# -------------------------------------------------------------
# AGENT TELEMETRY & SYSTEM INSPECTION
# -------------------------------------------------------------
@app.get('/api/agents')
def get_agents():
    """Returns live runtime state for all 5 agents and 3 reasoning components."""
    states = GLOBAL_STATE_TRACKER.get_all_states()
    return {'agents': states}

@app.get('/api/trace/{execution_id}')
def get_trace(execution_id: str):
    """Retrieves live execution trace steps."""
    trace_steps = ACTIVE_TRACES.get(execution_id, [])
    if not trace_steps:
        # Check database
        with connect() as c:
            row = c.execute("SELECT trace_json FROM executions WHERE id = ?", (execution_id,)).fetchone()
            if row:
                try:
                    trace_steps = json.loads(row['trace_json'])
                except Exception:
                    trace_steps = []
    return {'execution_id': execution_id, 'trace': trace_steps}

# -------------------------------------------------------------
# BENCHMARK EVALUATION & ABLATION RUNNER
# -------------------------------------------------------------
@app.get('/api/evaluation')
def get_evaluations():
    """Retrieves historical benchmark evaluation runs."""
    with connect() as c:
        rows = c.execute("SELECT * FROM evaluation_runs ORDER BY run_at DESC LIMIT 10").fetchall()
        runs = []
        for r in rows:
            item = dict(r)
            try:
                item['summary_metrics'] = json.loads(item['summary_metrics_json'])
                item['baseline_results'] = json.loads(item['baseline_results_json'])
                item['ablation_results'] = json.loads(item['ablation_results_json'])
            except Exception:
                pass
            runs.append(item)
    return {'runs': runs}

@app.post('/api/evaluation/run')
def run_evaluation(sample_size: int = Query(default=4, ge=1, le=14)):
    """Triggers live empirical benchmark comparing Baselines 1-4 and Ablations A-F."""
    try:
        report = eval_runner.run_benchmark(sample_size=sample_size)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark run failed: {e}")

# -------------------------------------------------------------
# DEMO DATA SEEDING & RESET
# -------------------------------------------------------------
@app.post('/api/seed')
def seed_demo_data():
    """Populates safe synthetic data demonstrating all HMRA research scenarios."""
    # 1. GLOBAL Memory
    m_global = memory.add(
        content="HMRA Architecture Standard: All inter-agent communication must use typed structured messages with task_id and confidence scores.",
        scope='GLOBAL',
        owner_agent='system',
        source='system_specification',
        confidence=0.95,
        importance=0.90,
        source_quality=0.95,
        metadata={'scenario': 'DEMO_GLOBAL'}
    )

    # 2. TEAM Memory
    m_team = memory.add(
        content="Team Decision: The backend API layer is constructed with FastAPI and asynchronous endpoint handlers.",
        scope='TEAM',
        owner_agent='researcher',
        source='sprint_planning',
        confidence=0.85,
        importance=0.75,
        source_quality=0.85,
        metadata={'scenario': 'DEMO_TEAM'}
    )

    # 3. PRIVATE Memory (Isolated to Researcher)
    m_private = memory.add(
        content="Researcher Scratchpad: Confidential experimental observation - project deadline scheduled for 30 September.",
        scope='PRIVATE',
        owner_agent='researcher',
        source='private_notes',
        confidence=0.80,
        importance=0.70,
        source_quality=0.80,
        metadata={'scenario': 'DEMO_PRIVATE_ISOLATION'}
    )

    # 4. CONTRADICTION GROUP (Memory A vs Memory B)
    m_conf_a = memory.add(
        content="HMRA primary persistent storage database engine is SQLite.",
        scope='GLOBAL',
        owner_agent='coder',
        source='architecture_doc',
        confidence=0.88,
        importance=0.80,
        source_quality=0.90
    )
    m_conf_b = memory.add(
        content="HMRA primary persistent storage database engine is MongoDB.",
        scope='GLOBAL',
        owner_agent='critic',
        source='unverified_forum_post',
        confidence=0.45,
        importance=0.50,
        source_quality=0.40
    )
    cid = memory.conflict_mgr.create_conflict(
        memory_a_id=m_conf_a['id'],
        memory_b_id=m_conf_b['id'],
        detected_by="critic",
        confidence_a=0.88,
        confidence_b=0.45
    )

    return {
        'ok': True,
        'message': 'Demo scenarios seeded successfully.',
        'seeded': {
            'global_id': m_global['id'],
            'team_id': m_team['id'],
            'private_id': m_private['id'],
            'conflict_id': cid
        }
    }

@app.post('/api/reset')
def reset_all_data():
    """Resets memory, conflicts, and execution logs to a clean state."""
    with connect() as c:
        c.execute('DELETE FROM memories')
        c.execute('DELETE FROM memory_lineage')
        c.execute('DELETE FROM conflicts')
        c.execute('DELETE FROM executions')
        c.execute('DELETE FROM tasks')
        c.execute('DELETE FROM agent_runs')
        c.execute('DELETE FROM tool_runs')
        c.execute('DELETE FROM documents')
        c.execute('DELETE FROM document_chunks')
        c.execute('DELETE FROM promotions')
    GLOBAL_STATE_TRACKER.reset_all_to_idle()
    return {'ok': True, 'message': 'Persistent memory and execution states cleared.'}
