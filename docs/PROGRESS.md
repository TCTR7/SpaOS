# TIẾN ĐỘ DỰ ÁN & TRẠNG THÁI HIỆN TẠI (PROJECT PROGRESS)

*Quy tắc cho AI: Sau khi hoàn thành mỗi Sprint hoặc Task lớn, hãy tự động cập nhật trạng thái `[x]` vào file này và ghi chú ngắn gọn các file quan trọng vừa tạo.*

## Đọc trước khi bắt đầu task: định hướng đa chi nhánh

- [x] Đã lưu [MULTI_BRANCH_STRATEGY.md](MULTI_BRANCH_STRATEGY.md) ngày 17/10/2026: deployment riêng từng chủ spa, nhiều chi nhánh, đăng nhập chung và dashboard tổng hợp.
- [x] **PO đã cho phép triển khai ngày 17/10/2026.** Đang thực hiện; xem mục triển khai đa chi nhánh ở cuối tài liệu.
- Conversation mới đọc tài liệu trên và kết quả triển khai ở cuối PROGRESS, phân biệt kế hoạch với phần đã kiểm chứng; tiếp tục trong phạm vi PO đã cho phép.

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

## Audit Codex — 16/10/2026
- [x] Audit 7 mục; báo cáo: `docs/AUDIT_2026-10-16.md`.
- [x] Vá deadlock package/booking và notification FK/auto-assign; buffer qua ngày; expiry thẻ thiếu offset; crash trang reports. Thêm tenant filter cho eager booking items, serialize subscribe theo tenant+endpoint. Đồng bộ API_CONTRACT với response thực tế.
- [x] Thêm 6 test backend trong `backend/tests/test_audit_regressions.py`, 1 E2E reports trong `automation_test/features/admin_reports/tests/test_reports.py`. Backend: 30/30 suite + 1/1 FK regression chạy riêng PASS; frontend build PASS.
- [x] E2E từng đạt 8/10 ở SLOW_MO=0; đã sửa readiness đăng nhập trong đợt release hardening bên dưới, full suite hiện đạt 11/11.
- Đối chiếu auth E2E: SLOW_MO=600 đạt 3/3 PASS; SLOW_MO=0 đạt 1/3. Cần chờ readiness/response rõ ràng, không dựa vào slow_mo để bảo đảm ổn định.

## Release hardening — 16/10/2026
- [x] API CUSTOMER `GET /customer-packages/me` cô lập theo JWT, trả số buổi giữ chỗ/khả dụng; PWA profile và booking dùng API riêng, hiển thị lỗi tải thẻ.
- [x] Đồng bộ `vapid-public-key` với frontend (`enabled`), payload push điều hướng đúng tenant/người nhận; đồng bộ kiểu unsubscribe/read-all.
- [x] Admin login chỉ nhận thao tác sau hydration; E2E chờ response đăng nhập đúng mã 200/401/404; wizard chờ response slots cho ngày đã chọn.
- [x] Backend full suite **33/33 PASS**; production build PASS; E2E headless **11/11 PASS với SLOW_MO=0**. Hai lượt E2E liên tiếp đều qua auth 3/3; lượt đầu lỗi fixture của test mới, đã sửa sang browser_instance trước lượt full PASS.
- [x] Test backend mới: quyền và cô lập thẻ cùng/khác tenant; giữ chỗ qua các trạng thái, hoàn thành idempotent, hủy giải phóng buổi. E2E mới xác minh dùng thẻ 0đ và số buổi giữ chỗ.
- [x] Service Worker kiểm tra mô phỏng 3 URL (2 tenant khác nhau và admin) PASS. Push backend dùng mock, chưa gửi trên thiết bị thật.
- [ ] Trước phát hành: đo tải đại diện spa 10 nhân viên, thử backup/restore, kiểm tra HTTPS và Web Push thiết bị thật. Chưa xác nhận production-ready.
- Mốc bàn giao model nhỏ hơn: UI/copy/docs và hướng dẫn vận hành có phạm vi rõ; sửa RLS/transaction/concurrency cần review chuyên sâu và chạy regression.

