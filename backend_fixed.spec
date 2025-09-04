
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Get the absolute path to the project directory
project_dir = Path(os.path.abspath(SPECPATH))

# Add project to path for imports
sys.path.insert(0, str(project_dir))

a = Analysis(
    [str(project_dir / 'backend_runner.py')],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        # Include all app module files
        (str(project_dir / 'app'), 'app'),
    ],
    hiddenimports=[
        'app',
        'app.main',
        'app.routers',
        'app.routers.sessions',
        'app.routers.images',
        'app.routers.questions',
        'app.routers.grade',
        'app.routers.results',
        'app.routers.stats',
        'app.routers.settings',
        'app.supabase_client',
        'app.schemas',
        'app.util',
        'app.util.errors',
        'app.util.openrouter_client',
        'app.util.process_img',
        'uvicorn',
        'uvicorn.main',
        'uvicorn.config',
        'uvicorn.server',
        'uvicorn.workers',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.logging',
        'fastapi',
        'fastapi.applications',
        'starlette',
        'pydantic',
        'httpx',
        'h11',
        'httpcore',
        'supabase',
        'gotrue',
        'storage3',
        'realtime',
        'postgrest',
        'dotenv',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='.',
)
