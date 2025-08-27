# Story 8: Keyboard Navigation

## Context and Goals
Provide minimal keyboard behaviors that come naturally with the existing component. Full a11y/ARIA is out-of-scope for the prototype.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Pressing the trigger opens/closes the dropdown.
- [ ] When opened, the search input is focusable and typing filters results.
- [ ] Clicking outside closes the dropdown.
- [ ] Optional: Escape closes the dropdown (nice-to-have enhancement).
- [ ] Tabbing moves focus through focusable elements (browser default).

## Implementation Plan
- Rely on existing `MultiSelect` behavior: click to open, input accepts typing, click outside closes.
- Optional: Focus the search input when opening by moving `setIsOpen(true)` then focusing the input via a ref.
- Optional: Add an onKeyDown handler to close on Escape.

## Testing Scenarios
- Ensure outside click closes the panel. If Escape is implemented, it also closes.
- Ensure typing filters while input is focused.

## Definition of Done
- Minimal keyboard interactions work without errors.