## Kiểm chứng vận hành local — 16/10/2026
- [x] Thêm và chạy `backend/scripts/release_load_check.py`: HTTP thật, tenant riêng, 10 KTV, 20 khách tranh cùng giờ → đúng 10 x 201 và 10 x 409, không trùng KTV; 200 lượt đọc với concurrency 10 → 200/200 HTTP 200. Booking thử thành công đã được hủy, giữ tenant để điều tra.
- Kết quả lượt cuối: p95 booking burst 1955.8ms; slots 237.5ms; calendar 271.6ms; reports 228.2ms; notifications 254.4ms. Ngưỡng thử local 2000ms PASS; burst sát ngưỡng, chưa suy ra sức chứa production hoặc nhiều spa đồng thời.
- [x] Thêm và chạy `scripts/db_recovery_check.py`: backup custom-format 228120 bytes; restore trong PostgreSQL 16 tạm không có network; 10 bảng khớp số dòng, 8 bảng nghiệp vụ có ENABLE/FORCE RLS và policies khớp. Role probe không bypass kiểm tra không context/đúng tenant PASS. Container/volume tạm được dọn.
- Kiểm tra bảo vệ nguồn thay đổi đã hoạt động: lượt đầu chạy cùng load dừng vì inventory thay đổi; lượt sau chạy khi hết ghi đã PASS. Diễn tập bỏ owner/grants; quyền runtime thực tế cần xác nhận khi triển khai.
- [x] Thêm `docs/RELEASE_RUNBOOK.md` với lệnh chạy lại, lưu backup, giới hạn kiểm thử và checklist push thiết bị thật; bỏ qua `backups/`, `*.dump` trong .gitignore.
- [ ] Còn cần môi trường staging HTTPS và thiết bị thật để xác minh push; chạy tải với dữ liệu/cấu hình production, lịch backup ngoài máy chủ và diễn tập phục hồi đầy đủ role/secrets trước phát hành.


## Review sửa lịch và quyền KTV — 17/10/2026
- [x] Hoàn tất 10 E2E regression đang dang dở: hủy lịch trả buổi, khóa nút hủy sát giờ (clock giả lập), dùng hết thẻ/idempotent completion, API thẻ lỗi và phục hồi, customer không vào Admin, token sai bị xóa, login/logout UI, đọc thông báo, đổi spa không tái dùng token, slot bị chiếm trước xác nhận. Tenant/khách riêng mỗi ca.
- [x] Review phát hiện frontend đã có sửa lịch bằng hủy rồi tạo mới và lọc quyền trên client; backend chưa có enforcement. Thay bằng PATCH /bookings/{id} atomic, giữ ID/items/giá/thời lượng/trạng thái; lỗi không làm mất lịch cũ.
- [x] Chốt theo PO: khách có KTV phụ trách cố định; chỉ Admin chuyển quyền. Thêm User.assigned_staff_id và migration 0003_customer_owner, đã chạy local. STAFF tạo khách được gán mình; booking thành công đầu tiên gán người phụ trách nếu chưa có; booking sau không thay đổi quyền.
- [x] API customers/packages/bookings lọc theo quyền; chặn truy cập trực tiếp ID ngoài phạm vi. Admin chuyển quyền tại CRM; đổi chủ hồ sơ không tự đổi KTV của lịch đã đặt. Khách cũ chưa phân công cần Admin gán hoặc được gán tại booking thành công đầu tiên sau migration.
- [x] Thông báo chỉ gửi Admin/chủ hồ sơ hiện tại; lọc lịch sử theo quyền hiện tại, kiểm tra lại trước dispatch push. Tránh session lồng nhau khi giữ khóa để không cạn pool.
- [x] Thêm 9 test backend trong backend/tests/test_ownership_reschedule.py: schema, tenant/role, thu hồi quyền, giá và buổi giữ chỗ, rollback, tranh slot giữa hai khách, hết hạn thẻ/cutoff và draft push cũ.
- [x] Thêm 3 E2E chuyển chủ hồ sơ qua CRM và dời lịch thành công/xung đột; POM tại automation_test/features/customer_regressions/pages/appointments_page.py.
- [x] Kiểm thử cuối: backend full suite **41/41 PASS** (115.55s) + test draft push mới **1/1 PASS** (5.00s), tổng 42 test đã kiểm chứng; frontend production build PASS; E2E full suite **24/24 PASS**, headless SLOW_MO=0 (81.66s). Không gọi kết quả backend là một lượt full suite 42/42.
- Thanh toán theo quyết định PO: xác nhận thủ công, ghi tiền thực nhận/phương thức/người xác nhận; không tích hợp QR/webhook ngân hàng trong phạm vi này. Module đã triển khai trong mục Thu tiền thủ công, nhật ký và bàn giao KTV bên dưới.


