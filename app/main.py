import os
import logging
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
import json
from dotenv import load_dotenv

from .util.errors import http_exception_handler, validation_exception_handler, general_exception_handler
from .routers import sessions as sessions_router
from .routers import images as images_router
from .routers import questions as questions_router
from .routers import grade as grade_router
from .routers import results as results_router
from .routers import stats as stats_router
from .routers import settings as settings_router


def load_environment():
    """
    Load environment variables with support for packaged backend.
    Checks multiple locations for .env file in order of priority.
    """
    env_locations = []
    
    # Priority 1: ENV_FILE_PATH environment variable (set by Tauri)
    env_file_path = os.environ.get('ENV_FILE_PATH')
    if env_file_path:
        env_locations.append(Path(env_file_path))
    
    # Priority 2: App data directory based on OS
    if hasattr(os, 'name') and os.name == 'nt':  # Windows
        # Try both possible paths for Windows
        app_data = Path(os.environ.get('APPDATA', '')) / 'com.markgrading.assistant'
        env_locations.append(app_data / '.env')
        # Also try the non-namespaced version
        app_data_alt = Path(os.environ.get('APPDATA', '')) / 'Mark Grading Assistant'
        env_locations.append(app_data_alt / '.env')
    elif hasattr(os, 'uname') and 'darwin' in os.uname().sysname.lower():  # macOS
        app_data = Path.home() / 'Library' / 'Application Support' / 'com.markgrading.assistant'
        env_locations.append(app_data / '.env')
        app_data_alt = Path.home() / 'Library' / 'Application Support' / 'Mark Grading Assistant'
        env_locations.append(app_data_alt / '.env')
    else:  # Linux/Unix
        app_data = Path.home() / '.config' / 'mark-grading-assistant'
        env_locations.append(app_data / '.env')
        app_data_alt = Path.home() / '.config' / 'com.markgrading.assistant'
        env_locations.append(app_data_alt / '.env')
    
    # Priority 3: Current working directory (development mode)
    env_locations.append(Path('.env'))
    
    # Priority 4: Project root (for development)
    env_locations.append(Path(__file__).parent.parent / '.env')
    
    # Try to load from each location
    for env_path in env_locations:
        if env_path and env_path.exists():
            print(f"Loading environment from: {env_path}")
            load_dotenv(env_path, override=True)
            
            # Log loaded environment variables (without showing sensitive values)
            loaded_vars = []
            for key in ['OPENROUTER_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 
                       'OPENROUTER_DEBUG', 'GRADING_MAX_CONCURRENCY']:
                if os.getenv(key):
                    loaded_vars.append(key)
                    print(f"Loaded env var: {key}")
            
            if loaded_vars:
                print(f"Successfully loaded {len(loaded_vars)} environment variables from {env_path}")
            return
    
    print("Warning: No .env file found in any expected location")
    print(f"Searched locations: {[str(p) for p in env_locations if p]}")
    
    # Check if we have any required environment variables
    required_vars = ['OPENROUTER_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Warning: Missing required environment variables: {missing_vars}")
        print("The application may not function correctly without these variables.")
    else:
        print("All required environment variables are present.")


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    env_origins = [o.strip() for o in raw.split(",") if o.strip()]
    
    # Always include Tauri app origins and all localhost ports
    defaults = [
        "http://localhost:*",
        "http://127.0.0.1:*",
        "tauri://localhost",
        "https://tauri.localhost",
        "http://tauri.localhost",
        # Add specific common ports
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
    ]
    
    # Merge env-provided origins with defaults, preserving order and removing duplicates
    seen: set[str] = set()
    combined: list[str] = []
    for o in env_origins + defaults:
        if o and o not in seen:
            combined.append(o)
            seen.add(o)
    return combined


def _cors_regex() -> str | None:
    # Optional regex via env; defaults to allowing localhost/127.0.0.1 with any port
    rx = os.getenv("CORS_ORIGIN_REGEX", None)
    if rx and rx.strip():
        return rx.strip()
    # Allow typical local dev origins and Tauri origins
    return r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|tauri://localhost|https://tauri\.localhost)$"


load_environment()  # Load environment variables from appropriate location

# Basic logging so router logs (INFO) are visible; allow override via LOG_LEVEL
try:
    _lvl = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, _lvl, logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
except Exception:
    pass

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger = logging.getLogger(__name__)
        
        # Log request
        body = await request.body()
        try:
            body_str = body.decode('utf-8')
        except UnicodeDecodeError:
            body_str = f"<binary data: {len(body)} bytes>"
        
        logger.info(f"REQUEST: {request.method} {request.url} Headers: {dict(request.headers)} Body: {body_str}")
        
        # Call next
        response = await call_next(request)
        
        # Log response
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        try:
            response_body_str = response_body.decode('utf-8')
        except UnicodeDecodeError:
            response_body_str = f"<binary data: {len(response_body)} bytes>"
        
        logger.info(f"RESPONSE: {response.status_code} Headers: {dict(response.headers)} Body: {response_body_str}")
        
        # Return new response with captured body
        from starlette.responses import StreamingResponse
        return StreamingResponse(iter([response_body]), status_code=response.status_code, headers=dict(response.headers))

app = FastAPI(title="Essay Grading Prototype Backend")

# Add startup diagnostics
@app.on_event("startup")
async def startup_diagnostics():
    """Perform startup diagnostics to ensure all components are working"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=== Backend Startup Diagnostics ===")
    
    # Check environment variables
    required_vars = ['OPENROUTER_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            logger.info(f"✓ {var} is configured")
    
    if missing_vars:
        logger.warning(f"⚠️ Missing environment variables: {missing_vars}")
    else:
        logger.info("✓ All required environment variables are present")
    
    # Check dependencies
    try:
        import httpx
        logger.info("✓ httpx is available for HTTP requests")
    except ImportError:
        logger.error("❌ httpx is not available - /models endpoint will fail")
    
    try:
        from .supabase_client import supabase
        logger.info("✓ Supabase client is available")
    except Exception as e:
        logger.error(f"❌ Supabase client failed to initialize: {e}")
    
    # List all registered routes
    logger.info("=== Registered Routes ===")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            logger.info(f"  {methods} {route.path}")
    
    logger.info("=== Startup Diagnostics Complete ===")

# Add debug endpoint to list all routes (moved after app initialization)
@app.get("/debug/routes")
def debug_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', None)
            })
    return {"routes": routes}

# CORS for local dev and Tauri app
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=_cors_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add logging middleware to capture full API requests and responses
app.add_middleware(LoggingMiddleware)

# Error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/health/detailed")
async def detailed_health():
    """Comprehensive health check for all backend components"""
    import logging
    logger = logging.getLogger(__name__)
    
    health_status = {
        "overall": "healthy",
        "timestamp": str(datetime.now()),
        "checks": {}
    }
    
    # Check environment variables
    required_vars = ['OPENROUTER_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    env_check = {"status": "pass", "details": {}}
    for var in required_vars:
        env_check["details"][var] = "configured" if os.getenv(var) else "missing"
        if not os.getenv(var):
            env_check["status"] = "fail"
    health_status["checks"]["environment"] = env_check
    
    # Check dependencies
    deps_check = {"status": "pass", "details": {}}
    try:
        import httpx
        deps_check["details"]["httpx"] = "available"
    except ImportError:
        deps_check["details"]["httpx"] = "missing"
        deps_check["status"] = "fail"
    
    try:
        from .supabase_client import supabase
        deps_check["details"]["supabase"] = "available"
    except Exception as e:
        deps_check["details"]["supabase"] = f"error: {str(e)}"
        deps_check["status"] = "fail"
    
    health_status["checks"]["dependencies"] = deps_check
    
    # Test database connection
    db_check = {"status": "unknown", "details": {}}
    try:
        from .supabase_client import supabase
        result = supabase.table("session").select("id").limit(1).execute()
        db_check["status"] = "pass"
        db_check["details"]["connection"] = "successful"
    except Exception as e:
        db_check["status"] = "fail"
        db_check["details"]["error"] = str(e)
    health_status["checks"]["database"] = db_check
    
    # Test OpenRouter API (if configured)
    openrouter_check = {"status": "skip", "details": {}}
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:5173"),
                    "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Mark Grading Assistant"),
                }
                
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    openrouter_check["status"] = "pass"
                    data = response.json()
                    model_count = len(data.get('data', [])) if isinstance(data.get('data'), list) else 0
                    openrouter_check["details"]["models_available"] = model_count
                else:
                    openrouter_check["status"] = "fail"
                    openrouter_check["details"]["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            openrouter_check["status"] = "fail"
            openrouter_check["details"]["error"] = str(e)
    else:
        openrouter_check["details"]["reason"] = "OPENROUTER_API_KEY not configured"
    
    health_status["checks"]["openrouter"] = openrouter_check
    
    # Determine overall status
    failed_checks = [name for name, check in health_status["checks"].items() if check["status"] == "fail"]
    if failed_checks:
        health_status["overall"] = "unhealthy"
        health_status["failed_checks"] = failed_checks
    
    return health_status


@app.get("/debug/info")
def debug_info():
    """Debug endpoint to show server info"""
    import os
    supabase_url = os.getenv("SUPABASE_URL", "Not set")
    has_key = bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    # Check if we can import supabase client successfully
    try:
        from .supabase_client import supabase
        supabase_connected = True
        # Try a simple query to test connection
        try:
            result = supabase.table("session").select("id").limit(1).execute()
            db_accessible = True
            db_error = None
        except Exception as e:
            db_accessible = False
            db_error = str(e)
    except Exception as e:
        supabase_connected = False
        db_accessible = False
        db_error = str(e)
    
    # Check httpx availability
    httpx_available = False
    try:
        import httpx
        httpx_available = True
    except ImportError:
        pass
    
    return {
        "message": "Backend is running!",
        "port": "Check the URL you used to reach this endpoint",
        "supabase_url": supabase_url,
        "has_service_key": has_key,
        "supabase_connected": supabase_connected,
        "db_accessible": db_accessible,
        "db_error": db_error,
        "env_loaded": bool(supabase_url != "Not set" or has_key),
        "has_openrouter_key": bool(os.getenv("OPENROUTER_API_KEY")),
        "httpx_available": httpx_available,
        "models_endpoint_should_work": httpx_available and bool(os.getenv("OPENROUTER_API_KEY")),
    }





# Routers - with error handling
import logging
logger = logging.getLogger(__name__)

try:
    logger.info("Registering routers...")
    app.include_router(sessions_router.router)
    logger.info("✓ Sessions router registered")
    
    app.include_router(images_router.router)
    logger.info("✓ Images router registered")
    
    app.include_router(questions_router.router)
    logger.info("✓ Questions router registered")
    
    app.include_router(grade_router.router)
    logger.info("✓ Grade router registered")
    
    app.include_router(results_router.router)
    logger.info("✓ Results router registered")
    
    app.include_router(stats_router.router)
    logger.info("✓ Stats router registered")
    
    app.include_router(settings_router.router)
    logger.info("✓ Settings router registered (includes /models endpoint)")
    
    logger.info("All routers registered successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to register routers: {e}")
    raise
