# API Contract (R19 Terminal)

## Scope

- This file is the terminal Parse contract boundary for the follow-up-context round.
- Existing Parse routes stay in force.
- Existing RAG, sync, CRUD, share, auth, and admin contracts remain in force and are out of scope.

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
- Existing field-level `keep / set / clear` semantics remain in force.

## Internal Improvement Closed In This Round

- Parse session runtime payloads now carry stronger follow-up cues during session turns, including:
  - recent dialogue window
  - latest assistant follow-up message
  - current `missing_fields`
  - current `follow_up_questions`
  - pending follow-up field list
  - a single `active_follow_up_field` when one slot is clearly pending
  - a `follow_up_reply_expected` signal when the latest reply is likely answering a pending clarification
- These additions remain internal only; no externally visible Parse payload break was required.
- A narrow internal guardrail was added for pending clarification slots:
  - when the runtime keeps a field that is still actively pending
  - and the existing fallback path extracts a concrete action for that same pending field
  - the fallback action is used for that pending field rather than being discarded

## Behavioral Goal Closed In This Round

- Given:
  - first turn `明天到A-201开会`
  - assistant follow-up asking for start time
  - second turn `早上九点开始`
- Parse now has a materially stronger path to interpret the second turn as a `start_time` completion rather than as an isolated fragment that leaves `start_time` missing.

## Non-Goals Preserved

- No large-scale expansion of heuristic time rules.
- No conversion of Parse into a general chatbot.
- No broad frontend redesign.
- No RAG or sync contract changes.

## Terminal Verification Snapshot

- `docker compose exec api pytest tests/test_parse_contract.py -q` passed with `14 passed`.
- `docker compose exec api pytest tests/test_ai_langchain_integration.py -q` passed with `4 passed`.
- `docker compose exec api pytest tests -q` passed with `49 passed`.
- `python -m compileall server/app server/tests` passed locally.
- `docker compose exec frontend npm run build` passed.
