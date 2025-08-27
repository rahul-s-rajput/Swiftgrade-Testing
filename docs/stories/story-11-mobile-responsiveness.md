# Story 11: Mobile Responsiveness

## Context and Goals
Make picker usable on phones and small screens with touch-friendly controls.

- Source: User Stories (Story 11), Implementation Plan (Accessibility/Design).

## Acceptance Criteria
- [ ] Responsive grid layout (1 col on small, 2+ on larger).
- [ ] Touch-friendly controls with larger hit targets.
- [ ] Swipe gestures for panels where appropriate.
- [ ] Collapsible filters on mobile.
- [ ] Bottom sheet modal on mobile for Reasoning Selector.
- [ ] Optimized for small screens; landscape supported.

## Implementation Plan
- __Responsive CSS__: Tailwind breakpoints.
- __Touch handlers__: Lightweight gesture support; optional lib if needed.
- __Layout shifts__: Filters collapse into accordion; selection panel becomes bottom drawer.

## Testing Scenarios
- Simulate common devices in devtools.
- Verify all actions possible via touch.

## Definition of Done
- Comfortable mobile experience without sacrificing features.
