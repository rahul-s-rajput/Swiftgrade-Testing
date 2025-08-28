# Story 6: Essential OpenRouter Model Information

## Context and Goals
Surface a minimal set of useful OpenRouter model details without complicating the UI. Show pricing (prompt/input and completion/output) inline in the model select dropdown options only. Do not show context length and do not show meta on chips.

- Source: This doc. Component: `src/components/MultiSelect.tsx` (option row rendering) with parent supplying transformed data.

## Acceptance Criteria
- [ ] Option rows show: Name, Provider, and a subtle one-line pricing string.
- [ ] Pricing format: `$<amount>/M input tokens | $<amount>/M output tokens`.
- [ ] Values are derived from OpenRouter `pricing.prompt` (input) and `pricing.completion` (output), multiplied by 1,000,000 to convert per-token to per-million tokens.
- [ ] If one value is missing, show only the available one; if both are missing, show nothing (no placeholders).
- [ ] Selected chips do not display pricing or context.

## Implementation Plan
- Data: Retain the full OpenRouter model object in memory keyed by `id` via `useOpenRouterModels()` (`modelInfoById[id].raw`).
- UI: Keep `AIModel` as `{ id, name, provider }` for `MultiSelect` options.
- Rendering:
  - In the parent (`NewAssessment`), compute a meta string from `raw.pricing`:
    - `prompt` → input price; `completion` → output price.
    - Multiply numeric values by 1,000,000; format as `$X.XX/M` using locale-aware formatting.
    - Join available parts with a pipe: `$X.XX/M input tokens | $Y.YY/M output tokens`.
    - If neither is available, return `null` so the UI renders nothing.
  - Pass this through `renderOptionMeta(id)` prop to `MultiSelect` to display under the provider line with muted styling.
  - Do not render any meta on chips.

## Data Contracts
- Inputs: `AIModel[]` for `MultiSelect` plus internal `modelInfoById: Record<string, { raw?: OpenRouterModel }>` from `useOpenRouterModels()`.
- Output: Display-only pricing meta (ReactNode) via `renderOptionMeta(id)`; no behavior changes.

## UX States
- Keep existing interactions; no extra clicks or expanders.
- Avoid clutter; pricing line is subtle, single-line, and omitted entirely if empty.

## Prototype Notes
- Do not add complex formatting or tooltips; stick to one-line summaries.

## Definition of Done
- Name, provider, and a subtle pricing line are visible on options: `$<input>/M input tokens | $<output>/M output tokens`.
- No context length shown anywhere. No pricing shown on chips.
- No console warnings.
