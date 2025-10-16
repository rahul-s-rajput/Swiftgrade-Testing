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
    logging.info(f"🔑 OPENROUTER_API_KEY loaded: {'Yes' if key else 'No'}")
    if key:
        logging.info(f"🔑 Key length: {len(key)}, starts with: {key[:15]}...")
    else:
        logging.error("❌ OPENROUTER_API_KEY is not set in environment!")
        logging.error(f"Current working directory: {os.getcwd()}")
        logging.error(f"Checked env var OPENROUTER_API_KEY: {os.environ.get('OPENROUTER_API_KEY', 'NOT FOUND')}")
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


def _build_rubric_messages(rubric_urls: List[str], questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build OpenRouter chat messages for rubric analysis using DB-configured templates.

    Placeholders supported:
    - In system template: [Grading rubric images], [Question list]
    - In user template: Same placeholders supported
    """

    # Normalize URLs
    rub_urls = [
        _encode_url(u) for u in (rubric_urls or []) if isinstance(u, str) and u
    ]

    # Try to load rubric templates from Supabase
    sys_template: str | None = None
    user_template: str | None = None
    try:
        if OPENROUTER_DEBUG:
            logging.info("\n" + "-"*60)
            logging.info("🔍 Fetching rubric prompt settings from database...")
            logging.info("-"*60)
        
        res = supabase.table("app_settings").select("value").eq("key", "rubric_prompt_settings").limit(1).execute()
        rows = res.data or []
        
        if rows and len(rows) > 0:
            row = rows[0]
            value = row.get("value")
            
            # Handle different formats
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = {}
            elif value is None:
                value = {}
            elif not isinstance(value, dict):
                value = {}
            
            # Extract templates
            sys_template = value.get("system_template") if isinstance(value, dict) else None
            user_template = value.get("user_template") if isinstance(value, dict) else None
            
            # Convert and validate
            if sys_template is not None:
                sys_template = str(sys_template).strip() if sys_template else None
                if not sys_template:
                    sys_template = None
            
            if user_template is not None:
                user_template = str(user_template).strip() if user_template else None
                if not user_template:
                    user_template = None
            
            if OPENROUTER_DEBUG:
                logging.info("📄 Extracted rubric templates:")
                logging.info("  - System: %s chars", len(sys_template) if sys_template else 0)
                logging.info("  - User: %s chars", len(user_template) if user_template else 0)
    except Exception as e:
        if OPENROUTER_DEBUG:
            logging.error("❌ Failed to load rubric settings: %s", str(e))
        sys_template = None
        user_template = None

    if sys_template and user_template:
        # Use custom templates
        questions_list = json.dumps({
            "question_list": [
                {
                    "question_number": q['question_number'],
                    "max_mark": q['max_mark']
                }
                for q in questions
            ]
        }, indent=2)
        
        # Build system message (plain text)
        sys_text = sys_template
        if "[Question list]" in sys_text:
            sys_text = sys_text.replace("[Question list]", questions_list)
        
        # Build user message content array
        user_content: List[Dict[str, Any]] = []
        
        # Define placeholders for rubric messages
        placeholders = {
            "[Grading rubric images]": ("images", rub_urls),
            "[Question list]": ("text", questions_list)
        }
        
        # Process user template
        remaining_template = user_template
        placeholder_positions = []
        for placeholder, (content_type, content) in placeholders.items():
            index = remaining_template.find(placeholder)
            if index != -1:
                placeholder_positions.append((index, placeholder, content_type, content))
        
        placeholder_positions.sort(key=lambda x: x[0])
        
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
                        for url in content:
                            user_content.append({"type": "image_url", "image_url": {"url": url, "detail": "high"}})
                    elif content_type == "text" and content:
                        user_content.append({"type": "text", "text": content})
                
                current_pos = index + len(placeholder)
            
            # Add remaining text
            if current_pos < len(remaining_template):
                text_after = remaining_template[current_pos:]
                if text_after.strip():
                    user_content.append({"type": "text", "text": text_after})
        else:
            user_content.append({"type": "text", "text": user_template})
        
        return [
            {"role": "system", "content": sys_text},
            {"role": "user", "content": user_content},
        ]
    else:
        # Default fallback
        sys_text = (
            "You are a grading rubric analyzer. Analyze the rubric images and extract grading criteria.\n"
            "Return the criteria as clear text organized by question."
        )
        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": "Analyze these grading rubric images:"},
        ]
        for u in rub_urls:
            user_content.append({"type": "image_url", "image_url": {"url": u, "detail": "high"}})
        
        questions_json = json.dumps({
            "question_list": [
                {"question_number": q['question_number'], "max_mark": q['max_mark']}
                for q in questions
            ]
        }, indent=2)
        user_content.append({"type": "text", "text": "Questions: " + questions_json})
        
        return [
            {"role": "system", "content": sys_text},
            {"role": "user", "content": user_content},
        ]


async def _call_rubric_llm(
    client: httpx.AsyncClient,
    model: str,
    rubric_urls: List[str],
    questions: List[Dict[str, Any]],
    reasoning: Dict[str, Any] | None,
    session_id: str,
    try_index: int,
    instance_id: str | None = None
) -> str:
    """Call rubric analysis LLM and return extracted rubric text.
    
    Stores the full response in rubric_result table.
    Returns the extracted rubric text for use in assessment.
    """
    messages = _build_rubric_messages(rubric_urls, questions)
    
    # Call OpenRouter
    raw_response = await _call_openrouter(
        client,
        model,
        messages,
        reasoning,
        session_id=session_id,
        try_index=try_index,
        instance_id=instance_id or model
    )
    
    # Extract rubric text from response and parse JSON
    rubric_text = ""
    raw_text = ""  # Define outside try block for proper scoping
    validation_errors = None
    
    try:
        choices = raw_response.get("choices") or []
        if not choices:
            validation_errors = {"reason": "no_choices"}
        else:
            msg = choices[0].get("message", {})
            content = msg.get("content")
            
            # Get raw text
            if isinstance(content, str):
                raw_text = content.strip()
            elif isinstance(content, list):
                # Concatenate text parts
                parts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        parts.append(c.get("text", ""))
                raw_text = "\n".join(parts).strip()
            else:
                validation_errors = {"reason": "unsupported_content_type"}
                
            # Extract JSON from raw text (handles preamble, markdown fences, etc.)
            if raw_text and not validation_errors:
                import re
                
                text = raw_text
                
                # Try to extract content from markdown code block using regex
                # Pattern: ```json or ``` at start, capture everything until closing ```
                code_block_pattern = r'```(?:json|JSON)?\s*\n(.*?)```'
                code_match = re.search(code_block_pattern, text, re.DOTALL)
                
                if code_match:
                    # Found code block, extract the content (which may still have preamble before {)
                    text = code_match.group(1).strip()
                    if OPENROUTER_DEBUG:
                        logging.info("📦 Extracted content from markdown code block (%d chars)", len(text))
                else:
                    # No code block found, use raw text as-is
                    text = text.strip()
                    if OPENROUTER_DEBUG:
                        logging.info("📝 No markdown code block found, using raw text (%d chars)", len(text))
                
                # Find the first opening brace (skips any remaining preamble text)
                start = text.find("{")
                if start == -1:
                    if OPENROUTER_DEBUG:
                        logging.warning("⚠️ No JSON object found in rubric LLM response")
                        logging.warning("Response preview: %s", text[:300])
                    validation_errors = {"reason": "no_json_in_content", "preview": text[:200]}
                else:
                    # Log if there's preamble text before JSON
                    if start > 0 and OPENROUTER_DEBUG:
                        preamble = text[:start].strip()
                        if preamble:
                            logging.info("📝 Rubric LLM added preamble before JSON: %s", preamble[:100])
                    
                    # Use brace matching to find closing brace
                    brace_count = 0
                    end = -1
                    in_string = False
                    escape_next = False
                    
                    for i in range(start, len(text)):
                        char = text[i]
                        
                        if escape_next:
                            escape_next = False
                            continue
                        
                        if char == '\\':
                            escape_next = True
                            continue
                        
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        
                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end = i
                                    break
                    
                    if end == -1:
                        if OPENROUTER_DEBUG:
                            logging.warning("⚠️ Brace matching failed for rubric response")
                        end = text.rfind("}")
                        if end == -1 or end <= start:
                            validation_errors = {"reason": "no_closing_brace", "preview": text[start:start+200]}
                    
                    if end != -1 and not validation_errors:
                        # Extract only the JSON portion
                        json_str = text[start : end + 1]
                        
                        # Validate it's proper JSON
                        try:
                            parsed = json.loads(json_str)
                            rubric_text = json_str  # Store the clean JSON string
                            
                            if OPENROUTER_DEBUG:
                                logging.info("✅ Successfully extracted and validated rubric JSON (%d chars)", len(json_str))
                                
                            # Validate structure
                            if not isinstance(parsed, dict):
                                validation_errors = {"reason": "rubric_not_dict"}
                            elif "grading_criteria" not in parsed:
                                validation_errors = {"reason": "missing_grading_criteria_key"}
                            elif not isinstance(parsed.get("grading_criteria"), list):
                                validation_errors = {"reason": "grading_criteria_not_array"}
                        except json.JSONDecodeError as json_err:
                            logging.error("❌ Rubric JSON parse error: %s", str(json_err))
                            logging.error("Attempted to parse: %s", json_str[:500])
                            validation_errors = {
                                "reason": "parse_exception",
                                "error": str(json_err),
                                "json_preview": json_str[:200]
                            }
                            
    except Exception as e:
        validation_errors = {"reason": "parse_exception", "error": str(e)}
        logging.error("❌ Exception during rubric extraction: %s", str(e))
        import traceback
        logging.error("Full traceback: %s", traceback.format_exc())
    
    # Log the extraction result
    if rubric_text:
        if OPENROUTER_DEBUG:
            logging.info("✅ Rubric extraction successful, storing %d chars of clean JSON", len(rubric_text))
    else:
        logging.warning("⚠️ Rubric extraction failed, validation_errors: %s", validation_errors)
        if raw_text:
            logging.warning("Raw text preview (first 500 chars): %s", raw_text[:500])
    
    # Store in rubric_result table
    model_identifier = instance_id if instance_id else model
    rubric_record = {
        "session_id": session_id,
        "model_name": model_identifier,
        "try_index": try_index,
        "rubric_response": rubric_text if rubric_text else None,
        "raw_output": raw_response,
        "validation_errors": validation_errors,
    }
    
    try:
        supabase.table("rubric_result").upsert(
            rubric_record,
            on_conflict="session_id,model_name,try_index"
        ).execute()
        
        if OPENROUTER_DEBUG:
            logging.info("✅ Saved rubric result for %s (try %s): %s chars",
                       model_identifier, try_index, len(rubric_text) if rubric_text else 0)
    except Exception as e:
        logging.error("Failed to store rubric result: %s", e)
    
    # Log to session log
    try:
        _append_session_log(
            session_id,
            f"RUBRIC_EXTRACTED model={model} instance_id={instance_id or ''} try={try_index}\n" +
            f"Rubric text ({len(rubric_text)} chars): {rubric_text[:500]}..."
        )
    except Exception:
        pass
    
    if not rubric_text and validation_errors:
        logging.warning("Rubric LLM failed to extract text: %s", validation_errors)
    
    return rubric_text


def _build_messages(
    student_urls: List[str],
    key_urls: List[str],
    questions: List[Dict[str, Any]],
    rubric_text: str | None = None  # NEW PARAMETER
) -> List[Dict[str, Any]]:
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
        
        if OPENROUTER_DEBUG:
            logging.info("🔍 Rubric text parameter: %s chars, is None: %s, is empty: %s",
                       len(rubric_text) if rubric_text else 0,
                       rubric_text is None,
                       rubric_text == "" if rubric_text is not None else "N/A")
        
        # Replace text-only placeholders in system message
        if "[Question list]" in sys_text:
            sys_text = sys_text.replace("[Question list]", questions_list)
        
        # NEW: Replace [Grading Rubric] placeholder with rubric text
        if rubric_text and "[Grading Rubric]" in sys_text:
            sys_text = sys_text.replace("[Grading Rubric]", rubric_text)
            if OPENROUTER_DEBUG:
                logging.info("✅ Replaced [Grading Rubric] in system template with %s chars", len(rubric_text))
        
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
            "[Response schema]": ("text", schema_text),
            "[Grading Rubric]": ("text", rubric_text if rubric_text else "")
        }
        
        if OPENROUTER_DEBUG:
            logging.info("🔍 Placeholders defined:")
            for ph, (ptype, pcontent) in placeholders.items():
                if ptype == "text":
                    logging.info("  - %s: type=%s, content_length=%s, is_empty=%s",
                               ph, ptype, len(pcontent) if pcontent else 0, not pcontent)
                else:
                    logging.info("  - %s: type=%s, count=%s", ph, ptype, len(pcontent) if pcontent else 0)
        
        # Find all placeholders in the template and their positions
        placeholder_positions = []
        for placeholder, (content_type, content) in placeholders.items():
            index = remaining_template.find(placeholder)
            if index != -1:
                placeholder_positions.append((index, placeholder, content_type, content))
                if OPENROUTER_DEBUG:
                    logging.info("  ✓ Found %s at position %s", placeholder, index)
        
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
                        if OPENROUTER_DEBUG and placeholder == "[Grading Rubric]":
                            logging.info("✅ Added [Grading Rubric] content: %s chars", len(content))
                else:
                    if OPENROUTER_DEBUG and placeholder == "[Grading Rubric]":
                        logging.warning("⚠️ [Grading Rubric] placeholder found but content is empty/falsy: %s", repr(content))
                
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


def _repair_json_string(text: str) -> str:
    """Attempt basic JSON repair for common LLM output issues.
    
    This function handles:
    - Markdown code fences (```json) anywhere in text
    - Preamble text before JSON
    - Extra text after the closing brace
    - Trailing commas
    """
    import re
    
    text = text.strip()
    
    # Try to extract content from markdown code block using regex
    # This handles preamble text before the code block
    code_block_pattern = r'```(?:json|JSON)?\s*\n(.*?)```'
    code_match = re.search(code_block_pattern, text, re.DOTALL)
    
    if code_match:
        # Found code block, extract the content
        text = code_match.group(1).strip()
    else:
        # No code block, use text as-is
        text = text.strip()
    
    # Find the JSON object using brace matching
    start = text.find("{")
    if start == -1:
        return text
    
    # Match braces to find the actual end of JSON
    brace_count = 0
    end = -1
    in_string = False
    escape_next = False
    
    for i in range(start, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i
                    break
    
    if end != -1:
        # Extract only the JSON portion
        return text[start:end + 1]
    
    return text


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

        # Try to locate JSON block with improved parsing
        import re
        
        text = text.strip()
        
        # Try to extract content from markdown code block using regex
        # This properly handles preamble text BEFORE the code block
        code_block_pattern = r'```(?:json|JSON)?\s*\n(.*?)```'
        code_match = re.search(code_block_pattern, text, re.DOTALL)
        
        if code_match:
            # Found code block, extract the content
            text = code_match.group(1).strip()
            if OPENROUTER_DEBUG:
                logging.info("📦 Extracted content from markdown code block (%d chars)", len(text))
        else:
            # No code block, use raw text
            text = text.strip()
            if OPENROUTER_DEBUG:
                logging.info("📝 No markdown code block found, using raw text (%d chars)", len(text))
        
        # Find the first opening brace (skips any remaining preamble text)
        start = text.find("{")
        if start == -1:
            if OPENROUTER_DEBUG:
                logging.warning("⚠️ No JSON object found in LLM response")
                logging.warning("Response preview: %s", text[:300])
            return None, {"reason": "no_json_in_content", "preview": text[:200]}
        
        # Log if there's text before the JSON (common with some models)
        if start > 0 and OPENROUTER_DEBUG:
            preamble = text[:start].strip()
            if preamble:
                logging.info("📝 LLM added preamble before JSON: %s", preamble[:100])
        
        # Use brace matching to find the MATCHING closing brace
        # This handles nested objects correctly
        brace_count = 0
        end = -1
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            char = text[i]
            
            # Handle string escaping
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # Track if we're inside a string (to ignore braces in strings)
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            # Only count braces outside of strings
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found the matching closing brace
                        end = i
                        break
        
        if end == -1:
            # Fallback to rfind if brace matching fails
            if OPENROUTER_DEBUG:
                logging.warning("⚠️ Brace matching failed, using fallback rfind method")
            end = text.rfind("}")
            if end == -1 or end <= start:
                if OPENROUTER_DEBUG:
                    logging.error("❌ No closing brace found in LLM response")
                    logging.error("Text excerpt: %s", text[start:start+200])
                return None, {"reason": "no_closing_brace", "preview": text[start:start+200]}
        
        # Extract ONLY the JSON portion (nothing after the closing brace)
        json_str = text[start : end + 1]
        
        if OPENROUTER_DEBUG:
            logging.info("🔍 Extracted JSON string (%d chars)", len(json_str))
            if len(json_str) < 500:
                logging.debug("Full JSON: %s", json_str)
        
        # Attempt to parse
        try:
            obj = json.loads(json_str)
            if OPENROUTER_DEBUG:
                logging.info("✅ Successfully parsed JSON response")
        except json.JSONDecodeError as json_err:
            # If parsing still fails, log the problematic JSON for debugging
            logging.error("❌ JSON parse error: %s", str(json_err))
            logging.error("Error at position %s (line %s, col %s)", 
                         json_err.pos if hasattr(json_err, 'pos') else 'unknown',
                         json_err.lineno if hasattr(json_err, 'lineno') else 'unknown',
                         json_err.colno if hasattr(json_err, 'colno') else 'unknown')
            logging.error("Attempted to parse: %s", json_str[:500])
            
            # Try to identify common issues
            error_hints = []
            if "Expecting property name" in str(json_err):
                error_hints.append("Possible trailing comma or missing quote")
            if "Expecting value" in str(json_err):
                error_hints.append("Possible extra comma or missing value")
            if "Unterminated string" in str(json_err):
                error_hints.append("String not properly closed")
            
            return None, {
                "reason": "parse_exception", 
                "error": str(json_err), 
                "json_preview": json_str[:200],
                "hints": error_hints if error_hints else None
            }
        
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
    rubric_urls = [r["url"] for r in (imgs.data or []) if r.get("role") == "grading_rubric"]  # NEW
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

    # Determine if using new model_pairs or legacy models
    use_model_pairs = payload.model_pairs is not None and len(payload.model_pairs) > 0
    use_legacy_models = payload.models is not None and len(payload.models) > 0
    
    if not use_model_pairs and not use_legacy_models:
        raise _bad_request("Either model_pairs or models must be provided")
    
    # Expand model tries
    if use_model_pairs:
        # NEW: Model pairs flow (rubric + assessment)
        # items: List[Tuple[rubric_model, assessment_model, try_index, rubric_reasoning, assessment_reasoning, instance_id]]
        items: List[Tuple[str, str, int, Dict[str, Any] | None, Dict[str, Any] | None, str | None]] = []
        
        for pair_idx, pair in enumerate(payload.model_pairs):
            rubric_model = pair.rubric_model.name
            assessment_model = pair.assessment_model.name
            
            # Determine tries from assessment model (rubric runs same number of times)
            tries = pair.assessment_model.tries if pair.assessment_model.tries and pair.assessment_model.tries > 0 else (payload.default_tries or 1)
            tries = max(1, tries)
            
            # Get reasoning configs
            rubric_reasoning = pair.rubric_model.reasoning if pair.rubric_model.reasoning else None
            assessment_reasoning = pair.assessment_model.reasoning if pair.assessment_model.reasoning else payload.reasoning
            
            # Generate instance_id if not provided
            pair_instance_id = pair.instance_id if pair.instance_id else f"pair_{pair_idx}_{rubric_model}_{assessment_model}"
            
            for i in range(1, tries + 1):
                items.append((rubric_model, assessment_model, i, rubric_reasoning, assessment_reasoning, pair_instance_id))
        
        if OPENROUTER_DEBUG:
            logging.info("🔗 Using model pairs flow: %s pairs expanded to %s tasks", len(payload.model_pairs), len(items))
    else:
        # LEGACY: Single models flow (no rubric)
        # items: List[Tuple[model, try_index, reasoning, instance_id, None, None]]
        # We'll use a compatible tuple structure for backward compat
        items: List[Tuple[str, str | None, int, Dict[str, Any] | None, Dict[str, Any] | None, str | None]] = []
        
        for m in payload.models:
            model_name = m.name
            tries = m.tries if m.tries and m.tries > 0 else (payload.default_tries or 1)
            tries = max(1, tries)
            model_reasoning = m.reasoning if hasattr(m, 'reasoning') and m.reasoning else payload.reasoning
            instance_id = m.instance_id if hasattr(m, 'instance_id') and m.instance_id else None
            
            for i in range(1, tries + 1):
                # Legacy format: (model, None, try_index, reasoning, None, instance_id)
                # None in position 1 indicates no rubric model (legacy flow)
                items.append((model_name, None, i, model_reasoning, None, instance_id))
        
        if OPENROUTER_DEBUG:
            logging.info("🔙 Using legacy single models flow: %s models expanded to %s tasks", len(payload.models), len(items))

    # Persist session configuration for UI
    try:
        if use_model_pairs:
            rubric_models = [pair.rubric_model.name for pair in payload.model_pairs]
            assessment_models = [pair.assessment_model.name for pair in payload.model_pairs]
            
            # Serialize complete model pair specifications including reasoning configs
            model_pairs_data = [
                {
                    "rubricModel": pair.rubric_model.name,
                    "assessmentModel": pair.assessment_model.name,
                    "rubricReasoning": pair.rubric_model.reasoning if pair.rubric_model.reasoning else None,
                    "assessmentReasoning": pair.assessment_model.reasoning if pair.assessment_model.reasoning else None,
                    "instanceId": pair.instance_id if pair.instance_id else None,
                }
                for pair in payload.model_pairs
            ]
            
            supabase.table("session").update({
                "rubric_models": rubric_models,
                "assessment_models": assessment_models,
                "model_pairs": model_pairs_data,  # NEW: Save complete specifications
                "default_tries": payload.default_tries or 1,
            }).eq("id", payload.session_id).execute()
        else:
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
    
    # Build messages for legacy flow only (model pairs build messages dynamically)
    legacy_messages = None
    if not use_model_pairs:
        legacy_messages = _build_messages(student_urls, key_urls, questions)
    
    # Debug: Log the exact system and user messages for legacy flow
    if OPENROUTER_DEBUG and legacy_messages:
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

            sys_msg = next((m.get("content") for m in legacy_messages if m.get("role") == "system"), None)
            user_msg = next((m.get("content") for m in legacy_messages if m.get("role") == "user"), None)
            
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
    if OPENROUTER_DEBUG and legacy_messages:
        try:
            urls: List[str] = []
            user_msg = next((m.get("content") for m in legacy_messages if m.get("role") == "user"), [])
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
        if use_model_pairs:
            # NEW: Model pairs flow (rubric + assessment)
            async def run_task(rubric_model: str, assessment_model: str, try_index: int,
                             rubric_reasoning: Dict[str, Any] | None, assessment_reasoning: Dict[str, Any] | None,
                             instance_id: str | None):
                async with semaphore:
                    # STAGE 1: Call rubric LLM
                    if OPENROUTER_DEBUG:
                        logging.info("📖 [PAIR %s] Try %s: Starting rubric analysis with %s",
                                   instance_id, try_index, rubric_model)
                    
                    rubric_text = ""
                    if rubric_urls:
                        try:
                            rubric_text = await _call_rubric_llm(
                                client,
                                rubric_model,
                                rubric_urls,
                                questions,
                                rubric_reasoning,
                                payload.session_id,
                                try_index,
                                instance_id
                            )
                            if OPENROUTER_DEBUG:
                                logging.info("✅ [PAIR %s] Try %s: Rubric extracted (%s chars)",
                                           instance_id, try_index, len(rubric_text))
                        except Exception as e:
                            logging.error("❌ [PAIR %s] Try %s: Rubric LLM failed: %s",
                                        instance_id, try_index, str(e))
                            # Store error and skip assessment
                            return rubric_model, assessment_model, try_index, None, None, instance_id, str(e)
                    else:
                        logging.warning("⚠️ No rubric images available, skipping rubric analysis")
                    
                    # STAGE 2: Call assessment LLM with rubric
                    if OPENROUTER_DEBUG:
                        logging.info("🎯 [PAIR %s] Try %s: Starting assessment with %s",
                                   instance_id, try_index, assessment_model)
                    
                    # Build messages with rubric text
                    messages = _build_messages(student_urls, key_urls, questions, rubric_text=rubric_text)
                    
                    # Force Anthropic provider for Claude models
                    adjusted_model = assessment_model
                    if "claude" in assessment_model.lower():
                        if not assessment_model.startswith("anthropic/"):
                            adjusted_model = f"anthropic/{assessment_model}"
                        adjusted_model = adjusted_model.replace("google/", "anthropic/")
                        if OPENROUTER_DEBUG:
                            logging.info("🔄 Adjusted assessment model from '%s' to '%s'",
                                       assessment_model, adjusted_model)
                    
                    data = await _call_openrouter(
                        client,
                        adjusted_model,
                        messages,
                        assessment_reasoning,
                        session_id=payload.session_id,
                        try_index=try_index,
                        instance_id=instance_id,
                    )
                    
                    if OPENROUTER_DEBUG:
                        logging.info("✅ [PAIR %s] Try %s: Assessment complete", instance_id, try_index)
                    
                    return rubric_model, assessment_model, try_index, rubric_text, data, instance_id, None
            
            # Create tasks for model pairs
            tasks = [
                asyncio.create_task(run_task(rub_m, ass_m, t, rub_r, ass_r, inst_id))
                for rub_m, ass_m, t, rub_r, ass_r, inst_id in items
            ]
        else:
            # LEGACY: Single models flow
            async def run_task(model: str, try_index: int, reasoning: Dict[str, Any] | None, instance_id: str | None):
                async with semaphore:
                    # Force Anthropic provider for Claude models
                    adjusted_model = model
                    if "claude" in model.lower():
                        if not model.startswith("anthropic/"):
                            adjusted_model = f"anthropic/{model}"
                        adjusted_model = adjusted_model.replace("google/", "anthropic/")
                        
                        if OPENROUTER_DEBUG:
                            logging.info("🔄 Adjusted model name from '%s' to '%s' to force Anthropic provider", model, adjusted_model)
                    
                    data = await _call_openrouter(
                        client,
                        adjusted_model,
                        legacy_messages,
                        reasoning,
                        session_id=payload.session_id,
                        try_index=try_index,
                        instance_id=instance_id,
                    )
                    return model, try_index, data, instance_id
            
            # Create tasks for legacy single models
            tasks = [
                asyncio.create_task(run_task(model, t, reasoning, inst_id))
                for model, _, t, reasoning, _, inst_id in items
            ]
        # Collect results - handle both legacy and new formats
        if use_model_pairs:
            # NEW format: (rubric_model, assessment_model, try_index, rubric_text, data, instance_id, error)
            results: List[Tuple[str, str, int, str | None, Dict[str, Any] | None, str | None, str | None]] = []
        else:
            # LEGACY format: (model, try_index, data, instance_id)
            results: List[Tuple[str, int, Dict[str, Any], str | None]] = []
        
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
    
    if use_model_pairs:
        # NEW: Process model pair results
        for rubric_model, assessment_model, try_index, rubric_text, raw, instance_id, error in results:
            # Use instance_id as model identifier (represents the pair)
            model_identifier = instance_id if instance_id else f"{rubric_model}_{assessment_model}"
            
            # If there was an error in rubric stage, skip assessment processing
            if error:
                logging.error("❌ Pair %s try %s failed at rubric stage: %s", model_identifier, try_index, error)
                # Store error marker
                upserts.append({
                    "session_id": payload.session_id,
                    "question_id": "__rubric_error__",
                    "model_name": model_identifier,
                    "try_index": try_index,
                    "marks_awarded": None,
                    "rubric_notes": None,
                    "raw_output": {"error": error},
                    "validation_errors": {"reason": "rubric_failed", "error": error},
                })
                continue
            
            # If no raw data (assessment didn't run), skip
            if not raw:
                continue
            
            # Extract token usage from assessment response
            token_usage = _extract_token_usage(raw)
            if token_usage:
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
                    "metadata": {"raw_usage": raw.get("usage", {}), "pair": {"rubric": rubric_model, "assessment": assessment_model}},
                }
                token_usage_records.append(token_usage_record)
                
                if OPENROUTER_DEBUG:
                    logging.info("📊 Token usage for %s (try %s): input=%s, output=%s, reasoning=%s",
                               model_identifier, try_index,
                               token_usage.get("input_tokens", 0),
                               token_usage.get("output_tokens", 0),
                               token_usage.get("reasoning_tokens", 0))
            
            # Parse assessment response
            answers, verr = _parse_model_output(raw)
            if answers:
                any_valid_answers = True
                try:
                    _append_session_log(
                        payload.session_id,
                        f"PARSED_PAIR rubric={rubric_model} assessment={assessment_model} instance_id={instance_id or ''} try={try_index}\n" +
                        _json_pp({"answers": answers})
                    )
                except Exception:
                    logging.exception("Failed to log parsed answers")
                
                for a in answers:
                    upserts.append({
                        "session_id": payload.session_id,
                        "question_id": a.get("question_id"),
                        "model_name": model_identifier,
                        "try_index": try_index,
                        "marks_awarded": a.get("marks_awarded"),
                        "rubric_notes": a.get("rubric_notes"),
                        "raw_output": raw,
                        "validation_errors": None,
                    })
            else:
                # Record validation error
                try:
                    _append_session_log(
                        payload.session_id,
                        f"PARSE_ERROR_PAIR rubric={rubric_model} assessment={assessment_model} instance_id={instance_id or ''} try={try_index}\n" +
                        _json_pp(verr)
                    )
                except Exception:
                    logging.exception("Failed to log parse error")
                
                upserts.append({
                    "session_id": payload.session_id,
                    "question_id": "__parse_error__",
                    "model_name": model_identifier,
                    "try_index": try_index,
                    "marks_awarded": None,
                    "rubric_notes": None,
                    "raw_output": raw,
                    "validation_errors": verr,
                })
    else:
        # LEGACY: Process single model results
        for model, try_index, raw, instance_id in results:
            # Use instance_id if available, otherwise use model name
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
        
        # Batch upserts to avoid SSL issues with large payloads
        BATCH_SIZE = 50  # Process 50 records at a time
        total_batches = (len(upserts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        if OPENROUTER_DEBUG:
            logging.info("📦 Upserting %s records in %s batches (batch size: %s)", 
                        len(upserts), total_batches, BATCH_SIZE)
        
        for batch_idx in range(0, len(upserts), BATCH_SIZE):
            batch = upserts[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = (batch_idx // BATCH_SIZE) + 1
            
            # Retry logic with exponential backoff for SSL errors
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if OPENROUTER_DEBUG and len(upserts) > BATCH_SIZE:
                        logging.info("  📤 Batch %s/%s: Upserting %s records (attempt %s/%s)", 
                                   batch_num, total_batches, len(batch), attempt + 1, max_retries)
                    
                    supabase.table("result").upsert(
                        batch,
                        on_conflict="session_id,question_id,model_name,try_index",
                    ).execute()
                    
                    if OPENROUTER_DEBUG and len(upserts) > BATCH_SIZE:
                        logging.info("  ✅ Batch %s/%s: Success", batch_num, total_batches)
                    
                    break  # Success, move to next batch
                    
                except Exception as e:
                    error_str = str(e).lower()
                    is_retryable = any(x in error_str for x in [
                        'ssl', 'eof', 'connection', 'timeout', 'broken pipe', 
                        'network', 'socket', 'timed out'
                    ])
                    
                    if attempt < max_retries - 1 and is_retryable:
                        # Retryable error, wait and retry
                        wait_time = (2 ** attempt)  # 1s, 2s, 4s
                        logging.warning("⚠️ Batch %s/%s failed (attempt %s/%s): %s - Retrying in %ss...", 
                                      batch_num, total_batches, attempt + 1, max_retries, 
                                      str(e)[:100], wait_time)
                        await asyncio.sleep(wait_time)
                    else:
                        # Final attempt failed or non-retryable error
                        logging.error("❌ Batch %s/%s failed after %s attempts: %s", 
                                    batch_num, total_batches, attempt + 1, str(e))
                        # Mark session failed
                        try:
                            supabase.table("session").update({"status": "failed"}).eq("id", payload.session_id).execute()
                        except Exception:
                            pass
                        raise HTTPException(
                            status_code=500, 
                            detail=f"failed to persist results (batch {batch_num}/{total_batches}, attempt {attempt + 1}/{max_retries}): {e}"
                        )
        
        if OPENROUTER_DEBUG and len(upserts) > BATCH_SIZE:
            logging.info("✅ All %s batches completed successfully", total_batches)
    
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
