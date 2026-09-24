from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MemoryScope(str, Enum):
    GLOBAL = "GLOBAL"
    TEAM = "TEAM"
    PRIVATE = "PRIVATE"

class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    CONFLICT = "CONFLICT"
    MERGED = "MERGED"
    DEPRECATED = "DEPRECATED"
    EXPIRED = "EXPIRED"
    PENDING_REVIEW = "PENDING_REVIEW"

class RetrievalSignals(BaseModel):
    semantic: float = 0.0
    lexical: float = 0.0
    recency: float = 0.0
    importance: float = 0.0
    confidence: float = 0.0
    frequency: float = 0.0
    scope: float = 0.0
    source_quality: float = 0.0
    final_score: float = 0.0

class MemoryRecord(BaseModel):
    id: str
    content: str
    scope: str = MemoryScope.PRIVATE.value
    owner_agent: str = "system"
    team_id: str = "default"
    source: str = "conversation"
    source_quality: float = 0.7
    confidence: float = 0.7
    importance: float = 0.5
    access_count: int = 0
    created_at: str
    updated_at: str
    last_accessed: str
    status: str = MemoryStatus.ACTIVE.value
    version: int = 1
    parent_memory_id: Optional[str] = None
    related_memory_ids: List[str] = Field(default_factory=list)
    promoted_from: Optional[str] = None
    promotion_reason: Optional[str] = None
    contradiction_group_id: Optional[str] = None
    embedding_json: Optional[str] = None
    metadata_json: Optional[str] = "{}"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retrieval_score: Optional[float] = None
    signals: Optional[RetrievalSignals] = None

class ConflictRecord(BaseModel):
    id: str
    memory_a_id: str
    memory_b_id: str
    status: str = "OPEN"
    detected_by: str = "consolidation_engine"
    confidence_a: float = 0.7
    confidence_b: float = 0.7
    resolution: Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_by: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None

class PromotionRecord(BaseModel):
    id: str
    memory_id: str
    from_scope: str
    to_scope: str
    requested_by: str
    approved_by: Optional[str] = None
    status: str = "PENDING"
    reason: Optional[str] = None
    created_at: str
    decided_at: Optional[str] = None

class ConsolidationReport(BaseModel):
    duplicates_found: int = 0
    merged: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0
    promotions_pending: int = 0
    details: List[str] = Field(default_factory=list)
