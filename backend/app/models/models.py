import enum
import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"


class PackageStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


def _enum(e: type) -> Enum:
    # native_enum=False -> VARCHAR + CHECK, dễ migrate hơn PG ENUM
    return Enum(e, native_enum=False, length=20, create_constraint=True, name="ck_" + e.__name__.lower())


class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantOwnedMixin:
    """Mọi bảng nghiệp vụ đều có tenant_id (được bảo vệ bởi RLS)."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    theme_color: Mapped[Optional[str]] = mapped_column(String(20))
    open_time: Mapped[time] = mapped_column(Time, nullable=False, server_default=text("'08:00'"))
    close_time: Mapped[time] = mapped_column(Time, nullable=False, server_default=text("'21:00'"))
    buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default=text("10"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")


class User(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "phone_number", name="uq_users_tenant_phone"), UniqueConstraint("tenant_id", "id", name="uq_users_tenant_id_id"))

    role: Mapped[UserRole] = mapped_column(_enum(UserRole), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    assigned_staff_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class StaffSchedule(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "staff_schedules"
    __table_args__ = (CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_staff_schedules_dow"),)

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=CN .. 6=Thứ 7
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_day_off: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))


class Service(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "services"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_package: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class CustomerPackage(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "customer_packages"
    __table_args__ = (
        CheckConstraint("used_sessions >= 0 AND used_sessions <= total_sessions", name="ck_customer_packages_sessions"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    used_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[PackageStatus] = mapped_column(
        _enum(PackageStatus), nullable=False, default=PackageStatus.ACTIVE, server_default="ACTIVE"
    )


class Booking(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (CheckConstraint("end_time > start_time", name="ck_bookings_time_range"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    staff_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default=text("0"))
    status: Mapped[BookingStatus] = mapped_column(
        _enum(BookingStatus), nullable=False, default=BookingStatus.PENDING, server_default="PENDING"
    )
    note: Mapped[Optional[str]] = mapped_column(Text)

    items: Mapped[List["BookingItem"]] = relationship(back_populates="booking", cascade="all, delete-orphan")


class BookingItem(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "booking_items"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    customer_package_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_packages.id", ondelete="SET NULL")
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default=text("0"))

    booking: Mapped["Booking"] = relationship(back_populates="items")


class PushSubscription(TimestampMixin, TenantOwnedMixin, Base):
    """Đăng ký nhận Web Push của 1 trình duyệt/PWA (PushSubscription.toJSON() của trình duyệt)."""

    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "endpoint", name="uq_push_subscriptions_user_endpoint"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))


class Notification(TimestampMixin, TenantOwnedMixin, Base):
    """Thông báo trong ứng dụng (quả chuông)."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    booking_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

class PaymentInvoice(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "payment_invoices"
    __table_args__ = (
        CheckConstraint("(booking_id IS NULL) <> (customer_package_id IS NULL)", name="ck_invoice_source"),
        CheckConstraint("amount_due >= 0", name="ck_invoice_amount"),
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    booking_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"), unique=True)
    customer_package_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_packages.id"), unique=True)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class PaymentEntry(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "payment_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_payment_idempotency"),
        CheckConstraint("method IN ('CASH','BANK_TRANSFER')", name="ck_payment_method"),
        CheckConstraint("(reversal_of IS NULL AND amount > 0) OR (reversal_of IS NOT NULL AND amount < 0)", name="ck_payment_sign"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_invoices.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reversal_of: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("payment_entries.id"), unique=True)
    note: Mapped[Optional[str]] = mapped_column(String(500))


class AuditLog(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class LoginAccount(TimestampMixin, Base):
    """Deployment-level authentication identity; no business/customer data."""
    __tablename__ = "login_accounts"
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class BranchMembership(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "branch_memberships"
    __table_args__ = (
        UniqueConstraint("account_id", "tenant_id", name="uq_account_branch"),
        UniqueConstraint("user_id", name="uq_membership_user"),
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"], ondelete="CASCADE"),
    )
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("login_accounts.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class DeploymentOperator(TimestampMixin, Base):
    """Installation identity, deliberately separate from tenant business users."""
    __tablename__ = "deployment_operators"
    __table_args__ = (CheckConstraint("slot = 1", name="ck_single_operator"),)
    slot: Mapped[int] = mapped_column(Integer, nullable=False, default=1, unique=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class OwnerProvision(TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "owner_provisions"
    __table_args__ = (
        UniqueConstraint("operator_id", "request_id", name="uq_owner_provision_request"),
        ForeignKeyConstraint(["tenant_id", "owner_user_id"], ["users.tenant_id", "users.id"]),
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_operators.id"), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)


class DeploymentBranding(TimestampMixin, Base):
    """Public deployment appearance; contains no tenant business data."""
    __tablename__ = "deployment_branding"
    __table_args__ = (
        CheckConstraint("slot = 1", name="ck_branding_singleton"),
        CheckConstraint("theme_color ~ '^#[0-9a-f]{6}$'", name="ck_branding_color"),
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False, default=1, unique=True)
    theme_color: Mapped[str] = mapped_column(String(7), nullable=False)
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployment_operators.id"), nullable=False)
