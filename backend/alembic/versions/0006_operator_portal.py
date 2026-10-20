"""Private installation operator and auditable owner provisioning."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0006_operator_portal"
down_revision = "0005_branch_accounts"
branch_labels = None
depends_on = None

def timestamps():
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]

def upgrade():
    op.create_table("deployment_operators", *timestamps(),
        sa.Column("slot", sa.Integer(), nullable=False, unique=True),
        sa.Column("phone_number", sa.String(20), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint("slot = 1", name="ck_single_operator"))
    op.create_table("owner_provisions", *timestamps(),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("operator_id", UUID(as_uuid=True), sa.ForeignKey("deployment_operators.id"), nullable=False),
        sa.Column("owner_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("branch_name", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "owner_user_id"], ["users.tenant_id", "users.id"]),
        sa.UniqueConstraint("operator_id", "request_id", name="uq_owner_provision_request"))
    for table in ("deployment_operators", "owner_provisions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""DO $$ DECLARE r text; BEGIN
          FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
            WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
          LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO %I', r); END LOOP;
          END $$""")
    op.execute("""CREATE POLICY operator_identity ON deployment_operators USING (
      id = NULLIF(current_setting('app.current_operator_id',true),'')::uuid OR
      phone_number = NULLIF(current_setting('app.operator_phone',true),''))
      WITH CHECK (id = NULLIF(current_setting('app.current_operator_id',true),'')::uuid OR
      phone_number = NULLIF(current_setting('app.operator_phone',true),''))""")
    op.execute("""CREATE POLICY provision_read ON owner_provisions FOR SELECT USING (
      operator_id = NULLIF(current_setting('app.current_operator_id',true),'')::uuid OR
      tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid)""")
    op.execute("""CREATE POLICY provision_insert ON owner_provisions FOR INSERT WITH CHECK (
      operator_id = NULLIF(current_setting('app.current_operator_id',true),'')::uuid AND
      tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid)""")
    op.execute("CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON owner_provisions FOR EACH ROW EXECUTE FUNCTION spaos_reject_ledger_change()")

def downgrade():
    op.drop_table("owner_provisions")
    op.drop_table("deployment_operators")
