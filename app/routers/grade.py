import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple
from urllib.parse import urlsplit, urlunsplit, quote, unquote, parse_qsl, urlencode

import httpx
from fastapi import APIRouter, HTTPException, status

from ..schemas import GradeSingleReq, GradeSingleRes
from ..supabase_client import supabase


router = APIRouter()

MAX_CONCURRENCY = int(os.getenv("GRADING_MAX_CONCURRENCY", "4"))
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER")
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "Local Dev App")
OPENROUTER_DEBUG = os.getenv("OPENROUTER_DEBUG", "0").lower() in ("1", "true", "yes", "on")

# File logging for full requests/responses per session
GRADE_LOG_DIR = os.getenv("GRADE_LOG_DIR", "logs")

def _json_pp(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except Exception:
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"

def _append_session_log(session_id: str, text: str) -> None:
    try:
        os.makedirs(GRADE_LOG_DIR, exist_ok=True)
        path = os.path.join(GRADE_LOG_DIR, f"session_{session_id}.log")
        ts = datetime.now().isoformat(timespec="seconds")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {text}\n")
    except Exception:
        logging.exception("Failed to write session log")


def _bad_request(message: str, code: str = "VALIDATION_ERROR", details: dict | None = None):
    ex = HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
    ex.code = code
    if details:
        ex.details = details
    return ex


def _get_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")
    return key


async def _call_openrouter(
    client: httpx.AsyncClient,
    model: str,
    messages: List[Dict[str, Any]],
    reasoning: Dict[str, Any] | None,
    *,
    session_id: str | None = None,
    try_index: int | None = None,
    instance_id: str | None = None,
) -> Dict[str, Any]:
    url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "provider": {"allow_fallbacks": False},
    }
    # Only add reasoning to payload if it's not None and not empty
    if reasoning is not None and reasoning:
        payload["reasoning"] = reasoning

    # Persist the complete request payload per model/try to a session log
    if session_id:
        _append_session_log(
            session_id,
            f"REQUEST model={model} instance_id={instance_id or ''} try={try_index or ''} url={url}\n" + _json_pp(payload),
        )

    last_retry_after: str | None = None
    for attempt in range(3):
        try:
            if OPENROUTER_DEBUG:
                try:
                    preview = json.dumps(payload, indent=2)[:1500]
                except Exception:
                    preview = "<payload-not-serializable>"
                logging.info("\n" + "-"*60)
                logging.info("🚀 OPENROUTER API CALL - Attempt %s", attempt + 1)
                logging.info("-"*60)
                logging.info("🌐 URL: %s", url)
                logging.info("🤖 Model: %s", model)
                if reasoning is not None and reasoning:
                    logging.info("🧠 Reasoning for this call: %s", json.dumps(reasoning, indent=2))
                else:
                    logging.info("🧠 No reasoning for this call")
                logging.info("📦 Payload Preview:")
                logging.info(preview)
                logging.info("-"*60)

            resp = await client.post(url, json=payload, timeout=60.0)
            # Persist full raw response body
            if session_id:
                try:
                    body_text = resp.text
                except Exception:
                    body_text = "<no-text>"
                _append_session_log(
                    session_id,
                    f"RESPONSE model={model} instance_id={instance_id or ''} try={try_index or ''} status={resp.status_code}\n{body_text}",
                )
            if OPENROUTER_DEBUG:
                try:
                    body_prev = (resp.text or "")[:1500]
                    # Try to pretty-print JSON response
                    try:
                        json_resp = json.loads(resp.text)
                        body_prev = json.dumps(json_resp, indent=2)[:1500]
                    except:
                        pass
                except Exception:
                    body_prev = "<no-text>"
                logging.info("✅ OPENROUTER RESPONSE")
                logging.info("📊 Status Code: %s", resp.status_code)
                logging.info("📄 Response Preview:")
                logging.info(body_prev)
                logging.info("-"*60 + "\n")
            if resp.status_code == 429:
                # Honor Retry-After if present
                last_retry_after = resp.headers.get("retry-after") or "2"
                retry_after = int(last_retry_after or "2")
                await asyncio.sleep((retry_after or 2) * (2 ** attempt))
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if OPENROUTER_DEBUG:
                logging.error("\n" + "-"*60)
                logging.error("❌ OPENROUTER API ERROR - Attempt %s", attempt + 1)
                logging.error("-"*60)
                logging.error("📊 Status Code: %s", e.response.status_code if e.response else "Unknown")
                logging.error("📄 Error Details: %s", str(e))
                if e.response:
                    try:
                        error_body = e.response.text[:1000]
                        try:
                            error_json = json.loads(e.response.text)
                            error_body = json.dumps(error_json, indent=2)[:1000]
                        except:
                            pass
                        logging.error("📄 Response Body:")
                        logging.error(error_body)
                    except:
                        pass
                logging.error("-"*60 + "\n")
            
            if attempt == 2:
                if e.response is not None and e.response.status_code == 429:
                    # Propagate Retry-After if present
                    ra = e.response.headers.get("retry-after")
                    http_exc = HTTPException(status_code=429, detail=str(e), headers={"Retry-After": ra} if ra else None)
                    try:
                        http_exc.details = {"openrouter_body": (e.response.text or "")[:1000]}
                    except Exception:
                        pass
                    raise http_exc
                http_exc = HTTPException(status_code=e.response.status_code, detail=str(e))
                try:
                    http_exc.details = {"openrouter_body": (e.response.text or "")[:1000]}
                except Exception:
                        pass
                raise http_exc
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            if OPENROUTER_DEBUG:
                logging.error("\n" + "-"*60)
                logging.error("⚠️ UNEXPECTED ERROR - Attempt %s", attempt + 1)
                logging.error("-"*60)
                logging.error("🐛 Exception Type: %s", type(e).__name__)
                logging.error("📄 Error Message: %s", str(e))
                logging.exception("Full traceback:")
                logging.error("-"*60 + "\n")
            if attempt == 2:
                raise HTTPException(status_code=500, detail=f"OpenRouter request failed: {e}")
            await asyncio.sleep(2 ** attempt)

    # Should not reach here
    if last_retry_after is not None:
        # Retries exhausted while rate-limited; surface 429 to client with Retry-After
        raise HTTPException(status_code=429, detail="OpenRouter rate limited", headers={"Retry-After": last_retry_after})
    raise HTTPException(status_code=500, detail="OpenRouter request failed after retries")


