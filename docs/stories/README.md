# OpenRouter Model Picker - Stories Documentation

## Overview
This directory contains detailed implementation stories for the OpenRouter Model Picker component, with special focus on the reasoning configuration challenge.

## Story Files

### 📁 Core Story
- **[story-04-reasoning-configuration.md](./story-04-reasoning-configuration.md)**  
  Complete implementation guide for reasoning configuration with code examples

### 📁 Summary
- **[story-04-reasoning-summary.md](./story-04-reasoning-summary.md)**  
  High-level summary of the reasoning detection challenge and solution

## Quick Reference: Reasoning Configuration Solution

### The Challenge
OpenRouter's API doesn't explicitly indicate which models support reasoning or what configuration type they accept.

### The Solution
We use a **hybrid approach**:
1. **Known Models Database** - Curated list of verified models
2. **Pattern Detection** - Regex patterns for model IDs
3. **Dynamic Enhancement** - Check API response for hints
4. **Graceful Fallbacks** - Warnings for unverified models

### Key Implementation Files

```typescript
// 1. Reasoning Models Database
src/utils/reasoningModels.ts
- Known models configurations
- Pattern matching functions
- Capability detection

// 2. Model Enhancement
src/hooks/useModelFetch.ts
- Enhance models with reasoning info during fetch
- Pattern detection logic

// 3. UI Component
src/components/OpenRouterModelPicker/components/ReasoningSelector.tsx
- Dynamic UI based on model capabilities
- Custom token input
- Visual indicators

// 4. API Builder
src/utils/openRouterApiBuilder.ts
- Build correct API requests based on model type
- Handle effort vs max_tokens
```

## Reasoning Support by Model Type

| Model Provider | Reasoning Type | Configuration | Notes |
|---------------|---------------|---------------|-------|
| **Anthropic Claude** (3.7+, 4.x) | ✅ Full | `effort` + `max_tokens` | Most flexible |
| **DeepSeek R1** | ✅ Token-based | `max_tokens` only | Returns reasoning |
| **Gemini Thinking** | ✅ Internal | `max_tokens` | No reasoning output |
| **OpenAI o-series** | ✅ Internal | `max_tokens` | No reasoning output |
| **Others** | ❓ Varies | Detected | Test required |

## Visual Flow

```
User Selects Model
       ↓
Check Reasoning Support
       ↓
    ┌──────────────────┐
    │ Known Model?     │
    └────────┬─────────┘
             ↓
      ┌──────┴──────┐
      ↓             ↓
   [Yes]          [No]
      ↓             ↓
Show Verified   Check Patterns
   Options          ↓
      ↓          [Match?]
      ↓             ↓
   Configure    Show Warning
      ↓          + Limited
      ↓          Options
      ↓             ↓
   Create Variant ←─┘
```

## Implementation Priority

1. **P0 - Critical**
   - Known models database
   - Basic pattern detection
   - UI component

2. **P1 - Important**
   - API request builder
   - Visual indicators
   - Warning messages

3. **P2 - Nice to Have**
   - Auto-detection
   - Cost calculator
   - Preset templates

## Testing Checklist

- [ ] Claude model shows all options
- [ ] DeepSeek shows token-only options
- [ ] Unknown model shows warning
- [ ] API requests have correct params
- [ ] Token limits are enforced
- [ ] Visual badges are accurate

## Related Documentation

- [Main Implementation Plan](../openrouter-model-picker-implementation-plan.md)
- [User Stories](../openrouter-model-picker-user-stories.md)
- [Quick Start Guide](../openrouter-model-picker-quick-start.md)

---

*Last Updated: December 2024*