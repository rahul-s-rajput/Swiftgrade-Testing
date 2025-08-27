# Story 17: Recent and Favorite Models

## Context and Goals
Make frequently used models easy to access by optionally showing "Recent" models first. Keep it parent-managed and simple. No Favorites.

- Source: This doc. Component: `src/components/MultiSelect.tsx` (parent prepares `options`).

## Acceptance Criteria
- [ ] When enabled, recently selected model ids appear first in the `options` array passed to `MultiSelect`.
- [ ] Parent updates a simple recents list when a selection occurs (most-recent-first, deduped).
- [ ] Optional: persist recents in `localStorage` with a small max size (e.g., 8).

## Implementation Plan
- In parent state:
  - Maintain `recents: string[]`.
  - On selection change, unshift new ids into `recents` while removing duplicates and capping length.
- Build `options` by sorting: ids in `recents` first (stable by recency), then the rest by name.
- Optional: persist `recents` to `localStorage` and hydrate on load.

## Testing Scenarios
- Selections update recents ordering.
- Hydration from `localStorage` places recent ids first.

## Definition of Done
- Recents-first ordering works when enabled; no UI groups or stars required.
