# Story 4: Reasoning Configuration

## Context and Goals
Enable users to configure reasoning levels per model, using presets and a custom option, applying only where supported.

- Source: User Stories (Story 4), Quick Start (Reasoning types and config), Implementation Plan (Reasoning Presets).

## Acceptance Criteria
- [ ] Preset options: None, Low, Medium, High, Custom.
- [ ] Low = 20% of max_tokens for reasoning; Medium = 50%; High = 80% (use provider `max_completion_tokens` where available; otherwise omit token-based calculations and just set `effort`).
- [ ] Custom allows manual token allocation.
- [ ] Visual indicator shows reasoning level on cards/variants.
- [ ] Reasoning only available for capable models (gate by available fields or capability flag if present).
- [ ] Configuration saved per model variant.

## Implementation Plan
- __Component__: `src/components/OpenRouterModelPicker/components/ReasoningSelector.tsx`
  - Props: `model`, `onSelect(reasoningType, customMaxTokens?)`.
  - Presets mapping to `ReasoningConfig`: none -> `{ include_reasoning: false }`; low/medium/high -> `{ effort: 'low'|'medium'|'high', include_reasoning: true }`; custom -> `{ max_tokens, include_reasoning: true }`.
  - Compute percent-of-max helper using `model.top_provider?.max_completion_tokens` if present.
- __Card__: Add "+ Add Variant" button to open selector and call `addModelVariant` with chosen config.
- __Validation__: Hide/disable reasoning options if unsupported; show tooltip.

## Data Contracts
- `ReasoningType = 'none' | 'low' | 'medium' | 'high' | 'custom'`.
- `ReasoningConfig` as in Quick Start.

## UX States
- Modal/bottom sheet for selector with clear presets.
- Badge on variant: e.g., "(medium reasoning)".

## Testing Scenarios
- Preset selection generates correct config.
- Custom token entry validated for numeric limits.
- Unsupported models cannot select reasoning.

## Definition of Done
- Selector integrated with cards and selection hook.
- Variants reflect reasoning choice and display name includes level.
- Validation and UX affordances in place.
