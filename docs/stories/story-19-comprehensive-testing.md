# Story 19: Comprehensive Testing

## Context and Goals
For the prototype, keep testing lightweight: a small set of unit tests and a manual QA checklist. No e2e, performance budgets, or CI gates.

- Source: This doc. Component under test: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Unit tests cover:
  - Renders with label and options
  - Filters options by name/provider when typing
  - Toggles selection and calls `onChange`
  - Displays chips and removes a chip on X click
- [ ] Manual QA checklist documented below.

## Implementation Plan
- Framework: Vitest + React Testing Library.
- Keep tests colocated near the component or in `src/__tests__/`.

## Testing Scenarios
- Manual QA Checklist:
  - Open dropdown, search, select multiple, remove chips
  - Close via outside click and Escape
  - Mobile: ensure tap targets are usable; list scrolls

## Definition of Done
- Basic unit tests pass locally and manual QA checklist is satisfied.
