import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from app.schemas.auth import _check_phone

class OperatorLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_number: str
    password: SecretStr
    _phone = field_validator("phone_number")(_check_phone)

class OwnerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: uuid.UUID
    branch_name: str = Field(min_length=1, max_length=255)
    owner_full_name: str = Field(min_length=1, max_length=255)
    phone_number: str
    password: SecretStr
    _phone = field_validator("phone_number")(_check_phone)

    @field_validator("branch_name", "owner_full_name")
    @classmethod
    def names(cls, value):
        if not value.strip():
            raise ValueError("Tên không được để trống")
        return value.strip()

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        raw = value.get_secret_value()
        if len(raw) < 8 or len(raw.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu chủ spa cần ít nhất 8 ký tự, tối đa 72 byte UTF-8")
        return value

class OperatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    phone_number: str

class OperatorToken(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "bearer"
    operator: OperatorOut

class ProvisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    owner_user_id: uuid.UUID
    branch_name: str
    owner_name: str
    phone_number: str
    created_at: datetime
