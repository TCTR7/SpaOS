"""Atomic counter bookings with durable tenant/actor-scoped retry results."""
import hashlib
import json
import secrets
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.core.security import hash_password
from app.models.models import CustomerPackage, ManualBookingBatch, PackageStatus, User, UserRole
from app.schemas.booking import BookingCreate, BookingItemIn
from app.schemas.manual_booking import ManualBatchOut
from app.services import booking_service as bookings
from app.services.audit_service import audit
from app.services.customer_access import customer_access


async def _request_lock(db, tenant_id, actor, request_id):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                     {"key": f"manual-batch:{tenant_id}:{actor.id}:{request_id}"})


async def _find(db, tenant_id, actor, request_id):
    return (await db.execute(select(ManualBookingBatch).where(
        ManualBookingBatch.tenant_id == tenant_id, ManualBookingBatch.actor_id == actor.id,
        ManualBookingBatch.request_id == request_id))).scalar_one_or_none()


async def get_result(db, tenant_id, actor, request_id):
    await _request_lock(db, tenant_id, actor, request_id)
    row = await _find(db, tenant_id, actor, request_id)
    if row is None:
        raise HTTPException(404, "Không có lần tạo lịch đã lưu với mã này")
    await customer_access(db, tenant_id, row.customer_id, actor)
    return ManualBatchOut.model_validate(row)


async def create_batch(db, tenant_id, actor, body):
    from app.services.assignment_service import lock_workforce
    await lock_workforce(db, tenant_id)
    digest = hashlib.sha256(json.dumps(body.model_dump(mode="json"), sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    try:
        await _request_lock(db, tenant_id, actor, body.request_id)
        old = await _find(db, tenant_id, actor, body.request_id)
        if old:
            await customer_access(db, tenant_id, old.customer_id, actor, write=True)
            if old.payload_hash != digest:
                raise HTTPException(409, "Mã tạo lịch đã dùng với nội dung khác")
            output = ManualBatchOut.model_validate(old)
            # Release retry/customer locks before post-response notification sessions.
            await db.commit()
            return output
        if body.new_customer:
            new = body.new_customer
            customer = User(tenant_id=tenant_id, role=UserRole.CUSTOMER,
                full_name=new.full_name, phone_number=new.phone_number, notes=new.notes,
                password_hash=hash_password(secrets.token_urlsafe(24)),
                assigned_staff_id=actor.id if actor.role == UserRole.STAFF else None)
            db.add(customer)
            await db.flush()
            audit(db, tenant_id, actor, "CUSTOMER_CREATED", "customer", customer.id)
        else:
            customer = await customer_access(db, tenant_id, body.customer_id, actor, write=True)
        await customer_access(db, tenant_id, customer.id, actor, write=True)
        services = await bookings.load_services(db, tenant_id, [i.service_id for i in body.items])
        issued, items = {}, []
        for line in body.items:
            svc = services[line.service_id]
            pid = line.customer_package_id
            if pid is None and svc.is_package:
                if svc.id not in issued:
                    package = CustomerPackage(tenant_id=tenant_id, customer_id=customer.id,
                        service_id=svc.id, package_name=svc.name, purchase_price=svc.price,
                        total_sessions=svc.total_sessions, used_sessions=0, status=PackageStatus.ACTIVE)
                    db.add(package)
                    await db.flush()
                    issued[svc.id] = package.id
                    audit(db, tenant_id, actor, "PACKAGE_ISSUED", "package", package.id,
                          {"customer_id": str(customer.id), "purchase_price": str(svc.price),
                           "total_sessions": svc.total_sessions})
                pid = issued[svc.id]
            items.append(BookingItemIn(service_id=svc.id, customer_package_id=pid))
        # Prelock the full resource set in the established order. Later rows
        # reuse this fixed technician set, never acquiring a new lower ID.
        await bookings._lock_packages(db, tenant_id, sorted({i.customer_package_id for i in items if i.customer_package_id}))
        candidates = [body.staff_id] if body.staff_id else await bookings.list_active_staff_ids(db, tenant_id, [i.service_id for i in items])
        for sid in sorted(candidates):
            await bookings._lock_staff_row(db, tenant_id, sid)
        created = []
        times = sorted(body.start_times, key=bookings.ensure_aware)
        for index, start in enumerate(times):
            prefix = f"[Buổi {index + 1}/{len(times)}]" if len(times) > 1 else ""
            booking = await bookings.create_booking(db, tenant_id, actor, BookingCreate(
                customer_id=customer.id, staff_id=body.staff_id, start_time=start,
                items=items, note=" ".join(p for p in (prefix, body.note) if p) or None),
                commit=False, staff_candidates=candidates)
            created.append(str(booking.id))
        result = ManualBookingBatch(tenant_id=tenant_id, actor_id=actor.id, request_id=body.request_id,
            payload_hash=digest, customer_id=customer.id, package_ids=[str(p) for p in issued.values()],
            booking_ids=created)
        db.add(result)
        await db.flush()
        output = ManualBatchOut.model_validate(result)
        await db.commit()
        return output
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Số điện thoại hoặc dữ liệu tạo lịch đã tồn tại; chưa lưu lần tạo này")
    except Exception:
        await db.rollback()
        raise