## Thu tiền thủ công, nhật ký và bàn giao KTV — 17/10/2026
- [x] Thêm migration 0004_manual_payments (đã áp dụng local): purchase_price của thẻ, payment_invoices/payment_entries/audit_logs; ENABLE/FORCE RLS theo tenant, trigger chặn sửa/xóa ledger và audit.
- [x] Admin lập phiếu từ lịch hẹn/thẻ; giá lấy snapshot đã chốt. Thẻ cũ không có giá phải được Admin xác nhận, không backfill theo menu hiện tại. Thu nhiều phần, chặn vượt số còn phải thu, hủy bằng bút toán âm có lý do.
- [x] Thu/hủy có UUID idempotency tenant-scoped và khóa invoice; retry cùng payload không ghi trùng. Giao dịch khác cùng lúc vẫn không thu vượt. Tiền được xử lý Decimal ở backend.
- [x] Màn hình /admin/payments: tìm khách, mở phiếu, thu/hủy thủ công, xem người xác nhận/thời gian, lịch sử và báo cáo thực thu theo ngày Việt Nam; STAFF/CUSTOMER không truy cập được. Thực thu tách khỏi báo cáo giá trị dịch vụ.
- [x] Audit cùng transaction cho lập/thu/hủy tiền, tạo/sửa hồ sơ, cấp thẻ, giao KTV, tạo/đổi trạng thái/hủy/dời lịch. Không sao chép mật khẩu hoặc nội dung ghi chú sức khỏe vào nhật ký.
- [x] Dời lịch có transfer_customer=true chỉ dành cho Admin, checkbox mặc định tắt. Nếu chọn, quyền hồ sơ và lịch đổi cùng transaction; trùng slot thì cả hai giữ nguyên. Bỏ chọn vẫn giữ chủ hồ sơ cố định.
- [x] Thêm 9 test backend trong backend/tests/test_manual_payments.py; backend full suite **51/51 PASS** (140.98s).
- [x] Thêm 4 E2E: thu một phần/đủ/hủy, retry sau response bị mất, chặn STAFF, Admin bàn giao tại dời lịch. Full suite **28/28 PASS**, headless SLOW_MO=0 (94.97s).
- [x] Production build cuối PASS; chạy lại nhóm E2E thu tiền **3/3 PASS** (14.75s) sau sửa formatter, có assertion số tiền 12.345,67 và retry giữ cùng UUID. Không thay đổi kết quả backend.
- [x] Cập nhật API_CONTRACT, RELEASE_RUNBOOK và probe recovery cho 11 bảng nghiệp vụ.
- Giới hạn: chưa có kết nối ngân hàng, giảm giá/sửa giá phiếu, hóa đơn thuế hoặc phân quyền thu ngân riêng. Hủy bút toán không chuyển tiền hoàn cho khách. Các hạng mục staging HTTPS/push thật/backup production vẫn cần thực hiện.
- [x] Backup/restore sau migration tiền PASS: 13 bảng khớp số dòng, policies khớp; role không bypass kiểm tra RLS không context và đúng tenant PASS cho 11 bảng nghiệp vụ. Restore chạy trong PostgreSQL tạm tách biệt, không thay database ứng dụng; chưa kiểm chứng owner/grants production.


