# Story 8: Keyboard Navigation

## Context and Goals
Provide keyboard-first navigation and accessibility for power users and a11y compliance.

- Source: User Stories (Story 8), Implementation Plan (Accessibility).

## Acceptance Criteria
- [ ] Tab navigation between interactive elements.
- [ ] Arrow keys navigate model grid.
- [ ] Space/Enter to select models.
- [ ] Escape to close modal.
- [ ] `/` to focus search.
- [ ] Ctrl+A to select all visible.
- [ ] Delete to remove selected.
- [ ] Focus trap in modal.

## Implementation Plan
- __Key handling__: Add handlers in `OpenRouterModelPicker.tsx` and propagate to grid.
- __ARIA__: Add roles/labels for cards, buttons, and list.
- __Focus management__: Initial focus to search input; trap while open.
- __Shortcut guide__: Small help tooltip or `?` modal.

## Testing Scenarios
- Keyboard-only flows succeed for all core actions.
- Screen reader announces labels correctly.

## Definition of Done
- All shortcuts implemented and documented.
- a11y checks pass (basic screen reader smoke tests).
