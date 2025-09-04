#!/usr/bin/env python3
"""
Backend launcher executable for Tauri.
This creates a proper .exe that Tauri can use as a sidecar.
This version embeds the FastAPI server directly and handles process cleanup properly.
"""

import sys
import os
import argparse
import logging
import signal
import atexit
from pathlib import Path
import threading
import time

# Global shutdown flag
shutdown_event = threading.Event()

def cleanup_handler(signum=None, frame=None):
    """Handle cleanup on process termination"""
    print(f"Received shutdown signal {signum}, cleaning up...", flush=True)
    shutdown_event.set()
    
    # Give the server a moment to shutdown gracefully
    time.sleep(0.5)
    
    # Force exit if still running
    os._exit(0)

def setup_signal_handlers():
    """Setup proper signal handlers for cleanup"""
    # Handle various termination signals
    signal.signal(signal.SIGTERM, cleanup_handler)
    signal.signal(signal.SIGINT, cleanup_handler)
    
    # Windows-specific
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, cleanup_handler)
    
    # Register cleanup on normal exit
    atexit.register(lambda: cleanup_handler(0, None))

def setup_environment():
    """Set up environment variables from .env file"""
    env_locations = []
    
    # Priority 1: ENV_FILE_PATH environment variable (set by Tauri)
    env_file_path = os.environ.get('ENV_FILE_PATH')
    if env_file_path:
        env_locations.append(Path(env_file_path))
    
    # Priority 2: App data directory based on OS
    if sys.platform == "win32":
        app_data = Path(os.environ.get('APPDATA', '')) / 'com.markgrading.assistant'
        env_locations.append(app_data / '.env')
        app_data_alt = Path(os.environ.get('APPDATA', '')) / 'Mark Grading Assistant'
        env_locations.append(app_data_alt / '.env')
    elif sys.platform == "darwin":
        app_data = Path.home() / 'Library' / 'Application Support' / 'com.markgrading.assistant'
        env_locations.append(app_data / '.env')
    else:  # Linux/Unix
        app_data = Path.home() / '.config' / 'mark-grading-assistant'
        env_locations.append(app_data / '.env')
    
    # Priority 3: Current working directory
    env_locations.append(Path('.env'))
    
    # Try to load from each location
    for env_path in env_locations:
        if env_path and env_path.exists():
            print(f"Loading environment from: {env_path}", flush=True)
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            
                            os.environ[key] = value
                            print(f"Loaded env var: {key}", flush=True)
                
                print(f"Environment loaded from {env_path}", flush=True)
                return
                    
            except Exception as e:
                print(f"Error reading {env_path}: {e}", flush=True)
                continue
    
    print("Warning: No .env file found in any expected location", flush=True)
    print(f"Searched locations: {[str(p) for p in env_locations if p]}", flush=True)

def run_embedded_server(host: str, port: int):
    """Run the FastAPI server directly in this process"""
    # Set up environment before importing app modules
    setup_environment()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    
    try:
        print("Starting embedded FastAPI server...", flush=True)
        
        # Import FastAPI and create a minimal app if the main app fails
        try:
            # Try to import the main app
            print("Attempting to import main app...", flush=True)
            from app.main import app
            print("Main app imported successfully", flush=True)
        except ImportError as e:
            print(f"Could not import main app: {e}", flush=True)
            print("Creating minimal FastAPI app with health endpoint...", flush=True)
            
            # Create a minimal FastAPI app with just a health endpoint
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            
            app = FastAPI(title="Mark Grading Assistant Backend")
            
            # Add CORS middleware - IMPORTANT: Include tauri://localhost for production
            app.add_middleware(
                CORSMiddleware,
                allow_origins=[
                    "http://localhost:5173",  # Dev
                    "http://localhost:*",      # Any localhost port
                    "http://127.0.0.1:*",      # Any 127.0.0.1 port
                    "tauri://localhost",       # Production Tauri
                    "https://tauri.localhost", # Alternative Tauri
                    "*"                        # Fallback - consider removing for security
                ],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            @app.get("/health")
            async def health_check():
                return {"status": "healthy", "message": "Backend is running (minimal mode)"}
            
            @app.get("/")
            async def root():
                return {"message": "Mark Grading Assistant Backend"}
        
        # Make sure the main app has proper CORS for production
        # Check if CORS middleware is already added
        has_cors = False
        for middleware in getattr(app, 'user_middleware', []):
            if 'CORSMiddleware' in str(middleware):
                has_cors = True
                break
        
        if not has_cors:
            print("Adding CORS middleware for Tauri compatibility...", flush=True)
            from fastapi.middleware.cors import CORSMiddleware
            app.add_middleware(
                CORSMiddleware,
                allow_origins=[
                    "http://localhost:5173",
                    "http://localhost:*",
                    "http://127.0.0.1:*",
                    "tauri://localhost",
                    "https://tauri.localhost",
                    "*"
                ],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Import and run uvicorn
        import uvicorn
        
        print(f"Starting server on {host}:{port}...", flush=True)
        print("Application startup complete", flush=True)  # Important for Tauri to know the server is ready
        
        # Create uvicorn server with shutdown handling
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            loop="asyncio"
        )
        server = uvicorn.Server(config)
        
        # Run server in a thread so we can handle shutdown
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def serve():
            await server.serve()
        
        # Start server
        server_task = loop.create_task(serve())
        
        # Monitor shutdown event
        def check_shutdown():
            while not shutdown_event.is_set():
                time.sleep(0.1)
            print("Shutdown requested, stopping server...", flush=True)
            server.should_exit = True
        
        shutdown_thread = threading.Thread(target=check_shutdown, daemon=True)
        shutdown_thread.start()
        
        # Run until complete
        loop.run_until_complete(server_task)
        
    except Exception as e:
        print(f"[ERROR] Failed to start embedded server: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main entry point for the backend launcher"""
    # Setup signal handlers first
    setup_signal_handlers()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Mark Grading Assistant Backend')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--log-level', type=str, default='info', help='Log level')
    args = parser.parse_args()
    
    print(f"Mark Grading Assistant Backend Launcher", flush=True)
    print(f"=" * 40, flush=True)
    print(f"Running as: {'compiled executable' if getattr(sys, 'frozen', False) else 'Python script'}", flush=True)
    print(f"Arguments: host={args.host}, port={args.port}", flush=True)
    print(f"PID: {os.getpid()}", flush=True)
    
    # Monitor parent process on Windows
    if sys.platform == "win32" and getattr(sys, 'frozen', False):
        import psutil
        parent_pid = os.getppid()
        print(f"Parent PID: {parent_pid}", flush=True)
        
        def monitor_parent():
            """Monitor parent process and exit if it dies"""
            try:
                parent = psutil.Process(parent_pid)
                while parent.is_running() and not shutdown_event.is_set():
                    time.sleep(1)
                if not shutdown_event.is_set():
                    print(f"Parent process {parent_pid} terminated, shutting down...", flush=True)
                    cleanup_handler(0, None)
            except:
                pass
        
        parent_monitor = threading.Thread(target=monitor_parent, daemon=True)
        parent_monitor.start()
    
    # Run the embedded server directly
    run_embedded_server(args.host, args.port)

if __name__ == "__main__":
    main()