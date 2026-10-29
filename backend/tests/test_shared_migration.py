"""Rehearse the actual additive migration on a separate legacy QA database."""
import asyncio
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.models import Tenant, LoginAccount, StaffAssignment
from scripts.shared_spa_migration import mapping_operation


@pytest.mark.asyncio
async def test_legacy_mapping_rehearsal_preserves_ids_and_is_repeatable():
    name = "spaos_qa_" + uuid.uuid4().hex
    source = make_url(settings.MIGRATION_DATABASE_URL)
    admin = create_async_engine(source, isolation_level="AUTOCOMMIT")
    engine = None
    created = False
    env = dict(os.environ,
        MIGRATION_DATABASE_URL=source.set(database=name).render_as_string(hide_password=False),
        DATABASE_URL=make_url(settings.DATABASE_URL).set(database=name).render_as_string(hide_password=False))
    async def migrate(revision):
        process = await asyncio.create_subprocess_exec(sys.executable, "-m", "alembic", "upgrade", revision,
            cwd=Path(__file__).resolve().parents[1], env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.communicate()
        assert process.returncode == 0, "Disposable rehearsal schema migration failed"
    try:
        async with admin.connect() as db:
            await db.execute(text('CREATE DATABASE "' + name + '"'))
            created = True
        await migrate("0011_staff_profile")
        engine = create_async_engine(source.set(database=name))
        session = async_sessionmaker(engine, expire_on_commit=False)
        tids, aids, uids = [uuid.uuid4() for _ in range(2)], [uuid.uuid4() for _ in range(2)], [uuid.uuid4() for _ in range(6)]
        spa_id = uuid.uuid4()
        async with session() as db:
            for i, tid in enumerate(tids):
                await db.execute(text("INSERT INTO tenants(id,slug,name) VALUES (:id,:slug,:name)"),
                    {"id":tid,"slug":"legacy-"+str(i),"name":"Legacy branch "+str(i)})
            for j, aid in enumerate(aids):
                await db.execute(text("INSERT INTO login_accounts(id,phone_number,password_hash) VALUES (:id,:phone,'fixture-only')"),
                    {"id":aid,"phone":"090000900"+str(j)})
                for i, tid in enumerate(tids):
                    uid = uids[j*2+i]
                    await db.execute(text("INSERT INTO users(id,tenant_id,role,full_name,phone_number,password_hash) VALUES (:id,:tid,:role,'Legacy QA',:phone,'fixture-only')"),
                        {"id":uid,"tid":tid,"role":"ADMIN" if j==0 else "STAFF","phone":"090000900"+str(j)})
                    await db.execute(text("INSERT INTO branch_memberships(tenant_id,user_id,account_id,is_owner) VALUES (:tid,:uid,:aid,:owner)"),
                        {"tid":tid,"uid":uid,"aid":aid,"owner":j==0})
            for i, tid in enumerate(tids):
                await db.execute(text("INSERT INTO users(id,tenant_id,role,full_name,phone_number,password_hash) VALUES (:id,:tid,'CUSTOMER','Same phone, separate CRM','0900009099','fixture-only')"),
                    {"id":uids[4+i],"tid":tid})
            for weekday in range(7):
                await db.execute(text("INSERT INTO staff_schedules(tenant_id,staff_id,day_of_week,start_time,end_time) VALUES (:tid,:uid,:day,'09:00','18:00')"),
                    {"tid":tids[0],"uid":uids[2],"day":weekday})
            await db.commit()
        await migrate("head")
        payload={"spas":[{"id":str(spa_id),"slug":"legacy-reviewed","name":"Reviewed brand","theme_color":"#116633",
            "owner_account_id":str(aids[0]),"tenant_ids":[str(t) for t in tids]}]}
        async with session() as db:
            # Dry-run and incomplete mapping never attach any original data.
            bad={"spas":[{**payload["spas"][0],"tenant_ids":[str(tids[0])]}]}
            with pytest.raises(ValueError,match="chưa đối chiếu"):
                await mapping_operation(db,bad)
            await db.rollback()
            assert (await mapping_operation(db,payload))["apply"] is False
            assert all(t.spa_id is None for t in (await db.execute(select(Tenant))).scalars())
            await db.rollback()
            await mapping_operation(db,payload,apply=True)
            # Rehearse failure rollback before allowing the real commit.
            await db.rollback()
            assert all(t.spa_id is None for t in (await db.execute(select(Tenant))).scalars())
            await db.rollback()
            await mapping_operation(db,payload,apply=True)
            await db.commit()
            await mapping_operation(db,payload,apply=True)
            await db.commit()
            mismatched={"spas":[{**payload["spas"][0],"slug":"silently-renamed"}]}
            with pytest.raises(ValueError,match="khác mapping"):
                await mapping_operation(db,mismatched)
            await db.rollback()
            assert {t.id for t in (await db.execute(select(Tenant))).scalars()} == set(tids)
            assert {a.id for a in (await db.execute(select(LoginAccount))).scalars()} == set(aids)
            assert set((await db.execute(text("SELECT id FROM users"))).scalars()) == set(uids)
            assert len((await db.execute(select(StaffAssignment))).scalars().all()) == 7
            assert (await db.execute(text("SELECT count(*) FROM users WHERE role='CUSTOMER' AND phone_number='0900009099'"))).scalar_one()==2
            # Ambiguous historical schedules must fail instead of picking a branch.
            await db.execute(text("INSERT INTO staff_schedules(tenant_id,staff_id,day_of_week,start_time,end_time) VALUES (:tid,:uid,1,'09:00','18:00')"),
                {"tid":tids[1],"uid":uids[3]})
            with pytest.raises(ValueError,match="nhiều chi nhánh"):
                await mapping_operation(db,payload)
            await db.rollback()
    finally:
        if engine: await engine.dispose()
        if created:
            async with admin.connect() as db:
                await db.execute(text('DROP DATABASE "' + name + '" WITH (FORCE)'))
        await admin.dispose()
