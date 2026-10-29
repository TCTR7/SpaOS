import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_tenant_db
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.models.models import (Tenant, User, UserRole, BranchMembership, LoginAccount,
    Booking, BookingStatus, PaymentEntry, CustomerPackage, PackageStatus)
from app.schemas.auth import TenantOut, UserOut
from app.schemas.branches import BranchOut, BranchCreate, BranchStatusUpdate, StaffGrant, DashboardOut, DashboardMetrics, DashboardBranch
from app.api.v1.auth import _token_response
from app.api.v1.payments import collection_statement
from app.services.branch_service import account_for, branches_for, account_context
from app.services.audit_service import audit
from app.services.booking_service import TZ

router = APIRouter(tags=["branches"])

def branch_view(link, user, tenant):
    return BranchOut(tenant=TenantOut.model_validate(tenant), user=UserOut.model_validate(user), is_owner=link.is_owner)

async def authorized_branches(db, user):
    account, current = await account_for(db, user)
    rows = await branches_for(db, account.id)
    await set_tenant_context(db, user.tenant_id)
    return account, current, rows

@router.get("/branches/public")
async def public_branches(spa_slug: str | None = None, db: AsyncSession = Depends(get_db)):
    from app.services.spa_service import public_spa
    if not spa_slug:
        return {"brand_name": settings.BRAND_NAME, "branches": []}
    spa = await public_spa(db, spa_slug)
    rows = (await db.execute(select(Tenant).where(Tenant.spa_id == spa.id, Tenant.status == "ACTIVE").order_by(Tenant.name, Tenant.id))).scalars().all()
    return {"brand_name": spa.name,
            "branches": [{"id": row.id, "name": row.name, "slug": row.slug, "address": row.address, "contact_phone": row.contact_phone} for row in rows]}

@router.get("/branches", response_model=list[BranchOut])
async def list_branches(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    _, _, rows = await authorized_branches(db, user)
    return [branch_view(*row) for row in rows]

async def managed_rows(db, user):
    account,current=await account_for(db,user)
    if user.role!=UserRole.ADMIN or not current.is_owner:
        raise HTTPException(403,"Chỉ chủ spa được quản lý trạng thái chi nhánh")
    links=(await db.execute(select(BranchMembership).where(BranchMembership.account_id==account.id,
        BranchMembership.is_owner.is_(True),BranchMembership.is_active.is_(True)))).scalars().all()
    rows=[]
    for link in links:
        await set_tenant_context(db,link.tenant_id)
        tenant=(await db.execute(select(Tenant).where(Tenant.id==link.tenant_id,Tenant.spa_id==account.spa_id))).scalar_one_or_none()
        local=(await db.execute(select(User).where(User.tenant_id==link.tenant_id,User.id==link.user_id,
            User.role==UserRole.ADMIN,User.is_active.is_(True)))).scalar_one_or_none()
        if tenant and local:rows.append((link,local,tenant))
    await set_tenant_context(db,user.tenant_id)
    return rows


@router.get("/branches/manage",response_model=list[BranchOut])
async def manage_branches(user: User=Depends(get_current_user),db: AsyncSession=Depends(get_tenant_db)):
    return [branch_view(*row) for row in await managed_rows(db,user)]


@router.patch("/branches/{branch_id}/status",response_model=BranchOut)
async def update_branch_status(branch_id: uuid.UUID,body: BranchStatusUpdate,
    user: User=Depends(get_current_user),db: AsyncSession=Depends(get_tenant_db)):
    from app.services.assignment_service import lock_workforce,check_revocation
    from app.services.spa_service import tenant_spa,check_branch_limit
    await lock_workforce(db,user.tenant_id)
    spa=await tenant_spa(db,user.tenant_id,lock=True)
    target=next((row for row in await managed_rows(db,user) if row[2].id==branch_id),None)
    if not target:raise HTTPException(404,"Không có quyền quản lý chi nhánh")
    link,local,tenant=target
    if tenant.status==body.status:return branch_view(*target)
    if body.status=="ACTIVE":
        await check_branch_limit(db,spa)
    else:
        if branch_id==user.tenant_id:
            raise HTTPException(409,"Chuyển sang một chi nhánh đang hoạt động khác trước khi tạm ngưng chi nhánh này")
        await set_tenant_context(db,branch_id)
        pending=(await db.execute(select(Booking.id).where(Booking.tenant_id==branch_id,
            Booking.status.in_([BookingStatus.PENDING,BookingStatus.CONFIRMED,BookingStatus.IN_PROGRESS]),
            ((Booking.end_time>datetime.now(TZ))|(Booking.status==BookingStatus.IN_PROGRESS))).limit(1))).first()
        customers=(await db.execute(select(User.id).where(User.tenant_id==branch_id,User.role==UserRole.CUSTOMER,
            User.assigned_staff_id.is_not(None)).limit(1))).first()
        if pending or customers:
            raise HTTPException(409,"Còn lịch hẹn hoặc khách đang được nhân viên phụ trách. Xử lý lịch và bàn giao về chủ spa trước khi tạm ngưng.")
        staff=(await db.execute(select(User).where(User.tenant_id==branch_id,User.role==UserRole.STAFF))).scalars().all()
        for person in staff:
            member=(await db.execute(select(BranchMembership).where(BranchMembership.tenant_id==branch_id,
                BranchMembership.user_id==person.id,BranchMembership.is_active.is_(True)))).scalar_one_or_none()
            if member:await check_revocation(db,branch_id,person)
    tenant.status=body.status
    await set_tenant_context(db,branch_id)
    audit(db,branch_id,local,"BRANCH_STATUS_UPDATED","branch",branch_id,{"status":body.status})
    result=branch_view(link,local,tenant)
    await db.commit()
    return result


@router.post("/branches/{branch_id}/switch")
async def switch_branch(branch_id: uuid.UUID, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_tenant_db)):
    account, _, rows = await authorized_branches(db, user)
    target = next((row for row in rows if row[2].id == branch_id), None)
    if target is None:
        raise HTTPException(404, "Không có quyền truy cập chi nhánh")
    await account_context(db, account.id)
    account.default_branch_id = branch_id
    result = _token_response(target[1])
    await db.commit()
    return result

