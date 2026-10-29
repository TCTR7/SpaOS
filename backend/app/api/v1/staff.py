import base64
import binascii
import uuid
from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.api.utils import apply_patch, commit_and_refresh
from app.api.v1.experience import validate_png
from app.core.database import get_db, set_tenant_context
from app.core.security import hash_password
from app.services.branch_service import provision_account, membership_for, account_for, account_context
from app.models.models import BranchMembership, Service, StaffPhoto, StaffSchedule, StaffService, Tenant, User, UserRole
from app.schemas.admin import (
    ScheduleOut,
    ScheduleReplace,
    StaffCreate,
    StaffDetailOut,
    StaffPhotoIn,
    StaffSkillsReplace,
    StaffUpdate,
)

router = APIRouter(prefix="/staff", tags=["staff"])
public_router = APIRouter(tags=["staff"])

_admin = require_roles(UserRole.ADMIN)


async def _get_staff(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> User:
    result = await db.execute(
        select(User).where(User.id == staff_id, User.tenant_id == tenant_id, User.role == UserRole.STAFF)
    )
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    return staff


_NULLABLE_PROFILE = {"notes", "job_title", "bio", "experience_years", "experience_detail"}


async def _with_skills(db: AsyncSession, tenant_id: uuid.UUID, rows: List[User]) -> List[StaffDetailOut]:
    """Gắn danh sách service_id (kỹ năng) cho từng nhân viên bằng một truy vấn duy nhất."""
    mapping: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    ids = [row.id for row in rows]
    if ids:
        found = await db.execute(
            select(StaffService.staff_id, StaffService.service_id)
            .where(StaffService.tenant_id == tenant_id, StaffService.staff_id.in_(ids))
        )
        for staff_id, service_id in found.all():
            mapping[staff_id].append(service_id)
    out = []
    for row in rows:
        item = StaffDetailOut.model_validate(row)
        item.skill_service_ids = sorted(mapping.get(row.id, []), key=str)
        out.append(item)
    return out


def validate_jpeg(data: bytes) -> None:
    bad = HTTPException(status_code=422, detail="Ảnh không hợp lệ")
    if len(data) > 2097152 or data[:3] != b"\xff\xd8\xff" or data[-2:] != b"\xff\xd9":
        raise bad
    cursor = 2
    while cursor + 4 <= len(data):
        if data[cursor] != 0xFF:
            raise bad
        marker = data[cursor + 1]
        if marker == 0xFF:
            cursor += 1
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            cursor += 2
            continue
        length = int.from_bytes(data[cursor + 2:cursor + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[cursor + 5:cursor + 7], "big")
            width = int.from_bytes(data[cursor + 7:cursor + 9], "big")
            if not (0 < width <= 2048 and 0 < height <= 2048):
                raise HTTPException(status_code=422, detail="Ảnh tối đa 2048 × 2048")
            return
        if marker == 0xDA or length < 2:
            break
        cursor += 2 + length
    raise bad


@router.get("", response_model=List[StaffDetailOut])
async def list_staff(
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[StaffDetailOut]:
    stmt = select(User).where(User.tenant_id == tenant_id, User.role == UserRole.STAFF).order_by(User.full_name)
    return await _with_skills(db, tenant_id, list((await db.execute(stmt)).scalars().all()))


@router.post("", response_model=StaffDetailOut, status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: StaffCreate,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> StaffDetailOut:
    from app.services.spa_service import check_staff_limit
    from app.services.assignment_service import lock_workforce
    await lock_workforce(db, tenant_id)
    await check_staff_limit(db, tenant_id)
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
        if body.branch_ids:
            from app.api.v1.branches import grant_staff_access
            for branch_id in sorted(set(body.branch_ids) - {tenant_id}, key=str):
                await set_tenant_context(db, tenant_id)
                await grant_staff_access(db, _user, branch_id, staff.id, commit=False)
        await commit_and_refresh(db, tenant_id, staff)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Số điện thoại đã tồn tại trong Spa")
    return (await _with_skills(db, tenant_id, [staff]))[0]


@router.patch("/{staff_id}", response_model=StaffDetailOut)
async def update_staff(
    staff_id: uuid.UUID,
    body: StaffUpdate,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> StaffDetailOut:
    staff = await _get_staff(db, tenant_id, staff_id)
    data = body.model_dump(exclude_unset=True)
    from app.services.assignment_service import lock_workforce, check_revocation
    await lock_workforce(db, tenant_id)
    if data.get("is_active") is False and staff.is_active:
        await check_revocation(db, tenant_id, staff)
    if data.get("is_active") is True and not staff.is_active:
        from app.services.spa_service import check_staff_limit
        membership = await membership_for(db, staff)
        await check_staff_limit(db, tenant_id, membership.account_id if membership else None)
        if membership:
            await account_context(db,membership.account_id)
            membership.is_active=True
    password = data.pop("password", None)
    for key, value in data.items():
        if value is None and key not in _NULLABLE_PROFILE:
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
    return (await _with_skills(db, tenant_id, [staff]))[0]


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
    from app.services.assignment_service import save_assignments
    from app.schemas.workforce import AssignmentIn
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    by_day = {item.day_of_week: item for item in body.schedules}
    entries = []
    for weekday in range(7):
        item = by_day.get(weekday)
        working = item is not None and not item.is_day_off
        entries.append(AssignmentIn(weekday=weekday, tenant_id=tenant_id if working else None,
            start_time=item.start_time if working else None, end_time=item.end_time if working else None))
    await save_assignments(db, _user, staff_id, entries, today, weekly=True)
    await db.execute(
        delete(StaffSchedule).where(StaffSchedule.tenant_id == tenant_id, StaffSchedule.staff_id == staff_id)
    )
    rows = [StaffSchedule(tenant_id=tenant_id, staff_id=staff_id, **item.model_dump()) for item in body.schedules]
    db.add_all(rows)
    await commit_and_refresh(db, tenant_id, *rows)
    return sorted(rows, key=lambda r: r.day_of_week)


@router.put("/{staff_id}/skills", response_model=StaffDetailOut)
async def replace_skills(
    staff_id: uuid.UUID,
    body: StaffSkillsReplace,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> StaffDetailOut:
    """Thay toàn bộ kỹ năng (dịch vụ được phép thực hiện) của nhân viên."""
    staff = await _get_staff(db, tenant_id, staff_id)
    wanted = set(body.service_ids)
    if wanted:
        found = set((await db.execute(
            select(Service.id).where(Service.tenant_id == tenant_id, Service.id.in_(wanted))
        )).scalars().all())
        if found != wanted:
            raise HTTPException(status_code=422, detail="Có dịch vụ không tồn tại trong chi nhánh này")
    await db.execute(delete(StaffService).where(StaffService.tenant_id == tenant_id, StaffService.staff_id == staff_id))
    db.add_all([StaffService(tenant_id=tenant_id, staff_id=staff_id, service_id=sid) for sid in sorted(wanted, key=str)])
    await commit_and_refresh(db, tenant_id, staff)
    return (await _with_skills(db, tenant_id, [staff]))[0]


@router.post("/{staff_id}/photo", response_model=StaffDetailOut)
async def upload_photo(
    staff_id: uuid.UUID,
    body: StaffPhotoIn,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> StaffDetailOut:
    """Ảnh đại diện nhân viên: PNG hoặc JPEG, tối đa 256 KB và 2048 × 2048."""
    staff = await _get_staff(db, tenant_id, staff_id)
    try:
        data = base64.b64decode(body.data, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=422, detail="Ảnh không hợp lệ")
    from app.api.v1.experience import validate_image_payload
    content_type = validate_image_payload(data)
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"staff-photo:{staff_id}"})
    old = (await db.execute(select(StaffPhoto).where(StaffPhoto.tenant_id == tenant_id, StaffPhoto.staff_id == staff_id))).scalar_one_or_none()
    if old:
        old.data, old.content_type = data, content_type
    else:
        db.add(StaffPhoto(tenant_id=tenant_id, staff_id=staff_id, data=data, content_type=content_type))
    slug = (await db.execute(select(Tenant.slug).where(Tenant.id == tenant_id))).scalar_one()
    staff.photo_url = f"/api/v1/public/tenants/{slug}/staff/{staff_id}/photo?v={uuid.uuid4().hex}"
    await commit_and_refresh(db, tenant_id, staff)
    return (await _with_skills(db, tenant_id, [staff]))[0]


@router.delete("/{staff_id}/photo", response_model=StaffDetailOut)
async def delete_photo(
    staff_id: uuid.UUID,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> StaffDetailOut:
    staff = await _get_staff(db, tenant_id, staff_id)
    await db.execute(delete(StaffPhoto).where(StaffPhoto.tenant_id == tenant_id, StaffPhoto.staff_id == staff_id))
    staff.photo_url = None
    await commit_and_refresh(db, tenant_id, staff)
    return (await _with_skills(db, tenant_id, [staff]))[0]


@public_router.get("/public/tenants/{slug}/staff/{staff_id}/photo")
async def public_staff_photo(slug: str, staff_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Response:
    tenant = (await db.execute(select(Tenant).where(Tenant.slug == slug.strip().lower(), Tenant.status == "ACTIVE"))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    await set_tenant_context(db, tenant.id)
    row = (await db.execute(select(StaffPhoto).where(StaffPhoto.tenant_id == tenant.id, StaffPhoto.staff_id == staff_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    return Response(row.data, media_type=row.content_type, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=60"})
