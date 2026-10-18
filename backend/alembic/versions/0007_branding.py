"""Deployment-wide public color, writable only by the private operator."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0007_branding"
down_revision = "0006_operator_portal"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("deployment_branding",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("slot", sa.Integer(), nullable=False, unique=True),
        sa.Column("theme_color", sa.String(7), nullable=False),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("deployment_operators.id"), nullable=False),
        sa.CheckConstraint("slot=1", name="ck_branding_singleton"),
        sa.CheckConstraint("theme_color ~ '^#[0-9a-f]{6}$'", name="ck_branding_color"))
    op.execute("ALTER TABLE deployment_branding ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE deployment_branding FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY public_branding ON deployment_branding FOR SELECT USING (true)")
    check = """updated_by = NULLIF(current_setting('app.current_operator_id',true),'')::uuid
        AND EXISTS(SELECT 1 FROM deployment_operators o WHERE o.id=updated_by AND o.is_active)"""
    op.execute(f"CREATE POLICY operator_branding_insert ON deployment_branding FOR INSERT WITH CHECK ({check})")
    op.execute(f"CREATE POLICY operator_branding_update ON deployment_branding FOR UPDATE USING ({check}) WITH CHECK ({check})")
    op.execute("""DO $$ DECLARE r text; BEGIN
      FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
        WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
      LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE ON deployment_branding TO %I', r); END LOOP;
      END $$""")

def downgrade():
    op.drop_table("deployment_branding")
