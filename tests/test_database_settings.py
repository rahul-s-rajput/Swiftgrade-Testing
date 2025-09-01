#!/usr/bin/env python3
"""
Test script to debug prompt settings storage and retrieval.

Run this script to verify that custom prompts are being saved and loaded correctly.
"""

import httpx
import json
import asyncio
import os
import sys

# Add the app directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.supabase_client import supabase

async def test_prompt_settings():
    """Test prompt settings storage and retrieval"""
    
    print("=" * 80)
    print("🧪 PROMPT SETTINGS DATABASE TEST")
    print("=" * 80)
    print()
    
    # Test 1: Check if app_settings table exists and has data
    print("📊 Test 1: Checking app_settings table...")
    try:
        result = supabase.table("app_settings").select("*").execute()
        print(f"✅ Table exists with {len(result.data)} rows")
        for row in result.data:
            print(f"  - Key: {row.get('key')}")
            if row.get('key') == 'prompt_settings':
                value = row.get('value', {})
                if isinstance(value, dict):
                    sys_template = value.get('system_template')
                    user_template = value.get('user_template')
                    print(f"    System template: {len(sys_template) if sys_template else 0} chars")
                    print(f"    User template: {len(user_template) if user_template else 0} chars")
                    if sys_template:
                        print(f"    System preview: {sys_template[:100]}...")
                    if user_template:
                        print(f"    User preview: {user_template[:100]}...")
                else:
                    print(f"    Value type: {type(value)}")
                    print(f"    Value: {value}")
    except Exception as e:
        print(f"❌ Error accessing table: {e}")
    print()
    
    # Test 2: Try to retrieve settings using the same query as grade.py
    print("📊 Test 2: Testing grade.py query (select value only)...")
    try:
        res = supabase.table("app_settings").select("value").eq("key", "prompt_settings").limit(1).execute()
        rows = res.data or []
        print(f"  Found {len(rows)} rows")
        if rows:
            print(f"  Raw row data: {json.dumps(rows[0], indent=2)[:500]}")
            value = rows[0].get("value")
            print(f"  Value type: {type(value)}")
            if value:
                print(f"  Has system_template: {'system_template' in value if isinstance(value, dict) else False}")
                print(f"  Has user_template: {'user_template' in value if isinstance(value, dict) else False}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 3: Try with key,value selection (like settings.py)
    print("📊 Test 3: Testing settings.py query (select key,value)...")
    try:
        res = supabase.table("app_settings").select("key,value").eq("key", "prompt_settings").limit(1).execute()
        rows = res.data or []
        print(f"  Found {len(rows)} rows")
        if rows:
            print(f"  Raw row data: {json.dumps(rows[0], indent=2)[:500]}")
            value = rows[0].get("value")
            print(f"  Value type: {type(value)}")
            if value:
                print(f"  Has system_template: {'system_template' in value if isinstance(value, dict) else False}")
                print(f"  Has user_template: {'user_template' in value if isinstance(value, dict) else False}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 4: Test saving and retrieving
    print("📊 Test 4: Testing save and retrieve cycle...")
    test_system = "TEST SYSTEM TEMPLATE"
    test_user = "TEST USER TEMPLATE"
    
    try:
        # Save
        print("  Saving test templates...")
        result = supabase.table("app_settings").upsert(
            {
                "key": "prompt_settings_test",
                "value": {
                    "system_template": test_system,
                    "user_template": test_user,
                },
            },
            on_conflict="key",
        ).execute()
        print(f"  ✅ Saved successfully")
        
        # Retrieve
        print("  Retrieving test templates...")
        res = supabase.table("app_settings").select("value").eq("key", "prompt_settings_test").limit(1).execute()
        rows = res.data or []
        if rows:
            value = rows[0].get("value", {})
            retrieved_sys = value.get("system_template")
            retrieved_usr = value.get("user_template")
            
            if retrieved_sys == test_system and retrieved_usr == test_user:
                print("  ✅ Retrieved templates match!")
            else:
                print("  ❌ Templates don't match:")
                print(f"    System match: {retrieved_sys == test_system}")
                print(f"    User match: {retrieved_usr == test_user}")
        else:
            print("  ❌ No rows retrieved")
            
        # Clean up
        supabase.table("app_settings").delete().eq("key", "prompt_settings_test").execute()
        print("  ✅ Test data cleaned up")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    print("=" * 80)
    print("📋 RECOMMENDATIONS:")
    print("=" * 80)
    print("1. Check if the prompt_settings key exists in the database")
    print("2. Verify that the value column contains a JSON object with system_template and user_template")
    print("3. Ensure the Settings page has been used to save prompts at least once")
    print("4. Check Supabase logs for any database errors")
    print()

if __name__ == "__main__":
    asyncio.run(test_prompt_settings())
