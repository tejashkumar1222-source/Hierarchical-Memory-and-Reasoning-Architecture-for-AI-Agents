"""
HMRA Tools Backward Compatibility Forwarder
"""

from .tools import (
    ToolRegistry,
    GLOBAL_TOOL_REGISTRY,
    execute,
    safe_calculate,
    get_current_time,
    BraveSearchProvider,
    fetch_web_page,
    is_safe_external_url,
    extract_text_from_file,
    chunk_text,
    process_and_ingest_document,
    tool_retrieve_memory,
    tool_write_memory,
    tool_consolidate_memory,
)

# Compatibility aliases
calculator = safe_calculate
current_time = lambda: get_current_time()['utc_iso']
fetch_url = lambda url: fetch_web_page(url).get('content', '')

__all__ = [
    'ToolRegistry',
    'GLOBAL_TOOL_REGISTRY',
    'execute',
    'safe_calculate',
    'get_current_time',
    'BraveSearchProvider',
    'fetch_web_page',
    'is_safe_external_url',
    'extract_text_from_file',
    'chunk_text',
    'process_and_ingest_document',
    'tool_retrieve_memory',
    'tool_write_memory',
    'tool_consolidate_memory',
    'calculator',
    'current_time',
    'fetch_url',
]
