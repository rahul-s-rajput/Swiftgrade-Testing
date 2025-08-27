# OpenRouter Model Picker Implementation Plan

## Overview
Build a comprehensive React component for selecting multiple AI models from the OpenRouter catalog with support for different reasoning capabilities and real-time filtering.

## Core Features
1. **Dynamic Model Loading**: Fetch and display all available models from OpenRouter API
2. **Multi-Selection**: Allow selecting multiple models simultaneously
3. **Reasoning Variants**: Enable selection of same model with different reasoning capabilities
4. **Advanced Filtering**: Filter by provider, price, capabilities, and model name
5. **Visual Indicators**: Show model capabilities, pricing, and status
6. **Persistent Selection**: Maintain selected models state for API calls

## Technical Architecture

### API Integration
- **Endpoint**: `https://openrouter.ai/api/v1/models`
- **No authentication required** for fetching model list
- **Caching**: Store model data locally to avoid repeated API calls
- **Real-time updates**: Option to refresh model list

### Data Structures

```typescript
// OpenRouter Model Response
interface OpenRouterModel {
  id: string;                    // e.g., "openai/gpt-4o"
  name: string;                   // Display name
  description?: string;           // Model description
  context_length: number;         // Max context tokens
  pricing: {
    prompt: string;             // Cost per token (as string)
    completion: string;         // Cost per token (as string)
    image?: string;             // Cost per image (if applicable)
    request?: string;           // Cost per request (if applicable)
  };
  top_provider?: {
    context_length?: number;
    max_completion_tokens?: number;
    is_moderated?: boolean;
  };
  per_request_limits?: {
    prompt_tokens?: string;
    completion_tokens?: string;
  };
  architecture?: {
    modality?: string;          // "text", "multimodal", etc.
    tokenizer?: string;
    instruct_type?: string;
  };
  supported_parameters?: string[]; // Available parameters
}

// Enhanced Model Selection with Reasoning
interface SelectedModel {
  id: string;                   // Base model ID
  displayName: string;          // Custom display name
  reasoningType: 'none' | 'low' | 'medium' | 'high' | 'custom';
  reasoningConfig?: {
    effort?: 'low' | 'medium' | 'high';
    max_tokens?: number;        // For custom reasoning
    include_reasoning?: boolean;
  };
  provider?: string;            // Optional provider preference
  customSettings?: {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
  };
  variantId?: string;           // Unique ID for this variant
}
```

## Component Structure

### 1. Main Component: `OpenRouterModelPicker`
```
OpenRouterModelPicker/
├── index.tsx                   # Main component
├── OpenRouterModelPicker.tsx   # Core logic
├── styles.module.css          # Component styles
├── hooks/
│   ├── useModelFetch.ts      # Fetch and cache models
│   ├── useModelFilter.ts     # Filtering logic
│   └── useModelSelection.ts  # Selection management
├── components/
│   ├── ModelCard.tsx          # Individual model display
│   ├── ModelFilters.tsx       # Filter controls
│   ├── ReasoningSelector.tsx  # Reasoning type selector
│   ├── SelectedModelsList.tsx # Display selected models
│   └── ModelSearchBar.tsx     # Search input
├── utils/
│   ├── modelUtils.ts          # Model data utilities
│   ├── reasoningUtils.ts      # Reasoning config helpers
│   └── pricingUtils.ts        # Price formatting
└── types/
    └── openrouter.ts          # TypeScript definitions

### 2. Key Features Implementation

#### Model Fetching & Caching
```typescript
// useModelFetch.ts
const useModelFetch = () => {
  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);

  const fetchModels = async (forceRefresh = false) => {
    // Check cache first (localStorage)
    const cached = getCachedModels();
    if (!forceRefresh && cached && !isStale(cached.timestamp)) {
      setModels(cached.data);
      return;
    }

    try {
      const response = await fetch('https://openrouter.ai/api/v1/models');
      const data = await response.json();
      
      // Transform and enhance model data
      const enhancedModels = data.data.map(enhanceModelData);
      
      // Cache the results
      setCachedModels(enhancedModels);
      setModels(enhancedModels);
    } catch (err) {
      setError(err.message);
    }
  };

  return { models, loading, error, fetchModels };
};
```

#### Multi-Selection with Reasoning Variants
```typescript
// useModelSelection.ts
const useModelSelection = () => {
  const [selectedModels, setSelectedModels] = useState<SelectedModel[]>([]);

  const addModelVariant = (baseModel: OpenRouterModel, reasoning: ReasoningConfig) => {
    const variant: SelectedModel = {
      id: baseModel.id,
      displayName: generateDisplayName(baseModel, reasoning),
      reasoningType: reasoning.type,
      reasoningConfig: reasoning.config,
      variantId: generateVariantId(baseModel.id, reasoning),
    };
    
    // Check if this exact variant already exists
    if (!variantExists(selectedModels, variant)) {
      setSelectedModels([...selectedModels, variant]);
    }
  };

  const removeModelVariant = (variantId: string) => {
    setSelectedModels(selectedModels.filter(m => m.variantId !== variantId));
  };

  return { selectedModels, addModelVariant, removeModelVariant };
};
```

#### Reasoning Configuration
```typescript
// ReasoningSelector component
interface ReasoningConfig {
  type: 'none' | 'low' | 'medium' | 'high' | 'custom';
  config?: {
    effort?: string;
    max_tokens?: number;
    include_reasoning?: boolean;
  };
}

