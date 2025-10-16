"""
Test JSON extraction from various LLM response formats.
This demonstrates that the parsing logic handles multiple edge cases.
"""

import json
import re

def extract_json(text: str) -> dict:
    """
    Simulates the extraction logic from grade.py
    """
    text = text.strip()
    
    # Remove markdown code fences
    if text.startswith("```json") or text.startswith("```JSON"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    # Find first opening brace
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found")
    
    # Use brace matching to find closing brace
    brace_count = 0
    end = -1
    in_string = False
    escape_next = False
    
    for i in range(start, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i
                    break
    
    if end == -1:
        raise ValueError("No closing brace found")
    
    json_str = text[start : end + 1]
    return json.loads(json_str)


# Test cases
test_cases = [
    {
        "name": "Plain JSON",
        "input": '{"result":[{"first_name":"John","last_name":"Doe"}]}',
    },
    {
        "name": "JSON with markdown fences",
        "input": '```json\n{"result":[{"first_name":"John","last_name":"Doe"}]}\n```',
    },
    {
        "name": "JSON with preamble text (your example)",
        "input": """# Grading Criteria for Physics 11 - Kinematics Unit Test

```json
{
  "grading_criteria": [
    {
      "question_number": "DES.1",
      "max_mark": 1.0,
      "components": [
        {
          "header": "🎯 Answer",
          "marks": 1.0,
          "criteria": "Answer: 'motion'"
        }
      ]
    }
  ]
}
```""",
    },
    {
        "name": "JSON with text before and after",
        "input": """Here's the grading result:

{"result":[{"first_name":"Jane","last_name":"Smith"}]}

Hope this helps!""",
    },
    {
        "name": "Uppercase JSON fence",
        "input": '```JSON\n{"result":[{"first_name":"Bob","last_name":"Wilson"}]}\n```',
    },
    {
        "name": "No fence, just preamble",
        "input": """I've analyzed the assessment and here's the result:

{"result":[{"first_name":"Alice","last_name":"Brown"}]}""",
    },
]


if __name__ == "__main__":
    print("=" * 70)
    print("JSON EXTRACTION TEST SUITE")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test['name']}")
        print("-" * 70)
        
        try:
            result = extract_json(test['input'])
            print(f"✅ PASSED")
            print(f"📦 Extracted: {json.dumps(result, indent=2)[:200]}...")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            print(f"Input preview: {test['input'][:100]}...")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
