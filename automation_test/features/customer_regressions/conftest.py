import json
from datetime import datetime, timedelta, timezone

import pytest
from common_setup.api_helper import random_phone, unique_suffix
from common_setup.config import config


@pytest.fixture
def scenario(api_helper, browser_instance):
    """Each test owns a tenant, customer, staff and package; no shared demo slots."""
    slug = "qa-" + unique_suffix().replace("_", "-")
    auth = api_helper.register_tenant("QA Spa", slug, "QA Admin", random_phone())
    admin = auth["access_token"]
    ah = {"Authorization": "Bearer " + admin}

    def call(method, path, **kwargs):
        kwargs.setdefault("headers", ah)
        response = api_helper.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    call("PATCH", "/tenants/me", json={"open_time": "00:00:00", "close_time": "23:59:00"})
    staff = call("POST", "/staff", json={"full_name": "QA Staff", "phone_number": random_phone(), "password": "Staff@123"})
    call("PUT", "/staff/" + staff["id"] + "/schedules", json={"schedules": [
        {"day_of_week": d, "start_time": "00:00:00", "end_time": "23:59:00"} for d in range(7)]})
    phone = random_phone()
    customer = api_helper.create_customer(admin, "QA Customer", phone)
    token = api_helper.login(slug, phone, "Customer@123")["access_token"]
    service = api_helper.create_service(admin, "QA Treatment", duration_minutes=30, is_package=True, total_sessions=1)
    package = api_helper.issue_customer_package(admin, customer["id"], service["id"], "QA One Session", 1)
    contexts = []
    bookings = []
    errors = []

    def page_for(token_value=token, admin_slot=False):
        context = browser_instance.new_context(viewport={"width": 390, "height": 844})
        key = "spaos_admin_token" if admin_slot else "spaos_customer_token_" + slug
        context.add_init_script("if (!sessionStorage.getItem('qa_seeded')) { localStorage.setItem(" + json.dumps(key) + "," + json.dumps(token_value) + "); sessionStorage.setItem('qa_seeded', '1'); }")
        contexts.append(context)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        return page

    def book(minutes=None):
        start = datetime.now(timezone.utc) + (timedelta(minutes=minutes) if minutes else timedelta(days=5))
        if minutes is None:
            start = start.replace(hour=3, minute=0, second=0, microsecond=0)
        result = api_helper.create_booking(token, start.isoformat(),
                    [{"service_id": service["id"], "customer_package_id": package["id"]}], staff_id=staff["id"])
        bookings.append(result["id"])
        return result

    yield dict(slug=slug, admin=admin, token=token, phone=phone, customer=customer,
               service=service, staff=staff, package=package, call=call, page=page_for, book=book,
               url=config.frontend_url + "/" + slug, errors=errors)
    for booking_id in bookings:
        current = call("GET", "/bookings/" + booking_id)
        if current["status"] in ("PENDING", "CONFIRMED", "IN_PROGRESS"):
            call("POST", "/bookings/" + booking_id + "/cancel")
    for context in contexts:
        context.close()
    assert not errors, errors