const reasoningPresets = {
  none: { include_reasoning: false },
  low: { effort: 'low', include_reasoning: true },
  medium: { effort: 'medium', include_reasoning: true },
  high: { effort: 'high', include_reasoning: true },
  custom: null, // User defines
};
```

## UI/UX Design

### Layout Structure
```
┌─────────────────────────────────────────────────────────┐
│  OpenRouter Model Picker                          [X]   │
├─────────────────────────────────────────────────────────┤
│  🔍 [Search models...]                [Refresh] [Clear]  │
├─────────────────────────────────────────────────────────┤
│  Filters:                                               │
│  Provider: [All ▼]  Max Price: [$0.01 ▼]  Features: [] │
│  Context: [Any ▼]   Modality: [Text ▼]                 │
├─────────────────────────────────────────────────────────┤
│  Available Models (247)        Selected Models (5)      │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │ Model Card       │         │ gpt-4o (medium)  │     │
│  │ ◯ Select         │         │ claude-3.5 (high)│     │
│  │ + Add Variant    │         │ deepseek-r1 (low)│     │
│  └──────────────────┘         └──────────────────┘     │
├─────────────────────────────────────────────────────────┤
│                              [Cancel] [Apply Selection]  │
└─────────────────────────────────────────────────────────┘
```

### Model Card Design
```
┌────────────────────────────────────────┐
│ ◯ openai/gpt-4o                       │
│ GPT-4 Optimized                       │
│                                        │
│ 💰 $0.005/$0.015 per 1K tokens        │
│ 📝 128K context                       │
│ 🖼️ Vision support                     │
│ 🧠 Reasoning capable                  │
│                                        │
│ [Select] [+ Add Variant]              │
└────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Model Fetching (Day 1)
- Set up component structure
- Implement model fetching from OpenRouter API
- Add caching mechanism
- Create basic model display

### Phase 2: Filtering & Search (Day 2)
- Implement search functionality
- Add provider filtering
- Add price range filtering
- Add capability filters

### Phase 3: Multi-Selection (Day 3)
- Implement basic multi-selection
- Add selected models management
- Create selection persistence

### Phase 4: Reasoning Variants (Day 4)
- Add reasoning type selector
- Implement variant creation
- Add custom reasoning configuration
- Create variant display

### Phase 5: Polish & Integration (Day 5)
- Add loading states
- Implement error handling
- Create export functionality
- Integrate with main app

## API Integration Examples

### Using Selected Models
```typescript
// Example: Making API calls with selected models
const makeOpenRouterCall = async (selectedModel: SelectedModel, prompt: string) => {
  const body = {
    model: selectedModel.id,
    messages: [{ role: 'user', content: prompt }],
    ...selectedModel.customSettings,
  };

  // Add reasoning configuration if applicable
  if (selectedModel.reasoningType !== 'none') {
    if (selectedModel.reasoningConfig?.effort) {
      body.reasoning = {
        effort: selectedModel.reasoningConfig.effort
      };
    } else if (selectedModel.reasoningConfig?.max_tokens) {
      body.reasoning = {
        max_tokens: selectedModel.reasoningConfig.max_tokens
      };
    }
    
    body.include_reasoning = selectedModel.reasoningConfig?.include_reasoning ?? true;
  }

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body)
  });

  return response.json();
};
```

## Dependencies

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "lucide-react": "^0.344.0",
    "clsx": "^2.1.0",
    "@tanstack/react-query": "^5.20.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.5"
  }
}
```

## Testing Strategy

### Unit Tests
- Model filtering logic
- Reasoning configuration generation
- Variant ID generation
- Price calculations

### Integration Tests
- API fetching with mock data
- Selection persistence
- Export functionality

### E2E Tests
- Full selection flow
- Filter combinations
- Variant creation

## Performance Optimizations

1. **Virtual Scrolling**: For large model lists (200+ models)
2. **Debounced Search**: 300ms debounce on search input
3. **Lazy Loading**: Load model details on demand
4. **Memoization**: Cache filtered results
5. **Request Batching**: Batch variant creation

## Error Handling

```typescript
type ErrorState = {
  type: 'fetch' | 'selection' | 'validation';
  message: string;
  retry?: () => void;
};

// Graceful degradation
- Fallback to cached models if API fails
- Allow manual model ID input if list unavailable
- Validate model selections before submission
```

## Accessibility

- Keyboard navigation (Tab, Arrow keys, Enter, Space)
- Screen reader support with ARIA labels
- Focus management in modal
- High contrast mode support
- Reduced motion support

## Future Enhancements

1. **Model Comparison**: Side-by-side model comparison
2. **Favorites**: Save frequently used models
3. **Presets**: Save selection configurations
4. **Cost Calculator**: Estimate costs based on usage
5. **Model Recommendations**: AI-powered suggestions
6. **Provider Statistics**: Show uptime and performance
7. **A/B Testing**: Built-in variant testing
8. **Export/Import**: Share configurations