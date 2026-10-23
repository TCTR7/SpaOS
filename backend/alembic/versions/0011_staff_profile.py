"""Hồ sơ nhân viên: chức danh, giới thiệu, kinh nghiệm, ảnh và kỹ năng theo dịch vụ."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0011_staff_profile"
down_revision = "0010_owner_recovery"
branch_labels = None
depends_on = None


def table(name, *columns):
    op.create_table(name,
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True), *columns)
    op.execute(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY")
    op.execute(f"""CREATE POLICY tenant_isolation ON {name}
      USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
      WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)""")
    op.execute(f"""DO $$ DECLARE r text; BEGIN
      FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
        WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
      LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON {name} TO %I', r); END LOOP;
      END $$""")


def upgrade():
    op.add_column("users", sa.Column("job_title", sa.String(100)))
    op.add_column("users", sa.Column("bio", sa.Text()))
    op.add_column("users", sa.Column("experience_years", sa.Integer()))
    op.add_column("users", sa.Column("experience_detail", sa.Text()))
    op.add_column("users", sa.Column("photo_url", sa.String(500)))
    table("staff_services",
        sa.Column("staff_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.UniqueConstraint("tenant_id", "staff_id", "service_id", name="uq_staff_service"))
    table("staff_photos",
        sa.Column("staff_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_type", sa.String(20), nullable=False, server_default="image/png"),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("tenant_id", "staff_id", name="uq_staff_photo"))


def downgrade():
    op.drop_table("staff_photos")
    op.drop_table("staff_services")
    for column in ("photo_url", "experience_detail", "experience_years", "bio", "job_title"):
        op.drop_column("users", column)
