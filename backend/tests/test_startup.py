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
    monkeypatch.setattr(schema, "verify_database_schema", AsyncMock(side_effect=RuntimeError("schema not ready")))
    worker = AsyncMock()
    monkeypatch.setattr(notification_queue, "worker", worker)
    with pytest.raises(RuntimeError, match="schema not ready"):
        async with app.router.lifespan_context(app):
            pass
    worker.assert_not_called()


@pytest.mark.parametrize("failed_stage", [0, 1])
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
    assert calls[0][-3:] == ["alembic", "upgrade", "head"]
    assert calls[1][-1] == "app.seed"
    assert executions[0][-2:] == ["--port", "10000"]
    assert "--reload" not in executions[0]
