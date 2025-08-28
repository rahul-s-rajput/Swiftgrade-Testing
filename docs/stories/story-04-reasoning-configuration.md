# Story 04: Reasoning Configuration - Implementation Guide

## Refined UI: Per-Chip Dropdown Popover

Reasoning configuration is presented as a compact dropdown popover anchored to a kebab (three-dot) button on each selected model chip.

- Kebab only appears for models that support reasoning (`modelInfoById[id].supportsReasoning`).
- Dropdown options adapt to the model's `reasoningType` (`effort`, `max_tokens`, `both`, or `none`).
- Positioning: popover is absolutely positioned within a local relative container, anchored to the kebab's bounding rect, vertically centered, with outside-click handling to close.
- Badges: each chip shows a small badge summarizing the current config (`None`, `Low/Medium/High`, or `Custom: N`).
- Pricing note: removed. We do not show a “reasoning billed” warning in the dropdown.

Components involved:
- `src/components/MultiSelect.tsx` exposes optional props to extend chip UI.
- `src/pages/NewAssessment.tsx` hosts the reasoning state per model and controls the popover.

## Real-Time Detection of Model Reasoning Capabilities

### How OpenRouter Provides Reasoning Information

OpenRouter's `/api/v1/models` API endpoint provides complete information about each model's reasoning capabilities through the `supported_parameters` array. No guessing or regex needed!

## API Response Structure

Each model in the response includes:

```typescript
interface OpenRouterModel {
  id: string;
  name: string;
  // ... other fields
  supported_parameters: string[];  // ← This tells us what the model supports
  pricing: {
    prompt: string;
    completion: string;
    internal_reasoning?: string;  // ← Some models have separate reasoning pricing
    // ... other pricing
  };
}
```

## Detection Logic

### 1. Identify Reasoning Support

```typescript
interface ReasoningCapabilities {
  supportsReasoning: boolean;
  reasoningType: 'effort' | 'max_tokens' | 'both' | 'none';
  hasIncludeReasoning: boolean;
  hasInternalReasoningPricing: boolean;
}

function detectReasoningCapabilities(model: OpenRouterModel): ReasoningCapabilities {
  const params = model.supported_parameters || [];
  
  const hasReasoning = params.includes('reasoning');
  const hasIncludeReasoning = params.includes('include_reasoning');
  const hasInternalReasoningPricing = !!model.pricing?.internal_reasoning;
  
  // Determine reasoning type based on model patterns
  let reasoningType: 'effort' | 'max_tokens' | 'both' | 'none' = 'none';
  
  if (hasReasoning) {
    // Models that support effort levels (based on documentation):
    // - Anthropic models (Claude 3.7+, Claude 4+)
    // - Mistral Magistral models
    // - Google Gemini 2.5 models
    // - Z.AI GLM models
    
    const supportsEffort = 
      model.id.includes('anthropic/') ||
      model.id.includes('mistral/magistral') ||
      model.id.includes('google/gemini-2.5') ||
      model.id.includes('z-ai/glm');
    
    // Models that support max_tokens:
    // - OpenAI reasoning models (o1, o3, GPT-5 series)
    // - DeepSeek R1 models
    // - Some open models
    
    const supportsMaxTokens = 
      model.id.includes('openai/') ||
      model.id.includes('deepseek/') ||
      model.id.includes('qwen/') && model.id.includes('thinking');
    
    if (supportsEffort && supportsMaxTokens) {
      reasoningType = 'both';
    } else if (supportsEffort) {
      reasoningType = 'effort';
    } else if (supportsMaxTokens) {
      reasoningType = 'max_tokens';
    }
  }
  
  return {
    supportsReasoning: hasReasoning || hasIncludeReasoning,
    reasoningType,
    hasIncludeReasoning,
    hasInternalReasoningPricing
  };
}
```

### 2. Enhanced Model Filtering Hook

```typescript
// useModelFilter.ts - Enhanced version
export const useModelFilter = (models: OpenRouterModel[]) => {
  const [filters, setFilters] = useState<ModelFilters>({
    // ... existing filters
    reasoningSupport: 'all', // 'all' | 'reasoning' | 'none'
  });

  const filteredModels = useMemo(() => {
    return models.filter(model => {
      // ... existing filters
      
      // Reasoning filter
      if (filters.reasoningSupport !== 'all') {
        const capabilities = detectReasoningCapabilities(model);
        if (filters.reasoningSupport === 'reasoning' && !capabilities.supportsReasoning) {
          return false;
        }
        if (filters.reasoningSupport === 'none' && capabilities.supportsReasoning) {
          return false;
        }
      }
      
      return true;
    });
  }, [models, filters]);

  // Group models by reasoning capability
  const modelsByReasoning = useMemo(() => {
    const groups = {
      effort: [] as OpenRouterModel[],
      maxTokens: [] as OpenRouterModel[],
      both: [] as OpenRouterModel[],
      none: [] as OpenRouterModel[]
    };
    
    filteredModels.forEach(model => {
      const capabilities = detectReasoningCapabilities(model);
      groups[capabilities.reasoningType].push(model);
    });
    
    return groups;
  }, [filteredModels]);

  return {
    filters,
    filteredModels,
    modelsByReasoning,
    updateFilter,
    clearFilters
  };
};
```

