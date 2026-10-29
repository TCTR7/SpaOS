import asyncio
import uuid
from datetime import datetime, timedelta
import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import Spa, StaffAssignment
from app.services.assignment_service import TZ
from tests.test_booking_concurrency import _setup_spa, _body, B
from tests.test_branches import new_branch


def week(tid, *, effective=None):
    return {"effective_from": effective or datetime.now(TZ).date().isoformat(), "days": [
        {"weekday": d, "tenant_id": tid, "start_time": "09:00", "end_time": "20:00"} for d in range(7)]}


@pytest.mark.asyncio
async def test_brands_directory_and_owner_isolation(client):
    a, b = await _setup_spa(client), await _setup_spa(client)
    sa = (await client.get(B+"/spas/me", headers=a["ah"])).json()
    sb = (await client.get(B+"/spas/me", headers=b["ah"])).json()
    assert sa["id"] != sb["id"]
    assert (await client.patch(B+"/spas/me", headers=a["ah"], json={"name":"Spa Sen", "theme_color":"#116633"})).status_code == 200
    directory = (await client.get(B+"/branches/public", params={"spa_slug":sa["slug"]})).json()
    assert directory["brand_name"] == "Spa Sen" and len(directory["branches"]) == 1
    assert (await client.get(B+"/branches/public")).json()["branches"] == []
    assert (await client.get(B+"/spas/me", headers=b["ah"])).json()["theme_color"] != "#116633"
    assert (await client.post(B+"/branches/"+directory["branches"][0]["id"]+"/switch", headers=b["ah"])).status_code == 404
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(Spa))).scalars().all() == []
        assert (await db.execute(select(StaffAssignment))).scalars().all() == []


@pytest.mark.asyncio
async def test_assignment_day_changes_slots_and_login(client):
    c = await _setup_spa(client)
    second, second_h = await new_branch(client, c)
    sid, tid = c["staff"][0], second["tenant"]["id"]
    grant = await client.post(B+f"/branches/{tid}/staff-access", headers=c["ah"], json={"source_staff_id":sid})
    assert grant.status_code == 201, grant.text
    aid = (await client.get(B+f"/workforce/staff/{sid}", headers=c["ah"])).json()
    origin = next(x["id"] for x in aid["branches"] if x["id"] != tid)
    days = week(origin)
    today = datetime.now(TZ).date()
    days["days"][(today.weekday()+1)%7]["tenant_id"] = tid
    assert (await client.put(B+f"/workforce/staff/{sid}/week", headers=c["ah"], json=days)).status_code == 200
    tomorrow = today+timedelta(days=1)
    response = await client.put(B+f"/workforce/staff/{sid}/day", headers=c["ah"], json={"day":str(tomorrow),"tenant_id":tid,"start_time":"09:00","end_time":"18:00"})
    assert response.status_code == 200, response.text
    public = await client.get(B+"/public/tenants/"+c["slug"], params={"day":str(tomorrow)})
    assert all(row["id"] != sid for row in public.json()["staff"])
    params={"date":str(tomorrow), "staff_id":sid, "service_ids":[c["s60"]["id"]]}
    assert (await client.get(B+"/bookings/available-slots",headers=c["ch"],params=params)).json()["slots"] == []
    # The selected default differs from today's assigned workplace.
    user = (await client.get(B+"/staff",headers=c["ah"])).json()[0]
    login=await client.post(B+"/auth/login",json={"phone_number":user["phone_number"],"password":"secret123"})
    assert login.status_code == 200 and login.json()["user"]["tenant_id"] == tid


@pytest.mark.asyncio
async def test_booking_schedule_race_never_leaves_wrong_workplace(client):
    c=await _setup_spa(client)
    second,_=await new_branch(client,c)
    sid,tid=c["staff"][0],second["tenant"]["id"]
    assert (await client.post(B+f"/branches/{tid}/staff-access",headers=c["ah"],json={"source_staff_id":sid})).status_code==201
    day=datetime.now(TZ).date()+timedelta(days=3)
    async def book():
        return await client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T10:00:00+07:00",[c["s60"]],sid))
    async def change():
        return await client.put(B+f"/workforce/staff/{sid}/day",headers=c["ah"],json={"day":str(day),"tenant_id":tid,"start_time":"09:00","end_time":"18:00"})
    booked,changed=await asyncio.gather(book(),change())
    assert sorted([booked.status_code,changed.status_code]) in ([200,409],[201,409]), (booked.text,changed.text)
    if booked.status_code==201:
        assert changed.status_code==409
        assert (await change()).status_code==409


