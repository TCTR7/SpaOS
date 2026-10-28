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
            "then restart. On Render use Start Command: python -m scripts.start_service. "
            "Do not use alembic stamp as a substitute for migrations."
        )
    from app.core.config import settings
    if settings.ENVIRONMENT == "production":
        from sqlalchemy import text
        async with engine.connect() as connection:
            missing=(await connection.execute(text("SELECT id FROM tenants WHERE spa_id IS NULL LIMIT 1"))).first()
        if missing:
            raise RuntimeError("Shared spa ownership mapping is incomplete. Run reviewed shared_spa_migration inventory/mapping during maintenance before serving production.")
