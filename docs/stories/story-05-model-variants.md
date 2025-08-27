# Story 5: Model Variants

## Context and Goals
Allow creating multiple variants of the same base model with different reasoning settings and custom names, preventing duplicates.

- Source: User Stories (Story 5), Quick Start (Variant generation), Implementation Plan (Variant creation).

## Acceptance Criteria
- [ ] "Add Variant" button on each model card.
- [ ] Variant creation modal with reasoning options.
- [ ] Custom name for each variant.
- [ ] Display format: `model-name (reasoning-level)`.
- [ ] Variants shown in selected models list.
- [ ] Each variant has unique ID.
- [ ] Can delete individual variants.
- [ ] Prevent duplicate variants for same base model + reasoning type.

## Implementation Plan
- __Hook__: Extend `useModelSelection` to generate `variantId = `${model.id}_${reasoningType}_${timestamp}`` and duplicate checks.
- __UI__: `ReasoningSelector` collects preset or custom and optional name.
- __Selected List__: Render custom name or `displayName` fallback; delete icon.

## Data Contracts
- `SelectedModel` includes `variantId`, `displayName` and `reasoningType`.

## UX States
- Success toast when variant added; warning if duplicate.

## Testing Scenarios
- Duplicate prevention works across filtering/navigations.
- Custom names persist.
- Deleting one variant does not affect others of same base model.

## Definition of Done
- Multiple variants per base model supported.
- IDs are unique and stable during session.
- UI shows and removes variants correctly.
