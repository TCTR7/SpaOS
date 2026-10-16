"""initial schema + RLS

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "users",
    "staff_schedules",
    "services",
    "customer_packages",
    "bookings",
    "booking_items",
]


def _base_cols():
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _tenant_col():
    return sa.Column(
        "tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )


def _enum(name: str, values: list, default: str = None):
    return sa.Enum(*values, name=name, native_enum=False, length=20, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "tenants",
        *_base_cols(),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("theme_color", sa.String(20)),
        sa.Column("open_time", sa.Time, nullable=False, server_default=sa.text("'08:00'")),
        sa.Column("close_time", sa.Time, nullable=False, server_default=sa.text("'21:00'")),
        sa.Column("buffer_minutes", sa.Integer, nullable=False, server_default=sa.text("10")),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        *_base_cols(),
        _tenant_col(),
        sa.Column("role", _enum("ck_userrole", ["ADMIN", "STAFF", "CUSTOMER"]), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("tenant_id", "phone_number", name="uq_users_tenant_phone"),
    )

    op.create_table(
        "staff_schedules",
        *_base_cols(),
        _tenant_col(),
        sa.Column("staff_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("is_day_off", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_staff_schedules_dow"),
    )
    op.create_index("ix_staff_schedules_staff_id", "staff_schedules", ["staff_id"])

    op.create_table(
        "services",
        *_base_cols(),
        _tenant_col(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_package", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("total_sessions", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "customer_packages",
        *_base_cols(),
        _tenant_col(),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("package_name", sa.String(255), nullable=False),
        sa.Column("total_sessions", sa.Integer, nullable=False),
        sa.Column("used_sessions", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("expiry_date", sa.DateTime(timezone=True)),
        sa.Column(
            "status", _enum("ck_packagestatus", ["ACTIVE", "COMPLETED", "EXPIRED"]),
            nullable=False, server_default="ACTIVE",
        ),
        sa.CheckConstraint("used_sessions >= 0 AND used_sessions <= total_sessions", name="ck_customer_packages_sessions"),
    )
    op.create_index("ix_customer_packages_customer_id", "customer_packages", ["customer_id"])

    op.create_table(
        "bookings",
        *_base_cols(),
        _tenant_col(),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("staff_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_duration_minutes", sa.Integer, nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "status",
            _enum("ck_bookingstatus", ["PENDING", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "NO_SHOW"]),
            nullable=False, server_default="PENDING",
        ),
        sa.Column("note", sa.Text),
        sa.CheckConstraint("end_time > start_time", name="ck_bookings_time_range"),
    )
    op.create_index("ix_bookings_customer_id", "bookings", ["customer_id"])
    op.create_index("ix_bookings_staff_id", "bookings", ["staff_id"])
    op.create_index("ix_bookings_start_time", "bookings", ["start_time"])

    op.create_table(
        "booking_items",
        *_base_cols(),
        _tenant_col(),
        sa.Column("booking_id", UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "customer_package_id", UUID(as_uuid=True),
            sa.ForeignKey("customer_packages.id", ondelete="SET NULL"),
        ),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_booking_items_booking_id", "booking_items", ["booking_id"])

    for t in TENANT_TABLES:
        op.create_index(f"ix_{t}_tenant_id", t, ["tenant_id"])

    # ---- Grants cho role ứng dụng (nếu tồn tại; được tạo bởi docker/init-db.sh) ----
    op.execute(
        """
        DO $$
        DECLARE r TEXT;
        BEGIN
            FOR r IN SELECT rolname FROM pg_roles WHERE rolname = 'spaos_app' LOOP
                EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', r);
                EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I', r);
            END LOOP;
        END $$;
        """
    )

    # ---- Row-Level Security theo tenant_id ----
    # Biến session `app.current_tenant_id` được set mỗi transaction (set_config(..., true)).
    # NULLIF(...) -> nếu chưa set biến thì policy trả về NULL => không thấy/ghi được dòng nào (fail-closed).
    # FORCE: owner cũng bị áp RLS (superuser vẫn bypass; app phải dùng role non-superuser).
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
    # Lưu ý: bảng `tenants` không bật RLS vì cần tra cứu công khai theo slug trước khi có tenant context.


def downgrade() -> None:
    for t in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
    for t in ["booking_items", "bookings", "customer_packages", "services", "staff_schedules", "users", "tenants"]:
        op.drop_table(t)
