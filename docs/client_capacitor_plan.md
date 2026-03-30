# Client Capacitor Plan

## Scope

- Local storage abstraction for schedule drafts and sync metadata.
- Local notifications abstraction for reminder scheduling.

## Current Baseline

- `frontend/src/services/local-store.ts`
  - Prefer `@capacitor/preferences` when available.
  - Fallback to browser `localStorage` with `smart-schedule:` prefix.
- `frontend/src/services/notification.ts`
  - Prefer `@capacitor/local-notifications` when available.
  - Fallback to web logging mode for non-native environments.

## Integration Path

1. Keep domain modules calling only service abstractions.
2. For Web:
   - Use fallback adapter behavior by default.
3. For Capacitor:
   - Keep same service API, rely on runtime plugin availability.

## Next Implementation Hooks

- Use local storage abstraction for:
  - offline `Schedule` drafts
  - `last_sync_time`
  - parse draft cache
- Use notification abstraction for:
  - schedule start reminders
  - user-configurable lead-time reminders

