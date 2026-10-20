"""Disposable API for operator E2E only. Never seeds the application database."""
import asyncio
import os
import re
import subprocess
import sys
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def database(name, create):
    if not re.fullmatch(r"spaos_e2e_[a-f0-9]{32}", name):
        raise ValueError("Only generated E2E database names are accepted")
    engine = create_async_engine(settings.MIGRATION_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as db:
            await db.execute(text(('CREATE DATABASE "'+name+'"') if create else ('DROP DATABASE IF EXISTS "'+name+'" WITH (FORCE)')))
    finally:
        await engine.dispose()

def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--drop":
        asyncio.run(database(sys.argv[2], False))
        return
    name = os.environ["SPAOS_QA_DB"]
    asyncio.run(database(name, True))
    env = dict(os.environ)
    env["DATABASE_URL"] = make_url(settings.DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    env["MIGRATION_DATABASE_URL"] = make_url(settings.MIGRATION_DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    env.update(ENVIRONMENT="test", OPERATOR_PHONE="0998888777", OPERATOR_NAME="QA Operator",
               OPERATOR_PASSWORD="OperatorOnlyForQa@2026")
    for args in (["alembic", "upgrade", "head"], [sys.executable, "-m", "app.seed"]):
        subprocess.run(args, env=env, check=True)
    if os.environ.get("SPAOS_QA_SEED_DEMO") == "1":
        subprocess.run([sys.executable, "-m", "app.seed_demo"], env=env, check=True)
    raise SystemExit(subprocess.call([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"], env=env))

if __name__ == "__main__":
    main()
