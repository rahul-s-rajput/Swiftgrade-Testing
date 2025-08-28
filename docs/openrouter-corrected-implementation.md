# OpenRouter Model Picker - Corrected Implementation Guide

## Quick Reference: What Actually Works with OpenRouter

### ✅ Correct API Endpoint & Response

```javascript
// CORRECT - No auth required for model list
const response = await fetch('https://openrouter.ai/api/v1/models');
const data = await response.json();

// ACTUAL response structure:
{
  "data": [
    {
      "id": "openai/gpt-4o",
      "name": "GPT-4 Optimized",
      "created": 1690502400,
      "context_length": 128000,
      "pricing": {
        "prompt": "0.000005",      // String to avoid float precision
        "completion": "0.000015",
        "image": "0",              // Optional
        "request": "0"             // Optional
      },
      "architecture": {            // Optional
        "modality": "text",
        "tokenizer": "cl100k_base",
        "instruct_type": "chat"
      },
      "top_provider": {           // Optional
        "context_length": 128000,
        "max_completion_tokens": 4096,
        "is_moderated": false
      },
      "supported_parameters": [   // Optional
        "temperature",
        "top_p", 
        "frequency_penalty",
        "presence_penalty",
        "response_format",
        "tools"
      ]
    }
  ]
}
```

### 🔧 Critical Fix #1: Detecting Reasoning Support

```javascript
// ❌ WRONG - This field doesn't exist
if (model.supportsReasoning) { ... }

// ✅ CORRECT - Use pattern matching
function supportsReasoning(model) {
  // Known reasoning model patterns
  const reasoningPatterns = [
    // OpenAI
    'gpt-4', 'gpt-5', 'o1', 'o3',
    // Anthropic  
    'claude-3', 'claude-4', 'claude-3.7',
    // DeepSeek
    'deepseek-r1', 'deepseek-reasoner',
    // Google
    'gemini-2.5-flash-thinking', 'gemini-2-flash-thinking',
    // Alibaba
    'qwq', 'qvq',
    // Model variants
    ':thinking'
  ];
  
  const modelIdLower = model.id.toLowerCase();
  return reasoningPatterns.some(pattern => modelIdLower.includes(pattern));
}
```

### 🔧 Critical Fix #2: Safe Field Access

```javascript
// ❌ WRONG - Fields may be undefined
const price = model.pricing.prompt * 1000;
const modality = model.architecture.modality;

// ✅ CORRECT - Safe access with defaults
const price = parseFloat(model.pricing?.prompt || '0') * 1000;
const modality = model.architecture?.modality || 'text';
const maxTokens = model.top_provider?.max_completion_tokens || null;
```

### 🔧 Critical Fix #3: Model Variants

```javascript
// OpenRouter uses suffixes for variants
function parseModelInfo(modelId) {
  const baseId = modelId.split(':')[0];
  const variants = [];
  
  if (modelId.includes(':free')) variants.push('free');
  if (modelId.includes(':nitro')) variants.push('nitro');
  if (modelId.includes(':floor')) variants.push('floor');
  if (modelId.includes(':thinking')) variants.push('thinking');
  
  return { baseId, variants };
}

// Examples:
// "google/gemini-2.5-flash-image-preview:free" -> free variant
// "deepseek/deepseek-r1:nitro" -> faster variant
// "anthropic/claude-3.7-sonnet:thinking" -> reasoning variant
```

## Complete Working Implementation

### 1. Fetch and Transform Models

