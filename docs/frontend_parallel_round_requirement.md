# Frontend Parallel Optimization Round Requirement

## Purpose

Launch a new frontend-only optimization round on top of the current `agent-a` MVP baseline.

This round exists to let two agents explore UI/UX improvements in parallel while preserving backend stability and API compatibility.

## How To Start

- Use the local skill: `skills/coding-agent-loop`
- This round must start from `PLAN`
- Existing `docs/current_state.md` and `docs/task_board.md` are historical anchors for the completed MVP loop, not the active state for this new round
- The planner must rebuild new active docs for this frontend optimization round before any execute step begins

## Top-Level Goal

Improve the frontend experience of Smart Schedule MVP without breaking the already working backend, authentication flow, provider integration, or route contract.

## Scope

Allowed primary touchpoints:

- `frontend/src/App.vue`
- `frontend/src/main.ts`
- `frontend/src/style.css`
- `frontend/src/views/`
- `frontend/src/components/` if needed
- `frontend/src/stores/` only if needed for frontend UX refinement
- `frontend/src/api/` only for compatibility-preserving cleanup
- `docs/current_state.md`
- `docs/task_board.md`
- `docs/decision_log.md` if a meaningful frontend decision must be recorded

## Hard Constraints

- Do not modify `server/`
- Do not modify `docker-compose.yml`
- Do not modify `prompts/`
- Do not modify `media/`
- Do not modify `skills/`
- Do not change backend API paths, auth contract, or request/response payload shapes
- Do not add new backend features
- Do not bypass existing auth flow
- Do not remove working route navigation
- Do not replace Chinese-first UI direction with English-first UI

## Freedom Allowed

The frontend agent may freely improve:

- visual hierarchy
- typography
- spacing rhythm
- color system
- page layout
- card and surface design
- empty/loading/error states
- motion and transition polish
- information architecture inside existing pages
- Chinese copywriting clarity and product feel

As long as backend compatibility remains intact, frontend expression may be bold.

## Desired Outcome

The app should feel like a deliberate mobile-first AI product rather than a scaffolded admin shell.

At the end of this round, the frontend should:

- look visually coherent across `/`, `/schedules`, `/parse`, `/rag`, `/share`
- preserve the current route map
- preserve working health/auth/API flows
- remain buildable
- remain demo-friendly

## Suggested Phase Layout

- `P12` Frontend planning and design baseline
- `P13` Home + navigation polish
- `P14` Schedule experience polish
- `P15` Parse / RAG / Share experience polish
- `P16` Frontend hardening and consistency sweep

The planner may rename these phases, but it must keep the sequence clear and execution-ready.

## Verification Expectations

At minimum, each successful round should preserve:

- `npm run build` passing
- all five frontend routes opening
- home health check still reaching backend
- no breaking change to auth-bearing requests
- no API contract drift introduced by frontend edits

## Parallel Comparison Intent

This round is intended for parallel experimentation across multiple agents.

Therefore:

- preserve a clean plan
- keep docs honest
- do not mark work complete unless it is verified
- prefer reversible UI improvements over risky architectural churn