## Đơn giản hóa màn hình thu tiền — 17/10/2026
- [x] Theo PO: bỏ bước chọn khách/nguồn và Mở phiếu thu; Admin → Thu tiền tự hiển thị danh sách lịch/thẻ đã có dữ liệu, giá chốt, đã thu/còn thiếu; tìm tên/SĐT, phân trang, mặc định Còn cần thu.
- [x] API GET /payments/collections chỉ ADMIN, lọc tenant trên mọi nguồn/join, aggregate SQL một query; không ghi dữ liệu khi xem. Thẻ cũ chưa có giá cần đối chiếu; lịch dùng thẻ không thu thêm; không lấy giá menu mới thay giá đã chốt. Lịch hủy/no-show chưa có invoice được loại; nguồn đã có invoice giữ để đối chiếu.
- [x] Xác nhận mặc định toàn bộ số còn thiếu, chọn tiền mặt/chuyển khoản. Trả một phần và lịch sử/hoàn tác là thao tác phụ; nhật ký chung chuyển tab Lịch sử thao tác. Tổng hôm nay tự tải và cập nhật. Giữ idempotency khi mất response; khóa thu tiếp nếu ghi thành công nhưng tải lại thất bại.
- [x] Thêm 3 backend regression (danh sách tự động/không ghi/tenant/quyền/tìm kiếm/phân trang; trạng thái và hoàn tác/lịch hủy; giá thẻ cũ). Module thanh toán **12/12 PASS (31.25s)**. Frontend production build PASS.
- [x] Cập nhật 3 E2E và thêm 3 ca: thu đủ mặc định/tìm kiếm/lọc; lịch dùng thẻ; ghi thành công nhưng tải lại lỗi. Module thu tiền **6/6 PASS (24.72s)**, headless SLOW_MO=0, cổng thử 3001. Không chạy lại toàn bộ suite trong đợt này.
- [x] Cập nhật API_CONTRACT, PRD và RELEASE_RUNBOOK; không cần migration mới. Đã tắt server thử 3001 sau kiểm thử; không khởi chạy frontend ở cổng 3000 trong đợt này.