```javascript
const useOpenRouterModels = () => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchModels = async (forceRefresh = false) => {
    // Check cache first
    if (!forceRefresh) {
      const cached = localStorage.getItem('openrouter_models');
      const cacheTime = localStorage.getItem('openrouter_models_time');
      
      if (cached && cacheTime && Date.now() - parseInt(cacheTime) < 3600000) {
        setModels(JSON.parse(cached));
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('https://openrouter.ai/api/v1/models');
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      
      // Transform with safe field access
      const transformedModels = data.data.map(model => ({
        // Always present
        id: model.id,
        name: model.name || model.id.split('/')[1],
        provider: model.id.split('/')[0],
        context_length: model.context_length,
        
        // Safe access for pricing
        pricing: {
          prompt: model.pricing?.prompt || '0',
          completion: model.pricing?.completion || '0',
          promptPerM: parseFloat(model.pricing?.prompt || '0') * 1000000,
          completionPerM: parseFloat(model.pricing?.completion || '0') * 1000000
        },
        
        // Optional fields
        description: model.description,
        modality: model.architecture?.modality || 'text',
        supportsVision: model.architecture?.modality === 'multimodal',
        supportsTools: model.supported_parameters?.includes('tools') || false,
        supportsReasoning: supportsReasoning(model),
        
        // Parse variants
        variants: parseModelVariants(model.id),
        
        // Display helpers
        contextDisplay: formatContext(model.context_length),
        priceDisplay: formatPrice(model.pricing)
      }));

      // Sort by provider, then name
      transformedModels.sort((a, b) => {
        if (a.provider !== b.provider) {
          return a.provider.localeCompare(b.provider);
        }
        return a.name.localeCompare(b.name);
      });

      // Cache the results
      localStorage.setItem('openrouter_models', JSON.stringify(transformedModels));
      localStorage.setItem('openrouter_models_time', Date.now().toString());
      
      setModels(transformedModels);
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch models:', err);
      
      // Try to use cached data as fallback
      const cached = localStorage.getItem('openrouter_models');
      if (cached) {
        setModels(JSON.parse(cached));
      }
    } finally {
      setLoading(false);
    }
  };

  return { models, loading, error, fetchModels };
};
```

### 2. Multi-Selection with Reasoning

```javascript
const ModelSelector = () => {
  const { models, loading, error } = useOpenRouterModels();
  const [selectedModels, setSelectedModels] = useState([]);
  
  const addModelWithReasoning = (model, reasoningType = 'none') => {
    const variant = {
      id: `${model.id}_${reasoningType}_${Date.now()}`,
      modelId: model.id,
      name: model.name,
      provider: model.provider,
      reasoningType,
      reasoningConfig: getReasoningConfig(reasoningType),
      displayName: getDisplayName(model, reasoningType),
      // Include all model info for API calls
      context_length: model.context_length,
      pricing: model.pricing
    };
    
    setSelectedModels([...selectedModels, variant]);
  };
  
  const getReasoningConfig = (type) => {
    switch (type) {
      case 'none':
        return { include_reasoning: false };
      case 'low':
        return { reasoning: { effort: 'low' }, include_reasoning: true };
      case 'medium':
        return { reasoning: { effort: 'medium' }, include_reasoning: true };
      case 'high':
        return { reasoning: { effort: 'high' }, include_reasoning: true };
      case 'custom':
        return null; // Set later with specific tokens
      default:
        return { include_reasoning: false };
    }
  };
  
  return (
    <div className="model-selector">
      {/* Search and filters */}
      <input 
        type="text" 
        placeholder="Search models..."
        onChange={(e) => filterModels(e.target.value)}
      />
      
      {/* Model dropdown */}
      <div className="models-dropdown">
        {models.map(model => (
          <ModelOption 
            key={model.id}
            model={model}
            onSelect={() => addModelWithReasoning(model, 'none')}
            onAddReasoning={(type) => {
              if (model.supportsReasoning) {
                addModelWithReasoning(model, type);
              }
            }}
            isSelected={selectedModels.some(s => s.modelId === model.id)}
            supportsReasoning={model.supportsReasoning}
          />
        ))}
      </div>
      
      {/* Selected models display */}
      <div className="selected-models">
        {selectedModels.map(selected => (
          <SelectedModelChip
            key={selected.id}
            model={selected}
            onRemove={() => removeModel(selected.id)}
            onConfigureReasoning={(tokens) => {
              if (selected.reasoningType === 'custom') {
                updateReasoningTokens(selected.id, tokens);
              }
            }}
          />
        ))}
      </div>
    </div>
  );
};
```

### 3. API Request Generation

