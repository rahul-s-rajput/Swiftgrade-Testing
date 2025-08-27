# Story 12: Integration with Main Application

## Context and Goals
Expose a clean API from the picker for the parent assessment app to consume and integrate into the workflow.

- Source: User Stories (Story 12), Quick Start (Usage Example), Implementation Plan (Phases 5, Component Structure).

## Acceptance Criteria
- [ ] Props interface for parent component.
- [ ] Callback for selection changes and apply.
- [ ] Controlled/uncontrolled modes.
- [ ] Default selections support.
- [ ] Disabled models option.
- [ ] Custom styling props.
- [ ] Event emissions for key actions.

## Implementation Plan
- __Component__: `OpenRouterModelPicker.tsx`
  - Props: `{ isOpen, onClose, onSelectionComplete(models), initialSelection?, className?, disabledModelIds? }`.
  - Internal state from hooks; hydrate from `initialSelection`.
  - Fire `onSelectionComplete` on Apply.
  - Optional `onChange(selectedModels)` for live updates.
- __Index__: `src/components/OpenRouterModelPicker/index.ts` to export.
- __Example__: Add demo usage to `src/pages/NewAssessment.tsx` or a new demo page.

## Testing Scenarios
- Controlled vs uncontrolled flows behave predictably.
- Disabled ids cannot be selected.
- Initial selections render correctly.

## Definition of Done
- Parent app can open picker, select, and receive variants.
- Types exported from `src/types/openrouter.ts`.
