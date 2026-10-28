"""Usage from root: python -B -m automation_test.run_ui_qa -- <pytest args>."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from .common_setup.qa_backend import qa_backend
from .common_setup.qa_frontend import ROOT, qa_frontend, stop_owned_process, verify_api_isolation


TEST_ROOT = ROOT / "automation_test"


def pytest_command(arguments):
    # pytest resolves configured testpaths relative to its working directory.
    # Keep E2E discovery inside automation_test; preserve root-relative examples.
    selected=[]
    for argument in arguments:
        path,separator,node=argument.partition("::")
        if path.replace("\\","/").startswith("automation_test/"):
            argument=str(ROOT / path)+(separator+node if separator else "")
        selected.append(argument)
    return [sys.executable,"-B","-m","pytest","-c",str(TEST_ROOT / "pytest.ini"),
            "-p","no:cacheprovider",*selected]


def run(pytest_args, *, mode="production", port=3001):
    code = 1
    try:
        with qa_backend() as backend_url:
            with qa_frontend(backend_url, mode=mode, port=port) as qa:
                verify_api_isolation(backend_url, qa["frontend_url"], qa["run_id"])
                print("QA: rewrite + SSR isolation verified; console only; run " + qa["run_id"], flush=True)
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                process = subprocess.Popen(
                    pytest_command(pytest_args),
                    cwd=TEST_ROOT, env=qa["env"], creationflags=flags,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                try:
                    for line in process.stdout:
                        print(line, end="", flush=True)
                    code = process.wait()
                finally:
                    stop_owned_process(process)
                    process.stdout.close()
        return code
    except KeyboardInterrupt:
        print("QA interrupted; owned resources cleaned up.", file=sys.stderr)
        return 130
    except Exception as error:
        print("QA failed: " + str(error), file=sys.stderr)
        return code if code != 0 else 1


def main():
    # Preserve Vietnamese diagnostics on Windows consoles without writing logs.
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
    return run(tests or ["-q", "--tb=short"],
               mode=args.mode, port=args.port)


if __name__ == "__main__":
    raise SystemExit(main())
