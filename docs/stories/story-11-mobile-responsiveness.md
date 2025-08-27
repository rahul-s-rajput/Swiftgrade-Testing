# Story 11: Mobile Responsiveness

## Context and Goals
Make the dropdown selector usable on phones and small screens with touch-friendly controls and mobile patterns.

- Source: `docs/openrouter-dropdown-user-stories.md` (Story 11), `docs/openrouter-dropdown-implementation-plan.md` (Mobile & Responsiveness).

## Acceptance Criteria
- [ ] Trigger adapts to small screens (full-width button with selected count).
- [ ] Touch-friendly controls (44px min target) for options and chips.
- [ ] Reasoning popover presents as a bottom sheet on mobile.
- [ ] Chips area collapses to horizontal scroll on small screens.
- [ ] Dropdown panel uses viewport height with internal scroll and sticky footer.
- [ ] Optimized for small screens; landscape supported.

## Implementation Plan
- __Responsive CSS__: Tailwind breakpoints for trigger, panel, and chips wrapper.
- __Bottom Sheet__: Media-query switch for `ReasoningConfigPopover` to bottom sheet.
- __Chips__: Horizontal scroll with fade edges on small screens.
- __Sticky Footer__: Actions (Export/Import/Cost) pinned at bottom of dropdown on mobile.

## Testing Scenarios
- Simulate common devices in devtools.
- Verify all actions possible via touch.

## Definition of Done
- Comfortable mobile experience without sacrificing features.
