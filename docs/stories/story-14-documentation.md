# Story 14: Documentation

## Context and Goals
Document the simple API and usage of the existing `MultiSelect` component so it can be adopted in pages quickly.

- Source: This doc. Component: `src/components/MultiSelect.tsx`.

## Acceptance Criteria
- [ ] Basic API docs for props and `AIModel` type.
- [ ] One usage snippet showing parent state and `onChange`.
- [ ] Note on styling via Tailwind classes already in component.

## Implementation Plan
- __Docs__: Add a short section to `docs/README.md` or keep this story as the reference.
- __TSdoc__: Ensure `MultiSelectProps` and `AIModel` have inline comments.
- __Example__:
  ```tsx
  import { useState } from 'react';
  import { MultiSelect } from '../components/MultiSelect';
  import type { AIModel } from '../types';

  const options: AIModel[] = [
    { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
    { id: 'gemini-1.5', name: 'Gemini 1.5', provider: 'Google' },
  ];

  export function Demo() {
    const [selected, setSelected] = useState<string[]>([]);
    return (
      <MultiSelect
        label="Models"
        options={options}
        selectedValues={selected}
        onChange={setSelected}
        placeholder="Select models..."
      />
    );
  }
  ```

## Definition of Done
- API and example reflect actual component props.
- Snippet compiles in the app context without errors.
