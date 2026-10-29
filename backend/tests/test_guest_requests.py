import asyncio
import uuid
from datetime import datetime, timedelta
import pytest
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.models import GuestBookingRequest, User
from app.services.booking_service import TZ
from tests.test_booking_concurrency import _setup_spa, _body, B
from tests.conftest import unique_phone

def enquiry(c, **extra):
    day = datetime.now(TZ).date() + timedelta(days=3)
    return {"request_id":str(uuid.uuid4()),"token":uuid.uuid4().hex+uuid.uuid4().hex,
        "full_name":"Khách chưa có tài khoản","phone_number":unique_phone(),"service_ids":[c["s60"]["id"]],
        "start_time":f"{day}T10:00:00+07:00", **extra}

def header(c): return {"X-Tenant-Slug":c["slug"]}
def key(body): return {k:body[k] for k in ("request_id","token")}

@pytest.mark.asyncio
async def test_guest_request_capability_idempotency_and_rls(client):
    c, other = await _setup_spa(client), await _setup_spa(client)
    body = enquiry(c)
    first = await client.post(B+"/public/guest-requests",headers=header(c),json=body)
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "PENDING"
    again = await client.post(B+"/public/guest-requests",headers=header(c),json=body)
    assert again.json() == first.json()
    assert (await client.post(B+"/public/guest-requests",headers=header(c),json={**body,"full_name":"Changed"})).status_code == 409
    status = await client.post(B+"/public/guest-requests/status",headers=header(c),json=key(body))
    assert "phone_number" not in status.json() and "customer_id" not in status.json()
    assert (await client.post(B+"/public/guest-requests/status",headers=header(other),json=key(body))).status_code == 404
    assert (await client.post(B+"/public/guest-requests/status",headers=header(c),json={**key(body),"token":"0"*64})).status_code == 404
    assert (await client.get(B+"/guest-requests",headers=c["ch"])).status_code == 403
    inbox = (await client.get(B+"/guest-requests",headers=c["ah"])).json()["items"]
    assert len(inbox)==1 and "token_hash" not in inbox[0]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(GuestBookingRequest))).scalars().all() == []
        tid = (await client.get(B+"/auth/me",headers=c["ah"])).json()["tenant"]["id"]
        await set_tenant_context(db,uuid.UUID(tid))
        row = (await db.execute(select(GuestBookingRequest).where(GuestBookingRequest.tenant_id==uuid.UUID(tid)))).scalar_one()
        assert row.token_hash != body["token"]
        assert not (await db.execute(select(User).where(User.tenant_id==uuid.UUID(tid),User.phone_number==body["phone_number"]))).scalar_one_or_none()
        assert (await db.execute(text("SELECT relforcerowsecurity FROM pg_class WHERE relname='guest_booking_requests'"))).scalar_one()

@pytest.mark.asyncio
async def test_guest_confirm_once_and_no_password_or_phone_merge(client):
    c=await _setup_spa(client)
    body=enquiry(c)
    assert (await client.post(B+"/public/guest-requests",headers=header(c),json=body)).status_code==201
    row=(await client.get(B+"/guest-requests",headers=c["ah"])).json()["items"][0]
    url=B+"/guest-requests/"+row["id"]+"/decision"
    assert (await client.post(url,headers=c["ah"],json={"action":"confirm"})).status_code==422
    results=await asyncio.gather(*[client.post(url,headers=c["ah"],json={"action":"confirm","identity_verified":True}) for _ in range(2)])
    assert [r.status_code for r in results]==[200,200], [r.text for r in results]
    assert results[0].json()["booking_id"]==results[1].json()["booking_id"]
    status=(await client.post(B+"/public/guest-requests/status",headers=header(c),json=key(body))).json()
    assert status["status"]=="CONFIRMED" and status["booking_status"]=="CONFIRMED"
    assert len((await client.get(B+"/bookings",headers=c["ah"])).json())==1
    booking_id = results[0].json()["booking_id"]
    moved_start = (datetime.now(TZ).date()+timedelta(days=4)).isoformat()+"T11:00:00+07:00"
    moved = await client.patch(B+"/bookings/"+booking_id,headers=c["ah"],json={"start_time":moved_start})
    assert moved.status_code == 200, moved.text
    view = (await client.post(B+"/public/guest-requests/status",headers=header(c),json=key(body))).json()
    assert view["start_time"] == moved_start and view["booking_status"] == "CONFIRMED"
    cancelled = await client.patch(B+"/bookings/"+booking_id+"/status",headers=c["ah"],json={"status":"CANCELLED"})
    assert cancelled.status_code == 200,cancelled.text
    view = (await client.post(B+"/public/guest-requests/status",headers=header(c),json=key(body))).json()
    assert view["booking_status"] == "CANCELLED" and "đã hủy" in view["message"]

