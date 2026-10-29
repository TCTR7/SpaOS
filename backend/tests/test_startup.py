from types import SimpleNamespace
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager
import pytest
from sqlalchemy import text
from app.core import schema
from app.core.database import engine
from scripts import start_service


@pytest.mark.asyncio
async def test_migrated_runtime_database_passes_schema_guard():
    try:
        await schema.verify_database_schema()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_outdated_database_fails_without_modifying_schema(monkeypatch):
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            await connection.execute(text("UPDATE alembic_version SET version_num='0008_manual_booking_batches'"))
            @asynccontextmanager
            async def connected():
                yield connection
            monkeypatch.setattr(schema, "engine", SimpleNamespace(connect=connected))
            with pytest.raises(RuntimeError, match="alembic upgrade head"):
                await schema.verify_database_schema()
            await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_stamp_alone_does_not_hide_missing_contact_columns(monkeypatch):
    original = schema.inspect
    def inspect_without_contact(connection):
        actual = original(connection)
        return SimpleNamespace(has_table=actual.has_table,
            get_columns=lambda name: [c for c in actual.get_columns(name) if c["name"] != "address"])
    monkeypatch.setattr(schema, "inspect", inspect_without_contact)
    try:
        with pytest.raises(RuntimeError, match="Do not use alembic stamp"):
            await schema.verify_database_schema()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_no_worker_starts_before_schema_is_ready(monkeypatch):
    from app.main import app
    from app.services import notification_queue
    monkeypatch.setattr(schema, "prepare_database_schema", AsyncMock(side_effect=RuntimeError("schema not ready")))
    worker = AsyncMock()
    monkeypatch.setattr(notification_queue, "worker", worker)
    with pytest.raises(RuntimeError, match="schema not ready"):
        async with app.router.lifespan_context(app):
            pass
    worker.assert_not_called()


@pytest.mark.parametrize("failed_stage", [0, 1, 2])
def test_start_does_not_open_server_after_failed_preparation(monkeypatch, failed_stage):
    calls = []
    monkeypatch.setattr(start_service.os, "chdir", lambda _: None)
    monkeypatch.setattr(start_service.subprocess, "run", lambda args, **kwargs:
        calls.append(args) or SimpleNamespace(returncode=7 if len(calls) == failed_stage + 1 else 0))
    monkeypatch.setattr(start_service.os, "execv", lambda *args: pytest.fail("Server must not start"))
    with pytest.raises(SystemExit) as failure:
        start_service.start()
    assert failure.value.code == 7
    assert len(calls) == failed_stage + 1


