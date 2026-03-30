# AI Workflow Patterns (Execution Snapshot)

## Purpose

This file summarizes reusable patterns extracted from the end-to-end execution of this repository.

## Pattern 1: Docs-As-Interface Loop

- Pattern:
  - Use `working_contract -> current_state -> task_board` as the default handoff interface.
  - Advance exactly one `current_step` at a time.
- Evidence:
  - `docs/working_contract.md`
  - `docs/current_state.md`
  - `docs/task_board.md`

## Pattern 2: Contract-First Feature Delivery

- Pattern:
  - Define or update API contracts before or together with implementation.
  - Keep data boundary rules explicit (`user_id` filtering, human review gates, share DTO desensitization).
- Evidence:
  - `docs/api_contract.md`
  - `docs/decision_log.md`

## Pattern 3: Service-Layer Control

- Pattern:
  - Keep routers thin; enforce behavior in services.
  - Use services to centralize critical constraints (LWW merge, parse gate, RAG filtering, share rules).
- Evidence:
  - `server/app/routers/`
  - `server/app/services/`

## Pattern 4: Deterministic Gate Checks

- Pattern:
  - Run deterministic scripts and tests as step gates.
  - Use import and docs consistency checks to avoid silent drift.
- Evidence:
  - `skills/coding-agent-loop/scripts/docs_consistency_check.py`
  - `skills/coding-agent-loop/scripts/import_guard.py`
  - `server/tests/`

## Pattern 5: Human-In-The-Loop by Contract

- Pattern:
  - AI parse output is always draft-first.
  - Persistence requires explicit confirmation.
  - Missing fields are resolved by SSE follow-up protocol.
- Evidence:
  - `server/app/routers/parse.py`
  - `server/app/services/parse_service.py`
  - `server/app/services/schedule_service.py`

## Pattern 6: Cross-Platform Adapter Strategy

- Pattern:
  - Prefer native adapter when available; fallback for web without breaking feature flow.
  - Keep business modules independent from platform-specific APIs.
- Evidence:
  - `frontend/src/services/local-store.ts`
  - `frontend/src/services/notification.ts`
  - `docs/client_capacitor_plan.md`

