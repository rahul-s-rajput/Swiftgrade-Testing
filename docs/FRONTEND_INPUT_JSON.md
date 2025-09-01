# TEST GRADING APP - FRONTEND INPUT FORMAT

## Instructions
Copy and paste these JSON strings directly into the frontend form fields.

---

## FOR SARAH JOHNSON (94/100 - Grade A)

### Questions Field (paste this entire JSON array):
```json
[
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
]
```

### Human Graded Marks Field (paste this entire JSON object):
```json
{
  "Q1": 10,
  "Q2": 14,
  "Q3": 11,
  "Q4": 8,
  "Q5": 10,
  "Q6": 13,
  "Q7": 9,
  "Q8": 8,
  "Q9": 6,
  "Q10": 5
}
```

---

## FOR MICHAEL CHEN (69/100 - Grade C+)

### Questions Field (paste this entire JSON array):
```json
[
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
]
```

### Human Graded Marks Field (paste this entire JSON object):
```json
{
  "Q1": 6,
  "Q2": 12,
  "Q3": 6,
  "Q4": 6,
  "Q5": 3,
  "Q6": 12,
  "Q7": 7,
  "Q8": 8,
  "Q9": 5,
  "Q10": 4
}
```

---

## QUESTION DESCRIPTIONS (for reference)

| ID  | Description | Max Marks |
|-----|------------|-----------|
| Q1  | Differentiate f(x) = 3x³ - 2x² + 5x - 7 | 10 |
| Q2  | Solve the integral ∫(2x² + 3x - 1)dx | 15 |
| Q3  | Explain photosynthesis and write chemical equation | 12 |
| Q4  | Calculate area of circle with radius r = 7.5 cm | 8 |
| Q5  | Balance chemical equation Fe + O₂ → Fe₂O₃ | 10 |
| Q6  | Ball thrown upward - find max height and time | 15 |
| Q7  | Describe atomic structure, atomic number, mass number | 10 |
| Q8  | Find roots of x² - 5x + 6 = 0 | 8 |
| Q9  | Convert 75°F to Celsius and Kelvin | 7 |
| Q10 | State Newton's Second Law and mathematical form | 5 |

---

## COMPLETE WORKFLOW

1. **Create New Assessment** → Click "New Assessment" button

2. **Fill in the form:**
   - **Assessment Name**: "Mathematics & Science Midterm - Sarah Johnson" (or Michael Chen)
   - **Upload Student Test Images**: Convert the HTML files to JPG and upload (4 pages)
   - **Upload Answer Key Images**: Convert the answer key HTML to JPG and upload (4 pages)
   - **Question List**: Paste the JSON array from above
   - **Human Graded Marks**: Paste the JSON object from above
   - **Select AI Models**: Choose multiple models for comparison
   - **Testing Iterations**: Set to 3

3. **Launch Assessment** → Click submit button

4. **Monitor Progress** → View results on dashboard

---

## NOTES

- The frontend expects valid JSON in both fields
- Do NOT include comments in the JSON
- Make sure to use the exact field names (question_id, number, max_marks)
- Human marks should be numbers without "/total" formatting
- The application will calculate discrepancies automatically