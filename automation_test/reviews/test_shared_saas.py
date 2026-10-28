"""Real HTTP and Chromium coverage for shared brands and daily workplaces."""
import json
import re
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import httpx
import pytest
from playwright.sync_api import expect
from common_setup.config import config


def create_spa(name):
    slug="shared-"+uuid.uuid4().hex[:10]
    phone="09"+str(uuid.uuid4().int)[-8:]
    with httpx.Client(base_url=config.backend_url+"/api/v1",timeout=30) as api:
        created=api.post("/auth/register-tenant",json={"tenant_name":name,"tenant_slug":slug,"admin_full_name":"Owner QA","phone_number":phone,"password":"SharedQa@2026"})
        created.raise_for_status()
        token=created.json()["access_token"]; headers={"Authorization":"Bearer "+token}
        me=api.get("/auth/me",headers=headers).json()
        updated=api.patch("/spas/me",headers=headers,json={"name":name,"theme_color":"#116633"})
        updated.raise_for_status()
        return {"slug":slug,"phone":phone,"password":"SharedQa@2026","token":token,"headers":headers,"me":me}


def enter(page,c):
    values={"spaos_admin_token:"+c["slug"]:c["token"],"spaos_admin_session_version:"+c["slug"]:str(uuid.uuid4()),
        "spaos_guide_v2_MANAGEMENT_"+c["me"]["user"]["id"]:"seen"}
    seed="qa_shared_seed:"+c["slug"]
    page.add_init_script("if(!sessionStorage.getItem("+json.dumps(seed)+")){for(const [k,v] of Object.entries("+json.dumps(values)+"))localStorage.setItem(k,v);sessionStorage.setItem("+json.dumps(seed)+",'1');}")
    page.goto(config.frontend_url+"/s/"+c["slug"]+"/admin/staff")
    later=page.get_by_role("button",name="Để sau",exact=True)
    if later.is_visible():later.click()


def test_canonical_login_routes_brand_manifest_and_worker(unauthenticated_page):
    page=unauthenticated_page
    c=create_spa("Spa Sen QA")
    page.goto(config.frontend_url+"/admin/login")
    page.get_by_label("Số điện thoại",exact=True).fill(c["phone"])
    page.get_by_label("Mật khẩu",exact=True).fill(c["password"])
    page.get_by_role("button",name="Đăng nhập",exact=True).click()
    page.wait_for_url("**/s/"+c["slug"]+"/admin/dashboard")
    expect(page.get_by_role("button",name="Đăng xuất",exact=True)).to_be_visible()
    manifest_path="/s/"+c["slug"]+"/manifest.webmanifest"
    raw=page.request.get(config.frontend_url+"/s/"+c["slug"]+"/admin/login")
    assert 'href="'+manifest_path+'"' in raw.text(), raw.text()[:1800]
    expect(page.locator('link[rel="manifest"]')).to_have_attribute("href",manifest_path)
    manifest=page.request.get(config.frontend_url+manifest_path).json()
    assert manifest["name"]=="Spa Sen QA" and manifest["scope"]=="/s/"+c["slug"]+"/"
    assert manifest["id"].endswith(c["me"]["spa"]["id"])
    worker=page.request.get(config.frontend_url+"/s/"+c["slug"]+"/sw.js")
    assert worker.status==200 and worker.headers["service-worker-allowed"]==manifest["scope"]
    page.goto(config.frontend_url+manifest["start_url"])
    page.wait_for_url("**/s/"+c["slug"]+"/admin/dashboard")


