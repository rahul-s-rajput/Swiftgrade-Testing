"""
Test script to verify backend is working correctly.
Run this after creating the result table in Supabase.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test if the backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running on port 8000?")
        return False

def test_create_session():
    """Test creating a new session"""
    try:
        response = requests.post(f"{BASE_URL}/sessions")
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Created session: {data['session_id']}")
            return data['session_id']
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return None

def test_register_image(session_id):
    """Test registering an image"""
    try:
        payload = {
            "session_id": session_id,
            "role": "student",
            "url": "https://example.com/test-image.png",
            "order_index": 0
        }
        response = requests.post(f"{BASE_URL}/images/register", json=payload)
        if response.status_code == 200:
            print("✅ Registered image successfully")
            return True
        else:
            print(f"❌ Failed to register image: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error registering image: {e}")
        return False

def test_questions_config(session_id):
    """Test configuring questions"""
    try:
        payload = {
            "session_id": session_id,
            "questions": [
                {"question_id": "Q1", "number": 1, "max_marks": 10},
                {"question_id": "Q2", "number": 2, "max_marks": 5}
            ],
            "human_marks_by_qid": {"Q1": 8, "Q2": 4}
        }
        response = requests.post(f"{BASE_URL}/questions/config", json=payload)
        if response.status_code == 200:
            print("✅ Configured questions successfully")
            return True
        else:
            print(f"❌ Failed to configure questions: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error configuring questions: {e}")
        return False

def main():
    print("=" * 50)
    print("BACKEND TESTING SCRIPT")
    print("=" * 50)
    print()
    
    # Test 1: Health check
    if not test_health():
        print("\n⚠️  Please start the backend with: uvicorn app.main:app --reload --port 8000")
        return
    
    print()
    
    # Test 2: Create session
    session_id = test_create_session()
    if not session_id:
        print("\n⚠️  Cannot proceed without a session")
        return
    
    print()
    
    # Test 3: Register image
    if not test_register_image(session_id):
        print("\n⚠️  Image registration failed")
    
    print()
    
    # Test 4: Configure questions
    if not test_questions_config(session_id):
        print("\n⚠️  Questions configuration failed")
        print("\n🔍 This usually means the 'result' table is missing.")
        print("   Please create it using the SQL in BACKEND_FIX_SIMPLE.md")
    else:
        print("\n✅ All basic tests passed! Backend is working correctly.")
    
    print()
    print("=" * 50)

if __name__ == "__main__":
    main()
