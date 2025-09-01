from fastapi import APIRouter, HTTPException, status
from ..supabase_client import supabase
from ..schemas import PromptSettingsReq, PromptSettingsRes


router = APIRouter()


DEFAULT_SYSTEM_TEMPLATE = (
    """
<Role>
You are a teacher whose job is to grade student assessments.
</Role>

<Task>
You will be given three inputs:
- `answer_key`
- `questions_list`
- `student_assessments`
For each student in `student_assessments`, you must:
1. Extract the student's `first_name`, `last_name` and `Student_ID`.
2. For each question in `questions_list`, assign a `marks_awarded` and provide `rubric_notes`.
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
</Question_List>
"""
    .strip()
)

DEFAULT_USER_TEMPLATE = (
    """
<Student_Assessments>
Here are the pages of the student's test:
[Student assessment]
</Student_Assessments>
"""
    .strip()
)

DEFAULT_SCHEMA_TEMPLATE = (
    """
Return ONLY JSON with this exact schema (no markdown fences, no prose):
{"result":[{"first_name":string,"last_name":string,"answers":[{"question_id":string,"marks_awarded":number,"rubric_notes":string}]}]}
Use the question_id values exactly as provided in the Questions list.
"""
    .strip()
)


TABLE = "app_settings"
KEY = "prompt_settings"


def _get_default_settings() -> PromptSettingsRes:
    return PromptSettingsRes(
        system_template=DEFAULT_SYSTEM_TEMPLATE,
        user_template=DEFAULT_USER_TEMPLATE,
        schema_template=DEFAULT_SCHEMA_TEMPLATE
    )


@router.get("/settings/prompt", response_model=PromptSettingsRes)
def get_prompt_settings() -> PromptSettingsRes:
    import logging
    from ..routers.grade import OPENROUTER_DEBUG
    
    try:
        if OPENROUTER_DEBUG:
            logging.info("\n" + "="*80)
            logging.info("🔍 FETCHING PROMPT SETTINGS")
            logging.info("="*80)
        
        res = supabase.table(TABLE).select("key,value").eq("key", KEY).limit(1).execute()
        rows = res.data or []
        
        if OPENROUTER_DEBUG:
            logging.info("📄 Found %s rows", len(rows))
            if rows:
                logging.info("📦 Raw data: %s", rows[0])
        
        if not rows:
            if OPENROUTER_DEBUG:
                logging.warning("⚠️ No settings found, returning defaults")
            return _get_default_settings()
        
        value = rows[0].get("value") or {}
        sys_t = value.get("system_template") or DEFAULT_SYSTEM_TEMPLATE
        usr_t = value.get("user_template") or DEFAULT_USER_TEMPLATE
        sch_t = value.get("schema_template") or DEFAULT_SCHEMA_TEMPLATE
        
        if OPENROUTER_DEBUG:
            logging.info("✅ Retrieved templates:")
            logging.info("  - System: %s chars", len(sys_t))
            logging.info("  - User: %s chars", len(usr_t))
            logging.info("  - Schema: %s chars", len(sch_t))
            logging.info("="*80 + "\n")
        
        return PromptSettingsRes(system_template=sys_t, user_template=usr_t, schema_template=sch_t)
    except Exception as e:
        if OPENROUTER_DEBUG:
            logging.error("❌ Error fetching settings: %s", str(e))
        # If table doesn't exist yet or other error, return defaults
        return _get_default_settings()


@router.get("/settings/prompt/debug")
def debug_prompt_settings():
    """Debug endpoint to check raw database values"""
    import logging
    from ..routers.grade import OPENROUTER_DEBUG
    
    try:
        # Get raw data from database
        res = supabase.table(TABLE).select("*").eq("key", KEY).limit(1).execute()
        rows = res.data or []
        
        if not rows:
            return {
                "status": "no_settings",
                "message": "No prompt settings found in database",
                "recommendation": "Save settings through the UI Settings page"
            }
        
        row = rows[0]
        value = row.get("value")
        
        # Check different aspects
        checks = {
            "row_exists": True,
            "value_type": str(type(value)),
            "value_is_dict": isinstance(value, dict),
            "has_system_template": False,
            "has_user_template": False,
            "has_schema_template": False,
            "system_template_length": 0,
            "user_template_length": 0,
            "schema_template_length": 0,
            "updated_at": str(row.get("updated_at", "unknown"))
        }
        
        if isinstance(value, dict):
            checks["has_system_template"] = "system_template" in value
            checks["has_user_template"] = "user_template" in value
            checks["has_schema_template"] = "schema_template" in value
            if value.get("system_template"):
                checks["system_template_length"] = len(str(value["system_template"]))
            if value.get("user_template"):
                checks["user_template_length"] = len(str(value["user_template"]))
            if value.get("schema_template"):
                checks["schema_template_length"] = len(str(value["schema_template"]))
        
        return {
            "status": "found",
            "checks": checks,
            "raw_value_preview": str(value)[:200] if value else None,
            "recommendation": "Settings exist" if checks["has_system_template"] and checks["has_user_template"] else "Re-save settings through UI"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "recommendation": "Check database connection and table structure"
        }


@router.put("/settings/prompt", response_model=PromptSettingsRes)
def put_prompt_settings(payload: PromptSettingsReq) -> PromptSettingsRes:
    import logging
    from ..routers.grade import OPENROUTER_DEBUG
    
    if not payload.system_template or not payload.user_template or not payload.schema_template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="system_template, user_template, and schema_template are all required")
    
    if OPENROUTER_DEBUG:
        logging.info("\n" + "="*80)
        logging.info("💾 SAVING PROMPT SETTINGS")
        logging.info("="*80)
        logging.info("📝 System template length: %s chars", len(payload.system_template))
        logging.info("📝 User template length: %s chars", len(payload.user_template))
        logging.info("📝 Schema template length: %s chars", len(payload.schema_template))
        logging.info("System preview: %s...", payload.system_template[:100])
        logging.info("User preview: %s...", payload.user_template[:100])
        logging.info("Schema preview: %s...", payload.schema_template[:100])
        logging.info("="*80 + "\n")
    
    try:
        # Prepare the data
        data = {
            "key": KEY,
            "value": {
                "system_template": payload.system_template,
                "user_template": payload.user_template,
                "schema_template": payload.schema_template,
            },
        }
        
        if OPENROUTER_DEBUG:
            logging.info("📤 Sending to database:")
            logging.info("  Key: %s", data["key"])
            logging.info("  Value type: %s", type(data["value"]))
            logging.info("  Value keys: %s", list(data["value"].keys()) if isinstance(data["value"], dict) else "Not a dict")
        
        result = supabase.table(TABLE).upsert(data, on_conflict="key").execute()
        
        if OPENROUTER_DEBUG:
            logging.info("✅ Settings saved successfully")
            logging.info("Database response: %s", result.data if hasattr(result, 'data') else 'No data')
    except Exception as e:
        if OPENROUTER_DEBUG:
            logging.error("❌ Failed to save settings: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")
    return PromptSettingsRes(
        system_template=payload.system_template,
        user_template=payload.user_template,
        schema_template=payload.schema_template
    )
