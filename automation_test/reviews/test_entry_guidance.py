import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario


def test_single_branch_redirect_and_management_entry(scenario):
    s=scenario
    page=s["page"]("",True)
    page.route("**/api/v1/branches/public",lambda r:r.fulfill(json={"brand_name":"QA Spa","branches":[{"id":"one","name":"QA Spa","slug":s["slug"]}]}))
    page.goto(config.frontend_url+"/")
    expect(page).to_have_url(s["url"])
    expect(page.get_by_role("link",name="Đăng nhập quản lý",exact=True)).to_be_visible()
    page.get_by_role("link",name="Đăng nhập quản lý",exact=True).click()
    expect(page).to_have_url(config.frontend_url+"/admin/login")
    expect(page.get_by_role("link",name="Quản trị hệ thống",exact=True)).to_have_attribute("href","/operator/login")


@pytest.mark.parametrize("admin,ua",[(True,"Android"),(False,"iPhone")])
def test_role_guides_and_manifest(scenario,admin,ua):
    s=scenario
    page=s["page"](s["admin"] if admin else s["token"],admin)
    page.add_init_script("Object.defineProperty(navigator,'userAgent',{get:()=>"+repr(ua)+"});")
    page.goto(config.frontend_url+"/admin/dashboard" if admin else s["url"])
    button=page.get_by_role("button",name="Hướng dẫn & Cài ứng dụng",exact=True)
    expect(button).to_be_visible()
    expected="/admin/app.webmanifest" if admin else "/"+s["slug"]+"/app.webmanifest"
    expect(page.locator('link[rel="manifest"]')).to_have_attribute("href",expected)
    manifest=page.locator('link[rel="manifest"]').get_attribute("href")
    data=page.request.get(config.frontend_url+manifest).json()
    assert data["start_url"]==("/admin" if admin else "/"+s["slug"])
    assert data["start_url"].startswith(data["scope"])
    assert data["id"]!=("/"+s["slug"]+"/" if admin else "/admin/")
    button.click()
    dialog=page.get_by_role("dialog",name="Hướng dẫn & Cài ứng dụng",exact=True)
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text("Chrome/Android" if admin else "Safari trên iPhone/iPad")
    expect(dialog).to_contain_text("Thiết lập spa" if admin else "Tìm thời gian phù hợp")
    dialog.get_by_role("button",name="Tiếp theo",exact=True).click()
    expect(dialog).to_contain_text("Bước 2/3")
    dialog.get_by_role("button",name="Tiếp theo",exact=True).click()
    dialog.get_by_role("button",name="Hoàn tất hướng dẫn",exact=True).click()
    expect(dialog).not_to_be_visible()
    button.click()
    expect(dialog).to_contain_text("Bước 1/3")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_install_prompt_is_only_on_user_action(scenario):
    s=scenario
    page=s["page"](s["admin"],True)
    page.goto(config.frontend_url+"/admin/dashboard")
    page.get_by_role("button",name="Hướng dẫn & Cài ứng dụng",exact=True).click()
    page.evaluate("""() => {window.qaPrompts=0;const e=new Event('beforeinstallprompt',{cancelable:true});e.prompt=async()=>{window.qaPrompts++;};e.userChoice=Promise.resolve({outcome:'dismissed'});window.dispatchEvent(e);}""")
    expect(page.get_by_role("button",name="Cài ứng dụng",exact=True)).to_be_visible()
    assert page.evaluate("window.qaPrompts")==0
    page.get_by_role("button",name="Cài ứng dụng",exact=True).click()
    assert page.evaluate("window.qaPrompts")==1
    expect(page.get_by_role("button",name="Cài ứng dụng",exact=True)).to_have_count(0)
