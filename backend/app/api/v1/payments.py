import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text, case, literal, union_all, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.core.database import set_tenant_context
from app.models.models import PaymentInvoice, PaymentEntry, AuditLog, Booking, CustomerPackage, User, UserRole, BookingItem, BookingStatus, Service
from app.schemas.payments import InvoiceCreate, ReceiptCreate, ReceiptVoid, InvoiceOut, EntryOut, AuditOut, PaymentSummaryOut, CollectionOut
from app.services.audit_service import audit
from app.services.booking_service import TZ

router = APIRouter(tags=["payments"])
_admin = require_roles(UserRole.ADMIN)


async def lock_key(db, value):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": value})


async def invoice_row(db, tenant_id, invoice_id, *, lock=False):
    query = select(PaymentInvoice).where(PaymentInvoice.tenant_id == tenant_id, PaymentInvoice.id == invoice_id)
    if lock:
        query = query.with_for_update()
    row = (await db.execute(query)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Không tìm thấy phiếu thu")
    return row


def view(row, paid):
    paid = Decimal(paid)
    return InvoiceOut(id=row.id, customer_id=row.customer_id, booking_id=row.booking_id,
        customer_package_id=row.customer_package_id, amount_due=row.amount_due, amount_paid=paid,
        balance_due=row.amount_due-paid, status="PAID" if paid == row.amount_due else "PARTIAL" if paid else "UNPAID",
        created_at=row.created_at)


async def total_paid(db, tenant_id, invoice_id):
    return (await db.execute(select(func.coalesce(func.sum(PaymentEntry.amount), 0)).where(
        PaymentEntry.tenant_id == tenant_id, PaymentEntry.invoice_id == invoice_id))).scalar_one()


async def existing_entry(db, tenant_id, key):
    return (await db.execute(select(PaymentEntry).where(
        PaymentEntry.tenant_id == tenant_id, PaymentEntry.idempotency_key == key))).scalar_one_or_none()


@router.post("/payments/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(body: InvoiceCreate, actor: User = Depends(_admin),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    source_id = body.booking_id or body.customer_package_id
    source_name = "booking" if body.booking_id else "package"
    await lock_key(db, f"invoice:{tenant_id}:{source_name}:{source_id}")
    field = PaymentInvoice.booking_id if body.booking_id else PaymentInvoice.customer_package_id
    old = (await db.execute(select(PaymentInvoice).where(
        PaymentInvoice.tenant_id == tenant_id, field == source_id))).scalar_one_or_none()
    if old:
        if body.legacy_amount_due is not None and body.legacy_amount_due != old.amount_due:
            raise HTTPException(409, "Phiếu đã có số tiền khác")
        return view(old, await total_paid(db, tenant_id, old.id))
    model = Booking if body.booking_id else CustomerPackage
    source = (await db.execute(select(model).where(model.tenant_id == tenant_id, model.id == source_id))).scalar_one_or_none()
    if source is None:
        raise HTTPException(404, "Không tìm thấy lịch hẹn hoặc thẻ")
    if body.booking_id:
        amount = source.total_price
    else:
        amount = source.purchase_price
        if amount is None:
            if body.legacy_amount_due is None:
                raise HTTPException(422, "Thẻ cũ chưa có giá bán; Admin cần xác nhận số tiền phải thu")
            amount = body.legacy_amount_due
        elif body.legacy_amount_due is not None:
            raise HTTPException(422, "Thẻ mới dùng giá bán đã chốt, không lấy giá từ request")
    row = PaymentInvoice(tenant_id=tenant_id, customer_id=source.customer_id,
        booking_id=body.booking_id, customer_package_id=body.customer_package_id,
        amount_due=amount, created_by=actor.id)
    db.add(row)
    await db.flush()
    audit(db, tenant_id, actor, "INVOICE_CREATED", "invoice", row.id,
          {"amount_due": str(amount), "source_id": str(source_id), "source_type": source_name,
           "legacy_price_confirmed": source_name == "package" and source.purchase_price is None})
    result = view(row, Decimal(0))
    await db.commit()
    return result


@router.get("/payments/invoices", response_model=List[InvoiceOut])
async def list_invoices(customer_id: Optional[uuid.UUID] = None, limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0), actor: User = Depends(_admin),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    query = (select(PaymentInvoice, func.coalesce(func.sum(PaymentEntry.amount), 0))
        .outerjoin(PaymentEntry, (PaymentEntry.invoice_id == PaymentInvoice.id) & (PaymentEntry.tenant_id == tenant_id))
        .where(PaymentInvoice.tenant_id == tenant_id).group_by(PaymentInvoice.id)
        .order_by(PaymentInvoice.created_at.desc(), PaymentInvoice.id).limit(limit).offset(offset))
    if customer_id:
        query = query.where(PaymentInvoice.customer_id == customer_id)
    return [view(row, paid) for row, paid in (await db.execute(query)).all()]


@router.get("/payments/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: uuid.UUID, actor: User = Depends(_admin),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    row = await invoice_row(db, tenant_id, invoice_id)
    return view(row, await total_paid(db, tenant_id, invoice_id))


@router.get("/payments/invoices/{invoice_id}/entries", response_model=List[EntryOut])
async def entries(invoice_id: uuid.UUID, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0),
        actor: User = Depends(_admin), tenant_id: uuid.UUID = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_tenant_db)):
    await invoice_row(db, tenant_id, invoice_id)
    return list((await db.execute(select(PaymentEntry).where(
        PaymentEntry.tenant_id == tenant_id, PaymentEntry.invoice_id == invoice_id)
        .order_by(PaymentEntry.created_at.desc(), PaymentEntry.id).limit(limit).offset(offset))).scalars().all())


@router.post("/payments/invoices/{invoice_id}/receipts", response_model=EntryOut, status_code=201)
async def receive(invoice_id: uuid.UUID, body: ReceiptCreate, actor: User = Depends(_admin),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    await lock_key(db, f"payment-key:{tenant_id}:{body.idempotency_key}")
    old = await existing_entry(db, tenant_id, body.idempotency_key)
    if old:
        if (old.invoice_id, old.amount, old.method, old.note, old.reversal_of) != (
                invoice_id, body.amount, body.method, body.note, None):
            raise HTTPException(409, "Mã giao dịch đã được dùng với nội dung khác")
        return old
    row = await invoice_row(db, tenant_id, invoice_id, lock=True)
    paid = await total_paid(db, tenant_id, invoice_id)
    if paid + body.amount > row.amount_due:
        raise HTTPException(409, "Số tiền vượt quá khoản còn phải thu")
    entry = PaymentEntry(tenant_id=tenant_id, invoice_id=invoice_id, amount=body.amount,
        method=body.method, recorded_by=actor.id, idempotency_key=body.idempotency_key, note=body.note)
    db.add(entry)
    await db.flush()
    audit(db, tenant_id, actor, "PAYMENT_RECEIVED", "invoice", invoice_id,
          {"entry_id": str(entry.id), "amount": str(body.amount), "method": body.method})
    result = EntryOut.model_validate(entry)
    await db.commit()
    return result


@router.post("/payments/entries/{entry_id}/void", response_model=EntryOut, status_code=201)
async def void_receipt(entry_id: uuid.UUID, body: ReceiptVoid, actor: User = Depends(_admin),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    if not body.reason.strip():
        raise HTTPException(422, "Cần ghi lý do hủy khoản thu")
    await lock_key(db, f"payment-key:{tenant_id}:{body.idempotency_key}")
    original = (await db.execute(select(PaymentEntry).where(
        PaymentEntry.tenant_id == tenant_id, PaymentEntry.id == entry_id))).scalar_one_or_none()
    if original is None:
        raise HTTPException(404, "Không tìm thấy khoản thu")
    old = await existing_entry(db, tenant_id, body.idempotency_key)
    if old:
        if old.reversal_of != entry_id or old.note != body.reason.strip():
            raise HTTPException(409, "Mã giao dịch đã được dùng với nội dung khác")
        return old
    if original.reversal_of is not None:
        raise HTTPException(409, "Không thể hủy một bút toán hủy")
    await invoice_row(db, tenant_id, original.invoice_id, lock=True)
    reversal = (await db.execute(select(PaymentEntry.id).where(
        PaymentEntry.tenant_id == tenant_id, PaymentEntry.reversal_of == entry_id))).scalar_one_or_none()
    if reversal:
        raise HTTPException(409, "Khoản thu đã được hủy")
    entry = PaymentEntry(tenant_id=tenant_id, invoice_id=original.invoice_id, amount=-original.amount,
        method=original.method, recorded_by=actor.id, idempotency_key=body.idempotency_key,
        reversal_of=entry_id, note=body.reason.strip())
    db.add(entry)
    await db.flush()
    audit(db, tenant_id, actor, "PAYMENT_VOIDED", "invoice", original.invoice_id,
          {"entry_id": str(entry.id), "original_entry_id": str(entry_id), "amount": str(entry.amount),
           "reason": body.reason.strip()})
    result = EntryOut.model_validate(entry)
    await db.commit()
    return result


@router.get("/payments/summary", response_model=PaymentSummaryOut)
async def summary(date_from: date, date_to: date, actor: User = Depends(_admin),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    if date_to < date_from or (date_to-date_from).days > 366:
        raise HTTPException(422, "Khoảng ngày không hợp lệ hoặc vượt 366 ngày")
    start = datetime.combine(date_from, time.min, tzinfo=TZ)
    end = datetime.combine(date_to+timedelta(days=1), time.min, tzinfo=TZ)
    rows = (await db.execute(select(PaymentEntry.method, func.sum(PaymentEntry.amount)).where(
        PaymentEntry.tenant_id == tenant_id, PaymentEntry.created_at >= start, PaymentEntry.created_at < end)
        .group_by(PaymentEntry.method))).all()
    by_method = {method: amount for method, amount in rows}
    return {"date_from": date_from, "date_to": date_to, "timezone": str(TZ),
            "cash": by_method.get("CASH", Decimal(0)), "bank_transfer": by_method.get("BANK_TRANSFER", Decimal(0)),
            "net_received": sum(by_method.values(), Decimal(0))}


@router.get("/audit-logs", response_model=List[AuditOut])
async def audit_logs(entity_id: Optional[uuid.UUID] = None, limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0), actor: User = Depends(_admin),
        tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_tenant_db)):
    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    return list((await db.execute(query.order_by(AuditLog.created_at.desc(), AuditLog.id).limit(limit).offset(offset))).scalars().all())


def collection_statement(tenant_id, q=""):
    # One bounded query across both sources; no writes while browsing.
    paid = (select(PaymentEntry.invoice_id.label("invoice_id"), func.sum(PaymentEntry.amount).label("paid"))
        .where(PaymentEntry.tenant_id == tenant_id).group_by(PaymentEntry.invoice_id).subquery())
    items = (select(BookingItem.booking_id.label("booking_id"),
        func.string_agg(Service.name, " + ").label("description"),
        func.bool_and(BookingItem.customer_package_id.is_not(None)).label("covered"))
        .join(Service, (Service.id == BookingItem.service_id) & (Service.tenant_id == tenant_id))
        .where(BookingItem.tenant_id == tenant_id).group_by(BookingItem.booking_id).subquery())

    def source_query(model, kind, amount, description, occurred, covered):
        field = PaymentInvoice.booking_id if kind == "booking" else PaymentInvoice.customer_package_id
        due = case((PaymentInvoice.id.is_not(None), PaymentInvoice.amount_due), else_=amount)
        query = (select(model.id.label("source_id"), literal(kind).label("source_type"),
            model.customer_id, User.full_name.label("customer_name"), User.phone_number,
            description.label("description"), occurred.label("occurred_at"),
            cast(model.status, String).label("source_status"), PaymentInvoice.id.label("invoice_id"),
            due.label("amount_due"), func.coalesce(paid.c.paid, 0).label("amount_paid"),
            covered.label("covered"))
            .join(User, (User.id == model.customer_id) & (User.tenant_id == tenant_id))
            .outerjoin(PaymentInvoice, (field == model.id) & (PaymentInvoice.tenant_id == tenant_id))
            .outerjoin(paid, paid.c.invoice_id == PaymentInvoice.id)
            .where(model.tenant_id == tenant_id))
        if q.strip():
            pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            query = query.where(or_(User.full_name.ilike(pattern, escape="\\"), User.phone_number.ilike(pattern, escape="\\")))
        return query

    bookings = source_query(Booking, "booking", Booking.total_price,
        func.coalesce(items.c.description, "Dịch vụ theo lịch hẹn"), Booking.start_time,
        func.coalesce(items.c.covered, False)).outerjoin(items, items.c.booking_id == Booking.id)
    # Cancelled/no-show appointments without a collection record are not a request for payment.
    bookings = bookings.where(or_(Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.NO_SHOW]),
                                  PaymentInvoice.id.is_not(None)))
    packages = source_query(CustomerPackage, "package", CustomerPackage.purchase_price,
        CustomerPackage.package_name, CustomerPackage.created_at, literal(False))
    sources = union_all(bookings, packages).subquery()
    status = case(
        (sources.c.amount_due.is_(None), "NEEDS_PRICE"),
        ((sources.c.amount_due == 0) & sources.c.covered, "COVERED"),
        (sources.c.amount_due == 0, "FREE"),
        (sources.c.amount_paid >= sources.c.amount_due, "PAID"),
        (sources.c.amount_paid > 0, "PARTIAL"), else_="UNPAID")
    rows = select(sources, (sources.c.amount_due-sources.c.amount_paid).label("balance_due"), status.label("status"))
    return rows


@router.get("/payments/collections", response_model=List[CollectionOut])
async def collections(q: str = Query("", max_length=100), scope: Literal["outstanding", "all"] = "outstanding", customer_id: Optional[uuid.UUID] = None,
        limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
        actor: User = Depends(_admin), tenant_id: uuid.UUID = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_tenant_db)):
    rows = collection_statement(tenant_id, q)
    status = rows.selected_columns.status
    sources = rows.get_final_froms()[0]
    if customer_id is not None:
        rows = rows.where(sources.c.customer_id == customer_id)
    if scope == "outstanding":
        rows = rows.where(status.in_(["UNPAID", "PARTIAL", "NEEDS_PRICE"]))
    rows = rows.order_by(case((status.in_(["UNPAID", "PARTIAL", "NEEDS_PRICE"]), 0), else_=1),
                         sources.c.occurred_at.desc(), sources.c.source_type, sources.c.source_id).limit(limit).offset(offset)
    return [dict(row) for row in (await db.execute(rows)).mappings().all()]