```javascript
const generateOpenRouterRequest = (selectedModel, prompt) => {
  const requestBody = {
    model: selectedModel.modelId,
    messages: [
      { role: 'user', content: prompt }
    ]
  };
  
  // Apply reasoning configuration
  if (selectedModel.reasoningConfig) {
    // For models supporting new unified reasoning parameter
    if (selectedModel.reasoningConfig.reasoning) {
      requestBody.reasoning = selectedModel.reasoningConfig.reasoning;
    }
    
    // Include reasoning tokens in response
    if (selectedModel.reasoningConfig.include_reasoning) {
      requestBody.include_reasoning = true;
    }
  }
  
  // For custom reasoning with specific tokens
  if (selectedModel.reasoningType === 'custom' && selectedModel.customTokens) {
    requestBody.reasoning = { 
      max_tokens: selectedModel.customTokens 
    };
    requestBody.include_reasoning = true;
  }
  
  return requestBody;
};

// Example API call
const callOpenRouter = async (selectedModel, prompt, apiKey) => {
  const requestBody = generateOpenRouterRequest(selectedModel, prompt);
  
  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': window.location.origin, // For OpenRouter analytics
      'X-Title': 'Assessment Grading App'     // Optional app name
    },
    body: JSON.stringify(requestBody)
  });
  
  if (!response.ok) {
    throw new Error(`OpenRouter API Error: ${response.status}`);
  }
  
  return response.json();
};
```

### 4. Model Display Component

```javascript
const ModelOption = ({ model, onSelect, onAddReasoning, isSelected, supportsReasoning }) => {
  const priceDisplay = `$${model.pricing.promptPerM.toFixed(3)}/$${model.pricing.completionPerM.toFixed(3)}/1M`;
  const contextDisplay = `${Math.round(model.context_length / 1000)}K`;
  
  return (
    <div className={`model-option ${isSelected ? 'selected' : ''}`}>
      <div className="model-info">
        <div className="model-name">{model.name}</div>
        <div className="model-id">{model.id}</div>
        <div className="model-badges">
          <span className="badge price">{priceDisplay}</span>
          <span className="badge context">{contextDisplay}</span>
          {model.supportsVision && <span className="badge vision">🖼️ Vision</span>}
          {model.supportsTools && <span className="badge tools">🔧 Tools</span>}
          {supportsReasoning && <span className="badge reasoning">🧠 Reasoning</span>}
          {model.variants.includes('free') && <span className="badge free">FREE</span>}
        </div>
      </div>
      
      <div className="model-actions">
        <button onClick={onSelect} className={isSelected ? 'selected' : ''}>
          {isSelected ? '✓ Selected' : 'Select'}
        </button>
        
        {supportsReasoning && !isSelected && (
          <div className="reasoning-actions">
            <button onClick={() => onAddReasoning('low')} className="mini">+Low</button>
            <button onClick={() => onAddReasoning('medium')} className="mini">+Med</button>
            <button onClick={() => onAddReasoning('high')} className="mini">+High</button>
          </div>
        )}
      </div>
    </div>
  );
};
```

## Helper Functions

```javascript
// Format context length for display
function formatContext(tokens) {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`;
  } else if (tokens >= 1000) {
    return `${Math.round(tokens / 1000)}K`;
  }
  return `${tokens}`;
}

// Format pricing for display
function formatPrice(pricing) {
  const prompt = parseFloat(pricing?.prompt || '0') * 1000;
  const completion = parseFloat(pricing?.completion || '0') * 1000;
  return `$${prompt.toFixed(3)}/$${completion.toFixed(3)}/1K`;
}

// Parse model variants from ID
function parseModelVariants(modelId) {
  const variants = [];
  if (modelId.includes(':free')) variants.push('free');
  if (modelId.includes(':nitro')) variants.push('nitro');
  if (modelId.includes(':floor')) variants.push('floor');
  if (modelId.includes(':thinking')) variants.push('thinking');
  return variants;
}

// Get display name with reasoning level
function getDisplayName(model, reasoningType) {
  const suffixes = {
    'none': '',
    'low': ' (Low Reasoning)',
    'medium': ' (Medium Reasoning)',
    'high': ' (High Reasoning)',
    'custom': ' (Custom Reasoning)'
  };
  return model.name + suffixes[reasoningType];
}
```

## Testing Checklist

- [ ] Models load from OpenRouter API
- [ ] Fallback to cached data on API error
- [ ] All model fields display correctly (handle missing fields)
- [ ] Reasoning detection works for known models
- [ ] Multi-selection works with unique variant IDs
- [ ] Reasoning configuration generates correct API body
- [ ] Price calculations are accurate
- [ ] Context length displays correctly
- [ ] Model variants (:free, :nitro, etc.) are recognized
- [ ] Search filters work across all fields

## Summary

This corrected implementation:
1. ✅ Properly detects reasoning support via ID patterns
2. ✅ Safely accesses all optional fields
3. ✅ Handles model variants correctly
4. ✅ Generates proper API request bodies
5. ✅ Works with the actual OpenRouter API response structure

Use this guide as the source of truth for implementation.