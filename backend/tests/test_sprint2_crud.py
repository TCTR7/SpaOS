import uuid
import pytest
from tests.conftest import unique_phone, unique_slug


async def _register_tenant_admin(client, slug=None):
    slug = slug or unique_slug()
    r = await client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": f"Spa {slug}",
            "tenant_slug": slug,
            "admin_full_name": "Admin Test",
            "phone_number": unique_phone(),
            "password": "secret_password",
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    tenant_id = r.json()["user"]["tenant_id"]
    return slug, tenant_id, {"Authorization": f"Bearer {token}"}


async def _create_staff(client, slug, admin_headers):
    phone = unique_phone()
    r = await client.post(
        "/api/v1/staff",
        headers=admin_headers,
        json={"full_name": "KTV Test", "phone_number": phone, "password": "staff_password"},
    )
    assert r.status_code == 201, r.text
    staff_id = r.json()["id"]

    login_res = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-Slug": slug},
        json={"phone_number": phone, "password": "staff_password"},
    )
    assert login_res.status_code == 200, login_res.text
    staff_token = login_res.json()["access_token"]
    return staff_id, {"Authorization": f"Bearer {staff_token}"}


@pytest.mark.asyncio
async def test_tenant_settings_and_public(client):
    slug, tenant_id, h = await _register_tenant_admin(client)

    # 1. GET /tenants/me
    me_res = await client.get("/api/v1/tenants/me", headers=h)
    assert me_res.status_code == 200
    assert me_res.json()["slug"] == slug

    # 2. PATCH /tenants/me
    patch_res = await client.patch(
        "/api/v1/tenants/me",
        headers=h,
        json={
            "name": "Spa Brand New",
            "open_time": "08:30:00",
            "close_time": "21:30:00",
            "buffer_minutes": 15,
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Spa Brand New"
    assert patch_res.json()["buffer_minutes"] == 15

    # Test validation close_time <= open_time -> 422
    invalid_time = await client.patch(
        "/api/v1/tenants/me",
        headers=h,
        json={"open_time": "21:00:00", "close_time": "08:00:00"},
    )
    assert invalid_time.status_code == 422

    # 3. Tạo 1 dịch vụ active và 1 dịch vụ inactive
    await client.post(
        "/api/v1/services",
        headers=h,
        json={"name": "Dich vu Public", "duration_minutes": 60, "price": "250000", "is_active": True},
    )
    await client.post(
        "/api/v1/services",
        headers=h,
        json={"name": "Dich vu An", "duration_minutes": 30, "price": "100000", "is_active": False},
    )

    # 4. GET /public/tenants/{slug}
    pub = await client.get(f"/api/v1/public/tenants/{slug}")
    assert pub.status_code == 200
    pub_data = pub.json()
    assert pub_data["name"] == "Spa Brand New"
    service_names = [s["name"] for s in pub_data["services"]]
    assert "Dich vu Public" in service_names
    assert "Dich vu An" not in service_names

    # Public 404 cho slug không tồn tại
    assert (await client.get("/api/v1/public/tenants/slug-khong-ton-tai")).status_code == 404


@pytest.mark.asyncio
async def test_services_crud_and_permissions(client):
    slug, tenant_id, admin_h = await _register_tenant_admin(client)
    staff_id, staff_h = await _create_staff(client, slug, admin_h)

    # 1. POST /services (Role ADMIN tạo thành công)
    svc_res = await client.post(
        "/api/v1/services",
        headers=admin_h,
        json={"name": "Tam trang", "duration_minutes": 45, "price": "500000.00"},
    )
    assert svc_res.status_code == 201
    service_id = svc_res.json()["id"]

    # Role STAFF không được phép POST -> 403
    staff_create = await client.post(
        "/api/v1/services",
        headers=staff_h,
        json={"name": "Staff svc", "duration_minutes": 30, "price": "100000.00"},
    )
    assert staff_create.status_code == 403

    # 2. GET /services (Cả ADMIN và STAFF đều xem được)
    admin_list = await client.get("/api/v1/services", headers=admin_h)
    assert admin_list.status_code == 200
    staff_list = await client.get("/api/v1/services", headers=staff_h)
    assert staff_list.status_code == 200
    assert len(staff_list.json()) == 1

    # 3. PATCH /services/{id}
    patch_svc = await client.patch(
        f"/api/v1/services/{service_id}",
        headers=admin_h,
        json={"price": "600000.00", "description": "Mo ta moi"},
    )
    assert patch_svc.status_code == 200
    assert patch_svc.json()["description"] == "Mo ta moi"

    # 4. DELETE /services/{id} (Hard delete khi chưa có ràng buộc)
    del_res = await client.delete(f"/api/v1/services/{service_id}", headers=admin_h)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
    assert del_res.json()["mode"] == "hard"

    # Gọi lại DELETE -> 404
    assert (await client.delete(f"/api/v1/services/{service_id}", headers=admin_h)).status_code == 404


@pytest.mark.asyncio
async def test_staff_and_schedules_crud(client):
    slug, tenant_id, admin_h = await _register_tenant_admin(client)
    staff_id, staff_h = await _create_staff(client, slug, admin_h)

    # 1. GET /staff (ADMIN được xem, STAFF bị 403)
    assert (await client.get("/api/v1/staff", headers=admin_h)).status_code == 200
    assert (await client.get("/api/v1/staff", headers=staff_h)).status_code == 403

    # 2. PATCH /staff/{id}
    patch_staff = await client.patch(
        f"/api/v1/staff/{staff_id}",
        headers=admin_h,
        json={"full_name": "Ten Da Doi", "notes": "Ghi chu KTV"},
    )
    assert patch_staff.status_code == 200
    assert patch_staff.json()["full_name"] == "Ten Da Doi"
    assert patch_staff.json()["notes"] == "Ghi chu KTV"

    # 3. PUT /staff/{staff_id}/schedules (Ghi đè lịch)
    schedules_data = [
        {"day_of_week": d, "start_time": "09:00:00", "end_time": "18:00:00", "is_day_off": False}
        for d in range(1, 6)
    ] + [
        {"day_of_week": 0, "start_time": "09:00:00", "end_time": "09:00:00", "is_day_off": True}
    ]
    put_sched = await client.put(
        f"/api/v1/staff/{staff_id}/schedules",
        headers=admin_h,
        json={"schedules": schedules_data},
    )
    assert put_sched.status_code == 200
    assert len(put_sched.json()) == 6

    # 4. GET /staff/{staff_id}/schedules
    get_sched = await client.get(f"/api/v1/staff/{staff_id}/schedules", headers=admin_h)
    assert get_sched.status_code == 200
    assert len(get_sched.json()) == 6


@pytest.mark.asyncio
async def test_customers_and_packages_crud(client):
    slug, tenant_id, admin_h = await _register_tenant_admin(client)
    staff_id, staff_h = await _create_staff(client, slug, admin_h)

    # 1. POST /customers (Tạo nhanh tại quầy bởi STAFF)
    phone = unique_phone()
    cust_res = await client.post(
        "/api/v1/customers",
        headers=staff_h,
        json={"full_name": "Tran Thi Khach", "phone_number": phone},
    )
    assert cust_res.status_code == 201
    customer_id = cust_res.json()["id"]

    # 2. GET /customers với search query 'q'
    search_res = await client.get("/api/v1/customers", headers=admin_h, params={"q": phone[-6:]})
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1

    # 3. PATCH /customers/{id}
    patch_cust = await client.patch(
        f"/api/v1/customers/{customer_id}",
        headers=staff_h,
        json={"notes": "Da de kich ung"},
    )
    assert patch_cust.status_code == 200
    assert patch_cust.json()["notes"] == "Da de kich ung"

    # 4. Tạo gói liệu trình
    pkg_svc = await client.post(
        "/api/v1/services",
        headers=admin_h,
        json={
            "name": "Lieu trinh tri nam 10 buoi",
            "duration_minutes": 60,
            "price": "5000000.00",
            "is_package": True,
            "total_sessions": 10,
        },
    )
    assert pkg_svc.status_code == 201
    pkg_svc_id = pkg_svc.json()["id"]

    # 5. POST /customer-packages (Cấp thẻ liệu trình)
    grant_pkg = await client.post(
        "/api/v1/customer-packages",
        headers=staff_h,
        json={"customer_id": customer_id, "service_id": pkg_svc_id},
    )
    assert grant_pkg.status_code == 201
    pkg_data = grant_pkg.json()
    assert pkg_data["package_name"] == "Lieu trinh tri nam 10 buoi"
    assert pkg_data["total_sessions"] == 10
    assert pkg_data["used_sessions"] == 0
    assert pkg_data["remaining_sessions"] == 10
    assert pkg_data["status"] == "ACTIVE"

    # 6. GET /customers/{customer_id}/packages & GET /customer-packages
    cust_pkgs = await client.get(f"/api/v1/customers/{customer_id}/packages", headers=staff_h)
    assert cust_pkgs.status_code == 200
    assert len(cust_pkgs.json()) == 1

    all_pkgs = await client.get("/api/v1/customer-packages", headers=admin_h, params={"status": "ACTIVE"})
    assert all_pkgs.status_code == 200
    assert len(all_pkgs.json()) == 1

    # Dịch vụ đã gắn với thẻ -> DELETE chuyển sang soft-delete
    del_svc = await client.delete(f"/api/v1/services/{pkg_svc_id}", headers=admin_h)
    assert del_svc.status_code == 200
    assert del_svc.json()["mode"] == "soft"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_strict(client):
    """KIỂM CHỨNG BẢO MẬT MULTI-TENANT ISOLATION:

    Tạo tài nguyên ở Spa A.
    Dùng token của Admin Spa B gọi GET, PATCH, DELETE vào ID của Spa A.
    Tất cả BẮT BUỘC trả về 404 hoặc danh sách rỗng (không rò rỉ dữ liệu chéo).
    """
    # 1. Khởi tạo 2 Spa độc lập
    slug_a, tid_a, admin_a_h = await _register_tenant_admin(client)
    slug_b, tid_b, admin_b_h = await _register_tenant_admin(client)

    # 2. Spa A tạo Service, Staff, Customer và CustomerPackage
    svc_a_res = await client.post(
        "/api/v1/services",
        headers=admin_a_h,
        json={
            "name": "Dich vu Spa A",
            "duration_minutes": 60,
            "price": "300000.00",
            "is_package": True,
            "total_sessions": 5,
        },
    )
    svc_a_id = svc_a_res.json()["id"]

    staff_a_res = await client.post(
        "/api/v1/staff",
        headers=admin_a_h,
        json={"full_name": "Nhan Vien Spa A", "phone_number": unique_phone(), "password": "pass_spa_a"},
    )
    staff_a_id = staff_a_res.json()["id"]

    cust_a_res = await client.post(
        "/api/v1/customers",
        headers=admin_a_h,
        json={"full_name": "Khach Hang Spa A", "phone_number": unique_phone()},
    )
    cust_a_id = cust_a_res.json()["id"]

    pkg_a_res = await client.post(
        "/api/v1/customer-packages",
        headers=admin_a_h,
        json={"customer_id": cust_a_id, "service_id": svc_a_id},
    )
    pkg_a_id = pkg_a_res.json()["id"]

    # 3. Admin Spa B truy vấn danh sách -> KHÔNG ĐƯỢC thấy tài nguyên của Spa A
    b_services = await client.get("/api/v1/services", headers=admin_b_h)
    assert b_services.status_code == 200
    assert all(s["id"] != svc_a_id for s in b_services.json())

    b_staff = await client.get("/api/v1/staff", headers=admin_b_h)
    assert b_staff.status_code == 200
    assert all(st["id"] != staff_a_id for st in b_staff.json())

    b_customers = await client.get("/api/v1/customers", headers=admin_b_h)
    assert b_customers.status_code == 200
    assert all(c["id"] != cust_a_id for c in b_customers.json())

    b_packages = await client.get("/api/v1/customer-packages", headers=admin_b_h)
    assert b_packages.status_code == 200
    assert all(p["id"] != pkg_a_id for p in b_packages.json())

    # 4. Admin Spa B tác động trực tiếp vào ID của Spa A -> BẮT BUỘC trả về 404
    # Services
    assert (await client.patch(f"/api/v1/services/{svc_a_id}", headers=admin_b_h, json={"name": "Hack"})).status_code == 404
    assert (await client.delete(f"/api/v1/services/{svc_a_id}", headers=admin_b_h)).status_code == 404

    # Staff & Schedules
    assert (await client.patch(f"/api/v1/staff/{staff_a_id}", headers=admin_b_h, json={"full_name": "Hack"})).status_code == 404
    assert (await client.get(f"/api/v1/staff/{staff_a_id}/schedules", headers=admin_b_h)).status_code == 404
    assert (await client.put(f"/api/v1/staff/{staff_a_id}/schedules", headers=admin_b_h, json={"schedules": []})).status_code == 404

    # Customers & Packages
    assert (await client.patch(f"/api/v1/customers/{cust_a_id}", headers=admin_b_h, json={"full_name": "Hack"})).status_code == 404
    assert (await client.get(f"/api/v1/customers/{cust_a_id}/packages", headers=admin_b_h)).status_code == 404

    # Admin Spa B cố tình cấp thẻ chéo tenant -> 404
    cross_pkg_create = await client.post(
        "/api/v1/customer-packages",
        headers=admin_b_h,
        json={"customer_id": cust_a_id, "service_id": svc_a_id},
    )
    assert cross_pkg_create.status_code == 404
