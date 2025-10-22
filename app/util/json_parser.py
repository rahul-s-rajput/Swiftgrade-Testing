"""
Utilities for sanitizing and parsing JSON responses from LLM APIs.
Handles common issues like invalid escape sequences, markdown fences, etc.
"""

import json
import re
import logging


def sanitize_json_escapes(text: str) -> str:
    """
    Sanitize invalid escape sequences in JSON strings.
    
    Common issues from LLMs:
    - Using \\t, \\n, \\r directly in strings (should be escaped)
    - Standalone backslashes not followed by valid escape chars
    - Invalid escape sequences like \\x, \\a, etc.
    
    Args:
        text: Raw JSON text potentially containing invalid escapes
        
    Returns:
        Sanitized JSON text with proper escape sequences
    """
    # Strategy: We need to escape invalid backslash sequences
    # Valid JSON escapes are: " \ / b f n r t u (followed by 4 hex digits)
    
    # First pass: Fix common literal escape sequences that should be escaped
    # These might appear as literal characters in the string
    result = []
    i = 0
    in_string = False
    
    while i < len(text):
        char = text[i]
        
        # Track if we're inside a string
        if char == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
            result.append(char)
            i += 1
            continue
        
        # Only process escapes inside strings
        if in_string and char == '\\' and i + 1 < len(text):
            next_char = text[i + 1]
            
            # Check if this is a valid JSON escape
            if next_char in '"\\/' or next_char in 'bfnrt':
                # Valid escape, keep as-is
                result.append(char)
                result.append(next_char)
                i += 2
                continue
            elif next_char == 'u':
                # Unicode escape - check if followed by 4 hex digits
                if i + 5 < len(text) and all(c in '0123456789abcdefABCDEF' for c in text[i+2:i+6]):
                    # Valid unicode escape
                    result.append(text[i:i+6])
                    i += 6
                    continue
                else:
                    # Invalid unicode escape, escape the backslash
                    result.append('\\\\')
                    i += 1
                    continue
            else:
                # Invalid escape sequence - escape the backslash
                result.append('\\\\')
                i += 1
                continue
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)


def extract_json_from_text(text: str, strict: bool = True) -> tuple[str | None, dict | None]:
    """
    Extract JSON object from text that may contain markdown fences, preamble, etc.
    
    Args:
        text: Raw text potentially containing JSON
        strict: If True, use strict JSON parsing. If False, allow some malformations
        
    Returns:
        Tuple of (json_string, error_dict)
        - If successful: (json_string, None)
        - If failed: (None, error_dict with reason and details)
    """
    text = text.strip()
    
    # Step 1: Try to extract from markdown code block
    code_block_pattern = r'```(?:json|JSON)?\s*\n(.*?)```'
    code_match = re.search(code_block_pattern, text, re.DOTALL)
    
    if code_match:
        text = code_match.group(1).strip()
        logging.debug("📦 Extracted content from markdown code block (%d chars)", len(text))
    else:
        logging.debug("📝 No markdown code block found, using raw text (%d chars)", len(text))
    
    # Step 2: Find the first opening brace
    start = text.find("{")
    if start == -1:
        return None, {"reason": "no_json_in_content", "preview": text[:200]}
    
    # Log preamble if present
    if start > 0:
        preamble = text[:start].strip()
        if preamble:
            logging.debug("📝 LLM added preamble before JSON: %s", preamble[:100])
    
    # Step 3: Use brace matching to find the matching closing brace
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
    
    # Step 4: Extract JSON
    if end == -1:
        # Fallback to rfind
        logging.warning("⚠️ Brace matching failed, using fallback rfind method")
        end = text.rfind("}")
        if end == -1 or end <= start:
            return None, {"reason": "no_closing_brace", "preview": text[start:start+200]}
    
    json_str = text[start : end + 1]
    logging.debug("🔍 Extracted JSON string (%d chars)", len(json_str))
    
    return json_str, None


