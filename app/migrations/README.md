# Database Migrations

This folder contains database migration scripts for the grading rubric feature.

---

## 📁 Files

### Migration Scripts
- **`001_add_grading_rubric_support.sql`** - Main migration script
- **`001_add_grading_rubric_support_ROLLBACK.sql`** - Rollback script
- **`run_migration.py`** - Helper script to view and run migrations

---

## 🚀 How to Run the Migration

### Method 1: Supabase Dashboard (Recommended)

This is the easiest and safest method.

1. **Backup your database first!** (Optional but recommended)
   - Go to Supabase Dashboard → Database → Backups
   - Create a manual backup

2. **Open the SQL Editor**
   - Go to Supabase Dashboard
   - Navigate to SQL Editor
   - Click "New Query"

3. **Copy the migration SQL**
   - Run the helper script to display the SQL:
     ```bash
     cd app/migrations
     python run_migration.py
     # Choose option 1 to show SQL
     ```
   - OR open `001_add_grading_rubric_support.sql` and copy the contents

4. **Paste and execute**
   - Paste the SQL into the query editor
   - Click "Run" (or press Ctrl+Enter)
   - Check for success messages in the output

5. **Verify the migration**
   - Go to Database → Tables
   - Check that `rubric_result` table exists
   - Go to Database → Indexes
   - Verify indexes were created

### Method 2: Command Line (psql)

If you have PostgreSQL command line tools installed:

```bash
# Get your connection string from Supabase Dashboard → Settings → Database
# It looks like: postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres

# Run the migration
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" -f app/migrations/001_add_grading_rubric_support.sql

# OR if you have .env configured
psql $DATABASE_URL -f app/migrations/001_add_grading_rubric_support.sql
```

### Method 3: Python Helper Script

The helper script displays the SQL for you to copy:

```bash
cd app/migrations
python run_migration.py
```

Then follow the on-screen instructions.

---

## 📋 What the Migration Does

### 1. Creates `rubric_result` Table
Stores results from rubric analysis LLM calls.

**Columns:**
- `id` (UUID, Primary Key)
- `session_id` (UUID, Foreign Key to session)
- `model_name` (TEXT) - Rubric model identifier
- `try_index` (INTEGER) - Attempt number
- `rubric_response` (TEXT) - Extracted rubric text
- `raw_output` (JSONB) - Full API response
- `validation_errors` (JSONB) - Parsing errors
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Constraints:**
- Foreign key to `session(id)` with CASCADE delete
- Unique constraint on `(session_id, model_name, try_index)`

### 2. Creates Indexes
Performance indexes for common queries:
- `idx_rubric_result_session` - Query by session
- `idx_rubric_result_model_try` - Query by model/try
- `idx_rubric_result_session_model` - Composite index

### 3. Updates `image` Table
Adds new role type for grading rubric images.

**Before:**
- Allowed roles: `'student'`, `'answer_key'`

**After:**
- Allowed roles: `'student'`, `'answer_key'`, `'grading_rubric'`

### 4. Updates `session` Table
Adds columns to track model pairs (optional metadata).

**New columns:**
- `rubric_models` (TEXT[]) - Array of rubric model IDs
- `assessment_models` (TEXT[]) - Array of assessment model IDs

### 5. Adds Triggers
Auto-update `updated_at` timestamp on row changes.

---

## 🔄 How to Rollback

If you need to undo the migration:

### Using Supabase Dashboard

1. **⚠️ WARNING: This will delete all `rubric_result` data!**

2. **Open SQL Editor**
   - Go to Supabase Dashboard → SQL Editor

3. **Copy the rollback SQL**
   - Run: `python run_migration.py` and choose option 2
   - OR open `001_add_grading_rubric_support_ROLLBACK.sql`

4. **Execute the rollback**
   - Paste into SQL Editor
   - Click "Run"
   - Verify success messages

### Using Command Line

```bash
psql "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres" -f app/migrations/001_add_grading_rubric_support_ROLLBACK.sql
```

---

## ✅ Verification Checklist

After running the migration, verify:

- [ ] `rubric_result` table exists
  ```sql
  SELECT * FROM information_schema.tables 
  WHERE table_name = 'rubric_result';
  ```

- [ ] Indexes were created
  ```sql
  SELECT indexname FROM pg_indexes 
  WHERE tablename = 'rubric_result';
  ```

- [ ] Image constraint updated
  ```sql
  SELECT conname, consrc FROM pg_constraint 
  WHERE conname = 'image_role_check';
  ```

- [ ] Session columns added
  ```sql
  SELECT column_name FROM information_schema.columns 
  WHERE table_name = 'session' 
  AND column_name IN ('rubric_models', 'assessment_models');
  ```

- [ ] Triggers created
  ```sql
  SELECT tgname FROM pg_trigger 
  WHERE tgrelid = 'rubric_result'::regclass;
  ```

---

## 🐛 Troubleshooting

### Error: "relation 'session' does not exist"
**Solution:** Make sure you're running the migration on the correct database. Check your connection string.

### Error: "permission denied"
**Solution:** Make sure you're using the service role key (not anon key) in your `.env` file.

### Error: "constraint already exists"
**Solution:** The migration has already been run. Check if `rubric_result` table exists.

### Error: "function gen_random_uuid() does not exist"
**Solution:** Make sure the `uuid-ossp` extension is enabled:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

## 📊 Database Schema After Migration

```
session
├── id (PK)
├── name
├── status
├── created_at
├── selected_models
├── rubric_models (NEW)
└── assessment_models (NEW)

image
├── id (PK)
├── session_id (FK → session.id)
├── role (CHECK: student | answer_key | grading_rubric)  ← UPDATED
├── url
└── order_index

rubric_result (NEW)
├── id (PK)
├── session_id (FK → session.id)
├── model_name
├── try_index
├── rubric_response
├── raw_output
├── validation_errors
├── created_at
└── updated_at
└── UNIQUE (session_id, model_name, try_index)

result (EXISTING)
├── id (PK)
├── session_id (FK → session.id)
├── question_id
├── model_name
├── try_index
├── marks_awarded
├── rubric_notes
├── raw_output
└── validation_errors
```

---

## 🔒 Security Notes

- Always backup your database before running migrations
- Use service role key (has admin privileges)
- Never commit your connection string or keys to git
- Review SQL before executing in production
- Test migrations on development/staging first

---

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the migration SQL file
3. Check Supabase logs in Dashboard → Logs
4. Verify your environment variables are correct

---

## 📝 Migration History

| Version | Date | Description | Status |
|---------|------|-------------|--------|
| 001 | 2025-01-XX | Add grading rubric support | ✅ Ready |

---

**Next Steps After Migration:**

1. ✅ Mark Phase 1 as complete in Implementation Plan
2. ✅ Update Quick Checklist
3. ➡️ Move to Phase 2: Backend Schemas (`app/schemas.py`)
