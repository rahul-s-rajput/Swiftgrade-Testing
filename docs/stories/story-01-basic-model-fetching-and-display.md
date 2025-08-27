# Story 1: Basic Model Fetching and Display

## Context and Goals
For the prototype, integrate the existing mock `MultiSelect` with an in-memory list of models. No API fetching or caching.

- Source of truth: This doc; use `src/components/MultiSelect.tsx` and the `AIModel` type in `src/types`.

## Acceptance Criteria
- [ ] Render `MultiSelect` with props: `label`, `options: AIModel[]`, `selectedValues: string[]`, `onChange`.
- [ ] Options display model `name` and `provider` (as implemented in `MultiSelect`).
- [ ] Provide a small mock `AIModel[]` list in the parent page.
- [ ] Selected chips show and can be removed.

## Implementation Plan
- __Parent page__: Import and render `MultiSelect`.
  - Maintain `const [selectedIds, setSelectedIds] = useState<string[]>([])`.
  - Prepare `const options: AIModel[] = [...]` with mock items: `{ id, name, provider }`.
- __Styling__: Use Tailwind classes already present in `MultiSelect`.

## Data Contracts
- __Types__: `src/types/index.ts` should export `AIModel` with `id`, `name`, `provider`.

## UX States
- __Empty__: If no options, show "No models found" (handled by `MultiSelect`).

## Prototype Notes
- Keep things simple: no network calls, no caching.

## Dependencies/Notes
- Tailwind present in project (`tailwind.config.js`).

## Definition of Done
- Parent renders `MultiSelect` with mock options.
- Selected chips render and are removable.
- Lint passes; no console errors.
