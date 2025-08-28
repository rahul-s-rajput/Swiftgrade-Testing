# Story 1: Basic Model Fetching and Display

## Context and Goals
Fetch the real OpenRouter model catalog and display models in the existing `MultiSelect`. Cache results locally to avoid repeated network calls.

- Source of truth: OpenRouter docs + this doc; component `src/components/MultiSelect.tsx`; types in `src/types` and OpenRouter model shape.

## Acceptance Criteria
- [ ] On load, fetch `https://openrouter.ai/api/v1/models` and transform to `AIModel[]` for `MultiSelect`.
- [ ] Options display `name` and `provider` (uses `MultiSelect` default rendering).
- [ ] Cache transformed list in `localStorage` with a 1h TTL; reuse cache if still valid.
- [ ] Handle loading and error states minimally (spinner/text).
- [ ] Selected chips show and can be removed.
- [ ] Detect reasoning support via model ID patterns (heuristic; e.g., contains `gpt-4`, `o1`, `deepseek-r1`, `:thinking`, etc.).
- [ ] Parse variant suffixes from model IDs (e.g., `:free`, `:nitro`, `:floor`, `:thinking`).
- [ ] Use safe field access with sensible defaults when building any display helpers.

## Implementation Plan
- __Hook/Fetcher__: Create a small hook or effect to fetch models, cache, and transform:
  - GET `https://openrouter.ai/api/v1/models`
  - Transform each item to `{ id, name, provider }` for display and also retain the full OpenRouter model in a map keyed by id.
  - Additionally compute helper fields (kept in memory, not required by `MultiSelect`):
    - `supportsReasoning`: detect via ID patterns
    - `variants`: parse suffixes from ID (e.g., `free`, `nitro`, `floor`, `thinking`)
    - Safe-access helpers like `contextDisplay`, `priceDisplay` using defaults when missing
  - Cache `transformedModels` + `Date.now()`; if `< 1h`, use cache.
- __Parent page__: Render `MultiSelect` with fetched `options` and `selectedValues`.
- __Styling__: Use Tailwind classes already present in `MultiSelect`.

## Data Contracts
- __Display Type__: `AIModel` with `id`, `name`, `provider` (for `MultiSelect`).
- __Source Type__: OpenRouter model objects (retain in memory for request usage: pricing, context_length, etc.).

## UX States
- __Loading__: Minimal text/spinner until models fetched.
- __Error__: Show text and allow retry.
- __Empty__: If no options, show "No models found" (handled by `MultiSelect`).

## Notes
- Authorization header is not required for the public models list; add if your setup demands it.

## Dependencies/Notes
- Tailwind present in project (`tailwind.config.js`).

## Definition of Done
- Parent renders `MultiSelect` with fetched OpenRouter options.
- Selected chips render and are removable.
- Cache works; basic loading/error handled; no console errors.
