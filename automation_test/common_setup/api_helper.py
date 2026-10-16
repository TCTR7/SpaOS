import random
import time
from typing import Any, Dict, List, Optional
import httpx

from common_setup.config import config


def random_phone(prefix: str = "098") -> str:
    suffix = "".join(str(random.randint(0, 9)) for _ in range(7))
    return f"{prefix}{suffix}"


def unique_suffix() -> str:
    return f"{int(time.time() * 1000) % 1000000}_{random.randint(100, 999)}"


class ApiHelper:
    """Direct HTTP helper against FastAPI /api/v1 for seeding, verification, and cleanup."""

    def __init__(self, api_v1_url: Optional[str] = None) -> None:
        self.base_url = (api_v1_url or config.api_v1_url).rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=15.0)

    def close(self) -> None:
        self.client.close()

    def login(self, tenant_slug: str, phone_number: str, password: str) -> Dict[str, Any]:
        resp = self.client.post(
            "/auth/login",
            headers={"X-Tenant-Slug": tenant_slug},
            json={"phone_number": phone_number, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    def get_admin_token(self, tenant_slug: Optional[str] = None) -> str:
        slug = tenant_slug or config.tenant_slug
        data = self.login(slug, config.admin_phone, config.admin_password)
        return str(data["access_token"])

    def get_customer_token(self, tenant_slug: Optional[str] = None) -> str:
        slug = tenant_slug or config.tenant_slug
        data = self.login(slug, config.customer_phone, config.customer_password)
        return str(data["access_token"])

    def register_tenant(
        self,
        tenant_name: str,
        tenant_slug: str,
        admin_full_name: str,
        phone_number: str,
        password: str = "Admin@123",
    ) -> Dict[str, Any]:
        resp = self.client.post(
            "/auth/register-tenant",
            json={
                "tenant_name": tenant_name,
                "tenant_slug": tenant_slug,
                "admin_full_name": admin_full_name,
                "phone_number": phone_number,
                "password": password,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def create_service(
        self,
        token: str,
        name: str,
        duration_minutes: int = 45,
        price: float = 250000,
        is_package: bool = False,
        total_sessions: int = 1,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        resp = self.client.post(
            "/services",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": name,
                "description": description,
                "duration_minutes": duration_minutes,
                "price": price,
                "is_package": is_package,
                "total_sessions": total_sessions if is_package else 1,
                "is_active": True,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def list_services(self, token: str, is_package: Optional[bool] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"is_active": "true"}
        if is_package is not None:
            params["is_package"] = str(is_package).lower()
        resp = self.client.get(
            "/services",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def create_customer(
        self,
        token: str,
        full_name: str,
        phone_number: str,
        notes: Optional[str] = None,
        password: str = "Customer@123",
    ) -> Dict[str, Any]:
        resp = self.client.post(
            "/customers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": full_name,
                "phone_number": phone_number,
                "notes": notes,
                "password": password,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def issue_customer_package(
        self,
        token: str,
        customer_id: str,
        service_id: str,
        package_name: Optional[str] = None,
        total_sessions: int = 10,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "customer_id": customer_id,
            "service_id": service_id,
            "total_sessions": total_sessions,
        }
        if package_name:
            payload["package_name"] = package_name
        resp = self.client.post(
            "/customer-packages",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def get_customer_packages(self, token: str, customer_id: str) -> List[Dict[str, Any]]:
        resp = self.client.get(
            f"/customers/{customer_id}/packages",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    def get_available_slots(
        self,
        tenant_slug: str,
        date_str: str,
        service_ids: List[str],
        staff_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: List[tuple[str, str]] = [("date", date_str)]
        for sid in service_ids:
            params.append(("service_ids", sid))
        if staff_id:
            params.append(("staff_id", staff_id))
        resp = self.client.get(
            "/bookings/available-slots",
            headers={"X-Tenant-Slug": tenant_slug},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def create_booking(
        self,
        token: str,
        start_time: str,
        items: List[Dict[str, Optional[str]]],
        customer_id: Optional[str] = None,
        staff_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "start_time": start_time,
            "items": items,
            "staff_id": staff_id,
            "note": note,
        }
        if customer_id:
            payload["customer_id"] = customer_id
        resp = self.client.post(
            "/bookings",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def list_bookings(self, token: str, **params: Any) -> List[Dict[str, Any]]:
        resp = self.client.get(
            "/bookings",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()
