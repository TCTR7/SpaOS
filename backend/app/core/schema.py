"""Upgrade pending migrations, then verify schema before serving requests."""
import asyncio
import logging
import os
import sys
from pathlib import Path
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from app.core.database import engine
from app.core.config import settings

logger = logging.getLogger(__name__)


def migration_config():
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    return config


async def database_revisions():
    async with engine.connect() as connection:
        return set(await connection.run_sync(
            lambda sync: MigrationContext.configure(sync).get_current_heads()))


async def upgrade_database_schema():
    # Separate process: Alembic owns its event loop and privileged connection.
    # env.py serializes migrations with a PostgreSQL advisory lock, including
    # when several Uvicorn workers discover the same old revision at startup.
    environment = dict(os.environ, DATABASE_URL=settings.DATABASE_URL,
                       MIGRATION_DATABASE_URL=settings.MIGRATION_DATABASE_URL,
                       ENVIRONMENT=settings.ENVIRONMENT)
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "alembic", "upgrade", "head",
        cwd=Path(__file__).resolve().parents[2], env=environment,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        await process.communicate()
    except asyncio.CancelledError:
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            await process.communicate()
        raise
    if process.returncode:
        # SQL/driver exceptions can contain connection details or bound values.
        raise RuntimeError(
            f"Automatic database migration failed (exit code {process.returncode}). "
            "API startup stopped. Check MIGRATION_DATABASE_URL and run "
            "'python -m scripts.check_database' / 'python -m alembic upgrade head' "
            "from backend/ in a private deployment console.")


async def prepare_database_schema():
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
    current = await database_revisions()
    if current != expected:
        logger.info("Pending database migrations: %s -> %s",
                    ", ".join(sorted(current)) or "empty", ", ".join(sorted(expected)))
        await upgrade_database_schema()
    else:
        logger.info("Database revision is current; skipping migrations")
    # Keep structural and ownership guards. A stamped head or unmapped legacy
    # branches must not silently become ready just because Alembic exited zero.
    await verify_database_schema()


async def verify_database_schema():
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())

    def inspect_schema(connection):
        current = set(MigrationContext.configure(connection).get_current_heads())
        inspector = inspect(connection)
        # Check the columns in the incident too: stamp head alone never applies DDL.
        columns = {c["name"] for c in inspector.get_columns("tenants")} if inspector.has_table("tenants") else set()
        required={"spas":{"id","slug","name","logo_data","cover_data","branch_limit","staff_limit"},
            "login_accounts":{"spa_id","default_branch_id"},
            "staff_assignments":{"spa_id","account_id","tenant_id","day","weekday","effective_from","start_time","end_time"}}
        shared = all(inspector.has_table(table) and fields.issubset({c["name"] for c in inspector.get_columns(table)})
            for table,fields in required.items())
        return current, {"address", "contact_phone", "spa_id"}.issubset(columns) and shared

    async with engine.connect() as connection:
        current, contact_columns = await connection.run_sync(inspect_schema)
    if current != expected or not contact_columns:
        raise RuntimeError(
            "Database schema is not ready for this backend. "
            f"Expected revision(s): {', '.join(sorted(expected))}; "
            f"found: {', '.join(sorted(current)) or 'none'}. "
            "From backend/, run 'alembic upgrade head' using MIGRATION_DATABASE_URL, "
            "then restart. Uvicorn startup applies pending migrations automatically. "
            "Do not use alembic stamp as a substitute for migrations."
        )
    if settings.ENVIRONMENT == "production":
        from sqlalchemy import text
        async with engine.connect() as connection:
            missing=(await connection.execute(text("SELECT id FROM tenants WHERE spa_id IS NULL LIMIT 1"))).first()
        if missing:
            raise RuntimeError("Shared spa ownership mapping is incomplete. Run reviewed shared_spa_migration inventory/mapping during maintenance before serving production.")
