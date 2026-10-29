"""Small, tenant-scoped APIs supporting role workflows; no new business role."""
import base64
import binascii
import hashlib
import json
import secrets
import struct
import uuid
import zlib
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, get_current_user, get_public_tenant, get_tenant_db, require_roles
from app.core.database import get_db, set_tenant_context
from app.core.security import hash_password, verify_password
from app.models.models import (Booking, BookingHandover, BookingItem, BookingRequest, BookingStatus, BranchMembership,
    CustomerPackage, LoginAccount, RecoveryGrant, Service, StaffDateOverride, StaffSchedule, Tenant, TenantLogo, User, UserRole)
from app.schemas.admin import UserDetailOut
from app.schemas.experience import (CredentialsUpdate, CustomerBookingRequest, DateOverrideIn, HandoverIn, LogoIn,
    ProfileUpdate, RecoveryClaim, RecoveryIssue)
from app.services import booking_service as bookings
from app.services.audit_service import audit
from app.services.branch_service import account_context, account_for, branch_password, membership_for
from app.services.customer_access import booking_access, customer_access

router = APIRouter(tags=["experience"])
admin = require_roles(UserRole.ADMIN)
management = require_roles(UserRole.ADMIN, UserRole.STAFF)
customer_role = require_roles(UserRole.CUSTOMER)


