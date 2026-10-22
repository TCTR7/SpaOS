"""Fail before serving requests if code and runtime database disagree."""
from pathlib import Path
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from app.core.database import engine


def migration_config():
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    return config


async def verify_database_schema():
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())

    def inspect_schema(connection):
        current = set(MigrationContext.configure(connection).get_current_heads())
        inspector = inspect(connection)
        # Check the columns in the incident too: stamp head alone never applies DDL.
        columns = {c["name"] for c in inspector.get_columns("tenants")} if inspector.has_table("tenants") else set()
        return current, {"address", "contact_phone"}.issubset(columns)

    async with engine.connect() as connection:
        current, contact_columns = await connection.run_sync(inspect_schema)
    if current != expected or not contact_columns:
        raise RuntimeError(
            "Database schema is not ready for this backend. "
            f"Expected revision(s): {', '.join(sorted(expected))}; "
            f"found: {', '.join(sorted(current)) or 'none'}. "
            "From backend/, run 'alembic upgrade head' using MIGRATION_DATABASE_URL, "
            "then restart. On Render use Start Command: python -m scripts.start_service. "
            "Do not use alembic stamp as a substitute for migrations."
        )
