import os
import tempfile
import uuid
import pytest

os.environ['HMRA_DB_PATH'] = os.path.join(tempfile.gettempdir(), f'hmra_test_doc_{uuid.uuid4().hex}.sqlite')

from backend.app.db import init_db
from backend.app.memory.store import MemoryManager
from backend.app.tools.documents import (
    extract_text_from_file,
    chunk_text,
    process_and_ingest_document
)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_extract_and_chunk_txt():
    content = b"This is a sample document for testing text ingestion in HMRA."
    text, ext = extract_text_from_file("sample.txt", content)
    assert ext == "txt"
    assert "sample document" in text

    chunks = chunk_text(text)
    assert len(chunks) >= 1

def test_extract_csv():
    csv_bytes = b"name,role,department\nAlice,Researcher,AI Lab\nBob,Engineer,Core\n"
    text, ext = extract_text_from_file("team.csv", csv_bytes)
    assert ext == "csv"
    assert "Alice" in text
    assert "Researcher" in text

def test_extract_json():
    json_bytes = b'{"architecture": "HMRA", "levels": 3, "agents": 5}'
    text, ext = extract_text_from_file("config.json", json_bytes)
    assert ext == "json"
    assert "levels" in text

def test_full_document_ingestion_pipeline():
    mgr = MemoryManager()
    sample_text = b"HMRA integrates 3 memory scopes: GLOBAL, TEAM, and PRIVATE. Each scope enforces strict isolation."
    res = process_and_ingest_document(
        filename="architecture_spec.md",
        data=sample_text,
        scope="TEAM",
        owner_agent="system",
        memory_mgr=mgr
    )

    assert res['filename'] == "architecture_spec.md"
    assert res['chunks_created'] >= 1
    assert res['scope'] == "TEAM"

    # Immediately retrievable from memory
    retrieved = mgr.retrieve("HMRA integrates 3 memory scopes", requester="researcher")
    assert len(retrieved) >= 1
    assert "architecture_spec.md" in retrieved[0]['metadata'].get('filename', '')
