"""Verified brand boundary, public metadata and serialized plan checks."""
import re
import unicodedata
import uuid
from fastapi import HTTPException
from sqlalchemy import select, text, func
from app.models.models import Spa, Tenant, User, UserRole, BranchMembership
from app.core.database import set_tenant_context


async def spa_context(db, spa_id):
    await db.execute(text("SELECT set_config('app.current_spa_id',:id,true)"), {"id": str(spa_id) if spa_id else ""})


async def new_spa(db, name, *, slug=None, operator_id=None, theme_color=None):
    ident = uuid.uuid4()
    stem = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode().lower()).strip("-")[:65] or "spa"
    await spa_context(db, ident)
    row = Spa(id=ident, name=name.strip(), slug=slug or stem + "-" + ident.hex[:8],
              operator_id=operator_id, theme_color=theme_color or "#be185d")
    db.add(row)
    await db.flush()
    return row


async def tenant_spa(db, tenant_id, *, lock=False):
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant or not tenant.spa_id:
        raise HTTPException(409, "Chi nhánh chưa được đối chiếu chủ spa; liên hệ operator")
    await spa_context(db, tenant.spa_id)
    stmt = select(Spa).where(Spa.id == tenant.spa_id, Spa.status == "ACTIVE")
    if lock:
        stmt = stmt.with_for_update()
    spa = (await db.execute(stmt)).scalar_one_or_none()
    if not spa:
        raise HTTPException(403, "Spa đã ngưng hoạt động")
    return spa


async def public_spa(db, slug, *, image=None):
    await db.execute(text("SELECT set_config('app.public_spa_slug',:slug,true)"), {"slug": slug})
    stmt = select(Spa).where(Spa.slug == slug, Spa.status == "ACTIVE")
    if image in ("logo", "cover"):
        from sqlalchemy.orm import undefer
        stmt = stmt.options(undefer(Spa.logo_data if image == "logo" else Spa.cover_data))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Không tìm thấy spa")
    return row


def brand_view(spa):
    return {key: getattr(spa, key) for key in ("id", "slug", "name", "theme_color", "logo_url", "cover_url", "contact_phone")}


async def check_branch_limit(db, spa):
    count = (await db.execute(select(func.count()).select_from(Tenant).where(Tenant.spa_id == spa.id, Tenant.status == "ACTIVE"))).scalar_one()
    if count >= spa.branch_limit:
        raise HTTPException(409, "Đã đạt giới hạn chi nhánh của gói. Liên hệ nâng gói.")


async def staff_accounts(db, spa):
    result = set()
    tids = (await db.execute(select(Tenant.id).where(Tenant.spa_id == spa.id))).scalars().all()
    for tid in sorted(tids, key=str):
        await set_tenant_context(db, tid)
        result.update((await db.execute(select(BranchMembership.account_id).join(User,
            (User.id == BranchMembership.user_id) & (User.tenant_id == tid)).where(
                BranchMembership.tenant_id == tid, BranchMembership.is_active.is_(True),
                User.role == UserRole.STAFF, User.is_active.is_(True)))).scalars().all())
    return result


async def check_staff_limit(db, tenant_id, account_id=None):
    spa = await tenant_spa(db, tenant_id, lock=True)
    accounts = await staff_accounts(db, spa)
    await set_tenant_context(db, tenant_id)
    if account_id not in accounts and len(accounts) >= spa.staff_limit:
        raise HTTPException(409, "Đã đạt giới hạn nhân viên của gói. Liên hệ nâng gói.")
