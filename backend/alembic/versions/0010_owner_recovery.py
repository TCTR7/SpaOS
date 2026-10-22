"""One-time owner recovery with narrow hash bootstrap and operator issuance."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0010_owner_recovery"
down_revision = "0009_role_experience"
branch_labels = depends_on = None

def upgrade():
    op.create_table("owner_recovery_grants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("operator_id", UUID(as_uuid=True), sa.ForeignKey("deployment_operators.id"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("login_accounts.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]))
    op.execute("ALTER TABLE owner_recovery_grants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE owner_recovery_grants FORCE ROW LEVEL SECURITY")
    op.execute("""DO $$ DECLARE r text; BEGIN
      FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
      LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON owner_recovery_grants TO %I',r); END LOOP; END $$""")
    op.execute("""CREATE POLICY owner_recovery_read ON owner_recovery_grants FOR SELECT USING (
      token_hash = NULLIF(current_setting('app.owner_recovery_hash',true),'') OR
      (tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid AND operator_id = NULLIF(current_setting('app.current_operator_id',true),'')::uuid))""")
    operator = "operator_id = NULLIF(current_setting('app.current_operator_id',true),'')::uuid"
    tenant = "tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid"
    token = "token_hash = NULLIF(current_setting('app.owner_recovery_hash',true),'')"
    op.execute(f"CREATE POLICY owner_recovery_insert ON owner_recovery_grants FOR INSERT WITH CHECK ({tenant} AND {operator})")
    op.execute(f"CREATE POLICY owner_recovery_update ON owner_recovery_grants FOR UPDATE USING ({tenant} AND ({operator} OR {token})) WITH CHECK ({tenant} AND ({operator} OR {token}))")
    op.execute(f"CREATE POLICY owner_recovery_delete ON owner_recovery_grants FOR DELETE USING ({tenant} AND {operator})")

def downgrade():
    op.drop_table("owner_recovery_grants")