def test_start_uses_render_port_after_successful_preparation(monkeypatch):
    calls, executions = [], []
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setattr(start_service.os, "chdir", lambda _: None)
    monkeypatch.setattr(start_service.subprocess, "run", lambda args, **kwargs:
        calls.append(args) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(start_service.os, "execv", lambda executable, args: executions.append(args))
    start_service.start()
    assert calls[0][-1] == "scripts.check_database"
    assert calls[1][-3:] == ["alembic", "upgrade", "head"]
    assert calls[2][-1] == "app.seed"
    assert executions[0][-2:] == ["--port", "10000"]
    assert "--reload" not in executions[0]


@pytest.mark.asyncio
async def test_current_revision_skips_upgrade_but_keeps_guard(monkeypatch):
    from alembic.script import ScriptDirectory
    head=set(ScriptDirectory.from_config(schema.migration_config()).get_heads())
    upgrade,verify=AsyncMock(),AsyncMock()
    monkeypatch.setattr(schema,"database_revisions",AsyncMock(return_value=head))
    monkeypatch.setattr(schema,"upgrade_database_schema",upgrade)
    monkeypatch.setattr(schema,"verify_database_schema",verify)
    await schema.prepare_database_schema()
    upgrade.assert_not_awaited()
    verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_pending_revision_upgrades_before_guard(monkeypatch):
    stages=[]
    async def upgrade():stages.append("upgrade")
    async def verify():stages.append("verify")
    monkeypatch.setattr(schema,"database_revisions",AsyncMock(return_value={"0011_staff_profile"}))
    monkeypatch.setattr(schema,"upgrade_database_schema",upgrade)
    monkeypatch.setattr(schema,"verify_database_schema",verify)
    await schema.prepare_database_schema()
    assert stages==["upgrade","verify"]


@pytest.mark.asyncio
async def test_failed_automatic_migration_stops_api_without_leaking_child_output(monkeypatch):
    from app.main import app
    from app.services import notification_queue
    marker="private-driver-details-not-for-startup-log"
    process=SimpleNamespace(returncode=7,communicate=AsyncMock(return_value=(marker.encode(),marker.encode())))
    launch=AsyncMock(return_value=process)
    monkeypatch.setattr(schema,"database_revisions",AsyncMock(return_value=set()))
    monkeypatch.setattr(schema.asyncio,"create_subprocess_exec",launch)
    worker,verify=AsyncMock(),AsyncMock()
    monkeypatch.setattr(notification_queue,"worker",worker)
    monkeypatch.setattr(schema,"verify_database_schema",verify)
    with pytest.raises(RuntimeError,match="Automatic database migration failed") as failure:
        async with app.router.lifespan_context(app):pass
    assert marker not in str(failure.value)
    worker.assert_not_called()
    verify.assert_not_awaited()
    assert launch.call_args.args[1:]==("-m","alembic","upgrade","head")


@pytest.mark.parametrize("legacy_revision",[None,"0011_staff_profile"])
@pytest.mark.asyncio
async def test_uvicorn_lifespan_prepares_disposable_database_concurrently(monkeypatch,legacy_revision):
    import asyncio,os,sys,uuid
    from pathlib import Path
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.core.config import settings
    from app.main import app
    name="spaos_qa_"+uuid.uuid4().hex
    owner_url=make_url(settings.MIGRATION_DATABASE_URL)
    runtime_url=make_url(settings.DATABASE_URL).set(database=name)
    owner_target=owner_url.set(database=name).render_as_string(hide_password=False)
    admin=create_async_engine(owner_url,isolation_level="AUTOCOMMIT")
    runtime=None
    created=False
    try:
        async with admin.connect() as db:
            await db.execute(text('CREATE DATABASE "'+name+'"'))
            created=True
        if legacy_revision:
            env=dict(os.environ,MIGRATION_DATABASE_URL=owner_target,DATABASE_URL=runtime_url.render_as_string(hide_password=False))
            process=await asyncio.create_subprocess_exec(sys.executable,"-m","alembic","upgrade",legacy_revision,
                cwd=Path(__file__).resolve().parents[1],env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            await process.communicate()
            assert process.returncode==0,"Disposable legacy setup failed"
        runtime=create_async_engine(runtime_url)
        monkeypatch.setattr(schema,"engine",runtime)
        monkeypatch.setattr(settings,"MIGRATION_DATABASE_URL",owner_target)
        monkeypatch.setattr(settings,"DATABASE_URL",runtime_url.render_as_string(hide_password=False))
        async def boot():
            async with app.router.lifespan_context(app):pass
        await asyncio.gather(boot(),boot())
        await schema.verify_database_schema()
        with monkeypatch.context() as checked:
            upgrade=AsyncMock(side_effect=AssertionError("Current schema must not migrate again"))
            checked.setattr(schema,"upgrade_database_schema",upgrade)
            await boot()
            upgrade.assert_not_awaited()
        # Schema automation never guesses ownership for legacy business rows.
        owner=create_async_engine(owner_target)
        try:
            async with owner.begin() as db:
                await db.execute(text("INSERT INTO tenants(slug,name) VALUES ('unmapped-startup','Legacy QA')"))
            monkeypatch.setattr(settings,"ENVIRONMENT","production")
            with pytest.raises(RuntimeError,match="ownership mapping is incomplete"):
                await schema.prepare_database_schema()
        finally:
            await owner.dispose()
    finally:
        if runtime is not None:await runtime.dispose()
        if created:
            async with admin.connect() as db:
                await db.execute(text('DROP DATABASE "'+name+'" WITH (FORCE)'))
        await admin.dispose()
