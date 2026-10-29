"""One workplace per local day. All schedule writes coordinate with booking writes."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, text, delete
from app.core.database import set_tenant_context
from app.models.models import StaffAssignment, BranchMembership, User, UserRole, Tenant, Booking, BookingStatus
from app.services.spa_service import tenant_spa, spa_context

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


async def lock_workforce(db, tenant_id):
    transaction=db.sync_session.get_transaction()
    lease=db.info.get("workforce_lease")
    if transaction is not None and lease is not None and lease[0] is transaction and lease[1]==tenant_id:
        return
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(401, "Chi nhánh của phiên không còn tồn tại")
    # A spa-wide lock gives a fixed order for multi-account batches and weekly edits.
    # Small spas trade some write parallelism for simple, auditable deadlock avoidance.
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                     {"key": "workforce-spa:" + str(tenant.spa_id or tenant.id)})
    # A commit/rollback produces a different SessionTransaction; never carry
    # lock ownership across transactions or sessions.
    db.info["workforce_lease"]=(db.sync_session.get_transaction(),tenant_id)


async def staff_account(db, tenant_id, staff_id):
    row = (await db.execute(select(BranchMembership).where(BranchMembership.tenant_id == tenant_id,
        BranchMembership.user_id == staff_id))).scalar_one_or_none()
    if not row or not row.is_active:
        raise HTTPException(409, "Nhân viên chưa có danh tính hợp lệ hoặc đã bị thu hồi quyền")
    return row.account_id


async def assignment(db, account_id, day):
    stmt = select(StaffAssignment).where(StaffAssignment.account_id == account_id)
    override = (await db.execute(stmt.where(StaffAssignment.day == day))).scalar_one_or_none()
    if override:
        return override
    return (await db.execute(stmt.where(StaffAssignment.day.is_(None),
        StaffAssignment.weekday == (day.weekday()+1) % 7, StaffAssignment.effective_from <= day)
        .order_by(StaffAssignment.effective_from.desc()).limit(1))).scalar_one_or_none()


async def effective_windows(db, tenant, staff_ids, day):
    result = {sid: [] for sid in staff_ids}
    links = (await db.execute(select(BranchMembership).where(BranchMembership.tenant_id == tenant.id,
        BranchMembership.user_id.in_(staff_ids), BranchMembership.is_active.is_(True)))).scalars().all()
    ids=[link.account_id for link in links]
    rows=(await db.execute(select(StaffAssignment).where(StaffAssignment.spa_id==tenant.spa_id,
        StaffAssignment.account_id.in_(ids),
        ((StaffAssignment.day==day) | ((StaffAssignment.day.is_(None)) &
          (StaffAssignment.weekday==(day.weekday()+1)%7) & (StaffAssignment.effective_from<=day))))
        .order_by(StaffAssignment.effective_from.desc()))).scalars().all() if ids else []
    for link in links:
        candidates=[r for r in rows if r.account_id==link.account_id]
        row=next((r for r in candidates if r.day==day),candidates[0] if candidates else None)
        if row and row.tenant_id == tenant.id and row.start_time and row.end_time:
            start, end = max(row.start_time, tenant.open_time), min(row.end_time, tenant.close_time)
            if start < end:
                result[link.user_id] = [(datetime.combine(day, start, TZ), datetime.combine(day, end, TZ))]
    return result


async def account_links(db, spa, aid):
    tids = (await db.execute(select(Tenant.id).where(Tenant.spa_id == spa.id))).scalars().all()
    links = []
    for tid in sorted(tids, key=str):
        await set_tenant_context(db, tid)
        row = (await db.execute(select(BranchMembership, User, Tenant).join(User,
            (User.id == BranchMembership.user_id) & (User.tenant_id == tid)).join(Tenant, Tenant.id == tid)
            .where(BranchMembership.tenant_id == tid, BranchMembership.account_id == aid,
                   User.role == UserRole.STAFF))).first()
        if row:
            links.append(row)
    return links


async def verify_bookings(db, spa, aid, start_day):
    # One bounded read for this identity; avoid two queries for every booking.
    assignments = (await db.execute(select(StaffAssignment).where(
        StaffAssignment.spa_id == spa.id, StaffAssignment.account_id == aid))).scalars().all()
    resolved = {}
    links = await account_links(db, spa, aid)
    for link, staff, tenant in links:
        await set_tenant_context(db, tenant.id)
        bookings = (await db.execute(select(Booking).where(Booking.tenant_id == tenant.id, Booking.staff_id == staff.id,
            Booking.status != BookingStatus.CANCELLED,
            Booking.end_time > datetime.combine(start_day, time.min, TZ)))).scalars().all()
        for booking in bookings:
            day = booking.start_time.astimezone(TZ).date()
            if day not in resolved:
                overrides = [r for r in assignments if r.day == day]
                weeks = [r for r in assignments if r.day is None and r.weekday == (day.weekday()+1)%7 and r.effective_from <= day]
                resolved[day] = overrides[0] if overrides else max(weeks,key=lambda r:r.effective_from,default=None)
            row = resolved[day]
            if not row or row.tenant_id != tenant.id or not row.start_time or not row.end_time or not link.is_active or not staff.is_active:
                raise HTTPException(409, "Còn lịch hẹn bị ảnh hưởng. Bàn giao, dời hoặc hủy lịch trước khi đổi phân công.")
            a = datetime.combine(day, max(row.start_time, tenant.open_time), TZ)
            b = datetime.combine(day, min(row.end_time, tenant.close_time), TZ)
            if not a <= booking.start_time or booking.end_time > b:
                raise HTTPException(409, "Còn lịch không nằm trong giờ làm mới. Hãy xử lý trước.")


async def save_assignments(db, actor, staff_id, entries, effective_from, *, weekly):
    origin = actor.tenant_id
    await lock_workforce(db, origin)
    from app.services.branch_service import account_for
    _, owner = await account_for(db, actor)
    if actor.role != UserRole.ADMIN or not owner.is_owner:
        raise HTTPException(403, "Chỉ chủ spa được phân công chi nhánh")
    spa = await tenant_spa(db, origin)
    staff = (await db.execute(select(User).where(User.tenant_id == origin, User.id == staff_id,
        User.role == UserRole.STAFF))).scalar_one_or_none()
    if not staff:
        raise HTTPException(404, "Không tìm thấy nhân viên")
    aid = await staff_account(db, origin, staff_id)
    links = await account_links(db, spa, aid)
    allowed = {t.id for link, u, t in links if link.is_active and u.is_active and t.status == "ACTIVE"}
    await spa_context(db, spa.id)
    for entry in entries:
        if entry.tenant_id is not None and entry.tenant_id not in allowed:
            raise HTTPException(422, "Nhân viên chưa được cấp chi nhánh được chọn")
    if weekly:
        await db.execute(delete(StaffAssignment).where(StaffAssignment.spa_id == spa.id,
            StaffAssignment.account_id == aid, StaffAssignment.day.is_(None), StaffAssignment.effective_from == effective_from))
    else:
        await db.execute(delete(StaffAssignment).where(StaffAssignment.spa_id == spa.id,
            StaffAssignment.account_id == aid, StaffAssignment.day == entries[0].day))
    for entry in entries:
        db.add(StaffAssignment(spa_id=spa.id, account_id=aid, tenant_id=entry.tenant_id,
            weekday=entry.weekday if weekly else None, day=None if weekly else entry.day,
            effective_from=effective_from, start_time=entry.start_time, end_time=entry.end_time))
    await db.flush()
    await verify_bookings(db, spa, aid, effective_from)
    await set_tenant_context(db, origin)
    from app.services.audit_service import audit
    audit(db, origin, actor, "STAFF_ASSIGNMENT_UPDATED", "user", staff_id, {"weekly": weekly, "effective_from": str(effective_from)})


async def check_revocation(db, tenant_id, staff):
    await lock_workforce(db, tenant_id)
    now = datetime.now(TZ)
    existing = (await db.execute(select(Booking.id).where(Booking.tenant_id == tenant_id, Booking.staff_id == staff.id,
        Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]),
        ((Booking.end_time > now) | (Booking.status == BookingStatus.IN_PROGRESS))).limit(1))).first()
    customers = (await db.execute(select(User.id).where(User.tenant_id == tenant_id, User.role == UserRole.CUSTOMER,
        User.assigned_staff_id == staff.id).limit(1))).first()
    if existing or customers:
        raise HTTPException(409, "Còn lịch hẹn hoặc khách đang phụ trách. Bàn giao trước khi thu hồi quyền.")
    aid = await staff_account(db, tenant_id, staff.id)
    spa = await tenant_spa(db, tenant_id)
    # Remove future exceptions; weekly references become days off from today.
    await db.execute(delete(StaffAssignment).where(StaffAssignment.spa_id == spa.id, StaffAssignment.account_id == aid,
        StaffAssignment.tenant_id == tenant_id, StaffAssignment.day >= now.date()))
    rows = (await db.execute(select(StaffAssignment).where(StaffAssignment.spa_id == spa.id,
        StaffAssignment.account_id == aid, StaffAssignment.day.is_(None)))).scalars().all()
    for weekday in range(7):
        current = max((row for row in rows if row.weekday == weekday and row.effective_from <= now.date()),
                      key=lambda row: row.effective_from, default=None)
        if current and current.tenant_id == tenant_id:
            if current.effective_from == now.date():
                current.tenant_id = current.start_time = current.end_time = None
            else:
                db.add(StaffAssignment(spa_id=spa.id, account_id=aid, weekday=weekday, effective_from=now.date()))
    for row in rows:
        if row.tenant_id == tenant_id and row.effective_from > now.date():
            row.tenant_id = row.start_time = row.end_time = None
    await db.flush()
    await set_tenant_context(db, tenant_id)


async def cross_branch_busy(db, tenant, staff_ids, start, end):
    """Return only time summaries for the same verified identities in this spa."""
    from datetime import timedelta
    from types import SimpleNamespace
    result={sid:[] for sid in staff_ids}
    spa=await tenant_spa(db,tenant.id)
    links=(await db.execute(select(BranchMembership).where(BranchMembership.tenant_id==tenant.id,
        BranchMembership.user_id.in_(staff_ids)))).scalars().all()
    identities={link.account_id:link.user_id for link in links}
    others=(await db.execute(select(Tenant).where(Tenant.spa_id==spa.id,Tenant.id!=tenant.id))).scalars().all()
    for other in others:
        await set_tenant_context(db,other.id)
        rows=(await db.execute(select(Booking.id,Booking.start_time,Booking.end_time,BranchMembership.account_id)
            .join(BranchMembership,(BranchMembership.user_id==Booking.staff_id)&(BranchMembership.tenant_id==other.id))
            .where(Booking.tenant_id==other.id,BranchMembership.account_id.in_(identities),Booking.status!=BookingStatus.CANCELLED,
                Booking.start_time<end+timedelta(minutes=tenant.buffer_minutes),
                Booking.end_time>start-timedelta(minutes=other.buffer_minutes)))).all()
        for row in rows:
            result[identities[row.account_id]].append(SimpleNamespace(id=row.id,start_time=row.start_time,end_time=row.end_time,
                buffer_minutes=other.buffer_minutes))
    await set_tenant_context(db,tenant.id)
    return result