@router.post("/branches", response_model=BranchOut, status_code=201)
async def create_branch(body: BranchCreate, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_tenant_db)):
    account, current = await account_for(db, user)
    if not current.is_owner or user.role != UserRole.ADMIN:
        raise HTTPException(403, "Chỉ chủ hệ thống được tạo chi nhánh")
    if not body.name.strip():
        raise HTTPException(422, "Tên chi nhánh không được để trống")
    from app.services.spa_service import tenant_spa, check_branch_limit
    spa = await tenant_spa(db, user.tenant_id, lock=True)
    await check_branch_limit(db, spa)
    tenant = Tenant(slug="cn-" + uuid.uuid4().hex, name=body.name.strip(), spa_id=spa.id)
    db.add(tenant)
    await db.flush()
    await set_tenant_context(db, tenant.id)
    local_user = User(tenant_id=tenant.id, role=UserRole.ADMIN, full_name=user.full_name,
                      phone_number=account.phone_number, password_hash=account.password_hash)
    db.add(local_user)
    await db.flush()
    link = BranchMembership(tenant_id=tenant.id, user_id=local_user.id, account_id=account.id, is_owner=True)
    db.add(link)
    await db.flush()
    audit(db, tenant.id, local_user, "BRANCH_CREATED", "branch", tenant.id, {"name": tenant.name})
    result = branch_view(link, local_user, tenant)
    await db.commit()
    return result

@router.post("/branches/{branch_id}/staff-access", response_model=UserOut, status_code=201)
async def grant_staff(branch_id: uuid.UUID, body: StaffGrant, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_tenant_db)):
    return await grant_staff_access(db, user, branch_id, body.source_staff_id)


