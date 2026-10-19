import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env.test")


@dataclass(frozen=True)
class TestConfig:
    frontend_url: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:3001").rstrip("/")
    frontend_run_id: str = os.getenv("SPAOS_QA_RUN_ID", "")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8001").rstrip("/")
    tenant_slug: str = os.getenv("TENANT_SLUG", "spa-demo")

    admin_phone: str = os.getenv("ADMIN_PHONE", "0900000001")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "Admin@123")

    staff_phone: str = os.getenv("STAFF_PHONE", "0900000011")
    staff_password: str = os.getenv("STAFF_PASSWORD", "Staff@123")

    customer_phone: str = os.getenv("CUSTOMER_PHONE", "0900000101")
    customer_password: str = os.getenv("CUSTOMER_PASSWORD", "Customer@123")

    headless: bool = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
    slow_mo: int = int(os.getenv("SLOW_MO", "600"))

    @property
    def api_v1_url(self) -> str:
        return f"{self.backend_url}/api/v1"


config = TestConfig()
