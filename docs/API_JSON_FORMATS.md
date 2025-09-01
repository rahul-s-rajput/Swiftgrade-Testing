# TEST GRADING APP - API JSON FORMATS

## 1. QUESTIONS CONFIGURATION ENDPOINT
### POST /questions/config

### For Sarah Johnson (94/100 - Grade A):
```json
{
  "session_id": "REPLACE_WITH_SESSION_ID",
  "questions": [
    {"question_id": "Q1", "number": 1, "max_marks": 10},
    {"question_id": "Q2", "number": 2, "max_marks": 15},
    {"question_id": "Q3", "number": 3, "max_marks": 12},
    {"question_id": "Q4", "number": 4, "max_marks": 8},
    {"question_id": "Q5", "number": 5, "max_marks": 10},
    {"question_id": "Q6", "number": 6, "max_marks": 15},
    {"question_id": "Q7", "number": 7, "max_marks": 10},
    {"question_id": "Q8", "number": 8, "max_marks": 8},
    {"question_id": "Q9", "number": 9, "max_marks": 7},
    {"question_id": "Q10", "number": 10, "max_marks": 5}
  ],
  "human_marks_by_qid": {
    "Q1": 10.0,
    "Q2": 14.0,
    "Q3": 11.0,
    "Q4": 8.0,
    "Q5": 10.0,
    "Q6": 13.0,
    "Q7": 9.0,
    "Q8": 8.0,
    "Q9": 6.0,
    "Q10": 5.0
  }
}
```

### For Michael Chen (69/100 - Grade C+):
```json
{
  "session_id": "REPLACE_WITH_SESSION_ID",
  "questions": [
    {"question_id": "Q1", "number": 1, "max_marks": 10},
    {"question_id": "Q2", "number": 2, "max_marks": 15},
    {"question_id": "Q3", "number": 3, "max_marks": 12},
    {"question_id": "Q4", "number": 4, "max_marks": 8},
    {"question_id": "Q5", "number": 5, "max_marks": 10},
    {"question_id": "Q6", "number": 6, "max_marks": 15},
    {"question_id": "Q7", "number": 7, "max_marks": 10},
    {"question_id": "Q8", "number": 8, "max_marks": 8},
    {"question_id": "Q9", "number": 9, "max_marks": 7},
    {"question_id": "Q10", "number": 10, "max_marks": 5}
  ],
  "human_marks_by_qid": {
    "Q1": 6.0,
    "Q2": 12.0,
    "Q3": 6.0,
    "Q4": 6.0,
    "Q5": 3.0,
    "Q6": 12.0,
    "Q7": 7.0,
    "Q8": 8.0,
    "Q9": 5.0,
    "Q10": 4.0
  }
}
```

## 2. GRADING REQUEST ENDPOINT
### POST /grade/single

```json
{
  "session_id": "REPLACE_WITH_SESSION_ID",
  "models": [
    {"name": "gpt-4-vision-preview", "tries": 3},
    {"name": "claude-3-opus-20240229", "tries": 3},
    {"name": "gemini-pro-vision", "tries": 2}
  ],
  "default_tries": 1,
  "reasoning": {
    "effort": "high",
    "max_reasoning_tokens": 8192
  }
}
```

## 3. QUESTION DETAILS SUMMARY

| Q# | Question ID | Description | Max Marks | Sarah's Score | Michael's Score |
|----|------------|-------------|-----------|---------------|-----------------|
| 1  | Q1 | Differentiate f(x) = 3x³ - 2x² + 5x - 7 | 10 | 10.0 | 6.0 |
| 2  | Q2 | Solve integral ∫(2x² + 3x - 1)dx | 15 | 14.0 | 12.0 |
| 3  | Q3 | Explain photosynthesis & equation | 12 | 11.0 | 6.0 |
| 4  | Q4 | Calculate circle area (r=7.5cm) | 8 | 8.0 | 6.0 |
| 5  | Q5 | Balance Fe + O₂ → Fe₂O₃ | 10 | 10.0 | 3.0 |
| 6  | Q6 | Ball kinematics problem | 15 | 13.0 | 12.0 |
| 7  | Q7 | Atomic structure & numbers | 10 | 9.0 | 7.0 |
| 8  | Q8 | Solve x² - 5x + 6 = 0 | 8 | 8.0 | 8.0 |
| 9  | Q9 | Convert 75°F to °C and K | 7 | 6.0 | 5.0 |
| 10 | Q10 | Newton's Second Law | 5 | 5.0 | 4.0 |
| **Total** | | | **100** | **94.0** | **69.0** |

## 4. PERFORMANCE COMPARISON

### Sarah Johnson (High Performer):
- **Total Score**: 94/100 (94%)
- **Grade**: A
- **Strengths**: Strong mathematical skills, clear presentation
- **Minor Issues**: Small rounding errors, minor formatting

### Michael Chen (Average Student):
- **Total Score**: 69/100 (69%)
- **Grade**: C+
- **Strengths**: Basic understanding, attempts all questions
- **Major Issues**: Fundamental errors, calculation mistakes, rushed work

## 5. EXPECTED AI GRADING BEHAVIOR

The AI models should be able to:
1. **Identify correct solutions** (Sarah's Q1, Q4, Q5, Q8, Q10)
2. **Detect minor errors** (Sarah's Q2, Q3, Q6, Q7, Q9)
3. **Recognize fundamental mistakes** (Michael's Q1, Q5)
4. **Award partial credit** appropriately
5. **Assess presentation quality** and clarity
6. **Handle different solution methods** (e.g., Q8 factoring vs quadratic formula)

## 6. TEST VALIDATION METRICS

Compare AI grading against human benchmarks:
- **Exact match tolerance**: ±1 mark per question
- **Total score tolerance**: ±5 marks overall
- **Grade boundary detection**: Should correctly identify A vs C+ performance
- **Error detection rate**: Should catch major errors (derivative of constant, unbalanced equations)
- **Partial credit consistency**: Should award similar partial credit for similar errors