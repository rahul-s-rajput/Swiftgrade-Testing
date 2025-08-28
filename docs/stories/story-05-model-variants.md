# Story 5: Model Variants

## Context and Goals
Do not build a separate variants UI. With OpenRouter, variants and providers are already expressed as distinct model `id`s (e.g., `google/gemini-2.5-flash-image-preview` and `google/gemini-2.5-flash-image-preview:free`). Selection is per-id. Reasoning levels are configured via a compact per-chip dropdown popover (Story 4 refined UI), not inline rows.

- Source: This doc. Component: `src/components/MultiSelect.tsx` with parent-held reasoning state.

## Acceptance Criteria
- [ ] User can select multiple models; each model appears once.
- [ ] Reasoning is configured per selected model via a compact per-chip dropdown popover.
- [ ] Chip shows model name and reasoning badge.

## Implementation Plan
- Use `MultiSelect` for selection; prevent duplicates inherently by `selectedValues` being unique ids.
- Treat each OpenRouter id as a unique option. If two ids are similar (e.g., free vs paid), both can be selected independently.
- Open the per-chip dropdown popover from a kebab on each selected chip.
- Only render the kebab for models that support reasoning (from `modelInfoById[id].supportsReasoning`).
- Badge on chip reflects current config: `None`, `Low/Medium/High`, or `Custom: <tokens>`.

## Data Contracts
- `AIModel` base type; state shape: `selectedValues: string[]` and `reasoningByModel: Record<string, { level: ReasoningLevel; tokens?: number }>`.

## UX States
- Simple: adding a model adds one chip; no variants.
- Kebab hidden for models without reasoning support; dropdown anchored beside kebab.

## Prototype Notes
- Variants deferred. Keep UI minimal.

## Definition of Done
- Single entry per model; chips show/remove correctly.
- Chip shows reasoning badge; kebab appears only for models with reasoning support and opens dropdown.
