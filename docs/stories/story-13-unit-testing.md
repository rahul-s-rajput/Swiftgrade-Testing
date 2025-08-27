# Story 13: Unit Testing

## Context and Goals
Add a minimal set of unit tests for the `MultiSelect` to ensure core prototype behaviors are stable.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Renders with label and a list of options.
- [ ] Filters options by name/provider as user types.
- [ ] Toggles selection and calls `onChange` with updated ids.
- [ ] Displays selected chips and removes on X click.

## Implementation Plan
- __Setup__: Vitest + React Testing Library.
- __Tests__ (examples):
  - Render component with two options; expect labels present.
  - Type in search; expect filtering.
  - Click an option; expect `onChange` called with that id.
  - Click chip X; expect `onChange` called without that id.
- Keep tests colocated near the component or in `src/__tests__/MultiSelect.test.tsx`.

## Testing Scenarios
- Basic behaviors only; no API, caching, or advanced keyboard.

## Definition of Done
- Tests run locally and pass; no console errors during test run.
