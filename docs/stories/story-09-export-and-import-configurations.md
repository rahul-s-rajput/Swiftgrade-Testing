# Story 9: Export and Import Configurations

## Context and Goals
Allow users to save, share, and load model selections via JSON, code snippets, and URLs.

- Source: User Stories (Story 9), Implementation Plan (API Integration Examples, Export/Import in Future Enhancements), Quick Start (Next Steps 5).

## Acceptance Criteria
- [ ] Export selection as JSON.
- [ ] Export selection as code snippet (TypeScript usage sample).
- [ ] Import from JSON file.
- [ ] Import from clipboard.
- [ ] Validate imported data (schema).
- [ ] Share via URL (encoded selection).
- [ ] Download configuration file.

## Implementation Plan
- __Serialization__: `src/components/OpenRouterModelPicker/utils/serialization.ts`
  - `serializeSelection(models: SelectedModel[]): string` (JSON string).
  - `deserializeSelection(json: string): SelectedModel[]` with validation.
  - URL-safe base64 param `?config=`.
- __UI__: Buttons in footer: Export JSON, Copy Code, Import.
- __Validation__: Zod or custom type guards to verify fields including `variantId` uniqueness.

## Testing Scenarios
- Round-trip import/export retains all fields.
- Invalid payloads are rejected with clear errors.
- URL encoding length manageable; large selections handled gracefully.

## Definition of Done
- Users can export/import reliably via file/clipboard/URL.
- Code snippet integrates with API call shape in docs.
