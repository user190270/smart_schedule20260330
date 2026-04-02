# API Contract (R18 Terminal)

## Scope

- This file is the terminal boundary for the Parse referential-update round.
- Existing Parse routes stay in force.
- Existing RAG, sync, CRUD, share, auth, and admin contracts remain in force and were not changed in this round.

## Parse Contract Preserved

- `POST /api/parse/schedule-draft`
  - still returns `draft`, `missing_fields`, `follow_up_questions`, `requires_human_review`, and `can_persist_directly`
- `POST /api/parse/schedule-draft/stream`
  - keeps the existing SSE behavior
- `POST /api/parse/sessions`
- `POST /api/parse/sessions/{session_id}/messages`
- `PATCH /api/parse/sessions/{session_id}/draft`
  - still returns `parse_session_id`, `messages`, `draft`, `missing_fields`, `follow_up_questions`, `ready_for_confirm`, `next_action`, `tool_calls`, `latest_assistant_message`, and `draft_visible`

Mandatory Parse guarantees preserved:

- Parse remains draft-first.
- AI-parsed schedules still require explicit user confirmation before persistence.
- Session-based clarification remains real backend-owned workflow state.
- The existing frontend Parse page still renders chat messages, draft state, and confirmation flow without a contract-breaking rewrite.
- Simple one-shot Parse behavior still works alongside the stronger multi-turn session semantics.

## Behavioral Improvement Closed In This Round

- Multi-turn follow-up instructions now distinguish more intentionally between:
  - adding a missing field
  - replacing an existing field
  - keeping an existing field unchanged
  - clearing a previously filled field
- Referential follow-up handling is now stronger for cases like:
  - keep the previous time and change only location
  - keep title and location while replacing time
  - clear end time without touching other fields
  - preserve an earlier referenced location while explicitly overriding title
- Unrelated fields are preserved by default unless the latest message clearly replaces or clears them.

## Internal Implementation Boundary

- Parse now uses a field-level internal update plan with `keep`, `set`, and `clear` semantics.
- Parse model payloads now carry structured prior-turn context during session follow-ups.
- These changes are internal only; no externally visible Parse payload break was required.

## Terminal Verification Snapshot

- `docker compose exec api pytest tests/test_parse_contract.py -q` passed with `14 passed`.
- `docker compose exec api pytest tests/test_ai_langchain_integration.py -q` passed with `4 passed`.
- `docker compose exec api pytest tests -q` passed with `49 passed`.
- `python -m compileall server/app server/tests` passed locally.
- `docker compose exec frontend npm run build` passed.
