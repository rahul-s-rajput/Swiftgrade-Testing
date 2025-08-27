# Story 6: Advanced Model Information

## Context and Goals
Provide expandable details per model to inform selection decisions.

- Source: User Stories (Story 6), Implementation Plan (Model Card Design), Quick Start types.

## Acceptance Criteria
- [ ] Expandable details on model cards.
- [ ] Show: description, architecture, tokenizer.
- [ ] Display supported parameters (if provided by API).
- [ ] Show provider information.
- [ ] Link to model documentation (if link derivable or provided).
- [ ] Visual badges for capabilities (vision, reasoning, modality) when detectable.
- [ ] Pricing breakdown (per 1K/1M tokens) with formatter.
- [ ] Last updated timestamp (from fetch time or API field if available).

## Implementation Plan
- __Card__: Expand/collapse section.
- __Utils__: `src/components/OpenRouterModelPicker/utils/modelUtils.ts` for provider extraction, capability badges, and safe pricing computations.
- __Utils__: `pricingUtils.ts` to format `$ per 1K/1M tokens` from `pricing.prompt/completion`.

## Data Contracts
- Use `OpenRouterModel.architecture`, `supported_parameters?`, `top_provider` where available.

## UX States
- Collapsed by default; remembers expand state in-session.

## Testing Scenarios
- Models without optional fields render gracefully.
- Pricing math verified.
- External links open safely (new tab, rel noopener).

## Definition of Done
- Cards show rich details without layout regressions.
- Utilities tested with representative model shapes.
