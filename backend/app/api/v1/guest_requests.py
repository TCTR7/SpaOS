"""No password, phone lookup, account merge or slot reservation for anonymous enquiries."""
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.booking_deps import TenantCtx, get_optional_tenant_ctx
from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.models.models import GuestBookingRequest, User, UserRole, Booking, BookingStatus
from app.schemas.auth import _check_phone
from app.schemas.booking import BookingCreate, BookingItemIn
from app.services import booking_service as bookings
from app.services.manual_booking_service import create_batch
from app.schemas.manual_booking import ManualBatchIn, ManualCustomerIn
from app.services.notification_queue import drain_events
from app.services.audit_service import audit

router = APIRouter(tags=["guest booking requests"])
management = require_roles(UserRole.ADMIN, UserRole.STAFF)

class GuestKey(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: uuid.UUID
    token: str = Field(pattern=r"^[a-f0-9]{64}$")

class GuestIn(GuestKey):
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str
    _phone = field_validator("phone_number")(_check_phone)
    service_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    staff_id: uuid.UUID | None = None
    start_time: datetime
    note: str | None = Field(default=None, max_length=950)

class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(pattern="^(confirm|reject)$")
    identity_verified: bool = False
    customer_id: uuid.UUID | None = None

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

async def public_result(db, row):
    # Capability grants this enquiry only; no CRM, package or other booking data.
    result = {"request_id": row.request_id, "status": row.status, "start_time": row.start_time.astimezone(bookings.TZ),
            "booking_status": None,
            "message": "Spa sẽ gọi xác nhận. Giờ chưa được giữ." if row.status == "PENDING" else
                       "Spa đã xác nhận lịch hẹn." if row.status == "CONFIRMED" else "Spa chưa nhận yêu cầu này. Vui lòng liên hệ spa."}
    if row.booking_id:
        booking = (await db.execute(select(Booking.start_time, Booking.status).where(
            Booking.tenant_id == row.tenant_id, Booking.id == row.booking_id))).one_or_none()
        if booking:
            result["start_time"] = booking.start_time.astimezone(bookings.TZ)
            result["booking_status"] = booking.status.value
            result["message"] = {"PENDING":"Lịch đang chờ spa xác nhận.","CONFIRMED":"Spa đã xác nhận lịch hẹn.",
                "IN_PROGRESS":"Buổi chăm sóc đang diễn ra.","COMPLETED":"Buổi chăm sóc đã hoàn thành.",
                "CANCELLED":"Lịch hẹn đã hủy. Liên hệ spa nếu cần đặt lại.","NO_SHOW":"Spa ghi nhận khách chưa đến buổi hẹn."}[booking.status.value]
    return result

@router.post("/public/guest-requests", status_code=201)
async def submit(body: GuestIn, ctx: TenantCtx = Depends(get_optional_tenant_ctx)):
    db, tid = ctx.db, ctx.tenant_id
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"guest-requests:{tid}"})
    digest = hashlib.sha256(json.dumps(body.model_dump(mode="json", exclude={"token"}), sort_keys=True).encode()).hexdigest()
    old = (await db.execute(select(GuestBookingRequest).where(GuestBookingRequest.tenant_id == tid,
        GuestBookingRequest.request_id == body.request_id))).scalar_one_or_none()
    if old:
        if not hmac.compare_digest(old.token_hash, token_hash(body.token)): raise HTTPException(404, "Không tìm thấy yêu cầu")
        if old.payload_hash != digest: raise HTTPException(409, "Mã yêu cầu đã dùng; kiểm tra yêu cầu cũ trước khi gửi lại")
        return await public_result(db, old)
    start = bookings.ensure_aware(body.start_time)
    now = datetime.now(timezone.utc)
    if not now < start <= now + timedelta(days=90): raise HTTPException(422, "Chọn giờ trong tương lai, tối đa 90 ngày")
    if len(set(body.service_ids)) != len(body.service_ids): raise HTTPException(422, "Không chọn trùng dịch vụ")
    # Shared DB limit works across workers; retries above do not consume the limit.
    recent = GuestBookingRequest.created_at > now - timedelta(hours=1)
    count = await db.scalar(select(func.count()).select_from(GuestBookingRequest).where(GuestBookingRequest.tenant_id == tid, recent))
    phone_count = await db.scalar(select(func.count()).select_from(GuestBookingRequest).where(GuestBookingRequest.tenant_id == tid, recent, GuestBookingRequest.phone_number == body.phone_number))
    if count >= 100 or phone_count >= 3: raise HTTPException(429, "Đã gửi nhiều yêu cầu. Vui lòng gọi spa để được hỗ trợ.")
    services = await bookings.load_services(db, tid, body.service_ids)
    tenant = await bookings.load_tenant(db, tid)
    staff_ids = await bookings.list_active_staff_ids(db, tid, body.service_ids)
    if body.staff_id:
        if body.staff_id not in staff_ids: raise HTTPException(422, "Nhân viên chưa phù hợp với dịch vụ")
        staff_ids = [body.staff_id]
    slots = await bookings.compute_available_slots(db, tenant, start.astimezone(bookings.TZ).date(), bookings.total_duration(body.service_ids, services), staff_ids)
    if not any(s == start for s, _, _ in slots): raise HTTPException(409, "Giờ này không còn trống. Vui lòng chọn lại.")
    row = GuestBookingRequest(tenant_id=tid, request_id=body.request_id, token_hash=token_hash(body.token), payload_hash=digest,
        full_name=body.full_name.strip(), phone_number=body.phone_number, note=body.note, service_ids=[str(s) for s in body.service_ids],
        staff_id=body.staff_id, start_time=start, status="PENDING")
    if not row.full_name: raise HTTPException(422, "Nhập họ tên khách")
    db.add(row)
    await db.flush()
    result = await public_result(db, row)
    await db.commit()
    return result

