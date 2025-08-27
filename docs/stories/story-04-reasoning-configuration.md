# Story 4: Reasoning Configuration

## Context and Goals
Enable users to set a simple reasoning level for each selected model using a lightweight inline control. No popovers/modals.

- Source: This doc. Component: `src/components/MultiSelect.tsx` wrapped by a parent with extra UI.

## Acceptance Criteria
- [ ] For each selected model, show a small select: None, Low, Medium, High, Custom.
- [ ] If Custom selected, show a numeric input for tokens (basic > 0 validation).
- [ ] The chosen level is displayed adjacent to the chip (e.g., small badge or label rendered by the parent below the chips).
- [ ] Reasoning config is stored in parent state keyed by model id: `{ [modelId]: { level: 'none'|'low'|'medium'|'high'|'custom', tokens?: number } }`.

## Implementation Plan
- __Parent wrapper__: Under the `MultiSelect`, render a list of selected chips (already shown) and, for each, a small `<select>` and optional `<input type="number">` for custom.
- __State__: `const [reasoningByModel, setReasoningByModel] = useState<Record<string, {level: string; tokens?: number}>>({});`
- __Display__: Render a small badge/label next to each chip (in a separate line/row) showing the chosen level.

## Data Contracts
- `ReasoningLevel = 'none' | 'low' | 'medium' | 'high' | 'custom'`.
- `ReasoningByModel: Record<string, { level: ReasoningLevel; tokens?: number }>`.

## UX States
- Simple inline controls; no popovers.
- Small badge/label rendered adjacent to chips, e.g., "[Medium]".

## Prototype Notes
- Keep validation minimal; no capability gating.

## Definition of Done
- Inline selectors appear for selected models.
- Badges reflect reasoning levels.
