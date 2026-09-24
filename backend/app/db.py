import os
import sqlite3
from contextlib import contextmanager
from .config import DATA_DIR

TABLES_SCHEMA = '''
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    scope TEXT NOT NULL CHECK(scope IN ('GLOBAL','TEAM','PRIVATE')),
    owner_agent TEXT NOT NULL DEFAULT 'system',
    team_id TEXT NOT NULL DEFAULT 'default',
    source TEXT NOT NULL DEFAULT 'conversation',
    source_quality REAL NOT NULL DEFAULT 0.7,
    confidence REAL NOT NULL DEFAULT 0.7,
    importance REAL NOT NULL DEFAULT 0.5,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    version INTEGER NOT NULL DEFAULT 1,
    parent_memory_id TEXT,
    related_memory_ids TEXT NOT NULL DEFAULT '[]',
    promoted_from TEXT,
    promotion_reason TEXT,
    contradiction_group_id TEXT,
    embedding_json TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS memory_lineage (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conflicts (
    id TEXT PRIMARY KEY,
    memory_a_id TEXT NOT NULL,
    memory_b_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    detected_by TEXT NOT NULL,
    confidence_a REAL NOT NULL DEFAULT 0.7,
    confidence_b REAL NOT NULL DEFAULT 0.7,
    resolution TEXT,
    resolution_note TEXT,
    resolved_by TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    requester TEXT NOT NULL DEFAULT 'orchestrator',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    final_answer TEXT,
    plan_json TEXT NOT NULL DEFAULT '{}',
    trace_json TEXT NOT NULL DEFAULT '[]',
    metrics_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_runs (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    scope TEXT NOT NULL DEFAULT 'TEAM',
    owner_agent TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    memory_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS promotions (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    from_scope TEXT NOT NULL,
    to_scope TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    approved_by TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id TEXT PRIMARY KEY,
    run_at TEXT NOT NULL,
    config_name TEXT NOT NULL,
    baseline_results_json TEXT NOT NULL DEFAULT '{}',
    ablation_results_json TEXT NOT NULL DEFAULT '{}',
    summary_metrics_json TEXT NOT NULL DEFAULT '{}'
);
'''

INDEXES_SCHEMA = '''
CREATE INDEX IF NOT EXISTS idx_mem_scope ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_mem_owner ON memories(owner_agent);
CREATE INDEX IF NOT EXISTS idx_mem_team ON memories(team_id);
CREATE INDEX IF NOT EXISTS idx_mem_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_mem_created ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_mem_updated ON memories(updated_at);
CREATE INDEX IF NOT EXISTS idx_mem_access ON memories(access_count);
CREATE INDEX IF NOT EXISTS idx_mem_conflict ON memories(contradiction_group_id);
CREATE INDEX IF NOT EXISTS idx_lineage_mem ON memory_lineage(memory_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);
'''

def get_db_path() -> str:
    return os.getenv('HMRA_DB_PATH', str(DATA_DIR / 'hmra.db'))

@contextmanager
def connect():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        yield conn
        conn.commit()
    finally:
        conn.close()

def _migrate_existing_schema(conn: sqlite3.Connection):
    """Safely adds missing columns to existing tables before creating indexes."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(memories)")
    existing_cols = {row['name'] for row in cur.fetchall()}
    
    col_defs = {
        'team_id': "TEXT NOT NULL DEFAULT 'default'",
        'source_quality': "REAL NOT NULL DEFAULT 0.7",
        'updated_at': "TEXT DEFAULT ''",
        'version': "INTEGER NOT NULL DEFAULT 1",
        'parent_memory_id': "TEXT",
        'promoted_from': "TEXT",
        'promotion_reason': "TEXT",
        'contradiction_group_id': "TEXT",
        'embedding_json': "TEXT",
    }
    for col, col_type in col_defs.items():
        if col not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE memories ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    cur.execute("UPDATE memories SET updated_at = created_at WHERE updated_at IS NULL OR updated_at = ''")

    cur.execute("PRAGMA table_info(conflicts)")
    existing_conflict_cols = {row['name'] for row in cur.fetchall()}
    conflict_col_defs = {
        'confidence_a': "REAL NOT NULL DEFAULT 0.7",
        'confidence_b': "REAL NOT NULL DEFAULT 0.7",
        'resolution': "TEXT",
        'resolved_by': "TEXT",
    }
    for col, col_type in conflict_col_defs.items():
        if col not in existing_conflict_cols:
            try:
                cur.execute(f"ALTER TABLE conflicts ADD COLUMN {col} {col_type}")
            except Exception:
                pass

def init_db():
    with connect() as c:
        try:
            c.execute("PRAGMA journal_mode = WAL")
        except Exception:
            pass
        c.executescript(TABLES_SCHEMA)
        _migrate_existing_schema(c)
        c.executescript(INDEXES_SCHEMA)
