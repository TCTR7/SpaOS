"""Run backend tests in a disposable database; never seed QA operators in the app database."""
import asyncio
import os
import re
import sys
import uuid
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def main():
    name = "spaos_qa_" + uuid.uuid4().hex
    if not re.fullmatch(r"spaos_qa_[a-f0-9]{32}", name):
        raise RuntimeError("Invalid temporary database name")
    admin = create_async_engine(settings.MIGRATION_DATABASE_URL, isolation_level="AUTOCOMMIT")
    created = False
    try:
        async with admin.connect() as db:
            await db.execute(text('CREATE DATABASE "' + name + '"'))
            created = True
        env = dict(os.environ)
        env["DATABASE_URL"] = make_url(settings.DATABASE_URL).set(database=name).render_as_string(hide_password=False)
        env["MIGRATION_DATABASE_URL"] = make_url(settings.MIGRATION_DATABASE_URL).set(database=name).render_as_string(hide_password=False)
        env["ENVIRONMENT"] = "test"
        # Never send real pushes with deployment secrets during QA. Tests opt in with mocks.
        env["VAPID_PUBLIC_KEY"], env["VAPID_PRIVATE_KEY"] = "", ""
        env["OPERATOR_PHONE"], env["OPERATOR_PASSWORD"] = "", ""
        cwd = str(Path(__file__).resolve().parents[1])
        for command in ([sys.executable, "-m", "alembic", "upgrade", "head"],
                        [sys.executable, "-m", "pytest", *(sys.argv[1:] or ["-q", "--tb=short"])]):
            process = await asyncio.create_subprocess_exec(*command, env=env, cwd=cwd)
            code = await process.wait()
            if code:
                return code
        return 0
    finally:
        if created:
            async with admin.connect() as db:
                await db.execute(text('DROP DATABASE "' + name + '" WITH (FORCE)'))
            print("Đã dọn database QA tạm; không thay database ứng dụng.")
        await admin.dispose()

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
