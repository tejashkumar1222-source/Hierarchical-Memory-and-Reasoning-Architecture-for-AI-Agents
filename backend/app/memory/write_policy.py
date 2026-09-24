"""Selective durable-memory write policy for HMRA.

The conversation transcript and execution trace are history. Only a small,
durable subset should become long-term memory. This module provides a
conservative application-level gate before anything is persisted as memory.
"""

import re
from typing import Tuple

# Temporary/error signals that should never become durable project memory.
TRANSIENT_PATTERNS = [
    r"\brate[- ]limit(?:ed|ing)?\b",
    r"\btoo many requests\b",
    r"\bhttp\s*(?:4\d\d|5\d\d)\b",
    r"\berror during (?:execution|analysis|research)\b",
    r"\b(?:i|we) (?:was|were|am|are) unable to\b",
    r"\b(?:i|we) (?:couldn't|could not|cannot|can't) (?:find|locate|retrieve|access)\b",
    r"\b(?:not|isn't|is not) available\b",
    r"\bweb[- ]search.*(?:disabled|unavailable)\b",
    r"\bllm (?:http|request) failed\b",
    r"\boffline fallback\b",
    r"\btry again later\b",
    r"\btemporar(?:y|ily)\b",
]

# Short-lived conversational/task outputs that are better kept in the trace.
TRANSIENT_QUERY_PATTERNS = [
    r"^(?:hi|hello|hey|thanks|thank you)\b",
    r"\bcalculate\b",
    r"\bcompute\b",
    r"\bwhat is\s+[-+*/().\d\s]+[?]?$",
    r"\bwhat's the (?:time|date)\b",
    r"\bcurrent (?:time|date)\b",
]

# Durable-intent signals. These are intentionally broad because HMRA is a
# project/research assistant, but they are only considered after the transient
# checks above.
DURABLE_INTENT_PATTERNS = [
    r"\bremember\b",
    r"\bkeep in mind\b",
    r"\bproject\b",
    r"\barchitecture\b",
    r"\bmilestone\b",
    r"\bdecision\b",
    r"\bapproved\b",
    r"\bconfiguration\b",
    r"\bwe use\b",
    r"\buse \w+ for\b",
    r"\brequirement\b",
    r"\bpolicy\b",
    r"\bworkflow\b",
    r"\bprocedure\b",
    r"\bsetup\b",
    r"\bimplementation\b",
    r"\bresearch finding\b",
    r"\bsource says\b",
]


def _matches(patterns, text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE | re.DOTALL) for p in patterns)


def assess_durability(query: str, answer: str) -> Tuple[bool, str]:
    """Return (should_store, reason) using conservative deterministic gates."""
    q = (query or "").strip()
    a = (answer or "").strip()
    combined = f"{q}\n{a}"

    if len(a) < 50:
        return False, "answer_too_short"

    if _matches(TRANSIENT_PATTERNS, a):
        return False, "transient_or_error_output"

    if _matches(TRANSIENT_QUERY_PATTERNS, q):
        return False, "transient_query"

    # Do not persist agent error wrappers even if the query itself sounds durable.
    if re.search(r"\[(?:researcher|coder|reviewer|critic|synthesizer)\]\s+error", a, re.I):
        return False, "agent_error_output"

    # Purely uncertain answers should remain in the execution/conflict layer.
    uncertainty = re.search(
        r"\b(?:no definitive|insufficient evidence|cannot determine|unable to determine|not enough evidence)\b",
        a,
        re.IGNORECASE,
    )
    if uncertainty:
        return False, "unresolved_uncertainty"

    if _matches(DURABLE_INTENT_PATTERNS, combined):
        return True, "durable_intent"

    # Conservative default: don't turn arbitrary answers into long-term memory.
    return False, "no_durable_intent"


def build_memory_content(query: str, answer: str, max_chars: int = 900) -> str:
    """Create a compact durable record instead of storing the whole transcript."""
    q = re.sub(r"\s+", " ", (query or "").strip())
    a = re.sub(r"\s+", " ", (answer or "").strip())
    content = f"Topic: {q}\nDurable knowledge: {a}"
    return content[:max_chars]