## Triển khai đa chi nhánh — 17/10/2026
- [x] PO phê duyệt triển khai sau khi lưu chiến lược. Bản đầu: mỗi chủ spa một deployment riêng; tài khoản quản trị dùng chung, hồ sơ/thẻ/dịch vụ/giá/nhân sự theo chi nhánh. Giữ tenant_id và toàn bộ ID nghiệp vụ; không gộp dữ liệu các chủ độc lập.
- [x] Migration 0005_branch_accounts đã áp dụng local: login_accounts (danh tính cấp deployment có FORCE RLS account/phone bootstrap), branch_memberships (tenant_id/FK kép tenant-user, FORCE RLS). SĐT quản trị duy nhất được chuyển đổi; trùng số bị bỏ qua, không tự gộp.
- [x] Đăng nhập ADMIN/STAFF bằng SĐT/mật khẩu không slug; API header cũ và PWA còn tương thích. Tài khoản mới/đổi credentials đơn chi nhánh đồng bộ danh tính chung; tài khoản nhiều chi nhánh chặn đổi credentials từ API chi nhánh. Khóa account/membership/user/tenant được kiểm tra khi truy cập.
- [x] API /branches, tạo chi nhánh cho chủ, switch cấp JWT theo membership đã xác minh; cấp STAFF làm thêm chi nhánh của cùng chủ; tắt STAFF tại đích thu hồi quyền/token đích ngay. Không tự sao chép hồ sơ khách, ca làm hoặc dịch vụ.
- [x] /admin/login bỏ slug/seed credentials/lời mời đăng ký public; /admin/branches tạo và cấp quyền; header dropdown desktop/mobile chuyển chi nhánh. Chuyển token xong tải lại để xóa state cũ, hủy subscription Push trước đổi, tab khác reload theo storage event.
- [x] /admin/dashboard thay redirect cũ bằng số liệu ngày Việt Nam, dashboard riêng/tổng các chi nhánh owner/Admin được cấp. Tiền thực thu/giá trị dịch vụ hoàn thành tách rõ; khoản còn thiếu tính toàn bộ nguồn không cắt trang; thẻ hiện tại và giá cũ chưa đối chiếu có chú thích. RLS nghiệp vụ không nới cho tổng hợp; query chạy theo từng tenant đã xác minh.
- [x] Trang / cho khách chọn tên chi nhánh; URL PWA/token customer theo slug được giữ. Chưa dùng thẻ xuyên chi nhánh hoặc gộp tài khoản/hồ sơ khách.
- [x] ENVIRONMENT, ALLOW_TENANT_REGISTRATION, BRAND_NAME qua Compose; production tắt đăng ký mới theo mặc định. Bỏ container_name cố định để dùng Compose project/DB/volume/secrets/domain riêng. CLI scripts.bootstrap_deployment khởi tạo database rỗng qua password nhập kín; scripts.branch_account_audit báo cáo và chuyển từng user cũ đã đối chiếu, không tự gộp.
- [x] Thêm backend/tests/test_branches.py (8 ca) và feature E2E admin_branches (3 ca, có POM); cập nhật 3 test đăng nhập theo luồng mới. Backend full suite cuối **62/62 PASS (178.57s)**; E2E full suite cuối **34/34 PASS (120.82s)**, headless SLOW_MO=0.
- Ghi nhận kiểm chứng: lượt đầu backend 60/60 PASS trước 2 regression bổ sung; E2E đầu 33 PASS/1 setup disconnect do sửa Python kích hoạt reload server local trong lúc chạy. Lượt full ổn định sau đó 34/34 PASS; không thêm retry để che lỗi.
- [x] Frontend production build PASS; bản cuối chỉ bỏ lời mời đăng ký mới khỏi trang login sau lượt full E2E, không đổi luồng đăng nhập. Server thử 3001 đã tắt; không khởi chạy/tắt server người dùng ở cổng 3000.
- [x] Backup/restore local sau 0005 PASS: 1,287,838 bytes, 15 bảng khớp inventory và policies, 12 bảng tenant + danh tính FORCE RLS. Probe không context/tenant scope/account membership/phone bootstrap PASS; account context không đọc được users. Container/volume phục hồi tạm được dọn. Vẫn chưa kiểm chứng owner/grants production.
- [x] Recovery CLI hỗ trợ --compose-project/--env-file để chọn đúng deployment. API_CONTRACT, PRD, MULTI_BRANCH_STRATEGY, RELEASE_RUNBOOK, AGENTS được cập nhật.
- [ ] Trước production: đối chiếu tài khoản cũ chưa liên kết; tách dữ liệu nếu database cũ chứa nhiều chủ độc lập trước công bố directory chi nhánh. Kiểm tra staging HTTPS/Push thiết bị thật, quyền runtime/backup tự động/giám sát, tải dashboard theo số chi nhánh thực tế. Không suy từ test local rằng đã production-ready.


