# HMRA Memory Write-Back Fix

This patch makes long-term memory selective and review-gated.

## New behavior
- Temporary errors, rate-limit messages, calculations, greetings, and unresolved "I don't know" responses are not stored as durable memory.
- Durable project/research knowledge is stored as a compact `Topic` + `Durable knowledge` record.
- New conversation-derived memories start in `PRIVATE` and `PENDING_REVIEW`.
- Automatic PRIVATE -> TEAM promotion has been removed.
- A formal promotion request is created for eligible candidates; a reviewer must approve it.
- Approved promotion activates the memory in its new scope.
- Legacy transient/error memories in the bundled demo database were marked `DEPRECATED` rather than deleted.
- Legacy auto-promoted conversation memories were moved to `PENDING_REVIEW`.
- Frontend LLM status mapping was fixed to read the nested `/api/status` response.

## Why
A transcript, tool result, error, or trace is evidence of what happened, not automatically durable knowledge. Long-term memory should be selective and governed before it affects future runs. This is consistent with current agent-memory guidance emphasizing explicit extraction/write gates and keeping most trace data out of durable memory. 
