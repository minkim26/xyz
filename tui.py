"""Standalone entry point — run with: python tui.py"""
import sys
import os

# Re-exec with the venv Python if the current interpreter isn't it
_here = os.path.dirname(os.path.abspath(__file__))
_venv_python = os.path.join(_here, ".venv", "bin", "python")
if os.path.exists(_venv_python) and os.path.realpath(sys.executable) != os.path.realpath(_venv_python):
    os.execv(_venv_python, [_venv_python] + sys.argv)

sys.path.insert(0, os.path.join(_here, "src"))

from xyz.tui.app import main

if __name__ == "__main__":
    main()