@pytest.mark.asyncio
async def test_guest_confirmation_conflict_rolls_back_request_and_customer(client):
    c=await _setup_spa(client)
    body=enquiry(c)
    assert (await client.post(B+"/public/guest-requests",headers=header(c),json=body)).status_code==201
    assert (await client.post(B+"/bookings",headers=c["ch"],json=_body(body["start_time"],[c["s60"]]))).status_code==201
    row=(await client.get(B+"/guest-requests",headers=c["ah"])).json()["items"][0]
    result=await client.post(B+"/guest-requests/"+row["id"]+"/decision",headers=c["ah"],json={"action":"confirm","identity_verified":True})
    assert result.status_code==409,result.text
    assert (await client.post(B+"/public/guest-requests/status",headers=header(c),json=key(body))).json()["status"]=="PENDING"
    customers=(await client.get(B+"/customers",headers=c["ah"],params={"q":body["phone_number"]})).json()
    assert customers==[]

@pytest.mark.asyncio
async def test_guest_confirmation_status_failure_rolls_back_entire_creation(client, monkeypatch):
    from fastapi import HTTPException
    from app.services import booking_service
    c=await _setup_spa(client)
    body=enquiry(c)
    await client.post(B+"/public/guest-requests",headers=header(c),json=body)
    row=(await client.get(B+"/guest-requests",headers=c["ah"])).json()["items"][0]
    original=booking_service.update_booking_status
    async def fail_before_commit(*args, **kwargs):
        assert kwargs.get("commit") is False
        await original(*args, **kwargs)
        raise HTTPException(409,"Chưa hoàn tất xác nhận")
    monkeypatch.setattr(booking_service,"update_booking_status",fail_before_commit)
    result=await client.post(B+"/guest-requests/"+row["id"]+"/decision",headers=c["ah"],json={"action":"confirm","identity_verified":True})
    assert result.status_code==409,result.text
    assert (await client.post(B+"/public/guest-requests/status",headers=header(c),json=key(body))).json()["status"]=="PENDING"
    assert (await client.get(B+"/customers",headers=c["ah"],params={"q":body["phone_number"]})).json()==[]
    assert (await client.get(B+"/bookings",headers=c["ah"])).json()==[]

@pytest.mark.asyncio
async def test_guest_existing_customer_requires_explicit_verified_choice(client):
    c=await _setup_spa(client)
    customers=(await client.get(B+"/customers",headers=c["ah"])).json()
    existing=next(x for x in customers if x["id"]==c["customer_id"])
    body=enquiry(c,phone_number=existing["phone_number"])
    await client.post(B+"/public/guest-requests",headers=header(c),json=body)
    row=(await client.get(B+"/guest-requests",headers=c["ah"])).json()["items"][0]
    url=B+"/guest-requests/"+row["id"]+"/decision"
    assert (await client.post(url,headers=c["ah"],json={"action":"confirm","identity_verified":True})).status_code==409
    result=await client.post(url,headers=c["ah"],json={"action":"confirm","identity_verified":True,"customer_id":c["customer_id"]})
    assert result.status_code==200,result.text

@pytest.mark.asyncio
async def test_guest_rate_limit_and_management_only_unqualified_slots(client):
    c=await _setup_spa(client)
    phone=unique_phone()
    for _ in range(3): assert (await client.post(B+"/public/guest-requests",headers=header(c),json=enquiry(c,phone_number=phone))).status_code==201
    assert (await client.post(B+"/public/guest-requests",headers=header(c),json=enquiry(c,phone_number=phone))).status_code==429
    params={"date":(datetime.now(TZ).date()+timedelta(days=3)).isoformat(),"service_ids":[c["s60"]["id"]],"all_staff":True}
    assert (await client.get(B+"/bookings/available-slots",headers=header(c),params=params)).status_code==403
    assert (await client.get(B+"/bookings/available-slots",headers=c["ah"],params=params)).status_code==200
