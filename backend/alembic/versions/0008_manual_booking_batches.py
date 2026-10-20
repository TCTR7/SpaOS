"""Atomic manual booking requests, isolated and durable across retries."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0008_manual_booking_batches"
down_revision = "0007_branding"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("manual_booking_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("package_ids", JSONB, nullable=False),
        sa.Column("booking_ids", JSONB, nullable=False),
        sa.UniqueConstraint("tenant_id", "actor_id", "request_id", name="uq_manual_batch_request"))
    op.execute("ALTER TABLE manual_booking_batches ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE manual_booking_batches FORCE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY tenant_isolation ON manual_booking_batches
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)""")
    op.execute("""DO $$ DECLARE r text; BEGIN
        FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
            WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
        LOOP EXECUTE format('GRANT SELECT, INSERT ON manual_booking_batches TO %I', r); END LOOP;
        END $$""")


def downgrade():
    op.drop_table("manual_booking_batches")
