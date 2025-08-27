# Story 5: Model Variants

## Context and Goals
For the prototype, we will NOT support multiple variants per model. Selection is per-model only. Reasoning levels are handled inline as in Story 4.

- Source: This doc. Component: `src/components/MultiSelect.tsx` with parent-held reasoning state.

## Acceptance Criteria
- [ ] User can select multiple models; each model appears once.
- [ ] Reasoning is configured per selected model using Story 4's inline controls.
- [ ] Chip shows model name and reasoning badge.

## Implementation Plan
- Use `MultiSelect` for selection; prevent duplicates inherently by `selectedValues` being unique ids.
- Render Story 4's inline reasoning controls below chips in the parent.

## Data Contracts
- `AIModel` base type; state shape: `selectedValues: string[]` and `reasoningByModel: Record<string, { level: ReasoningLevel; tokens?: number }>`.

## UX States
- Simple: adding a model adds one chip; no variants.

## Prototype Notes
- Variants deferred. Keep UI minimal.

## Definition of Done
- Single entry per model; chips show/remove correctly.
