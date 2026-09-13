"""Use this project's environment even when the IDE selects the old test interpreter."""
from pathlib import Path
import subprocess
import sys


def ensure_project_python():
    root = Path(__file__).resolve().parent
    environment = root / '.venv'
    interpreter = environment / 'Scripts' / 'python.exe'
    if not interpreter.is_file() or Path(sys.prefix).resolve() == environment.resolve():
        return
    print('[SGMO2] Switching to test2/.venv/Scripts/python.exe', flush=True)
    # Run before importing Qt, numpy or zmq. Preserve --demo and other application arguments.
    result = subprocess.call([str(interpreter), str(root / 'main.py'), *sys.argv[1:]])
    raise SystemExit(result)
