# OpenRouter Model Selector - User Stories (Dropdown Version)

## Epic: OpenRouter Dropdown Model Selector
Build an enhanced dropdown multi-select component that enables users to select and configure multiple AI models from OpenRouter with inline reasoning options, seamlessly integrated into the existing assessment form.

---

## Story 1: Enhance Dropdown with OpenRouter Models
**As a** user  
**I want to** see all available OpenRouter models in the existing dropdown selector  
**So that** I can choose models without leaving the assessment form

### Acceptance Criteria:
- [ ] Dropdown loads models from OpenRouter API
- [ ] Models show provider, price, and context info inline
- [ ] Search filters models in real-time
- [ ] Loading state while fetching models
- [ ] Cached models load instantly (1-hour cache)
- [ ] Graceful fallback if API fails

### Technical Tasks:
1. Create `useOpenRouterModels` hook
2. Implement caching mechanism
3. Transform API response to match component needs
4. Integrate with existing MultiSelect pattern
5. Add model metadata display

**Story Points:** 5  
**Priority:** P0 (Critical)

---

## Story 2: Quick Variant Selection
**As a** user  
**I want to** quickly add model variants with different reasoning levels  
**So that** I can test the same model with different configurations

### Acceptance Criteria:
- [ ] Each model shows quick-add buttons: [Standard] [+Low] [+Med] [+High]
- [ ] Clicking adds that variant immediately
- [ ] Visual indicator shows which variants are already selected
- [ ] Can add multiple variants of the same model
- [ ] Reasoning buttons only show for capable models
- [ ] Selected variants appear as chips above dropdown

### Technical Tasks:
1. Create `ModelOptionItem` component
2. Implement variant quick-add buttons
3. Add variant detection logic
4. Create visual states for selected variants
5. Filter reasoning options by model capability

**Story Points:** 5  
**Priority:** P0 (Critical)

---

## Story 3: Selected Model Chips Display
**As a** user  
**I want to** see my selected models as chips with their reasoning configuration  
**So that** I can quickly review and modify my selection

### Acceptance Criteria:
- [ ] Each selected model appears as a chip
- [ ] Chip shows model name and reasoning level
- [ ] Color-coded reasoning badges (gray=none, blue=low, yellow=med, red=high)
- [ ] Click X to remove a model variant
- [ ] Click gear icon to configure reasoning
- [ ] Chips wrap when many selected
- [ ] Show count badge when > 5 models

### Technical Tasks:
1. Create `SelectedModelChip` component
2. Implement chip styling with badges
3. Add remove functionality
4. Create configuration trigger
5. Implement responsive chip layout

**Story Points:** 3  
**Priority:** P0 (Critical)

---

## Story 4: Inline Reasoning Configuration
**As a** user  
**I want to** configure reasoning settings without leaving the form  
**So that** I can quickly adjust model parameters

### Acceptance Criteria:
- [ ] Click gear on chip opens small popover
- [ ] Shows reasoning options: None/Low/Medium/High/Custom
- [ ] Custom option shows token input field
- [ ] Visual preview of token allocation
- [ ] Apply/Cancel buttons
- [ ] Popover auto-positions to stay visible
- [ ] ESC key closes popover

### Technical Tasks:
1. Create `ReasoningConfigPopover` component
2. Implement popover positioning logic
3. Add custom token validation
4. Create reasoning preset logic
5. Handle keyboard interactions

**Story Points:** 5  
**Priority:** P1 (High)

---

## Story 5: Search and Filter in Dropdown
**As a** user  
**I want to** search and filter models within the dropdown  
**So that** I can quickly find specific models

### Acceptance Criteria:
- [ ] Search box at top of dropdown
- [ ] Filters by model name, provider, ID
- [ ] Real-time filtering as user types
- [ ] Show "No results" when nothing matches
- [ ] Clear search with X button
- [ ] Maintains selection during search
- [ ] Highlight matching text

### Technical Tasks:
1. Enhance search functionality
2. Implement text highlighting
3. Add clear button
4. Optimize search performance
5. Maintain scroll position

**Story Points:** 3  
**Priority:** P1 (High)

---

## Story 6: Provider and Price Indicators
**As a** user  
**I want to** see provider and pricing information inline  
**So that** I can make cost-aware decisions

