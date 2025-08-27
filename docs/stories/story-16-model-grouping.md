# Story 16: Model Grouping

## Context and Goals
Grouping is out-of-scope for the prototype. The list remains flat. Optionally sort by provider/name in the parent.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Flat list with optional sorting by provider/name implemented in parent before passing `options`.

## Implementation Plan
- In the parent, pre-sort `options` by `provider` then `name` (if desired).
- Pass flat `options` to `MultiSelect`.

## Testing Scenarios
- Ensure sorting does not affect selection ids or chip order unexpectedly.

## Definition of Done
- Flat list works; optional sort applied without regressions.
