"""Read-only inventory by default. Apply only an explicit, reviewed owner mapping.

Mapping: {"spas":[{"id":"uuid","slug":"spa-sen","name":"Spa Sen",
"owner_account_id":"uuid","tenant_ids":["uuid"],"theme_color":"#116633"}]}
Never infer ownership from phone/name/password. No credentials are changed.
"""
import argparse
import asyncio
import json
import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.config import settings
from app.core.database import set_tenant_context
from app.models.models import (Tenant, LoginAccount, BranchMembership, User, UserRole,
    Spa, StaffSchedule, StaffDateOverride, StaffAssignment, Booking, BookingStatus)
from app.services.spa_service import spa_context
from app.schemas.branding import color


class Group(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: uuid.UUID
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    name: str = Field(min_length=1,max_length=255)
    owner_account_id: uuid.UUID
    tenant_ids: list[uuid.UUID] = Field(min_length=1)
    theme_color: str
    _color = field_validator("theme_color")(color)


async def inventory(db):
    tenants = (await db.execute(select(Tenant))).scalars().all()
    links, schedules, overrides, users, bookings = [], [], [], [], []
    for tenant in tenants:
        await set_tenant_context(db, tenant.id)
        for model, output in ((BranchMembership,links),(StaffSchedule,schedules),(StaffDateOverride,overrides),(User,users),(Booking,bookings)):
            output.extend((await db.execute(select(model).where(model.tenant_id == tenant.id))).scalars().all())
    accounts = (await db.execute(select(LoginAccount))).scalars().all()
    return tenants, accounts, links, schedules, overrides, users, bookings


def inventory_report(data):
    tenants, accounts, links, schedules, overrides, users, bookings = data
    roles = {u.id: u.role.value for u in users}
    normalized = defaultdict(list)
    invalid = []
    from app.schemas.auth import _check_phone
    for account in accounts:
        try:
            phone = _check_phone(account.phone_number)
            normalized[phone].append(str(account.id))
            if phone != account.phone_number: invalid.append(str(account.id))
        except ValueError:
            invalid.append(str(account.id))
    identities = {link.user_id: link.account_id for link in links}
    weekly = defaultdict(set)
    for row in schedules:
        if not row.is_day_off and row.staff_id in identities:
            weekly[(str(identities[row.staff_id]), row.day_of_week)].add(str(row.tenant_id))
    return {"read_only": True,
        "unmapped_branch_ids": [str(t.id) for t in tenants if not t.spa_id],
        "unmapped_account_ids": [str(a.id) for a in accounts if not a.spa_id],
        "memberships": [{"account_id":str(l.account_id),"tenant_id":str(l.tenant_id),"user_id":str(l.user_id),
            "is_owner":l.is_owner,"active":l.is_active,"role":roles.get(l.user_id)} for l in links],
        "phone_normalization_required_account_ids": invalid,
        "phone_conflict_account_ids": [ids for ids in normalized.values() if len(ids)>1],
        "weekly_conflicts": [{"account_id":aid,"weekday":weekday,"tenant_ids":sorted(tids)}
            for (aid,weekday),tids in weekly.items() if len(tids)>1]}


async def mapping_operation(db, payload, *, apply=False):
    groups=[Group.model_validate(row) for row in payload["spas"]]
    tenants, accounts, links, schedules, overrides, users, bookings=await inventory(db)
    from app.schemas.auth import _check_phone
    unnormalized=[str(a.id) for a in accounts if _check_phone(a.phone_number)!=a.phone_number]
    if unnormalized:
        raise ValueError("SĐT tài khoản cần chuẩn hóa/đối chiếu trước cutover: "+",".join(unnormalized))
    by_tenant={row.id:row for row in tenants}; by_account={row.id:row for row in accounts}
    destinations={}
    if len({g.id for g in groups})!=len(groups) or len({g.slug for g in groups})!=len(groups):
        raise ValueError("Spa id/slug trùng trong mapping")
    for g in groups:
        owner=by_account.get(g.owner_account_id)
        if not owner:
            raise ValueError("Không có owner_account_id đã đối chiếu")
        await spa_context(db,g.id)
        existing_spa=(await db.execute(select(Spa).where(Spa.id==g.id))).scalar_one_or_none()
        if existing_spa and (existing_spa.slug!=g.slug or any(t.spa_id==g.id and t.id not in g.tenant_ids for t in tenants)):
            raise ValueError("Spa đã tồn tại nhưng slug/phạm vi chi nhánh khác mapping được duyệt")
        for tid in g.tenant_ids:
            if tid in destinations or tid not in by_tenant:
                raise ValueError("Chi nhánh trùng/không tồn tại trong mapping")
            if not any(l.tenant_id==tid and l.account_id==owner.id and l.is_owner for l in links):
                raise ValueError("Chủ được chỉ định chưa có membership owner ở mọi chi nhánh")
            if any(l.tenant_id==tid and l.is_owner and l.account_id!=owner.id for l in links):
                raise ValueError("Chi nhánh có nhiều danh tính chủ; cần đối chiếu một chủ được duyệt")
            if by_tenant[tid].spa_id not in (None,g.id):
                raise ValueError("Mapping cố đổi spa đã được gắn")
            destinations[tid]=g.id
    unresolved=[str(t.id) for t in tenants if not t.spa_id and t.id not in destinations]
    if unresolved:
        raise ValueError("Còn chi nhánh chưa đối chiếu: "+",".join(unresolved))
    account_spas=defaultdict(set)
    for link in links:
        destination=destinations.get(link.tenant_id,by_tenant[link.tenant_id].spa_id)
        if destination:account_spas[link.account_id].add(destination)
    if any(len(values)!=1 for values in account_spas.values()):
        raise ValueError("Một danh tính nối nhiều chủ; cần đối chiếu thủ công, không tự gộp")
    for aid,ids in account_spas.items():
        if by_account[aid].spa_id not in (None,next(iter(ids))):
            raise ValueError("Account đã gắn spa khác")
    missing=[str(u.id) for u in users if u.role in (UserRole.ADMIN,UserRole.STAFF) and not any(l.user_id==u.id for l in links)]
    if missing:raise ValueError("Có tài khoản vận hành chưa liên kết: "+",".join(missing))
    # Prepare weekly/daily assignments without silently choosing one branch.
    staff_accounts={l.user_id:l.account_id for l in links}
    working=defaultdict(list)
    for row in schedules:
        if not row.is_day_off and row.start_time<row.end_time and row.staff_id in staff_accounts:
            working[(staff_accounts[row.staff_id],row.day_of_week)].append(row)
    if any(len(rows)>1 for rows in working.values()):
        raise ValueError("Lịch tuần cũ có cùng người làm nhiều chi nhánh cùng thứ; cần mapping phân công riêng trước")
    busy=defaultdict(set)
    from app.services.assignment_service import TZ
    for b in bookings:
        if b.staff_id in staff_accounts and b.status in (BookingStatus.PENDING,BookingStatus.CONFIRMED,BookingStatus.IN_PROGRESS):
            busy[(staff_accounts[b.staff_id],b.start_time.astimezone(TZ).date())].add(b.tenant_id)
    if any(len(tids)>1 for tids in busy.values()):
        raise ValueError("Lịch hẹn cũ có cùng người ở nhiều chi nhánh cùng ngày")
    if overrides:
        dated=defaultdict(list)
        for row in overrides:
            if row.staff_id in staff_accounts:
                dated[(staff_accounts[row.staff_id],row.day)].append(row)
        if any(len(rows)>1 for rows in dated.values()):
            raise ValueError("Có nhiều ngoại lệ cho cùng nhân viên/ngày; cần đối chiếu trước")
        # Dated exceptions must be checked against weekly branch allocation; no guessed priority.
        for row in overrides:
            aid=staff_accounts.get(row.staff_id)
            if not aid:continue
            other=working.get((aid,(row.day.weekday()+1)%7),[])
            if not row.is_day_off and any(r.tenant_id!=row.tenant_id for r in other):
                raise ValueError("Ngoại lệ ngày và lịch tuần khác chi nhánh; cần đối chiếu trước")
    report={"groups":len(groups),"tenants":len(destinations),"accounts":len(account_spas),"apply":apply}
    # Validate unmapped legacy bookings in dry-run too, before any writes.
    from datetime import datetime, time
    today = datetime.now(TZ).date()
    dated_rows = {(staff_accounts[r.staff_id],r.day):r for r in overrides if r.staff_id in staff_accounts}
    for booking in bookings:
        if by_tenant[booking.tenant_id].spa_id or booking.staff_id not in staff_accounts:
            continue
        if booking.status not in (BookingStatus.PENDING,BookingStatus.CONFIRMED,BookingStatus.IN_PROGRESS):
            continue
        if booking.end_time <= datetime.combine(today,time.min,TZ) and booking.status != BookingStatus.IN_PROGRESS:
            continue
        aid = staff_accounts[booking.staff_id]
        day = booking.start_time.astimezone(TZ).date()
        row = dated_rows.get((aid,day))
        if row is None:
            candidates = working.get((aid,(day.weekday()+1)%7),[])
            row = candidates[0] if candidates else None
        tenant = by_tenant[booking.tenant_id]
        if not row or row.is_day_off or row.tenant_id != booking.tenant_id or not (
            datetime.combine(day,max(row.start_time,tenant.open_time),TZ) <= booking.start_time and
            booking.end_time <= datetime.combine(day,min(row.end_time,tenant.close_time),TZ)):
            raise ValueError("Lịch hẹn legacy không khớp phân công; cần bàn giao/đối chiếu trước cutover")
    if not apply:return report
    for g in groups:
        await spa_context(db,g.id)
        old=(await db.execute(select(Spa).where(Spa.id==g.id))).scalar_one_or_none()
        if not old:
            db.add(Spa(id=g.id,slug=g.slug,name=g.name,theme_color=g.theme_color))
            await db.flush()
        for tid in g.tenant_ids:by_tenant[tid].spa_id=g.id
    for aid,ids in account_spas.items():
        account=by_account[aid]; target=next(iter(ids))
        if account.spa_id not in (None,target):raise ValueError("Account đã gắn spa khác")
        account.spa_id=target
    await db.flush()
    for (aid,weekday),rows in working.items():
        row=rows[0]; spa_id=next(iter(account_spas[aid]));await spa_context(db,spa_id)
        if not (await db.execute(select(StaffAssignment.id).where(StaffAssignment.account_id==aid,
            StaffAssignment.weekday==weekday,StaffAssignment.day.is_(None)))).first():
            db.add(StaffAssignment(spa_id=spa_id,account_id=aid,tenant_id=row.tenant_id,weekday=weekday,
                effective_from=date(1970,1,1),start_time=row.start_time,end_time=row.end_time))
    for row in overrides:
        aid=staff_accounts.get(row.staff_id)
        if not aid:continue
        spa_id=next(iter(account_spas[aid]));await spa_context(db,spa_id)
        if not (await db.execute(select(StaffAssignment.id).where(StaffAssignment.account_id==aid,StaffAssignment.day==row.day))).first():
            db.add(StaffAssignment(spa_id=spa_id,account_id=aid,tenant_id=None if row.is_day_off else row.tenant_id,
                day=row.day,effective_from=row.day,start_time=None if row.is_day_off else row.start_time,
                end_time=None if row.is_day_off else row.end_time))
    await db.flush()
    from app.services.assignment_service import verify_bookings, TZ
    for aid,ids in account_spas.items():
        spa_id=next(iter(ids));await spa_context(db,spa_id)
        spa=(await db.execute(select(Spa).where(Spa.id==spa_id))).scalar_one()
        from datetime import datetime
        await verify_bookings(db,spa,aid,datetime.now(TZ).date())
    return report


async def run(args):
    engine=create_async_engine(settings.MIGRATION_DATABASE_URL)
    try:
        async with async_sessionmaker(engine,expire_on_commit=False)() as db:
            if not args.mapping:
                data=await inventory(db)
                print(json.dumps(inventory_report(data)))
                return
            if args.apply and not args.confirm_maintenance:
                raise ValueError("--apply cần --confirm-maintenance sau backup/restore và duyệt mapping")
            payload=json.loads(Path(args.mapping).read_text(encoding="utf-8"))
            report=await mapping_operation(db,payload,apply=args.apply)
            if args.apply:await db.commit()
            print(json.dumps(report))
    finally:await engine.dispose()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping")
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--confirm-maintenance",action="store_true")
    asyncio.run(run(parser.parse_args()))
