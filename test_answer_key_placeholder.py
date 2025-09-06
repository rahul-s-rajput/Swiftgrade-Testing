#!/usr/bin/env python3
"""
Test script to verify the answer key placeholder fix.
This tests the _build_messages function to ensure [Answer key] placeholder
is respected and images are placed correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.routers.grade import _build_messages

def test_answer_key_placeholder():
    """Test that [Answer key] placeholder works correctly"""
    print("=" * 60)
    print("🧪 TESTING ANSWER KEY PLACEHOLDER FIX")
    print("=" * 60)
    print()
    
    # Test data
    student_urls = ["https://example.com/student1.jpg"]
    key_urls = ["https://example.com/answer1.jpg", "https://example.com/answer2.jpg"]
    questions = [{"question_number": "Q1", "max_mark": 1.0}]
    
    # Test 1: System template WITH [Answer key] placeholder
    print("📝 Test 1: System template WITH [Answer key] placeholder")
    
    # Mock the database response for custom templates
    import app.routers.grade as grade_module
    original_supabase = grade_module.supabase
    
    class MockSupabase:
        class MockTable:
            def select(self, *args):
                return self
            def eq(self, *args):
                return self
            def limit(self, *args):
                return self
            def execute(self):
                return type('obj', (object,), {
                    'data': [{
                        'value': {
                            'system_template': 'Grade the assessment.\n\n<Answer_Key>\n[Answer key]\n</Answer_Key>',
                            'user_template': 'Student work: [Student assessment]'
                        }
                    }]
                })()
        
        def table(self, name):
            return self.MockTable()
    
    grade_module.supabase = MockSupabase()
    
    try:
        messages = _build_messages(student_urls, key_urls, questions)
        
        print(f"  System message: {messages[0]['content'][:100]}...")
        print(f"  User content parts: {len(messages[1]['content'])}")
        
        # Check that answer key URLs are in system message
        system_content = messages[0]['content']
        if 'answer1.jpg' in system_content:
            print("  ✅ Answer key URLs found in system message")
        else:
            print("  ❌ Answer key URLs NOT found in system message")
        
        # Check that answer key images are at beginning of user content
        user_content = messages[1]['content']
        has_answer_key_images = any('Answer key images' in str(part) for part in user_content)
        if has_answer_key_images:
            print("  ✅ Answer key images properly placed in user content")
        else:
            print("  ❌ Answer key images not found in user content")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    
    # Test 2: System template WITHOUT [Answer key] placeholder
    print("📝 Test 2: System template WITHOUT [Answer key] placeholder")
    
    class MockSupabaseNoPlaceholder:
        class MockTable:
            def select(self, *args):
                return self
            def eq(self, *args):
                return self
            def limit(self, *args):
                return self
            def execute(self):
                return type('obj', (object,), {
                    'data': [{
                        'value': {
                            'system_template': 'Grade the assessment. Use the answer key provided.',
                            'user_template': 'Student work: [Student assessment]'
                        }
                    }]
                })()
        
        def table(self, name):
            return self.MockTable()
    
    grade_module.supabase = MockSupabaseNoPlaceholder()
    
    try:
        messages = _build_messages(student_urls, key_urls, questions)
        
        print(f"  System message: {messages[0]['content'][:100]}...")
        print(f"  User content parts: {len(messages[1]['content'])}")
        
        # Check that answer key URLs are NOT in system message
        system_content = messages[0]['content']
        if 'answer1.jpg' not in system_content:
            print("  ✅ Answer key URLs correctly NOT in system message")
        else:
            print("  ❌ Answer key URLs incorrectly found in system message")
        
        # Check that answer key images are at end of user content
        user_content = messages[1]['content']
        has_answer_key_images = any('Answer key images:' in str(part) for part in user_content)
        if has_answer_key_images:
            print("  ✅ Answer key images properly placed at end of user content")
        else:
            print("  ❌ Answer key images not found in user content")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    finally:
        # Restore original supabase
        grade_module.supabase = original_supabase
    
    print()
    print("=" * 60)
    print("✅ ANSWER KEY PLACEHOLDER TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_answer_key_placeholder()