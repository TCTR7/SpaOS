"""Shared management login and branch membership, preserve existing business IDs."""
from collections import defaultdict
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0005_branch_accounts"
down_revision = "0004_manual_payments"
branch_labels = None
depends_on = None

def timestamps():
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]

def upgrade():
    op.create_unique_constraint("uq_users_tenant_id_id", "users", ["tenant_id", "id"])
    op.create_table("login_accounts", *timestamps(),
        sa.Column("phone_number", sa.String(20), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.create_table("branch_memberships", *timestamps(),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("login_accounts.id"), nullable=False, index=True),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("account_id", "tenant_id", name="uq_account_branch"))
    # Never merge duplicate phone numbers, even when password hashes happen to match.
    conn = op.get_bind()
    by_phone = defaultdict(list)
    for tid in conn.execute(sa.text("SELECT id FROM tenants")).scalars().all():
        conn.execute(sa.text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(tid)})
        for row in conn.execute(sa.text("SELECT id,tenant_id,phone_number,password_hash,role FROM users WHERE tenant_id=:tid AND role IN ('ADMIN','STAFF')"), {"tid": tid}).mappings():
            by_phone[row["phone_number"]].append(dict(row))
    for phone, users in by_phone.items():
        if len(users) != 1:
            continue
        row, aid = users[0], uuid.uuid4()
        conn.execute(sa.text("INSERT INTO login_accounts(id,phone_number,password_hash) VALUES (:id,:phone,:hash)"),
                     {"id": aid, "phone": phone, "hash": row["password_hash"]})
        conn.execute(sa.text("INSERT INTO branch_memberships(tenant_id,user_id,account_id,is_owner) VALUES (:tid,:uid,:aid,:owner)"),
                     {"tid": row["tenant_id"], "uid": row["id"], "aid": aid, "owner": row["role"] == "ADMIN"})
    for table in ("login_accounts", "branch_memberships"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""DO $$ DECLARE r text; BEGIN
            FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
              WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
            LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO %I', r); END LOOP;
            END $$""")
    # Identity bootstrap is limited to a single phone; subsequent access uses verified account ID.
    op.execute("""CREATE POLICY account_access ON login_accounts USING (
        id = NULLIF(current_setting('app.current_account_id',true),'')::uuid OR
        phone_number = NULLIF(current_setting('app.login_phone',true),''))
        WITH CHECK (id = NULLIF(current_setting('app.current_account_id',true),'')::uuid OR
        phone_number = NULLIF(current_setting('app.login_phone',true),''))""")
    op.execute("""CREATE POLICY membership_read ON branch_memberships FOR SELECT USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid OR
        account_id = NULLIF(current_setting('app.current_account_id',true),'')::uuid)""")
    op.execute("""CREATE POLICY membership_write ON branch_memberships FOR ALL USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid)""")

def downgrade():
    op.drop_table("branch_memberships")
    op.drop_table("login_accounts")
    op.drop_constraint("uq_users_tenant_id_id", "users", type_="unique")
