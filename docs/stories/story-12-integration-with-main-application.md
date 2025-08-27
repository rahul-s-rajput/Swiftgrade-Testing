# Story 12: Integration with Main Application

## Context and Goals
Integrate the existing `MultiSelect` into the assessment app pages using simple, controlled parent state. No custom wrapper component.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Use `MultiSelect` with props:
  - `label: string`
  - `options: AIModel[]`
  - `selectedValues: string[]`
  - `onChange(values: string[]): void`
  - `placeholder?: string`
- [ ] Parent holds selections in state and passes to `MultiSelect`.
- [ ] Default selections supported by initializing parent state.

## Implementation Plan
- __Parent State__: In `src/pages/NewAssessment.tsx` (or similar), maintain:
  - `const [selectedModels, setSelectedModels] = useState<string[]>(defaultIds)`
  - `const options: AIModel[] = [...]` (mock list or pulled from context)
- __Render__:
  - `<MultiSelect label="Models" options={options} selectedValues={selectedModels} onChange={setSelectedModels} />`
- __Reasoning__ (from Story 4): Optionally render inline reasoning controls per selected model below the chips, keyed by model id.

## Testing Scenarios
- Initial selections render from the parent state initializer.
- `onChange` updates parent state and chips reflect selection.

## Definition of Done
- Parent app renders `MultiSelect` with mock options.
- Selection changes flow through `onChange` without console errors.
