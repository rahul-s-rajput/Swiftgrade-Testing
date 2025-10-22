#!/usr/bin/env python3
"""
Quick fix script to resolve database schema cache issues.
Run this after applying migration 004_verify_and_fix_schema.sql
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.supabase_client import supabase

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def verify_schema():
    """Verify that the schema is correct after migration."""
    
    print("\n" + "="*80)
    print("🔍 VERIFYING DATABASE SCHEMA")
    print("="*80)
    
    # Check rubric_result columns
    print("\n📋 Checking rubric_result table...")
    try:
        result = supabase.rpc('exec_sql', {
            'query': """
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                  AND table_name = 'rubric_result'
                ORDER BY ordinal_position;
            """
        }).execute()
        
        rubric_cols = [row['column_name'] for row in result.data]
        print(f"  Columns: {rubric_cols}")
        
        # Check for token columns (should NOT exist)
        token_cols = [
            'cache_creation_input_tokens', 'cache_read_input_tokens',
            'input_tokens', 'output_tokens', 'reasoning_tokens',
            'total_tokens', 'cost_estimate'
        ]
        found_token_cols = [col for col in token_cols if col in rubric_cols]
        
        if found_token_cols:
            print(f"  ❌ ERROR: Found token columns in rubric_result: {found_token_cols}")
            print(f"  ⚠️  These should be removed. Run migration 004.")
            return False
        else:
            print(f"  ✅ No token columns in rubric_result (correct!)")
    except Exception as e:
        print(f"  ❌ ERROR checking rubric_result: {e}")
        return False
    
    # Check token_usage columns
    print("\n📊 Checking token_usage table...")
    try:
        result = supabase.rpc('exec_sql', {
            'query': """
                SELECT column_name, data_type, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                  AND table_name = 'token_usage'
                  AND column_name IN ('phase', 'cache_creation_input_tokens')
                ORDER BY column_name;
            """
        }).execute()
        
        token_cols = {row['column_name']: row for row in result.data}
        
        # Check for phase column
        if 'phase' not in token_cols:
            print(f"  ❌ ERROR: phase column missing from token_usage")
            print(f"  ⚠️  Run migration 003_add_phase_to_token_usage.sql")
            return False
        else:
            print(f"  ✅ phase column exists in token_usage")
        
        # Check for cache columns
        if 'cache_creation_input_tokens' not in token_cols:
            print(f"  ❌ ERROR: cache_creation_input_tokens missing from token_usage")
            return False
        else:
            print(f"  ✅ cache_creation_input_tokens exists in token_usage")
            
    except Exception as e:
        print(f"  ❌ ERROR checking token_usage: {e}")
        return False
    
    # Check unique constraints
    print("\n🔐 Checking unique constraints...")
    try:
        result = supabase.rpc('exec_sql', {
            'query': """
                SELECT 
                  con.conname AS constraint_name,
                  array_agg(att.attname ORDER BY att.attnum) AS columns
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
                WHERE nsp.nspname = 'public'
                  AND rel.relname = 'token_usage'
                  AND con.contype = 'u'
                GROUP BY con.conname;
            """
        }).execute()
        
        constraints = {row['constraint_name']: row['columns'] for row in result.data}
        
        # Check if phase is in unique constraint
        found_phase_constraint = False
        for name, cols in constraints.items():
            if 'phase' in cols:
                found_phase_constraint = True
                print(f"  ✅ Unique constraint '{name}' includes phase column")
                print(f"     Columns: {cols}")
        
        if not found_phase_constraint:
            print(f"  ❌ ERROR: No unique constraint includes phase column")
            print(f"  ⚠️  The constraint should be: (session_id, model_name, try_index, phase)")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR checking constraints: {e}")
        return False
    
    print("\n" + "="*80)
    print("✅ SCHEMA VERIFICATION PASSED!")
    print("="*80)
    print("\n✨ Your database schema is correctly configured for:")
    print("  • Separate rubric and assessment token tracking")
    print("  • Performance analysis per phase")
    print("  • Cost breakdown per phase")
    print("\n")
    
    return True

def refresh_schema_cache():
    """Refresh PostgREST schema cache."""
    print("\n🔄 Refreshing PostgREST schema cache...")
    try:
        result = supabase.rpc('exec_sql', {
            'query': "NOTIFY pgrst, 'reload schema';"
        }).execute()
        print("  ✅ Schema cache refresh signal sent")
        print("  ⏳ Wait 30-60 seconds for cache to refresh")
        print("     OR restart your API server for immediate effect")
    except Exception as e:
        print(f"  ⚠️  Could not refresh cache: {e}")
        print("     Try running this SQL directly in Supabase SQL Editor:")
        print("     NOTIFY pgrst, 'reload schema';")

if __name__ == "__main__":
    load_dotenv()
    
    print("\n🚀 Database Schema Verification Tool")
    print("="*80)
    
    # Verify schema
    is_valid = verify_schema()
    
    if is_valid:
        print("\n✅ All checks passed! Your schema is correctly configured.")
        print("\n💡 If you're still seeing errors, try:")
        print("   1. Restart your API server")
        print("   2. Wait 1 minute and retry")
        print("   3. Check Supabase logs for any issues")
    else:
        print("\n❌ Schema verification failed. Please:")
        print("   1. Run migration: app/migrations/004_verify_and_fix_schema.sql")
        print("   2. Run this script again to verify")
        
        refresh_schema_cache()
    
    print("\n" + "="*80)
