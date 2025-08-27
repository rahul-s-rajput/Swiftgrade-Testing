# OpenRouter Model Picker Implementation Plan (Dropdown Version)

## Overview
Build an enhanced dropdown multi-select component for selecting OpenRouter models with inline reasoning configuration, integrated seamlessly into the existing assessment application UI.

## Core Features
1. **Dynamic Model Loading**: Fetch models from OpenRouter API and populate dropdown
2. **Dropdown Multi-Selection**: Use existing MultiSelect pattern with enhancements
3. **Inline Reasoning Configuration**: Configure reasoning for each selected model
4. **Real-time Search**: Filter models within dropdown
5. **Model Variants**: Support multiple configurations of the same model
6. **Persistent Selection**: Maintain selected models with their configurations

## Technical Architecture

### Component Enhancement Strategy
Instead of creating a new modal component, we'll enhance the existing `MultiSelect` component and create a new `OpenRouterModelSelect` component that extends it with OpenRouter-specific features.

### Data Structures

```typescript
// Extend existing AIModel type
export interface OpenRouterModel extends AIModel {
  id: string;
  name: string;
  provider: string;
  context_length: number;
  pricing: {
    prompt: string;
    completion: string;
    image?: string;
    request?: string;
  };
  architecture?: {
    modality?: string;
    tokenizer?: string;
    instruct_type?: string;
  };
  supportsReasoning?: boolean;
}

// Model configuration with reasoning
export interface ConfiguredModel {
  modelId: string;
  variantId: string;
  displayName: string;
  reasoningType: 'none' | 'low' | 'medium' | 'high' | 'custom';
  reasoningTokens?: number;
  reasoningConfig?: {
    effort?: 'low' | 'medium' | 'high';
    max_tokens?: number;
    include_reasoning?: boolean;
  };
}
```

## Component Structure

### Enhanced Component Hierarchy
```
src/components/
├── OpenRouterModelSelect/
│   ├── index.tsx                      # Main export
│   ├── OpenRouterModelSelect.tsx      # Main component
│   ├── ModelOptionItem.tsx            # Individual model in dropdown
│   ├── SelectedModelChip.tsx          # Selected model display with config
│   ├── ReasoningConfigPopover.tsx     # Inline reasoning configuration
│   ├── hooks/
│   │   ├── useOpenRouterModels.ts     # Fetch and cache models
│   │   └── useModelConfiguration.ts   # Handle model configs
│   └── utils/
│       ├── modelHelpers.ts            # Model data utilities
│       └── reasoningHelpers.ts        # Reasoning config helpers
```

## UI/UX Design