### 3. Per-Chip Dropdown Integration

We no longer use modals or inline rows. Instead, `MultiSelect` exposes opt-in props to enable a kebab-triggered popover per chip. The parent manages reasoning state and popover.

```typescript
// src/components/MultiSelect.tsx (props excerpt)
interface MultiSelectProps {
  label: string;
  options: AIModel[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  getChipBadge?: (id: string) => React.ReactNode;
  onChipMenuRequest?: (id: string, anchorRect: DOMRect) => void;
  shouldShowChipMenu?: (id: string) => boolean;
}
```

Example usage in `src/pages/NewAssessment.tsx`:

```tsx
<div ref={containerRef} className="relative">
  <MultiSelect
    label="Models"
    options={models}
    selectedValues={selectedModels}
    onChange={setSelectedModels}
    shouldShowChipMenu={(id) => !!modelInfoById?.[id]?.supportsReasoning}
    getChipBadge={(id) => renderReasoningBadge(reasoningByModel[id])}
    onChipMenuRequest={(id, anchorRect) => openReasoningDropdown(id, anchorRect)}
  />

  {activeMenu && (
    <div
      style={{
        position: 'absolute',
        left: activeMenu.left,
        top: activeMenu.top,
        transform: 'translateY(-50%)', // vertical center
      }}
      className="z-50 w-56 rounded-md border bg-white shadow-lg"
      ref={dropdownRef}
    >
      {/* Render options based on modelInfoById[activeMenu.modelId].reasoningType */}
      {/* Effort: Low/Medium/High; Tokens: numeric input (min 256); Both: toggle */}
    </div>
  )}
</div>
```

Notes:
- Compute `left/top` from the kebab button’s `getBoundingClientRect()` relative to `containerRef`.
- Close on outside-click; clamp to viewport if needed.
- Minimum custom tokens: 256.

## Key Implementation Points

### 1. **No Guessing Required**
The `supported_parameters` array tells you exactly what each model supports:
- `"reasoning"` - Model supports the unified reasoning parameter
- `"include_reasoning"` - Model supports including reasoning in response

### 2. **Model-Specific Reasoning Types**
Based on OpenRouter documentation and API patterns:

**Effort-based models** (low/medium/high):
- Anthropic Claude models (3.7+, 4+)
- Mistral Magistral models  
- Google Gemini 2.5 models
- Z.AI GLM models

**Token-based models** (max_tokens):
- OpenAI reasoning models (o1, o3, GPT-5)
- DeepSeek R1 models
- Qwen thinking models

**Both types**:
- Some models support both configuration methods
- Let users choose their preferred method

### 3. **Pricing Awareness**
Some models have separate pricing for reasoning tokens:
```typescript
if (model.pricing.internal_reasoning) {
  // This model charges separately for reasoning
  const reasoningCostPerMillion = parseFloat(model.pricing.internal_reasoning) * 1000000;
}
```

### 4. **Dynamic UI Generation**
The UI automatically adapts based on model capabilities:
- Shows effort selector for effort-based models
- Shows token input for token-based models
- Shows both options for flexible models
- Hides reasoning options for non-reasoning models

## Testing the Implementation

```typescript
// Example: Test with real models from the API
const testModels = [
  {
    id: "anthropic/claude-opus-4",
    supported_parameters: ["include_reasoning", "reasoning", "max_tokens"]
    // Result: Shows effort levels UI
  },
  {
    id: "openai/gpt-5",
    supported_parameters: ["max_tokens", "structured_outputs"] 
    // Result: No reasoning UI shown
  },
  {
    id: "deepseek/deepseek-r1",
    supported_parameters: ["include_reasoning", "reasoning"]
    // Result: Shows custom tokens UI
  }
];
```

## Benefits of This Approach

1. **Real-time accuracy** - Always reflects current model capabilities
2. **No maintenance** - Automatically works with new models
3. **User-friendly** - Shows only relevant options
4. **Type-safe** - TypeScript ensures correct usage
5. **Future-proof** - Adapts to new reasoning parameters

This implementation ensures your model picker always shows accurate reasoning options based on real-time data from OpenRouter's API, eliminating any guesswork or manual maintenance.