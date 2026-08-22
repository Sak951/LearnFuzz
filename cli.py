"""
Learn Fuzz - Red Team CLI Agent
Main CLI entrypoint.
"""
import os
import sys


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend directory is in python path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Change cwd to backend directory so sqlite database path is consistent
os.chdir(BACKEND_DIR)

from cli_agent import main

if __name__ == "__main__":
    main()
