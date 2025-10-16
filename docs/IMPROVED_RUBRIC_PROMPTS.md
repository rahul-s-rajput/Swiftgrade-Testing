# Improved Grading Rubric Prompts - Usage Guide

## 📋 Overview

The improved rubric prompts use **JSON structured output** instead of plain text. This provides:
- ✅ Better parsing and validation
- ✅ Easier integration with assessment prompts
- ✅ Consistent structure across all rubrics
- ✅ Programmatic access to criteria and deductions

---

## 🎯 Key Improvements

### 1. **Images Only in User Prompt**
- ✅ System prompt: Text only (no image placeholders)
- ✅ User prompt: Contains `[Grading rubric images]` placeholder
- ✅ Compliant with OpenRouter/Claude API requirements

### 2. **JSON Structured Output**
- ✅ Rubric returns parseable JSON
- ✅ Consistent schema across all questions
- ✅ Easy to merge with question list
- ✅ Clean injection into assessment prompt

---

## 📝 Example Flow

### Input to Rubric LLM

**System Message:**
```
<Role>You are a grading rubric analyzer...</Role>

<Question_List>
{
  "question_list": [
    {"question_number": "Q1", "max_mark": 10},
    {"question_number": "Q2", "max_mark": 15}
  ]
}
</Question_List>

<Output_Format>
Return ONLY valid JSON:
{
  "rubric": [
    {
      "question_id": "Q1",
      "max_marks": 10,
      "grading_criteria": [...],
      "deductions": [...],
      "notes": "..."
    }
  ]
}
</Output_Format>
```

**User Message:**
```
<Grading_Rubric_Images>
[Image 1: Rubric page 1]
[Image 2: Rubric page 2]
</Grading_Rubric_Images>

Please analyze the grading rubric images and extract criteria.
Return valid JSON (no markdown fences).
```

---

### Output from Rubric LLM

```json
{
  "rubric": [
    {
      "question_id": "Q1",
      "max_marks": 10,
      "grading_criteria": [
        {
          "criterion": "Correct formula identification",
          "marks": 5,
          "requirements": "Student must identify and write the correct quadratic formula: x = (-b ± √(b²-4ac)) / 2a"
        },
        {
          "criterion": "Accurate calculation and simplification",
          "marks": 5,
          "requirements": "Student must substitute values correctly, perform arithmetic accurately, and simplify to final answer"
        }
      ],
      "deductions": [
        {
          "reason": "Missing or incorrect units in final answer",
          "marks": -1
        },
        {
          "reason": "Arithmetic error in intermediate steps (if final answer still reasonable)",
          "marks": -2
        }
      ],
      "notes": "Award partial credit (3/5) for formula if student shows understanding but makes minor notation errors. Do not award calculation marks if formula is completely wrong."
    },
    {
      "question_id": "Q2",
      "max_marks": 15,
      "grading_criteria": [
        {
          "criterion": "Graph axes properly labeled",
          "marks": 3,
          "requirements": "Both x and y axes labeled with variable names and units in parentheses"
        },
        {
          "criterion": "Data points plotted accurately",
          "marks": 7,
          "requirements": "All 10 data points plotted within ±0.5 units of correct position on grid"
        },
        {
          "criterion": "Best fit line drawn correctly",
          "marks": 5,
          "requirements": "Straight line with approximately equal points above and below, passing through or near the mean"
        }
      ],
      "deductions": [
        {
          "reason": "Graph not drawn with ruler (wobbly line)",
          "marks": -1
        }
      ],
      "notes": "No partial credit for unlabeled axes - this is a critical requirement. However, if only one axis is unlabeled, deduct only -2 marks instead of full -3."
    }
  ]
}
```

---

### This JSON is Injected into Assessment Prompt

**Assessment System Message (after placeholder replacement):**
```
<Role>You are a teacher grading student work...</Role>

<Grading_Rubric>
Here is the detailed grading rubric (JSON format):
{
  "rubric": [
    {
      "question_id": "Q1",
      "max_marks": 10,
      "grading_criteria": [
        {
          "criterion": "Correct formula identification",
          "marks": 5,
          "requirements": "Student must identify and write..."
        },
        {
          "criterion": "Accurate calculation",
          "marks": 5,
          "requirements": "Student must substitute values..."
        }
      ],
      "deductions": [
        {"reason": "Missing units", "marks": -1}
      ],
      "notes": "Award partial credit (3/5) for formula..."
    }
  ]
}
</Grading_Rubric>

<Question_List>
{
  "question_list": [
    {"question_number": "Q1", "max_mark": 10},
    {"question_number": "Q2", "max_mark": 15}
  ]
}
</Question_List>
```

---

## 🔧 Backend Implementation

The backend already handles this correctly:

**In `grade.py` → `_call_rubric_llm()`:**
```python
# Calls rubric LLM
raw_response = await _call_openrouter(...)

# Extracts rubric text (which is JSON)
rubric_text = content.strip()  # e.g., '{"rubric": [...]}'

# Stores in database
rubric_record = {
    "rubric_response": rubric_text,  # Full JSON string
    ...
}

# Returns for use in assessment
return rubric_text  # JSON string
```

**In `grade.py` → `_build_messages()`:**
```python
# Replaces placeholder with JSON
if rubric_text and "[Grading Rubric]" in sys_text:
    sys_text = sys_text.replace("[Grading Rubric]", rubric_text)
```

✅ **No code changes needed!** The backend already handles JSON properly.

---

## 📊 Benefits of JSON Structure

### 1. **Programmatic Access**
Frontend can parse and display rubric data:
```typescript
const rubric = JSON.parse(rubricResponse);
rubric.rubric.forEach(q => {
  console.log(`${q.question_id}: ${q.max_marks} marks`);
  q.grading_criteria.forEach(c => {
    console.log(`  - ${c.criterion}: ${c.marks} marks`);
  });
});
```

### 2. **Validation**
Can validate rubric extraction succeeded:
```typescript
const rubric = JSON.parse(rubricResponse);
if (!rubric.rubric || !Array.isArray(rubric.rubric)) {
  console.error('Invalid rubric format');
}
```

### 3. **Rich UI Display**
Can render rubric in structured format:
```tsx
<div>
  {rubric.rubric.map(q => (
    <div key={q.question_id}>
      <h3>{q.question_id} ({q.max_marks} marks)</h3>
      <ul>
        {q.grading_criteria.map(c => (
          <li>{c.criterion} - {c.marks} marks</li>
        ))}
      </ul>
    </div>
  ))}
</div>
```

### 4. **Assessment LLM Benefits**
The assessment model receives clear, structured criteria:
- Knows exactly how many marks each criterion is worth
- Understands deductions clearly
- Can reference specific requirements

---

## 🎨 Example Rubric Display (Future Enhancement)

In Review page, could render rubric beautifully:

```tsx
{questionTab === 'rubric' && (
  <div>
    {(() => {
      try {
        const rubric = JSON.parse(rubricResponse);
        const questionRubric = rubric.rubric.find(
          r => r.question_id === selectedQuestion
        );
        
        return (
          <div className="space-y-4">
            <h3>{questionRubric.question_id} - {questionRubric.max_marks} Marks</h3>
            
            <div className="criteria">
              <h4>Grading Criteria:</h4>
              {questionRubric.grading_criteria.map((c, i) => (
                <div key={i} className="criterion">
                  <span className="badge">{c.marks} marks</span>
                  <strong>{c.criterion}</strong>
                  <p>{c.requirements}</p>
                </div>
              ))}
            </div>
            
            {questionRubric.deductions.length > 0 && (
              <div className="deductions">
                <h4>Deductions:</h4>
                {questionRubric.deductions.map((d, i) => (
                  <div key={i}>
                    <span className="badge">{d.marks}</span>
                    <span>{d.reason}</span>
                  </div>
                ))}
              </div>
            )}
            
            {questionRubric.notes && (
              <div className="notes">
                <strong>Notes:</strong>
                <p>{questionRubric.notes}</p>
              </div>
            )}
          </div>
        );
      } catch {
        // Fallback to plain text display
        return <p>{rubricResponse}</p>;
      }
    })()}
  </div>
)}
```

---

## ✅ Summary of Changes

**Updated Files:**
- ✅ `app/routers/settings.py` - Both rubric and assessment templates

**New Template Features:**

**Rubric System Prompt:**
- ✅ No image placeholders (text only)
- ✅ Defines JSON output structure
- ✅ Lists 8 critical rules
- ✅ Clear schema with examples

**Rubric User Prompt:**
- ✅ Contains `[Grading rubric images]` placeholder
- ✅ Simple, clear instruction
- ✅ Emphasizes "no markdown fences"

**Assessment System Prompt:**
- ✅ Added `<Grading_Rubric>` section
- ✅ Explains it's JSON format
- ✅ Instructs to use rubric for marking
- ✅ Maintains all other features

---

## 🧪 Testing These Prompts

1. **Save New Prompts via UI:**
   ```bash
   npm run dev
   # Go to Settings → Rubric Prompt Settings
   # Copy the improved system/user templates
   # Click Save
   ```

2. **Create Test Assessment:**
   - Upload rubric images
   - Select model pair
   - Run assessment

3. **Check Rubric Output:**
   - Navigate to Review page
   - Click "Grading Rubric Only" tab
   - Verify JSON structure

4. **Verify Assessment Used Rubric:**
   - Click "Both" tab
   - Check that feedback references rubric criteria
   - Verify marks align with rubric allocations

---

**Status:** ✅ Prompts Updated and Ready to Use!

The improved prompts are now the defaults in the backend. Users can customize them further via the Settings UI if needed.