@router.post("/public/guest-requests/status")
async def check(body: GuestKey, ctx: TenantCtx = Depends(get_optional_tenant_ctx)):
    row = (await ctx.db.execute(select(GuestBookingRequest).where(GuestBookingRequest.tenant_id == ctx.tenant_id,
        GuestBookingRequest.request_id == body.request_id))).scalar_one_or_none()
    if not row or not hmac.compare_digest(row.token_hash, token_hash(body.token)): raise HTTPException(404, "Không tìm thấy yêu cầu")
    return await public_result(ctx.db, row)

@router.get("/guest-requests")
async def inbox(offset: int = Query(0, ge=0), actor: User = Depends(management),
    tid: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    rows = (await db.execute(select(GuestBookingRequest).where(GuestBookingRequest.tenant_id == tid,
        GuestBookingRequest.status == "PENDING").order_by(GuestBookingRequest.created_at).limit(51).offset(offset))).scalars().all()
    return {"has_more":len(rows)>50, "items":[{"id":r.id, "full_name":r.full_name, "phone_number":r.phone_number,
        "start_time":r.start_time, "note":r.note, "service_ids":r.service_ids, "staff_id":r.staff_id} for r in rows[:50]]}

@router.post("/guest-requests/{request_id}/decision")
async def decide(request_id: uuid.UUID, body: Decision, background_tasks: BackgroundTasks, actor: User = Depends(management),
    tid: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    # Consistent ordering with bookings and assignment changes.
    from app.services.assignment_service import lock_workforce
    await lock_workforce(db, tid)
    row = (await db.execute(select(GuestBookingRequest).where(GuestBookingRequest.tenant_id == tid,
        GuestBookingRequest.id == request_id).with_for_update())).scalar_one_or_none()
    if not row: raise HTTPException(404, "Không tìm thấy yêu cầu")
    if row.status != "PENDING": return {"status":row.status,"booking_id":row.booking_id}
    if body.action == "reject":
        row.status = "REJECTED"
    else:
        if not body.identity_verified: raise HTTPException(422, "Gọi xác minh khách trước khi xác nhận")
        if row.start_time <= datetime.now(timezone.utc): raise HTTPException(409, "Yêu cầu đã quá giờ. Tạo lịch mới sau khi thống nhất với khách.")
        if body.customer_id:
            from app.services.customer_access import customer_access
            customer = await customer_access(db, tid, body.customer_id, actor, write=True)
            if customer.phone_number != row.phone_number: raise HTTPException(422, "Số điện thoại hồ sơ khác yêu cầu; xác minh lại với khách")
        # Existing profiles require explicit selection and customer_access; never merge by phone.
        batch = ManualBatchIn(request_id=row.request_id, customer_id=body.customer_id,
            new_customer=None if body.customer_id else ManualCustomerIn(full_name=row.full_name,phone_number=row.phone_number),
            staff_id=row.staff_id, items=[{"service_id":s} for s in row.service_ids], start_times=[row.start_time], note=row.note)
        result = await create_batch(db, tid, actor, batch, commit=False)
        row.booking_id, row.status = result.booking_ids[0], "CONFIRMED"
        await bookings.update_booking_status(db, tid, row.booking_id, BookingStatus.CONFIRMED, actor, commit=False)
    audit(db, tid, actor, "GUEST_REQUEST_" + row.status, "guest_request", row.id)
    result = {"status":row.status,"booking_id":row.booking_id}
    confirmed = row.status == "CONFIRMED"
    await db.commit()
    if confirmed: background_tasks.add_task(drain_events, tid)
    return result
