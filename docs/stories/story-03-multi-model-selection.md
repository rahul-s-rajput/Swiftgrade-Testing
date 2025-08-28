# Story 3: Multi-Model Selection

## Context and Goals
Allow users to select/deselect multiple OpenRouter models with visual feedback and persistent selection while filtering, showing selections as chips above the dropdown. Selection is by exact OpenRouter model `id` (e.g., `openai/gpt-5`, `google/gemini-2.5-flash-image-preview:free`).

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Click to select/deselect models.
- [ ] Visual indicator for selected items on dropdown list.
- [ ] Selected models appear as chips above the dropdown.
- [ ] Can remove models from selected list.
- [ ] Selection persists during filtering and search.
- [ ] Optional: "Clear all" button provided by parent next to chips.
- [ ] Show count of selected models on trigger.

## Implementation Plan
- __Parent state__: Maintain `selectedValues: string[]` of OpenRouter model ids and pass to `MultiSelect`.
- __Chips/UI__: `MultiSelect` already renders removable chips and selected count on trigger.
- __Optional Clear All__: Parent renders a small button to reset `selectedValues` to `[]`.

## Data Contracts
- `AIModel` from `src/types/index.ts`; `selectedValues: string[]` of OpenRouter model ids.

## UX States
- Selecting a model animates/marks dropdown item.
- Removing from chip updates dropdown item state.

## Prototype Notes
- No variants; one entry per model id.
- No bulk select; keep behavior simple.

## Definition of Done
- Chips reflect current selection with remove.
- Optional Clear All resets selection.
- No console warnings; state remains consistent.
