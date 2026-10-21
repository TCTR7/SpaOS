"""Role UX: contact, date overrides, recovery, booking receipts and durable notifications."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0009_role_experience"
down_revision = "0008_manual_booking_batches"
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


def uid(name, target, **kw):
    return sa.Column(name, UUID(as_uuid=True), sa.ForeignKey(target), nullable=False, **kw)


def upgrade():
    op.add_column("tenants", sa.Column("address", sa.String(500)))
    op.add_column("tenants", sa.Column("contact_phone", sa.String(20)))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    table("staff_date_overrides", uid("staff_id", "users.id"), sa.Column("day", sa.Date(), nullable=False),
      sa.Column("start_time", sa.Time(), nullable=False), sa.Column("end_time", sa.Time(), nullable=False),
      sa.Column("is_day_off", sa.Boolean(), nullable=False), sa.UniqueConstraint("tenant_id", "staff_id", "day", name="uq_staff_override_day"))
    table("tenant_logos", sa.Column("data", sa.LargeBinary(), nullable=False), sa.UniqueConstraint("tenant_id", name="uq_tenant_logo"))
    table("recovery_grants", uid("user_id", "users.id"), sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
      sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)))
    table("booking_requests", uid("actor_id", "users.id"), sa.Column("request_id", UUID(as_uuid=True), nullable=False),
      sa.Column("payload_hash", sa.String(64), nullable=False), uid("booking_id", "bookings.id"),
      sa.UniqueConstraint("tenant_id", "actor_id", "request_id", name="uq_customer_booking_request"))
    table("booking_handovers", uid("booking_id", "bookings.id"), uid("author_id", "users.id"), sa.Column("note", sa.String(1000), nullable=False),
      sa.UniqueConstraint("tenant_id", "booking_id", name="uq_booking_handover"))
    table("notification_events", uid("booking_id", "bookings.id"), uid("actor_id", "users.id"),
      sa.Column("event", sa.String(30), nullable=False), sa.Column("to_staff", sa.Boolean(), nullable=False),
      sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
      sa.Column("processed_at", sa.DateTime(timezone=True)), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("notifications", sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("notification_events.id")))
    op.create_unique_constraint("uq_event_recipient", "notifications", ["event_id", "user_id"])
    table("notification_dispatches", uid("notification_id", "notifications.id"),
      sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("push_subscriptions.id", ondelete="CASCADE"), nullable=False),
      sa.Column("url", sa.String(500), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
      sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
      sa.Column("delivered_at", sa.DateTime(timezone=True)),
      sa.UniqueConstraint("tenant_id", "notification_id", "subscription_id", name="uq_notification_dispatch"))

    op.create_index("ix_notification_events_pending", "notification_events", ["tenant_id", "next_attempt_at", "created_at"], postgresql_where=sa.text("processed_at IS NULL"))
    op.create_index("ix_notification_dispatches_pending", "notification_dispatches", ["tenant_id", "next_attempt_at", "created_at"], postgresql_where=sa.text("delivered_at IS NULL"))


def downgrade():
    op.drop_constraint("uq_event_recipient", "notifications", type_="unique")
    op.drop_column("notifications", "event_id")
    for name in ["notification_dispatches", "notification_events", "booking_handovers", "booking_requests", "recovery_grants", "tenant_logos", "staff_date_overrides"]:
        op.drop_table(name)
    op.drop_column("users", "auth_version")
    op.drop_column("tenants", "contact_phone")
    op.drop_column("tenants", "address")
