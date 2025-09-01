#!/usr/bin/env python3
"""
Test script to verify auto-numbering functionality for questions.
The backend now auto-generates question numbers from array index,
so the frontend only needs to send question_id and max_marks.
"""

import httpx
import json
import sys

# Backend URL
API_BASE = "http://127.0.0.1:8000"

def create_test_session():
    """Create a test session and return session_id"""
    try:
        response = httpx.post(f"{API_BASE}/sessions", json={"name": "Auto-Number Test"})
        response.raise_for_status()
        session_id = response.json()["session_id"]
        print(f"✅ Created test session: {session_id}")
        return session_id
    except Exception as e:
        print(f"❌ Failed to create session: {e}")
        sys.exit(1)

def test_auto_numbering(session_id: str):
    """Test that auto-numbering works correctly"""
    
    print("\n" + "=" * 80)
    print("🧪 TESTING AUTO-NUMBERING FOR QUESTIONS")
    print("=" * 80)
    print()
    
    # Test Case 1: Simplified format (no number field)
    print("📝 Test Case 1: Simplified format (no number field)")
    print("-" * 40)
    
    payload_simple = {
        "session_id": session_id,
        "questions": [
            {"question_id": "DES.1", "max_marks": 10},
            {"question_id": "DES.2", "max_marks": 15},
            {"question_id": "APP.1", "max_marks": 20},
            {"question_id": "APP.2", "max_marks": 25}
        ],
        "human_marks_by_qid": {
            "DES.1": 8,
            "DES.2": 12,
            "APP.1": 18,
            "APP.2": 22
        }
    }
    
    print("📤 Request:")
    print(json.dumps(payload_simple, indent=2))
    
    try:
        response = httpx.post(f"{API_BASE}/questions/config", json=payload_simple)
        response.raise_for_status()
        print("\n✅ Success! Questions configured without number field")
        
        # Verify by fetching the questions
        response = httpx.get(f"{API_BASE}/questions/{session_id}")
        response.raise_for_status()
        questions = response.json()["questions"]
        
        print("\n📥 Saved questions with auto-generated numbers:")
        for q in questions:
            print(f"   {q['question_id']}: number={q['number']}, max_marks={q['max_marks']}")
        
        # Verify numbering is correct
        expected_numbers = {
            "DES.1": 1,
            "DES.2": 2,
            "APP.1": 3,
            "APP.2": 4
        }
        
        all_correct = True
        for q in questions:
            if q["number"] != expected_numbers.get(q["question_id"]):
                print(f"   ❌ Wrong number for {q['question_id']}: got {q['number']}, expected {expected_numbers[q['question_id']]}")
                all_correct = False
        
        if all_correct:
            print("\n   ✅ All numbers correctly auto-generated from array index!")
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ Request failed: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Test Case 2: Legacy format (with number field) - should still work
    print("\n" + "=" * 80)
    print("📝 Test Case 2: Legacy format (with number field)")
    print("-" * 40)
    
    payload_legacy = {
        "session_id": session_id,
        "questions": [
            {"question_id": "Q1", "number": 1, "max_marks": 10},
            {"question_id": "Q2", "number": 2, "max_marks": 15},
            {"question_id": "Q3", "number": 3, "max_marks": 20}
        ],
        "human_marks_by_qid": {
            "Q1": 8,
            "Q2": 12,
            "Q3": 18
        }
    }
    
    print("📤 Request:")
    print(json.dumps(payload_legacy, indent=2))
    
    try:
        response = httpx.post(f"{API_BASE}/questions/config", json=payload_legacy)
        response.raise_for_status()
        print("\n✅ Success! Legacy format still works")
        
        # Verify
        response = httpx.get(f"{API_BASE}/questions/{session_id}")
        response.raise_for_status()
        questions = response.json()["questions"]
        
        print("\n📥 Saved questions:")
        for q in questions:
            print(f"   {q['question_id']}: number={q['number']}, max_marks={q['max_marks']}")
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ Request failed: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Test Case 3: Mixed format (should fail with validation error)
    print("\n" + "=" * 80)
    print("📝 Test Case 3: Mixed format (should fail)")
    print("-" * 40)
    
    payload_mixed = {
        "session_id": session_id,
        "questions": [
            {"question_id": "MIX.1", "max_marks": 10},  # No number
            {"question_id": "MIX.2", "number": 2, "max_marks": 15},  # Has number
        ],
        "human_marks_by_qid": {
            "MIX.1": 8,
            "MIX.2": 12
        }
    }
    
    print("📤 Request:")
    print(json.dumps(payload_mixed, indent=2))
    
    try:
        response = httpx.post(f"{API_BASE}/questions/config", json=payload_mixed)
        response.raise_for_status()
        print("\n❌ Unexpected success! Mixed format should have failed")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            print("\n✅ Correctly rejected mixed format!")
            print(f"   Error: {e.response.json().get('detail', 'Unknown error')}")
        else:
            print(f"\n❌ Unexpected error: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Test Case 4: Reordering questions (array order determines number)
    print("\n" + "=" * 80)
    print("📝 Test Case 4: Reordering questions")
    print("-" * 40)
    
    payload_reorder = {
        "session_id": session_id,
        "questions": [
            {"question_id": "APP.2", "max_marks": 25},  # Now first
            {"question_id": "APP.1", "max_marks": 20},  # Now second
            {"question_id": "DES.2", "max_marks": 15},  # Now third
            {"question_id": "DES.1", "max_marks": 10}   # Now fourth
        ],
        "human_marks_by_qid": {
            "DES.1": 8,
            "DES.2": 12,
            "APP.1": 18,
            "APP.2": 22
        }
    }
    
    print("📤 Request (reordered):")
    print(json.dumps(payload_reorder, indent=2))
    
    try:
        response = httpx.post(f"{API_BASE}/questions/config", json=payload_reorder)
        response.raise_for_status()
        print("\n✅ Success! Questions reordered")
        
        # Verify new ordering
        response = httpx.get(f"{API_BASE}/questions/{session_id}")
        response.raise_for_status()
        questions = response.json()["questions"]
        
        print("\n📥 New question order:")
        for q in questions:
            print(f"   Position {q['number']}: {q['question_id']} (max_marks={q['max_marks']})")
        
        # Verify new numbering
        expected_order = {
            "APP.2": 1,
            "APP.1": 2,
            "DES.2": 3,
            "DES.1": 4
        }
        
        all_correct = True
        for q in questions:
            if q["number"] != expected_order.get(q["question_id"]):
                print(f"   ❌ Wrong number for {q['question_id']}: got {q['number']}, expected {expected_order[q['question_id']]}")
                all_correct = False
        
        if all_correct:
            print("\n   ✅ Array order correctly determines question numbering!")
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ Request failed: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def main():
    """Run all tests"""
    
    print("\n" + "🚀" * 40)
    print("AUTO-NUMBERING TEST SUITE")
    print("🚀" * 40)
    
    print("\nThis script tests the auto-numbering feature:")
    print("- Frontend sends only question_id and max_marks")
    print("- Backend auto-generates numbers from array position")
    print("- Array order determines question order (1-indexed)")
    print("- Backward compatible with legacy format")
    
    # Create test session
    session_id = create_test_session()
    
    # Run tests
    test_auto_numbering(session_id)
    
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print("\n✅ Auto-numbering feature tested!")
    print("\nFrontend benefits:")
    print("- ✨ Simpler JSON structure (no number field needed)")
    print("- 📝 Only send: {\"question_id\": \"Q1\", \"max_marks\": 10}")
    print("- 🔢 Array index becomes question number automatically")
    print("- ↕️  Reorder questions by changing array order")
    print("- 🔄 Backward compatible with existing code")
    print("\nExample frontend code:")
    print("""
    // Old way (still works):
    questions: [
        {question_id: "Q1", number: 1, max_marks: 10},
        {question_id: "Q2", number: 2, max_marks: 15}
    ]
    
    // New simplified way:
    questions: [
        {question_id: "Q1", max_marks: 10},  // Gets number: 1
        {question_id: "Q2", max_marks: 15}   // Gets number: 2
    ]
    """)

if __name__ == "__main__":
    main()
