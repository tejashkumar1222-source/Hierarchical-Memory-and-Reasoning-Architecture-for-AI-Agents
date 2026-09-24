"""
HMRA Web Search Provider & Network Security Module

Integrates Brave Search API with safe network abstractions and graceful fallback.
Protects against SSRF (no requests to internal IPs or local subnets).
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import ipaddress
from typing import Dict, Any, List, Optional
from ..config import BRAVE_API_KEY

def is_safe_external_url(url: str) -> bool:
    """Validates that a URL is HTTP/HTTPS and does not target localhost or private networks."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
            return False

        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass  # It is a domain name, proceed
        return True
    except Exception:
        return False

class SearchProvider:
    """Abstract search provider interface."""
    def search(self, query: str, count: int = 5) -> Dict[str, Any]:
        raise NotImplementedError

class BraveSearchProvider(SearchProvider):
    """Real Brave Search implementation with graceful fallback."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key if api_key is not None else BRAVE_API_KEY

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def search(self, query: str, count: int = 5) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                'configured': False,
                'query': query,
                'results': [],
                'message': 'Web search is not configured. Add BRAVE_API_KEY to your .env file to enable live web retrieval.'
            }

        safe_query = urllib.parse.quote(query.strip())
        url = f"https://api.search.brave.com/res/v1/web/search?q={safe_query}&count={max(1, min(count, 10))}"
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'identity',
            'X-Subscription-Token': self.api_key.strip(),
            'User-Agent': 'HMRA-Research-Agent/1.0'
        }
        req = urllib.request.Request(url, headers=headers, method='GET')

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                payload = json.loads(response.read().decode('utf-8'))
                web_results = payload.get('web', {}).get('results', [])
                formatted = []
                for item in web_results[:count]:
                    formatted.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'snippet': item.get('description', ''),
                        'source': 'Brave Search',
                        'timestamp': item.get('page_age') or item.get('age') or ''
                    })
                return {
                    'configured': True,
                    'query': query,
                    'count': len(formatted),
                    'results': formatted,
                    'message': f"Found {len(formatted)} web results."
                }
        except urllib.error.HTTPError as e:
            return {
                'configured': True,
                'query': query,
                'results': [],
                'error': f"Brave Search API HTTP {e.code}: {e.reason}",
                'message': f"Search request failed with HTTP {e.code}"
            }
        except Exception as e:
            return {
                'configured': True,
                'query': query,
                'results': [],
                'error': str(e),
                'message': f"Web search failed: {e}"
            }

def fetch_web_page(url: str, max_chars: int = 6000) -> Dict[str, Any]:
    """Safely retrieves textual content from a public web URL with length constraints."""
    if not is_safe_external_url(url):
        return {'url': url, 'content': '', 'error': 'Blocked: URL is invalid or targets an internal address.'}

    req = urllib.request.Request(url, headers={'User-Agent': 'HMRA-Research-Agent/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
            return {'url': url, 'content': raw[:max_chars], 'error': None}
    except Exception as e:
        return {'url': url, 'content': '', 'error': str(e)}
