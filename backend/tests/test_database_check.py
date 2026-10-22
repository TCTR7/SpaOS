from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from asyncpg import InvalidPasswordError

from scripts import check_database


@pytest.mark.asyncio
async def test_authentication_failure_is_redacted(monkeypatch, capsys):
    secret = "private-password-do-not-log"
    engine = SimpleNamespace(dispose=AsyncMock())

    def connect():
        try:
            raise InvalidPasswordError(secret)
        except InvalidPasswordError as error:
            raise RuntimeError(secret) from error

    engine.connect = connect
    monkeypatch.setattr(check_database, "create_async_engine", lambda *a, **kw: engine)
    assert not await check_database.check_connection("MIGRATION_DATABASE_URL", secret)
    output = capsys.readouterr().out
    assert "MIGRATION_DATABASE_URL: authentication rejected (28P01)" in output
    assert secret not in output
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_both_connections_checked_after_failure(monkeypatch, capsys):
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "secret-value")
    check = AsyncMock(side_effect=[False, True])
    monkeypatch.setattr(check_database, "check_connection", check)
    assert not await check_database.check_connections()
    assert [call.args[0] for call in check.await_args_list] == ["MIGRATION_DATABASE_URL", "DATABASE_URL"]
    output = capsys.readouterr().out
    assert "MIGRATION_DATABASE_URL: configuration source = environment" in output
    assert "secret-value" not in output


@pytest.mark.asyncio
async def test_real_qa_connections():
    assert await check_database.check_connections()