async def grant_staff_access(db, user, branch_id, source_staff_id, *, commit=True):
    from app.services.assignment_service import lock_workforce
    await lock_workforce(db, user.tenant_id)
    owner, current, rows = await authorized_branches(db, user)
    target = next((row for row in rows if row[2].id == branch_id and row[0].is_owner and row[1].role == UserRole.ADMIN), None)
    if not current.is_owner or user.role != UserRole.ADMIN or target is None:
        raise HTTPException(403, "Chỉ chủ hệ thống được cấp quyền giữa các chi nhánh của mình")
    source = (await db.execute(select(User).where(User.tenant_id == user.tenant_id,
        User.id == source_staff_id, User.role == UserRole.STAFF, User.is_active.is_(True)))).scalar_one_or_none()
    if source is None:
        raise HTTPException(404, "Không tìm thấy nhân viên tại chi nhánh hiện tại")
    account, _ = await account_for(db, source)
    from app.services.spa_service import check_staff_limit
    await check_staff_limit(db, user.tenant_id, account.id)
    await set_tenant_context(db, branch_id)
    old = (await db.execute(select(BranchMembership).where(BranchMembership.tenant_id == branch_id,
        BranchMembership.account_id == account.id))).scalar_one_or_none()
    if old:
        local_user = (await db.execute(select(User).where(User.tenant_id == branch_id, User.id == old.user_id))).scalar_one()
        old.is_active = True
        local_user.is_active = True
    else:
        local_user = User(id=uuid.uuid4(), tenant_id=branch_id, role=UserRole.STAFF, full_name=source.full_name,
                          phone_number=account.phone_number, password_hash=account.password_hash)
        db.add(local_user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(409, "Chi nhánh đã có hồ sơ trùng số điện thoại; cần đối chiếu, không tự gộp")
        db.add(BranchMembership(tenant_id=branch_id, user_id=local_user.id, account_id=account.id))
    audit(db, branch_id, target[1], "BRANCH_ACCESS_GRANTED", "user", local_user.id, {"source_branch_id": str(user.tenant_id)})
    try:
        await db.flush()
        result = UserOut.model_validate(local_user)
        if commit:
            await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Chi nhánh đã có hồ sơ trùng số điện thoại; cần đối chiếu, không tự gộp")
    return result

@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(day: date | None = None, branch_id: uuid.UUID | None = None, all_branches: bool = False,
                    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_tenant_db)):
    _, current, rows = await authorized_branches(db, user)
    if user.role != UserRole.ADMIN:
        raise HTTPException(403, "Chỉ Admin được xem dashboard")
    if all_branches and branch_id:
        raise HTTPException(422, "Chọn một chi nhánh hoặc tất cả")
    if all_branches:
        if not current.is_owner:
            raise HTTPException(403, "Chỉ chủ hệ thống được xem tổng hợp")
        rows = [row for row in rows if row[0].is_owner and row[1].role == UserRole.ADMIN]
    else:
        rows = [row for row in rows if row[2].id == (branch_id or user.tenant_id) and row[1].role == UserRole.ADMIN]
        if not rows:
            raise HTTPException(404, "Không có quyền xem chi nhánh")
    day = day or datetime.now(TZ).date()
    start = datetime.combine(day, time.min, tzinfo=TZ)
    end = start + timedelta(days=1)
    output, totals = [], DashboardMetrics()
    for link, local_user, tenant in rows:
        tid = tenant.id
        await set_tenant_context(db, tid)
        b = (await db.execute(select(
            func.count().filter(Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.NO_SHOW])),
            func.count().filter(Booking.status == BookingStatus.IN_PROGRESS),
            func.count().filter(Booking.status == BookingStatus.COMPLETED),
            func.coalesce(func.sum(Booking.total_price).filter(Booking.status == BookingStatus.COMPLETED), 0)
        ).where(Booking.tenant_id == tid, Booking.start_time >= start, Booking.start_time < end))).one()
        received = dict((await db.execute(select(PaymentEntry.method, func.sum(PaymentEntry.amount)).where(
            PaymentEntry.tenant_id == tid, PaymentEntry.created_at >= start, PaymentEntry.created_at < end)
            .group_by(PaymentEntry.method))).all())
        sources = collection_statement(tid).subquery()
        outstanding, unknown = (await db.execute(select(
            func.coalesce(func.sum(case((sources.c.balance_due > 0, sources.c.balance_due), else_=0)), 0),
            func.count().filter(sources.c.status == "NEEDS_PRICE")))).one()
        active = (await db.execute(select(func.count()).select_from(CustomerPackage).where(
            CustomerPackage.tenant_id == tid, CustomerPackage.status == PackageStatus.ACTIVE,
            CustomerPackage.used_sessions < CustomerPackage.total_sessions,
            (CustomerPackage.expiry_date.is_(None) | (CustomerPackage.expiry_date > datetime.now(TZ)))))).scalar_one()
        cash, bank = received.get("CASH", Decimal(0)), received.get("BANK_TRANSFER", Decimal(0))
        metrics = DashboardMetrics(appointments=b[0], in_progress=b[1], completed=b[2], completed_value=b[3],
            cash=cash, bank_transfer=bank, net_received=cash+bank, outstanding=outstanding,
            unknown_prices=unknown, active_packages=active)
        output.append(DashboardBranch(branch_id=tid, name=tenant.name, metrics=metrics))
        totals = DashboardMetrics(**{key: getattr(totals, key)+getattr(metrics, key) for key in DashboardMetrics.model_fields})
    await set_tenant_context(db, user.tenant_id)
    return DashboardOut(date=day, branches=output, totals=totals)
