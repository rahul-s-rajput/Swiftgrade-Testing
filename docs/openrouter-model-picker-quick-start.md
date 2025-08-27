# OpenRouter Model Picker - Quick Start Implementation Guide

## 1. Initial Setup

### Install Dependencies
```bash
npm install clsx @tanstack/react-query
```

## 2. Type Definitions

Create `src/types/openrouter.ts`:

```typescript
// OpenRouter Model Types
export interface OpenRouterModel {
  id: string;
  name: string;
  description?: string;
  created?: number;
  context_length: number;
  architecture?: {
    modality?: string;
    tokenizer?: string;
    instruct_type?: string;
  };
  pricing: {
    prompt: string;      // Price per token as string
    completion: string;
    image?: string;
    request?: string;
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
}

export interface OpenRouterModelsResponse {
  data: OpenRouterModel[];
}

// Selected Model with Reasoning
export interface SelectedModel {
  id: string;
  baseModelId: string;
  displayName: string;
  reasoningType: ReasoningType;
  reasoningConfig?: ReasoningConfig;
  provider?: string;
  customSettings?: ModelSettings;
  variantId: string;
}

export type ReasoningType = 'none' | 'low' | 'medium' | 'high' | 'custom';

export interface ReasoningConfig {
  effort?: 'low' | 'medium' | 'high';
  max_tokens?: number;
  include_reasoning?: boolean;
}

export interface ModelSettings {
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export interface ModelFilters {
  search: string;
  provider?: string;
  maxPrice?: number;
  minContext?: number;
  capabilities?: string[];
  modality?: string;
}
```

## 3. Core Hooks

### Model Fetching Hook

Create `src/components/OpenRouterModelPicker/hooks/useModelFetch.ts`:

```typescript
import { useState, useEffect, useCallback } from 'react';
import type { OpenRouterModel, OpenRouterModelsResponse } from '../../../types/openrouter';

const CACHE_KEY = 'openrouter_models_cache';
const CACHE_TTL = 3600000; // 1 hour in milliseconds

interface CachedData {
  data: OpenRouterModel[];
  timestamp: number;
}

export const useModelFetch = () => {
  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getCachedModels = (): CachedData | null => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        return JSON.parse(cached);
      }
    } catch (err) {
      console.error('Error reading cache:', err);
    }
    return null;
  };

  const setCachedModels = (data: OpenRouterModel[]) => {
    try {
      const cacheData: CachedData = {
        data,
        timestamp: Date.now(),
      };
      localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
    } catch (err) {
      console.error('Error setting cache:', err);
    }
  };

  const isStale = (timestamp: number): boolean => {
    return Date.now() - timestamp > CACHE_TTL;
  };

  const fetchModels = useCallback(async (forceRefresh = false) => {
    // Check cache first
    if (!forceRefresh) {
      const cached = getCachedModels();
      if (cached && !isStale(cached.timestamp)) {
        setModels(cached.data);
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('https://openrouter.ai/api/v1/models');
      
      if (!response.ok) {
        throw new Error(`Failed to fetch models: ${response.statusText}`);
      }

      const data: OpenRouterModelsResponse = await response.json();
      
      // Sort models by provider and name
      const sortedModels = data.data.sort((a, b) => {
        const providerA = a.id.split('/')[0];
        const providerB = b.id.split('/')[0];
        if (providerA !== providerB) {
          return providerA.localeCompare(providerB);
        }
        return a.name.localeCompare(b.name);
      });

      setModels(sortedModels);
      setCachedModels(sortedModels);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch models');
      
      // Try to use cached data as fallback
      const cached = getCachedModels();
      if (cached) {
        setModels(cached.data);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  return { models, loading, error, refetch: fetchModels };
};
```

### Model Selection Hook

Create `src/components/OpenRouterModelPicker/hooks/useModelSelection.ts`:

```typescript
import { useState, useCallback } from 'react';
import type { OpenRouterModel, SelectedModel, ReasoningType, ReasoningConfig } from '../../../types/openrouter';

export const useModelSelection = () => {
  const [selectedModels, setSelectedModels] = useState<SelectedModel[]>([]);

  const generateVariantId = (modelId: string, reasoningType: ReasoningType, timestamp?: number): string => {
    return `${modelId}_${reasoningType}_${timestamp || Date.now()}`;
  };

  const generateDisplayName = (model: OpenRouterModel, reasoningType: ReasoningType): string => {
    if (reasoningType === 'none') {
      return model.name;
    }
    return `${model.name} (${reasoningType} reasoning)`;
  };

  const getReasoningConfig = (reasoningType: ReasoningType, maxTokens?: number): ReasoningConfig | undefined => {
    switch (reasoningType) {
      case 'none':
        return { include_reasoning: false };
      case 'low':
        return { effort: 'low', include_reasoning: true };
      case 'medium':
        return { effort: 'medium', include_reasoning: true };
      case 'high':
        return { effort: 'high', include_reasoning: true };
      case 'custom':
        return maxTokens ? { max_tokens: maxTokens, include_reasoning: true } : undefined;
      default:
        return undefined;
    }
  };

  const addModelVariant = useCallback((
    model: OpenRouterModel,
    reasoningType: ReasoningType,
    customMaxTokens?: number
  ) => {
    const variantId = generateVariantId(model.id, reasoningType);
    const displayName = generateDisplayName(model, reasoningType);
    const reasoningConfig = getReasoningConfig(reasoningType, customMaxTokens);

    const newVariant: SelectedModel = {
      id: model.id,
      baseModelId: model.id,
      displayName,
      reasoningType,
      reasoningConfig,
      variantId,
    };

    // Check if this exact variant already exists
    const exists = selectedModels.some(
      m => m.baseModelId === model.id && m.reasoningType === reasoningType
    );

    if (!exists) {
      setSelectedModels(prev => [...prev, newVariant]);
      return true;
    }
    return false;
  }, [selectedModels]);

  const removeModelVariant = useCallback((variantId: string) => {
    setSelectedModels(prev => prev.filter(m => m.variantId !== variantId));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedModels([]);
  }, []);

  const toggleModel = useCallback((model: OpenRouterModel) => {
    const defaultVariant = selectedModels.find(
      m => m.baseModelId === model.id && m.reasoningType === 'none'
    );

    if (defaultVariant) {
      removeModelVariant(defaultVariant.variantId);
    } else {
      addModelVariant(model, 'none');
    }
  }, [selectedModels, addModelVariant, removeModelVariant]);

  const isModelSelected = useCallback((modelId: string): boolean => {
    return selectedModels.some(m => m.baseModelId === modelId);
  }, [selectedModels]);

  return {
    selectedModels,
    addModelVariant,
    removeModelVariant,
    clearSelection,
    toggleModel,
    isModelSelected,
  };
};
```

### Model Filtering Hook

Create `src/components/OpenRouterModelPicker/hooks/useModelFilter.ts`:

```typescript
import { useMemo, useState } from 'react';
import type { OpenRouterModel, ModelFilters } from '../../../types/openrouter';

export const useModelFilter = (models: OpenRouterModel[]) => {
  const [filters, setFilters] = useState<ModelFilters>({
    search: '',
    provider: undefined,
    maxPrice: undefined,
    minContext: undefined,
    capabilities: [],
    modality: undefined,
  });

  const providers = useMemo(() => {
    const uniqueProviders = new Set<string>();
    models.forEach(model => {
      const provider = model.id.split('/')[0];
      uniqueProviders.add(provider);
    });
    return Array.from(uniqueProviders).sort();
  }, [models]);

  const filteredModels = useMemo(() => {
    return models.filter(model => {
      // Search filter
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        const matchesSearch = 
          model.name.toLowerCase().includes(searchLower) ||
          model.id.toLowerCase().includes(searchLower) ||
          (model.description?.toLowerCase().includes(searchLower) ?? false);
        
        if (!matchesSearch) return false;
      }

      // Provider filter
      if (filters.provider) {
        const provider = model.id.split('/')[0];
        if (provider !== filters.provider) return false;
      }

      // Price filter
      if (filters.maxPrice !== undefined) {
        const promptPrice = parseFloat(model.pricing.prompt) * 1000000; // Convert to price per 1M tokens
        const completionPrice = parseFloat(model.pricing.completion) * 1000000;
        if (promptPrice > filters.maxPrice || completionPrice > filters.maxPrice) {
          return false;
        }
      }

      // Context length filter
      if (filters.minContext !== undefined) {
        if (model.context_length < filters.minContext) return false;
      }

      // Modality filter
      if (filters.modality) {
        if (model.architecture?.modality !== filters.modality) return false;
      }

      return true;
    });
  }, [models, filters]);

  const updateFilter = <K extends keyof ModelFilters>(
    key: K,
    value: ModelFilters[K]
  ) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }));
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      provider: undefined,
      maxPrice: undefined,
      minContext: undefined,
      capabilities: [],
      modality: undefined,
    });
  };

  return {
    filters,
    filteredModels,
    providers,
    updateFilter,
    clearFilters,
  };
};
```

## 4. Main Component

Create `src/components/OpenRouterModelPicker/OpenRouterModelPicker.tsx`:

