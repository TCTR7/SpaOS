"""Usage from root: python -B -m automation_test.run_ui_qa -- <pytest args>."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from .common_setup.qa_backend import qa_backend
from .common_setup.qa_frontend import ROOT, qa_frontend, stop_owned_process, verify_api_isolation


def run(pytest_args, *, mode="production", port=3001):
    code = 1
    try:
        with qa_backend() as backend_url:
            with qa_frontend(backend_url, mode=mode, port=port) as qa:
                proof = verify_api_isolation(backend_url, qa["frontend_url"], qa["run_id"])
                (qa["artifacts"] / "isolation.json").write_text(
                    json.dumps(proof, indent=2), encoding="utf-8")
                print("QA: rewrite + SSR isolation verified; running pytest", flush=True)
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                test_log = qa["artifacts"] / "pytest.log"
                with test_log.open("w", encoding="utf-8") as output:
                    process = subprocess.Popen(
                        [sys.executable, "-B", "-m", "pytest"] + list(pytest_args),
                        cwd=ROOT, env=qa["env"], creationflags=flags,
                        stdout=output, stderr=subprocess.STDOUT,
                    )
                    try:
                        code = process.wait()
                    finally:
                        stop_owned_process(process)
                print("\n".join(test_log.read_text(encoding="utf-8", errors="replace").splitlines()[-45:]), flush=True)
                print("QA test log: " + str(test_log), flush=True)
        return code
    except KeyboardInterrupt:
        print("QA interrupted; owned resources cleaned up.", file=sys.stderr)
        return 130
    except Exception as error:
        print("QA failed: " + str(error), file=sys.stderr)
        return code if code != 0 else 1


def main():
    # Preserve Vietnamese diagnostics on Windows consoles as well as log files.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("production", "dev"), default="production")
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    tests = args.pytest_args
    if tests[:1] == ["--"]:
        tests = tests[1:]
    return run(tests or ["automation_test/features", "-q", "--tb=short"],
               mode=args.mode, port=args.port)


if __name__ == "__main__":
    raise SystemExit(main())
