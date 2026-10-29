import base64
import binascii
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from app.api.deps import get_current_user, get_tenant_db
from app.core.database import get_db, set_tenant_context
from app.models.models import Tenant, UserRole
from app.schemas.auth import _check_phone
from app.schemas.branding import color
from app.services.branch_service import account_for
from app.services.spa_service import public_spa, tenant_spa, brand_view, staff_accounts

router = APIRouter(prefix="/spas", tags=["spas"])


class SpaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    theme_color: str
    logo_data: str | None = Field(default=None, max_length=3000000)
    cover_data: str | None = Field(default=None, max_length=3000000)
    cover_url: str | None = Field(default=None, max_length=500)
    contact_phone: str | None = None
    _color = field_validator("theme_color")(color)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Nhập tên spa")
        return value.strip()

    @field_validator("cover_url")
    @classmethod
    def local_asset(cls, value):
        if value and (not value.startswith("/") or value.startswith("//") or "\\" in value):
            raise ValueError("Ảnh phải nằm trên cùng hệ thống")
        return value

    @field_validator("contact_phone")
    @classmethod
    def phone(cls, value):
        return _check_phone(value) if value else None


@router.get("/public/{slug}")
async def public(slug: str, response: Response, db=Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    spa = await public_spa(db, slug)
    branches = (await db.execute(select(Tenant).where(Tenant.spa_id == spa.id, Tenant.status == "ACTIVE").order_by(Tenant.name, Tenant.id))).scalars().all()
    return {**brand_view(spa), "branches": [{"id": t.id, "slug": t.slug, "name": t.name,
        "address": t.address, "contact_phone": t.contact_phone} for t in branches]}


@router.get("/public/{slug}/logo")
async def logo(slug: str, db=Depends(get_db)):
    spa = await public_spa(db, slug, image="logo")
    if not spa.logo_data:
        raise HTTPException(404, "Chưa có logo")
    media = "image/png" if spa.logo_data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return Response(spa.logo_data, media_type=media, headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"})


@router.get("/public/{slug}/cover")
async def cover(slug: str, db=Depends(get_db)):
    spa = await public_spa(db, slug, image="cover")
    if not spa.cover_data:
        raise HTTPException(404, "Chưa có ảnh bìa")
    media = "image/png" if spa.cover_data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return Response(spa.cover_data, media_type=media, headers={"Cache-Control":"no-cache","X-Content-Type-Options":"nosniff"})


def apply_images(spa, logo, cover):
    from app.api.v1.experience import validate_image_payload
    for kind, payload in (("logo",logo),("cover",cover)):
        if payload is None:
            continue
        try:
            image = base64.b64decode(payload, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, "Ảnh không hợp lệ")
        validate_image_payload(image)
        setattr(spa, kind+"_data", image)
        setattr(spa, kind+"_url", f"/api/v1/spas/public/{spa.slug}/{kind}?v={uuid.uuid4().hex}")


@router.get("/me")
async def me(actor=Depends(get_current_user), db=Depends(get_tenant_db)):
    account, link = await account_for(db, actor)
    spa = await tenant_spa(db, actor.tenant_id)
    view = brand_view(spa)
    view["is_owner"] = link.is_owner and actor.role == UserRole.ADMIN
    if view["is_owner"]:
        staff = await staff_accounts(db, spa)
        count = len((await db.execute(select(Tenant.id).where(Tenant.spa_id == spa.id, Tenant.status == "ACTIVE"))).all())
        view["plan"] = {"price_usd": 10, "branch_limit": spa.branch_limit, "staff_limit": spa.staff_limit,
                        "branches": count, "staff": len(staff)}
    await set_tenant_context(db, actor.tenant_id)
    return view


@router.patch("/me")
async def update(body: SpaUpdate, actor=Depends(get_current_user), db=Depends(get_tenant_db)):
    _, owner = await account_for(db, actor)
    if actor.role != UserRole.ADMIN or not owner.is_owner:
        raise HTTPException(403, "Chỉ chủ spa được sửa nhận diện")
    spa = await tenant_spa(db, actor.tenant_id, lock=True)
    spa.name, spa.theme_color = body.name, body.theme_color
    for field in ("cover_url", "contact_phone"):
        if field in body.model_fields_set:
            setattr(spa,field,getattr(body,field))
    apply_images(spa, body.logo_data, body.cover_data)
    from app.services.audit_service import audit
    audit(db, actor.tenant_id, actor, "SPA_BRANDING_UPDATED", "spa", spa.id, {"fields": ["name", "theme_color", "logo", "cover", "contact_phone"]})
    result = brand_view(spa)
    await db.commit()
    return result