```typescript
import React, { useState } from 'react';
import { X, Search, RefreshCw, Check } from 'lucide-react';
import { useModelFetch } from './hooks/useModelFetch';
import { useModelSelection } from './hooks/useModelSelection';
import { useModelFilter } from './hooks/useModelFilter';
import ModelCard from './components/ModelCard';
import ModelFilters from './components/ModelFilters';
import SelectedModelsList from './components/SelectedModelsList';
import type { SelectedModel } from '../../types/openrouter';

interface OpenRouterModelPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectionComplete: (models: SelectedModel[]) => void;
  initialSelection?: SelectedModel[];
}

export const OpenRouterModelPicker: React.FC<OpenRouterModelPickerProps> = ({
  isOpen,
  onClose,
  onSelectionComplete,
  initialSelection = [],
}) => {
  const { models, loading, error, refetch } = useModelFetch();
  const {
    selectedModels,
    addModelVariant,
    removeModelVariant,
    clearSelection,
    toggleModel,
    isModelSelected,
  } = useModelSelection();
  
  const {
    filters,
    filteredModels,
    providers,
    updateFilter,
    clearFilters,
  } = useModelFilter(models);

  const [showReasoningModal, setShowReasoningModal] = useState(false);
  const [selectedModelForReasoning, setSelectedModelForReasoning] = useState<any>(null);

  const handleApplySelection = () => {
    onSelectionComplete(selectedModels);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">OpenRouter Model Picker</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-4 border-b">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search models..."
                value={filters.search}
                onChange={(e) => updateFilter('search', e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              onClick={() => refetch(true)}
              disabled={loading}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={clearFilters}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              Clear Filters
            </button>
          </div>
        </div>

        {/* Filters */}
        <ModelFilters
          filters={filters}
          providers={providers}
          onUpdateFilter={updateFilter}
        />

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Models List */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="mb-2 text-sm text-gray-600">
              Available Models ({filteredModels.length})
            </div>
            
            {error && (
              <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-4">
                {error}
              </div>
            )}

            {loading && (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredModels.map(model => (
                <ModelCard
                  key={model.id}
                  model={model}
                  isSelected={isModelSelected(model.id)}
                  onToggleSelect={() => toggleModel(model)}
                  onAddVariant={(reasoningType, maxTokens) => 
                    addModelVariant(model, reasoningType, maxTokens)
                  }
                />
              ))}
            </div>
          </div>

          {/* Selected Models */}
          <div className="w-80 border-l bg-gray-50 p-4 overflow-y-auto">
            <div className="mb-2 text-sm text-gray-600">
              Selected Models ({selectedModels.length})
            </div>
            <SelectedModelsList
              selectedModels={selectedModels}
              onRemove={removeModelVariant}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t flex justify-between">
          <button
            onClick={clearSelection}
            className="px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            Clear Selection
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleApplySelection}
              disabled={selectedModels.length === 0}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Apply Selection ({selectedModels.length})
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OpenRouterModelPicker;
```

## 5. Usage Example

Update your main app to use the picker:

```typescript
import React, { useState } from 'react';
import OpenRouterModelPicker from './components/OpenRouterModelPicker/OpenRouterModelPicker';
import type { SelectedModel } from './types/openrouter';

function App() {
  const [showPicker, setShowPicker] = useState(false);
  const [selectedModels, setSelectedModels] = useState<SelectedModel[]>([]);

  const handleSelectionComplete = (models: SelectedModel[]) => {
    setSelectedModels(models);
    console.log('Selected models:', models);
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">OpenRouter Model Selection Demo</h1>
      
      <button
        onClick={() => setShowPicker(true)}
        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
      >
        Select Models ({selectedModels.length} selected)
      </button>

      {selectedModels.length > 0 && (
        <div className="mt-4">
          <h2 className="font-semibold mb-2">Selected Models:</h2>
          <ul className="space-y-1">
            {selectedModels.map(model => (
              <li key={model.variantId} className="text-sm">
                {model.displayName}
              </li>
            ))}
          </ul>
        </div>
      )}

      <OpenRouterModelPicker
        isOpen={showPicker}
        onClose={() => setShowPicker(false)}
        onSelectionComplete={handleSelectionComplete}
        initialSelection={selectedModels}
      />
    </div>
  );
}

export default App;
```

## 6. Next Steps

1. **Create Sub-Components**: Build ModelCard, ModelFilters, and SelectedModelsList components
2. **Add Styling**: Enhance with Tailwind CSS classes
3. **Add Reasoning Modal**: Create UI for configuring reasoning levels
4. **Add Persistence**: Save selections to localStorage
5. **Add Export**: Create export functionality for selected models
6. **Testing**: Add unit tests for hooks and components
7. **Documentation**: Create comprehensive API documentation

## 7. API Integration

When using the selected models with OpenRouter API:

```typescript
const callOpenRouter = async (model: SelectedModel, prompt: string) => {
  const body: any = {
    model: model.id,
    messages: [{ role: 'user', content: prompt }],
  };

  // Add reasoning configuration
  if (model.reasoningConfig) {
    if (model.reasoningConfig.effort) {
      body.reasoning = { effort: model.reasoningConfig.effort };
    } else if (model.reasoningConfig.max_tokens) {
      body.reasoning = { max_tokens: model.reasoningConfig.max_tokens };
    }
    body.include_reasoning = model.reasoningConfig.include_reasoning;
  }

  // Add custom settings
  if (model.customSettings) {
    Object.assign(body, model.customSettings);
  }

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  return response.json();
};
```

This guide provides a solid foundation to start building the OpenRouter Model Picker component. Follow the implementation plan and user stories for complete feature development.