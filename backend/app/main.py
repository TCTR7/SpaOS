import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

@asynccontextmanager
async def lifespan(app):
    from app.services.notification_queue import worker
    task = asyncio.create_task(worker()) if settings.ENVIRONMENT != "test" else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError): await task

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
