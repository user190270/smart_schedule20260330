# Working Contract (R25 - RAG Context Rechunking And Local Time Grounding)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md`
5. `docs/decision_log.md` only if an older RAG tradeoff needs explanation

## Round Goal

Repair the current RAG answer quality collapse without broadening product scope:

1. Stop cutting schedule knowledge into semantically broken fixed-width fragments.
2. Stop grounding temporal reasoning on UTC-looking text that does not match the user's local-time view.
3. Stop sending duplicate fragmented schedule snippets straight into answer generation without schedule-level consolidation.
4. Preserve true streaming and lightweight multi-turn follow-up behavior from R20/R21.

## Scope

### In Scope
- `server/app/services/rag_service.py`
- `server/app/routers/rag.py` only if stream metadata needs the smallest supporting adjustment
- `server/app/schemas/rag.py` only if a minimal chunking-default adjustment is warranted
- RAG-related backend tests
- active round docs
- `docs/decision_log.md` only if the new RAG orchestration tradeoffs need to be made durable

### Out of Scope
- Parse service or Parse frontend work
- sync / Pull reconciliation
- auth, admin, share
- RAG frontend redesign beyond the smallest verification aid
- `skills/`, `prompts/`, `media/`
- cloud deployment
- replacing the LLM provider or broad model experimentation

## Constraints

- R20 true streaming (`meta / token / done`) must remain intact.
- R21 lightweight multi-turn behavior must remain intact.
- Single-turn RAG must not regress.
- User isolation by `user_id` must not regress.
- This round should remain primarily backend-focused.
- Local verification may temporarily point the frontend to local API, but defaults must be restored before round end.

## RAG Repair Strategy

- Replace raw fixed-width character chunking with schedule-aware chunking that keeps one schedule's factual context semantically coherent.
- Rebuild indexed schedule text around user-facing local-time facts instead of raw UTC-looking timestamps.
- Before answer generation, merge retrieved chunk hits into schedule-level candidates so the model sees deduplicated schedule facts rather than repeated fragments.
- Strengthen the answer-generation prompt so time-comparison questions (`earliest`, `latest`, `what date`, `what time`) are answered by comparing the supplied structured candidates instead of free-form extrapolation.

## Verification Strategy

- Prove that rebuild results no longer explode a small schedule set into many arbitrary fragments under normal chunk-size settings.
- Prove that indexed content includes local-time-oriented date/time text.
- Prove that answer-generation payloads are grouped at the schedule level before being sent to the runtime.
- Re-run targeted RAG tests plus broad backend regression and frontend build verification.
