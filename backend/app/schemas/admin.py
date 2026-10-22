import uuid
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.models.models import PackageStatus, UserRole
from app.schemas.auth import _check_phone


# ---------- Tenant ----------
class TenantDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None
    theme_color: Optional[str] = None
    open_time: time
    close_time: time
    buffer_minutes: int
    status: str


class TenantUpdate(BaseModel):
    logo_data: Optional[str] = Field(default=None, max_length=360000)
    @field_validator("contact_phone")
    @classmethod
    def contact(cls, value):
        return _check_phone(value) if value else None

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    address: Optional[str] = Field(default=None, max_length=500)
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    theme_color: Optional[str] = Field(default=None, max_length=20)
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    buffer_minutes: Optional[int] = Field(default=None, ge=0, le=180)


# ---------- Service ----------
class ServiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(gt=0, le=1440)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    is_package: bool = False
    total_sessions: int = Field(default=1, ge=1, le=1000)
    is_active: bool = True


class ServiceCreate(ServiceBase):
    @model_validator(mode="after")
    def _single_has_one_session(self) -> "ServiceCreate":
        if not self.is_package:
            self.total_sessions = 1
        return self


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0, le=1440)
    price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_package: Optional[bool] = None
    total_sessions: Optional[int] = Field(default=None, ge=1, le=1000)
    is_active: Optional[bool] = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: Decimal
    is_package: bool
    total_sessions: int
    is_active: bool


class ServiceDeleteOut(BaseModel):
    id: uuid.UUID
    deleted: bool
    mode: str  # "hard" | "soft"


# ---------- Public ----------
class PublicStaffOut(BaseModel):
    id: uuid.UUID
    full_name: str


class PublicTenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None
    theme_color: Optional[str] = None
    open_time: time
    close_time: time
    buffer_minutes: int
    services: List[ServiceOut]
    staff: List[PublicStaffOut] = Field(default_factory=list)


# ---------- Users (staff / customer) ----------
class UserDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    role: UserRole
    full_name: str
    phone_number: str
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    assigned_staff_id: Optional[uuid.UUID] = None


class StaffCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str
    password: str = Field(min_length=6, max_length=128)
    notes: Optional[str] = None

    _phone = field_validator("phone_number")(_check_phone)


class StaffUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    phone_number: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _check_phone(v)


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str
    notes: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)

    _phone = field_validator("phone_number")(_check_phone)


class CustomerAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assigned_staff_id: Optional[uuid.UUID]


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    notes: Optional[str] = None


# ---------- Staff schedules ----------
class ScheduleItem(BaseModel):
    day_of_week: int = Field(ge=0, le=6)  # 0=CN .. 6=Thứ 7
    start_time: time
    end_time: time
    is_day_off: bool = False

    @model_validator(mode="after")
    def _range(self) -> "ScheduleItem":
        if not self.is_day_off and self.end_time <= self.start_time:
            raise ValueError("end_time phải lớn hơn start_time")
        return self


class ScheduleReplace(BaseModel):
    schedules: List[ScheduleItem] = Field(max_length=7)

    @model_validator(mode="after")
    def _unique_days(self) -> "ScheduleReplace":
        days = [s.day_of_week for s in self.schedules]
        if len(days) != len(set(days)):
            raise ValueError("day_of_week bị trùng")
        return self


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    staff_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    is_day_off: bool


# ---------- Customer packages ----------
class CustomerPackageCreate(BaseModel):
    customer_id: uuid.UUID
    service_id: uuid.UUID
    package_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    total_sessions: Optional[int] = Field(default=None, ge=1, le=1000)
    expiry_date: Optional[datetime] = None

    @field_validator("expiry_date")
    @classmethod
    def _aware_expiry(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
        return value.astimezone(timezone.utc)


class CustomerPackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    service_id: uuid.UUID
    package_name: str
    purchase_price: Optional[Decimal] = None
    total_sessions: int
    used_sessions: int
    expiry_date: Optional[datetime] = None
    status: PackageStatus
    created_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def remaining_sessions(self) -> int:
        return self.total_sessions - self.used_sessions


class MyCustomerPackageOut(CustomerPackageOut):
    reserved_sessions: int
    available_sessions: int
