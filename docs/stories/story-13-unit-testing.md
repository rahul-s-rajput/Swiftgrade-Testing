# Story 13: Unit Testing

## Context and Goals
Establish solid test coverage for hooks and key UI behaviors.

- Source: Technical Debt (Story 13), Implementation Plan (Testing Strategy).

## Acceptance Criteria
- [ ] 80% code coverage.
- [ ] Test all hooks.
- [ ] Test filtering logic.
- [ ] Test selection logic.
- [ ] Test API integration with mocks.
- [ ] Snapshot tests for UI.

## Implementation Plan
- __Setup__: Ensure testing libs configured (Vitest + React Testing Library).
- __Hook tests__: `useModelFetch`, `useModelFilter`, `useModelSelection`.
- __Component tests__: ModelCard, ModelFilters, SelectedModelsList, OpenRouterModelPicker shell.
- __Mocks__: Mock fetch for model list and localStorage for cache paths.

## Testing Scenarios
- Cache hit vs stale paths in `useModelFetch`.
- Complex filter combinations.
- Variant duplication prevention.

## Definition of Done
- CI passes with coverage threshold.
- Tests document major behaviors and edge cases.
