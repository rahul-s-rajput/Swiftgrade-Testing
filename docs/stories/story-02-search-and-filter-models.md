# Story 2: Search and Filter Models

## Context and Goals
Enable users to quickly find models through search and filters. Build search bar, provider filter, price/context filters, and combine them with real-time updates.

- Source: `docs/openrouter-model-picker-user-stories.md` (Story 2), Quick Start (useModelFilter), Implementation Plan (Phase 2, Advanced Filtering).

## Acceptance Criteria
- [ ] Search bar filters by name, id, and description.
- [ ] Filter by provider (OpenAI, Anthropic, Google, etc.) derived from `model.id`.
- [ ] Filter by price range (prompt and completion costs) per 1M tokens.
- [ ] Filter by capabilities (placeholder for now until richer data; keep modality filter now).
- [ ] Filter by minimum context length.
- [ ] Filters can be combined.
- [ ] Results update in real-time with debounce on search (300ms) if necessary.
- [ ] Show count of filtered results.

## Implementation Plan
- __Hook__: `src/components/OpenRouterModelPicker/hooks/useModelFilter.ts`
  - State: `{ search, provider, maxPrice, minContext, capabilities, modality }`.
  - `providers` derived from `models` (unique provider from `id.split('/')`).
  - `filteredModels` computed with `useMemo`.
  - `updateFilter` and `clearFilters` helpers.
  - Parse pricing: multiply `pricing.prompt` and `pricing.completion` by 1,000,000 to compare against `maxPrice`.
- __UI__: `src/components/OpenRouterModelPicker/components/ModelFilters.tsx`
  - Provider dropdown (All + list from hook).
  - Max price input/select.
  - Min context input.
  - Modality dropdown where available.
  - Clear filters button.
- __Search__: Use the input in `OpenRouterModelPicker.tsx` bound to `filters.search`.
- __Count__: “Available Models (N)” from `filteredModels.length`.

## Data Contracts
- Inputs: `OpenRouterModel[]`, `ModelFilters` type.
- Outputs: `filteredModels`, `providers`, and filter setters.

## UX States
- Filters persist while navigating within the picker.
- Visually indicate active filters and provide a one-click clear.

## Testing Scenarios
- Combined filters narrow results as expected.
- Debounce prevents excessive re-renders (if implemented).
- Provider detection robust for all `id` shapes.
- Price parsing correct for prompt and completion.

## Definition of Done
- Filter UI wired to hook.
- Real-time filtered list displayed.
- Clear filters works and resets all.
- Count reflects filtered results.
