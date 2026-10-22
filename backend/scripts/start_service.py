"""Native Render/Docker entrypoint: prepare schema before opening the HTTP port."""
import os
import subprocess
import sys
from pathlib import Path


def start():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    raw_port = os.environ.get("PORT", "8000")
    try:
        port = int(raw_port)
        if not 1 <= port <= 65535:
            raise ValueError()
    except ValueError:
        raise SystemExit("PORT must be an integer between 1 and 65535")
    for module, arguments in (("alembic", ["upgrade", "head"]), ("app.seed", [])):
        result = subprocess.run([sys.executable, "-m", module, *arguments], cwd=root)
        if result.returncode:
            raise SystemExit(result.returncode)
    # No --reload in a deployed service; use the exact interpreter from the venv.
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app",
                             "--host", "0.0.0.0", "--port", str(port)])


if __name__ == "__main__":
    start()
