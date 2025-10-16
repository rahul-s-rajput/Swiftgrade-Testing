#!/usr/bin/env python3
"""
Database Migration Runner for Grading Rubric Feature
Runs SQL migrations against Supabase PostgreSQL database
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.supabase_client import supabase


def print_header(message: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80)


def print_success(message: str):
    """Print a success message"""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message"""
    print(f"✗ {message}")


def read_sql_file(filepath: Path) -> str:
    """Read SQL file contents"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print_error(f"Migration file not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error reading migration file: {e}")
        sys.exit(1)


def run_migration(sql_content: str) -> bool:
    """
    Run SQL migration using Supabase client
    
    Note: Supabase Python client doesn't directly support raw SQL execution.
    This function uses the rpc method to execute SQL via a stored procedure.
    
    Alternative: Use psycopg2 or run SQL directly via Supabase Dashboard.
    """
    try:
        print("\n📝 Executing migration SQL...")
        print("⚠️  Note: The Supabase Python client has limited SQL execution support.")
        print("    You have two options:\n")
        print("    Option 1 (Recommended): Run this SQL in Supabase SQL Editor")
        print("    Option 2: Use psql command line tool")
        print("\n" + "-" * 80)
        
        return True
        
    except Exception as e:
        print_error(f"Migration failed: {e}")
        return False


def show_sql_content(filepath: Path):
    """Display SQL content for manual execution"""
    sql = read_sql_file(filepath)
    
    print("\n" + "=" * 80)
    print("SQL MIGRATION CONTENT")
    print("Copy and paste this into Supabase SQL Editor")
    print("=" * 80 + "\n")
    print(sql)
    print("\n" + "=" * 80)


def main():
    """Main migration runner"""
    migrations_dir = Path(__file__).parent
    migration_file = migrations_dir / "001_add_grading_rubric_support.sql"
    rollback_file = migrations_dir / "001_add_grading_rubric_support_ROLLBACK.sql"
    
    print_header("Grading Rubric Database Migration")
    
    # Check if migration file exists
    if not migration_file.exists():
        print_error(f"Migration file not found: {migration_file}")
        sys.exit(1)
    
    print(f"\n📄 Migration file: {migration_file.name}")
    print(f"📄 Rollback file: {rollback_file.name}")
    
    # Check Supabase connection
    try:
        print("\n🔌 Checking Supabase connection...")
        
        # Test connection by querying a system table
        result = supabase.table("session").select("id").limit(1).execute()
        print_success("Connected to Supabase successfully")
        
    except Exception as e:
        print_error(f"Failed to connect to Supabase: {e}")
        print("\n💡 Make sure your .env file has:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    
    # Show options
    print("\n" + "=" * 80)
    print("MIGRATION OPTIONS")
    print("=" * 80)
    print("\n1. Show SQL content (for manual execution in Supabase Dashboard)")
    print("2. Show rollback SQL content")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        show_sql_content(migration_file)
        print("\n" + "=" * 80)
        print("INSTRUCTIONS:")
        print("=" * 80)
        print("\n1. Go to your Supabase Dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Create a new query")
        print("4. Copy and paste the SQL above")
        print("5. Click 'Run' to execute the migration")
        print("\n⚠️  Important: Make sure to backup your database first!")
        
    elif choice == "2":
        show_sql_content(rollback_file)
        print("\n" + "=" * 80)
        print("ROLLBACK INSTRUCTIONS:")
        print("=" * 80)
        print("\n⚠️  WARNING: This will delete all rubric_result data!")
        print("\n1. Go to your Supabase Dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Create a new query")
        print("4. Copy and paste the SQL above")
        print("5. Click 'Run' to execute the rollback")
        
    elif choice == "3":
        print("\n👋 Exiting...")
        sys.exit(0)
    
    else:
        print_error("Invalid choice")
        sys.exit(1)
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
