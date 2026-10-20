"""Disposable backend/database for every E2E; never seeds the user database."""
import subprocess
import json
import threading
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
    def command(args, check=True, input=None):
        return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True, encoding="utf-8", errors="replace", input=input)
    started = False
    attached = None
    reader = None
    try:
        # In-memory Compose override: Docker must not persist QA container logs either.
        override = json.dumps({"services": {"backend": {"logging": {"driver": "none"}}}})
        command(["docker-compose", "-f", "docker-compose.yml", "-f", "-", "run", "--rm", "--no-deps", "-d", "--name", name,
            "-p", "127.0.0.1::8000", "-e", "SPAOS_QA_DB="+database,
            "-e", "SPAOS_QA_SEED_DEMO=1", "backend", "python", "-m", "scripts.operator_qa_server"], input=override)
        started = True
        attached = subprocess.Popen(["docker", "attach", "--no-stdin", name], cwd=ROOT,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
        def forward_diagnostics():
            for line in attached.stdout:
                if "authentication" in line.lower():
                    print(line.rstrip(), flush=True)
        reader = threading.Thread(target=forward_diagnostics, daemon=True)
        reader.start()
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
            command(["docker", "stop", "-t", "2", name], check=False)
        if attached is not None:
            try:
                attached.wait(timeout=5)
            except subprocess.TimeoutExpired:
                attached.kill()
                attached.wait(timeout=5)
            if reader is not None:
                reader.join(timeout=5)
            attached.stdout.close()
        command(["docker-compose", "exec", "-T", "backend", "python", "-m", "scripts.operator_qa_server", "--drop", database])

