import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Reports ----------
class StaffPerformanceItem(BaseModel):
    staff_id: uuid.UUID
    full_name: str
    is_active: bool
    completed_bookings_count: int
    completed_services_count: int  # tổng số booking_items đã thực hiện
    single_services_count: int  # dịch vụ lẻ (không dùng thẻ)
    package_sessions_count: int  # buổi liệu trình (dùng thẻ)
    total_revenue: Decimal


class StaffPerformanceTotals(BaseModel):
    completed_bookings_count: int
    completed_services_count: int
    single_services_count: int
    package_sessions_count: int
    total_revenue: Decimal


class StaffPerformanceOut(BaseModel):
    start_date: date
    end_date: date
    timezone: str
    staff: List[StaffPerformanceItem]
    totals: StaffPerformanceTotals


# ---------- Notifications ----------
class VapidKeyOut(BaseModel):
    public_key: str
    enabled: bool


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class SubscribeRequest(BaseModel):
    """Định dạng PushSubscription.toJSON() của trình duyệt."""

    endpoint: str = Field(min_length=10, max_length=2000)
    keys: PushKeys
    expirationTime: Optional[float] = None


class UnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000)


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    endpoint: str
    created_at: datetime


class UnsubscribeOut(BaseModel):
    deleted: int


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    type: str
    booking_id: Optional[uuid.UUID] = None
    is_read: bool
    created_at: datetime


class NotificationListOut(BaseModel):
    unread_count: int
    items: List[NotificationOut]


class ReadAllOut(BaseModel):
    updated: int
