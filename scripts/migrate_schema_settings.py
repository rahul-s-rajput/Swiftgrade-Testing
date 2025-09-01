#!/usr/bin/env python3
"""
Migration script to add schema_template to existing prompt settings.
Run this script to update your existing settings with the new schema field.
"""

import httpx
import json
import sys

# Backend URL
API_BASE = "http://127.0.0.1:8000"

# Default schema template
DEFAULT_SCHEMA = """Return ONLY JSON with this exact schema (no markdown fences, no prose):
{"result":[{"first_name":string,"last_name":string,"answers":[{"question_id":string,"marks_awarded":number,"rubric_notes":string}]}]}
Use the question_id values exactly as provided in the Questions list."""

def migrate_settings_add_schema():
    """Add schema_template to existing settings"""
    
    print("=" * 80)
    print("🔧 MIGRATING SETTINGS TO INCLUDE SCHEMA TEMPLATE")
    print("=" * 80)
    print()
    
    try:
        # Get current settings
        print("📥 Fetching current settings...")
        response = httpx.get(f"{API_BASE}/settings/prompt")
        
        if response.status_code == 200:
            current = response.json()
            print("✅ Current settings retrieved")
            print(f"   System template: {len(current.get('system_template', ''))} chars")
            print(f"   User template: {len(current.get('user_template', ''))} chars")
            
            # Check if schema_template already exists
            if "schema_template" in current and current["schema_template"]:
                print("ℹ️ Schema template already exists in settings")
                print(f"   Schema template: {len(current['schema_template'])} chars")
                print("\nNo migration needed!")
                return
            
            # Add schema_template
            updated = {
                "system_template": current.get("system_template", ""),
                "user_template": current.get("user_template", ""),
                "schema_template": DEFAULT_SCHEMA
            }
            
            print()
            print("📤 Updating settings with schema template...")
            print(f"   Adding default schema template ({len(DEFAULT_SCHEMA)} chars)")
            
            response = httpx.put(
                f"{API_BASE}/settings/prompt",
                json=updated,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            print()
            print("✅ Settings migrated successfully!")
            print()
            print("📝 The schema template has been added to your settings.")
            print("   You can now customize it from the Settings page!")
            print()
            print("🎯 The schema template controls the JSON response format.")
            print("   You can modify it to match your specific grading needs.")
            
        else:
            print(f"⚠️ No existing settings found (status: {response.status_code})")
            print("Settings will be created with defaults on first save.")
            print()
            print("To create default settings now, save them from the UI Settings page.")
            
    except httpx.ConnectError:
        print("❌ Could not connect to backend at", API_BASE)
        print("Make sure the backend server is running:")
        print("  cd project")
        print("  python -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("You may need to manually save settings from the UI.")
    
    print()
    print("=" * 80)
    print("📋 NEXT STEPS")
    print("=" * 80)
    print()
    print("1. The backend now supports customizable schema templates")
    print("2. The Settings page needs to be updated to show the schema field")
    print("3. You can customize the JSON response format through settings")
    print()
    print("Example custom schemas you could use:")
    print()
    print("Simple format:")
    print('  {"grades": {"Q1": 10, "Q2": 15, "Q3": 12}}')
    print()
    print("Detailed format with confidence:")
    print('  {"result": [{"question_id": "Q1", "score": 10, "confidence": 0.95}]}')
    print()
    print("The parser is flexible and will adapt to different formats!")

if __name__ == "__main__":
    migrate_settings_add_schema()
