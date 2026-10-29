"""Management identity registry. Never use these contexts for business queries."""
import uuid
from fastapi import HTTPException
from sqlalchemy import select, text
from app.models.models import LoginAccount, BranchMembership, User, UserRole, Tenant
from app.core.database import set_tenant_context
from app.core.security import verify_password

async def account_context(db, account_id):
    await db.execute(text("SELECT set_config('app.current_account_id', :value, true)"), {"value": str(account_id)})

async def phone_context(db, phone):
    await db.execute(text("SELECT set_config('app.login_phone', :value, true)"), {"value": phone})

async def membership_for(db, user):
    return (await db.execute(select(BranchMembership).where(
        BranchMembership.tenant_id == user.tenant_id, BranchMembership.user_id == user.id))).scalar_one_or_none()

async def provision_account(db, user, *, owner=False):
    existing = await membership_for(db, user)
    if existing:
        return existing
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                     {"key": "account-phone:" + user.phone_number})
    await phone_context(db, user.phone_number)
    old = (await db.execute(select(LoginAccount).where(LoginAccount.phone_number == user.phone_number))).scalar_one_or_none()
    if old:
        raise HTTPException(409, "Số điện thoại đã có tài khoản chung. Dùng chức năng cấp quyền chi nhánh, không tạo tài khoản trùng.")
    from app.services.spa_service import tenant_spa
    spa = await tenant_spa(db, user.tenant_id)
    account = LoginAccount(phone_number=user.phone_number, password_hash=user.password_hash, spa_id=spa.id, default_branch_id=user.tenant_id)
    db.add(account)
    await db.flush()
    link = BranchMembership(tenant_id=user.tenant_id, user_id=user.id, account_id=account.id, is_owner=owner)
    db.add(link)
    await db.flush()
    await phone_context(db, "")
    return link

async def account_for(db, user):
    link = await membership_for(db, user)
    if not link or not link.is_active:
        raise HTTPException(403, "Tài khoản chưa được chuyển đổi hoặc đã bị thu hồi quyền chi nhánh")
    await account_context(db, link.account_id)
    account = (await db.execute(select(LoginAccount).where(LoginAccount.id == link.account_id))).scalar_one_or_none()
    if not account or not account.is_active:
        raise HTTPException(403, "Tài khoản đã bị khóa")
    from app.services.spa_service import tenant_spa
    spa = await tenant_spa(db, user.tenant_id)
    if account.spa_id != spa.id:
        raise HTTPException(403, "Tài khoản không thuộc spa này")
    return account, link

async def branches_for(db, account_id):
    await account_context(db, account_id)
    account = (await db.execute(select(LoginAccount).where(LoginAccount.id == account_id, LoginAccount.is_active.is_(True)))).scalar_one_or_none()
    if not account or not account.spa_id:
        return []
    from app.services.spa_service import spa_context
    await spa_context(db, account.spa_id)
    links = list((await db.execute(select(BranchMembership).where(
        BranchMembership.account_id == account_id, BranchMembership.is_active.is_(True))
        .order_by(BranchMembership.created_at, BranchMembership.id))).scalars().all())
    result = []
    for link in links:
        await set_tenant_context(db, link.tenant_id)
        user = (await db.execute(select(User).where(User.tenant_id == link.tenant_id,
                User.id == link.user_id, User.is_active.is_(True), User.role.in_([UserRole.ADMIN, UserRole.STAFF])))).scalar_one_or_none()
        tenant = (await db.execute(select(Tenant).where(Tenant.id == link.tenant_id, Tenant.spa_id == account.spa_id, Tenant.status == "ACTIVE"))).scalar_one_or_none()
        if user and tenant:
            result.append((link, user, tenant))
    return result

async def authenticate_management(db, phone, password):
    await phone_context(db, phone)
    account = (await db.execute(select(LoginAccount).where(LoginAccount.phone_number == phone))).scalar_one_or_none()
    if not account or not account.is_active or not verify_password(password, account.password_hash):
        raise HTTPException(401, "Sai số điện thoại hoặc mật khẩu")
    await phone_context(db, "")
    branches = await branches_for(db, account.id)
    if not branches:
        raise HTTPException(401, "Tài khoản không có chi nhánh được phép truy cập")
    return await preferred_branch(db, account, branches)


async def preferred_branch(db, account, branches):
    target = next((row for row in branches if row[2].id == account.default_branch_id), branches[0])
    if target[1].role == UserRole.STAFF:
        from datetime import datetime
        from app.services.assignment_service import assignment, TZ
        assigned = await assignment(db, account.id, datetime.now(TZ).date())
        if assigned and assigned.tenant_id:
            target = next((row for row in branches if row[2].id == assigned.tenant_id), target)
    await set_tenant_context(db, target[2].id)
    return target[1]

async def branch_password(db, user, password):
    link = await membership_for(db, user)
    if link:
        account, _ = await account_for(db, user)
        return verify_password(password, account.password_hash)
    return verify_password(password, user.password_hash)
