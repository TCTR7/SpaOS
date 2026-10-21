import uuid
from datetime import date, time
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.auth import _check_phone
from app.schemas.booking import BookingCreate

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CustomerBookingRequest(BookingCreate):
    model_config = ConfigDict(extra="forbid")
    request_id: uuid.UUID

class ProfileUpdate(Strict):
    full_name: str = Field(min_length=1, max_length=255)
    @field_validator("full_name")
    @classmethod
    def name(cls, value):
        if not value.strip(): raise ValueError("Nhập họ tên")
        return value.strip()

class CredentialsUpdate(Strict):
    current_password: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=72)
    phone_number: str | None = None
    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf8")) > 72: raise ValueError("Mật khẩu quá dài")
        return value
    @field_validator("phone_number")
    @classmethod
    def phone(cls, value):
        return _check_phone(value) if value else None

class RecoveryIssue(Strict):
    current_password: str = Field(min_length=1, max_length=128)
    identity_verified: bool
    @field_validator("identity_verified")
    @classmethod
    def verified(cls, value):
        if not value: raise ValueError("Cần xác minh khách trước khi cấp liên kết")
        return value

class RecoveryClaim(Strict):
    token: str = Field(min_length=40, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    _password = field_validator("password")(CredentialsUpdate.password_bytes.__func__)

class HandoverIn(Strict):
    note: str = Field(max_length=1000)

class LogoIn(Strict):
    data: str = Field(max_length=360000)

class DateOverrideIn(Strict):
    day: date
    is_day_off: bool = True
    start_time: time = time(8)
    end_time: time = time(21)
    @field_validator("start_time", "end_time")
    @classmethod
    def local_clock(cls, value):
        if value.tzinfo is not None: raise ValueError("Nhập giờ làm tại Việt Nam, không kèm múi giờ")
        return value
    @model_validator(mode="after")
    def range(self):
        if not self.is_day_off and self.end_time <= self.start_time: raise ValueError("Giờ kết thúc cần sau giờ bắt đầu")
        return self
