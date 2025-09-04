#!/usr/bin/env python3
"""
Backend runner for the packaged FastAPI application.
This script handles environment configuration and starts the server.
"""

import os
import sys
import argparse
from pathlib import Path
import logging

# Ensure proper encoding for Windows console output
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def setup_environment():
    """Set up environment variables from .env file with enhanced error handling"""
    env_locations = []
    
    # Priority 1: ENV_FILE_PATH environment variable (set by Tauri)
    env_file_path = os.environ.get('ENV_FILE_PATH')
    if env_file_path:
        env_locations.append(Path(env_file_path))
    
    # Priority 2: App data directory based on OS (multiple possible locations)
    if sys.platform == "win32":
        # Try both possible paths for Windows
        app_data = Path(os.environ.get('APPDATA', '')) / 'com.markgrading.assistant'
        env_locations.append(app_data / '.env')
        # Also try the non-namespaced version
        app_data_alt = Path(os.environ.get('APPDATA', '')) / 'Mark Grading Assistant'
        env_locations.append(app_data_alt / '.env')
    elif sys.platform == "darwin":
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
    env_locations.append(Path(__file__).parent / '.env')
    
    # Try to load from each location
    loaded_vars = []
    for env_path in env_locations:
        if env_path and env_path.exists():
            print(f"Loading environment from: {env_path}")
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            try:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                # Remove quotes if present
                                if value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]
                                elif value.startswith("'") and value.endswith("'"):
                                    value = value[1:-1]
                                
                                os.environ[key] = value
                                loaded_vars.append(key)
                                print(f"Loaded env var: {key}")
                            except ValueError as e:
                                print(f"Warning: Invalid line {line_num} in {env_path}: {line}")
                
                if loaded_vars:
                    print(f"Successfully loaded {len(loaded_vars)} environment variables from {env_path}")
                    return
                    
            except Exception as e:
                print(f"Error reading {env_path}: {e}")
                continue
    
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

def main():
    """Main entry point for the backend"""
    parser = argparse.ArgumentParser(description='Mark Grading Assistant Backend')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--log-level', type=str, default='info', help='Log level')
    args = parser.parse_args()
    
    print(f"Starting Mark Grading Assistant Backend on {args.host}:{args.port}...")
    
    # Set up environment before importing app modules
    setup_environment()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s"
    )
    
    # Import and run the FastAPI app
    try:
        print("Importing backend modules...")
        import uvicorn
        print("[OK] uvicorn imported successfully")
        
        from app.main import app
        print("[OK] FastAPI app imported successfully")
        
        # Test if critical dependencies are available
        try:
            import httpx
            print("[OK] httpx is available")
        except ImportError:
            print("[ERROR] httpx is not available - /models endpoint will fail")
        
        try:
            from app.supabase_client import supabase
            print("[OK] Supabase client is available")
        except Exception as e:
            print(f"[WARNING] Supabase client issue: {e}")
        
        print("Backend modules loaded successfully")
        print(f"Starting server on {args.host}:{args.port}...")
        
        # Start the server
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level
        )
    except ImportError as e:
        print(f"[ERROR] Failed to import required modules: {e}")
        print("This might indicate missing dependencies or packaging issues")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to start backend: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()