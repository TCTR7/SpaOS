"""Guest enquiries are separate from confirmed calendar bookings."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0013_guest_requests"
down_revision = "0012_shared_spas"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("guest_booking_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("note", sa.String(950)),
        sa.Column("service_ids", JSONB, nullable=False),
        sa.Column("staff_id", UUID(as_uuid=True)),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("booking_id", UUID(as_uuid=True), sa.ForeignKey("bookings.id")),
        sa.UniqueConstraint("tenant_id", "request_id", name="uq_guest_request"),
        sa.CheckConstraint("status IN ('PENDING','CONFIRMED','REJECTED')", name="ck_guest_request_status"))
    op.execute("ALTER TABLE guest_booking_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE guest_booking_requests FORCE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY tenant_isolation ON guest_booking_requests
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)""")
    op.execute("""DO $$ DECLARE r text; BEGIN
        FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
            WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
        LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE ON guest_booking_requests TO %I', r); END LOOP;
        END $$""")

def downgrade():
    op.drop_table("guest_booking_requests")
