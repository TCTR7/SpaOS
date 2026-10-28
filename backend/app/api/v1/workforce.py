import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, delete
from app.api.deps import get_current_user, get_tenant_db
from app.core.database import set_tenant_context
from app.models.models import User, UserRole, StaffAssignment
from app.schemas.workforce import WeekIn, AssignmentIn
from app.services.spa_service import tenant_spa
from app.services.assignment_service import staff_account, save_assignments, account_links, TZ
from app.services.branch_service import account_for

router = APIRouter(prefix="/workforce", tags=["workforce"])


class AccessIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    default_branch_id: uuid.UUID


@router.put("/staff/{staff_id}/access")
async def access(staff_id: uuid.UUID, body: AccessIn, actor=Depends(get_current_user), db=Depends(get_tenant_db)):
    from app.services.assignment_service import lock_workforce, check_revocation
    from app.api.v1.branches import authorized_branches, grant_staff_access
    from app.services.branch_service import account_context
    from app.models.models import LoginAccount
    origin = actor.tenant_id
    await lock_workforce(db, origin)
    _, owner, owned = await authorized_branches(db, actor)
    allowed = {t.id for link, u, t in owned if link.is_owner and u.role == UserRole.ADMIN}
    wanted = set(body.branch_ids)
    if actor.role != UserRole.ADMIN or not owner.is_owner or not wanted.issubset(allowed) or body.default_branch_id not in wanted:
        raise HTTPException(403, "Chi nhánh phải thuộc quyền chủ spa và mặc định phải được cấp")
    spa = await tenant_spa(db, origin)
    aid = await staff_account(db, origin, staff_id)
    links = await account_links(db, spa, aid)
    await set_tenant_context(db, origin)
    for tid in sorted(wanted, key=str):
        await grant_staff_access(db, actor, tid, staff_id, commit=False)
        await set_tenant_context(db, origin)
    for link, staff, tenant in links:
        if tenant.id not in wanted and link.is_active and staff.is_active:
            if tenant.id not in allowed:
                raise HTTPException(403, "Không có quyền điều chuyển chi nhánh nguồn")
            await set_tenant_context(db, tenant.id)
            await check_revocation(db, tenant.id, staff)
            link.is_active, staff.is_active = False, False
            # Membership and active state revoke business access immediately. Retain
            # the credential version so a signed session can resolve another branch.
            await db.flush()
    await account_context(db, aid)
    account = (await db.execute(select(LoginAccount).where(LoginAccount.id == aid, LoginAccount.spa_id == spa.id))).scalar_one()
    account.default_branch_id = body.default_branch_id
    await set_tenant_context(db, origin)
    from app.services.audit_service import audit
    audit(db, origin, actor, "STAFF_ACCESS_UPDATED", "user", staff_id, {"branches": [str(x) for x in sorted(wanted, key=str)]})
    await db.commit()
    return {"updated": True}


@router.get("/staff/{staff_id}")
async def read(staff_id: uuid.UUID, actor=Depends(get_current_user), db=Depends(get_tenant_db)):
    _, owner = await account_for(db, actor)
    if not (actor.role == UserRole.ADMIN and owner.is_owner) and not (actor.role == UserRole.STAFF and actor.id == staff_id):
        raise HTTPException(403, "Không có quyền xem phân công")
    aid = await staff_account(db, actor.tenant_id, staff_id)
    spa = await tenant_spa(db, actor.tenant_id)
    links = await account_links(db, spa, aid)
    rows = (await db.execute(select(StaffAssignment).where(StaffAssignment.spa_id == spa.id,
        StaffAssignment.account_id == aid).order_by(StaffAssignment.effective_from, StaffAssignment.weekday))).scalars().all()
    await set_tenant_context(db, actor.tenant_id)
    from app.services.branch_service import account_context
    from app.models.models import LoginAccount
    await account_context(db,aid)
    account=(await db.execute(select(LoginAccount).where(LoginAccount.id==aid,LoginAccount.spa_id==spa.id))).scalar_one()
    return {"account_id": aid,"default_branch_id":account.default_branch_id, "branches": [{"id": t.id, "name": t.name, "staff_id": u.id}
        for link, u, t in links if link.is_active and u.is_active and t.status == "ACTIVE"],
        "assignments": [{k: getattr(row, k) for k in ("id", "tenant_id", "day", "weekday", "effective_from", "start_time", "end_time")} for row in rows]}


@router.put("/staff/{staff_id}/week")
async def week(staff_id: uuid.UUID, body: WeekIn, actor=Depends(get_current_user), db=Depends(get_tenant_db)):
    if body.effective_from < datetime.now(TZ).date():
        raise HTTPException(422, "Chọn ngày hiệu lực từ hôm nay")
    await save_assignments(db, actor, staff_id, body.days, body.effective_from, weekly=True)
    await db.commit()
    return {"updated": True}


@router.put("/staff/{staff_id}/day")
async def day(staff_id: uuid.UUID, body: AssignmentIn, actor=Depends(get_current_user), db=Depends(get_tenant_db)):
    if not body.day or body.weekday is not None or body.day < datetime.now(TZ).date():
        raise HTTPException(422, "Chọn ngày ngoại lệ từ hôm nay, không gửi weekday")
    await save_assignments(db, actor, staff_id, [body], body.day, weekly=False)
    await db.commit()
    return {"updated": True}


@router.delete("/staff/{staff_id}/day/{day}")
async def remove_day(staff_id: uuid.UUID, day: date, actor=Depends(get_current_user), db=Depends(get_tenant_db)):
    from app.services.assignment_service import lock_workforce, verify_bookings
    if day < datetime.now(TZ).date():
        raise HTTPException(422,"Chọn ngày ngoại lệ từ hôm nay")
    await lock_workforce(db,actor.tenant_id)
    _,owner=await account_for(db,actor)
    if actor.role!=UserRole.ADMIN or not owner.is_owner:
        raise HTTPException(403,"Chỉ chủ spa được phân công chi nhánh")
    aid=await staff_account(db,actor.tenant_id,staff_id)
    spa=await tenant_spa(db,actor.tenant_id)
    await db.execute(delete(StaffAssignment).where(StaffAssignment.spa_id==spa.id,
        StaffAssignment.account_id==aid,StaffAssignment.day==day))
    await verify_bookings(db,spa,aid,day)
    await set_tenant_context(db,actor.tenant_id)
    from app.services.audit_service import audit
    audit(db,actor.tenant_id,actor,"STAFF_ASSIGNMENT_REMOVED","user",staff_id,{"day":str(day)})
    await db.commit()
    return {"removed":True}
