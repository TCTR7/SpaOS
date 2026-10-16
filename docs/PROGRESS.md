# TIẾN ĐỘ DỰ ÁN & TRẠNG THÁI HIỆN TẠI (PROJECT PROGRESS)

*Quy tắc cho AI: Sau khi hoàn thành mỗi Sprint hoặc Task lớn, hãy tự động cập nhật trạng thái `[x]` vào file này và ghi chú ngắn gọn các file quan trọng vừa tạo.*

## Trạng thái các Sprint (HOÀN TẤT 7/7 SPRINT - 100% MVP & E2E AUTOMATION)
- [x] **Sprint 1:** Hạ tầng Docker, Database Schema (7 bảng), Alembic, RLS & Auth Multi-tenant.
  - Files: `docker-compose.yml`, `docker/init-db.sh`, `.env.example`, `backend/Dockerfile`, `backend/.dockerignore`, `backend/requirements.txt`, `backend/app/core/{config,database,security}.py`, `backend/app/models/models.py`, `backend/app/schemas/auth.py`, `backend/app/api/deps.py` (`get_current_tenant`, `get_tenant_db`, `require_roles`), `backend/app/api/v1/auth.py`, `backend/alembic/versions/0001_initial.py`, `backend/tests/test_auth.py`.
  - Kiểm thử: `5/5 tests PASSED` (100% bao gồm cả RLS Multi-tenant isolation).
- [x] **Sprint 2:** API Quản trị cơ bản (Tenants, Services, Staff Schedules, Customer Packages) + Seed Data.
  - Files: `backend/app/api/v1/{tenants,services,staff,customers}.py`, `backend/app/api/utils.py`, `backend/app/schemas/admin.py`, `backend/app/seed.py`, `backend/tests/test_sprint2_crud.py`. Kiểm thử: `10/10 tests PASSED` (100% gồm Sprint 1 và toàn bộ CRUD + Multi-tenant Isolation chéo tenant của Sprint 2). Seed: `docker compose exec backend python -m app.seed` (spa-demo; ADMIN 0900000001/Admin@123, STAFF 0900000011-13/Staff@123, CUSTOMER 0900000101/Customer@123).
- [x] **Sprint 3:** Core Booking Engine (Available Slots, Concurrency Row Locking, Tự động trừ buổi liệu trình).
  - Files: `backend/app/services/booking_service.py`, `backend/app/api/v1/bookings.py`, `backend/app/api/booking_deps.py` (tenant từ JWT hoặc `X-Tenant-Slug`), `backend/app/schemas/booking.py`, `backend/tests/test_booking_concurrency.py`. Kiểm thử: `19/19 tests PASSED` (Sprint 1: 5, Sprint 2: 5, Sprint 3: 9 gồm 5 request song song cùng KTV/cùng giờ -> đúng 1 thành công, auto-assign 3 KTV, chống đặt lố thẻ liệu trình, trừ buổi idempotent).
- [x] **Sprint 4:** API Báo cáo Hoa hồng KTV & Thông báo Web Push / In-App Notification (bỏ Telegram theo PO).
  - Files: `backend/alembic/versions/0002_notifications.py` (bảng `push_subscriptions`, `notifications` + FORCE RLS), `backend/app/models/models.py`, `backend/app/schemas/sprint4.py`, `backend/app/services/notification_service.py`, `backend/app/api/v1/{reports,notifications}.py`, `backend/app/generate_vapid.py`, `backend/tests/test_sprint4_reports_notifications.py`. Kiểm thử: `25/25 tests PASSED` (Sprint 1: 5, Sprint 2: 5, Sprint 3: 9, Sprint 4: 6).
