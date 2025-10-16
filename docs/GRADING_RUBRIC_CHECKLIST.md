# Grading Rubric - Quick Checklist

## Today's Focus: [Fill in current phase]

### 🎯 Current Sprint Tasks
- [ ] 
- [ ] 
- [ ] 

---

## Quick Phase Overview

### ✅ Completed Phases
(None yet)

### 🚧 In Progress
- [ ] Phase X: [Name]

### ⏳ Upcoming
- [ ] Phase 1: Database Schema
- [ ] Phase 2: Backend Schemas
- [ ] Phase 3: Backend Settings
- [ ] Phase 4: Backend Grading Logic
- [ ] Phase 5: Backend Results
- [ ] Phase 6: Frontend Types
- [ ] Phase 7: Frontend API
- [ ] Phase 8: Frontend Settings
- [ ] Phase 9: Frontend NewAssessment
- [ ] Phase 10: Frontend Review
- [ ] Phase 11: Frontend Context
- [ ] Phase 12: Testing
- [ ] Phase 13: Documentation
- [ ] Phase 14: Deployment

---

## Daily Standup Notes

### [Date]
**Completed:**
- 

**In Progress:**
- 

**Blockers:**
- 

**Next:**
- 

---

### [Date]
**Completed:**
- 

**In Progress:**
- 

**Blockers:**
- 

**Next:**
- 

---

## Quick Commands

### Backend Testing
```bash
# Run backend
python backend_runner.py

# Test endpoints
curl http://localhost:8000/settings/rubric-prompt
curl http://localhost:8000/results/{session_id}/rubric
```

### Frontend Testing
```bash
# Run dev server
npm run dev

# Type check
npm run type-check

# Build
npm run build
```

### Database
```bash
# Run migration
psql -U postgres -d grading_db -f app/migrations/add_grading_rubric_support.sql

# Check tables
psql -U postgres -d grading_db -c "\dt"
```

---

## Key Files Reference

### Backend
- `app/schemas.py` - Add ModelPairSpec
- `app/routers/settings.py` - Rubric prompts
- `app/routers/grade.py` - Main grading logic
- `app/routers/results.py` - Rubric results

### Frontend
- `src/types/index.ts` - Type definitions
- `src/utils/api.ts` - API calls
- `src/pages/Settings.tsx` - Rubric prompt UI
- `src/pages/NewAssessment.tsx` - Dual selectors
- `src/pages/Review.tsx` - Sub-tabs
- `src/context/AssessmentContext.tsx` - State management

### Database
- `app/migrations/add_grading_rubric_support.sql` - Schema changes

---

## Critical Checkpoints

- [ ] Database migration runs successfully
- [ ] Rubric prompts save/load correctly
- [ ] Rubric LLM call works with OpenRouter
- [ ] Assessment LLM receives rubric text
- [ ] Model pairs display correctly in UI
- [ ] Results page shows rubric + feedback
- [ ] Backward compatibility maintained
- [ ] All tests passing

---

## Quick Links
- [Full Implementation Plan](./GRADING_RUBRIC_IMPLEMENTATION_PLAN.md)
- [Technical Spec](./GRADING_RUBRIC_TECHNICAL_SPEC.md)
- [Project README](../README.md)
