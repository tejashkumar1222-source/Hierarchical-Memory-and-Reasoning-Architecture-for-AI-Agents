import json
import time
import re
import urllib.request
import urllib.error
from .config import LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, LLM_BASE_URL, LLM_TIMEOUT, LLM_TEMPERATURE, ALLOW_OFFLINE_FALLBACK

class LLMError(RuntimeError):
    pass

class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.model = LLM_MODEL

    @property
    def configured(self):
        return bool(LLM_API_KEY)

    def chat(self, messages, temperature=None):
        if not self.configured:
            if ALLOW_OFFLINE_FALLBACK:
                return self._offline(messages)
            raise LLMError('LLM_API_KEY is not configured. Add it to .env and restart the server.')
        if self.provider not in {'gemini', 'openai', 'openai_compatible', 'groq'}:
            raise LLMError(f'Unsupported LLM_PROVIDER: {self.provider}')

        url = LLM_BASE_URL.rstrip('/') + '/chat/completions'
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': LLM_TEMPERATURE if temperature is None else temperature,
        }

        # Handle rate limits with adaptive backoff
        max_attempts = 4
        for attempt in range(max_attempts):
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {LLM_API_KEY}',
                    'User-Agent': 'HMRA-Agent/1.0'
                },
                method='POST'
            )
            try:
                with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
                    data = json.loads(r.read().decode('utf-8'))
                    return data['choices'][0]['message']['content'].strip()
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='ignore')
                if e.code == 429 and attempt < max_attempts - 1:
                    wait_s = 2.0 * (attempt + 1)
                    # Parse millisecond or second duration: e.g. "try again in 802.5ms" or "try again in 5.2s"
                    m = re.search(r'try again in\s+(\d+(?:\.\d+)?)\s*(ms|s)?', body, re.IGNORECASE)
                    if m:
                        val = float(m.group(1))
                        unit = (m.group(2) or 's').lower()
                        if unit == 'ms':
                            wait_s = (val / 1000.0) + 0.6
                        else:
                            wait_s = val + 0.6
                    wait_s = min(max(wait_s, 1.0), 15.0)
                    time.sleep(wait_s)
                    continue
                raise LLMError(f'LLM HTTP {e.code}: {body[:600]}') from e
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(1.5)
                    continue
                raise LLMError(f'LLM request failed: {e}') from e

    def _offline(self, messages):
        user = messages[-1]['content'] if messages else ''
        return 'Offline fallback is enabled. The configured LLM was not called. Query received: ' + user[:500]
