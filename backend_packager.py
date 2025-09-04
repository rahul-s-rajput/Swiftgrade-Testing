#!/usr/bin/env python3
"""
Package the FastAPI backend into a standalone executable for Tauri
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def create_backend_runner():
    """Create a runner script for the backend"""
    
    runner_content = '''
import os
import sys
import argparse
from pathlib import Path

def setup_environment():
    """Set up environment variables from .env file"""
    # Check for ENV_FILE_PATH environment variable (set by Tauri)
    env_file_path = os.environ.get('ENV_FILE_PATH')
    
    if not env_file_path:
        # Fallback to app data directory
        if sys.platform == "win32":
            app_data = Path(os.environ.get('APPDATA', '')) / 'mark-grading-assistant'
        elif sys.platform == "darwin":
            app_data = Path.home() / 'Library' / 'Application Support' / 'mark-grading-assistant'
        else:
            app_data = Path.home() / '.config' / 'mark-grading-assistant'
        
        env_file_path = app_data / '.env'
    else:
        env_file_path = Path(env_file_path)
    
    # Load environment variables from .env file
    if env_file_path.exists():
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"Loaded env var: {key}")
    else:
        print(f"Warning: .env file not found at {env_file_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    args = parser.parse_args()
    
    print(f"Starting backend on port {args.port}...")
    
    # Set up environment
    setup_environment()
    
    # Import and run the FastAPI app
    import uvicorn
    from app.main import app
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
'''
    
    with open('backend_runner.py', 'w') as f:
        f.write(runner_content)
    print("✅ Created backend_runner.py")

def create_pyinstaller_spec():
    """Create PyInstaller spec file"""
    
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['backend_runner.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app', 'app'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'httpx',
        'supabase',
        'gotrue',
        'postgrest',
        'realtime',
        'storage3',
        'supafunc',
        'httpx._transports.default',
        'httpx._transports.wsgi',
        'httpx._transports.asgi',
        'app.main',
        'app.db',
        'app.models',
        'app.schemas',
        'app.supabase_client',
        'app.routers',
        'app.routers.grade',
        'app.routers.images',
        'app.routers.questions',
        'app.routers.results',
        'app.routers.sessions',
        'app.routers.settings',
        'app.routers.stats',
        'app.util',
        'dotenv',
        'fastapi',
        'starlette',
        'pydantic',
        'typing_extensions',
        'anyio',
        'sniffio',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend',
)
'''
    
    with open('backend.spec', 'w') as f:
        f.write(spec_content)
    print("✅ Created backend.spec")

def package_backend():
    """Package the backend using PyInstaller"""
    
    print("📦 Packaging Python backend...")
    
    # Create runner and spec files
    create_backend_runner()
    create_pyinstaller_spec()
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("📥 Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Clean previous builds
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🧹 Cleaned {dir_name} directory")
    
    # Run PyInstaller
    print("🔨 Building executable...")
    result = subprocess.run(["pyinstaller", "backend.spec", "--clean"], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ PyInstaller failed:")
        print(result.stderr)
        sys.exit(1)
    
    # Create resources directory for Tauri
    resources_dir = Path("src-tauri/resources")
    resources_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy the executable (Tauri will add platform suffix automatically)
    if sys.platform == "win32":
        source = Path("dist/backend/backend.exe")
        dest = resources_dir / "backend.exe"
    else:
        source = Path("dist/backend/backend")
        dest = resources_dir / "backend"
    
    if source.exists():
        shutil.copy2(source, dest)
        print(f"✅ Backend packaged: {dest}")
    else:
        # Try to copy the entire directory if it's not a single file
        source_dir = Path("dist/backend")
        if source_dir.exists():
            dest_dir = resources_dir / "backend"
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir)
            print(f"✅ Backend packaged: {dest_dir}")
        else:
            print(f"❌ Could not find backend executable at {source}")
            sys.exit(1)
    
    # Clean up
    for file in ['backend_runner.py', 'backend.spec']:
        if os.path.exists(file):
            os.remove(file)
    
    print("✅ Backend packaging complete!")

if __name__ == "__main__":
    package_backend()
