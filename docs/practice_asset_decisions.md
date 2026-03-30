# Practice Asset Decisions

## Goal

Decide which execution patterns should be promoted to reusable prompt assets, skill assets, or kept as project-level docs.

## Decisions

### A1: Keep as Skill-Level Workflow

- Asset target: `coding-agent-loop` skill
- Why:
  - Requires explicit state transitions (`PLAN/EXECUTE/REVIEW/REWORK/REPLAN`)
  - Depends on deterministic routing and contract fields
- Source patterns:
  - Docs-as-interface loop
  - Deterministic gate checks

### A2: Keep as Prompt-Level Reviewer/Executor Contracts

- Asset target:
  - `prompts/coding_executor_single_step.md`
  - `prompts/coding_reviewer_single_step.md`
- Why:
  - Strong single-step boundary and review output schema
  - Works as reusable guardrails across repos
- Source patterns:
  - Service-layer control checks
  - Reject routing logic

### A3: Keep as Repo-Level Domain Contract

- Asset target:
  - `docs/api_contract.md`
  - `docs/decision_log.md`
- Why:
  - Contains project-specific architecture constraints
  - Not all rules are portable across products
- Source patterns:
  - Human-in-the-loop persistence gate
  - Multi-tenant `user_id` isolation
  - Share DTO desensitization rules

### A4: Keep as Cross-Platform Frontend Adapter Template

- Asset target:
  - `frontend/src/services/local-store.ts`
  - `frontend/src/services/notification.ts`
- Why:
  - Adapter design is reusable in AI app clients with Web/Capacitor dual target
- Source patterns:
  - Capacitor-first, Web-fallback runtime design

## Deferred Items

- Convert adapter pattern into a standalone skill template:
  - deferred until real SQLite/IndexedDB implementation is added.
- Convert RAG placeholder embedding flow into a skill:
  - deferred until real embedding provider and evaluator are integrated.