## Quản trị triển khai cấp chủ spa — 17/10/2026
- [x] Theo PO: seed duy nhất danh tính quản trị của đơn vị triển khai, tạo chủ spa qua giao diện riêng; chủ spa tiếp tục luồng Admin/chi nhánh hiện có. Đây là portal trong từng deployment, không tự chuyển thành control plane quản lý các server khách.
- [x] Thay CLI bootstrap nhập tên qua terminal (đã gây surrogate Unicode) bằng /operator/login và /operator. Script cũ chỉ in hướng dẫn, không hỏi nhập hoặc tạo owner.
- [x] Migration 0006_operator_portal đã chạy local: deployment_operators singleton (danh tính hạ tầng FORCE RLS), owner_provisions tenant-scoped/FORCE RLS/append-only. Không sửa/xóa account hoặc dữ liệu kinh doanh cũ.
- [x] app.seed chỉ tạo operator từ OPERATOR_PHONE/NAME/PASSWORD; không có credential mặc định, không tự reset mật khẩu/quyền đã tồn tại. Demo chuyển sang app.seed_demo, chặn production. Docker startup chạy seed sau migration nếu đã cấu hình; .env.example và Compose chuyển biến bí mật đúng phía backend.
- [x] Operator JWT có audience/scope riêng, 30 phút, kiểm tra active/token_version; đăng xuất thu hồi phiên. Sai 5 lần khóa 5 phút. Không dùng UserRole SUPER_ADMIN hoặc DB superuser/bypass RLS, không cho token operator gọi API hồ sơ/booking/chi nhánh.
- [x] Operator tạo owner + chi nhánh đầu + account + membership + lịch sử + audit atomic; request_id/HMAC chống tạo trùng sau mất response. Tên nhập web UTF-8; không lưu/hiện password trong danh sách, không nhận role/tenant/operator_id từ body.
- [x] Production chặn public register-tenant hoàn toàn; guard không tạo chủ độc lập trên database đã có tenant. Không tự gộp hoặc nhận owner cũ; thêm chi nhánh vẫn theo quyền chủ.
- [x] Đồng bộ kiểm tra account/membership/tenant active trong booking_deps (đường xác thực optional trước đây chưa đồng bộ với get_current_user); regression chặn JWT chi nhánh bị khóa tại cả services/bookings.
- [x] Thêm 7 backend test operator và scripts.test_isolated tạo/migrate/test/drop database QA riêng. Full suite cuối **69/69 PASS (203.61s)**, không seed operator QA vào database ứng dụng.
- [x] Feature E2E operator_portal có POM và API/container/database tạm thật: token riêng/logout, tạo owner tên Trần Cao Trung + chủ spa đăng nhập dashboard, retry response mất giữ cùng body/UUID. Full suite cuối **37/37 PASS (142.17s)**, headless SLOW_MO=0.
- [x] Sửa teardown harness Playwright: bỏ route khi đóng context với ignoreErrors chỉ trong cleanup để không phát sinh callback của request nền đã hủy; assertion luồng chính vẫn đợi API/dashboard thật. API/DB QA tạm được dọn sau fixture.
- [x] Production build PASS; server thử 3001 đã tắt, không thao tác server người dùng ở 3000. API_CONTRACT, PRD, MULTI_BRANCH_STRATEGY, AGENTS, RELEASE_RUNBOOK cập nhật quy trình mới.
- [x] Backup/restore sau 0006 PASS: 1,342,289 bytes, 17 bảng khớp inventory/policies; no-context/tenant/account probes PASS. Hai bảng mới có FORCE RLS; operator/provision hiện có 0 dòng trong database ứng dụng nên probe operator có dữ liệu được kiểm chứng qua test QA riêng, không nhận là đã seed operator thật. Vẫn chưa kiểm chứng owner/grants production trong restore.
- Ghi nhận QA: một lượt backend trước đạt 68/69 với 401 trong test quyền hồ sơ cũ; chạy chuỗi operator + test đó đạt 8/8, lượt full sau đạt 69/69. Chưa xác định nguyên nhân 401 gián đoạn; không nới kiểm tra JWT hoặc thêm retry để che lỗi. Tiếp tục theo dõi khi chạy CI. Lượt E2E trước qua assertion 37 ca nhưng lỗi teardown; chỉ lấy lượt full cuối 37/37 sạch làm kết quả hoàn tất.
- [ ] Cần người vận hành đặt OPERATOR_PHONE/OPERATOR_PASSWORD bí mật của chính mình và rebuild/recreate backend đúng deployment để seed tài khoản thật. Không tự đặt mật khẩu công khai hoặc xóa demo/owner hiện có. Production đã có dữ liệu cần kiểm kê/tách đúng deployment, không xóa DB để vượt guard.
- [ ] Trước phát hành: staging HTTPS, proxy kiểm soát đường operator/tốc độ, secrets riêng và các gate backup/giám sát/push thật còn hiệu lực.
