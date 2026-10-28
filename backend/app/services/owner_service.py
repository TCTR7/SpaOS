"""Operate on a verified provision; keep every business query tenant scoped."""
from fastapi import HTTPException
from sqlalchemy import select
from app.core.database import set_tenant_context
from app.models.models import OwnerProvision, BranchMembership, LoginAccount, User, UserRole, Tenant
from app.services.branch_service import account_context


async def resolve_owner(db, operator_id, provision_id):
    record = (await db.execute(select(OwnerProvision).where(OwnerProvision.operator_id == operator_id,
        OwnerProvision.id == provision_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Không tìm thấy tài khoản đã cấp")
    await set_tenant_context(db, record.tenant_id)
    link = (await db.execute(select(BranchMembership).where(BranchMembership.tenant_id == record.tenant_id,
        BranchMembership.user_id == record.owner_user_id, BranchMembership.is_owner.is_(True),
        BranchMembership.is_active.is_(True)))).scalar_one_or_none()
    if not link:
        raise HTTPException(409, "Quyền chủ spa không còn hiệu lực; cần đối chiếu tài khoản")
    account, rows = await owner_memberships(db, link.account_id)
    return record, account, rows


async def owner_memberships(db, account_id):
    await account_context(db, account_id)
    account = (await db.execute(select(LoginAccount).where(LoginAccount.id == account_id)
        .execution_options(populate_existing=True).with_for_update())).scalar_one_or_none()
    if not account or not account.is_active:
        raise HTTPException(409, "Tài khoản đang ngưng hoạt động")
    links = list((await db.execute(select(BranchMembership).where(BranchMembership.account_id == account_id)
        .order_by(BranchMembership.tenant_id))).scalars())
    if not links or any(not link.is_owner for link in links):
        raise HTTPException(409, "Cần đối chiếu quyền chủ spa ở các chi nhánh")
    rows = []
    for link in links:
        await set_tenant_context(db, link.tenant_id)
        user = (await db.execute(select(User).where(User.tenant_id == link.tenant_id, User.id == link.user_id,
            User.role == UserRole.ADMIN).execution_options(populate_existing=True).with_for_update())).scalar_one_or_none()
        tenant = (await db.execute(select(Tenant).where(Tenant.id == link.tenant_id))).scalar_one_or_none()
        if not user or not tenant or not account.spa_id or tenant.spa_id != account.spa_id:
            raise HTTPException(409, "Hồ sơ chi nhánh cần được đối chiếu")
        rows.append((link, user, tenant))
    return account, rows


async def owner_view(db, operator_id, provision_id):
    record, account, rows = await resolve_owner(db, operator_id, provision_id)
    primary = next(user for _, user, _ in rows if user.id == record.owner_user_id)
    from app.services.spa_service import tenant_spa, brand_view
    spa = await tenant_spa(db, record.tenant_id)
    return {"id": record.id, "spa": brand_view(spa), "full_name": primary.full_name, "phone_number": account.phone_number,
        "branches": [{"id": t.id, "name": t.name, "slug": t.slug, "logo_url": t.logo_url,
            "address": t.address, "active": link.is_active and user.is_active and t.status == "ACTIVE"}
            for link, user, t in rows]}