@pytest.mark.asyncio
async def test_limits_and_staff_create_grants_are_atomic(client):
    c=await _setup_spa(client)
    second,_=await new_branch(client,c)
    assert (await client.post(B+"/branches",headers=c["ah"],json={"name":"Third"})).status_code==409
    before=len((await client.get(B+"/staff",headers=c["ah"])).json())
    bad=await client.post(B+"/staff",headers=c["ah"],json={"full_name":"Atomic", "phone_number":"09"+str(uuid.uuid4().int)[:8],"password":"Secret@123","branch_ids":[str(uuid.uuid4())]})
    assert bad.status_code==403
    assert len((await client.get(B+"/staff",headers=c["ah"])).json())==before
    spa=(await client.get(B+"/spas/me",headers=c["ah"])).json()
    assert spa["plan"]["staff"]==before


@pytest.mark.asyncio
async def test_workforce_cannot_assign_foreign_branch_or_escalate_staff(client):
    a,b=await _setup_spa(client),await _setup_spa(client)
    foreign=(await client.get(B+"/auth/me",headers=b["ah"])).json()["tenant"]["id"]
    response=await client.put(B+f"/workforce/staff/{a['staff'][0]}/week",headers=a["ah"],json=week(foreign))
    assert response.status_code==422
    assert (await client.get(B+f"/workforce/staff/{a['staff'][0]}",headers=b["ah"])).status_code==409


@pytest.mark.asyncio
async def test_transfer_requires_handover_and_revokes_old_token(client):
    c=await _setup_spa(client)
    second,_=await new_branch(client,c)
    sid,tid=c["staff"][0],second["tenant"]["id"]
    day=datetime.now(TZ).date()+timedelta(days=3)
    staff=(await client.get(B+"/staff",headers=c["ah"])).json()[0]
    login=(await client.post(B+"/auth/login",json={"phone_number":staff["phone_number"],"password":"secret123"})).json()
    old={"Authorization":"Bearer "+login["access_token"]}
    booked=await client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T10:00:00+07:00",[c["s60"]],sid))
    assert booked.status_code==201
    transfer={"branch_ids":[tid],"default_branch_id":tid}
    assert (await client.put(B+f"/workforce/staff/{sid}/access",headers=c["ah"],json=transfer)).status_code==409
    assert (await client.get(B+"/auth/me",headers=old)).status_code==200
    assert (await client.patch(B+"/bookings/"+booked.json()["id"]+"/status",headers=c["ah"],json={"status":"CANCELLED"})).status_code==200
    replacement=await client.post(B+"/staff",headers=c["ah"],json={"full_name":"Bàn giao QA","phone_number":"09"+str(uuid.uuid4().int)[-8:],"password":"Secret@123"})
    assert replacement.status_code==201
    assert (await client.patch(B+"/customers/"+c["customer_id"]+"/assignment",headers=c["ah"],json={"assigned_staff_id":replacement.json()["id"]})).status_code==200
    response=await client.put(B+f"/workforce/staff/{sid}/access",headers=c["ah"],json=transfer)
    assert response.status_code==200,response.text
    assert (await client.get(B+"/auth/me",headers=old)).status_code==401
    resolved=await client.post(B+"/auth/resolve",headers=old)
    assert resolved.status_code==200 and resolved.json()["user"]["tenant_id"]==tid
    # Credential reset must also invalidate resolution from the retired branch.
    local=(await client.get(B+"/staff",headers={"Authorization":"Bearer "+(await client.post(B+f"/branches/{tid}/switch",headers=c["ah"])).json()["access_token"]})).json()[0]
    second_h={"Authorization":"Bearer "+(await client.post(B+f"/branches/{tid}/switch",headers=c["ah"])).json()["access_token"]}
    reset=await client.patch(B+f"/staff/{local['id']}/account",headers=second_h,json={"current_password":"secret123","phone_number":staff["phone_number"],"password":"Changed@123"})
    assert reset.status_code==200,reset.text
    assert (await client.post(B+"/auth/resolve",headers=old)).status_code==401
    latest=await client.post(B+"/auth/login",json={"phone_number":staff["phone_number"],"password":"Changed@123"})
    assert latest.status_code==200 and latest.json()["user"]["tenant_id"]==tid
    assert (await client.get(B+"/bookings/"+booked.json()["id"],headers=c["ah"])).json()["status"]=="CANCELLED"


