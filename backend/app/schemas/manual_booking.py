import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.auth import _check_phone
from app.schemas.booking import BookingItemIn


class ManualCustomerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str
    notes: Optional[str] = Field(default=None, max_length=5000)
    _phone = field_validator("phone_number")(_check_phone)


class ManualItemIn(BookingItemIn):
    model_config = ConfigDict(extra="forbid")


class ManualBatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    new_customer: Optional[ManualCustomerIn] = None
    staff_id: Optional[uuid.UUID] = None
    items: list[ManualItemIn] = Field(min_length=1, max_length=10)
    start_times: list[datetime] = Field(min_length=1, max_length=20)
    note: Optional[str] = Field(default=None, max_length=950)

    @model_validator(mode="after")
    def validate_customer(self):
        if (self.customer_id is None) == (self.new_customer is None):
            raise ValueError("Chọn khách hiện có hoặc tạo khách mới")
        from app.services.booking_service import ensure_aware
        times = [ensure_aware(t) for t in self.start_times]
        if len(set(times)) != len(times):
            raise ValueError("Các buổi phải khác giờ")
        return self


class ManualBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    request_id: uuid.UUID
    customer_id: uuid.UUID
    package_ids: list[uuid.UUID]
    booking_ids: list[uuid.UUID]
