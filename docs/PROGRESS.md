# TIẾN ĐỘ DỰ ÁN & TRẠNG THÁI HIỆN TẠI (PROJECT PROGRESS)

*Quy tắc cho AI: Sau khi hoàn thành mỗi Sprint hoặc Task lớn, hãy tự động cập nhật trạng thái `[x]` vào file này và ghi chú ngắn gọn các file quan trọng vừa tạo.*

## Trạng thái các Sprint (HOÀN TẤT 6/6 SPRINT - 100% MVP)
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
  - Files: `frontend/public/manifest.json` (Web App Manifest chuẩn PWA), `frontend/src/lib/customer-api.ts` (tách biệt token theo từng `slug` `spaos_customer_token_<slug>` + tự động đính kèm `X-Tenant-Slug`), `frontend/src/components/customer/{customer-context,customer-notification-bell,customer-shell}.tsx` (Dynamic Branding theo `theme_color`/`logo_url`, Mobile-first Bottom Navigation Bar, In-App + Web Push Notification), và các trang khách hàng trong `frontend/src/app/[tenant_slug]/`:
    + `/[tenant_slug]` (`page.tsx`): Trang chủ khám phá dịch vụ lẻ & gói liệu trình của Spa.
    + `/[tenant_slug]/book` (`book/page.tsx`): Booking Wizard 4 bước (1. Chọn đa dịch vụ hoặc áp dụng Thẻ liệu trình 0đ -> 2. Chọn KTV hoặc Spa tự sắp xếp -> 3. Chọn Ngày & Khung giờ trống `available-slots` -> 4. Xác nhận đặt lịch + đăng nhập/đăng ký nhanh inline).
    + `/[tenant_slug]/appointments` (`appointments/page.tsx`): Quản lý lịch hẹn (Tab "Sắp tới" + nút Hủy lịch trước >= 2 giờ, Tab "Lịch sử").
    + `/[tenant_slug]/profile` (`profile/page.tsx`): Hồ sơ cá nhân & danh sách Thẻ liệu trình kèm thanh tiến độ `used_sessions / total_sessions`.
    + `/[tenant_slug]/login` & `/[tenant_slug]/register`: Đăng nhập / Đăng ký thành viên theo từng Spa.
  - Kiểm thử Build: `cd frontend && npm run build` thành công 100% cho toàn bộ routes `/admin/*` và `/[tenant_slug]/*`.

## Ghi chú kiến trúc & Biến môi trường đã thiết lập
- **Backend Port:** 8000 (Host: ${BACKEND_PORT:-8001} do port 8000 đang được dùng bởi project khác)
- **Frontend Port:** 3000 (`NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`)
- **Database:** PostgreSQL Port 5432 (Host: ${POSTGRES_PORT:-5433} do port 5432 đang được dùng bởi project khác)
- **Tổng kết toàn dự án (Sprints 1–6):**
  - **Backend (FastAPI + PostgreSQL 16 RLS + Alembic):** 25/25 automated tests PASSED (`pytest -v`), đảm bảo cô lập Multi-tenant 2 lớp (Application DI + PostgreSQL `FORCE ROW LEVEL SECURITY`), chống trùng lịch bằng `SELECT ... FOR UPDATE`, tự động trừ buổi thẻ liệu trình khi `COMPLETED`, báo cáo hoa hồng KTV và gửi thông báo In-App + Web Push bất đồng bộ.
  - **Frontend (Next.js 14 App Router + TypeScript Strict + TailwindCSS + shadcn/ui):** Tách biệt hoàn toàn phân hệ Quản trị `src/app/(admin)/admin/*` và phân hệ Khách hàng PWA `src/app/[tenant_slug]/*`, build production (`npm run build`) đạt 100%.
