import uuid
from typing import Any, Iterable

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_tenant_context


async def commit_and_refresh(db: AsyncSession, tenant_id: uuid.UUID, *objs: Any) -> None:
    """Commit rồi gán lại tenant context (biến RLS chỉ sống trong 1 transaction) trước khi refresh."""
    await db.commit()
    await set_tenant_context(db, tenant_id)
    for obj in objs:
        await db.refresh(obj)


def apply_patch(obj: Any, body: BaseModel, nullable: Iterable[str] = ()) -> None:
    """Áp dụng các field client thực sự gửi lên (exclude_unset). Field NOT NULL không được gửi null."""
    nullable_set = set(nullable)
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is None and key not in nullable_set:
            raise HTTPException(
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                detail=f"Trường '{key}' không được để null",
            )
        setattr(obj, key, value)
