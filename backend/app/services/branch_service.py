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
    account = LoginAccount(phone_number=user.phone_number, password_hash=user.password_hash)
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
    return account, link

async def branches_for(db, account_id):
    await account_context(db, account_id)
    links = list((await db.execute(select(BranchMembership).where(
        BranchMembership.account_id == account_id, BranchMembership.is_active.is_(True))
        .order_by(BranchMembership.created_at, BranchMembership.id))).scalars().all())
    result = []
    for link in links:
        await set_tenant_context(db, link.tenant_id)
        user = (await db.execute(select(User).where(User.tenant_id == link.tenant_id,
                User.id == link.user_id, User.is_active.is_(True), User.role.in_([UserRole.ADMIN, UserRole.STAFF])))).scalar_one_or_none()
        tenant = (await db.execute(select(Tenant).where(Tenant.id == link.tenant_id, Tenant.status == "ACTIVE"))).scalar_one_or_none()
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
    return branches[0][1]

async def branch_password(db, user, password):
    link = await membership_for(db, user)
    if link:
        account, _ = await account_for(db, user)
        return verify_password(password, account.password_hash)
    return verify_password(password, user.password_hash)
