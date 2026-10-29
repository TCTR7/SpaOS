import re
import base64
import json
import os
import fitz
from PIL import Image
import zxingcpp
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from playwright.sync_api import expect
from common_setup.config import config
from features.operator_portal.pages.operator_page import OperatorPage


def test_handover_update_recovery_and_concurrent_claim(operator_ui):
    page_for, backend = operator_ui
    page = page_for()
    ui = OperatorPage(page)
    ui.login()
    phone = ui.fill_owner()
    ui.submit()
    expect(page.get_by_label("Họ tên hiện tại", exact=True)).to_have_value("Trần Cao Trung")
    preview = page.get_by_role("img", name="Bản xem trước bộ bàn giao")
    expect(preview).to_have_attribute("width", "1200")
    text = page.get_by_label("Tin nhắn bàn giao", exact=True).input_value()
    assert phone in text and "/admin/login" in text and "/operator" not in text
    assert "OwnerQa@123" not in text
    # Capture browser downloads in memory: never save screenshots/downloads/proofs.
    page.evaluate("""() => {
      window.qaDownloads = [];
      const original = URL.createObjectURL;
      URL.createObjectURL = function(blob) { window.qaDownloads.push(blob); return original.call(URL, blob); };
      HTMLAnchorElement.prototype.click = function() {};
    }""")
    page.get_by_role("button",name="Tải ảnh PNG",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Đã tải ảnh PNG")).to_be_visible()
    page.get_by_role("button",name="Tải PDF bàn giao",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Đã tải PDF")).to_be_visible()
    payloads=page.evaluate("""async () => await Promise.all(window.qaDownloads.map(async blob => ({type:blob.type,data:await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.readAsDataURL(blob);})})))""")
    png=base64.b64decode(payloads[0]["data"])
    assert png.startswith(b"\x89PNG")
    pdf=base64.b64decode(payloads[1]["data"])
    assert pdf.startswith(b"%PDF-")
    # The PDF pages contain rasterized Unicode labels and clickable URLs.
    assert b"/URI" in pdf and b"/admin/login" in pdf
    assert b"OwnerQa@123" not in pdf
    document=fitz.open(stream=pdf,filetype="pdf")
    assert len(document)==3
    for i,pdf_page in enumerate(document):
        pixmap=pdf_page.get_pixmap(matrix=fitz.Matrix(1.5,1.5))
        image=Image.frombytes("RGB",(pixmap.width,pixmap.height),pixmap.samples)
        qr=zxingcpp.read_barcode(image)
        assert qr is not None
        uri=pdf_page.get_links()[0]["uri"]
        assert qr.text==uri
        assert "/operator" not in uri and "#" not in uri
        if os.getenv("SPAOS_REVIEW_PREVIEW")=="1" and i in (0,2):
            image.thumbnail((600,900))
            output=BytesIO();image.save(output,format="PNG")
            print("SPAOS_PREVIEW:"+base64.b64encode(output.getvalue()).decode())
    document.close()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.get_by_label("Họ tên hiện tại",exact=True).fill("Chủ spa cập nhật QA")
    page.get_by_label("Tôi đã xác minh đúng chủ spa",exact=True).check()
    page.get_by_label("Mật khẩu operator để xác nhận",exact=True).fill("OperatorOnlyForQa@2026")
    page.get_by_role("button",name="Lưu thông tin chủ spa",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Đã cập nhật tài khoản ở các chi nhánh")).to_be_visible()
    page.get_by_label("Tôi đã xác minh đúng chủ spa",exact=True).check()
    page.get_by_label("Mật khẩu operator để xác nhận",exact=True).fill("OperatorOnlyForQa@2026")
    page.get_by_role("button",name="Cấp liên kết đặt lại mật khẩu",exact=True).click()
    link=page.get_by_label("Liên kết riêng cho chủ spa",exact=True)
    expect(link).to_be_visible()
    recovery_url=link.input_value()
    customer=page_for()
    customer.goto(recovery_url)
    expect(customer.get_by_role("heading",name="Đặt lại mật khẩu chủ spa",exact=True)).to_be_visible()
    expect(customer).to_have_url(re.compile(re.escape(config.frontend_url)+r"/s/[^/]+/admin/recover$"))
    assert customer.evaluate("location.hash") == ""
    customer.get_by_label("Mật khẩu mới",exact=True).fill("RecoveryOwner@2026")
    customer.get_by_label("Nhập lại mật khẩu",exact=True).fill("RecoveryOwner@2026")
    customer.get_by_role("button",name="Đặt mật khẩu mới",exact=True).click()
    expect(customer.get_by_role("status").filter(has_text="Đã đặt lại mật khẩu")).to_be_visible()
    customer.get_by_role("link",name="Đăng nhập quản lý",exact=True).click()
    customer.locator("#phone").fill(phone)
    customer.locator("#password").fill("RecoveryOwner@2026")
    customer.get_by_role("button",name="Đăng nhập",exact=True).click()
    expect(customer).to_have_url(re.compile(re.escape(config.frontend_url)+r"/s/[^/]+/admin/dashboard$"))
    # Fresh grant: two simultaneous claims must have exactly one winner.
    page.get_by_label("Tôi đã xác minh đúng chủ spa",exact=True).check()
    page.get_by_label("Mật khẩu operator để xác nhận",exact=True).fill("OperatorOnlyForQa@2026")
    page.get_by_role("button",name="Cấp liên kết đặt lại mật khẩu",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Đã cấp liên kết dùng một lần")).to_be_visible()
    token=link.input_value().split("#")[1]
    def claim(_):
        request=Request(backend+"/api/v1/operator/recovery",data=json.dumps({"token":token,"password":"ConcurrentOwner@2026"}).encode(),headers={"Content-Type":"application/json"})
        try:
            with urlopen(request) as response: return response.status
        except HTTPError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(claim,range(2))) == [200,400]


def test_version_reload_and_mismatch_states(operator_ui):
    page_for,_=operator_ui
    page=page_for()
    ui=OperatorPage(page)
    ui.login()
    expect(page.get_by_role("heading",name="Hệ thống & Phiên bản",exact=True)).to_be_visible()
    current=page.request.get(config.frontend_url+"/api/system/version").json()
    page.route("**/api/system/version",lambda r:r.fulfill(json={**current,"build_id":"new-server-build"}))
    page.get_by_role("button",name="Kiểm tra lại phiên bản",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Trình duyệt đang mở bản cũ")).to_be_visible()
    page.unroute("**/api/system/version")
    page.route("**/api/v1/operator/system",lambda r:r.fulfill(json={**current,"release_id":"other-release"}))
    page.get_by_role("button",name="Kiểm tra lại phiên bản",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Frontend và backend khác đợt phát hành")).to_be_visible()
