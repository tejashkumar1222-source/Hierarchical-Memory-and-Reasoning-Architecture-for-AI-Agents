"""
HMRA Document Ingestion & Text Processing Module

Extracts, structures, and chunks content from TXT, MD, CSV, JSON, and PDF files.
Persists metadata into documents and document_chunks tables, and outputs
memory records ready for immediate hierarchical retrieval.
"""

import os
import csv
import json
import uuid
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

from ..db import connect
from ..config import UPLOAD_DIR
from ..memory.store import MemoryManager

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def extract_text_from_file(filename: str, data: bytes) -> Tuple[str, str]:
    """
    Safely extracts human-readable text from binary data based on file extension.
    Returns (extracted_text, file_type).
    """
    ext = Path(filename).suffix.lower()

    if ext in ('.txt', '.md'):
        text = data.decode('utf-8', errors='ignore')
        return text, ext.lstrip('.')

    elif ext == '.json':
        try:
            parsed = json.loads(data.decode('utf-8', errors='ignore'))
            formatted = json.dumps(parsed, indent=2)
            return formatted, 'json'
        except Exception as e:
            raise ValueError(f"Invalid JSON file: {e}")

    elif ext == '.csv':
        try:
            text_stream = io.StringIO(data.decode('utf-8', errors='ignore'))
            reader = csv.DictReader(text_stream)
            rows_text = []
            headers = reader.fieldnames or []
            for idx, row in enumerate(reader, start=1):
                items = [f"{k}: {v}" for k, v in row.items() if v]
                rows_text.append(f"Row {idx} -> " + ", ".join(items))
            full_text = f"CSV Document: {filename}\nHeaders: {', '.join(headers)}\n\n" + "\n".join(rows_text)
            return full_text, 'csv'
        except Exception as e:
            raise ValueError(f"Invalid CSV file: {e}")

    elif ext == '.pdf':
        try:
            from pypdf import PdfReader
            pdf_file = io.BytesIO(data)
            reader = PdfReader(pdf_file)
            page_texts = []
            for page_idx, page in enumerate(reader.pages, start=1):
                t = page.extract_text() or ''
                if t.strip():
                    page_texts.append(f"--- Page {page_idx} ---\n{t.strip()}")
            full_text = "\n\n".join(page_texts)
            if not full_text.strip():
                raise ValueError("No text could be extracted from PDF (file may be scanned/image-only).")
            return full_text, 'pdf'
        except Exception as e:
            raise ValueError(f"Could not parse PDF: {e}")

    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .txt, .md, .csv, .json, .pdf")

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """Splits continuous text into overlapping chunks, preferring paragraph/sentence breaks."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Attempt to break on paragraph or sentence boundary
        split_point = text.rfind('\n\n', start + overlap, end)
        if split_point == -1:
            split_point = text.rfind('\n', start + overlap, end)
        if split_point == -1:
            split_point = text.rfind('. ', start + overlap, end)

        if split_point != -1 and split_point > start:
            chunks.append(text[start:split_point + 1].strip())
            start = split_point + 1
        else:
            chunks.append(text[start:end].strip())
            start = end - overlap

    return [c for c in chunks if c]

def process_and_ingest_document(
    filename: str,
    data: bytes,
    scope: str = "TEAM",
    owner_agent: str = "system",
    team_id: str = "default",
    memory_mgr: MemoryManager = None
) -> Dict[str, Any]:
    """
    Processes uploaded document, saves file locally, creates DB records,
    chunks content, and adds memory records with source provenance.
    """
    if memory_mgr is None:
        memory_mgr = MemoryManager()

    # 1. Extract text
    text, file_type = extract_text_from_file(filename, data)

    # 2. Save physical file in upload dir
    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    safe_name = f"{doc_id}_{Path(filename).name}"
    save_path = UPLOAD_DIR / safe_name
    save_path.write_bytes(data)

    # 3. Chunk text
    chunks = chunk_text(text)
    if not chunks:
        chunks = [text[:1200]]

    t = now_iso()

    # 4. Insert into documents table
    with connect() as c:
        c.execute(
            '''INSERT INTO documents(id, filename, file_type, size_bytes, chunk_count, scope, owner_agent, created_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?)''',
            (doc_id, filename, file_type, len(data), len(chunks), scope.upper(), owner_agent, t)
        )

    # 5. Create memory records (outside the documents connect block to prevent nested lock)
    created_memories = []
    for idx, ch in enumerate(chunks):
        mem = memory_mgr.add(
            content=ch,
            scope=scope.upper(),
            owner_agent=owner_agent,
            team_id=team_id,
            source=f"document:{filename}",
            confidence=0.85,
            importance=0.65,
            source_quality=0.90,
            metadata={
                'document_id': doc_id,
                'filename': filename,
                'file_type': file_type,
                'chunk_index': idx,
                'total_chunks': len(chunks),
                'upload_timestamp': t
            }
        )
        created_memories.append(mem)

    # 6. Record document chunks in a dedicated transaction
    with connect() as c:
        for idx, mem in enumerate(created_memories):
            chunk_id = f"chk_{uuid.uuid4().hex[:10]}"
            c.execute(
                '''INSERT INTO document_chunks(id, document_id, chunk_index, memory_id, created_at)
                   VALUES(?, ?, ?, ?, ?)''',
                (chunk_id, doc_id, idx, mem['id'], t)
            )

    return {
        'document_id': doc_id,
        'filename': filename,
        'file_type': file_type,
        'size_bytes': len(data),
        'chunks_created': len(created_memories),
        'scope': scope.upper(),
        'memories': created_memories,
        'message': f"Successfully ingested {filename} into {len(created_memories)} {scope.upper()} memory chunks."
    }
