# Story 2: Search and Filter Models

## Context and Goals
Enable users to quickly find models using the built-in search inside `MultiSelect`. Keep it simple: filter by name or provider; preserve selections.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Typing filters options by model name or provider in real-time.
- [ ] Shows "No results" state when nothing matches.
- [ ] Selection is preserved while searching.
- [ ] Optional: Display filtered count (skip for prototype).

## Implementation Plan
- Built-in: `MultiSelect` manages `searchTerm` internally and filters `options` by `name` and `provider`.
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
