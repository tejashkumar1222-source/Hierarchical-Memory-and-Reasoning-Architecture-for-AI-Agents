import pytest
from backend.app.tools.registry import GLOBAL_TOOL_REGISTRY
from backend.app.tools.calculator import safe_calculate
from backend.app.tools.current_time import get_current_time
from backend.app.tools.web_search import BraveSearchProvider, is_safe_external_url

def test_calculator_tool():
    assert safe_calculate("2 + 2") == 4.0
    assert safe_calculate("10 / 2 + 5 * 3") == 20.0
    with pytest.raises(ValueError):
        safe_calculate("10 / 0")

def test_current_time_tool():
    res = get_current_time()
    assert 'utc_iso' in res
    assert 'local_iso' in res

def test_web_search_fallback_when_unconfigured():
    provider = BraveSearchProvider(api_key="")
    res = provider.search("HMRA agent architecture")
    assert res['configured'] is False
    assert "Web search is not configured" in res['message']
    assert res['results'] == []

def test_url_ssrf_safety_checks():
    assert not is_safe_external_url("http://localhost:8000/secret")
    assert not is_safe_external_url("http://127.0.0.1/admin")
    assert not is_safe_external_url("http://192.168.1.1/router")
    assert not is_safe_external_url("http://10.0.0.1/internal")
    assert not is_safe_external_url("ftp://example.com/file")
    assert is_safe_external_url("https://example.com/article")
    assert is_safe_external_url("https://en.wikipedia.org/wiki/Artificial_intelligence")

def test_global_tool_registry():
    tools = GLOBAL_TOOL_REGISTRY.list_tools()
    tool_names = [t['name'] for t in tools]
    assert 'calculator' in tool_names
    assert 'current_time' in tool_names
    assert 'web_search' in tool_names
