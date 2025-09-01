#!/usr/bin/env python3
"""
Script to manually save custom prompt settings to the database.
This ensures the settings are properly stored for the grading system to use.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.supabase_client import supabase

# Custom prompts from the user
CUSTOM_SYSTEM_TEMPLATE = """<Role>
You are a teacher whose job is to grade student assessments.
</Role>

<Task>
You will be given three inputs:
- `answer_key`
- `questions_list`
- `student_assessments`
For each student in `student_assessments`, you must:
1. Extract the student's `first_name`, `last_name` and `Student_ID`.
2. For each question in `questions_list`, assign a `mark` and provide `feedback`.
3. Format the final output for each student as a single JSON object.
</Task>

<Instructions>
Follow the detailed grading instructions and feedback rubric precisely.
</Instructions>

<Answer_Key>
Here are the answer key pages. Use these to determine correct answers and any specific grading criteria:
[Answer key]
</Answer_Key>

<Question_List>
Here are the specific questions to grade. Only grade these questions in the student's assessment:
[Question list]
</Question_List>"""

CUSTOM_USER_TEMPLATE = """<Student_Assessments>
Here are the pages of the student's test:
[Student assessment]
</Student_Assessments>"""

def save_custom_settings():
    """Save custom prompt settings to database"""
    print("=" * 80)
    print("💾 SAVING CUSTOM PROMPT SETTINGS")
    print("=" * 80)
    print()
    
    try:
        # First, check if settings exist
        print("📊 Checking existing settings...")
        res = supabase.table("app_settings").select("key,value").eq("key", "prompt_settings").limit(1).execute()
        if res.data:
            print("  Found existing settings, will update them")
        else:
            print("  No existing settings, will create new")
        
        # Save the custom templates
        print("\n📝 Saving custom templates...")
        print(f"  System template: {len(CUSTOM_SYSTEM_TEMPLATE)} chars")
        print(f"  User template: {len(CUSTOM_USER_TEMPLATE)} chars")
        
        result = supabase.table("app_settings").upsert(
            {
                "key": "prompt_settings",
                "value": {
                    "system_template": CUSTOM_SYSTEM_TEMPLATE,
                    "user_template": CUSTOM_USER_TEMPLATE,
                },
            },
            on_conflict="key",
        ).execute()
        
        print("\n✅ Settings saved successfully!")
        
        # Verify the save
        print("\n🔍 Verifying saved settings...")
        verify_res = supabase.table("app_settings").select("value").eq("key", "prompt_settings").limit(1).execute()
        if verify_res.data:
            value = verify_res.data[0].get("value", {})
            saved_sys = value.get("system_template", "")
            saved_usr = value.get("user_template", "")
            
            if saved_sys == CUSTOM_SYSTEM_TEMPLATE and saved_usr == CUSTOM_USER_TEMPLATE:
                print("  ✅ Verification successful! Templates match.")
            else:
                print("  ⚠️ Warning: Saved templates don't match!")
                print(f"    System match: {saved_sys == CUSTOM_SYSTEM_TEMPLATE}")
                print(f"    User match: {saved_usr == CUSTOM_USER_TEMPLATE}")
        else:
            print("  ❌ Could not verify - no data retrieved")
            
    except Exception as e:
        print(f"\n❌ Error saving settings: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ SETUP COMPLETE")
    print("=" * 80)
    print("\nYour custom prompt settings have been saved to the database.")
    print("The grading system should now use these templates.")
    print("\nTo verify:")
    print("1. Enable debug mode: OPENROUTER_DEBUG=1 in .env")
    print("2. Run a grading session")
    print("3. Check the backend logs for '✅ Using custom templates from settings'")
    print()
    
    return True

if __name__ == "__main__":
    save_custom_settings()
