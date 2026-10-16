"""notifications + push_subscriptions (RLS)

Revision ID: 0002_notifications
Revises: 0001_initial
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_notifications"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

TENANT_TABLES = ["push_subscriptions", "notifications"]


def _base_cols():
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        *_base_cols(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.String(500)),
        sa.UniqueConstraint("tenant_id", "user_id", "endpoint", name="uq_push_subscriptions_user_endpoint"),
    )
    op.create_index("ix_push_subscriptions_tenant_id", "push_subscriptions", ["tenant_id"])
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    op.create_table(
        "notifications",
        *_base_cols(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="SET NULL")),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "is_read", "created_at"])

    op.execute(
        """
        DO $$
        DECLARE r TEXT;
        BEGIN
            FOR r IN SELECT rolname FROM pg_roles WHERE rolname = 'spaos_app' LOOP
                EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I', r);
            END LOOP;
        END $$;
        """
    )

    for t in TENANT_TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {t}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            """
        )


def downgrade() -> None:
    for t in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
    op.drop_table("notifications")
    op.drop_table("push_subscriptions")
