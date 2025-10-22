#!/usr/bin/env python3
"""
Verify that the bug fixes have been applied correctly.
This script checks:
1. Database schema is updated
2. JSON parser is working
3. Token storage is configured correctly
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def verify_database_schema():
    """Verify that the phase column exists in token_usage table."""
    print("\n" + "="*80)
    print("🔍 Verifying Database Schema")
    print("="*80)
    
    try:
        from app.supabase_client import supabase
        
        # Query to check if phase column exists
        result = supabase.table("token_usage").select("phase").limit(1).execute()
        
        print("✅ Phase column exists in token_usage table")
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if "column" in error_msg and "phase" in error_msg:
            print("❌ Phase column does not exist in token_usage table")
            print("   💡 Run: python app/migrations/run_phase_migration.py")
            return False
        else:
            print(f"❌ Database connection error: {e}")
            print("   💡 Check your .env file and Supabase credentials")
            return False


def verify_json_parser():
    """Verify that the JSON parser utility exists and works."""
    print("\n" + "="*80)
    print("🔍 Verifying JSON Parser Utility")
    print("="*80)
    
    try:
        from app.util.json_parser import parse_llm_json_response, sanitize_json_escapes
        
        # Test with sample problematic JSON
        test_cases = [
            # Case 1: Valid JSON with markdown fence
            ('```json\n{"test": "value"}\n```', True),
            
            # Case 2: JSON with preamble
            ('Here is the result:\n{"test": "value"}', True),
            
            # Case 3: JSON with invalid escape (should be fixed)
            ('{"test": "line1\\nline2"}', True),
            
            # Case 4: Invalid JSON (should fail gracefully)
            ('not json at all', False),
        ]
        
        all_passed = True
        for i, (test_input, should_succeed) in enumerate(test_cases, 1):
            obj, error = parse_llm_json_response(test_input, strict=False)
            
            if should_succeed:
                if obj is not None:
                    print(f"  ✅ Test {i}: Parsed successfully")
                else:
                    print(f"  ❌ Test {i}: Failed to parse (expected success)")
                    print(f"     Error: {error}")
                    all_passed = False
            else:
                if obj is None:
                    print(f"  ✅ Test {i}: Correctly rejected invalid JSON")
                else:
                    print(f"  ⚠️ Test {i}: Parsed invalid JSON (unexpected)")
        
        if all_passed:
            print("\n✅ JSON parser is working correctly")
            return True
        else:
            print("\n❌ Some JSON parser tests failed")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import JSON parser utility: {e}")
        print("   💡 Ensure app/util/json_parser.py exists")
        return False
    except Exception as e:
        print(f"❌ JSON parser test failed: {e}")
        return False


def verify_code_updates():
    """Verify that grade.py has been updated with the fixes."""
    print("\n" + "="*80)
    print("🔍 Verifying Code Updates")
    print("="*80)
    
    grade_file = Path(__file__).parent / "app" / "routers" / "grade.py"
    
    if not grade_file.exists():
        print(f"❌ grade.py not found at: {grade_file}")
        return False
    
    with open(grade_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "JSON parser import": "from ..util.json_parser import parse_llm_json_response",
        "Rubric phase='rubric'": '"phase": "rubric"',
        "Assessment phase='assessment'": '"phase": "assessment"',
        "Updated conflict clause": 'on_conflict="session_id,model_name,try_index,phase"',
    }
    
    all_found = True
    for check_name, check_str in checks.items():
        if check_str in content:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name} - NOT FOUND")
            all_found = False
    
    if all_found:
        print("\n✅ All code updates are present")
        return True
    else:
        print("\n❌ Some code updates are missing")
        print("   💡 Review BUGFIX_README.md for manual update instructions")
        return False


def verify_environment():
    """Verify that the environment is properly configured."""
    print("\n" + "="*80)
    print("🔍 Verifying Environment Configuration")
    print("="*80)
    
    required_vars = {
        "OPENROUTER_API_KEY": "OpenRouter API access",
        "SUPABASE_URL": "Supabase database connection",
        "SUPABASE_SERVICE_ROLE_KEY": "Supabase admin access",
    }
    
    all_present = True
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            print(f"  ✅ {var_name} ({description})")
        else:
            print(f"  ❌ {var_name} - NOT SET ({description})")
            all_present = False
    
    if all_present:
        print("\n✅ Environment is properly configured")
        return True
    else:
        print("\n❌ Some environment variables are missing")
        print("   💡 Check your .env file")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "="*80)
    print("🧪 Bug Fix Verification Script")
    print("="*80)
    print("Checking that all fixes have been applied correctly...\n")
    
    results = {
        "Environment": verify_environment(),
        "Code Updates": verify_code_updates(),
        "JSON Parser": verify_json_parser(),
        "Database Schema": verify_database_schema(),
    }
    
    print("\n" + "="*80)
    print("📊 VERIFICATION SUMMARY")
    print("="*80)
    
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "="*80)
        print("🎉 All verifications passed! Your system is ready.")
        print("="*80)
        print("\n💡 Next steps:")
        print("  1. Restart your backend server")
        print("  2. Test grading with both GPT and Gemini models")
        print("  3. Check Performance Analysis tab for token breakdown")
        print()
        return 0
    else:
        print("\n" + "="*80)
        print("⚠️ Some verifications failed. Please review and fix.")
        print("="*80)
        print("\n💡 See BUGFIX_README.md for detailed instructions")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
