# Story 2: Search and Filter Models

## Context and Goals
Enable users to quickly find models using the built-in search inside `MultiSelect`. With OpenRouter data, filter by `name` and derived `provider` (from the model `id` prefix), and preserve selections.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Typing filters options by model `name` or `provider` in real-time.
- [ ] Shows "No results" state when nothing matches.
- [ ] Selection is preserved while searching.
- [ ] Optional: Display filtered count (skip for prototype).

## Implementation Plan
- Built-in: `MultiSelect` already filters by `option.name` and `option.provider`.
- Transform step (from Story 1 fetch): set `AIModel.provider = openrouterModel.id.split('/')[0]` and `AIModel.name = openrouterModel.name`.
- Parent passes `options: AIModel[]` and `selectedValues: string[]`.

## Data Contracts
- Inputs: `AIModel[]`.
- Outputs: filtered list is handled internally by `MultiSelect`.

## UX States
- Search term persists while dropdown is open.

## Prototype Notes
- No special performance or highlighting; rely on the existing component.

## Definition of Done
- Real-time filtered list displayed in dropdown.
- Selection remains intact as user searches.
