import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import BookingStatus


# ---------- Available slots ----------
class SlotOut(BaseModel):
    start_time: datetime  # ISO8601 kèm offset Asia/Ho_Chi_Minh (+07:00)
    end_time: datetime
    available_staff_ids: List[uuid.UUID]


class AvailableSlotsOut(BaseModel):
    date: date
    total_duration_minutes: int
    buffer_minutes: int
    slot_step_minutes: int
    slots: List[SlotOut]


# ---------- Booking ----------
class BookingItemIn(BaseModel):
    service_id: uuid.UUID
    customer_package_id: Optional[uuid.UUID] = None


class BookingCreate(BaseModel):
    start_time: datetime  # có offset; nếu không có offset sẽ hiểu là giờ Asia/Ho_Chi_Minh
    staff_id: Optional[uuid.UUID] = None  # None = "Spa tự sắp xếp"
    customer_id: Optional[uuid.UUID] = None  # bắt buộc với ADMIN/STAFF; bị bỏ qua/kiểm tra với CUSTOMER
    note: Optional[str] = Field(default=None, max_length=1000)
    items: List[BookingItemIn] = Field(min_length=1, max_length=10)


class BookingItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    customer_package_id: Optional[uuid.UUID] = None
    duration_minutes: int
    price: Decimal


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    staff_id: Optional[uuid.UUID] = None
    start_time: datetime
    end_time: datetime
    total_duration_minutes: int
    total_price: Decimal
    status: BookingStatus
    note: Optional[str] = None
    created_at: datetime
    items: List[BookingItemOut]


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingUpdate(BaseModel):
    transfer_customer: bool = False
    model_config = ConfigDict(extra="forbid")
    start_time: datetime
    staff_id: Optional[uuid.UUID] = None
    note: Optional[str] = Field(default=None, max_length=1000)
