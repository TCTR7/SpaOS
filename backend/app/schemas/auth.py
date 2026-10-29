import re
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.models import UserRole

_PHONE_RE = re.compile(r"^\+?\d{9,15}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _check_phone(v: str) -> str:
    v = re.sub(r"[\s.\-()]", "", v.strip())
    v = re.sub(r"^\+?84([35789]\d{8})$", r"0\1", v)
    if not _PHONE_RE.match(v):
        raise ValueError("Số điện thoại không hợp lệ")
    return v


class LoginRequest(BaseModel):
    phone_number: str
    password: str = Field(min_length=1, max_length=128)

    _phone = field_validator("phone_number")(_check_phone)


class CustomerRegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str
    password: str = Field(min_length=6, max_length=128)

    _phone = field_validator("phone_number")(_check_phone)


class TenantRegisterRequest(BaseModel):
    """Đăng ký Spa mới + tài khoản ADMIN đầu tiên."""

    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(min_length=3, max_length=100)
    admin_full_name: str = Field(min_length=1, max_length=255)
    phone_number: str
    password: str = Field(min_length=6, max_length=128)

    _phone = field_validator("phone_number")(_check_phone)

    @field_validator("tenant_slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError("Slug chỉ gồm chữ thường, số và dấu gạch ngang")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    role: UserRole
    full_name: str
    phone_number: str
    is_active: bool


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    spa_id: Optional[uuid.UUID] = None
    slug: str
    name: str
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None
    theme_color: Optional[str] = None
    buffer_minutes: int
    status: str


class TokenResponse(BaseModel):
    spa_slug: str | None = None
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MeResponse(BaseModel):
    user: UserOut
    tenant: TenantOut
    spa: dict | None = None
