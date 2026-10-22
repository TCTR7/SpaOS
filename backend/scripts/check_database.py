"""Read-only startup diagnostics; never print URLs or underlying exceptions."""
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def check_connection(name: str, url: str) -> bool:
    engine = None
    try:
        engine = create_async_engine(url, connect_args={"timeout": 15})
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as error:
        current, seen = error, set()
        authentication_failed = False
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            authentication_failed |= getattr(current, "sqlstate", None) == "28P01"
            current = current.__cause__ or current.__context__
        if authentication_failed:
            print(f"{name}: authentication rejected (28P01). Verify effective environment "
                  "value, username/password, endpoint and password URL encoding. "
                  "This does not prove the password itself was changed.", flush=True)
        else:
            print(f"{name}: connection failed. Check URL format, host, port, database, "
                  "SSL and network access. Connection details suppressed.", flush=True)
        return False
    finally:
        if engine is not None:
            await engine.dispose()
    print(f"{name}: connection OK", flush=True)
    return True


async def check_connections() -> bool:
    results = []
    for name in ("MIGRATION_DATABASE_URL", "DATABASE_URL"):
        source = "environment" if any(key.upper() == name for key in os.environ) else "dotenv/default"
        print(f"{name}: configuration source = {source}", flush=True)
        results.append(await check_connection(name, getattr(settings, name)))
    return all(results)


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(check_connections()) else 1)