### Acceptance Criteria:
- [ ] Show provider name (OpenAI, Anthropic, etc.)
- [ ] Display price per 1K tokens
- [ ] Color-code prices (green=cheap, yellow=moderate, red=expensive)
- [ ] Show context length in K tokens
- [ ] Provider logos if available
- [ ] Sort option by price
- [ ] Total cost estimate for selection

### Technical Tasks:
1. Add price formatting utilities
2. Implement color coding logic
3. Create price comparison display
4. Add sorting functionality
5. Calculate total estimates

**Story Points:** 3  
**Priority:** P1 (High)

---

## Story 7: Keyboard Navigation
**As a** power user  
**I want to** navigate the dropdown with keyboard shortcuts  
**So that** I can select models efficiently

### Acceptance Criteria:
- [ ] Arrow keys navigate dropdown options
- [ ] Enter/Space toggles selection
- [ ] Tab moves between elements
- [ ] Escape closes dropdown
- [ ] Type to search/filter
- [ ] Ctrl+A selects all visible
- [ ] Delete removes selected when focused

### Technical Tasks:
1. Implement keyboard event handlers
2. Add focus management
3. Create keyboard shortcut map
4. Handle edge cases
5. Add accessibility attributes

**Story Points:** 3  
**Priority:** P2 (Medium)

---

## Story 8: Bulk Reasoning Configuration
**As a** user  
**I want to** apply the same reasoning setting to multiple models  
**So that** I can configure many models quickly

### Acceptance Criteria:
- [ ] "Apply to all" button in reasoning popover
- [ ] Bulk action dropdown above chips
- [ ] Options: Set all to Low/Medium/High
- [ ] Only affects reasoning-capable models
- [ ] Confirmation for bulk changes
- [ ] Undo last bulk action

### Technical Tasks:
1. Create bulk action dropdown
2. Implement apply-to-all logic
3. Add confirmation dialog
4. Create undo mechanism
5. Filter applicable models

**Story Points:** 3  
**Priority:** P2 (Medium)

---

## Story 9: Model Grouping
**As a** user  
**I want to** see models grouped by provider in the dropdown  
**So that** I can find models more easily

### Acceptance Criteria:
- [ ] Group models by provider
- [ ] Collapsible provider sections
- [ ] Show count per provider
- [ ] Expand/collapse all option
- [ ] Remember expansion state
- [ ] Visual separators between groups

### Technical Tasks:
1. Implement grouping logic
2. Create collapsible sections
3. Add expansion state management
4. Style group headers
5. Add group actions

**Story Points:** 3  
**Priority:** P2 (Medium)

---

## Story 10: Recent and Favorite Models
**As a** user  
**I want to** quickly access frequently used models  
**So that** I can save time on repeated selections

### Acceptance Criteria:
- [ ] "Recent" section at top of dropdown
- [ ] Shows last 5 used models
- [ ] Star icon to favorite models
- [ ] Favorites section below recent
- [ ] Persist favorites in localStorage
- [ ] Clear recent history option

### Technical Tasks:
1. Track model usage
2. Implement favorites system
3. Create recent/favorites sections
4. Add persistence layer
5. Build management UI

**Story Points:** 3  
**Priority:** P3 (Low)

---

## Story 11: Smart Model Recommendations
**As a** user  
**I want to** get model suggestions based on my task  
**So that** I can choose appropriate models

### Acceptance Criteria:
- [ ] "Suggested for grading" section
- [ ] Based on assessment type
- [ ] Considers cost/performance trade-offs
- [ ] Shows why recommended
- [ ] Can dismiss suggestions
- [ ] Learn from user selections

### Technical Tasks:
1. Create recommendation engine
2. Define suggestion criteria
3. Build suggestion UI
4. Add dismissal logic
5. Implement learning mechanism

**Story Points:** 5  
**Priority:** P3 (Low)

---

## Story 12: Export Selection Configuration
**As a** user  
**I want to** save my model selection for reuse  
**So that** I can quickly apply the same configuration again

### Acceptance Criteria:
- [ ] "Save as preset" button
- [ ] Name custom presets
- [ ] Load preset from dropdown
- [ ] Export as JSON
- [ ] Import from JSON
- [ ] Share via URL

### Technical Tasks:
1. Create preset management system
2. Implement export/import logic
3. Add preset dropdown
4. Create sharing mechanism
5. Validate imported data

