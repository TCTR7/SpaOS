"""Operator tool: report legacy identities; explicitly provision ONE reviewed user.
Run with migration credentials. No automatic merging and no password changes.
"""
import argparse
import asyncio
import uuid
from collections import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.database import set_tenant_context
from app.models.models import Tenant, User, UserRole, BranchMembership
from app.schemas.auth import _check_phone
from app.services.branch_service import provision_account
from app.services.audit_service import audit

async def run(args):
    engine = create_async_engine(settings.MIGRATION_DATABASE_URL)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            tenants = (await db.execute(select(Tenant))).scalars().all()
            rows, missing = [], []
            for tenant in tenants:
                await set_tenant_context(db, tenant.id)
                users = (await db.execute(select(User).where(User.tenant_id == tenant.id,
                    User.role.in_([UserRole.ADMIN, UserRole.STAFF])))).scalars().all()
                linked = set((await db.execute(select(BranchMembership.user_id).where(
                    BranchMembership.tenant_id == tenant.id))).scalars().all())
                for user in users:
                    rows.append(user)
                    if user.id not in linked:
                        missing.append((tenant, user))
            counts = Counter(u.phone_number for u in rows)
            if not args.apply:
                print("Tài khoản quản trị chưa chuyển đổi:", len(missing))
                for tenant, user in missing:
                    print(tenant.id, user.id, user.phone_number, user.role.value,
                          "TRUNG_SO" if counts[user.phone_number] > 1 else "CHUA_LIEN_KET")
                print("Chỉ báo cáo; không ghi hoặc gộp tài khoản.")
                return
            if not args.tenant_id or not args.user_id:
                raise ValueError("--apply cần --tenant-id và --user-id đã đối chiếu")
            target = next((u for t, u in missing if str(t.id) == args.tenant_id and str(u.id) == args.user_id), None)
            if target is None:
                raise ValueError("Chỉ hỗ trợ user ADMIN/STAFF chưa liên kết tại đúng chi nhánh")
            phone = _check_phone(args.phone or target.phone_number)
            if any(u.id != target.id and u.phone_number == phone for u in rows):
                raise ValueError("SĐT còn trùng. Đối chiếu và chọn SĐT riêng cho đúng người; không tự gộp.")
            await set_tenant_context(db, target.tenant_id)
            target.phone_number = phone
            await db.flush()
            await provision_account(db, target, owner=target.role == UserRole.ADMIN)
            audit(db, target.tenant_id, None, "IDENTITY_PROVISIONED", "user", target.id,
                  {"operator_reviewed": True})
            await db.commit()
            print("Đã chuyển đúng một tài khoản đã đối chiếu; giữ nguyên user ID và dữ liệu nghiệp vụ.")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--tenant-id")
    parser.add_argument("--user-id")
    parser.add_argument("--phone", help="SĐT đã đối chiếu; không nhập mật khẩu trên CLI")
    asyncio.run(run(parser.parse_args()))