def test_week_editor_saves_branch_per_day_and_brand_settings(unauthenticated_page):
    page=unauthenticated_page;c=create_spa("Workforce QA")
    with httpx.Client(base_url=config.backend_url+"/api/v1",timeout=30,headers=c["headers"]) as api:
        branch=api.post("/branches",json={"name":"Chi nhánh 2"});branch.raise_for_status();tid=branch.json()["tenant"]["id"]
        staff=api.post("/staff",json={"full_name":"Lan QA","phone_number":"09"+str(uuid.uuid4().int)[-8:],"password":"StaffQa@2026","branch_ids":[tid]});staff.raise_for_status();sid=staff.json()["id"]
    enter(page,c)
    expect(page.get_by_role("heading",name="Phân công chi nhánh theo ngày",exact=True)).to_be_visible()
    page.get_by_label("Chi nhánh Thứ 2",exact=True).select_option(tid)
    page.get_by_role("button",name="Lưu phân công tuần",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Đã lưu.")).to_be_visible()
    with httpx.Client(base_url=config.backend_url+"/api/v1",timeout=30,headers=c["headers"]) as api:
        saved=api.get("/workforce/staff/"+sid).json()["assignments"]
        assert next(r for r in saved if r["weekday"]==1 and r["day"] is None)["tenant_id"]==tid
    page.goto(config.frontend_url+"/s/"+c["slug"]+"/admin/brand")
    page.get_by_label("Tên spa / thương hiệu",exact=True).fill("Workforce Updated QA")
    page.get_by_role("button",name="Lưu nhận diện spa",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Đã cập nhật nhận diện spa")).to_be_visible()
    page.reload()
    expect(page.get_by_label("Tên spa / thương hiệu",exact=True)).to_have_value("Workforce Updated QA")


def test_scoped_sessions_and_public_directory_do_not_mix(unauthenticated_page):
    page=unauthenticated_page;a=create_spa("Brand A QA");b=create_spa("Brand B QA")
    enter(page,a)
    page.goto(config.frontend_url+"/s/"+b["slug"]+"/admin/staff")
    page.wait_for_url("**/s/"+b["slug"]+"/admin/login")
    with httpx.Client(base_url=config.frontend_url,timeout=30) as http:
        direct=http.get("/api/v1/branches/public").json()
        assert direct["branches"]==[]
        directory=http.get("/api/v1/branches/public",params={"spa_slug":a["slug"]}).json()
        assert len(directory["branches"])==1 and directory["branches"][0]["id"]==a["me"]["tenant"]["id"]
        assert directory["brand_name"]=="Brand A QA"
        raw=http.get("/s/"+a["slug"]+"/admin/login",headers={"x-spa-slug":b["slug"]})
        assert '<title>Brand A QA</title>' in raw.text
        neutral=http.get("/admin/login",headers={"x-spa-slug":a["slug"]})
        assert '<title>Brand A QA</title>' not in neutral.text


def test_customer_route_preserves_brand_manifest(unauthenticated_page):
    page=unauthenticated_page;c=create_spa("Customer Brand QA")
    path="/s/"+c["slug"]+"/b/"+c["me"]["tenant"]["slug"]
    page.goto(config.frontend_url+path)
    expect(page.locator('link[rel="manifest"]')).to_have_attribute("href","/s/"+c["slug"]+"/manifest.webmanifest")
    expect(page.get_by_role("link",name="Đặt lịch",exact=True).first).to_have_attribute("href",path+"/book")


def test_revoked_staff_tab_automatically_opens_remaining_branch(unauthenticated_page):
    page=unauthenticated_page;c=create_spa("Transfer QA")
    with httpx.Client(base_url=config.backend_url+"/api/v1",headers=c["headers"],timeout=30) as api:
        branch=api.post("/branches",json={"name":"Remaining branch"});branch.raise_for_status();tid=branch.json()["tenant"]["id"]
        phone="09"+str(uuid.uuid4().int)[-8:]
        staff=api.post("/staff",json={"full_name":"Transfer Staff QA","phone_number":phone,"password":"Transfer@123","branch_ids":[tid]});staff.raise_for_status();sid=staff.json()["id"]
        login=api.post("/auth/login",json={"phone_number":phone,"password":"Transfer@123"});login.raise_for_status();auth=login.json()
        values={"spaos_admin_token:"+c["slug"]:auth["access_token"],"spaos_guide_v2_MANAGEMENT_"+sid:"seen"}
        page.add_init_script("if(!sessionStorage.getItem('transfer_seeded')){for(const [k,v] of Object.entries("+json.dumps(values)+"))localStorage.setItem(k,v);sessionStorage.setItem('transfer_seeded','1');}")
        page.goto(config.frontend_url+"/s/"+c["slug"]+"/admin/bookings")
        expect(page.locator("#activeBranch")).to_be_visible()
        moved=api.put("/workforce/staff/"+sid+"/access",json={"branch_ids":[tid],"default_branch_id":tid})
        assert moved.status_code==200,moved.text
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.locator("header span").filter(has_text="Remaining branch")).to_be_visible(timeout=15000)
        expect(page.locator("#activeBranch")).to_be_hidden()
        expect(page.get_by_role("status").filter(has_text="Quyền chi nhánh đã thay đổi")).to_be_visible()
        expect(page.get_by_test_id("today-workplace")).to_contain_text("Bạn nghỉ hoặc chưa được phân công hôm nay")
        assert api.get("/auth/me",headers={"Authorization":"Bearer "+auth["access_token"]}).status_code==401


def test_owner_pauses_and_reopens_branch_without_losing_brand(unauthenticated_page):
    page=unauthenticated_page;c=create_spa("Lifecycle QA")
    with httpx.Client(base_url=config.backend_url+"/api/v1",headers=c["headers"],timeout=30) as api:
        created=api.post("/branches",json={"name":"Lifecycle branch"});created.raise_for_status()
        tid=created.json()["tenant"]["id"]
    enter(page,c)
    page.goto(config.frontend_url+"/s/"+c["slug"]+"/admin/branches")
    expect(page.get_by_role("link",name="Trang đặt lịch",exact=True).first).to_have_attribute("href",re.compile("/s/"+c["slug"]+"/b/"))
    page.get_by_role("button",name="Tạm ngưng Lifecycle branch",exact=True).click()
    modal=page.get_by_role("dialog",name="Tạm ngưng chi nhánh?",exact=True)
    modal.get_by_role("button",name="Xác nhận trạng thái chi nhánh",exact=True).click()
    expect(page.get_by_role("button",name="Mở lại Lifecycle branch",exact=True)).to_be_visible()
    page.get_by_role("button",name="Mở lại Lifecycle branch",exact=True).click()
    page.get_by_role("dialog",name="Mở lại chi nhánh?",exact=True).get_by_role("button",name="Xác nhận trạng thái chi nhánh",exact=True).click()
    expect(page.get_by_role("button",name="Tạm ngưng Lifecycle branch",exact=True)).to_be_visible()
    with httpx.Client(base_url=config.backend_url+"/api/v1",headers=c["headers"],timeout=30) as api:
        assert next(r for r in api.get("/branches/manage").json() if r["tenant"]["id"]==tid)["tenant"]["status"]=="ACTIVE"


def test_in_app_notification_keeps_spa_scope(unauthenticated_page):
    page=unauthenticated_page;c=create_spa("Notification QA")
    bid=str(uuid.uuid4())
    page.route("**/api/v1/notifications?*",lambda route:route.fulfill(json={"unread_count":1,"items":[{
        "id":str(uuid.uuid4()),"booking_id":bid,"title":"QA scoped appointment","body":"Open this appointment",
        "type":"BOOKING_CREATED","is_read":False,"created_at":"2026-10-28T00:00:00Z"}]}))
    enter(page,c)
    page.get_by_role("button",name="Thông báo",exact=True).click()
    page.get_by_role("dialog",name="Bảng thông báo",exact=True).get_by_role("button",name="Xem lịch hẹn",exact=True).click()
    page.wait_for_url(config.frontend_url+"/s/"+c["slug"]+"/admin/bookings?booking_id="+bid)


@pytest.mark.parametrize("session",["active","anonymous","expired"])
def test_booking_deep_link_opens_verified_target_after_login(unauthenticated_page,session):
    page=unauthenticated_page;c=create_spa("Deep Link QA")
    today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    with httpx.Client(base_url=config.backend_url+"/api/v1",headers=c["headers"],timeout=30) as api:
        branch=api.post("/branches",json={"name":"Booking destination"});branch.raise_for_status();tid=branch.json()["tenant"]["id"]
        switched=api.post("/branches/"+tid+"/switch");switched.raise_for_status()
        target_headers={"Authorization":"Bearer "+switched.json()["access_token"]}
        def create(path,payload):
            response=api.post(path,headers=target_headers,json=payload);response.raise_for_status();return response.json()
        staff=create("/staff",{"full_name":"Destination staff","phone_number":"09"+str(uuid.uuid4().int)[-8:],"password":"StaffLink@123"})
        scheduled=api.put("/workforce/staff/"+staff["id"]+"/week",headers=target_headers,json={"effective_from":str(today),"days":[{"weekday":d,"tenant_id":tid,"start_time":"09:00","end_time":"18:00"} for d in range(7)]})
        scheduled.raise_for_status()
        service=create("/services",{"name":"Destination service","price":"150000","duration_minutes":30})
        customer=create("/customers",{"full_name":"Destination customer","phone_number":"09"+str(uuid.uuid4().int)[-8:],"password":"Customer@123"})
        booking=create("/bookings",{"customer_id":customer["id"],"staff_id":staff["id"],"start_time":str(today+timedelta(days=3))+"T10:00:00+07:00","items":[{"service_id":service["id"]}]})
    key="spaos_admin_token:"+c["slug"]
    if session=="active":
        enter(page,c)
    else:
        values={"spaos_guide_v2_MANAGEMENT_"+c["me"]["user"]["id"]:"seen"}
        if session=="expired":values[key]="expired.invalid.token"
        page.add_init_script("if(!sessionStorage.getItem('deep_link_seeded')){for(const [k,v] of Object.entries("+json.dumps(values)+"))localStorage.setItem(k,v);sessionStorage.setItem('deep_link_seeded','1');}")
    target=config.frontend_url+"/s/"+c["slug"]+"/admin/bookings?booking_id="+booking["id"]+"&target_branch="+tid
    page.goto(target)
    if session!="active":
        page.wait_for_url("**/s/"+c["slug"]+"/admin/login")
        page.get_by_label("Số điện thoại",exact=True).fill(c["phone"])
        page.get_by_label("Mật khẩu",exact=True).fill(c["password"])
        page.get_by_role("button",name="Đăng nhập",exact=True).click()
    else:
        expect(page.get_by_role("region",name="Chi nhánh của lịch hẹn",exact=True)).to_be_visible()
        expect(page.get_by_role("dialog",name="Chi tiết lịch hẹn",exact=True)).to_have_count(0)
        page.get_by_role("button",name="Mở lịch tại Booking destination",exact=True).click()
    page.wait_for_url(target)
    expect(page.get_by_role("dialog",name="Chi tiết lịch hẹn",exact=True)).to_contain_text("Destination customer")
    expect(page.locator("#activeBranch")).to_have_value(tid)


def test_booking_deep_link_without_membership_does_not_load_booking(unauthenticated_page):
    page=unauthenticated_page;c=create_spa("Denied Link QA")
    enter(page,c)
    calls=[]
    bid=str(uuid.uuid4())
    page.on("request",lambda request:calls.append(request.url) if request.url.endswith("/bookings/"+bid) else None)
    page.goto(config.frontend_url+"/s/"+c["slug"]+"/admin/bookings?booking_id="+bid+"&target_branch="+str(uuid.uuid4()))
    region=page.get_by_role("region",name="Chi nhánh của lịch hẹn",exact=True)
    expect(region).to_contain_text("Bạn không còn được cấp chi nhánh")
    expect(region.get_by_role("button")).to_have_count(0)
    assert calls==[]