def _encode_url(u: str) -> str:
    """Safely URL-encode the path and query components of a URL.
    Leaves scheme/host intact. Falls back to original on error.
    """
    try:
        sp = urlsplit(u)
        path = quote(unquote(sp.path), safe="/")
        if sp.query:
            q_pairs = parse_qsl(sp.query, keep_blank_values=True)
            query = urlencode(q_pairs, doseq=True)
        else:
            query = ""
        return urlunsplit((sp.scheme, sp.netloc, path, query, sp.fragment))
    except Exception:
        return u


def _build_messages(student_urls: List[str], key_urls: List[str], questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build OpenRouter chat messages using DB-configured templates when available.

    Placeholders supported:
    - In system template: [Answer key], [Question list]
    - In user template: [Student assessment]
    We also attach image_url parts so models can process images reliably.
    """

    # Normalize URLs to be safely fetchable by providers
    stu_urls = [
        _encode_url(u) for u in (student_urls or []) if isinstance(u, str) and u
    ]
    key_urls_norm = [
        _encode_url(u) for u in (key_urls or []) if isinstance(u, str) and u
    ]

    # Try to load templates from Supabase (table: app_settings, key: prompt_settings)
    sys_template: str | None = None
    user_template: str | None = None
    schema_template: str | None = None
    try:
        if OPENROUTER_DEBUG:
            logging.info("\n" + "-"*60)
            logging.info("🔍 Fetching prompt settings from database...")
            logging.info("-"*60)
        
        res = supabase.table("app_settings").select("value").eq("key", "prompt_settings").limit(1).execute()
        rows = res.data or []
        
        if OPENROUTER_DEBUG:
            logging.info("📄 Database response: %s rows found", len(rows))
            if rows:
                # Log the raw response to debug JSONB parsing
                logging.info("🔍 Raw row type: %s", type(rows[0]))
                logging.info("📦 Raw row: %s", rows[0])
        
        if rows and len(rows) > 0:
            row = rows[0]
            value = row.get("value")
            
            if OPENROUTER_DEBUG:
                logging.info("🔍 Value type: %s", type(value))
                logging.info("📦 Value content: %s", str(value)[:500] if value else "None")
            
            # Handle different possible formats of the value
            if isinstance(value, str):
                # If it's a string, try to parse it as JSON
                try:
                    value = json.loads(value)
                    if OPENROUTER_DEBUG:
                        logging.info("🔄 Parsed string value as JSON")
                except json.JSONDecodeError:
                    if OPENROUTER_DEBUG:
                        logging.error("❌ Failed to parse value string as JSON")
                    value = {}
            elif value is None:
                value = {}
            elif not isinstance(value, dict):
                if OPENROUTER_DEBUG:
                    logging.warning("⚠️ Unexpected value type: %s", type(value))
                value = {}
            
            # Extract templates
            sys_template = value.get("system_template") if isinstance(value, dict) else None
            user_template = value.get("user_template") if isinstance(value, dict) else None
            schema_template = value.get("schema_template") if isinstance(value, dict) else None
            
            # Convert to string if needed and validate
            if sys_template is not None:
                sys_template = str(sys_template).strip() if sys_template else None
                if not sys_template:  # Empty string becomes None
                    sys_template = None
                    
            if user_template is not None:
                user_template = str(user_template).strip() if user_template else None
                if not user_template:  # Empty string becomes None
                    user_template = None
            
            if schema_template is not None:
                schema_template = str(schema_template).strip() if schema_template else None
                if not schema_template:  # Empty string becomes None
                    schema_template = None
            
            if OPENROUTER_DEBUG:
                logging.info("📄 Extracted templates:")
                logging.info("  - System template: %s chars (is None: %s)", 
                           len(sys_template) if sys_template else 0, sys_template is None)
                logging.info("  - User template: %s chars (is None: %s)", 
                           len(user_template) if user_template else 0, user_template is None)
                logging.info("  - Schema template: %s chars (is None: %s)", 
                           len(schema_template) if schema_template else 0, schema_template is None)
                if sys_template:
                    logging.info("  - System preview: %s...", sys_template[:100])
                if user_template:
                    logging.info("  - User preview: %s...", user_template[:100])
                if schema_template:
                    logging.info("  - Schema preview: %s...", schema_template[:100])
        else:
            if OPENROUTER_DEBUG:
                logging.warning("⚠️ No prompt settings found in database")
    except Exception as e:
        # Log the error before falling back
        if OPENROUTER_DEBUG:
            logging.error("❌ Failed to load prompt settings from database: %s", str(e))
            logging.exception("Full traceback:")
        # Fallback to hardcoded
        sys_template = None
        user_template = None
        schema_template = None

    if sys_template and user_template:
        if OPENROUTER_DEBUG:
            logging.info("-"*60)
            logging.info("✅ Using custom templates from settings")
            logging.info("-"*60 + "\n")
        
        # Render placeholders
        questions_list = "\n".join([f"{q['question_id']} (max {q['max_marks']})" for q in questions])
        sys_text = (
            sys_template
            .replace("[Answer key]", "\n".join(key_urls_norm) if key_urls_norm else "")
            .replace("[Question list]", questions_list)
        )
        # Use custom schema template if provided, otherwise use default
        if schema_template:
            # Allow placeholders in schema template too
            schema_text = "\n\n" + schema_template.replace("[Question list]", questions_list)
        else:
            # Fallback to default schema if not provided
            schema_text = (
                "\n\nReturn ONLY JSON with this exact schema (no markdown fences, no prose):\n"
                '{"result":[{"first_name":string,"last_name":string,'
                '"answers":[{"question_id":string,"marks_awarded":number,"rubric_notes":string}]}]}\n'
                "Use the question_id values exactly as provided in the Questions list."
            )
        sys_text = f"{sys_text}{schema_text}"
        user_text = user_template.replace("[Student assessment]", "\n".join(stu_urls))

        # Compose user content with template text + image parts for reliability
        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": user_text},
        ]
        for u in stu_urls:
            user_content.append({"type": "image_url", "image_url": {"url": u}})
        if key_urls_norm:
            user_content.append({"type": "text", "text": "Answer key images:"})
            for u in key_urls_norm:
                user_content.append({"type": "image_url", "image_url": {"url": u}})

        return [
            {"role": "system", "content": sys_text},
            {"role": "user", "content": user_content},
        ]
    else:
        if OPENROUTER_DEBUG:
            logging.info("-"*60)
            logging.warning("⚠️ Using default fallback templates")
            logging.info("  - sys_template is None: %s", sys_template is None)
            logging.info("  - user_template is None: %s", user_template is None) 
            logging.info("-"*60 + "\n")

    # Default legacy behavior if settings not configured
    sys_text = (
        "You are a strict grader. Read the student's answer images and the answer key images. "
        "Return ONLY JSON with this exact schema (no markdown, no prose):\n"
        '{"result":[{"first_name":string,"last_name":string,'
        '"answers":[{"question_id":string,"marks_awarded":number,"rubric_notes":string}]}]}\n'
        "Use the question_id values exactly as provided in the Questions list."
    )
    user_content: List[Dict[str, Any]] = [
        {"type": "text", "text": "Grade the student's answers against the answer key."},
    ]
    for u in stu_urls:
        user_content.append({"type": "image_url", "image_url": {"url": u}})
    if key_urls_norm:
        user_content.append({"type": "text", "text": "Answer key images:"})
        for u in key_urls_norm:
            user_content.append({"type": "image_url", "image_url": {"url": u}})
    q_lines = [f"{q['question_id']} (max {q['max_marks']})" for q in questions]
    user_content.append({"type": "text", "text": "Questions: " + ", ".join(q_lines)})

    return [
        {"role": "system", "content": sys_text},
        {"role": "user", "content": user_content},
    ]


def _parse_model_output(raw: Dict[str, Any]) -> Tuple[List[Dict[str, Any]] | None, Dict[str, Any] | None]:
    """Attempt to parse the first choice content as JSON with expected schema.
    Returns (answers, validation_errors)."""
    try:
        choices = raw.get("choices") or []
        if not choices:
            return None, {"reason": "no_choices"}
        msg = choices[0].get("message", {})
        content = msg.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Concatenate text parts if content array
            parts = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    parts.append(c.get("text", ""))
            text = "\n".join(parts)
        else:
            return None, {"reason": "unsupported_content_type"}

        # Try to locate JSON block
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None, {"reason": "no_json_in_content", "preview": text[:200]}
        obj = json.loads(text[start : end + 1])
        
        # Extract student info if present (for future use/logging)
        student_info = {
            "first_name": obj.get("first_name"),
            "last_name": obj.get("last_name"),
            "student_id": obj.get("Student_ID")
        }
        
        if OPENROUTER_DEBUG and (student_info.get("first_name") or student_info.get("last_name")):
            logging.info("📚 Parsed student info: %s", student_info)
        
        # Handle multiple possible response formats
        answers = obj.get("answers")
        
        # Tolerant handling: if answers is a JSON string or a dict, coerce to expected list
        if isinstance(answers, str):
            try:
                parsed = json.loads(answers)
                answers = parsed
            except Exception:
                # Leave as-is to trigger validation error later
                pass
        
        if isinstance(answers, dict):
            coerced: List[Dict[str, Any]] = []
            for qid, grade_info in answers.items():
                if isinstance(grade_info, dict):
                    # Support multiple possible field names
                    marks = grade_info.get("mark")
                    if marks is None:
                        marks = grade_info.get("marks_awarded")
                    if marks is None:
                        marks = grade_info.get("score")
                    notes = grade_info.get("feedback")
                    if notes is None:
                        notes = grade_info.get("rubric_notes")
                    if notes is None:
                        notes = grade_info.get("notes")
                    coerced.append({
                        "question_id": qid,
                        "marks_awarded": marks,
                        "rubric_notes": notes,
                    })
                elif isinstance(grade_info, (int, float)):
                    coerced.append({
                        "question_id": qid,
                        "marks_awarded": grade_info,
                        "rubric_notes": None,
                    })
                elif isinstance(grade_info, str):
                    # Treat as textual notes with unknown marks
                    coerced.append({
                        "question_id": qid,
                        "marks_awarded": None,
                        "rubric_notes": grade_info,
                    })
            answers = coerced

        # Support schema: { "result": [ { first_name, last_name, answers: [ { question_number, mark, feedback } ] } ] }
        if answers is None and isinstance(obj.get("result"), list):
            combined: List[Dict[str, Any]] = []
            for student in obj.get("result") or []:
                if not isinstance(student, dict):
                    continue
                try:
                    if OPENROUTER_DEBUG and (student.get("first_name") or student.get("last_name")):
                        logging.info("📚 Parsed student info: %s", {
                            "first_name": student.get("first_name"),
                            "last_name": student.get("last_name"),
                        })
                except Exception:
                    pass
                ans = student.get("answers")
                if isinstance(ans, list):
                    for e in ans:
                        if isinstance(e, dict):
                            qid = (
                                e.get("question_id")
                                or e.get("qid")
                                or e.get("questionID")
                                or e.get("question")
                                or e.get("question_number")
                            )
                            marks = e.get("marks_awarded")
                            if marks is None:
                                marks = e.get("mark")
                            if marks is None:
                                marks = e.get("score")
                            notes = e.get("rubric_notes")
                            if notes is None:
                                notes = e.get("feedback")
                            if notes is None:
                                notes = e.get("notes")
                            combined.append({
                                "question_id": qid,
                                "marks_awarded": marks,
                                "rubric_notes": notes,
                            })
            if combined:
                answers = combined
        
        # Check for new formats with "results" or "grades"
        if answers is None:
            grades_key = None
            if "results" in obj:
                grades_key = "results"
            elif "grades" in obj:
                grades_key = "grades"
            
            if grades_key:
                # Convert nested object format to expected list format
                grades = obj.get(grades_key, {})
                answers = []
                for qid, grade_info in grades.items():
                    if isinstance(grade_info, dict):
                        # Handle both "mark" and "marks_awarded" field names
                        marks = grade_info.get("mark")
                        if marks is None:
                            marks = grade_info.get("marks_awarded")
                        
                        # Handle both "feedback" and "rubric_notes" field names
                        notes = grade_info.get("feedback")
                        if notes is None:
                            notes = grade_info.get("rubric_notes")
                        
                        answers.append({
                            "question_id": qid,
                            "marks_awarded": marks,
                            "rubric_notes": notes
                        })
        
        if not isinstance(answers, list):
            return None, {"reason": "answers_not_list"}
        norm: List[Dict[str, Any]] = []
        for a in answers:
            if not isinstance(a, dict):
                continue
            # Accept alternate key names for robustness
            qid = (
                a.get("question_id")
                or a.get("qid")
                or a.get("questionID")
                or a.get("question")
                or a.get("question_number")
            )
            marks = a.get("marks_awarded")
            if marks is None:
                marks = a.get("mark")
            if marks is None:
                marks = a.get("score")
            notes = a.get("rubric_notes")
            if notes is None:
                notes = a.get("feedback")
            if notes is None:
                notes = a.get("notes")
            if isinstance(qid, str) and (isinstance(marks, (int, float)) or marks is None):
                norm.append({"question_id": qid, "marks_awarded": marks, "rubric_notes": notes})
        if not norm:
            return None, {"reason": "no_valid_answers"}
        return norm, None
    except Exception as e:
        return None, {"reason": "parse_exception", "error": str(e)}


@router.post("/grade/single", response_model=GradeSingleRes)
async def grade_single(payload: GradeSingleReq) -> GradeSingleRes:
    # Validate session exists
    s = supabase.table("session").select("id").eq("id", payload.session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")

    # Load images (URL-only) and questions for this session
    imgs = (
        supabase.table("image")
        .select("role,url,order_index")
        .eq("session_id", payload.session_id)
        .order("order_index")
        .execute()
    )
    student_urls = [r["url"] for r in (imgs.data or []) if r.get("role") == "student"]
    key_urls = [r["url"] for r in (imgs.data or []) if r.get("role") == "answer_key"]
    if not student_urls:
        raise _bad_request("no student images registered for session")

    qs = (
        supabase.table("question")
        .select("question_id,number,max_marks")
        .eq("session_id", payload.session_id)
        .order("number")
        .execute()
    )
    questions: List[Dict[str, Any]] = qs.data or []
    if not questions:
        raise _bad_request("no questions configured for session")

    # Expand model tries
    items: List[Tuple[str, int, Dict[str, Any] | None, str | None]] = []
    for m in payload.models:
        model_name = m.name
        tries = m.tries if m.tries and m.tries > 0 else (payload.default_tries or 1)
        tries = max(1, tries)
        # Use per-model reasoning if available, otherwise fall back to global
        model_reasoning = m.reasoning if hasattr(m, 'reasoning') and m.reasoning else payload.reasoning
        instance_id = m.instance_id if hasattr(m, 'instance_id') and m.instance_id else None
        for i in range(1, tries + 1):
            items.append((model_name, i, model_reasoning, instance_id))

    # Persist session configuration for UI (selected models and default tries)
    try:
        model_names = [m.name for m in payload.models]
        supabase.table("session").update({
            "selected_models": model_names,
            "default_tries": payload.default_tries or 1,
        }).eq("id", payload.session_id).execute()
    except Exception:
        # Non-fatal if this fails; continue with grading
        pass

    # Set session status to 'grading'
    try:
        supabase.table("session").update({"status": "grading"}).eq("id", payload.session_id).execute()
    except Exception:
        pass

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    messages = _build_messages(student_urls, key_urls, questions)
    # Debug: Log the exact system and user messages before any LLM request is made
    if OPENROUTER_DEBUG:
        try:
            def _preview(obj: Any, limit: int = 2000) -> str:
                try:
                    if isinstance(obj, (dict, list)):
                        s = json.dumps(obj, ensure_ascii=False, indent=2)
                    else:
                        s = str(obj)
                    return s[:limit]
                except Exception:
                    return "<unserializable>"

            sys_msg = next((m.get("content") for m in messages if m.get("role") == "system"), None)
            user_msg = next((m.get("content") for m in messages if m.get("role") == "user"), None)
            
            logging.info("\n" + "="*80)
            logging.info("🔍 LLM REQUEST DETAILS")
            logging.info("="*80)
            logging.info("📝 Session ID: %s", payload.session_id)
            logging.info("🤖 Models: %s", [(m.name, getattr(m, 'instance_id', None)) for m in payload.models])
            logging.info("🔁 Default Tries: %s", payload.default_tries)
            
            # Log per-model reasoning if available
            has_reasoning = False
            for i, m in enumerate(payload.models):
                if hasattr(m, 'reasoning') and m.reasoning:
                    if not has_reasoning:
                        logging.info("🧠 Per-Model Reasoning Configs:")
                        has_reasoning = True
                    logging.info("  Model %s (%s):", i + 1, m.name)
                    if hasattr(m, 'instance_id') and m.instance_id:
                        logging.info("    Instance ID: %s", m.instance_id)
                    logging.info("    Reasoning: %s", json.dumps(m.reasoning, indent=2))
            
            # Log global reasoning if no per-model configs
            if not has_reasoning and payload.reasoning:
                logging.info("🧠 Global Reasoning Config: %s", json.dumps(payload.reasoning, indent=2))
            logging.info("-"*80)
            logging.info("💬 SYSTEM MESSAGE:")
            logging.info(_preview(sys_msg))
            logging.info("-"*80)
            logging.info("👤 USER MESSAGE:")
            logging.info(_preview(user_msg))
            logging.info("="*80 + "\n")
        except Exception:
            logging.exception("Failed to log LLM messages preview")
    # Optional preflight checks to verify that image URLs are accessible (debug only)
    if OPENROUTER_DEBUG:
        try:
            urls: List[str] = []
            user_msg = next((m.get("content") for m in messages if m.get("role") == "user"), [])
            if isinstance(user_msg, list):
                for part in user_msg:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        u = (part.get("image_url") or {}).get("url")
                        if u:
                            urls.append(u)
            if urls:
                logging.info("\n" + "-"*60)
                logging.info("🖼️ IMAGE URL PREFLIGHT CHECKS")
                logging.info("-"*60)
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as pcli:
                    for idx, u in enumerate(urls, 1):
                        try:
                            r = await pcli.head(u)
                            if r.status_code >= 400:
                                # Fallback to a tiny GET to work around HEAD not supported
                                r = await pcli.get(u, headers={"Range": "bytes=0-0"})
                            status_icon = "✅" if r.status_code < 400 else "⚠️"
                            logging.info("%s Image %s: Status %s - %s", status_icon, idx, r.status_code, u[:100] + ("..." if len(u) > 100 else ""))
                        except Exception as e:
                            logging.warning("❌ Image %s: Failed - %s (URL: %s)", idx, str(e)[:100], u[:100] + ("..." if len(u) > 100 else ""))
                logging.info("-"*60 + "\n")
        except Exception:
            logging.exception("Failed preflight image checks")
    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if OPENROUTER_HTTP_REFERER:
        headers["HTTP-Referer"] = OPENROUTER_HTTP_REFERER
    if OPENROUTER_APP_TITLE:
        headers["X-Title"] = OPENROUTER_APP_TITLE

    async with httpx.AsyncClient(headers=headers) as client:
        async def run_task(model: str, try_index: int, reasoning: Dict[str, Any] | None, instance_id: str | None):
            async with semaphore:
                data = await _call_openrouter(
                    client,
                    model,
                    messages,
                    reasoning,
                    session_id=payload.session_id,
                    try_index=try_index,
                    instance_id=instance_id,
                )
                return model, try_index, data, instance_id

        tasks = [asyncio.create_task(run_task(model, t, reasoning, inst_id)) for model, t, reasoning, inst_id in items]
        results: List[Tuple[str, int, Dict[str, Any], str | None]] = []
        # Collect results and exceptions per task so one failure doesn't cancel all
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        errors: List[Exception] = []
        for r in gathered:
            if isinstance(r, Exception):
                errors.append(r)
            else:
                results.append(r)
        if not results:
            # All tasks failed; mark session failed and bubble up most relevant error
            supabase.table("session").update({"status": "failed"}).eq("id", payload.session_id).execute()
            # Prefer propagating HTTPException (may include 4xx like 404/429)
            for err in errors:
                if isinstance(err, HTTPException):
                    raise err
            # Fallback to 500 with first error message
            raise HTTPException(status_code=500, detail=f"grading failed: {errors[0] if errors else 'unknown error'}")

    # Persist results per question
    any_valid_answers: bool = False
    upserts: List[Dict[str, Any]] = []
    for model, try_index, raw, instance_id in results:
        # Use instance_id if available, otherwise use model name
        # This allows differentiating same model with different reasoning
        model_identifier = instance_id if instance_id else model
        
        answers, verr = _parse_model_output(raw)
        if answers:
            any_valid_answers = True
            # Log parsed answers for this attempt
            try:
                _append_session_log(
                    payload.session_id,
                    f"PARSED model={model} instance_id={instance_id or ''} model_id={model_identifier} try={try_index}\n" + _json_pp({"answers": answers}),
                )
            except Exception:
                logging.exception("Failed to log parsed answers")
            for a in answers:
                upserts.append(
                    {
                        "session_id": payload.session_id,
                        "question_id": a.get("question_id"),
                        "model_name": model_identifier,  # Use identifier instead of plain model name
                        "try_index": try_index,
                        "marks_awarded": a.get("marks_awarded"),
                        "rubric_notes": a.get("rubric_notes"),
                        "raw_output": raw,
                        "validation_errors": None,
                    }
                )
        else:
            # Record validation error as a single row with marker question_id
            try:
                _append_session_log(
                    payload.session_id,
                    f"PARSE_ERROR model={model} instance_id={instance_id or ''} model_id={model_identifier} try={try_index}\n" + _json_pp(verr),
                )
            except Exception:
                logging.exception("Failed to log parse error")
            upserts.append(
                {
                    "session_id": payload.session_id,
                    "question_id": "__parse_error__",
                    "model_name": model_identifier,  # Use identifier instead of plain model name
                    "try_index": try_index,
                    "marks_awarded": None,
                    "rubric_notes": None,
                    "raw_output": raw,
                    "validation_errors": verr,
                }
            )

    if upserts:
        # Deduplicate rows by composite key to avoid Postgres 21000 error when
        # multiple proposed rows in the same statement would target the same
        # ON CONFLICT (session_id, question_id, model_name, try_index).
        # If duplicates exist, keep the last occurrence.
        unique_map = {}
        for r in upserts:
            try:
                key = (r["session_id"], r["question_id"], r["model_name"], r["try_index"])
            except Exception:
                # If any key missing, fall back to appending as-is
                key = None
            if key is not None:
                unique_map[key] = r
        if unique_map:
            upserts = list(unique_map.values())
        try:
            supabase.table("result").upsert(
                upserts,
                on_conflict="session_id,question_id,model_name,try_index",
            ).execute()
        except Exception as e:
            # Do not fail the entire request; mark session failed
            supabase.table("session").update({"status": "failed"}).eq("id", payload.session_id).execute()
            raise HTTPException(status_code=500, detail=f"failed to persist results: {e}")

    # Mark session status based on whether any valid answers were parsed
    try:
        supabase.table("session").update({"status": "graded" if any_valid_answers else "failed"}).eq("id", payload.session_id).execute()
    except Exception:
        pass

    return GradeSingleRes(ok=True, session_id=payload.session_id)