@router.get("/customers/{customer_id}", response_model=UserDetailOut)
async def customer_detail(customer_id: uuid.UUID, actor: User = Depends(management),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    return await customer_access(db, tenant_id, customer_id, actor)


@router.patch("/account/profile", response_model=UserDetailOut)
async def update_profile(body: ProfileUpdate, actor: User = Depends(customer_role),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    row = await customer_access(db, tenant_id, actor.id, actor, write=True)
    row.full_name = body.full_name
    audit(db, tenant_id, actor, "PROFILE_UPDATED", "customer", row.id, {"fields": ["full_name"]})
    await db.commit()
    return row


@router.patch("/account/credentials")
async def own_credentials(body: CredentialsUpdate, actor: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    if not await branch_password(db, actor, body.current_password): raise HTTPException(403, "Mật khẩu hiện tại không đúng")
    await change_credentials(db, tenant_id, actor, actor, body)
    from app.api.v1.auth import _token_response
    return _token_response(actor)


async def change_credentials(db, tenant_id, actor, target, body):
    link = await membership_for(db, target)
    digest = hash_password(body.password)
    try:
        if not link:
            target = (await db.execute(select(User).where(User.tenant_id == tenant_id, User.id == target.id)
                .execution_options(populate_existing=True).with_for_update())).scalar_one()
            if actor.id == target.id and not verify_password(body.current_password, target.password_hash):
                raise HTTPException(403, "Mật khẩu hiện tại không đúng")
            if body.phone_number and body.phone_number != target.phone_number:
                raise HTTPException(422, "Đổi số điện thoại khách cần được spa xác minh riêng")
            target.password_hash = digest
            target.auth_version += 1
        else:
            # Resolve the actor's verified owner scope BEFORE switching account context.
            actor_account, actor_link = await account_for(db, actor)
            own = actor_account.id == link.account_id
            allowed = set((await db.execute(select(BranchMembership.tenant_id).where(
                BranchMembership.account_id == actor_account.id, BranchMembership.is_owner.is_(True),
                BranchMembership.is_active.is_(True)))).scalars().all())
            await account_context(db, link.account_id)
            account = (await db.execute(select(LoginAccount).where(LoginAccount.id == link.account_id).with_for_update())).scalar_one()
            links = list((await db.execute(select(BranchMembership).where(BranchMembership.account_id == link.account_id)
                .order_by(BranchMembership.tenant_id))).scalars().all())
            if not own and (any(item.is_owner for item in links) or not {item.tenant_id for item in links}.issubset(allowed)):
                raise HTTPException(403, "Bạn cần quyền chủ spa ở mọi chi nhánh của tài khoản này")
            if own and not verify_password(body.current_password, account.password_hash):
                raise HTTPException(403, "Mật khẩu hiện tại không đúng")
            phone = body.phone_number or account.phone_number
            account.phone_number, account.password_hash = phone, digest
            await db.flush()
            for item in links:
                await set_tenant_context(db, item.tenant_id)
                local = (await db.execute(select(User).where(User.tenant_id == item.tenant_id, User.id == item.user_id).with_for_update())).scalar_one()
                local.phone_number, local.password_hash = phone, digest
                local.auth_version += 1
                await db.flush()
            await set_tenant_context(db, tenant_id)
        audit(db, tenant_id, actor, "CREDENTIALS_CHANGED", "user", target.id, {"sessions_revoked": True})
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Số điện thoại đã được sử dụng; chưa thay đổi tài khoản")


@router.patch("/staff/{staff_id}/account")
async def staff_credentials(staff_id: uuid.UUID, body: CredentialsUpdate, actor: User = Depends(admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    if not await branch_password(db, actor, body.current_password): raise HTTPException(403, "Mật khẩu xác nhận không đúng")
    target = await bookings.get_active_staff(db, tenant_id, staff_id)
    await change_credentials(db, tenant_id, actor, target, body)
    return {"updated": True}


@router.post("/customers/{customer_id}/recovery-link")
async def issue_recovery(customer_id: uuid.UUID, body: RecoveryIssue, actor: User = Depends(admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    if not await branch_password(db, actor, body.current_password): raise HTTPException(403, "Mật khẩu xác nhận không đúng")
    user = await customer_access(db, tenant_id, customer_id, actor, write=True)
    if not user.is_active: raise HTTPException(409, "Tài khoản khách đang ngưng hoạt động")
    await db.execute(select(User.id).where(User.tenant_id == tenant_id, User.id == customer_id).with_for_update())
    await db.execute(delete(RecoveryGrant).where(RecoveryGrant.tenant_id == tenant_id, RecoveryGrant.user_id == user.id))
    token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.add(RecoveryGrant(tenant_id=tenant_id, user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=expiry))
    audit(db, tenant_id, actor, "RECOVERY_LINK_ISSUED", "customer", user.id, {"identity_verified": True})
    await db.commit()
    return {"token": token, "expires_at": expiry}


@router.post("/auth/recovery")
async def claim_recovery(body: RecoveryClaim, tenant: Tenant = Depends(get_public_tenant), db: AsyncSession = Depends(get_db)):
    await set_tenant_context(db, tenant.id)
    digest = hashlib.sha256(body.token.encode()).hexdigest()
    grant = (await db.execute(select(RecoveryGrant).where(RecoveryGrant.tenant_id == tenant.id, RecoveryGrant.token_hash == digest))).scalar_one_or_none()
    invalid = HTTPException(400, "Liên kết không còn hiệu lực. Vui lòng nhờ spa cấp liên kết mới.")
    if grant is None: raise invalid
    user = (await db.execute(select(User).where(User.tenant_id == tenant.id, User.id == grant.user_id,
        User.role == UserRole.CUSTOMER, User.is_active.is_(True)).with_for_update())).scalar_one_or_none()
    grant = (await db.execute(select(RecoveryGrant).where(RecoveryGrant.tenant_id == tenant.id, RecoveryGrant.id == grant.id)
        .execution_options(populate_existing=True).with_for_update())).scalar_one_or_none()
    if not user or not grant or grant.consumed_at or grant.expires_at <= datetime.now(timezone.utc): raise invalid
    user.password_hash = hash_password(body.password)
    user.auth_version += 1
    grant.consumed_at = datetime.now(timezone.utc)
    audit(db, tenant.id, user, "RECOVERY_COMPLETED", "customer", user.id, {"sessions_revoked": True})
    await db.commit()
    return {"updated": True}


@router.get("/staff/me/work-hours")
async def own_hours(actor: User = Depends(require_roles(UserRole.STAFF)), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    week = (await db.execute(select(StaffSchedule).where(StaffSchedule.tenant_id == tenant_id, StaffSchedule.staff_id == actor.id).order_by(StaffSchedule.day_of_week))).scalars().all()
    overrides = (await db.execute(select(StaffDateOverride).where(StaffDateOverride.tenant_id == tenant_id,
        StaffDateOverride.staff_id == actor.id, StaffDateOverride.day >= datetime.now(bookings.TZ).date()).order_by(StaffDateOverride.day).limit(100))).scalars().all()
    return {"week": [{"day_of_week": r.day_of_week, "start_time": r.start_time, "end_time": r.end_time, "is_day_off": r.is_day_off} for r in week],
        "overrides": [{"day": r.day, "start_time": r.start_time, "end_time": r.end_time, "is_day_off": r.is_day_off} for r in overrides]}


@router.get("/staff/{staff_id}/date-overrides")
async def date_overrides(staff_id: uuid.UUID, actor: User = Depends(admin), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    await bookings.get_active_staff(db, tenant_id, staff_id)
    rows = (await db.execute(select(StaffDateOverride).where(StaffDateOverride.tenant_id == tenant_id,
        StaffDateOverride.staff_id == staff_id, StaffDateOverride.day >= datetime.now(bookings.TZ).date()).order_by(StaffDateOverride.day).limit(100))).scalars().all()
    return [{"day": r.day, "start_time": r.start_time, "end_time": r.end_time, "is_day_off": r.is_day_off} for r in rows]


async def check_override(db, tenant_id, staff_id, day, windows):
    start, end = bookings.local_day_bounds(day)
    rows = (await db.execute(select(Booking).where(Booking.tenant_id == tenant_id, Booking.staff_id == staff_id,
        Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]),
        Booking.start_time < end, Booking.end_time > start))).scalars().all()
    affected = [row for row in rows if not bookings._fits(windows, row.start_time, row.end_time)]
    if affected: raise HTTPException(409, f"Có {len(affected)} lịch bị ảnh hưởng. Hãy đổi hoặc hủy các lịch đó trước khi đổi ca.")


@router.put("/staff/{staff_id}/date-overrides")
async def save_override(staff_id: uuid.UUID, body: DateOverrideIn, actor: User = Depends(admin), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    if body.day < datetime.now(bookings.TZ).date(): raise HTTPException(422, "Chọn hôm nay hoặc ngày tương lai")
    from app.services.assignment_service import save_assignments
    from app.schemas.workforce import AssignmentIn
    await save_assignments(db, actor, staff_id, [AssignmentIn(day=body.day,
        tenant_id=None if body.is_day_off else tenant_id, start_time=None if body.is_day_off else body.start_time,
        end_time=None if body.is_day_off else body.end_time)], body.day, weekly=False)
    await bookings._lock_staff_row(db, tenant_id, staff_id)
    await bookings.get_active_staff(db, tenant_id, staff_id)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    windows = [] if body.is_day_off else [(datetime.combine(body.day, max(body.start_time, tenant.open_time), bookings.TZ),
        datetime.combine(body.day, min(body.end_time, tenant.close_time), bookings.TZ))]
    await check_override(db, tenant_id, staff_id, body.day, windows)
    old = (await db.execute(select(StaffDateOverride).where(StaffDateOverride.tenant_id == tenant_id,
        StaffDateOverride.staff_id == staff_id, StaffDateOverride.day == body.day))).scalar_one_or_none()
    if old:
        old.start_time, old.end_time, old.is_day_off = body.start_time, body.end_time, body.is_day_off
    else: db.add(StaffDateOverride(tenant_id=tenant_id, staff_id=staff_id, **body.model_dump()))
    audit(db, tenant_id, actor, "STAFF_DATE_OVERRIDE", "user", staff_id, {"day": body.day.isoformat()})
    await db.commit()
    return {"updated": True}


@router.delete("/staff/{staff_id}/date-overrides/{day}")
async def remove_override(staff_id: uuid.UUID, day: date, actor: User = Depends(admin), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    await bookings._lock_staff_row(db, tenant_id, staff_id)
    await bookings.get_active_staff(db, tenant_id, staff_id)
    from app.services.assignment_service import staff_account, verify_bookings
    from app.services.spa_service import tenant_spa
    from app.models.models import StaffAssignment
    spa = await tenant_spa(db, tenant_id)
    aid = await staff_account(db, tenant_id, staff_id)
    await db.execute(delete(StaffAssignment).where(StaffAssignment.spa_id == spa.id,
        StaffAssignment.account_id == aid, StaffAssignment.day == day))
    await verify_bookings(db, spa, aid, day)
    await set_tenant_context(db, tenant_id)
    await db.execute(delete(StaffDateOverride).where(StaffDateOverride.tenant_id == tenant_id,
        StaffDateOverride.staff_id == staff_id, StaffDateOverride.day == day))
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    windows = await bookings.get_schedule_windows(db, tenant, [staff_id], day)
    await check_override(db, tenant_id, staff_id, day, windows[staff_id])
    await db.commit()
    return {"removed": True}


@router.get("/bookings/{booking_id}/handover")
async def get_handover(booking_id: uuid.UUID, actor: User = Depends(management), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    await booking_access(db, tenant_id, booking_id, actor, allow_assigned=True)
    row = (await db.execute(select(BookingHandover).where(BookingHandover.tenant_id == tenant_id, BookingHandover.booking_id == booking_id))).scalar_one_or_none()
    return {"note": row.note if row else "", "updated_at": row.updated_at if row else None}


@router.put("/bookings/{booking_id}/handover")
async def save_handover(booking_id: uuid.UUID, body: HandoverIn, actor: User = Depends(management), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    await booking_access(db, tenant_id, booking_id, actor, write=True)
    row = (await db.execute(select(BookingHandover).where(BookingHandover.tenant_id == tenant_id, BookingHandover.booking_id == booking_id))).scalar_one_or_none()
    if row: row.note, row.author_id = body.note.strip(), actor.id
    else: db.add(BookingHandover(tenant_id=tenant_id, booking_id=booking_id, author_id=actor.id, note=body.note.strip()))
    audit(db, tenant_id, actor, "HANDOVER_UPDATED", "booking", booking_id, {"fields": ["handover"]})
    await db.commit()
    return {"updated": True}


@router.get("/customer-packages/{package_id}/history")
async def package_history(package_id: uuid.UUID, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
    actor: User = Depends(get_current_user), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    package = (await db.execute(select(CustomerPackage).where(CustomerPackage.tenant_id == tenant_id, CustomerPackage.id == package_id))).scalar_one_or_none()
    if not package: raise HTTPException(404, "Không tìm thấy thẻ")
    await customer_access(db, tenant_id, package.customer_id, actor)
    rows = (await db.execute(select(Booking.id, Booking.start_time, Booking.status).join(BookingItem,
        (BookingItem.booking_id == Booking.id) & (BookingItem.tenant_id == tenant_id)).where(Booking.tenant_id == tenant_id,
        Booking.customer_id == package.customer_id, BookingItem.customer_package_id == package_id)
        .distinct().order_by(Booking.start_time.desc(), Booking.id).limit(limit).offset(offset))).all()
    return [{"booking_id": r.id, "start_time": r.start_time, "status": r.status} for r in rows]


@router.get("/tenants/me/setup")
async def setup_summary(actor: User = Depends(admin), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    staff_ids = select(User.id).where(User.tenant_id == tenant_id, User.role == UserRole.STAFF, User.is_active.is_(True))
    service_count = (await db.execute(select(func.count(Service.id)).where(Service.tenant_id == tenant_id, Service.is_active.is_(True)))).scalar_one()
    staff_count = (await db.execute(select(func.count(User.id)).where(User.tenant_id == tenant_id, User.id.in_(staff_ids)))).scalar_one()
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    from app.services.assignment_service import effective_windows
    ids=list((await db.execute(staff_ids)).scalars())
    working=set()
    today=datetime.now(bookings.TZ).date()
    for offset in range(7):
        windows=await effective_windows(db,tenant,ids,today+timedelta(days=offset))
        working.update(sid for sid,hours in windows.items() if hours)
    schedules=len(working)
    return {"services": service_count, "staff": staff_count, "staff_with_hours": schedules,
        "contact_ready": bool(tenant.address and tenant.contact_phone), "slug": tenant.slug}


def validate_jpeg(data: bytes) -> tuple[int, int]:
    if len(data) > 2097152 or len(data) < 4 or data[:2] != b"\xff\xd8":
        raise HTTPException(422, "Chọn ảnh JPG/PNG tối đa 2 MB")
    cursor, width, height = 2, None, None
    while cursor < len(data):
        if data[cursor] != 0xff:
            cursor += 1
            continue
        while cursor < len(data) and data[cursor] == 0xff:
            cursor += 1
        if cursor >= len(data):
            break
        marker = data[cursor]
        cursor += 1
        if marker in (0xd8, 0xd9):
            continue
        if 0xd0 <= marker <= 0xd7:
            continue
        if cursor + 2 > len(data):
            break
        length = struct.unpack(">H", data[cursor:cursor+2])[0]
        if length < 2 or cursor + length > len(data):
            break
        if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
            if length >= 7:
                h, w = struct.unpack(">HH", data[cursor+3:cursor+7])
                width, height = w, h
                break
        cursor += length
    if not width or not height or not (0 < width <= 2048 and 0 < height <= 2048):
        raise HTTPException(422, "Ảnh tối đa 2048 × 2048")
    return width, height


def validate_png(data: bytes) -> tuple[int, int]:
    if len(data) > 2097152 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(422, "Chọn ảnh PNG/JPG tối đa 2 MB")
    cursor, first, ended = 8, True, False
    width, height = None, None
    while cursor + 12 <= len(data):
        length = struct.unpack(">I", data[cursor:cursor+4])[0]
        kind, payload = data[cursor+4:cursor+8], data[cursor+8:cursor+8+length]
        if length > 2097152 or cursor+12+length > len(data): raise HTTPException(422, "Ảnh không hợp lệ")
        checksum = struct.unpack(">I", data[cursor+8+length:cursor+12+length])[0]
        if zlib.crc32(kind + payload) & 0xffffffff != checksum: raise HTTPException(422, "Ảnh không hợp lệ")
        if first:
            if kind != b"IHDR" or length != 13: raise HTTPException(422, "Ảnh không hợp lệ")
            w, h = struct.unpack(">II", payload[:8])
            if not (0 < w <= 2048 and 0 < h <= 2048): raise HTTPException(422, "Ảnh tối đa 2048 × 2048")
            width, height = w, h
            first = False
        cursor += length + 12
        if kind == b"IEND": ended = length == 0 and cursor == len(data); break
    if not ended or not width or not height: raise HTTPException(422, "Ảnh không hợp lệ")
    return width, height


def validate_image_payload(data: bytes) -> str:
    if len(data) > 2097152:
        raise HTTPException(422, "Ảnh vượt quá dung lượng tối đa 2 MB")
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        validate_png(data)
        return "image/png"
    elif data[:2] == b"\xff\xd8":
        validate_jpeg(data)
        return "image/jpeg"
    raise HTTPException(422, "Vui lòng chọn ảnh PNG hoặc JPG hợp lệ.")


@router.post("/tenants/me/logo")
async def upload_logo(body: LogoIn, actor: User = Depends(admin), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    try: data = base64.b64decode(body.data, validate=True)
    except (ValueError, binascii.Error): raise HTTPException(422, "Ảnh không hợp lệ")
    validate_image_payload(data)
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"logo:{tenant_id}"})
    old = (await db.execute(select(TenantLogo).where(TenantLogo.tenant_id == tenant_id))).scalar_one_or_none()
    if old: old.data = data
    else: db.add(TenantLogo(tenant_id=tenant_id, data=data))
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    tenant.logo_url = f"/api/v1/public/tenants/{tenant.slug}/logo?v={uuid.uuid4().hex}"
    await db.commit()
    return {"logo_url": tenant.logo_url}


@router.get("/public/tenants/{slug}/logo")
async def public_logo(slug: str, db: AsyncSession = Depends(get_db)):
    tenant = (await db.execute(select(Tenant).where(Tenant.slug == slug.strip().lower(), Tenant.status == "ACTIVE"))).scalar_one_or_none()
    if not tenant: raise HTTPException(404, "Không tìm thấy ảnh")
    await set_tenant_context(db, tenant.id)
    row = (await db.execute(select(TenantLogo).where(TenantLogo.tenant_id == tenant.id))).scalar_one_or_none()
    if not row: raise HTTPException(404, "Không tìm thấy ảnh")
    media_type = "image/jpeg" if row.data[:2] == b"\xff\xd8" else "image/png"
    return Response(row.data, media_type=media_type, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=60"})


@router.post("/booking-requests", status_code=201)
async def customer_booking(body: CustomerBookingRequest, background_tasks: BackgroundTasks, actor: User = Depends(customer_role), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"customer-request:{tenant_id}:{actor.id}:{body.request_id}"})
    digest = hashlib.sha256(json.dumps(body.model_dump(mode="json", exclude={"request_id"}), sort_keys=True).encode()).hexdigest()
    old = (await db.execute(select(BookingRequest).where(BookingRequest.tenant_id == tenant_id,
        BookingRequest.actor_id == actor.id, BookingRequest.request_id == body.request_id))).scalar_one_or_none()
    if old:
        if old.payload_hash != digest: raise HTTPException(409, "Yêu cầu đã dùng cho nội dung khác")
        booking_id = old.booking_id
    else:
        from app.schemas.booking import BookingCreate
        booking = await bookings.create_booking(db, tenant_id, actor, BookingCreate(**body.model_dump(exclude={"request_id"})), commit=False)
        booking_id = booking.id
        db.add(BookingRequest(tenant_id=tenant_id, actor_id=actor.id, request_id=body.request_id, payload_hash=digest, booking_id=booking_id))
    await db.commit()
    await set_tenant_context(db, tenant_id)
    booking = await bookings.get_booking_full(db, tenant_id, booking_id)
    from app.services.notification_queue import drain_events
    background_tasks.add_task(drain_events, tenant_id)
    result = (await bookings.present_bookings(db, tenant_id, [booking], actor))[0]
    await db.commit()
    return result


@router.get("/booking-requests/{request_id}")
async def booking_result(request_id: uuid.UUID, actor: User = Depends(customer_role), tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"customer-request:{tenant_id}:{actor.id}:{request_id}"})
    row = (await db.execute(select(BookingRequest).where(BookingRequest.tenant_id == tenant_id,
        BookingRequest.actor_id == actor.id, BookingRequest.request_id == request_id))).scalar_one_or_none()
    if not row: raise HTTPException(404, "Chưa tìm thấy lịch đã lưu cho yêu cầu này")
    booking = await bookings.get_booking_full(db, tenant_id, row.booking_id)
    return (await bookings.present_bookings(db, tenant_id, [booking], actor))[0]
