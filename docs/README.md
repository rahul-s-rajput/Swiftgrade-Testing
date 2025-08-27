# OpenRouter Model Picker Documentation

## Overview
This directory contains comprehensive documentation for implementing an OpenRouter model picker component with multi-selection and reasoning configuration capabilities.

## Documents

### 1. [Implementation Plan](./openrouter-model-picker-implementation-plan.md)
Complete technical implementation plan including:
- Core features and architecture
- Data structures and API integration
- Component structure and UI/UX design
- Implementation phases (5-day plan)
- Performance optimizations
- Testing strategy
- Future enhancements

### 2. [User Stories](./openrouter-model-picker-user-stories.md)
Detailed user stories and acceptance criteria:
- 14 comprehensive user stories
- Story points and prioritization
- Sprint planning suggestions
- Definition of done
- Future enhancement ideas

### 3. [Quick Start Guide](./openrouter-model-picker-quick-start.md)
Ready-to-use code implementation:
- Type definitions
- React hooks (fetching, selection, filtering)
- Main component structure
- Usage examples
- API integration patterns

## Key Features

✅ **Dynamic Model Loading** - Fetch all models from OpenRouter API  
✅ **Multi-Selection** - Select multiple models simultaneously  
✅ **Reasoning Variants** - Configure different reasoning levels (low/medium/high/custom)  
✅ **Advanced Filtering** - Filter by provider, price, capabilities  
✅ **Real-time Search** - Search models by name and description  
✅ **Cost Estimation** - View pricing per model  
✅ **Caching** - Local storage caching to reduce API calls  
✅ **Responsive Design** - Works on desktop and mobile

## Technology Stack

- **React 18** - Component framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **TanStack Query** (optional) - Data fetching
- **OpenRouter API** - Model catalog

## Implementation Timeline

### Week 1: Core Functionality
- Day 1: Basic model fetching and display
- Day 2: Search and filtering
- Day 3: Multi-selection functionality
- Day 4: Reasoning configuration
- Day 5: Integration and polish

### Week 2: Enhancements
- Advanced features
- Testing
- Documentation
- Performance optimization

## OpenRouter API Integration

### Model Fetching
```javascript
// No authentication required
fetch('https://openrouter.ai/api/v1/models')
```

### Using Selected Models
```javascript
const body = {
  model: selectedModel.id,
  messages: [{ role: 'user', content: prompt }],
  reasoning: { effort: 'high' },  // For reasoning models
  include_reasoning: true
};
```

## Reasoning Configuration

The component supports OpenRouter's reasoning capabilities:

- **None** - Standard model without reasoning
- **Low** - 20% of max_tokens for reasoning (faster, less thorough)
- **Medium** - 50% of max_tokens for reasoning (balanced)
- **High** - 80% of max_tokens for reasoning (slower, more thorough)
- **Custom** - Manual token allocation for fine control

## Getting Started

1. **Review the Implementation Plan** - Understand the architecture
2. **Check User Stories** - Understand requirements and priorities
3. **Use Quick Start Guide** - Copy ready-to-use code
4. **Install Dependencies**:
   ```bash
   npm install clsx @tanstack/react-query
   ```
5. **Copy Type Definitions** - Set up TypeScript types
6. **Implement Core Hooks** - Start with model fetching
7. **Build Components** - Create UI components
8. **Test & Iterate** - Refine based on usage

## Project Structure

```
src/
├── components/
│   └── OpenRouterModelPicker/
│       ├── index.tsx
│       ├── OpenRouterModelPicker.tsx
│       ├── hooks/
│       │   ├── useModelFetch.ts
│       │   ├── useModelSelection.ts
│       │   └── useModelFilter.ts
│       ├── components/
│       │   ├── ModelCard.tsx
│       │   ├── ModelFilters.tsx
│       │   ├── ReasoningSelector.tsx
│       │   └── SelectedModelsList.tsx
│       └── styles.module.css
└── types/
    └── openrouter.ts
```

## Support & Resources

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [OpenRouter Models](https://openrouter.ai/models)
- [API Reference](https://openrouter.ai/docs/api-reference/overview)
- [Reasoning Tokens Guide](https://openrouter.ai/docs/use-cases/reasoning-tokens)

## Notes for Development

1. **No API Key Required** - Model list fetching doesn't need authentication
2. **Caching is Important** - 200+ models, cache to avoid repeated fetches
3. **Reasoning Support Varies** - Not all models support reasoning tokens
4. **Virtual Scrolling** - Consider implementing for large model lists
5. **Mobile Optimization** - Many models to display on small screens

## Contact & Questions

This documentation was created for the assessment testing web app prototype. For questions or clarifications about implementation, refer to the detailed documents above or consult the OpenRouter API documentation.

---

*Last Updated: December 2024*  
*Version: 1.0.0*