from fastapi import APIRouter, HTTPException, status
from ..supabase_client import supabase
from ..schemas import PromptSettingsReq, PromptSettingsRes, RubricPromptSettingsReq, RubricPromptSettingsRes
import httpx
import os
from datetime import datetime


router = APIRouter()

@router.get("/settings/test")
def test_settings_router():
    """Simple test endpoint to verify settings router is working"""
    return {
        "message": "Settings router is working!",
        "router": "settings",
        "endpoints": ["/settings/prompt", "/models", "/settings/debug/models"]
    }


DEFAULT_SYSTEM_TEMPLATE = (
    """
<Role>
You are a teacher whose job is to grade student assessments.
</Role>

<Task>
You will be given:
- `answer_key` (images)
- `questions_list` (JSON)
- `grading_rubric` (JSON with detailed criteria)
- `student_assessments` (images)

For each student in `student_assessments`, you must:
1. Extract the student's `first_name`, `last_name` and `Student_ID`.
2. For each question in `questions_list`, assign a `marks_awarded` and provide `rubric_notes`.
3. Use the `grading_rubric` JSON to guide your marking - it contains specific criteria, mark allocations, and deductions for each question.
4. Format the final output for each student as a single JSON object.
</Task>

<Instructions>
Follow the grading rubric precisely. The rubric specifies:
- Grading criteria for each question (what earns marks)
- Mark allocations (how many marks for each criterion)
- Deductions (what loses marks)
- Additional notes or instructions

Use this rubric to ensure consistent, fair grading.
</Instructions>

<Answer_Key>
Here are the answer key pages. Use these to determine correct answers:
[Answer key]
</Answer_Key>

<Grading_Rubric>
Here is the detailed grading rubric extracted from the rubric images (JSON format):
[Grading Rubric]
</Grading_Rubric>

<Question_List>
Here are the specific questions to grade:
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

# --- Rubric Prompt Templates ---

DEFAULT_RUBRIC_SYSTEM_TEMPLATE = (
    """
<Role>
You are a grading rubric analyzer whose job is to extract and structure grading criteria from rubric images.
</Role>

<Task>
You will be given:
1. Grading rubric images (in the user message)
2. A list of questions with their maximum marks

Your task is to:
1. Carefully analyze ALL rubric images
2. Extract the grading criteria for EACH question
3. Identify mark allocations, requirements, and deductions
4. Return the information as structured JSON
</Task>

<Question_List>
Here are the questions that need grading criteria:
[Question list]
</Question_List>

<Output_Format>
Return ONLY valid JSON (no markdown fences, no explanatory text) with this exact structure:

{
  "rubric": [
    {
      "question_id": "Q1",
      "max_marks": 10,
      "grading_criteria": [
        {
          "criterion": "Brief description of what earns marks",
          "marks": 5,
          "requirements": "Specific requirements to earn these marks"
        }
      ],
      "deductions": [
        {
          "reason": "What causes mark deduction",
          "marks": -1
        }
      ],
      "notes": "Any additional grading notes or instructions"
    }
  ]
}

CRITICAL RULES:
1. Return ONLY valid JSON - no markdown code fences (```json), no prose before or after
2. Use the exact question_id values from the Question_List above
3. Include ALL questions from the Question_List, even if not explicitly mentioned in rubric
4. If rubric doesn't specify criteria for a question, include it with empty grading_criteria and deductions arrays
5. Ensure all mark values are numbers (not strings)
6. Deduction marks should be negative numbers
7. The grading_criteria array should contain all ways to earn marks
8. The deductions array should contain all ways to lose marks
</Output_Format>
"""
    .strip()
)

DEFAULT_RUBRIC_USER_TEMPLATE = (
    """
<Grading_Rubric_Images>
[Grading rubric images]
</Grading_Rubric_Images>

Please analyze the grading rubric images above and extract all grading criteria for each question in the Question_List.

Return your analysis as valid JSON following the exact structure specified in the system message.

Do NOT include markdown code fences. Return ONLY the JSON object.
"""
    .strip()
)


TABLE = "app_settings"
KEY = "prompt_settings"
RUBRIC_KEY = "rubric_prompt_settings"


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


# --- Rubric Prompt Settings Endpoints ---

def _get_default_rubric_settings() -> RubricPromptSettingsRes:
    return RubricPromptSettingsRes(
        system_template=DEFAULT_RUBRIC_SYSTEM_TEMPLATE,
        user_template=DEFAULT_RUBRIC_USER_TEMPLATE
    )


@router.get("/settings/rubric-prompt", response_model=RubricPromptSettingsRes)
def get_rubric_prompt_settings() -> RubricPromptSettingsRes:
    """Get rubric prompt templates from database or return defaults"""
    import logging
    from ..routers.grade import OPENROUTER_DEBUG
    
    try:
        if OPENROUTER_DEBUG:
            logging.info("\n" + "="*80)
            logging.info("🔍 FETCHING RUBRIC PROMPT SETTINGS")
            logging.info("="*80)
        
        res = supabase.table(TABLE).select("key,value").eq("key", RUBRIC_KEY).limit(1).execute()
        rows = res.data or []
        
        if OPENROUTER_DEBUG:
            logging.info("📄 Found %s rows", len(rows))
            if rows:
                logging.info("📦 Raw data: %s", rows[0])
        
        if not rows:
            if OPENROUTER_DEBUG:
                logging.warning("⚠️ No rubric settings found, returning defaults")
            return _get_default_rubric_settings()
        
        value = rows[0].get("value") or {}
        sys_t = value.get("system_template") or DEFAULT_RUBRIC_SYSTEM_TEMPLATE
        usr_t = value.get("user_template") or DEFAULT_RUBRIC_USER_TEMPLATE
        
        if OPENROUTER_DEBUG:
            logging.info("✅ Retrieved rubric templates:")
            logging.info("  - System: %s chars", len(sys_t))
            logging.info("  - User: %s chars", len(usr_t))
            logging.info("="*80 + "\n")
        
        return RubricPromptSettingsRes(system_template=sys_t, user_template=usr_t)
    except Exception as e:
        if OPENROUTER_DEBUG:
            logging.error("❌ Error fetching rubric settings: %s", str(e))
        # If table doesn't exist yet or other error, return defaults
        return _get_default_rubric_settings()


@router.put("/settings/rubric-prompt", response_model=RubricPromptSettingsRes)
def put_rubric_prompt_settings(payload: RubricPromptSettingsReq) -> RubricPromptSettingsRes:
    """Update rubric prompt templates in database"""
    import logging
    from ..routers.grade import OPENROUTER_DEBUG
    
    if not payload.system_template or not payload.user_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="system_template and user_template are both required"
        )
    
    if OPENROUTER_DEBUG:
        logging.info("\n" + "="*80)
        logging.info("💾 SAVING RUBRIC PROMPT SETTINGS")
        logging.info("="*80)
        logging.info("📝 System template length: %s chars", len(payload.system_template))
        logging.info("📝 User template length: %s chars", len(payload.user_template))
        logging.info("System preview: %s...", payload.system_template[:100])
        logging.info("User preview: %s...", payload.user_template[:100])
        logging.info("="*80 + "\n")
    
    try:
        # Prepare the data
        data = {
            "key": RUBRIC_KEY,
            "value": {
                "system_template": payload.system_template,
                "user_template": payload.user_template,
            },
        }
        
        if OPENROUTER_DEBUG:
            logging.info("📤 Sending to database:")
            logging.info("  Key: %s", data["key"])
            logging.info("  Value type: %s", type(data["value"]))
            logging.info("  Value keys: %s", list(data["value"].keys()) if isinstance(data["value"], dict) else "Not a dict")
        
        result = supabase.table(TABLE).upsert(data, on_conflict="key").execute()
        
        if OPENROUTER_DEBUG:
            logging.info("✅ Rubric settings saved successfully")
            logging.info("Database response: %s", result.data if hasattr(result, 'data') else 'No data')
    except Exception as e:
        if OPENROUTER_DEBUG:
            logging.error("❌ Failed to save rubric settings: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save rubric settings: {e}")
    
    return RubricPromptSettingsRes(
        system_template=payload.system_template,
        user_template=payload.user_template
    )


@router.get("/settings/rubric-prompt/debug")
def debug_rubric_prompt_settings():
    """Debug endpoint to check raw rubric prompt database values"""
    try:
        # Get raw data from database
        res = supabase.table(TABLE).select("*").eq("key", RUBRIC_KEY).limit(1).execute()
        rows = res.data or []
        
        if not rows:
            return {
                "status": "no_settings",
                "message": "No rubric prompt settings found in database",
                "recommendation": "Save rubric settings through the UI Settings page"
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
            "system_template_length": 0,
            "user_template_length": 0,
            "updated_at": str(row.get("updated_at", "unknown"))
        }
        
        if isinstance(value, dict):
            checks["has_system_template"] = "system_template" in value
            checks["has_user_template"] = "user_template" in value
            if value.get("system_template"):
                checks["system_template_length"] = len(str(value["system_template"]))
            if value.get("user_template"):
                checks["user_template_length"] = len(str(value["user_template"]))
        
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


@router.get("/models")
async def get_models():
    """Proxy endpoint for OpenRouter models API"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 Models endpoint called")
    
    # Check if httpx is available
    try:
        import httpx
        logger.info("✓ httpx is available")
    except ImportError as e:
        logger.error("❌ httpx not available")
        raise HTTPException(status_code=500, detail="httpx dependency not available")
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        logger.error("❌ No OpenRouter API key found")
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")
    
    logger.info("✓ OpenRouter API key is configured")
    
    try:
        logger.info("📡 Making request to OpenRouter API...")
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:5173"),
                "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Mark Grading Assistant"),
            }
            
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=30.0
            )
            
            logger.info(f"📡 OpenRouter API response: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            model_count = len(data.get('data', [])) if isinstance(data.get('data'), list) else 0
            logger.info(f"✅ Successfully fetched {model_count} models")
            

            
            return data
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ OpenRouter API HTTP error: {e.response.status_code if e.response else 'Unknown'}")
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"OpenRouter API error: {e}"
        )
    except httpx.TimeoutException as e:
        logger.error("❌ OpenRouter API timeout")
        raise HTTPException(status_code=504, detail="OpenRouter API timeout")
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {e}")

@router.get("/debug/models")
async def debug_models():
    """Debug endpoint to check models endpoint configuration"""
    import logging
    logger = logging.getLogger(__name__)
    
    checks = {
        "httpx_available": False,
        "openrouter_key_configured": False,
        "openrouter_key_length": 0,
        "http_referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:5173"),
        "app_title": os.getenv("OPENROUTER_APP_TITLE", "Mark Grading Assistant"),
    }
    
    # Check httpx availability
    try:
        import httpx
        checks["httpx_available"] = True
    except ImportError:
        pass
    
    # Check OpenRouter key
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        checks["openrouter_key_configured"] = True
        checks["openrouter_key_length"] = len(openrouter_key)
    
    return {
        "status": "debug_info",
        "checks": checks,
        "recommendation": "All checks should pass for /models endpoint to work"
    }


# --- Template Management Endpoints ---

@router.get("/settings/templates/{template_type}")
def list_templates(template_type: str):
    """
    List all templates of a given type (rubric or assessment)
    Returns: {templates: [{name: str, ...}]}
    """
    if template_type not in ["rubric", "assessment"]:
        raise HTTPException(status_code=400, detail="template_type must be 'rubric' or 'assessment'")
    
    try:
        templates = []
        
        # First, add the "default" template from existing settings
        if template_type == "rubric":
            # Get from rubric_prompt_settings
            res = supabase.table(TABLE).select("key,value").eq("key", RUBRIC_KEY).limit(1).execute()
            if res.data:
                value = res.data[0].get("value", {})
                templates.append({
                    "name": "default",
                    "display_name": "Default Template",
                    "system_template": value.get("system_template", DEFAULT_RUBRIC_SYSTEM_TEMPLATE),
                    "user_template": value.get("user_template", DEFAULT_RUBRIC_USER_TEMPLATE),
                    "schema_template": None
                })
        else:  # assessment
            # Get from prompt_settings
            res = supabase.table(TABLE).select("key,value").eq("key", KEY).limit(1).execute()
            if res.data:
                value = res.data[0].get("value", {})
                templates.append({
                    "name": "default",
                    "display_name": "Default Template",
                    "system_template": value.get("system_template", DEFAULT_SYSTEM_TEMPLATE),
                    "user_template": value.get("user_template", DEFAULT_USER_TEMPLATE),
                    "schema_template": value.get("schema_template", DEFAULT_SCHEMA_TEMPLATE)
                })
        
        # Then, get all custom templates that match the pattern
        prefix = f"{template_type}_template_"
        res = supabase.table(TABLE).select("key,value").like("key", f"{prefix}%").execute()
        rows = res.data or []
        
        for row in rows:
            key = row.get("key", "")
            # Extract template name from key (e.g., "rubric_template_detailed" -> "detailed")
            template_name = key.replace(prefix, "")
            value = row.get("value", {})
            
            templates.append({
                "name": template_name,
                "display_name": value.get("display_name", template_name),
                "system_template": value.get("system_template", ""),
                "user_template": value.get("user_template", ""),
                "schema_template": value.get("schema_template", "") if template_type == "assessment" else None
            })
        
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {e}")


@router.put("/settings/templates/{template_type}/{template_name}")
def save_template(template_type: str, template_name: str, payload: dict):
    """
    Save or update a template
    Payload: {display_name: str, system_template: str, user_template: str, schema_template?: str}
    """
    if template_type not in ["rubric", "assessment"]:
        raise HTTPException(status_code=400, detail="template_type must be 'rubric' or 'assessment'")
    
    # Validate required fields
    if not payload.get("system_template") or not payload.get("user_template"):
        raise HTTPException(status_code=400, detail="system_template and user_template are required")
    
    if template_type == "assessment" and not payload.get("schema_template"):
        raise HTTPException(status_code=400, detail="schema_template is required for assessment templates")
    
    try:
        # Special handling for "default" template - update the original settings keys
        if template_name == "default":
            if template_type == "rubric":
                # Update rubric_prompt_settings
                data = {
                    "key": RUBRIC_KEY,
                    "value": {
                        "system_template": payload["system_template"],
                        "user_template": payload["user_template"],
                    }
                }
            else:  # assessment
                # Update prompt_settings
                data = {
                    "key": KEY,
                    "value": {
                        "system_template": payload["system_template"],
                        "user_template": payload["user_template"],
                        "schema_template": payload["schema_template"]
                    }
                }
        else:
            # Regular custom template
            key = f"{template_type}_template_{template_name}"
            data = {
                "key": key,
                "value": {
                    "display_name": payload.get("display_name", template_name),
                    "system_template": payload["system_template"],
                    "user_template": payload["user_template"],
                }
            }
            
            # Add schema_template for assessment templates
            if template_type == "assessment":
                data["value"]["schema_template"] = payload["schema_template"]
        
        supabase.table(TABLE).upsert(data, on_conflict="key").execute()
        
        return {"success": True, "message": f"Template '{template_name}' saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save template: {e}")


@router.delete("/settings/templates/{template_type}/{template_name}")
def delete_template(template_type: str, template_name: str):
    """Delete a template"""
    if template_type not in ["rubric", "assessment"]:
        raise HTTPException(status_code=400, detail="template_type must be 'rubric' or 'assessment'")
    
    # Prevent deletion of default template
    if template_name == "default":
        raise HTTPException(status_code=400, detail="Cannot delete the default template")
    
    try:
        key = f"{template_type}_template_{template_name}"
        supabase.table(TABLE).delete().eq("key", key).execute()
        
        return {"success": True, "message": f"Template '{template_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {e}")
