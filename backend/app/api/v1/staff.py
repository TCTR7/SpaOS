import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.api.utils import apply_patch, commit_and_refresh
from app.core.security import hash_password
from app.services.branch_service import provision_account, membership_for, account_for, account_context
from app.models.models import StaffSchedule, User, UserRole, BranchMembership
from app.schemas.admin import (
    ScheduleOut,
    ScheduleReplace,
    StaffCreate,
    StaffUpdate,
    UserDetailOut,
)

router = APIRouter(prefix="/staff", tags=["staff"])

_admin = require_roles(UserRole.ADMIN)


async def _get_staff(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> User:
    result = await db.execute(
        select(User).where(User.id == staff_id, User.tenant_id == tenant_id, User.role == UserRole.STAFF)
    )
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    return staff


@router.get("", response_model=List[UserDetailOut])
async def list_staff(
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[User]:
    stmt = select(User).where(User.tenant_id == tenant_id, User.role == UserRole.STAFF).order_by(User.full_name)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=UserDetailOut, status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: StaffCreate,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> User:
    staff = User(
        tenant_id=tenant_id,
        role=UserRole.STAFF,
        full_name=body.full_name,
        phone_number=body.phone_number,
        password_hash=hash_password(body.password),
        notes=body.notes,
    )
    db.add(staff)
    try:
        await db.flush()
        await provision_account(db, staff)
        await commit_and_refresh(db, tenant_id, staff)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Số điện thoại đã tồn tại trong Spa")
    return staff


@router.patch("/{staff_id}", response_model=UserDetailOut)
async def update_staff(
    staff_id: uuid.UUID,
    body: StaffUpdate,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> User:
    staff = await _get_staff(db, tenant_id, staff_id)
    data = body.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    for key, value in data.items():
        if value is None and key != "notes":
            raise HTTPException(422, f"Trường '{key}' không được để null")
    account, link = None, None
    if password or "phone_number" in data:
        link = await membership_for(db, staff)
        if link:
            account, _ = await account_for(db, staff)
            links = (await db.execute(select(BranchMembership.id).where(BranchMembership.account_id == account.id))).all()
            if len(links) > 1:
                raise HTTPException(409, "Tài khoản dùng nhiều chi nhánh: không đổi SĐT/mật khẩu tại một chi nhánh.")
    try:
        for key, value in data.items():
            setattr(staff, key, value)
        if account:
            account.phone_number = staff.phone_number
            if password:
                account.password_hash = hash_password(password)
                staff.password_hash = account.password_hash
        elif password:
            staff.password_hash = hash_password(password)
        if password or "phone_number" in data:
            staff.auth_version += 1
        if (password or "phone_number" in data) and not link:
            await provision_account(db, staff)
        await commit_and_refresh(db, tenant_id, staff)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Số điện thoại đã tồn tại trong hệ thống")
    return staff


@router.get("/{staff_id}/schedules", response_model=List[ScheduleOut])
async def get_schedules(
    staff_id: uuid.UUID,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[StaffSchedule]:
    await _get_staff(db, tenant_id, staff_id)
    stmt = (
        select(StaffSchedule)
        .where(StaffSchedule.tenant_id == tenant_id, StaffSchedule.staff_id == staff_id)
        .order_by(StaffSchedule.day_of_week)
    )
    return list((await db.execute(stmt)).scalars().all())


@router.put("/{staff_id}/schedules", response_model=List[ScheduleOut])
async def replace_schedules(
    staff_id: uuid.UUID,
    body: ScheduleReplace,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[StaffSchedule]:
    """Ghi đè toàn bộ lịch làm việc của KTV (xóa cũ + thêm mới trong cùng 1 transaction)."""
    await _get_staff(db, tenant_id, staff_id)
    await db.execute(
        delete(StaffSchedule).where(StaffSchedule.tenant_id == tenant_id, StaffSchedule.staff_id == staff_id)
    )
    rows = [StaffSchedule(tenant_id=tenant_id, staff_id=staff_id, **item.model_dump()) for item in body.schedules]
    db.add_all(rows)
    await commit_and_refresh(db, tenant_id, *rows)
    return sorted(rows, key=lambda r: r.day_of_week)
