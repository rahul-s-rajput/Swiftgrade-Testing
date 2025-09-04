#!/usr/bin/env python3
"""
Backend executable for the Mark Grading Assistant.
This script ensures dependencies are available and starts the backend server.
"""

import sys
import os
import subprocess
from pathlib import Path

def find_python_executable():
    """Find the correct Python executable to use."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Check for .venv directory relative to the script
    venv_paths = [
        script_dir / ".venv" / "Scripts" / "python.exe",  # Windows
        script_dir / ".venv" / "bin" / "python",          # Unix/Linux/macOS
    ]
    
    for venv_python in venv_paths:
        if venv_python.exists():
            print(f"Found virtual environment Python: {venv_python}")
            return str(venv_python)
    
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"Using current virtual environment Python: {sys.executable}")
        return sys.executable
    
    # Fallback to system Python
    print(f"Using system Python: {sys.executable}")
    return sys.executable

def verify_and_install_dependencies():
    """Verify dependencies and install if missing."""
    python_exe = find_python_executable()
    script_dir = Path(__file__).parent.absolute()
    
    # Run dependency verification
    try:
        result = subprocess.run([
            python_exe, str(script_dir / "verify_dependencies.py")
        ], capture_output=True, text=True, cwd=script_dir)
        
        print("Dependency verification output:")
        print(result.stdout)
        
        if result.stderr:
            print("Dependency verification errors:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to run dependency verification: {e}")
        return False

def start_backend():
    """Start the backend server."""
    python_exe = find_python_executable()
    script_dir = Path(__file__).parent.absolute()
    
    # Start the backend runner
    try:
        # Pass through all command line arguments
        args = [python_exe, str(script_dir / "backend_runner.py")] + sys.argv[1:]
        
        print(f"Starting backend with: {' '.join(args)}")
        
        # Use subprocess.run to start the backend
        result = subprocess.run(args, cwd=script_dir)
        sys.exit(result.returncode)
            
    except Exception as e:
        print(f"Failed to start backend: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    print("Mark Grading Assistant Backend Launcher")
    print("=" * 40)
    
    # Change to the script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    print(f"Working directory: {os.getcwd()}")
    print(f"Python executable: {find_python_executable()}")
    
    # Verify dependencies
    if not verify_and_install_dependencies():
        print("[ERROR] Dependency verification failed")
        sys.exit(1)
    
    print("[OK] Dependencies verified")
    
    # Start the backend
    start_backend()

if __name__ == "__main__":
    main()