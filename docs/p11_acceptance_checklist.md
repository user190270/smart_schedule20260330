# P11 Acceptance Checklist (R2)

## Scope

- Project: `Smart Schedule MVP`
- Round: `R2-2026-03-23`
- Goal: reproducible Docker-first MVP verification for demo handoff.

## Prerequisites

- Docker Desktop running.
- Workspace: `C:\Users\nor\Documents\project\study\unit22-agent-a`
- Optional real AI credentials for live provider path:
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
  - `LLM_CHAT_MODEL`
  - `LLM_EMBEDDING_MODEL`

## Core Startup

1. `docker compose up --build -d`
2. `docker compose ps`
3. `docker compose logs api --tail 120`
4. `docker compose logs frontend --tail 120`

Pass criteria:

- `api` and `frontend` are both `Up`.
- API log shows migration/bootstrap and uvicorn startup.
- Frontend log shows Vite dev server ready on `5173`.

## Backend Smoke (API)

- Run a script that validates:
  - `GET /api/health -> 200`
  - `POST /api/auth/register -> 201`
  - `GET /api/auth/me` with bearer token -> `200`
  - `POST /api/schedules -> 201`
  - `POST /api/parse/schedule-draft -> 200`
  - `POST /api/rag/chunks/rebuild/{schedule_id} -> 200`
  - `POST /api/rag/retrieve -> 200`
  - `POST /api/share/schedules/{schedule_id} -> 201`
  - `GET /api/share/{share_uuid} -> 200` and no `user_id` field
  - unauthenticated protected route -> `401`

Pass criteria:

- All listed status codes match.
- User isolation and share desensitization hold.

## Frontend Smoke (Route-Click)

- Open `http://localhost:5173`.
- Validate route navigation:
  - `/`
  - `/schedules`
  - `/parse`
  - `/rag`
  - `/share`
- Validate home health check button reaches backend successfully.

Pass criteria:

- All five routes load without fatal error.
- Home health check succeeds in browser context (CORS verified).

## Build/Test Gates

- Frontend build:
  - `docker compose exec frontend npm run build`
- Backend tests:
  - `docker compose exec api python -m unittest discover -s tests -p "test_*.py"`

Pass criteria:

- Frontend build succeeds.
- Backend tests pass.

## Observed Results (2026-03-23)

- Docker startup: pass.
- API smoke: pass.
- Frontend route-click smoke: pass.
- Frontend build: pass.
- Backend unit tests: pass (`27` tests).

## Residual Risks

- Live provider success path requires real `LLM_*` credentials to validate non-fallback behavior end-to-end.
- Playwright input actions were intermittently cancelled by MCP permission gate; click-path evidence is stronger than full form-entry automation evidence.