@pytest.mark.asyncio
async def test_tenth_staff_slot_is_serialized_and_phone_normalized(client):
    c=await _setup_spa(client,staff_count=9)
    async def add():
        return await client.post(B+"/staff",headers=c["ah"],json={"full_name":"Limit QA","phone_number":"09"+str(uuid.uuid4().int)[-8:],"password":"Secret@123"})
    responses=await asyncio.gather(add(),add())
    assert sorted(r.status_code for r in responses)==[201,409]
    assert (await client.get(B+"/spas/me",headers=c["ah"])).json()["plan"]["staff"]==10
    from app.schemas.auth import _check_phone
    assert _check_phone("+84 901-234-567")=="0901234567"


@pytest.mark.asyncio
async def test_weekly_edit_checks_far_future_bookings(client):
    c=await _setup_spa(client)
    day=datetime.now(TZ).date()+timedelta(days=90)
    sid=c["staff"][0]
    response=await client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T10:00:00+07:00",[c["s60"]],sid))
    assert response.status_code==201,response.text
    rows=[{"weekday":i,"tenant_id":None} for i in range(7)]
    changed=await client.put(B+f"/workforce/staff/{sid}/week",headers=c["ah"],json={"effective_from":str(datetime.now(TZ).date()),"days":rows})
    assert changed.status_code==409
    existing=(await client.get(B+f"/workforce/staff/{sid}",headers=c["ah"])).json()["assignments"]
    assert any(row["tenant_id"] for row in existing)


@pytest.mark.asyncio
async def test_queued_staff_write_rechecks_revocation_after_workforce_lock(client,monkeypatch):
    from app.services import assignment_service
    from app.models.models import User
    from app.core.database import set_tenant_context
    c=await _setup_spa(client)
    sid=c["staff"][0]
    staff=(await client.get(B+"/staff",headers=c["ah"])).json()[0]
    old=(await client.post(B+"/auth/login",json={"phone_number":staff["phone_number"],"password":"secret123"})).json()
    tid=uuid.UUID(old["user"]["tenant_id"])
    entered=asyncio.Event()
    original=assignment_service.lock_workforce
    async def observed(db,tenant_id):
        entered.set()
        await original(db,tenant_id)
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db,tid)
        await original(db,tid)
        monkeypatch.setattr(assignment_service,"lock_workforce",observed)
        pending=asyncio.create_task(client.post(B+"/customers",headers={"Authorization":"Bearer "+old["access_token"]},
            json={"full_name":"Must not be created","phone_number":"09"+str(uuid.uuid4().int)[-8:]}))
        try:
            await asyncio.wait_for(entered.wait(),5)
            user=(await db.execute(select(User).where(User.tenant_id==tid,User.id==uuid.UUID(sid)))).scalar_one()
            user.is_active=False
            await db.commit()
            response=await asyncio.wait_for(pending,10)
            assert response.status_code==401,response.text
        finally:
            if not pending.done():pending.cancel()


