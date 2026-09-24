import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')

DATA_DIR = ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = os.getenv('HMRA_DB_PATH', str(DATA_DIR / 'hmra.db'))
UPLOAD_DIR = Path(os.getenv('HMRA_UPLOAD_DIR', str(DATA_DIR / 'uploads')))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq').lower()
LLM_MODEL = os.getenv('LLM_MODEL', 'openai/gpt-oss-20b')
LLM_API_KEY = os.getenv('LLM_API_KEY', '').strip()
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.groq.com/openai/v1').rstrip('/') + '/'
LLM_TIMEOUT = float(os.getenv('LLM_TIMEOUT', '60'))
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.2'))
ALLOW_OFFLINE_FALLBACK = os.getenv('ALLOW_OFFLINE_FALLBACK', 'false').lower() == 'true'

# Web Search Configuration
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY', '').strip()

# Context budget
TOP_K = int(os.getenv('TOP_K', '6'))
MAX_CONTEXT_CHARS = int(os.getenv('MAX_CONTEXT_CHARS', '12000'))

# 8-Signal Configurable Retrieval Weights
# Defaults adhere to HMRA research specifications:
# semantic=0.30, lexical=0.10, recency=0.10, importance=0.15, confidence=0.15, frequency=0.05, scope=0.10, source_quality=0.05
RETRIEVAL_WEIGHTS = {
    'semantic': float(os.getenv('W_SEMANTIC', '0.30')),
    'lexical': float(os.getenv('W_LEXICAL', '0.10')),
    'recency': float(os.getenv('W_RECENCY', '0.10')),
    'importance': float(os.getenv('W_IMPORTANCE', '0.15')),
    'confidence': float(os.getenv('W_CONFIDENCE', '0.15')),
    'frequency': float(os.getenv('W_FREQUENCY', '0.05')),
    'scope': float(os.getenv('W_SCOPE', '0.10')),
    'source_quality': float(os.getenv('W_SOURCE_QUALITY', '0.05')),
}
