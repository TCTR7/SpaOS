import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class InvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    booking_id: Optional[uuid.UUID] = None
    customer_package_id: Optional[uuid.UUID] = None
    legacy_amount_due: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def source(self):
        if (self.booking_id is None) == (self.customer_package_id is None):
            raise ValueError("Chọn đúng một lịch hẹn hoặc thẻ liệu trình")
        if self.booking_id and self.legacy_amount_due is not None:
            raise ValueError("Giá lịch hẹn được lấy từ dữ liệu đã chốt")
        return self

class ReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal["CASH", "BANK_TRANSFER"]
    idempotency_key: uuid.UUID
    note: Optional[str] = Field(default=None, max_length=500)

class ReceiptVoid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: uuid.UUID
    reason: str = Field(min_length=1, max_length=500)

class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: str
    recorded_by: uuid.UUID
    created_at: datetime
    reversal_of: Optional[uuid.UUID]
    note: Optional[str]

class InvoiceOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    booking_id: Optional[uuid.UUID]
    customer_package_id: Optional[uuid.UUID]
    amount_due: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: Literal["UNPAID", "PARTIAL", "PAID"]
    created_at: datetime

class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    action: str
    entity_type: str
    entity_id: uuid.UUID
    details: dict
    created_at: datetime

class PaymentSummaryOut(BaseModel):
    date_from: date
    date_to: date
    timezone: str
    cash: Decimal
    bank_transfer: Decimal
    net_received: Decimal

class CollectionOut(BaseModel):
    source_id: uuid.UUID
    source_type: Literal["booking", "package"]
    customer_id: uuid.UUID
    customer_name: str
    phone_number: str
    description: str
    occurred_at: datetime
    source_status: str
    invoice_id: Optional[uuid.UUID]
    amount_due: Optional[Decimal]
    amount_paid: Decimal
    balance_due: Optional[Decimal]
    status: Literal["UNPAID", "PARTIAL", "PAID", "NEEDS_PRICE", "COVERED", "FREE"]