**Story Points:** 3  
**Priority:** P3 (Low)

---

## Story 13: Mobile-Optimized Dropdown
**As a** mobile user  
**I want to** easily select models on my phone  
**So that** I can use the app on any device

### Acceptance Criteria:
- [ ] Touch-friendly tap targets
- [ ] Bottom sheet on mobile
- [ ] Swipe to dismiss
- [ ] Larger text and buttons
- [ ] Simplified layout
- [ ] Responsive chip size

### Technical Tasks:
1. Detect mobile viewport
2. Create mobile layout
3. Implement touch handlers
4. Optimize for small screens
5. Test on various devices

**Story Points:** 5  
**Priority:** P2 (Medium)

---

## Story 14: Integration with Assessment Form
**As a** developer  
**I want to** seamlessly integrate the selector with the existing form  
**So that** it works with current validation and submission

### Acceptance Criteria:
- [ ] Works with existing form validation
- [ ] Saves selection to assessment state
- [ ] Restores selection on form edit
- [ ] Triggers onChange properly
- [ ] Shows validation errors
- [ ] Integrates with form submit

### Technical Tasks:
1. Update assessment types
2. Modify form state management
3. Add validation rules
4. Update submission handler
5. Test with existing flow

**Story Points:** 3  
**Priority:** P1 (High)

---

## Technical Stories

### Story 15: Performance Optimization
**As a** developer  
**I want** the dropdown to handle 200+ models smoothly  
**So that** users have a responsive experience

### Acceptance Criteria:
- [ ] Virtual scrolling for long lists
- [ ] Debounced search (300ms)
- [ ] Memoized filtering
- [ ] Lazy load model details
- [ ] < 100ms interaction response
- [ ] Smooth animations

**Story Points:** 5  
**Priority:** P2 (Medium)

---

### Story 16: Comprehensive Testing
**As a** developer  
**I want** full test coverage for the component  
**So that** it's reliable and maintainable

### Acceptance Criteria:
- [ ] Unit tests for all hooks
- [ ] Component integration tests
- [ ] Dropdown interaction tests
- [ ] Accessibility tests
- [ ] Performance benchmarks
- [ ] 80% code coverage

**Story Points:** 5  
**Priority:** P2 (Medium)

---

## Sprint Planning

### Sprint 1 (Days 1-5)
- Story 1: Load OpenRouter Models (5 pts)
- Story 2: Quick Variant Selection (5 pts)
- Story 3: Model Chips Display (3 pts)
**Total: 13 points**

### Sprint 2 (Days 6-10)
- Story 4: Inline Reasoning Config (5 pts)
- Story 5: Search and Filter (3 pts)
- Story 6: Price Indicators (3 pts)
- Story 14: Form Integration (3 pts)
**Total: 14 points**

### Sprint 3 (Days 11-15)
- Story 7: Keyboard Navigation (3 pts)
- Story 8: Bulk Configuration (3 pts)
- Story 9: Model Grouping (3 pts)
- Story 15: Performance (5 pts)
**Total: 14 points**

### Backlog
- Story 10: Recent/Favorites (3 pts)
- Story 11: Recommendations (5 pts)
- Story 12: Export/Import (3 pts)
- Story 13: Mobile Optimization (5 pts)
- Story 16: Testing (5 pts)

---

## Definition of Done

A story is complete when:
1. ✅ Feature works in the dropdown
2. ✅ Integrates with existing form
3. ✅ Responsive design implemented
4. ✅ Keyboard accessible
5. ✅ Error states handled
6. ✅ Loading states shown
7. ✅ Tested in Chrome, Firefox, Safari
8. ✅ Code reviewed
9. ✅ No console errors
10. ✅ Documentation updated

---

## Key Differences from Modal Approach

### Benefits:
- **Faster Selection**: No modal open/close overhead
- **Better Context**: Stay in form while selecting
- **Consistent UX**: Matches existing components
- **Mobile Friendly**: Dropdowns work better on phones
- **Less Code**: Reuses existing patterns

### Trade-offs:
- **Less Space**: Constrained to dropdown size
- **Fewer Features**: Can't show as much detail
- **Simpler Filters**: Limited filtering options

### Migration Strategy:
1. Enhance existing MultiSelect gradually
2. Add OpenRouter features incrementally
3. Test with users at each stage
4. Roll back easily if needed