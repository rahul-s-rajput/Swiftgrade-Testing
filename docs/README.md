# OpenRouter Model Picker Documentation

## Overview
This directory contains comprehensive documentation for implementing an OpenRouter model selector with multi-selection and reasoning configuration capabilities. Two implementation approaches are documented to suit different UI preferences.

## Implementation Approaches

### 🎯 Approach 1: Dropdown Multi-Select (Recommended)
A seamless integration with the existing form UI using an enhanced dropdown selector.

**Documents:**
- [Dropdown Implementation Plan](./openrouter-dropdown-implementation-plan.md)
- [Dropdown User Stories](./openrouter-dropdown-user-stories.md)

**Key Features:**
- Integrates with existing MultiSelect component pattern
- Inline reasoning configuration via popover
- Quick variant selection buttons
- Selected models shown as chips
- No modal overlay - stays in form context
- Mobile-friendly dropdown interface

### 🔲 Approach 2: Modal Picker (Alternative)
A comprehensive modal-based picker for scenarios requiring more screen space.

**Documents:**
- [Modal Implementation Plan](./openrouter-model-picker-implementation-plan.md)
- [Modal User Stories](./openrouter-model-picker-user-stories.md)
- [Interactive Prototype](./openrouter-model-picker-prototype.html)

**Key Features:**
- Full-screen modal with advanced filtering
- Visual model cards with detailed information
- Dedicated selected models panel
- More space for model details
- Advanced filtering options

## Quick Reference

### Component Structure (Dropdown Version)
```
OpenRouterModelSelect/
├── OpenRouterModelSelect.tsx      # Main dropdown component
├── ModelOptionItem.tsx            # Model display in dropdown
├── SelectedModelChip.tsx          # Selected model chips
├── ReasoningConfigPopover.tsx     # Inline configuration
└── hooks/
    ├── useOpenRouterModels.ts     # Fetch & cache models
    └── useModelConfiguration.ts   # Handle configurations
```

### Data Flow
```
OpenRouter API → Cache → Dropdown → Selection → Chips → Form State
                  ↑                      ↓
              User Search            Configuration
```

### Key Features Comparison

| Feature | Dropdown | Modal |
|---------|----------|--------|
| Screen Space | Compact | Full screen |
| User Context | Stays in form | Overlay |
| Mobile UX | Native dropdown | Custom modal |
| Model Details | Inline summary | Full cards |
| Filtering | Basic search | Advanced filters |
| Selection Speed | Quick buttons | Click cards |
| Implementation | Extends existing | New component |

## Core Features (Both Approaches)

✅ **Dynamic Model Loading** - Fetch from OpenRouter API with caching  
✅ **Multi-Selection** - Select multiple models and variants  
✅ **Reasoning Configuration** - Configure different reasoning levels:
  - None (standard)
  - Low (20% tokens)
  - Medium (50% tokens)  
  - High (80% tokens)
  - Custom (specific token count)
✅ **Real-time Search** - Filter models as you type  
✅ **Cost Display** - See pricing per 1K tokens  
✅ **Provider Info** - View model provider and capabilities  
✅ **Persistence** - Cache models and remember selections

## API Integration

### Fetching Models (No Auth Required)
```javascript
const response = await fetch('https://openrouter.ai/api/v1/models');
const { data } = await response.json();
```

### Using Selected Models with Reasoning
```javascript
const body = {
  model: selectedModel.modelId,
  messages: [{ role: 'user', content: prompt }],
  reasoning: { effort: 'high' },  // or { max_tokens: 5000 }
  include_reasoning: true
};

// Requires API key for chat completions
fetch('https://openrouter.ai/api/v1/chat/completions', {
  headers: {
    'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(body)
});
```

## Implementation Timeline

### Phase 1: Core (Days 1-3)
- Fetch and cache models
- Basic multi-selection
- Display selected models

### Phase 2: Enhancement (Days 4-5) 
- Add reasoning configuration
- Implement quick variants
- Search and filtering

### Phase 3: Polish (Days 6-7)
- Performance optimization
- Mobile responsiveness
- Integration testing

## Getting Started

### For Dropdown Implementation (Recommended):
1. Review [Dropdown Implementation Plan](./openrouter-dropdown-implementation-plan.md)
2. Check [Dropdown User Stories](./openrouter-dropdown-user-stories.md) for requirements
3. Start with the `useOpenRouterModels` hook
4. Enhance existing MultiSelect component
5. Add reasoning configuration popover

### For Modal Implementation:
1. Review [Modal Implementation Plan](./openrouter-model-picker-implementation-plan.md)
2. Check [Modal User Stories](./openrouter-model-picker-user-stories.md)
3. View [Interactive Prototype](./openrouter-model-picker-prototype.html) for UX
4. Use [Quick Start Guide](./openrouter-model-picker-quick-start.md) for code

## Key Decisions

### Why Dropdown Over Modal?
Based on your feedback, the dropdown approach is preferred because:
- **Consistency**: Matches existing UI patterns in the app
- **Context**: Users stay in the assessment form
- **Simplicity**: Less code, reuses existing components
- **Mobile**: Better mobile experience with native dropdowns
- **Speed**: Faster selection with quick-add buttons

### Reasoning Levels Explained
- **None**: Standard model without reasoning tokens
- **Low (20%)**: Quick analysis, basic reasoning
- **Medium (50%)**: Balanced depth and speed
- **High (80%)**: Deep analysis, thorough reasoning
- **Custom**: User-defined token allocation

## Dependencies

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "lucide-react": "^0.344.0",  // Icons
    "clsx": "^2.1.0"             // Utility for className
  }
}
```

## Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [Available Models](https://openrouter.ai/models)
- [Reasoning Tokens](https://openrouter.ai/docs/use-cases/reasoning-tokens)
- [API Reference](https://openrouter.ai/docs/api-reference/overview)

## Files in this Directory

- `README.md` - This file
- `openrouter-dropdown-implementation-plan.md` - Dropdown approach technical plan
- `openrouter-dropdown-user-stories.md` - User stories for dropdown implementation
- `openrouter-model-picker-implementation-plan.md` - Modal approach technical plan
- `openrouter-model-picker-user-stories.md` - User stories for modal implementation
- `openrouter-model-picker-quick-start.md` - Ready-to-use code examples
- `openrouter-model-picker-prototype.html` - Interactive HTML prototype

## Support

This documentation supports the assessment grading prototype application. Choose the implementation approach that best fits your needs:
- **Dropdown**: For seamless form integration
- **Modal**: For detailed model exploration

---

*Last Updated: December 2024*  
*Version: 2.0.0 - Added dropdown implementation approach*