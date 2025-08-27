# Story 6: Advanced Model Information

## Context and Goals
For the prototype, keep each option minimal. Show only model name and provider in the list. No expand/collapse or deep details.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Option displays `name` and a small `provider` subtitle.
- [ ] No expandable sections, links, or badges.

## Implementation Plan
- Use existing rendering in `MultiSelect` option rows.

## Data Contracts
- `AIModel` with `id`, `name`, `provider` only.

## UX States
- Clean, simple list; no expand/collapse.

## Prototype Notes
- Defer rich details to future work.

## Definition of Done
- List shows name + provider only, with no console warnings.