### Dropdown Layout
```
┌─────────────────────────────────────────────────┐
│ Select AI Models                                 │
│                                                   │
│ [Selected Model Chips with Reasoning Badges]     │
│ ┌──────────────────┐ ┌──────────────────┐       │
│ │ GPT-4o [Medium] × │ │ Claude-3.5 [High] × │    │
│ └──────────────────┘ └──────────────────┘       │
│                                                   │
│ ┌─────────────────────────────────────────────┐ │
│ │ 🔍 Search models...              ▼          │ │
│ └─────────────────────────────────────────────┘ │
│   ┌───────────────────────────────────────┐     │
│   │ □ GPT-4 Optimized                     │     │
│   │   OpenAI • $0.005/1K • 128K context   │     │
│   │   [Standard] [+Low] [+Med] [+High]    │     │
│   ├───────────────────────────────────────┤     │
│   │ ✓ Claude 3.5 Sonnet                   │     │
│   │   Anthropic • $0.003/1K • 200K        │     │
│   │   [Standard] [+Low] [+Med] [+High]    │     │
│   └───────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

### Selected Model Chip Design
```
┌────────────────────────┐
│ Model Name             │
│ [Reasoning: Medium] ⚙️  │  <- Click gear for config
│                     ×  │  <- Remove
└────────────────────────┘
```

### Inline Reasoning Configuration (Popover)
```
┌──────────────────────────┐
│ Configure Reasoning      │
│                          │
│ ○ None (Standard)        │
│ ○ Low (20% tokens)       │
│ ● Medium (50% tokens)    │
│ ○ High (80% tokens)      │
│ ○ Custom: [____] tokens  │
│                          │
│ [Cancel] [Apply]         │
└──────────────────────────┘
```

## Implementation Approach

### Phase 1: Enhance Model Data Fetching
```typescript
// useOpenRouterModels.ts
export const useOpenRouterModels = () => {
  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModels = async () => {
      setLoading(true);
      try {
        // Check cache first
        const cached = localStorage.getItem('openrouter_models');
        const cacheTime = localStorage.getItem('openrouter_models_time');
        
        if (cached && cacheTime && Date.now() - parseInt(cacheTime) < 3600000) {
          setModels(JSON.parse(cached));
          setLoading(false);
          return;
        }

        // Fetch from API
        const response = await fetch('https://openrouter.ai/api/v1/models');
        const data = await response.json();
        
        // Transform to our format
        const transformedModels = data.data.map(transformModel);
        
        // Cache the results
        localStorage.setItem('openrouter_models', JSON.stringify(transformedModels));
        localStorage.setItem('openrouter_models_time', Date.now().toString());
        
        setModels(transformedModels);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, []);

  return { models, loading, error };
};
```

### Phase 2: Enhanced Dropdown Component
```typescript
// OpenRouterModelSelect.tsx
export const OpenRouterModelSelect: React.FC<Props> = ({
  selectedModels,
  onChange,
  ...props
}) => {
  const { models, loading, error } = useOpenRouterModels();
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [configuringModel, setConfiguringModel] = useState<string | null>(null);

  const handleAddVariant = (modelId: string, reasoning: ReasoningType) => {
    const model = models.find(m => m.id === modelId);
    if (!model) return;

    const variant: ConfiguredModel = {
      modelId,
      variantId: `${modelId}_${reasoning}_${Date.now()}`,
      displayName: `${model.name} (${reasoning})`,
      reasoningType: reasoning,
      reasoningConfig: getReasoningConfig(reasoning)
    };

    onChange([...selectedModels, variant]);
  };

  const handleRemoveModel = (variantId: string) => {
    onChange(selectedModels.filter(m => m.variantId !== variantId));
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Select AI Models for Testing
      </label>

      {/* Selected Models Display */}
      <div className="flex flex-wrap gap-2">
        {selectedModels.map(model => (
          <SelectedModelChip
            key={model.variantId}
            model={model}
            onRemove={handleRemoveModel}
            onConfigure={() => setConfiguringModel(model.variantId)}
          />
        ))}
      </div>

      {/* Dropdown */}
      <div className="relative">
        <button onClick={() => setIsOpen(!isOpen)} className="dropdown-trigger">
          <span>{selectedModels.length} models selected</span>
          <ChevronDown />
        </button>

        {isOpen && (
          <div className="dropdown-content">
            {/* Search */}
            <input
              type="text"
              placeholder="Search models..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />

            {/* Model List */}
            <div className="model-list">
              {filteredModels.map(model => (
                <ModelOptionItem
                  key={model.id}
                  model={model}
                  selectedVariants={selectedModels.filter(m => m.modelId === model.id)}
                  onAddVariant={handleAddVariant}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Reasoning Config Popover */}
      {configuringModel && (
        <ReasoningConfigPopover
          model={selectedModels.find(m => m.variantId === configuringModel)}
          onSave={(config) => {
            // Update model config
            const updated = selectedModels.map(m => 
              m.variantId === configuringModel 
                ? { ...m, ...config }
                : m
            );
            onChange(updated);
            setConfiguringModel(null);
          }}
          onClose={() => setConfiguringModel(null)}
        />
      )}
    </div>
  );
};
```

### Phase 3: Model Option Item Component
```typescript
// ModelOptionItem.tsx
export const ModelOptionItem: React.FC<Props> = ({
  model,
  selectedVariants,
  onAddVariant
}) => {
  const hasStandard = selectedVariants.some(v => v.reasoningType === 'none');
  
  return (
    <div className="model-option">
      <div className="model-info">
        <div className="model-name">{model.name}</div>
        <div className="model-meta">
          {model.provider} • ${parseFloat(model.pricing.prompt) * 1000}/1K • {Math.round(model.context_length / 1000)}K
        </div>
      </div>
      
      <div className="model-actions">
        <button 
          className={`variant-btn ${hasStandard ? 'selected' : ''}`}
          onClick={() => onAddVariant(model.id, 'none')}
        >
          {hasStandard ? '✓' : '+'} Standard
        </button>
        
        {model.supportsReasoning && (
          <>
            <button 
              className="variant-btn mini"
              onClick={() => onAddVariant(model.id, 'low')}
            >
              +Low
            </button>
            <button 
              className="variant-btn mini"
              onClick={() => onAddVariant(model.id, 'medium')}
            >
              +Med
            </button>
            <button 
              className="variant-btn mini"
              onClick={() => onAddVariant(model.id, 'high')}
            >
              +High
            </button>
          </>
        )}
      </div>
    </div>
  );
};
```

## Key Differences from Modal Approach

### Advantages of Dropdown Approach:
1. **Consistent UI**: Matches existing app patterns
2. **Less Intrusive**: No modal overlay blocking the interface
3. **Quick Access**: Faster selection without opening/closing modals
4. **Inline Configuration**: Configure reasoning without leaving the form
5. **Better Mobile UX**: Dropdowns work better on mobile devices

### Technical Simplifications:
1. **No Modal State Management**: Simpler state handling
2. **Reuse Existing Components**: Extend MultiSelect component
3. **Smaller Bundle**: Less code than full modal implementation
4. **Easier Testing**: Simpler component hierarchy

## API Integration

### Using Selected Models with Reasoning
```typescript
const callOpenRouterWithModel = async (
  model: ConfiguredModel,
  prompt: string,
  apiKey: string
) => {
  const body: any = {
    model: model.modelId,
    messages: [{ role: 'user', content: prompt }],
  };

  // Apply reasoning configuration
  if (model.reasoningType !== 'none') {
    body.include_reasoning = true;
    
    if (model.reasoningConfig?.effort) {
      body.reasoning = { effort: model.reasoningConfig.effort };
    } else if (model.reasoningConfig?.max_tokens) {
      body.reasoning = { max_tokens: model.reasoningConfig.max_tokens };
    }
  }

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  return response.json();
};
```

## Implementation Timeline

### Week 1: Core Development
- **Day 1**: Set up data fetching and caching
- **Day 2**: Enhance dropdown with model display
- **Day 3**: Implement variant selection (reasoning levels)
- **Day 4**: Add inline configuration popovers
- **Day 5**: Integration and testing

### Week 2: Polish & Features
- **Day 6-7**: Performance optimization
- **Day 8-9**: Additional filters and sorting
- **Day 10**: Documentation and examples

## Performance Considerations

1. **Virtual Scrolling**: For dropdown with 200+ models
2. **Debounced Search**: 300ms delay on search input
3. **Lazy Loading**: Load model details on demand
4. **Memoization**: Cache filtered results
5. **Optimistic UI**: Immediate visual feedback

## Styling Approach

```css
/* Extend existing styles */
.model-option {
  padding: 8px 12px;
  border-bottom: 1px solid #e5e7eb;
}

.variant-btn {
  padding: 4px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
  margin-left: 4px;
}

.variant-btn.mini {
  padding: 2px 6px;
  font-size: 0.7rem;
}

.selected-model-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: #eff6ff;
  border: 1px solid #3b82f6;
  border-radius: 16px;
  font-size: 0.875rem;
}

.reasoning-badge {
  padding: 2px 6px;
  background: #6366f1;
  color: white;
  border-radius: 8px;
  font-size: 0.7rem;
  font-weight: 600;
}
```

## Testing Strategy

1. **Unit Tests**: Component logic and hooks
2. **Integration Tests**: Dropdown interactions
3. **E2E Tests**: Full selection flow
4. **Performance Tests**: With 200+ models
5. **Accessibility Tests**: Keyboard navigation

## Migration Path

1. **Keep existing MultiSelect**: For backward compatibility
2. **Create new OpenRouterModelSelect**: Specialized component
3. **Gradual adoption**: Replace in assessment form
4. **Feature flag**: Optional during transition

## Future Enhancements

1. **Favorites**: Star frequently used models
2. **Recent Models**: Show recently selected
3. **Model Groups**: Group by provider or capability
4. **Cost Calculator**: Inline cost estimation
5. **Model Comparison**: Quick compare in dropdown
6. **Presets**: Save model configurations
7. **Bulk Actions**: Apply reasoning to multiple models