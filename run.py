"""Single-command entry point.

Default (production):
    python run.py
  → FastAPI на :8000, отдаёт API + статический frontend/out
  → http://localhost:8000

Dev режим (с hot-reload и React/Next DevTools):
    python run.py --dev
  → npm run dev на :3000 (hot-reload, dev overlay)
  → uvicorn --reload на :8000 (API)
  → Открывать http://localhost:3000
"""

import argparse
import os
import socket
import subprocess
import sys
from pathlib import Path

import uvicorn


REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"


def is_port_free(port: int) -> bool:
    """Check if port is free by trying to connect. Avoids leaving the socket
    in TIME_WAIT (что могло происходить на Windows при bind+close с
    SO_REUSEADDR — следующий uvicorn после такой проверки не стартовал)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
        except (ConnectionRefusedError, socket.timeout, OSError):
            return True   # никто не слушает → порт свободен
        return False      # connect прошёл → кто-то держит порт


def check_port_or_exit(port: int) -> None:
    if not is_port_free(port):
        print(
            f"ERROR: порт {port} уже занят — вероятно работает старый uvicorn.\n"
            f"  Найти процесс:  netstat -ano | findstr :{port}\n"
            f"  Убить процесс:  taskkill /F /PID <PID>\n"
            f"После этого запустите снова.",
            file=sys.stderr,
        )
        sys.exit(1)


def chdir_to_backend() -> None:
    if not BACKEND_DIR.is_dir():
        print(f"ERROR: backend/ not found at {BACKEND_DIR}", file=sys.stderr)
        sys.exit(1)
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))


def run_prod() -> None:
    """API + статический фронт на одном порту 8000."""
    check_port_or_exit(8000)
    chdir_to_backend()
    print("=" * 60)
    print("ИГИС-БДД | Модуль М10")
    print("=" * 60)
    print("API + frontend: http://localhost:8000")
    print("Swagger UI:     http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


def run_dev() -> None:
    """`npm run dev` (фронт с hot-reload) + `uvicorn --reload` (API).

    Открывать http://localhost:3000 — там будет фронт с DevTools и hot-reload.
    """
    check_port_or_exit(8000)
    if not FRONTEND_DIR.is_dir():
        print(f"ERROR: frontend/ not found at {FRONTEND_DIR}", file=sys.stderr)
        sys.exit(1)
    if not (FRONTEND_DIR / "node_modules").is_dir():
        print(
            "ERROR: node_modules отсутствует. Сначала:\n"
            "  cd frontend && npm install",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=" * 60)
    print("ИГИС-БДД | Модуль М10  [DEV MODE]")
    print("=" * 60)
    print("Frontend (hot-reload):  http://localhost:3000")
    print("Backend API:            http://localhost:8000")
    print("Swagger UI:             http://localhost:8000/docs")
    print("=" * 60)
    print("Ctrl+C один раз для остановки обоих процессов.")
    print()

    env = os.environ.copy()
    env["NEXT_PUBLIC_API_BASE"] = "http://localhost:8000/api/m10"

    # Spawn npm run dev. shell=True нужен на Windows чтобы найти npm.cmd.
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    npm_proc = subprocess.Popen(
        "npm run dev",
        cwd=str(FRONTEND_DIR),
        env=env,
        shell=True,
        creationflags=creationflags,
    )

    chdir_to_backend()
    try:
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    finally:
        print("\nОстанавливаю npm run dev...")
        if sys.platform == "win32":
            # Убиваем дерево процессов (npm и его дети node)
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(npm_proc.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            npm_proc.terminate()
            try:
                npm_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                npm_proc.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="ИГИС-БДД М10 launcher")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Dev mode: npm run dev (фронт с hot-reload) + uvicorn --reload (API)",
    )
    args = parser.parse_args()

    if args.dev:
        run_dev()
    else:
        run_prod()


if __name__ == "__main__":
    main()
