# Story 15: Bulk Reasoning Configuration

## Context and Goals
Provide a simple way to apply a reasoning preset to all currently selected models. Keep it lightweight and parent-managed.

- Source: This doc. Component: `src/components/MultiSelect.tsx` with parent-managed state.

## Acceptance Criteria
- [ ] Choose a preset: None, Low, Medium, High, Custom.
- [ ] Click "Apply to Selected" updates reasoning for all currently selected model ids.
- [ ] If "Custom", show a tokens numeric input that applies the same value to all selected.
- [ ] Optional: show affected count (e.g., `Apply to N`).

## Implementation Plan
- In the parent below chips, render a small bulk action row:
  - `<select>` for preset and optional `<input type="number">` for tokens when preset === 'custom'.
  - An "Apply to Selected" button. Disabled when no selections.
- On apply, iterate `selectedValues` and update `reasoningByModel[id]` to the chosen preset/tokens.

## Testing Scenarios
- Applying a preset updates all selected models' displayed badges.
- Custom tokens input propagates to all selected models.

## Definition of Done
- A single click applies the selected preset to all selected models; badges/labels reflect the change.
