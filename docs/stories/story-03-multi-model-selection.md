# Story 3: Multi-Model Selection

## Context and Goals
Allow users to select/deselect multiple models with visual feedback and persistent selection while filtering.

- Source: `docs/openrouter-model-picker-user-stories.md` (Story 3), Quick Start (useModelSelection), Implementation Plan (Multi-Selection).

## Acceptance Criteria
- [ ] Click to select/deselect models.
- [ ] Visual indicator for selected models on cards.
- [ ] Selected models appear in a separate list panel.
- [ ] Can remove models from selected list.
- [ ] Selection persists during filtering and search.
- [ ] "Clear all" and "Select all visible" options.
- [ ] Show count of selected models.

## Implementation Plan
- __Hook__: `src/components/OpenRouterModelPicker/hooks/useModelSelection.ts`
  - `selectedModels: SelectedModel[]`.
  - `toggleModel(model)` selects/deselects a default "none"-reasoning variant.
  - `addModelVariant(model, reasoningType, customMaxTokens?)` returns success boolean; prevent duplicates.
  - `removeModelVariant(variantId)` and `clearSelection()`.
  - `isModelSelected(modelId)` to style cards.
- __Card Integration__: `ModelCard.tsx`
  - Checkbox or button toggle; badge/state when selected.
- __Selected List__: `src/components/OpenRouterModelPicker/components/SelectedModelsList.tsx`
  - Shows `displayName` per variant; remove button.
  - Footer actions: Clear all. Provide bulk action hook for "Select all visible" from parent.
- __Layout__: Right sidebar `Selected Models (count)`.

## Data Contracts
- `SelectedModel` with fields: `id`, `baseModelId`, `displayName`, `reasoningType`, `reasoningConfig?`, `variantId`.

## UX States
- Selecting a model animates/marks card.
- Removing from sidebar updates card state.
- Bulk select/deselect available.

## Testing Scenarios
- Select/deselect cycles correctly.
- Selections persist across filter operations.
- Duplicates not added.
- Clear all empties both list and card states.

## Definition of Done
- Hook and UI connected.
- Sidebar reflects current selection with remove.
- Bulk actions implemented.
- No console warnings; state remains consistent.
