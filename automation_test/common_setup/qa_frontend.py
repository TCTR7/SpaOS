"""Runner-owned frontend with isolated build output and deterministic cleanup."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import html
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from uuid import uuid4

import httpx

from .frontend_preflight import FrontendPreflightError, verify_frontend

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def stop_owned_process(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.wait(timeout=10)
    else:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def source_fingerprints():
    return {name: hashlib.sha256((FRONTEND / name).read_bytes()).hexdigest()
            if (FRONTEND / name).exists() else None
            for name in ("tsconfig.json", "next-env.d.ts")}


def check_sources_unchanged(before):
    if source_fingerprints() != before:
        raise RuntimeError("Frontend tsconfig/next-env changed during QA. Review the change; no automatic restore was attempted.")


def qa_environment(backend_url, frontend_url, run_id):
    return dict(os.environ, SPAOS_QA_MODE="1", SPAOS_QA_MANAGED="1",
                SPAOS_QA_RUN_ID=run_id, SPAOS_QA_BACKEND_URL=backend_url,
                BACKEND_URL=backend_url, BACKEND_INTERNAL_URL=backend_url,
                FRONTEND_URL=frontend_url, NEXT_PUBLIC_API_URL="/api/v1",
                NEXT_TELEMETRY_DISABLED="1", HEADLESS="true", SLOW_MO="0",
                PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", SPAOS_QA_NO_ARTIFACTS="1")


def write_qa_tsconfig(run_id):
    path = FRONTEND / ".qa" / ("tsconfig." + run_id + ".json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({
        "extends": "../tsconfig.json",
        "compilerOptions": {
            "baseUrl": "..",
            "tsBuildInfoFile": "../.next-qa/" + run_id + "/qa.tsbuildinfo",
        },
        "include": ["../next-env.d.ts", "../src/**/*.ts", "../src/**/*.tsx",
                    "../.next-qa/" + run_id + "/types/**/*.ts"],
        "exclude": ["../node_modules", "../.next", "../.qa"],
    }, indent=2), encoding="utf-8")


@contextmanager
def qa_frontend(backend_url, *, mode="production", port=3001, artifact_root=None):
    if mode not in {"dev", "production"}:
        raise ValueError("QA mode must be dev or production")
    if not 0 < port < 65536 or port == 3000:
        raise ValueError("QA frontend requires a valid port other than 3000")
    run_id = str(uuid4())
    frontend_url = "http://127.0.0.1:" + str(port)
    artifacts = (artifact_root or ROOT / "automation_test" / "artifacts" / "qa") / run_id
    env = qa_environment(backend_url, frontend_url, run_id)
    env["NODE_ENV"] = "production" if mode == "production" else "development"
    before = source_fingerprints()
    owned = []
    readers = []
    reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            reservation.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        reservation.bind(("127.0.0.1", port))
        write_qa_tsconfig(run_id)
        cli = ["node", str(FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next")]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        def launch(args):
            process = subprocess.Popen(cli + args, cwd=FRONTEND, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace",
                                       creationflags=flags)
            owned.append(process)
            def forward_console():
                for line in process.stdout:
                    print(line, end="", flush=True)
            reader = threading.Thread(target=forward_console, daemon=True)
            readers.append((reader, process))
            reader.start()
            return process
        if mode == "production":
            print("QA: building isolated production frontend", flush=True)
            build = launch(["build"])
            if build.wait(timeout=600) != 0:
                raise RuntimeError("QA frontend build failed; see console output")
            check_sources_unchanged(before)
        reservation.close()
        command = "start" if mode == "production" else "dev"
        process = launch([command, "--hostname", "127.0.0.1", "--port", str(port)])
        deadline = time.monotonic() + 180
        while True:
            if process.poll() is not None:
                raise RuntimeError("QA frontend exited before readiness; see console output")
            try:
                verify_frontend(frontend_url, run_id)
                break
            except FrontendPreflightError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("QA frontend not ready; see console output") from None
                time.sleep(0.25)
        check_sources_unchanged(before)
        print("QA: frontend verified at " + frontend_url, flush=True)
        yield dict(env=env, run_id=run_id, frontend_url=frontend_url, artifacts=artifacts)
    finally:
        reservation.close()
        try:
            for process in reversed(owned):
                stop_owned_process(process)
            for reader, process in readers:
                reader.join(timeout=5)
                process.stdout.close()
        finally:
            check_sources_unchanged(before)


def verify_api_isolation(backend_url, frontend_url, run_id):
    """Real HTTP without browser routing: prove rewrite and SSR use this QA DB."""
    slug = "qa-proof-" + run_id
    name = "QA Proof " + run_id[:8]
    phone = "09" + str(uuid4().int).zfill(8)[-8:]
    with httpx.Client(timeout=45, follow_redirects=False, trust_env=False) as client:
        created = client.post(backend_url + "/api/v1/auth/register-tenant", json={
            "tenant_name": name, "tenant_slug": slug, "admin_full_name": "QA Proof Admin",
            "phone_number": phone, "password": "QAProofOnly@2026",
        })
        created.raise_for_status()
        direct = client.get(backend_url + "/api/v1/public/tenants/" + slug)
        direct.raise_for_status()
        rewritten = client.get(frontend_url + "/api/v1/public/tenants/" + slug)
        rewritten.raise_for_status()
        if rewritten.json()["id"] != direct.json()["id"] or rewritten.json()["name"] != name:
            raise RuntimeError("Frontend API rewrite did not reach this QA database")
        page = client.get(frontend_url + "/" + slug)
        page.raise_for_status()
        expected_title = "<title>" + name + " — Đặt lịch Online | SpaOS</title>"
        if expected_title not in html.unescape(page.text):
            raise RuntimeError("Frontend SSR metadata did not reach this QA database")
    return dict(run_id=run_id, rewrite=True, ssr=True, proof_slug=slug)
