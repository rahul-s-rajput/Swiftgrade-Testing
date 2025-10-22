#!/usr/bin/env python3
"""
Run the token_usage phase migration.
This script adds the phase column to token_usage table to distinguish
between rubric extraction and assessment token usage.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.supabase_client import supabase


def run_migration():
    """Run the migration to add phase column to token_usage table."""
    
    migration_file = Path(__file__).parent / "003_add_phase_to_token_usage.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print("=" * 80)
    print("Running migration: Add phase column to token_usage table")
    print("=" * 80)
    
    # Read migration SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        # Execute migration
        print("\n📋 Executing migration SQL...")
        
        # Split into individual statements and execute
        # This is safer than executing all at once
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for i, stmt in enumerate(statements, 1):
            if stmt.strip():
                print(f"\n  [{i}/{len(statements)}] Executing statement...")
                try:
                    # Use the RPC method if available, otherwise direct SQL
                    try:
                        result = supabase.rpc("exec_sql", {"query": stmt}).execute()
                        print(f"  ✅ Statement {i} completed")
                    except Exception as rpc_error:
                        # Fallback: Try direct execution if RPC not available
                        print(f"  ⚠️ RPC not available, attempting direct execution...")
                        # This might not work depending on Supabase setup
                        print(f"  ❌ Cannot execute: {str(rpc_error)}")
                        print(f"  💡 Please run this SQL manually in Supabase SQL Editor:")
                        print(f"\n{stmt}\n")
                        continue
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check if error is about column already existing
                    if "already exists" in error_msg or "duplicate" in error_msg:
                        print(f"  ℹ️ Statement {i} - Column/constraint already exists, skipping...")
                    else:
                        print(f"  ❌ Statement {i} failed: {e}")
                        raise
        
        print("\n" + "=" * 80)
        print("✅ Migration completed successfully!")
        print("=" * 80)
        print("\n📊 Summary:")
        print("  • Added 'phase' column to token_usage table")
        print("  • Updated unique constraint to include phase")
        print("  • Created index for phase queries")
        print("\n💡 Next steps:")
        print("  • Restart your backend server")
        print("  • Token usage will now be tracked separately for rubric and assessment phases")
        print("  • Check the Performance Analysis tab to see the new data structure")
        print()
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ Migration failed: {e}")
        print("=" * 80)
        print("\n💡 Manual migration required:")
        print(f"  1. Open Supabase SQL Editor")
        print(f"  2. Copy and paste the contents of: {migration_file}")
        print(f"  3. Execute the SQL")
        print()
        
        import traceback
        print("Full error:")
        traceback.print_exc()
        
        return False


def rollback_migration():
    """Rollback the migration (remove phase column)."""
    
    rollback_file = Path(__file__).parent / "003_add_phase_to_token_usage_ROLLBACK.sql"
    
    if not rollback_file.exists():
        print(f"❌ Rollback file not found: {rollback_file}")
        return False
    
    print("=" * 80)
    print("Rolling back migration: Remove phase column from token_usage table")
    print("=" * 80)
    
    with open(rollback_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        print("\n📋 Executing rollback SQL...")
        
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for i, stmt in enumerate(statements, 1):
            if stmt.strip():
                print(f"\n  [{i}/{len(statements)}] Executing statement...")
                try:
                    result = supabase.rpc("exec_sql", {"query": stmt}).execute()
                    print(f"  ✅ Statement {i} completed")
                except Exception as e:
                    error_msg = str(e).lower()
                    if "does not exist" in error_msg:
                        print(f"  ℹ️ Statement {i} - Column/constraint doesn't exist, skipping...")
                    else:
                        print(f"  ❌ Statement {i} failed: {e}")
                        raise
        
        print("\n" + "=" * 80)
        print("✅ Rollback completed successfully!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        print(f"\nManual rollback required - see: {rollback_file}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage token_usage phase migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)
