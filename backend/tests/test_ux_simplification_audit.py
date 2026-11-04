import uuid
import pytest
from tests.test_sprint4_reports_notifications import B, _setup, _day
from tests.conftest import unique_phone


@pytest.mark.asyncio
async def test_public_staff_projection(client):
    c = await _setup(client)
    result = await client.get(f"{B}/public/tenants/{c['slug']}")
    assert result.status_code == 200, result.text
    assert len(result.json()['staff']) == 2
    assert all(set(row) == {'id', 'full_name', 'photo_url'} for row in result.json()['staff'])


@pytest.mark.asyncio
async def test_staff_batch_transfers_only_after_all_rows(client):
    c = await _setup(client)
    a, b = c['staff']
    body = dict(request_id=str(uuid.uuid4()), new_customer={'full_name': 'QA transfer', 'phone_number': unique_phone()},
                staff_id=b['id'], items=[{'service_id': c['s30']['id']}],
                start_times=[f"{_day(i)}T10:00:00+07:00" for i in (3, 4)])
    result = await client.post(B+'/bookings/manual-batches', headers=a['h'], json=body)
    assert result.status_code == 201, result.text
    assert len(result.json()['booking_ids']) == 2
    assert (await client.get(B+'/customers', headers=a['h'])).json() == []
    rows = (await client.get(B+'/customers', headers=b['h'])).json()
    assert any(row['id'] == result.json()['customer_id'] for row in rows)
    # Losing ownership still denies later replay; no reusable authorization bypass.
    assert (await client.post(B+'/bookings/manual-batches', headers=a['h'], json=body)).status_code == 404


@pytest.mark.asyncio
async def test_password_and_photo_authorization_matrix(client):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, set_tenant_context
    from app.core.security import verify_password
    from app.models.models import User, AuditLog
    from tests.test_staff_profile import _png, _b64
    c, other = await _setup(client), await _setup(client)
    a, b = c['staff']
    url = B+'/customers/'+c['customer_id']
    assert (await client.patch(url+'/assignment', headers=c['ah'], json={'assigned_staff_id':a['id']})).status_code == 200
    for headers, target in [(b['h'],c['customer_id']), (other['ah'],c['customer_id']),
                            (c['ah'],c['admin_id']), (a['h'],b['id'])]:
        assert (await client.patch(B+'/customers/'+target, headers=headers, json={'password':'audit-secret'})).status_code == 404
    for value in [None, '', 'short']:
        assert (await client.patch(url, headers=a['h'], json={'password':value})).status_code == 422
    reset = await client.patch(url, headers=a['h'], json={'password':'audit-secret'})
    assert reset.status_code == 200, reset.text
    assert 'password' not in reset.json() and 'password_hash' not in reset.json()
    assert (await client.get(B+'/auth/me', headers=c['ch'])).status_code == 401
    tid = uuid.UUID(reset.json()['tenant_id'])
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tid)
        customer = (await db.execute(select(User).where(User.tenant_id == tid, User.id == uuid.UUID(c['customer_id'])))).scalar_one()
        assert verify_password('audit-secret', customer.password_hash)
        logs = (await db.execute(select(AuditLog.details).where(AuditLog.tenant_id == tid, AuditLog.entity_id == customer.id))).scalars().all()
        assert 'audit-secret' not in str(logs)
    photo = {'data':_b64(_png())}
    photo_url = B+'/staff/'+a['id']+'/photo'
    assert (await client.post(photo_url, headers=b['h'], json=photo)).status_code == 403
    assert (await client.post(photo_url, headers=other['ah'], json=photo)).status_code == 404
    assert (await client.delete(photo_url, headers=other['ah'])).status_code == 404
    uploaded = await client.post(photo_url, headers=a['h'], json=photo)
    assert uploaded.status_code == 200, uploaded.text
    me = (await client.get(B+'/auth/me', headers=a['h'])).json()
    assert me['user']['photo_url'] == uploaded.json()['photo_url']
    public = (await client.get(B+'/public/tenants/'+c['slug'])).json()
    assert next(s for s in public['staff'] if s['id'] == a['id'])['photo_url'] == me['user']['photo_url']
    assert (await client.delete(photo_url, headers=a['h'])).status_code == 200
    assert (await client.patch(B+'/staff/'+b['id'], headers=c['ah'], json={'is_active':False})).status_code == 200
    public = (await client.get(B+'/public/tenants/'+c['slug'])).json()
    assert b['id'] not in {s['id'] for s in public['staff']}


@pytest.mark.asyncio
async def test_staff_guest_confirm_transfers_after_status_change(client):
    c = await _setup(client)
    a, b = c['staff']
    body = dict(request_id=str(uuid.uuid4()), token=uuid.uuid4().hex+uuid.uuid4().hex,
                full_name='QA guest transfer', phone_number=unique_phone(), staff_id=b['id'],
                service_ids=[c['s30']['id']], start_time=f"{_day()}T10:00:00+07:00")
    sent = await client.post(B+'/public/guest-requests', headers={'X-Tenant-Slug':c['slug']}, json=body)
    assert sent.status_code == 201, sent.text
    row = (await client.get(B+'/guest-requests', headers=a['h'])).json()['items'][0]
    result = await client.post(B+'/guest-requests/'+row['id']+'/decision', headers=a['h'], json={'action':'confirm','identity_verified':True})
    assert result.status_code == 200, result.text
    booking = await client.get(B+'/bookings/'+result.json()['booking_id'], headers=b['h'])
    assert booking.status_code == 200, booking.text
    assert booking.json()['status'] == 'CONFIRMED'
    assert (await client.get(B+'/customers', headers=a['h'])).json() == []
