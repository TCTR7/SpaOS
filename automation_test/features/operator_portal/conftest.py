import subprocess
import time
import uuid
from pathlib import Path
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]

@pytest.fixture(scope="session")
def operator_qa_backend():
    suffix = uuid.uuid4().hex
    name, database = "spaos-op-qa-" + suffix, "spaos_e2e_" + suffix
    def command(args, check=True):
        return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True, encoding="utf-8", errors="replace")
    started = False
    try:
        result = command(["docker-compose", "run", "--rm", "--no-deps", "-d", "--name", name,
            "-p", "127.0.0.1::8000", "-e", "SPAOS_QA_DB="+database,
            "backend", "python", "-m", "scripts.operator_qa_server"])
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
            command(["docker", "stop", "-t", "2", name], check=False)
        command(["docker-compose", "exec", "-T", "backend", "python", "-m", "scripts.operator_qa_server", "--drop", database])

@pytest.fixture
def operator_ui(browser_instance, operator_qa_backend):
    contexts, errors = [], []
    def page_for():
        context = browser_instance.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        def forward(route):
            path = route.request.url.split("/api/v1", 1)[1]
            response = route.fetch(url=operator_qa_backend+"/api/v1"+path)
            route.fulfill(response=response)
        page.route("**/api/v1/**", forward)
        page.on("pageerror", lambda e: errors.append(str(e)))
        contexts.append(context)
        return page
    yield page_for, operator_qa_backend
    for context in contexts:
        for page in context.pages:
            # Closing a page cancels background requests; suppress only callbacks left during teardown.
            page.unroute_all(behavior="ignoreErrors")
        context.close()
    assert not errors