- [x] **Sprint 5:** Web Admin Dashboard (Next.js `/admin/*`).
  - Files: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts`, `frontend/.env.example`, `frontend/public/sw.js` (Web Push Service Worker), `frontend/src/lib/{types,utils,api}.ts`, `frontend/src/components/ui/{button,input,card,modal}.tsx`, `frontend/src/components/admin/{auth-context,notification-bell,admin-shell}.tsx`, `frontend/src/app/(admin)/admin/{layout,page}.tsx`, và các trang quản trị: `/admin/login`, `/admin/register-tenant`, `/admin/bookings` (alias `/admin/dashboard`), `/admin/customers`, `/admin/services`, `/admin/staff`, `/admin/settings`, `/admin/reports`.
  - Kiểm thử Build: `cd frontend && npm run build` thành công 100% (TypeScript strict, không dùng `any`).
- [x] **Sprint 6:** Client PWA Đặt lịch (`/[tenant_slug]`).
  - Files: `frontend/public/manifest.json` (Web App Manifest chuẩn PWA), `frontend/src/lib/customer-api.ts` (tách biệt token theo từng `slug` `spaos_customer_token_<slug>` + tự động đính kèm `X-Tenant-Slug`), `frontend/src/components/customer/{customer-context,customer-notification-bell,customer-shell}.tsx`, và các trang khách hàng trong `frontend/src/app/[tenant_slug]/`: `page.tsx`, `book/page.tsx`, `appointments/page.tsx`, `profile/page.tsx`, `login/page.tsx`, `register/page.tsx`.
  - Kiểm thử Build: `cd frontend && npm run build` thành công 100% cho toàn bộ routes `/admin/*` và `/[tenant_slug]/*`.
- [x] **Sprint 7:** Bộ Kiểm thử Tự động E2E (`automation_test/`) theo mô hình Feature-based Page Object Model (POM) với `pytest` + `playwright`.
  - Files:
    + Gốc: `automation_test/requirements.txt`, `automation_test/pytest.ini`, `automation_test/.env.test`, `automation_test/conftest.py`.
    + `common_setup/`: `__init__.py`, `config.py`, `base_page.py`, `api_helper.py`, `auth_setup.py` (2 `BrowserContext` độc lập: `admin_page` Desktop `1440x900` và `customer_pwa_page` Mobile `390x844`).
    + `features/admin_auth/`: `pages/login_page.py`, `tests/test_admin_login.py` (3 tests: đăng nhập đúng, sai mật khẩu/slug, chặn unauthenticated).
    + `features/admin_catalog/`: `pages/{service_page.py,staff_page.py}`, `tests/{test_services.py,test_staff_schedules.py}` (tạo dịch vụ lẻ & gói liệu trình, thêm KTV & lưu lịch 7 ngày).
    + `features/admin_crm_packages/`: `pages/customer_package_page.py`, `tests/test_issue_package.py` (tìm kiếm khách & cấp thẻ liệu trình mới).
    + `features/admin_bookings/`: `pages/booking_calendar_page.py`, `tests/test_booking_status_and_deduct_session.py` (chuyển lịch hẹn sang `COMPLETED` trên Calendar và xác minh `used_sessions += 1`).
    + `features/client_pwa_booking/`: `pages/{tenant_home_page.py,booking_wizard_page.py,my_appointments_page.py}`, `tests/{test_pwa_booking_flow.py,test_multi_tenant_isolation_ui.py}` (luồng đặt lịch 4 bước trên PWA đồng bộ sang Calendar Admin + kiểm thử cô lập giao diện Multi-tenant giữa 2 Spa).
  - Lệnh chạy test E2E: `cd automation_test && .\.venv\Scripts\pytest.exe -v` -> **`9/9 tests PASSED (100%)`**.

## Ghi chú kiến trúc & Biến môi trường đã thiết lập
- **Backend Port:** 8000 (Host: ${BACKEND_PORT:-8001} do port 8000 đang được dùng bởi project khác)
- **Frontend Port:** 3000 (`NEXT_PUBLIC_API_URL=/api/v1` proxy qua `next.config.mjs` rewrites tới `BACKEND_INTERNAL_URL=http://localhost:8001` để đồng nguồn trình duyệt)
- **Database:** PostgreSQL Port 5432 (Host: ${POSTGRES_PORT:-5433} do port 5432 đang được dùng bởi project khác)
- **Tổng kết toàn dự án (Sprints 1–7):**
  - **Backend Unit/Integration (`backend/tests/`):** `25/25 PASSED` (`docker compose exec backend pytest -v`).
  - **Frontend Build (`frontend/`):** `100% Compiled & Typechecked` (`cd frontend && npm run build`).
  - **E2E Automation (`automation_test/`):** `9/9 PASSED` (`cd automation_test && .\.venv\Scripts\pytest.exe -v`).
