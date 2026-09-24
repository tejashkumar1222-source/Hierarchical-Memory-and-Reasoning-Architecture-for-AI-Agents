"""
HMRA Current Time Tool
"""

from datetime import datetime, timezone

def get_current_time() -> dict:
    """Returns ISO and human-readable UTC and local time."""
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now().astimezone()
    return {
        "utc_iso": now_utc.isoformat(),
        "local_iso": now_local.isoformat(),
        "readable": now_local.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
    }
