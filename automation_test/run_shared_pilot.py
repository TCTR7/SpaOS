"""Three-spa HTTP pilot and backup/restore, exclusively on runner-owned QA data."""
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from .common_setup.qa_backend import qa_backend, ROOT


async def measure(url, container, database):
    # Import the existing bounded workload without requiring deployment secrets.
    sys.path.insert(0, str(ROOT / "backend"))
    from scripts.release_load_check import run
    args=SimpleNamespace(base_url=url, reads=200, max_p95_ms=5000)
    results=await asyncio.gather(*(run(args,emit=False,enforce_budget=False) for _ in range(3)))
    print(json.dumps({"scenario":"3 spas x 10 staff, 60 contending bookings, 600 reads",
        "spas":results,"local_budget_ms":5000},ensure_ascii=False,indent=2),flush=True)
    stats=subprocess.run(["docker","stats","--no-stream","--format","{{json .}}",container],
        capture_output=True,text=True,check=True)
    print("QA backend resource snapshot after workload: "+stats.stdout.strip(),flush=True)
    # Identifiers are created by the QA runner, never entered or read from .env.
    size=subprocess.run(["docker-compose","exec","-T","-e","POSTGRES_DB="+database,"db","sh","-c",
        'exec psql -X -q -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_database_size(current_database())"'],
        capture_output=True,text=True,check=True)
    print("QA database bytes: "+size.stdout.strip(),flush=True)
    return all(r["within_budget"] for r in results)


def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8",errors="replace")
    metadata={}
    with qa_backend(metadata=metadata) as url:
        within_budget=asyncio.run(measure(url,metadata["container"],metadata["database"]))
        # Dump is synthetic QA data. Retain it only for the duration of the rehearsal.
        with tempfile.TemporaryDirectory(prefix="spaos-qa-recovery-") as temporary:
            result=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/db_recovery_check.py"),
                "--qa-database",metadata["database"],"--output",str(Path(temporary)/"qa.dump")],cwd=ROOT)
            if result.returncode:raise RuntimeError("QA backup/restore rehearsal failed")
        if not within_budget:raise RuntimeError("Pilot p95 exceeded the 5000 ms local budget; metrics above retained in console")


if __name__=="__main__":main()
