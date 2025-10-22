#!/usr/bin/env python3
"""
Run the total_tokens column fix migration
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.supabase_client import supabase


def main():
    """Run the total_tokens fix migration"""
    print("=" * 80)
    print("FIXING TOTAL_TOKENS COLUMN")
    print("=" * 80)

    print("\n📝 The issue: total_tokens column is calculated instead of using OpenRouter's value")
    print("🔧 Solution: Replace calculated column with regular column")

    # SQL to fix the total_tokens column
    sql = """
    -- First, drop the generated column constraint
    ALTER TABLE token_usage DROP COLUMN IF EXISTS total_tokens;

    -- Add total_tokens as a regular integer column that will store OpenRouter's actual total_tokens value
    ALTER TABLE token_usage ADD COLUMN total_tokens integer null DEFAULT 0;

    -- Add comment to clarify this should store OpenRouter's total_tokens value
    COMMENT ON COLUMN token_usage.total_tokens IS 'Total tokens from OpenRouter response (should use usage.total_tokens directly, not calculated)';

    -- Create index for performance
    CREATE INDEX IF NOT EXISTS idx_token_usage_total_tokens ON public.token_usage(total_tokens);

    -- Update existing records with calculated totals as temporary fix
    UPDATE token_usage
    SET total_tokens = (input_tokens + output_tokens + COALESCE(reasoning_tokens, 0))
    WHERE total_tokens = 0;
    """

    print("\n" + "=" * 80)
    print("SQL TO EXECUTE:")
    print("=" * 80)
    print(sql)
    print("=" * 80)

    print("\n📋 INSTRUCTIONS:")
    print("1. Go to your Supabase Dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Copy and paste the SQL above")
    print("4. Click 'Run' to execute the migration")
    print("5. After running, the total_tokens will use OpenRouter's actual value")

    print("\n⚠️  Important: Make sure to backup your database first!")

    # Test connection
    try:
        print("\n🔌 Checking Supabase connection...")
        result = supabase.table("token_usage").select("id, total_tokens").limit(1).execute()
        print_success("Connected to Supabase successfully")

        if result.data:
            sample = result.data[0]
            print(f"📊 Sample total_tokens value: {sample.get('total_tokens', 'N/A')}")

    except Exception as e:
        print_error(f"Failed to connect to Supabase: {e}")
        print("\n💡 Make sure your .env file has:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ Migration script ready for manual execution")
    print("=" * 80)


def print_success(message: str):
    """Print a success message"""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message"""
    print(f"✗ {message}")


if __name__ == "__main__":
    main()