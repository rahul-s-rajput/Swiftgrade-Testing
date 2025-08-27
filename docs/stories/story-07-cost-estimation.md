# Story 7: Cost Estimation

## Context and Goals
Estimate monthly costs based on user-provided token usage for each selected variant and overall.

- Source: User Stories (Story 7), Implementation Plan (Future Enhancements mentions cost calculator), Quick Start types.

## Acceptance Criteria
- [ ] Input expected tokens/month.
- [ ] Show cost per model variant.
- [ ] Total monthly cost estimate.
- [ ] Cost comparison between variants.
- [ ] Sort by cost-effectiveness.
- [ ] Export cost breakdown.
- [ ] Visual cost indicators (color coding).

## Implementation Plan
- __Utility__: `src/components/OpenRouterModelPicker/utils/costUtils.ts`
  - Convert `pricing.prompt/completion` strings to numeric per token costs.
  - Assume split: prompt:completion ratio input or show separate fields; start with a single total tokens field and assume 50:50 split with ability to adjust later.
  - Compute per-variant and total monthly costs.
- __UI__: Add a panel in picker footer or sidebar to input usage and show breakdown.
- __Export__: Reuse export infra from Story 9 once available; CSV/JSON.

## Testing Scenarios
- Numeric parsing with edge cases.
- Large usage values performance.
- Sorting changes order without mutating base selection.

## Definition of Done
- Cost estimates accurate to simple assumptions.
- Clear visuals and export of breakdown.