def parse_llm_json_response(text: str, strict: bool = False) -> tuple[dict | None, dict | None]:
    """
    Parse JSON from LLM response text with automatic sanitization and error recovery.
    
    This function handles common LLM output issues:
    - Markdown code fences
    - Preamble text before JSON
    - Invalid escape sequences (especially from Gemini models)
    - Trailing text after JSON
    
    Args:
        text: Raw response text from LLM
        strict: If True, fail on any JSON errors. If False, attempt recovery
        
    Returns:
        Tuple of (parsed_dict, error_dict)
        - If successful: (parsed_dict, None)
        - If failed: (None, error_dict with reason and details)
    """
    # Step 1: Extract JSON string
    json_str, extract_error = extract_json_from_text(text, strict=strict)
    
    if extract_error:
        return None, extract_error
    
    # Step 2: ALWAYS sanitize before parsing (especially important for Gemini)
    # This prevents "Invalid \escape" errors
    sanitized = sanitize_json_escapes(json_str)
    
    if sanitized != json_str:
        logging.info("🔧 Applied escape sequence sanitization (%d chars changed)", 
                    abs(len(sanitized) - len(json_str)))
    
    # Step 3: Try parsing with strict=False first (more lenient)
    try:
        obj = json.loads(sanitized, strict=False)
        logging.debug("✅ Successfully parsed JSON response")
        return obj, None
    except json.JSONDecodeError as e:
        # Step 4: If still failing and not in strict mode, try more aggressive fixes
        if not strict:
            try:
                # Try removing trailing commas (common LLM mistake)
                fixed = re.sub(r',(\s*[}\]])', r'\1', sanitized)
                obj = json.loads(fixed, strict=False)
                logging.info("✅ Parsed JSON after removing trailing commas")
                return obj, None
            except json.JSONDecodeError as e2:
                # Still failed, return detailed error
                logging.error("❌ JSON parse error even after sanitization: %s", str(e2))
                
                # Find the error location in the original text for debugging
                error_pos = getattr(e2, 'pos', None)
                context = ""
                if error_pos and error_pos > 0:
                    start = max(0, error_pos - 50)
                    end = min(len(sanitized), error_pos + 50)
                    context = sanitized[start:end]
                    # Mark the error position
                    marker_pos = error_pos - start
                    context = context[:marker_pos] + " <<<ERROR>>> " + context[marker_pos:]
                
                return None, {
                    "reason": "parse_exception",
                    "error": str(e2),
                    "original_error": str(e),
                    "json_preview": sanitized[:500],
                    "error_context": context,
                    "position": error_pos,
                    "line": getattr(e2, 'lineno', None),
                    "column": getattr(e2, 'colno', None)
                }
        else:
            # Strict mode - just return error
            return None, {
                "reason": "parse_exception",
                "error": str(e),
                "json_preview": sanitized[:500]
            }


def validate_grading_response_schema(obj: dict) -> tuple[bool, str | None]:
    """
    Validate that parsed JSON conforms to expected grading response schema.
    
    Expected schemas:
    1. Direct format: {"answers": [...]}
    2. Wrapped format: {"result": [{"first_name": ..., "answers": [...]}]}
    3. Grades format: {"grades": {...}} or {"results": {...}}
    
    Args:
        obj: Parsed JSON object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(obj, dict):
        return False, "Response is not a JSON object"
    
    # Check for any of the expected top-level keys
    has_answers = "answers" in obj and isinstance(obj["answers"], (list, dict))
    has_result = "result" in obj and isinstance(obj["result"], list)
    has_grades = ("grades" in obj or "results" in obj)
    has_grading_criteria = "grading_criteria" in obj  # For rubric responses
    
    if not (has_answers or has_result or has_grades or has_grading_criteria):
        return False, f"Missing expected keys. Found: {list(obj.keys())}"
    
    return True, None
