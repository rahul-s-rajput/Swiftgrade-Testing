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
    
    # Force specific provider for Claude models to avoid routing issues
    if "claude" in model.lower():
        # Specify Anthropic as the required provider for Claude models
        payload["provider"]["require_parameters"] = True
        payload["provider"]["order"] = ["Anthropic"]  # Only use Anthropic
        # Alternative: You can also use specific provider routing
        # payload["route"] = "anthropic"  # If OpenRouter supports this
        
        if OPENROUTER_DEBUG:
            logging.info("🎯 Forcing Anthropic provider for Claude model: %s", model)
    
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
            # Always log request directly to console
            logging.info("\n" + "-"*80)
            logging.info("🚀 OPENROUTER API CALL - Attempt %s", attempt + 1)
            logging.info("-"*80)
            logging.info("🌐 URL: %s", url)
            logging.info("🤖 Model: %s", model)
            if reasoning is not None and reasoning:
                logging.info("🧠 Reasoning for this call: %s", json.dumps(reasoning, indent=2))
            else:
                logging.info("🧠 No reasoning for this call")
            logging.info("📦 FULL REQUEST PAYLOAD:")
            logging.info(_json_pp(payload))
            logging.info("-"*80)
            
            # Keep original debug logging if enabled
            if OPENROUTER_DEBUG:
                try:
                    logging.info("\n" + "-"*80)
                    logging.info("🚀 OPENROUTER API CALL - Attempt %s", attempt + 1)
                    logging.info("-"*80)
                    logging.info("🌐 URL: %s", url)
                    logging.info("🤖 Model: %s", model)
                    if reasoning is not None and reasoning:
                        logging.info("🧠 Reasoning for this call: %s", json.dumps(reasoning, indent=2))
                    else:
                        logging.info("🧠 No reasoning for this call")
                    logging.info("📦 FULL REQUEST PAYLOAD:")
                    logging.info(_json_pp(payload))
                    logging.info("-"*80)
                except Exception as e:
                    logging.error("Failed to log full request payload: %s", str(e))

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
            # Always log response directly to console
            try:
                logging.info("✅ OPENROUTER RESPONSE")
                logging.info("📊 Status Code: %s", resp.status_code)
                logging.info("📄 FULL RESPONSE BODY:")
                logging.info(resp.text)
                
                # Also save to file to prevent terminal truncation
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = os.path.join(log_dir, f"openrouter_responses_{timestamp}.log")
                
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
                    f.write(f"MODEL: {model}\n")
                    f.write(f"INSTANCE_ID: {instance_id or 'N/A'}\n")
                    f.write(f"TRY: {try_index or 'N/A'}\n")
                    f.write(f"STATUS CODE: {resp.status_code}\n")
                    f.write(f"RESPONSE BODY:\n{resp.text}\n")
                    f.write(f"{'='*80}\n")
                logging.info("-"*80 + "\n")
            except Exception as e:
                logging.error("Failed to log full response: %s", str(e))
            if resp.status_code == 429:
                # Honor Retry-After if present
                last_retry_after = resp.headers.get("retry-after") or "2"
                retry_after = int(last_retry_after or "2")
                await asyncio.sleep((retry_after or 2) * (2 ** attempt))
                continue
            resp.raise_for_status()
            
            # Try to parse JSON, but catch and log the actual response if it fails
            try:
                return resp.json()
            except json.JSONDecodeError as json_err:
                # Log the actual response content for debugging
                response_text = resp.text
                logging.error("Failed to parse JSON response. Status: %s", resp.status_code)
                logging.error("Response headers: %s", dict(resp.headers))
                logging.error("Response text (first 1000 chars): %s", response_text[:1000])
                logging.error("Response text (last 1000 chars): %s", response_text[-1000:] if len(response_text) > 1000 else "")
                logging.error("Total response length: %s characters", len(response_text))
                
                # Save full response for debugging
                if session_id:
                    _append_session_log(
                        session_id,
                        f"JSON_PARSE_ERROR model={model} status={resp.status_code}\nResponse:\n{response_text}"
                    )
                
                # Re-raise with more context
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenRouter returned invalid JSON. Response starts with: {response_text[:100]}"
                ) from json_err
        except httpx.HTTPStatusError as e:
            # Always log errors directly to console
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
            # Always log unexpected errors directly to console
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
    - In system template: [Answer key], [Question list], [Response schema]
    - In user template: [Student assessment]
    Placeholders are replaced with actual image_url objects where appropriate.
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
        
        # Prepare replacement values
        questions_list = json.dumps({
            "question_list": [
                {
                    "question_number": q['question_number'],
                    "max_mark": q['max_mark']
                }
                for q in questions
            ]
        }, indent=2)
        
        # Prepare schema text
        if schema_template:
            schema_text = "\n\n" + schema_template.replace("[Question list]", questions_list)
        else:
            schema_text = (
                "\n\nReturn ONLY JSON with this exact schema (no markdown fences, no prose):\n"
                '{"result":[{"first_name":string,"last_name":string,'
                '"answers":[{"question_number":string,"marks_awarded":number,"rubric_notes":string}]}]}\n'
                "Use the question_number values exactly as provided in the Questions list."
            )
        
        # Process system template - replace text placeholders only
        # System messages must be plain text for compatibility with all models
        sys_text = sys_template
        
        # Replace text-only placeholders in system message
        if "[Question list]" in sys_text:
            sys_text = sys_text.replace("[Question list]", questions_list)
        
        if "[Response schema]" in sys_text:
            sys_text = sys_text.replace("[Response schema]", schema_text)
        elif schema_text:  # Append schema if placeholder not present (backward compatibility)
            sys_text = sys_text + schema_text
        
        # Process user template - build content array with support for all placeholders
        user_content: List[Dict[str, Any]] = []
        
        # Handle multiple placeholders in user message
        # We need to process the template and replace each placeholder appropriately
        remaining_template = user_template
        
        # Define placeholders and their content
        placeholders = {
            "[Answer key]": ("images", key_urls_norm),
            "[Student assessment]": ("images", stu_urls),
            "[Question list]": ("text", questions_list),
            "[Response schema]": ("text", schema_text)
        }
        
        # Find all placeholders in the template and their positions
        placeholder_positions = []
        for placeholder, (content_type, content) in placeholders.items():
            index = remaining_template.find(placeholder)
            if index != -1:
                placeholder_positions.append((index, placeholder, content_type, content))
        
        # Sort by position
        placeholder_positions.sort(key=lambda x: x[0])
        
        # Process template by splitting at each placeholder
        if placeholder_positions:
            current_pos = 0
            for index, placeholder, content_type, content in placeholder_positions:
                # Add text before placeholder
                if index > current_pos:
                    text_before = remaining_template[current_pos:index]
                    if text_before.strip():
                        user_content.append({"type": "text", "text": text_before})
                
                # Add placeholder content
                if content:
                    if content_type == "images" and content:
                        # Add image URLs
                        for url in content:
                            user_content.append({"type": "image_url", "image_url": {"url": url, "detail": "high"}})
                    elif content_type == "text" and content:
                        # Add text content
                        user_content.append({"type": "text", "text": content})
                
                # Move position past the placeholder
                current_pos = index + len(placeholder)
            
            # Add any remaining text after the last placeholder
            if current_pos < len(remaining_template):
                text_after = remaining_template[current_pos:]
                if text_after.strip():
                    user_content.append({"type": "text", "text": text_after})
        else:
            # No placeholders found, use template as is
            user_content.append({"type": "text", "text": user_template})
            
            # Add images at the end if they exist but no placeholders were found
            if key_urls_norm:
                user_content.append({"type": "text", "text": "\n\nAnswer key images:"})
                for url in key_urls_norm:
                    user_content.append({"type": "image_url", "image_url": {"url": url, "detail": "high"}})
            
            if stu_urls:
                user_content.append({"type": "text", "text": "\n\nStudent test pages:"})
                for url in stu_urls:
                    user_content.append({"type": "image_url", "image_url": {"url": url, "detail": "high"}})
        
        return [
            {"role": "system", "content": sys_text},  # Always plain text for system messages
            {"role": "user", "content": user_content},  # Content array with text and images
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
        user_content.append({"type": "image_url", "image_url": {"url": u, "detail": "high"}})
    if key_urls_norm:
        user_content.append({"type": "text", "text": "Answer key images:"})
        for u in key_urls_norm:
            user_content.append({"type": "image_url", "image_url": {"url": u, "detail": "high"}})
    # Format questions as JSON structure for consistency
    questions_json = json.dumps({
        "question_list": [
            {
                "question_number": q['question_number'],
                "max_mark": q['max_mark']
            }
            for q in questions
        ]
    }, indent=2)
    user_content.append({"type": "text", "text": "Questions: " + questions_json})

    return [
        {"role": "system", "content": sys_text},
        {"role": "user", "content": user_content},
    ]


def _extract_token_usage(raw: Dict[str, Any]) -> Dict[str, Any] | None:
    """Extract token usage information from OpenRouter API response."""
    try:
        usage = raw.get("usage", {})
        if not usage:
            return None
        
        token_data = {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": usage.get("reasoning_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        }
        
        # Add model info if available
        if raw.get("model"):
            token_data["model_id"] = raw.get("model")
        
        # Add finish reason if available
        choices = raw.get("choices", [])
        if choices and len(choices) > 0:
            finish_reason = choices[0].get("finish_reason")
            if finish_reason:
                token_data["finish_reason"] = finish_reason
        
        # Calculate cost estimate (adjust rates based on actual model pricing)
        input_cost = token_data["input_tokens"] * 0.003 / 1000  # $3 per 1M tokens
        output_cost = token_data["output_tokens"] * 0.015 / 1000  # $15 per 1M tokens
        reasoning_cost = token_data["reasoning_tokens"] * 0.001 / 1000  # $1 per 1M tokens
        token_data["cost_estimate"] = round(input_cost + output_cost + reasoning_cost, 6)
        
        return token_data
    except Exception as e:
        logging.warning(f"Failed to extract token usage: {e}")
        return None


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
    db_questions: List[Dict[str, Any]] = qs.data or []
    if not db_questions:
        raise _bad_request("no questions configured for session")
    
    # Map database fields to the format expected by _build_messages
    questions = [
        {
            "question_number": q["question_id"],  # Map question_id to question_number for LLM
            "max_mark": q["max_marks"]  # Map max_marks to max_mark for LLM
        }
        for q in db_questions
    ]

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
                # Force Anthropic provider for Claude models to avoid Google Vertex routing issues
                adjusted_model = model
                if "claude" in model.lower():
                    # If it's a Claude model without explicit provider, add anthropic provider
                    if not model.startswith("anthropic/"):
                        adjusted_model = f"anthropic/{model}"
                    # Also ensure we're not using Google's hosted Claude
                    adjusted_model = adjusted_model.replace("google/", "anthropic/")
                    
                    if OPENROUTER_DEBUG:
                        logging.info("🔄 Adjusted model name from '%s' to '%s' to force Anthropic provider", model, adjusted_model)
                
                data = await _call_openrouter(
                    client,
                    adjusted_model,
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

    # Persist results per question and token usage
    any_valid_answers: bool = False
    upserts: List[Dict[str, Any]] = []
    token_usage_records: List[Dict[str, Any]] = []
    
    for model, try_index, raw, instance_id in results:
        # Use instance_id if available, otherwise use model name
        # This allows differentiating same model with different reasoning
        model_identifier = instance_id if instance_id else model
        
        # Extract token usage from the raw response
        token_usage = _extract_token_usage(raw)
        if token_usage:
            # Use instance_id if available, otherwise use model name
            model_identifier = instance_id if instance_id else model
            
            token_usage_record = {
                "session_id": payload.session_id,
                "model_name": model_identifier,
                "try_index": try_index,
                "input_tokens": token_usage.get("input_tokens", 0),
                "output_tokens": token_usage.get("output_tokens", 0),
                "reasoning_tokens": token_usage.get("reasoning_tokens", 0),
                "cache_creation_input_tokens": token_usage.get("cache_creation_input_tokens", 0),
                "cache_read_input_tokens": token_usage.get("cache_read_input_tokens", 0),
                "model_id": token_usage.get("model_id"),
                "finish_reason": token_usage.get("finish_reason"),
                "cost_estimate": token_usage.get("cost_estimate"),
                "metadata": {"raw_usage": raw.get("usage", {})},
            }
            token_usage_records.append(token_usage_record)
            
            if OPENROUTER_DEBUG:
                logging.info("📊 Token usage for %s (try %s): input=%s, output=%s, reasoning=%s, total=%s, cost=$%.4f",
                           model_identifier, try_index,
                           token_usage.get("input_tokens", 0),
                           token_usage.get("output_tokens", 0),
                           token_usage.get("reasoning_tokens", 0),
                           token_usage.get("total_tokens", 0),
                           token_usage.get("cost_estimate", 0))
        
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
    
    # Persist token usage data
    if token_usage_records:
        try:
            # Create the token_usage table if it doesn't exist (for development)
            # In production, this should be done via proper migrations
            try:
                supabase.rpc("exec_sql", {
                    "query": """
                    CREATE TABLE IF NOT EXISTS token_usage (
                        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                        session_id UUID NOT NULL,
                        model_name TEXT NOT NULL,
                        try_index INTEGER NOT NULL,
                        input_tokens INTEGER DEFAULT 0,
                        output_tokens INTEGER DEFAULT 0,
                        reasoning_tokens INTEGER DEFAULT 0,
                        total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens + COALESCE(reasoning_tokens, 0)) STORED,
                        cache_creation_input_tokens INTEGER DEFAULT 0,
                        cache_read_input_tokens INTEGER DEFAULT 0,
                        model_id TEXT,
                        finish_reason TEXT,
                        cost_estimate DECIMAL(10, 6),
                        metadata JSONB,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT unique_token_usage_per_attempt UNIQUE (session_id, model_name, try_index)
                    )
                    """
                }).execute()
            except Exception:
                # Table might already exist, continue
                pass
            
            # Insert token usage records
            supabase.table("token_usage").upsert(
                token_usage_records,
                on_conflict="session_id,model_name,try_index"
            ).execute()
            
            if OPENROUTER_DEBUG:
                logging.info("✅ Saved token usage for %s records", len(token_usage_records))
        except Exception as e:
            # Log error but don't fail the request
            logging.error("Failed to persist token usage: %s", e)
            # Optionally append to session log
            try:
                _append_session_log(
                    payload.session_id,
                    f"TOKEN_USAGE_ERROR: {e}\n" + _json_pp(token_usage_records)
                )
            except Exception:
                pass

    # Mark session status based on whether any valid answers were parsed
    try:
        supabase.table("session").update({"status": "graded" if any_valid_answers else "failed"}).eq("id", payload.session_id).execute()
    except Exception:
        pass

    return GradeSingleRes(ok=True, session_id=payload.session_id)
