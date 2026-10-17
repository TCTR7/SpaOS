from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "SpaOS API"
    ENVIRONMENT: str = "development"
    ALLOW_TENANT_REGISTRATION: bool = False
    BRAND_NAME: str = "SpaOS"
    OPERATOR_PHONE: str = ""
    OPERATOR_NAME: str = "Quản trị triển khai"
    OPERATOR_PASSWORD: SecretStr = SecretStr("")
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = (
        "postgresql+asyncpg://spaos_app:spaos_app_password@localhost:5432/spaos"
    )
    MIGRATION_DATABASE_URL: str = (
        "postgresql+asyncpg://spaos:spaos_password@localhost:5432/spaos"
    )

    JWT_SECRET_KEY: str = "change-me-with-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DEFAULT_TIMEZONE: str = "Asia/Ho_Chi_Minh"
    # Khách chỉ được hủy lịch trước giờ hẹn tối thiểu X giờ
    CANCELLATION_MIN_HOURS: int = 2

    # Web Push (VAPID). Sinh khoá: python -m app.generate_vapid. Để trống = chỉ lưu thông báo in-app, không bắn push.
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@spaos.local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