@pytest.mark.asyncio
async def test_assignment_database_constraints_and_runtime_rls(client):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from app.services.spa_service import spa_context
    from app.core.database import set_tenant_context
    a,b=await _setup_spa(client),await _setup_spa(client)
    w=(await client.get(B+f"/workforce/staff/{a['staff'][0]}",headers=a["ah"])).json()
    me=(await client.get(B+"/auth/me",headers=a["ah"])).json()
    foreign=(await client.get(B+"/auth/me",headers=b["ah"])).json()
    async with AsyncSessionLocal() as db:
        role=(await db.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"))).one()
        assert not role.rolsuper and not role.rolbypassrls
        await set_tenant_context(db,uuid.UUID(me["tenant"]["id"]))
        await spa_context(db,uuid.UUID(me["spa"]["id"]))
        visible=(await db.execute(select(Spa.id))).scalars().all()
        assert visible==[uuid.UUID(me["spa"]["id"])]
        base=dict(spa_id=uuid.UUID(me["spa"]["id"]),account_id=uuid.UUID(w["account_id"]),effective_from=datetime.now(TZ).date())
        invalid=[dict(weekday=1,tenant_id=uuid.UUID(foreign["tenant"]["id"]),start_time=datetime.strptime("09:00","%H:%M").time(),end_time=datetime.strptime("18:00","%H:%M").time()),
            dict(weekday=None,day=None),dict(weekday=2,tenant_id=uuid.UUID(me["tenant"]["id"]),start_time=datetime.strptime("09:00","%H:%M").time(),end_time=None)]
        for values in invalid:
            with pytest.raises(IntegrityError):
                async with db.begin_nested():
                    db.add(StaffAssignment(**base,**values));await db.flush()


@pytest.mark.asyncio
async def test_buffer_across_midnight_when_next_day_is_another_branch(client):
    c=await _setup_spa(client)
    branch,bh=await new_branch(client,c)
    tid,sid=branch["tenant"]["id"],c["staff"][0]
    grant=await client.post(B+f"/branches/{tid}/staff-access",headers=c["ah"],json={"source_staff_id":sid})
    assert grant.status_code==201
    target_staff=grant.json()["id"]
    for headers,buffer in ((c["ah"],20),(bh,0)):
        assert (await client.patch(B+"/tenants/me",headers=headers,json={"open_time":"00:00","close_time":"23:59","buffer_minutes":buffer})).status_code==200
    origin=(await client.get(B+"/auth/me",headers=c["ah"])).json()["tenant"]["id"]
    day=datetime.now(TZ).date()+timedelta(days=5)
    for d,place in ((day,origin),(day+timedelta(days=1),tid)):
        assert (await client.put(B+f"/workforce/staff/{sid}/day",headers=c["ah"],json={"day":str(d),"tenant_id":place,"start_time":"00:00","end_time":"23:59"})).status_code==200
    first=await client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T23:29:00+07:00",[c["s30"]],sid))
    assert first.status_code==201,first.text
    service=(await client.post(B+"/services",headers=bh,json={"name":"Next day","duration_minutes":30,"price":100000})).json()
    customer=(await client.post(B+"/customers",headers=bh,json={"full_name":"Next branch QA","phone_number":"09"+str(uuid.uuid4().int)[-8:]})).json()
    next_day=day+timedelta(days=1)
    body=_body(f"{next_day}T00:00:00+07:00",[service],target_staff,customer_id=customer["id"])
    assert (await client.post(B+"/bookings",headers=bh,json=body)).status_code==409
    slots=(await client.get(B+"/bookings/available-slots",headers=bh,params={"date":str(next_day),"service_ids":[service["id"]],"staff_id":target_staff})).json()["slots"]
    assert slots[0]["start_time"].startswith(f"{next_day}T00:30:00")


@pytest.mark.asyncio
async def test_spa_images_are_atomic_and_brand_patch_preserves_omitted_assets(client):
    import base64
    from tests.test_staff_profile import _png
    c=await _setup_spa(client)
    image=_png(512,512)
    changed=await client.patch(B+"/spas/me",headers=c["ah"],json={"name":"Images QA","theme_color":"#116633",
        "logo_data":base64.b64encode(image).decode(),"cover_data":base64.b64encode(image).decode()})
    assert changed.status_code==200,changed.text
    brand=changed.json()
    for field in ("logo_url","cover_url"):
        response=await client.get(brand[field])
        assert response.status_code==200 and response.content==image
        assert response.headers["x-content-type-options"]=="nosniff"
    rejected=await client.patch(B+"/spas/me",headers=c["ah"],json={"name":"Must rollback","theme_color":"#116633","logo_data":"invalid"})
    assert rejected.status_code==422
    assert (await client.get(B+"/spas/me",headers=c["ah"])).json()["name"]=="Images QA"
    updated=await client.patch(B+"/spas/me",headers=c["ah"],json={"name":"Renamed QA","theme_color":"#2563eb"})
    assert updated.status_code==200 and updated.json()["cover_url"]==brand["cover_url"]
    assert updated.json()["slug"]==brand["slug"]


@pytest.mark.asyncio
async def test_remove_daily_exception_restores_week_without_moving_existing_bookings(client):
    c=await _setup_spa(client)
    sid=c["staff"][0]
    day=datetime.now(TZ).date()+timedelta(days=5)
    path=B+f"/workforce/staff/{sid}/day"
    assert (await client.put(path,headers=c["ah"],json={"day":str(day),"tenant_id":None})).status_code==200
    params={"date":str(day),"service_ids":[c["s30"]["id"]],"staff_id":sid}
    assert (await client.get(B+"/bookings/available-slots",headers=c["ch"],params=params)).json()["slots"]==[]
    assert (await client.delete(path+"/"+str(day),headers=c["ah"])).status_code==200
    assert (await client.get(B+"/bookings/available-slots",headers=c["ch"],params=params)).json()["slots"]
    assert (await client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T10:00:00+07:00",[c["s30"]],sid))).status_code==201
    assert (await client.put(path,headers=c["ah"],json={"day":str(day),"tenant_id":None})).status_code==409


@pytest.mark.asyncio
async def test_revocation_preserves_newer_week_at_remaining_branch(client):
    from datetime import date, time
    from sqlalchemy import delete
    from app.services.spa_service import tenant_spa
    from app.services.assignment_service import staff_account
    from app.core.database import set_tenant_context
    c=await _setup_spa(client)
    second,_=await new_branch(client,c)
    sid,tid=c["staff"][0],second["tenant"]["id"]
    assert (await client.post(B+f"/branches/{tid}/staff-access",headers=c["ah"],json={"source_staff_id":sid})).status_code==201
    me=(await client.get(B+"/auth/me",headers=c["ah"])).json()
    origin=uuid.UUID(me["tenant"]["id"])
    today=datetime.now(TZ).date()
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db,origin)
        spa=await tenant_spa(db,origin)
        aid=await staff_account(db,origin,uuid.UUID(sid))
        await db.execute(delete(StaffAssignment).where(StaffAssignment.spa_id==spa.id,StaffAssignment.account_id==aid))
        for weekday in range(7):
            for effective,branch in [(date(1970,1,1),origin),(today-timedelta(days=1),uuid.UUID(tid))]:
                db.add(StaffAssignment(spa_id=spa.id,account_id=aid,tenant_id=branch,weekday=weekday,
                    effective_from=effective,start_time=time(9),end_time=time(18)))
        await db.commit()
    changed=await client.put(B+f"/workforce/staff/{sid}/access",headers=c["ah"],json={"branch_ids":[tid],"default_branch_id":tid})
    assert changed.status_code==200,changed.text
    token=(await client.post(B+f"/branches/{tid}/switch",headers=c["ah"])).json()["access_token"]
    local=(await client.get(B+"/staff",headers={"Authorization":"Bearer "+token})).json()[0]
    schedule=(await client.get(B+f"/workforce/staff/{local['id']}",headers={"Authorization":"Bearer "+token})).json()
    for weekday in range(7):
        active=max((r for r in schedule["assignments"] if r["weekday"]==weekday and r["effective_from"]<=str(today)),key=lambda r:r["effective_from"])
        assert active["tenant_id"]==tid


@pytest.mark.asyncio
async def test_branch_pause_handover_scope_and_reactivation_limit(client):
    c=await _setup_spa(client)
    second,bh=await new_branch(client,c)
    tid=second["tenant"]["id"]
    origin=(await client.get(B+"/auth/me",headers=c["ah"])).json()["tenant"]["id"]
    status=lambda ident:B+f"/branches/{ident}/status"
    assert (await client.patch(status(origin),headers=c["ah"],json={"status":"INACTIVE"})).status_code==409
    day=datetime.now(TZ).date()+timedelta(days=3)
    booked=await client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T10:00:00+07:00",[c["s60"]],c["staff"][0]))
    assert booked.status_code==201
    assert (await client.patch(status(origin),headers=bh,json={"status":"INACTIVE"})).status_code==409
    assert (await client.patch(B+"/bookings/"+booked.json()["id"]+"/status",headers=c["ah"],json={"status":"CANCELLED"})).status_code==200
    assert (await client.patch(B+"/customers/"+c["customer_id"]+"/assignment",headers=c["ah"],json={"assigned_staff_id":c["staff"][0]})).status_code==200
    assert (await client.patch(status(origin),headers=bh,json={"status":"INACTIVE"})).status_code==409
    assert (await client.patch(B+"/customers/"+c["customer_id"]+"/assignment",headers=c["ah"],json={"assigned_staff_id":None})).status_code==200
    stopped=await client.patch(status(origin),headers=bh,json={"status":"INACTIVE"})
    assert stopped.status_code==200,stopped.text
    assert (await client.get(B+"/auth/me",headers=c["ah"])).status_code==401
    resolved=await client.post(B+"/auth/resolve",headers=c["ah"])
    assert resolved.status_code==200 and resolved.json()["user"]["tenant_id"]==tid
    managed=(await client.get(B+"/branches/manage",headers=bh)).json()
    assert len(managed)==2 and next(r for r in managed if r["tenant"]["id"]==origin)["tenant"]["status"]=="INACTIVE"
    third=await client.post(B+"/branches",headers=bh,json={"name":"Third active"})
    assert third.status_code==201
    assert (await client.patch(status(origin),headers=bh,json={"status":"ACTIVE"})).status_code==409
    assert (await client.patch(status(third.json()["tenant"]["id"]),headers=bh,json={"status":"INACTIVE"})).status_code==200
    assert (await client.patch(status(origin),headers=bh,json={"status":"ACTIVE"})).status_code==200
    # No business record was deleted or moved while paused.
    assert (await client.get(B+"/customers/"+c["customer_id"],headers=c["ah"])).status_code==200
    assert (await client.get(B+"/bookings/"+booked.json()["id"],headers=c["ah"])).json()["status"]=="CANCELLED"
    other=await _setup_spa(client)
    assert (await client.patch(status(origin),headers=other["ah"],json={"status":"INACTIVE"})).status_code==404
    assert (await client.get(B+"/branches/manage",headers=c["ch"])).status_code==403


@pytest.mark.asyncio
async def test_booking_and_branch_pause_are_serialized(client):
    c=await _setup_spa(client)
    _,bh=await new_branch(client,c)
    origin=(await client.get(B+"/auth/me",headers=c["ah"])).json()["tenant"]["id"]
    day=datetime.now(TZ).date()+timedelta(days=3)
    booked,closed=await asyncio.gather(
        client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T10:00:00+07:00",[c["s60"]],c["staff"][0])),
        client.patch(B+f"/branches/{origin}/status",headers=bh,json={"status":"INACTIVE"}))
    assert (booked.status_code,closed.status_code) in [(201,409),(401,200)],(booked.text,closed.text)


@pytest.mark.asyncio
async def test_completed_visit_keeps_one_workplace_for_the_whole_day(client):
    c=await _setup_spa(client)
    second,_=await new_branch(client,c)
    sid,tid=c["staff"][0],second["tenant"]["id"]
    assert (await client.post(B+f"/branches/{tid}/staff-access",headers=c["ah"],json={"source_staff_id":sid})).status_code==201
    day=datetime.now(TZ).date()+timedelta(days=3)
    booked=await client.post(B+"/bookings",headers=c["ch"],json=_body(f"{day}T10:00:00+07:00",[c["s60"]],sid))
    assert booked.status_code==201
    bid=booked.json()["id"]
    for state in ["CONFIRMED","IN_PROGRESS","COMPLETED"]:
        response=await client.patch(B+f"/bookings/{bid}/status",headers=c["ah"],json={"status":state})
        assert response.status_code==200,response.text
    moved=await client.put(B+f"/workforce/staff/{sid}/day",headers=c["ah"],json={"day":str(day),"tenant_id":tid,"start_time":"09:00","end_time":"18:00"})
    assert moved.status_code==409,moved.text
    # A different local day remains independently assignable.
    next_day=day+timedelta(days=1)
    assert (await client.put(B+f"/workforce/staff/{sid}/day",headers=c["ah"],json={"day":str(next_day),"tenant_id":tid,"start_time":"09:00","end_time":"18:00"})).status_code==200
