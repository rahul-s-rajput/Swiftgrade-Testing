# Story 1: Basic Model Fetching and Display

## Context and Goals
Build the base of the OpenRouter Model Picker by fetching models from the OpenRouter API and displaying them in a responsive grid/list with loading, error handling, and 1-hour caching.

- Source of truth: `docs/openrouter-model-picker-user-stories.md` (Story 1), `docs/openrouter-model-picker-quick-start.md` (Sections 2–4), `docs/openrouter-model-picker-implementation-plan.md` (Core Features 1, Architecture/API Integration, Phases 1).

## Acceptance Criteria
- [ ] Component fetches model data from `https://openrouter.ai/api/v1/models`.
- [ ] Models are displayed in a grid or list format.
- [ ] Each model shows: name, provider, pricing, context length.
- [ ] Loading state is shown while fetching.
- [ ] Error state handles API failures gracefully and falls back to cache when available.
- [ ] Model data is cached in `localStorage` with 1 hour TTL.

## Implementation Plan
- __Create hook__: `src/components/OpenRouterModelPicker/hooks/useModelFetch.ts`
  - Expose `{ models, loading, error, refetch(forceRefresh?: boolean) }`.
  - Cache key `openrouter_models_cache`, TTL 1h.
  - Sort models by provider then name.
  - On error, attempt to load cached data.
- __Create main shell component__: `src/components/OpenRouterModelPicker/OpenRouterModelPicker.tsx`
  - Integrate `useModelFetch()`.
  - Render header and content shell.
- __Create card component__: `src/components/OpenRouterModelPicker/components/ModelCard.tsx`
  - Props: `model`, `isSelected?`, `onToggleSelect?` (selection is for later stories, but structure now).
  - Display minimal surface: `name`, `provider` (from `id.split('/')`), pricing (prompt/completion per 1M tokens), `context_length`.
- __Responsive grid__: Tailwind-based grid, `1col` on mobile, `2cols` on md+.
- __States__: Loading spinner, error banner with retry.

## Data Contracts
- __Types__: `src/types/openrouter.ts`
  - Use `OpenRouterModel`, `OpenRouterModelsResponse` from Quick Start.
- __API__: GET `https://openrouter.ai/api/v1/models` returns `{ data: OpenRouterModel[] }`.

## UX States
- __Loading__: Centered spinner.
- __Error__: Non-blocking red banner with friendly message and a Retry button.
- __Empty__: If list is empty after fetch, show an empty state with guidance.

## Testing Scenarios
- __Fetch success__: models render; grid count matches.
- __Fetch error without cache__: error banner shown; list remains empty.
- __Fetch error with cache__: error banner shown; models render from cache.
- __Cache TTL__: data older than 1h triggers fresh fetch.

## Dependencies/Notes
- No auth required for model list.
- Use `fetch` with graceful error handling.
- Tailwind present in project (`tailwind.config.js`).

## Definition of Done
- Hook and components exist with types.
- Grid renders key fields per card.
- Loading and error states implemented.
- Caching with TTL and fallback works.
- Lint passes; no console errors.
