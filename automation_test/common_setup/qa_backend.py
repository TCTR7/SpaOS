"""Disposable backend/database for every E2E; never seeds the user database."""
import subprocess
import time
import uuid
from pathlib import Path
from contextlib import contextmanager
import httpx

ROOT = Path(__file__).resolve().parents[2]

@contextmanager
def qa_backend():
    suffix = uuid.uuid4().hex
    name, database = "spaos-e2e-qa-" + suffix, "spaos_e2e_" + suffix
    def command(args, check=True):
        return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True, encoding="utf-8", errors="replace")
    started = False
    try:
        result = command(["docker-compose", "run", "--rm", "--no-deps", "-d", "--name", name,
            "-p", "127.0.0.1::8000", "-e", "SPAOS_QA_DB="+database,
            "-e", "SPAOS_QA_SEED_DEMO=1", "backend", "python", "-m", "scripts.operator_qa_server"])
        started = True
        port = command(["docker", "port", name, "8000"]).stdout.strip().rsplit(":", 1)[1]
        url = "http://127.0.0.1:" + str(int(port))
        for _ in range(120):
            try:
                if httpx.get(url+"/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.25)
        else:
            raise RuntimeError("Operator QA backend did not become ready")
        yield url
    finally:
        if started:
            logs = command(["docker", "logs", "--tail", "1000", name], check=False)
            for line in (logs.stdout + logs.stderr).splitlines():
                if "authentication" in line.lower():
                    print(line)
            command(["docker", "stop", "-t", "2", name], check=False)
        command(["docker-compose", "exec", "-T", "backend", "python", "-m", "scripts.operator_qa_server", "--drop", database])

