# Story 12: Integration with Main Application

## Context and Goals
Integrate the existing `MultiSelect` into the assessment app pages using simple, controlled parent state. Use real OpenRouter model ids and call the OpenRouter chat/completions API with per-model reasoning configuration.

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
- [ ] When user runs an assessment, execute one OpenRouter request per selected model id with mapped reasoning parameters.
- [ ] Handle loading and error states minimally.

## Implementation Plan
- __Parent State__: In `src/pages/NewAssessment.tsx` (or similar), maintain:
  - `const [selectedModels, setSelectedModels] = useState<string[]>(defaultIds)`
  - `const [reasoningByModel, setReasoningByModel] = useState<Record<string, { level: 'none'|'low'|'medium'|'high'|'custom'; tokens?: number; exclude?: boolean }>>({})`
  - `const options: AIModel[] = [...]` (fetched and transformed from Story 1; `provider` = `id.split('/')[0]`)
- __Render__:
  - `<MultiSelect label="Models" options={options} selectedValues={selectedModels} onChange={setSelectedModels} />`
  - Render inline reasoning controls per selected model below the chips (Story 4).
- __OpenRouter Request__ (one per model id):
  - Endpoint: `POST https://openrouter.ai/api/v1/chat/completions`
  - Headers:
    - `Authorization: Bearer ${OPENROUTER_API_KEY}`
    - `Content-Type: application/json`
    - Optional but recommended: `HTTP-Referer`, `X-Title`
  - Body (per model):
    - `model`: the exact OpenRouter model id from selection
    - `messages`: array of `{ role: 'system'|'user'|'assistant', content: string }`
    - `reasoning`: based on `reasoningByModel[modelId]` per Story 4 mapping:
      - level `none` → omit `reasoning`
      - level `low|medium|high` → `{ effort: 'low'|'medium'|'high', ...(exclude && { exclude: true }) }`
      - level `custom` with tokens → `{ max_tokens: tokens, ...(exclude && { exclude: true }) }`
    - Optional: `temperature`, `top_p`, etc., if needed by the app.
- __Execution Strategy__:
  - Iterate selected model ids and perform requests sequentially or in parallel with simple concurrency control.
  - Collect responses into the assessment result structure and update via `updateAssessmentStatus()` in `src/context/AssessmentContext.tsx`.
- __Loading/Error Handling__:
  - Show a minimal spinner or status text while requests are in flight.
  - On error (e.g., 401, 429), mark that model's result with an error message and continue others.

## Testing Scenarios
- Initial selections render from the parent state initializer.
- `onChange` updates parent state and chips reflect selection.
- For 2+ selected models, two API requests are sent with correct `model` ids and `reasoning` payloads.
- A 401 without key halts the run with a user-facing message; 429 retry is optional and can be skipped for prototype.

## Security Notes
- Do not commit API keys. Use environment variables.
- Do not call OpenRouter directly from the browser in production. Use a backend/proxy route that injects the API key server-side.
- For local development with Vite, consider a small serverless/API route or dev proxy; never embed the key in client code.

## Definition of Done
- Parent app renders `MultiSelect` with real OpenRouter options from Story 1 fetch.
- Selection changes flow through `onChange` without console errors.
- Pressing "Run" sends one request per selected model id with correct `reasoning` mapping and shows results or minimal errors.
