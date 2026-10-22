"""Read-only UI inventory on disposable QA data; console output only."""
import json
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario


def test_ui_inventory(scenario, api_helper):
    s = scenario
    staff_token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    roles = [
        (s["admin"], True, ["/admin/" + path for path in ["dashboard", "branches", "bookings", "customers", "services", "staff", "reports", "payments", "settings", "account"]]),
        (staff_token, True, ["/admin/work-hours", "/admin/account", "/admin/bookings", "/admin/customers", "/admin/services"]),
        (s["token"], False, ["/" + s["slug"] + path for path in ["", "/book", "/appointments", "/profile"]]),
        ("", False, ["/", "/admin/login", "/operator/login", "/" + s["slug"] + "/login", "/" + s["slug"] + "/register", "/" + s["slug"] + "/activate"]),
    ]
    for token, admin, paths in roles:
        page = s["page"](token, admin)
        key_errors = []
        page.on("console", lambda msg: key_errors.append(msg.text) if msg.type == "error" and "same key" in msg.text else None)
        for path in paths:
            page.goto(config.frontend_url + path)
            expect(page.locator("main,form").first).to_be_visible()
            for width in (320, 1366):
                page.set_viewport_size({"width": width, "height": 844})
                result = page.evaluate("""() => {
                    const visible = e => e.getBoundingClientRect().width > 0 && e.getBoundingClientRect().height > 0;
                    const small = Array.from(document.querySelectorAll('main a,main button,main select')).filter(visible).filter(e => e.getBoundingClientRect().height < 40).map(e => ({label: (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0,70), height: Math.round(e.getBoundingClientRect().height)}));
                    const duplicates = Array.from(document.querySelectorAll('[id]')).map(e=>e.id).filter((v,i,a)=>a.indexOf(v)!==i);
                    return {overflow: document.documentElement.scrollWidth > innerWidth + 1, small: small.slice(0,12), duplicate_ids: duplicates};
                }""")
                print("UI_AUDIT", path.replace(s["slug"], "SPA"), width, json.dumps(result, ensure_ascii=True))
            if path == "/" + s["slug"]:
                print("CSS_AUDIT", page.evaluate("""() => {const e=document.createElement('div');e.className='shadow-xs backdrop-blur-xs';document.body.append(e);const s=getComputedStyle(e);const r={shadow:s.boxShadow,blur:s.backdropFilter};e.remove();return r;}"""))
        assert not key_errors, key_errors
