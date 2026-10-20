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


## Màu thương hiệu qua Operator — 17/10/2026
- [x] Operator có bảng chọn màu/HEX/xem trước và Lưu màu thương hiệu; chọn màu ngay khi tạo owner. Màu chung từng deployment, áp dụng Admin/đăng nhập/PWA khách và mọi chi nhánh; deployment khác độc lập. Chữ nút tự chọn đen/trắng, chữ nhấn tăng độ tương phản; trạng thái lỗi/cảnh báo giữ màu riêng.
- [x] Migration 0007_branding đã áp dụng local: deployment_branding singleton cấu hình giao diện, ENABLE/FORCE RLS public SELECT chỉ cho cấu hình màu và ghi theo Operator active. Không thay RLS bảng nghiệp vụ. API chỉ công khai theme_color/configured; HEX 6 chữ số, extra forbid, không nhận tenant_id. Tạo owner + màu atomic, digest cũ bỏ màu còn tương thích.
- [x] API GET /branding, GET/POST /operator/branding; public tenant trả màu chung nếu đã cấu hình, còn lại giữ màu cũ. Admin settings không ghi đè màu Operator; server render/viewport/manifest dùng BACKEND_INTERNAL_URL và fallback khi API lỗi, tab refresh màu khi focus/storage.
- [x] Thêm 4 test backend branding: validation, role/RLS, public DTO, rollback/idempotency/digest. Target branding + Operator 11/11 PASS. Thêm E2E đổi xanh/vàng qua Operator, owner login/Admin/Customer thật và chữ đen trên nền vàng.
- [x] Toàn bộ E2E chuyển sang container/database QA tạm, seed demo/Operator chỉ trong QA, ApiHelper và browser dùng chung API thật tạm. Lượt đầu cũ thiếu spa-demo trong DB ứng dụng; không seed demo/reset credentials vào DB đó để vượt test. Lượt đầu dùng harness cũ vẫn tạo một số bản ghi tenant/khách QA trong DB local ứng dụng; không tự xóa dữ liệu hiện có. Các lượt QA tiếp theo không ghi vào DB ứng dụng; cần kiểm kê dữ liệu local trước khi bàn giao production.
- [x] Sửa harness: request giả lập mất response vẫn tới QA, retry dùng route.fallback; request kiểm tra quyền dùng API QA; POM lịch chờ API hydration/ngày và PATCH status thật trước kiểm tra số buổi. Full E2E 38/38 PASS (159.10s), headless SLOW_MO=0, trước bản vá clock skew dưới đây.
- [x] Xác định nguyên nhân 401 gián đoạn đã ghi ở mục trước: captured log ImmatureSignatureError trong test_sprint2_crud, không phải SecretStr/plaintext. Thêm log loại lỗi không chứa token/password, dung sai JWT cố định 2 giây cho nghiệp vụ và Operator; vẫn kiểm tra chữ ký/audience/scope/version/expiry. Hai regression clock đóng băng thời gian PASS (1.42s), kiểm tra iat +1 giây được nhận, +3 giây/hết hạn -3 giây/sai chữ ký/audience/scope/version bị chặn. Vẫn cần đồng bộ NTP host/container.
- [x] Frontend production build PASS. Backup/restore sau 0007 PASS: 119944 bytes, 18 bảng khớp inventory/policies; FORCE RLS mới và public branding scope kiểm tra, no-context/tenant/account/operator probes PASS. Branding thật hiện chưa cấu hình (0 dòng), có dữ liệu được kiểm chứng qua QA; restore vẫn loại owner/grants.
- [x] Sau vá clock skew: backend full suite 75/75 PASS (192.78s), E2E auth + Operator 7/7 PASS (52.18s). Full E2E trước đó 38/38 PASS; không tính các lượt 72/73 trước vá là PASS toàn bộ. Các database/container QA tạm đã được dọn.
- API_CONTRACT, PRD, MULTI_BRANCH_STRATEGY, RELEASE_RUNBOOK đã cập nhật. Giới hạn staging HTTPS/Push thiết bị thật/role runtime/backup ngoài máy chủ trước production vẫn còn hiệu lực.


- [x] Đã tắt server Next thử do Codex mở ở 3001 (PID 29108, xác minh command start -p 3001); listener 3000 của người dùng vẫn chạy (PID 36348).


## Review UI/UX trước pilot — 18/10/2026
- Theo PO: lưu nhận xét và tiếp tục review bố cục lịch/thẻ/tràn nội dung, ưu tiên trải nghiệm PC và điện thoại. Backlog, mức ưu tiên và tiêu chí nghiệm thu tại [UI_UX_REVIEW.md](UI_UX_REVIEW.md).
- Đang thu bằng chứng Chromium ở 360/390/768/1024/1366px qua automation_test/reviews/layout_probe.py, API/database QA tạm. Chưa thay đổi UI; không coi test nghiệp vụ PASS là visual/accessibility PASS.

- [x] Review bố cục trực tiếp: 31 ảnh/DOM ở 5 viewport, collector hoàn tất 58.80s. Xác nhận lịch tuần bị cắt/tràn nội dung trên 768px và 1366px; ghi chú dài kéo trang 390px thành 1821px. Thu tiền mobile chật, thẻ còn ACTIVE và diễn đạt buổi giữ chỗ cần cải thiện. Bằng chứng/link ảnh trong UI_UX_REVIEW.md.
- [ ] Chưa vá UI trong lượt review; chưa kiểm chứng Safari/iOS/Android thật, bàn phím ảo, zoom và dữ liệu 10 KTV/nhiều lịch. Collector PASS không phải UI PASS.

## Review sâu mobile và hướng thiết kế — 18/10/2026
- [x] Theo PO tiếp tục review/design ưu tiên phone: bổ sung UX-13 đến UX-20 trong UI_UX_REVIEW.md (KTV bằng mã, lỗi mạng/auth, tự chọn giờ/nhảy bước, lookup 200 khách, nhãn KTV thực hiện, dashboard, đổi chi nhánh, chữ phụ trên theme sáng). Đây là review source, chưa runtime-test các lỗi mạng hoặc dữ liệu >200 trong lượt này.
- [x] Lưu thiết kế tác vụ theo vai trò và từng màn hình tại [MOBILE_UX_DESIGN.md](MOBILE_UX_DESIGN.md), gồm điều hướng, lịch agenda, thu tiền, CRM/thẻ, wizard, phục hồi lỗi, accessibility, tiêu chí nghiệm thu và trình tự triển khai.
- [ ] Chưa sửa UI hoặc API, chưa chạy test/build mới; bằng chứng hình ảnh hiện có vẫn là 31 mẫu ở lượt review trước. Bước tiếp theo là triển khai các lỗi P1 và nghiệm thu theo tài liệu thiết kế, không coi đề xuất đã được triển khai.

## Kế hoạch bàn giao review UI/UX cho model nhỏ — 18/10/2026
- [x] Review bổ sung UX-21–24: tạo nhiều buổi thành công một phần, response lịch cũ, ý định dời lịch/giữ KTV và dữ liệu tham chiếu lỗi bị bỏ qua. Mới xác nhận cấu trúc source/rủi ro, chưa chạy fault-injection để kết luận dữ liệu trùng.
- [x] Lập [UI_UX_EXECUTION_PLAN.md](UI_UX_EXECUTION_PLAN.md): T00–T12, dependency/file/acceptance/tests, prompt bàn giao mặc định KIỂM TRA, invariant và mốc cần reviewer chuyên sâu. Model nhỏ có thể bắt đầu kiểm tra T00 rồi T03/T04; không mặc định được sửa giao dịch/API từ task layout.
- [ ] Chưa triển khai UI theo plan, không có build/test/ảnh mới trong lượt lập kế hoạch; các số test trước là kết quả lịch sử.


## Chốt lại review và plan UI/UX trước bàn giao — 18/10/2026

- [x] Rà source/fixture và sửa [UI_UX_EXECUTION_PLAN.md](UI_UX_EXECUTION_PLAN.md) bản 2: chia task lá, thứ tự dependency, điều kiện đầu vào/đầu ra, phạm vi file và phần cần chốt API/giao dịch.
- [x] Bổ sung UX-25/26 trong [UI_UX_REVIEW.md](UI_UX_REVIEW.md): mất phiên Admin khi lỗi mạng và báo nhầm Spa không tồn tại khi public tenant lỗi. Đây là source review, chưa fault-injection runtime.
- [x] Ghi QA-01–03: fixture fallback mở 3000 dù FRONTEND_URL khác; route browser không bao phủ SSR; collector ghi đè artifact và chưa có assertions clipping. Đưa T00a/T00b/T00c lên đầu.
- [x] Đồng bộ thiết kế/plan, bổ sung coverage login/chọn chi nhánh/settings/Operator và sửa mô tả register-tenant production cũ trong API_CONTRACT để khớp code hiện hành; không đổi endpoint.
- [ ] Chưa sửa code ứng dụng hoặc test harness. Không chạy build/test/collector mới, không mở/tắt server. Kết quả test/31 ảnh trước đó vẫn là bằng chứng lịch sử.
- [ ] Có thể giao model nhỏ KIỂM TRA hoặc TRIỂN KHAI riêng T00a. T00b/T00c là điều kiện trước QA runtime; T01a/T08a/T09b cần reviewer chốt quyết định, T07/T11b cần review phiên/quyền. Không giao toàn bộ plan để model nhỏ tự suy diễn.


## T00a — Chặn harness mở nhầm frontend — 18/10/2026

- [x] Theo PO triển khai riêng T00a: thay ensure_frontend_server bằng preflight chỉ đọc, bỏ hoàn toàn npm/subprocess/kill frontend. isolated_backend chỉ setup sau preflight.
- [x] Thêm common_setup/frontend_preflight.py: kiểm tra HTTP loopback/port riêng khác 3000, 200 text/html tại /admin/login và X-SpaOS-QA-Run-ID khớp SPAOS_QA_RUN_ID. Không redirect/proxy, không fallback server khác; thông báo không lộ URL chứa credential/query hay response body. Default frontend 127.0.0.1:3001; không đổi .env/.env.test.
- [x] Thêm 12 unittest độc lập tại automation_test/harness_tests, chạy bằng python -B -m unittest discover -s automation_test/harness_tests -v. Baseline fixture cũ: đúng 3 regression FAIL, lệnh start bị mock chặn. Sau vá: 12/12 PASS trên Python 3.9 của môi trường automation. Không mở server/browser/database.
- [x] Cập nhật trạng thái plan/review và contract nối T00b. Không đổi endpoint nghiệp vụ hoặc UI.
- [ ] Tiếp theo T00b: runner tạo frontend QA với marker cùng UUID, output riêng và backend SSR/rewrite/browser cùng QA. Cho đến khi hoàn tất, preflight chủ động chặn E2E không có marker; không bỏ kiểm tra để dùng server 3000. T00c và các UX task khác chưa triển khai.

## Nhóm A — Nền QA và UI cơ bản — 18/10/2026

- [x] PO đã cho phép gộp task liên quan để triển khai cùng đợt. Hoàn tất T00b/T00c/T04a/T04b; cộng T00a là 5/29 task, còn 24. Thứ tự nhóm tiếp theo được lưu trong UI_UX_EXECUTION_PLAN.
- [x] T00b: thêm run_ui_qa.py và common_setup/qa_frontend.py, một backend/database QA dùng chung; frontend output/tsconfig/build-info riêng, marker cùng run UUID. Bỏ universal browser/API forwarding để dùng rewrite thật; HTTP kiểm chứng tenant QA duy nhất qua API rewrite và title SSR. Production build PASS, fingerprint tsconfig/next-env không đổi do runner, cấu hình thường không bật QA header/output override.
- [x] Unit harness 23/23 PASS: không tự dùng cổng 3000; cổng bị chiếm không bị kill/reuse; cleanup build/start/preflight/interrupt/test lỗi; giữ exit code. Server QA chỉ quản lý PID do runner tạo.
- [x] T00c: collector 44 mẫu tại 320/360/390/430/768/1024/1366, thêm modal cao 480px và note dài; stress 14 mẫu với 10 KTV, 210 khách, 240 lịch (60/ngày). Bounds viewport/card/text clipping/control overlap lưu theo run UUID; baseline trước giữ nguyên. Tuần hiện cap 200/240 được ghi rõ cho T08. Ba strict xfail tái hiện UX-01/02; collector hoàn tất không phải UI PASS.
- [x] T04a/b: shared button/input mobile 44–48px/16px, desktop giữ kích thước; toolbar lịch wrap màn nhỏ; focus offset và icon login căn giữa. Xóa credentials mẫu wizard/login khách; trạng thái thẻ tiếng Việt, phân biệt chưa dùng/đã đặt/có thể đặt thêm; dùng một buổi không ghi 0đ. Chỉnh nhãn KTV thực hiện và selected subtitle theo foreground. POM/assertion copy đồng bộ, kiểm tra số buổi/ID/quyền/tiền giữ nguyên. Sáu ca mobile controls/theme/320px mới PASS; thiết bị thật chưa kiểm chứng.
- [x] Sửa race phát hiện khi chạy regression CRM: khởi tạo ownerId cùng selectedCustomer, bỏ effect có thể ghi đè lựa chọn mới sau render. Test chuyển người phụ trách và thu hồi quyền nhân viên cũ đã PASS trong production run. Không đổi API/quyền; phần bố cục CRM vẫn chờ T10a.
- [ ] Full E2E CHƯA XANH: lượt production có 42 PASS/2 setup ERROR (188.65s), backend ghi ImmatureSignatureError ở bước tạo dữ liệu. Lượt focused cuối 7 PASS/3 XFAIL/1 setup ERROR (20.20s); lỗi setup này còn tái diễn. Không tăng JWT leeway, không retry/sleep để che. Cần điều tra claim iat/đồng hồ runtime; gắn blocker QA-04 trước T12. Các test invalid-token chủ ý có DecodeError riêng, không nhầm với lỗi setup.
- Bằng chứng: artifacts/qa/d0bfa806-135e-428f-9c67-1f15daaacfd1 (production full + stress); artifacts/qa/3794bd1b-784d-4939-9036-014cc6c0190d (production focused); artifacts/ui-review/13122f4c-4663-4dac-a654-e65ef5556fa4 (collector 44 mẫu + known regressions). Không thay cấu hình secrets hoặc dữ liệu DB người dùng; không mở/tắt cổng 3000.

## Nhóm B — Dữ liệu và bố cục lịch — 18/10/2026

- [x] T02: scope theo tenant/user/role/ngày/view/KTV/status và request ID; data/loading/error chỉ cập nhật bởi request mới nhất, invalidate khi unmount. Snapshot hiển thị gắn scope ngay lúc render, không hiện lịch A dưới ngày B. Reload sau đổi trạng thái dùng cùng guard, old read không ghi đè kết quả mutation.
- [x] Reference data dùng allSettled, giữ riêng trạng thái dịch vụ/khách/KTV; lỗi hiển thị đúng phần và có Thử lại. Chặn mở/submit tạo lịch hoặc dời lịch khi thiếu dữ liệu cần thiết; vẫn xem lịch hoặc đổi trạng thái độc lập. Không lấy thêm dữ liệu ngoài quyền, không đổi query contract, transaction hay quyền backend.
- [x] T03a: min-width/wrap cho nội dung dài; thẻ tuần gọn với native details, mở đủ thông tin và thao tác. Mobile/tablet agenda; ngày trống một dòng. PC giữ 7 cột đủ rộng, scroll cục bộ và tự đưa ngày đang chọn vào vùng nhìn; danh sách nhiều lịch scroll trong ngày. Bộ lọc tên KTV dài không kéo rộng trang. Chưa thực hiện thiết kế hành động/focus T03b.
- [x] Thêm 7 E2E race/reference thực sự giữ/release response (ngày cũ thành công/lỗi, ngày mới lỗi/retry, đổi KTV/status, mutation chồng read, reference lỗi). Cả 7 PASS ở dev run b1fa70d6. Lượt production cuối 6 PASS/1 setup ERROR trước khi test chạy do JWT ImmatureSignatureError; giữ blocker QA-04.
- [x] Bỏ 3 strict xfail UX-01/02: test thường PASS, gồm thẻ tuần đóng/mở ở 768/1366 và note 280 ký tự ở 390. Nâng detector: bỏ qua nội dung details đóng không được paint, nhưng vẫn đo khi mở và bắt text/control chồng nhau trong cùng card; 2 ca hiệu chuẩn PASS, không loại trừ toàn card trong vùng scroll.
- [x] Production build PASS. Run a1fe3aeb-5aff-4bec-8db2-f6861f905ba3: 18 PASS/1 setup ERROR (144.74s), không xfail/skip. Gồm legacy status/trừ thẻ, 4 ownership/reschedule, các ca race, layout/calibration, collector và stress. 23 unit harness PASS ở đầu nhóm; không chạy lại backend suite vì không đổi backend.
- [x] 44 mẫu thường + 14 mẫu stress tại 320/360/390/430/768/1024/1366: documentWidth = viewport, card violations=0. Stress: 60 lịch/ngày, 10 KTV, 210 khách, 240 lịch; vẫn cap 200 lịch/tuần (UX-16/T08 chưa sửa). Đã xem ảnh phone và PC expanded; chưa kiểm chứng thiết bị thật/screen reader.
- Bằng chứng cuối: automation_test/artifacts/qa/a1fe3aeb-5aff-4bec-8db2-f6861f905ba3/ và automation_test/artifacts/ui-review/a1fe3aeb-5aff-4bec-8db2-f6861f905ba3/. Baseline lịch sử giữ nguyên. QA server/container được runner dọn; không mở/tắt 3000, không seed DB ứng dụng.
- Tiến độ UI/UX: 7/29 task, còn 22. Nhóm tiếp theo C: T05a/T05b/T03b/T06. Full E2E/release gate chưa PASS vì QA-04 và công việc còn lại.

Lệnh kiểm chứng nhóm B (PowerShell tại root; tự tạo/dọn backend, DB và frontend QA riêng):

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/admin_bookings automation_test/features/customer_regressions/tests/test_ownership_reschedule.py automation_test/reviews/test_layout_regressions.py automation_test/reviews/test_layout_measurements.py automation_test/reviews/layout_probe.py automation_test/reviews/layout_stress.py -q -s --tb=short
```

## Review lại 7 task UI/UX đã triển khai — 18/10/2026

- Theo PO review T00a/T00b/T00c/T04a/T04b/T02/T03a; đọc code/tiêu chí, chạy lại QA cô lập và bổ sung reproducer. Không thay mã ứng dụng hoặc API/backend. Không phát hiện CRITICAL mới trong phạm vi, ghi 4 WARNING ở [UI_UX_REVIEW.md](UI_UX_REVIEW.md), mục R7-01–04.
- R7-01 (T02, P1): PATCH xác nhận lịch bị giữ; đổi lọc PENDING rồi cho commit. Server CONFIRMED nhưng UI vẫn Chờ xác nhận vì callback loadBookings scope cũ bị guard bỏ qua, scope mới không invalidate. Reproducer runtime FAIL đúng assertion.
- R7-02 (T00c, P2): gate không kiểm tra viewportOutsideCount; calibration nút fixed ngoài màn hình được chấp nhận. Collector payments/notifications/customer-package dùng selector booking, cards=[]; số 0 violations không đủ kết luận card các màn này đạt. Mở lại task để sửa gate/selector và tiêu chí coverage.
- R7-03 (T04b, P2): test màu cũ đổi biến ở html nhưng CustomerShell override, cả vàng/xanh đậm thực tế vẫn hồng rgb(190,24,93). Hai ca kiểm tra premise FAIL. Test bổ sung dùng response branding qua provider thực tế PASS cả vàng/gần trắng/xanh đậm/đen; phần selected subtitle hoạt động, cần sửa fixture test chính.
- R7-04 (T04b, P2): wizard vẫn “Giá 0₫”/“Dùng thẻ (0₫)”/“Trừ thẻ (0 ₫)”; test UI xác nhận copy còn sót. Cần đồng bộ theo buổi thẻ, giữ giá/payload/ledger server.
- Unit harness: 23/23 PASS (0.507s). Production build PASS. Production run `010d1f34-5f0a-424b-8815-07bfaabe5171`: 19 PASS/4 FAIL (48.67s), các ca cũ đều PASS, ca mới xác nhận R7-01/02/03; có log Target closed từ Playwright ở teardown sau assertion R7-01, không phải bằng chứng crash ứng dụng. Dev run `1ad3e8e9-c939-4d3f-82b7-60176936e8bb`: 4 PASS/1 FAIL/4 deselected (25.60s), màu thật PASS và copy FAIL.
- Không xfail/retry/sleep để che lỗi. Reproducer lưu `automation_test/reviews/seven_task_recheck.py`, chạy tường minh (ngoài default discovery); khi vá cần đưa regression tương ứng vào suite thường. Không chạy lại full E2E/backend suite/stress 240 lịch trong lượt này; chưa xác nhận thiết bị thật. QA-04 không tái hiện ở hai lượt mới nhưng vẫn mở do chưa có bản sửa/nguyên nhân.
- Artifacts: `automation_test/artifacts/qa/010d1f34-5f0a-424b-8815-07bfaabe5171/`, `automation_test/artifacts/qa/1ad3e8e9-c939-4d3f-82b7-60176936e8bb/`; ảnh stale status tại `automation_test/artifacts/ui-review/010d1f34-5f0a-424b-8815-07bfaabe5171/seven-task-review/390x844-status-filter-after-commit.png`. Cả hai runner dùng API rewrite/SSR đúng DB QA và dọn process/container; không mở/tắt 3000 hoặc seed DB ứng dụng.
- **Điều chỉnh nghiệm thu:** đã triển khai 7 task nhưng chỉ 4 đạt phạm vi (T00a/T00b/T04a/T03a); mở lại T00c/T02/T04b. Tổng: 4/29 đã nghiệm thu, còn 25 (3 sửa lại + 22 chưa triển khai). Ưu tiên đóng R7-01–04 trước nhóm C. Đã đồng bộ checkbox và hướng bàn giao trong UI_UX_EXECUTION_PLAN/MOBILE_UX_DESIGN.

Lệnh thực tế tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m unittest discover -s automation_test/harness_tests -v
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/admin_bookings automation_test/reviews/test_mobile_controls.py automation_test/reviews/test_layout_regressions.py automation_test/reviews/test_layout_measurements.py automation_test/reviews/seven_task_recheck.py -q -s --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa --mode dev -- automation_test/reviews/seven_task_recheck.py -k 'branding_response or session_copy' -q -s --tb=short
```

Lưu ý: lệnh production khi chạy lại file reproducer hiện tại sẽ gồm thêm 5 ca đã được bổ sung cho lượt dev sau đó (bản tại thời điểm run production chỉ có 4 ca mới).

## Sửa và kiểm tra lại T02/T00c/T04b — 19/10/2026

- [x] PO yêu cầu sửa ba task mở lại; đã đóng R7-01–04. T02 dùng latest callback cho scope đang xem sau mutation, kiểm tra mounted/danh tính/chi nhánh gốc; status/create/reschedule cùng dùng. Lỗi response cũng tải lại server trước khi báo lỗi. Không replay mutation hoặc đổi payload/transaction.
- [x] 9 regression mới giữ PATCH rồi đổi bộ lọc/tuần/ngày, kiểm tra cả thành công, từ chối và response lỗi sau commit. Cộng 7 ca đọc/ref trước đó thành 16 ca calendar loading PASS. Có kiểm tra trạng thái API và GET scope hiện tại.
- [x] T00c: gate kiểm tra viewportOutsideCount và target rỗng; JSON có cardCount/cardSelector/measurementStatus. Hooks/selector đo đúng collection, notification, customer package, modal. Cuộn dọc modal được khai báo riêng, vẫn bắt tràn ngang/clipper con; 6 calibration PASS. Regression UI được đưa vào default features qua features/ui_quality/tests/test_ui_quality.py; entry point seven_task_recheck giữ tương thích, không xfail/skip lỗi.
- [x] T04b: màu qua branding provider, assert nền/foreground thật ở 4 màu; wizard chuyển nhãn 0đ sang dùng buổi thẻ, tổng có thẻ ghi số tiền thu thêm ngoài thẻ, wrap nhãn dài. Ca thẻ riêng/thẻ + dịch vụ lẻ PASS (0/125.000); E2E đặt thẻ xác minh package ID, total_price=0 và số buổi giữ chỗ. Không đổi API/giá/quyền.
- [x] Unit harness 23/23 PASS (1.002s). Dev run `cb30855f-2802-4259-b33d-221976839eaa`: 40/40 PASS (151.31s). Sau hiệu chuẩn thêm cuộn dọc, production build PASS và run `76d5ebba-de8f-4832-9f18-b1f1b6b29e7d`: **55/55 PASS (220.91s), không xfail/skip/setup error**. Phạm vi: admin_bookings, ui_quality, customer_regressions, client_pwa_booking, collector và stress. Không chạy full backend suite/toàn bộ E2E.
- [x] 44 mẫu thường đều có target thực; 14 mẫu stress 10 KTV/210 khách/240 lịch qua gate ở 320/360/390/430/768/1024/1366. 60 lịch/ngày, tuần vẫn cap 200/240 (T08). Stress không có tràn viewport/card. Mẫu modal cuộn dọc không bị báo lỗi giả; không coi collector hoàn tất là tất cả UI PASS.
- [ ] UX-07/T11c: popup Admin 320px vượt trái viewport, 5 phần tử bị detector mới bắt; documentWidth vẫn 320. Đã xem ảnh và đưa vào task T11c, chưa sửa popup trong nhóm công cụ đo. 360px trở lên không tái hiện với mẫu đã chạy. Các task modal/accessibility/phone thật còn mở.
- QA-04 không tái hiện nhưng chưa đóng nguyên nhân; DecodeError cuối run là ca invalid-token chủ ý. Không tăng leeway/retry để làm xanh. Không đổi RLS/backend/credentials, không seed DB ứng dụng, không mở/tắt port 3000. Runner đã dọn QA process/container.
- Bằng chứng cuối tại `automation_test/artifacts/qa/76d5ebba-de8f-4832-9f18-b1f1b6b29e7d/` và `automation_test/artifacts/ui-review/76d5ebba-de8f-4832-9f18-b1f1b6b29e7d/`. Các mốc 4/7 và test FAIL ở mục review trước là lịch sử, đã được thay bằng kết quả này.
- **Tiến độ nghiệm thu: 7/7 task đã triển khai đạt phạm vi; tổng 7/29, còn 22.** Đồng bộ UI_UX_REVIEW/UI_UX_EXECUTION_PLAN/MOBILE_UX_DESIGN. Nhóm tiếp theo C: T05a → T05b → T03b/T06. Chưa kết luận production release hoặc toàn bộ phone UI đạt.

Lệnh kiểm chứng production tại root (QA riêng, tự cleanup):

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/admin_bookings automation_test/features/ui_quality automation_test/features/customer_regressions automation_test/features/client_pwa_booking automation_test/reviews/layout_probe.py automation_test/reviews/layout_stress.py -q -s --tb=short
```

## Nhóm C — Dialog, form dài, thao tác lịch và thu tiền — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T05a/T05b/T03b/T06: tổng 11/29 task, còn 18. Kết quả production cuối ghi dưới đây thay cho các lượt đang sửa/lỗi trước đó.
- Modal dùng native dialog/portal, accessible name/description, focus trap/restore (có ref opener khi nút bị khóa hoặc fallback), khóa scroll và nền, dirty/pending policy; manual/payment có history guard. Header/footer riêng, body cuộn, safe area cho customer nav; giữ màu shell khi portal.
- Manual booking có CTA ngoài vùng cuộn, giữ field khi 409; khi response không rõ hoặc đã có một phần thay đổi, chặn gửi lại và yêu cầu đối chiếu lịch. Có thể xem danh sách rồi mở lại draft cùng state trong trang. Không giải quyết tự động batch/idempotency/khôi phục qua reload của T01; không đổi API hoặc transaction.
- Lịch có một trạng thái tiếp theo và mở chi tiết dùng Modal; hoàn thành/hủy/vắng mặt yêu cầu xác nhận đúng khách/giờ, hoàn thành thẻ vẫn kiểm tra số buổi qua API. Thu tiền mở một ledger trong Modal, giữ key/payload/UUID khi resize và retry; CTA có tiền, tìm kiếm toàn hàng mobile và có return-focus ref cho dòng thu.
- Đã cập nhật POM/selector và thêm features/ui_quality/tests/test_dialog_workflows.py, mở rộng test retry/row30 payments. Layout regression chỉ tạo PNG/JSON khi assertion lỗi; không chạy collector/stress chụp hàng loạt trong nhóm C.
- Dev baseline 758557ad: 27 PASS (96.88s). Dev fc90225d: 14 PASS/2 FAIL/1 teardown ERROR (79.47s), phát hiện focus khi opener bị khóa và transient ApiError import trong lúc HMR; đã sửa. Production 67a1b62b: 69 PASS/2 FAIL (206.76s), gồm một lỗi prepare UI chưa sẵn sàng và theme portal còn từ bản build trước chỉnh sửa. Đã bổ sung readiness trước fault injection và chạy build mới; chưa coi lượt lỗi này là PASS.
- [x] Unit harness 23/23 PASS (0.753s). Production bbdb6b74-dd12-4dd6-a02a-8eb8e25ad0b8: 71/71 PASS (182.15s). Focused dev 1122b223-a067-42fd-b850-6487c10b5918: 2 PASS/17 deselected (22.92s), kiểm tra thu một phần ở row30 rồi đóng và reload không replay draft.
- [x] Bổ sung giữ vị trí cuộn sau mutation lịch khi cùng scope, bỏ khôi phục nếu đã đổi ngày/bộ lọc; regression dùng 30 booking thật, tôn trọng ca/buffer và xác minh trạng thái server. Sau thay đổi này chạy production mới 05e51f6a-7512-4a87-8c72-137fc391bf81: **build PASS, 73/73 PASS (171.35s), không xfail/skip/setup error**. Phạm vi admin_bookings/admin_payments/ui_quality/customer_regressions/client_pwa_booking. Gồm 13 ca dialog/long form, 19 UI acceptance/calibration, 16 calendar loading, trạng thái/trừ thẻ, 7 payment và quyền/PWA. Không chạy backend suite vì không đổi backend/API.
- Artifacts cuối: automation_test/artifacts/qa/05e51f6a-7512-4a87-8c72-137fc391bf81/ (logs và isolation proof). Không chạy collector/stress ảnh toàn bộ trong đợt này; layout regression đã đổi sang chỉ lưu PNG/JSON khi assertion lỗi. Không xóa bằng chứng lịch sử.
- Giới hạn: draft manual chỉ giữ trong trang, reload không khôi phục và không tự gửi; guard đối chiếu thủ công không giải quyết batch/recovery tự động của T01. Caller ngoài nhóm C tiếp tục áp dụng policy nghiệp vụ ở T09/T10; Safari/iPhone/keyboard ảo/screen reader/zoom còn T12. Popup 320px vẫn T11c; QA-04 chưa đóng nguyên nhân, DecodeError cuối run là invalid-token chủ ý.
- Runner dọn QA frontend/container/DB, không mở/tắt cổng 3000 hoặc seed DB ứng dụng. Nhóm tiếp theo D: T07a/T07b/T07c, cần review ranh giới phiên/quyền; không coi nhóm C PASS là release đã sẵn sàng.

Lệnh kiểm chứng production nhóm C tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/admin_bookings automation_test/features/admin_payments automation_test/features/ui_quality automation_test/features/customer_regressions automation_test/features/client_pwa_booking -q --tb=short
```

## Nhóm D — Phiên đăng nhập, tenant và tải khung giờ — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T07a/T07b/T07c: tổng 14/29 task, còn 15. Các lượt phát triển bên dưới là lịch sử; kết quả cuối ghi rõ riêng từng source/build.
- Admin/Customer phân biệt lỗi xác minh 503/offline với 401: giữ token khi lỗi tạm thời, ẩn dữ liệu/chặn thao tác và có Thử lại. Không coi lỗi tải danh sách chi nhánh là danh sách quyền rỗng đã xác minh.
- Request được gắn với phiên và lượt xác minh; phản hồi cũ không ghi user, lưu lại token hoặc xóa token phiên mới. Đăng xuất xóa UI ngay; dọn push dùng credentials đã chụp, không xóa phiên vừa đăng nhập lại. Đổi slug tạo state riêng; đổi phiên gỡ cả dialog portal chứa dữ liệu cũ. Đăng nhập nhanh từ khách chưa đăng nhập giữ draft đặt lịch trong trang.
- Public tenant: chỉ 404 là không tìm thấy, 503/offline có retry. Slots: tách lỗi mạng khỏi 200 rỗng, khóa submit khi scope ngày/dịch vụ/KTV chưa được xác minh; retry giữ lựa chọn nếu vẫn hợp lệ. Áp dụng wizard, đổi lịch Customer/Admin và từng dòng đặt lịch thủ công.
- Bổ sung test_session_recovery.py và test_slots_recovery.py, fault injection tại browser HTTP boundary, không chụp ảnh hàng loạt. Backend/JWT/RLS/API contract không thay đổi.
- Baseline dev ebc346ca: 16/16 PASS (79.10s). Lượt phát triển c9d9a804: 6 PASS/9 FAIL do selector trùng và cách giữ route trong test, đã sửa test. Production trung gian 5e017c9c: build PASS, 30 PASS/7 FAIL (101.89s), lỗi selector role alert đụng Next route announcer và so sánh xuống dòng; không coi là nghiệm thu. Đang chạy lại và bổ sung kiểm tra dialog/cleanup/đăng nhập nhanh.
- Dev 53c5e794: 33 PASS/1 FAIL (172.89s); ca cuối dùng sai tên nút đăng nhập nhanh, đã sửa thành tên UI thực tế. Unit harness 23/23 PASS (0.977s). Đã bổ sung version của phiên theo slug để phân biệt cả đăng nhập lại có cùng JWT ở tab khác; không lưu thêm credentials. Production cuối đang chạy với toàn bộ nhóm A/B/C/D và auth/branches.
- Production 285de710-1bac-4d1a-992e-21c98e2399d2: **build/TypeScript PASS, 114/114 PASS (273.94s)**, không skip/xfail/setup error. Gồm 73 ca nhóm C, 35 ca mới về phiên/tenant/slots và 6 ca auth/branches hiện có. Bao gồm cùng JWT ở tab khác, response me/401 đến muộn, dọn push chậm, dialog riêng tư và giữ draft sau inline login. DecodeError là ca token sai chủ ý; không đóng QA-04 từ kết quả không tái hiện.
- Rà lại phát hiện dropdown có thể còn busy khi bỏ qua response đổi branch cũ; đã thêm finally mở khóa và bỏ qua cả lỗi cũ trong context. Bổ sung regression 200/503 đến muộn sau khi đã xác minh branch khác. Bản build mới đang chạy 8 ca auth/branch liên quan; kết quả 114 ở trên là trước bản vá nhỏ này, không gộp thành một lượt chạy cùng source.
- [x] Production sau bản vá cuối bfc064b8-f064-484e-9d46-166ef1a59aa6: **build/TypeScript PASS, 8/8 PASS (17.06s)**. Kiểm tra 2 biến thể switch cũ 200/503 không thay token/branch mới, không hiện lỗi cũ, dropdown vẫn dùng được; 3 ca login và 3 ca đa chi nhánh hiện có. Không chạy lại collector/stress ảnh. Tổng các ca mới hiện tại là 36 (thêm biến thể switch lỗi sau lượt 114), không gọi các lượt trên là một run 115 ca.
- Review ranh giới quyền: giữ namespace token Admin/Customer/operator và theo slug; header Customer vẫn X-Tenant-Slug; JWT/RLS/quyền Backend không đổi. Khi phiên chưa xác minh không hiển thị dữ liệu riêng hoặc enable thao tác ghi. Guard trước/sau các await của switch/push cleanup; logout hoặc đổi phiên gỡ dialog chứa dữ liệu cũ. Không tự retry mutation hoặc nới JWT leeway để làm test xanh.
- QA chạy trong backend/DB tạm và frontend 3001 do runner sở hữu; không seed DB ứng dụng hoặc mở/tắt port 3000. Logs/isolation proof ở hai run production trên; không có PNG layout hàng loạt. Không chạy backend suite vì không sửa backend/contract. Thiết bị thật T12, popup 320px T11c, recovery T01 và QA-04 vẫn theo backlog. Tiếp theo E: T08a chốt contract rồi T08b triển khai/kiểm tra tên hiển thị, nguồn KTV công khai và phân trang.

Lệnh kiểm chứng nhóm D tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/admin_bookings automation_test/features/admin_payments automation_test/features/ui_quality automation_test/features/customer_regressions automation_test/features/client_pwa_booking automation_test/features/admin_auth automation_test/features/admin_branches -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_session_recovery.py::test_late_branch_switch_cannot_replace_a_new_verified_branch automation_test/features/admin_auth automation_test/features/admin_branches -q --tb=short
```

## Nhóm E — Tên hiển thị, nguồn KTV và phân trang — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T08a/T08b: tổng 16/29 task, còn 13. Các lượt trung gian bên dưới giữ làm lịch sử; không gọi chúng là một full run xanh trên cùng source.
- Contract tại API_CONTRACT mục T08: Booking thêm customer_name/staff_name, item thêm service_name nullable; lấy theo lô sau lọc quyền, không trả thêm hồ sơ/số điện thoại. PublicTenant.staff chỉ id/full_name STAFF active, theo slug/tenant và độc lập slots. GET bookings/customers giữ body mảng, thêm X-Has-More/X-Next-Offset, lấy limit+1; thứ tự có ID để phân trang ổn định. Không thay RLS/transaction hoặc thêm migration.
- QA backend lần đầu bị automatic approval review chặn vì chưa có bằng chứng DB tạm; đã kiểm tra runner thay URL của child process sang DB UUID tạm và bổ sung autouse guard từ chối database ứng dụng trước mọi fixture. Lệnh cùng runner sau kiểm chứng được duyệt; không đổi sang chạy test trên DB chính hoặc nới quyền.
- Backend qua scripts.test_isolated: scoped display/pagination/ownership 12/12 PASS (35.69s); toàn suite **78/78 PASS (193.76s)**. Bao gồm hơn 200 khách/lịch thật trong DB QA, quyền STAFF/tenant/customer, public DTO không có phone/notes, tên lịch/dịch vụ inactive và query count không tăng theo số card. Runner đã dọn DB tạm.
- UI đang nối dữ liệu tên, phân trang theo người dùng yêu cầu và tìm khách bằng q/limit=50; không gọi một API cho từng card hoặc tự quét toàn CRM. Regression mới test_display_pagination.py phân biệt test dữ liệu QA thật (>200 khách) với response giả lập tại HTTP boundary cho paging/stale/fault của UI. Không tạo ảnh hàng loạt.
- Dev cebc2b86-4b6f-4aed-8661-57ea8c07c3f9: **55/55 PASS (336.90s)** cho lịch, slots, customer safety và dialog. Build 95d411c7 bị TypeScript chặn MapIterator theo target hiện tại; đã sửa bằng Array.from, không đổi strict/target để né kiểm tra. Chưa chạy browser ở lượt build lỗi này.
- Phạm vi T08 UI: calendar, customer appointments, wizard KTV và bộ chọn khách tạo lịch. Trang CRM chính vẫn giới hạn 100 dòng tại admin/customers/page.tsx:92; đã thêm yêu cầu phân trang vào T10a (màn này chưa nghiệm thu), không gọi toàn bộ danh sách trong ứng dụng là đã hết giới hạn.
- Unit QA harness 23/23 PASS (1.877s). Đã sửa fallback tên thiếu thành câu dễ hiểu, bỏ UUID trong dời lịch; callback tìm khách/slots có type=button để không submit form. Khi tìm khách mới xóa selection/thẻ cũ và chặn response thẻ cũ; lỗi trang kế tiếp giữ những lịch đã tải. Bổ sung min-width/wrap cho tên KTV/dịch vụ dài trên thẻ Customer và regression range bounds; lượt production đang chạy 122 ca, cần phân biệt source trước/sau chỉnh CSS cuối nếu chạy bổ sung.
- Production 0a0ec6f2-1983-4009-bdfd-709e9eab2509: build/TypeScript PASS, **120 PASS/2 FAIL (660.51s)**. Ca tên KTV dài fail trên build trước min-width/wrap cuối; ca late_resource_401 Admin fail ở assert held=[] do header đã sẵn sàng nhưng request CRM chưa bắt đầu. Đã thêm barrier đợi request bị giữ thực sự, không sleep/retry/nới JWT. Không gọi lượt này là full PASS; production build mới đang chạy 7 ca T08 cùng 2 ca resource-401 Customer/Admin.
- [x] Production source cuối **376d1a89-63c7-48f6-9b20-3c560e1c603d: build/TypeScript PASS, 9/9 PASS (95.50s)**. Gồm 7 ca T08: hơn 200 khách QA thật và tìm đúng khách/thẻ, tên lịch không phụ thuộc trang CRM đầu, calendar 200+5/tải thêm lỗi/response cũ 200 hoặc 503, KTV hôm nay nghỉ vẫn chọn được cho ngày mai, history 50+5 với tên thường/tên dài không vượt biên. Hai ca resource-401 Customer/Admin xác nhận test readiness và bảo vệ token mới. Các ca phân trang lịch giả lập HTTP được phân biệt với 205 lịch thật/backend query-count test.
- Review ranh giới quyền: tên được chiếu theo lô từ lịch đã lọc actor/tenant; public staff chỉ id/full_name, không phone/notes/customer. Has-more được tính sau lọc quyền. Các query mới đều lọc tenant_id từ dependency/slug đã xác minh; không tin tenant_id từ body, không thay JWT/RLS/locking/thẻ/thu tiền. Pagination là live offset, dedup ID, reset trang đầu sau đổi scope/mutation; không tuyên bố snapshot toàn bộ dữ liệu.
- Giới hạn còn lại: CRM chính limit=100 ở T10a; STAFF phụ trách A1 với lịch do A2 làm cần preview/option KTV cũ ở T09; batch recovery T01, popup 320px T11c, QA-04 và thiết bị thật T12 chưa đóng. Không chạy collector/stress ảnh hoặc tạo PNG/JSON layout hàng loạt; logs/isolation proof ở các run nêu trên. QA chỉ dùng DB/container tạm và port 3001 do runner sở hữu; không mở/tắt port 3000 hoặc seed DB ứng dụng.

Lệnh kiểm chứng nhóm E:

```powershell
docker-compose exec -T backend python -m scripts.test_isolated -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_display_pagination.py automation_test/features/customer_regressions/tests/test_session_recovery.py::test_late_resource_401_does_not_clear_replacement_session -q --tb=short
```

## T09b/T09c — Gợi ý giờ và UI dời lịch — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T09b/T09c; tổng 18/29 task, còn 11. Làm T09b/T09c trước T09a để sửa đúng contract dời lịch. Wizard 3 bước T09a chưa triển khai, chưa cộng vào task nghiệm thu và là task tiếp theo.
- API GET /bookings/{id}/available-slots đã chốt tại API_CONTRACT: kiểm tra actor/tenant trước exclude chính booking đó, duration theo snapshot và giờ cũ hợp lệ được giữ cả khi lệch grid 15 phút. Không nhận exclude ID qua public endpoint; gợi ý không khóa và không thay kiểm tra dưới khóa của PATCH. PATCH bỏ staff_id giữ KTV hiện tại, explicit null mới tự sắp xếp. Không thay khóa/giao dịch/số buổi.
- Backend isolated: **21/21 scoped PASS (48.74s)** (gợi ý/ownership/concurrency); **81/81 toàn suite PASS (166.18s)**. Runner đã dọn database tạm, không seed DB ứng dụng.
- UI dùng API snapshot cho cả Admin/Customer, mặc định giữ KTV/giờ cũ nếu hợp lệ; đổi ngày không tự chọn giờ đầu. Có preview trước/sau, giữ duration/giá/quyền hồ sơ; Admin chuyển chủ hồ sơ mặc định tắt. STAFF A1 phụ trách khách nhưng A2 làm buổi hẹn có option hiển thị đúng A2; không tự chuyển sang A1/auto khi sửa note.
- Form dời lịch có pending/dirty policy của Modal, khóa fieldset khi gửi và chốt ref chống hai submit trước khi React commit. 409 tải lại gợi ý (GET), giữ ghi chú/form/lịch gốc; không retry mutation. Đã cập nhật POM/route intercept cho endpoint riêng; test retry ngày mới yêu cầu chọn giờ rõ ràng thay vì dựa vào auto-select.
- Test mới test_reschedule_snapshot.py kiểm tra ba vai trò, menu đổi duration/inactive, sửa note giữ snapshot/ID/KTV/thẻ, submit nhanh hai lần chỉ một PATCH, Escape khi pending, đổi ngày/dirty note và lịch đã COMPLETED chặn gợi ý/gửi tiếp. Lỗi nghiệp vụ 4xx hiển thị thông báo server; lỗi mạng/5xx vẫn phân biệt với danh sách giờ rỗng.
- Production trung gian f5bdee11-3cf6-4cb7-9fc5-b566f7984e64: build PASS, 22 PASS/3 FAIL (86.90s). Ba lỗi cùng do test tìm nút theo tên cũ trong khi UI pending đã đổi thành “Đang lưu...”; đã dùng selector submit ổn định và barrier request thực để kiểm chứng double-submit. Không nới retry/sleep/JWT để làm xanh.
- Production cuối a15b5244-054b-4ab7-af1a-a3a152917a66: **build/TypeScript PASS, 55/55 PASS (152.34s)**, không skip/xfail/setup error. Gồm snapshot 6, ownership/reschedule 4, slots recovery 16, calendar loading 16 và dialog workflows 13. Đây là phạm vi hồi quy liên quan, không phải full release suite hoặc nghiệm thu thiết bị thật T12.
- Runner dọn frontend 3001/backend/database QA tạm; không mở/tắt port 3000 hoặc seed database ứng dụng. Chỉ lưu logs/isolation proof; không chạy collector/stress ảnh. T01, T09a, T10/T11/T12 và nguyên nhân QA-04 còn theo backlog.

Lệnh kiểm chứng UI đợt T09b/T09c tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_reschedule_snapshot.py automation_test/features/customer_regressions/tests/test_ownership_reschedule.py automation_test/features/customer_regressions/tests/test_slots_recovery.py automation_test/features/admin_bookings/tests/test_calendar_loading.py automation_test/features/ui_quality/tests/test_dialog_workflows.py -q --tb=short
```

## T09a — Wizard đặt lịch 3 bước — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T09a: tổng 19/29 task, còn 10. Gộp KTV/ngày giờ thành một bước: Dịch vụ/thẻ → Ngày giờ/KTV → Xác nhận. Stepper chỉ cho tới xác nhận khi đã có giờ được xác minh; chặn ngày quá khứ cả input và mũi tên.
- Wizard yêu cầu tự chọn giờ; hook có tùy chọn autoSelect=false chỉ cho wizard, giữ mặc định caller khác và hành vi snapshot T09b/c. Back giữ dịch vụ/KTV/giờ hợp lệ/ghi chú; nguồn KTV độc lập slots. Card chọn dịch vụ/thẻ/auto trở thành button dùng bàn phím được; nhãn dài xuống dòng và stepper 3 cột.
- Chốt ref chống hai submit trong cùng lượt React, khóa Back/stepper/ghi chú khi pending; thành công giữ khóa đến chuyển trang. 409 trở về chọn giờ, tải lại gợi ý bằng GET và giữ draft; không retry POST. Không thay API/backend/RLS/JWT hoặc giá/số buổi server.
- POM và regression đổi theo 3 bước, không còn phụ thuộc auto-select. Thêm ca 360/390/1366px kiểm tra tràn ngang với tên dịch vụ/KTV dài, Back và nhảy bước; ca thẻ giữ một buổi, hai click chỉ một POST. PRD đồng bộ ba bước; không thêm endpoint/payload.
- Production 9685143a-cf19-475b-9dac-2bc324fe94bc: **build/TypeScript PASS, 70/70 PASS (253.08s)**, không skip/xfail/setup error. Phạm vi customer_regressions (67 ca) + client_pwa_booking (3 ca), gồm 4 ca mới, inline login giữ draft, server 409 và chọn lại, phân trang/quyền/phiên/slots/dời lịch và đặt bằng thẻ. Không chạy lại backend suite vì không sửa backend/API.
- Runner đã dọn frontend 3001/backend/database QA tạm; không seed DB ứng dụng hoặc mở/tắt port 3000. Chỉ log/isolation proof, không collector/stress ảnh. DecodeError thuộc ca invalid-token chủ ý; QA-04 chưa đóng nguyên nhân. Chromium các viewport trên chưa thay nghiệm thu thiết bị thật T12; không chốt full release từ lượt này.
- Tiếp theo nhóm F: T01a tái hiện thành công một phần/mất response và chốt recovery/idempotency trước T01b; sau đó T10/T11 và gate T12.

Lệnh kiểm chứng T09a tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions automation_test/features/client_pwa_booking -q --tb=short
```

## Nhóm F — T01a/T01b, tạo nhiều buổi và khôi phục — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T01a/T01b trong QA cô lập: tổng 21/29 task, còn 8. Luồng cũ handleCreateManualBooking tạo khách, cấp thẻ và từng booking bằng các request riêng; test tái hiện buổi 2 lỗi để lại khách/thẻ/buổi 1. Luồng mới thay bằng atomic batch; guard đối chiếu thủ công nhóm C được thay bằng UUID và API kiểm tra kết quả.
- Đã chốt quyết định T01 tại API_CONTRACT: POST /bookings/manual-batches atomically tạo khách/thẻ/1–20 buổi, UUID chống lặp theo tenant/actor; GET kết quả cùng actor và quyền khách hiện tại. Ghi hash + IDs, không ghi payload hồ sơ; migration 0008 có tenant FK và ENABLE/FORCE RLS. Không tự migrate database ứng dụng.
- Backend tái dùng kiểm tra booking hiện hành với commit=False nội bộ, prelock toàn bộ thẻ rồi tập KTV cố định theo ID trước các buổi, chỉ commit một lần cùng request record. Lỗi rollback toàn bộ, cùng UUID/nội dung trả IDs cũ, khác nội dung 409; không xóa bù hoặc retry tự động.
- UI thay chuỗi POST bằng một batch. Khi không rõ kết quả có Kiểm tra kết quả (GET) và Thử lại cùng yêu cầu (cùng UUID/body). sessionStorage chỉ UUID theo tenant/actor; reload không replay POST hoặc khôi phục PII. GET 404 không có kết quả cho sửa lại nhưng giữ UUID để POST tới muộn không tạo batch thứ hai; 404 mất quyền không mở khóa. Guard generation không cho response chi nhánh/phiên cũ thay UI mới.
- Backend scoped ban đầu **4/4 PASS (15.73s)**. Toàn suite tại mốc đó **85/85 PASS (269.55s)**. Bổ sung test sau đó và chạy scoped **8/8 PASS (36.31s)**: 7 ca manual batch + RLS gate, gồm tái hiện chuỗi cũ để lại một khách/một thẻ/buổi 1, hai batch khác UUID tranh KTV auto chỉ một thành công, STAFF replay bị chặn sau Admin chuyển chủ hồ sơ, không context không thấy bảng và ENABLE/FORCE RLS. Không gọi các lượt là một full run 88 ca trên cùng test tree.
- Production trung gian 52e27132-ff51-4ac4-8dd7-e5d8624f1a1e: **build/TypeScript PASS, 49/49 PASS (196.63s)**, gồm 4 ca recovery mới + 13 dialog + 16 slots + 16 calendar loading. Đã xác minh commit thành công rồi mất phản hồi, cùng body/UUID khi retry, GET không POST, reload chỉ giữ UUID không PII, giữ một khách/một thẻ/3 lịch. Sau đó bổ sung thông báo số buổi và Kiểm tra sau; đang kiểm chứng build mới, chưa coi lượt trước là kết quả source cuối.
- Production 7a2fd9a6-6d78-4851-a6d3-29eb754f2aa6: build/TypeScript PASS, **36 PASS/1 FAIL (136.48s)**. 20 ca session và 13 dialog PASS; ca check mới tìm Kiểm tra sau không có trong bản build đã compile trước khi bổ sung nút. Không coi lượt này là nghiệm thu; đang build lại source cuối và chạy 4 recovery + 13 dialog, không nới selector/retry để bỏ qua nút cần kiểm tra.
- Production cuối **9f4d3b45-125e-4c09-ba11-3d0b120e5026: build/TypeScript PASS, 17/17 PASS (51.29s)**, không skip/xfail/setup error. Gồm 4 recovery + 13 dialog, có Kiểm tra sau đóng/mở giữ draft, thông báo đúng 3 buổi đã lưu, retry cùng body/UUID và reload đối chiếu bằng GET. Không gộp các lượt thành full suite release xanh trên source cuối.
- Runner đã dọn frontend 3001/backend/DB QA tạm; không mở/tắt port 3000, seed hoặc migrate DB ứng dụng. RELEASE_RUNBOOK bổ sung triển khai đồng bộ frontend/backend + migration 0008, giữ request record trong backup và giới hạn mất tham chiếu khi xóa sessionStorage/đóng tab. QA-04 và nghiệm thu thiết bị thật/full release T12 chưa đóng.
- Tiếp theo nhóm G: T10a CRM/nhân sự (CRM chính còn limit=100), T10b báo cáo, T10c thẻ theo dependency; sau đó nhóm H và T12.

Lệnh kiểm chứng nhóm F tại root:

```powershell
docker-compose exec -T backend python -m scripts.test_isolated -q --tb=short
docker-compose exec -T backend python -m scripts.test_isolated tests/test_manual_batches.py tests/test_audit_regressions.py::test_all_business_tables_force_rls -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_manual_batch_recovery.py automation_test/features/ui_quality/tests/test_dialog_workflows.py -q --tb=short
```
- Lượt ghi file trước từng bị hệ thống auto-review dừng vì hết quota, không phải đánh giá action không an toàn; đã tiếp tục sau chỉ thị PO và quyền công cụ hoạt động trở lại. Không có server 3000 hoặc seed DB ứng dụng.

## T10a — CRM và nhân sự trên mobile — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T10a: tổng 22/29 task, còn 7. T10b dịch vụ/báo cáo và T10c trang thẻ khách chưa triển khai trong đợt này, là nhóm tiếp theo.
- CRM dùng GET customers limit=50 + header phân trang hiện có, có Đã tải/còn kết quả/Tải thêm, bỏ trùng ID, response tìm kiếm cũ không ghi đè kết quả mới. Tải thêm giữ selection; mutation hồ sơ tải lại query để tránh offset sai khi tên/thứ tự thay đổi, tạo mới tìm theo SĐT vừa tạo.
- Mobile CRM/nhân sự dùng danh sách → chi tiết với Quay lại, giữ DOM/từ khóa/scroll/focus bằng use-list-detail.ts. Desktop giữ hai cột, không nhân đôi form/ID. Lựa chọn là button tách khỏi nút sửa; tên dài xuống dòng, giờ ca làm co theo chiều rộng khả dụng.
- Tải thẻ/ca làm phân biệt lỗi với danh sách rỗng, có retry; guard ID/request chống phản hồi khách/KTV cũ. Ca làm lỗi không hiện mặc định để lưu đè, khóa Lưu cho tới GET thành công. Back giữ draft ca làm; đổi KTV có xác nhận bỏ thay đổi. Form sửa/tạo/cấp thẻ có pending/dirty và chốt chống submit nhanh hai lần.
- Production baseline ebc01326-439f-407e-86cc-183b67fed806: build/TypeScript PASS, 5 PASS/1 FAIL (51.52s). Ca chuyển quyền chưa mở chi tiết mobile trước khi chọn KTV; cập nhật test theo luồng mới, giữ assert quyền API và người cũ không xem/sửa được. Đang chạy 6 ca mới + 6 hồi quy liên quan; không sửa backend/API hoặc chạy suite backend không liên quan. Không collector/stress ảnh hoặc chạm port 3000/DB ứng dụng.
- Production efeed967-a200-49b8-9576-077e5791ee3c: build/TypeScript PASS, 9 PASS/3 FAIL (39.10s). Xác nhận tên dài gây overflow header CRM hai cột ở PC; đã thêm min-width/wrap. Hai lỗi khác là selector alert bắt Next route announcer, đã giới hạn main. Bổ sung retry danh mục thẻ, khóa lịch mặc định ngay khi chọn KTV và giữ Quay lại khi sửa khách khiến kết quả tìm kiếm không còn khớp.
- Production 489fe800-ed03-4432-baf1-f5fb29af1274: **build/TypeScript PASS, 15/15 PASS (50.34s)**, gồm 9 ca mới và 6 hồi quy cấp thẻ/ca làm/ownership. Sau review thêm phát hiện modal cấp thẻ dùng selectedCustomer có thể đổi khi search đang chờ: đã pin issueTarget tại lúc mở, chờ kiểm chứng thêm ca POST đúng khách. Dirty so với giá trị ban đầu để đóng form chưa sửa không hỏi bỏ thay đổi; đang chạy build cuối với 16 ca, chưa nghiệm thu từ run trước.
- Production cuối **ace45b5b-a6d5-463d-b2a8-ef1099eac35f: build/TypeScript PASS, 16/16 PASS (51.39s)**, không skip/xfail/setup error. 10 ca mới: 105 khách ở 360/390/1366px, Back giữ scroll/focus/query, search cũ, thẻ lỗi/retry, ca làm lỗi/chặn lưu/draft/đổi KTV, thẻ/ca làm response cũ, sửa tên không khớp query vẫn Quay lại được, cấp thẻ pin đúng ID khách khi search hoàn tất. 6 ca hiện có xác minh cấp thẻ, lưu ca và quyền/dời lịch.
- Không thay endpoint/payload/backend/RLS; không chạy lại backend suite không liên quan. Runner dọn frontend 3001/backend/DB QA tạm; không mở/tắt 3000 hoặc seed/migrate DB ứng dụng, không chạy collector/stress ảnh. Các viewport Chromium không thay nghiệm thu thiết bị thật T12; QA-04 và full release gate chưa đóng.

Lệnh kiểm chứng T10a tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_crm_staff_mobile.py automation_test/features/admin_crm_packages automation_test/features/admin_catalog/tests/test_staff_schedules.py automation_test/features/customer_regressions/tests/test_ownership_reschedule.py -q --tb=short
```

## T10b/T10c — Dịch vụ, báo cáo và trang thẻ khách — 19/10/2026

- [x] ĐÃ NGHIỆM THU phạm vi T10b/T10c: tổng 24/29 task, còn 5 (T11a/b/c/d, T12). Dịch vụ/báo cáo dùng cùng một DOM table: mobile từng dòng là thẻ có nhãn, desktop giữ bảng; không nhân đôi form/ID/nút thao tác. Tên/ghi chú/giá dài xuống dòng, không che overflow toàn trang.
- Báo cáo phân biệt giá trị dịch vụ COMPLETED với thực thu và hoa hồng ước tính; không thêm API/chỉ số hoặc tính lại tổng server. Guard request bỏ response kỳ báo cáo cũ, ẩn tổng cũ khi đổi bộ lọc/lỗi, retry báo cáo/danh sách KTV; chặn ngày kết thúc trước bắt đầu, tỷ lệ 0–100. Form dịch vụ có pending/dirty/ref chống double-submit và lỗi hiện trong modal.
- Thẻ khách phân biệt ACTIVE khả dụng, giữ chỗ hết buổi, dùng hết và hết hạn (kể cả ACTIVE nhưng expiry_date đã qua); CTA chỉ khi server còn buổi và chưa hết hạn. Không suy số buổi thành đã thu tiền, có giải thích đối chiếu với spa. GET lỗi có retry và giữ phân biệt với rỗng.
- Customer shell rộng hơn trên PC cho trang hồ sơ/danh mục, nav cùng độ rộng; form book/login/register giữ chiều rộng đọc được. Home/profile dùng grid hai cột trên màn rộng, giữ phone một cột. Không thay token/quyền/API/backend/RLS hoặc thao tác tiền/thẻ.
- Đang build production và chạy các ca mới ở 360/390/768/1366px cùng regression dịch vụ/báo cáo/PWA/thẻ/409. Chưa chốt kết quả từ build PASS. Không collector/stress ảnh, không mở/tắt 3000 hoặc seed/migrate DB ứng dụng.
- Production 0c71b0a2-f8bc-43f4-b2cf-7a191eb93ccf: build/TypeScript PASS, **30 PASS/1 FAIL (78.85s)**. 12 ca mới đều PASS; ca cũ so toàn bộ alert bằng một chuỗi nên không tính nút retry vừa thêm. Đã kiểm tra riêng thông báo lỗi exact và bấm retry thay reload. Rà lại sửa nhãn cột cuối desktop thành Hoa hồng ước tính, bổ sung assertion nhãn ở cả bốn viewport. Đang chạy lại 31 ca trên build/source cuối; không coi run này là nghiệm thu.
- Production cuối **f1eedaa1-b440-48bd-a5c7-1a7b11ac675e: build/TypeScript PASS, 31/31 PASS (74.35s)**, không skip/xfail/setup error. Gồm 12 ca mới (4 viewport dịch vụ/báo cáo, stale report 200/503, lỗi/ngày báo cáo, 4 viewport trạng thái thẻ/PC width, retry thẻ) và 19 ca hiện có dịch vụ/báo cáo/PWA/khách/wizard. Kiểm tra tiền lớn/tên không khoảng trắng, số buổi dùng/giữ/khả dụng, ACTIVE quá hạn không đặt được, hoa hồng ước tính và không nhân đôi input. DecodeError thuộc invalid-token chủ ý; không đóng QA-04 từ lượt không tái hiện.
- Không sửa API/backend/RLS hoặc logic ghi tiền/số buổi, không chạy lại backend suite không liên quan. Runner dọn frontend 3001/backend/DB QA tạm; không mở/tắt 3000 hoặc seed/migrate DB ứng dụng, không collector/stress ảnh. Chromium không thay nghiệm thu iPhone/Android thật T12. Nhóm tiếp theo H: T11a điều hướng/safe area → T11b guard chuyển chi nhánh (cần review phiên/giao dịch), rồi T11c/T11d; cuối cùng gate T12.

Lệnh kiểm chứng T10b/T10c tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_catalog_reports_packages.py automation_test/features/admin_catalog/tests/test_services.py automation_test/features/admin_reports automation_test/features/client_pwa_booking automation_test/features/customer_regressions/tests/test_customer_safety.py automation_test/features/customer_regressions/tests/test_three_step_wizard.py -q --tb=short
```

### 19/10/2026 — T11a: điều hướng mobile, Back và focus

- [x] T11a đạt phạm vi Chromium; **25/29 task**, còn T11b/T11c/T11d/T12. Admin mobile: Tổng quan/Lịch hẹn/Khách/Thu tiền/Thêm; STAFF: Lịch hẹn/Khách/Thêm, phần bổ sung chỉ dịch vụ. Giữ sidebar desktop và route/quyền hiện hành. Thêm dùng Modal chung, browser Back đóng menu/trả focus; chọn mục gỡ entry dialog trước điều hướng, Back không mở lại menu. Resize desktop đóng menu. Header bỏ hamburger trùng, bộ chọn chi nhánh co vừa; main đệm thanh dưới/safe area. Customer giữ 4 mục, aria-current và vùng chạm 48px. File: admin-shell.tsx, customer-shell.tsx.
- Thêm test_mobile_navigation.py: 9 ca gồm 320/360/390px, landscape 667x375, resize 844x390, khách PC 1366px; deep link/reload, active tab, quyền, Back/Escape/focus, đủ route, không overflow, padding và modal/action footer không bị nav chiếm tương tác.
- Run đầu 2bfcfed5-2a3f-4068-abb0-9f1755c8413d: build PASS, **35 PASS/7 FAIL (138.70s)**. Cả 9 ca mới và 13 dialog PASS. Sáu lỗi session_recovery tìm heading hồ sơ tự mở đã đổi ở T10a thành list/detail mobile; helper nay xác minh đúng nút khách đã tải. Một lỗi assert held trước request thẻ; thêm barrier theo request thực, không sleep/retry/nới xác thực. Không sửa source auth để làm xanh.
- Run cuối **0f2f8f4c-60a9-4a3b-899c-31f2452d5bbc: build production/TypeScript PASS, 42/42 PASS (105.39s)**, không skip/xfail/setup error: 9 điều hướng + 13 dialog + 20 phiên (hai tab, late me/401/switch, cùng JWT đăng nhập mới, push cleanup). Không coi các regression phiên này là đã triển khai T11b.
- Không thay API/backend/RLS/token hoặc vòng đời payload ghi tiền/manual batch. Không collector/stress ảnh; runner chỉ giữ log/proof QA. Không mở/tắt 3000, không seed/migrate DB ứng dụng. Thiết bị thật/keyboard/safe area vẫn T12; QA-04 chưa đóng nguyên nhân.
- Tiếp theo **T11b**: bảo vệ dirty/pending ở form inline và modal; manual batch chưa rõ kết quả dù modal đã đóng, payment attempt/voidAttempt/refreshFailed; hai tab và response muộn. Giữ xóa UI riêng tư khi phiên thay đổi từ tab khác, không lưu draft/payload khách trong localStorage. Sau đó T11c/T11d và gate T12.
- Cleanup cuối: runner exit 0, port 3001 không còn listener và không còn container spaos-ui-qa; không đụng server 3000.

Lệnh kiểm chứng T11a tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_mobile_navigation.py automation_test/features/ui_quality/tests/test_dialog_workflows.py automation_test/features/customer_regressions/tests/test_session_recovery.py -q --tb=short
```

### 19/10/2026 — T11b/T11c/T11d và phần tự động của T12

- [x] T11b/T11c/T11d đạt phạm vi Chromium, **28/29 task**. T12 chưa hoàn tất vì QA-04 chưa đóng nguyên nhân, chưa có nghiệm thu thiết bị thật và pilot. Không đồng nghĩa sẵn sàng release.
- T11b: `frontend/src/lib/branch-guard.ts:30` đăng ký dirty/pending trong bộ nhớ; `:38` giữ shared Web Lock trong request ghi, `:46` chỉ cho đổi chi nhánh khi lấy được exclusive lock. Tab khác còn form/giao dịch thì bị chặn; không hàng đợi gửi lại mutation sau đổi phiên. `api.ts:112` kiểm tra identity trước fetch. Không chứa token/draft/PII trong tên khóa hoặc lưu payload vào localStorage; đây là guard UX, backend JWT/RLS/transaction vẫn là ranh giới bảo mật.
- Caller gồm Modal quản trị, PaymentLedger (attempt/voidAttempt/refreshFailed), manual batch (busy/uncertain kể cả Kiểm tra sau), cấu hình, ca làm, cấp quyền chi nhánh, lựa chọn KTV phụ trách CRM và Push đang chờ quyền. Provider giữ guard UUID manual batch đúng tenant/user khi chuyển trang/reload, không khóa nhầm yêu cầu của tài khoản khác. Dirty có Tiếp tục chỉnh sửa/Bỏ thay đổi và chuyển; pending không cho bỏ để đổi branch. Giữ xóa UI giữa các tab khi phiên thực sự đổi. Trình duyệt không có Web Locks bị chặn đổi branch với thông báo rõ; kiểm chứng HTTPS/trình duyệt thực thuộc T12.
- T11c: cả hai bell dùng Modal chung, vừa màn hình, Back/Escape/focus/scroll; không còn popup rộng cố định tràn ở 320px. GET lỗi khác danh sách rỗng, có làm mới; request cũ không thay kết quả mới. Dashboard đưa lịch/thu tiền lên trước metrics, tổng chi nhánh chỉ xem, không có quick action thu tiền từ tổng hợp. Scope và dropdown đồng bộ query URL/Back/Forward; thêm Suspense theo yêu cầu build Next.js, không bỏ strict hoặc thay kiến trúc. Không thêm API/chỉ số báo cáo.
- T11d: kiểm chứng chọn chi nhánh, Admin login, customer login/register, branches/settings, Operator login/page và branding ở 320/390/768/1366px. Bổ sung wrap tên/lỗi dài, retry GET chi nhánh/cấu hình/Operator/branding, label và giữ luồng cấp tài khoản riêng. Operator retry giữ UUID/payload, ref chặn submit lặp; không remount attempt khi đổi viewport. **UX-28 đã sửa:** settings GET lỗi không còn cho lưu mặc định; handler chặn khi chưa có baseline, có retry.
- Thêm `test_branch_work_guard.py` (10 ca), `test_final_mobile_routes.py` (15 ca), `operator_portal/tests/test_operator_mobile.py` (4 ca). Giữ regression mất phản hồi thu tiền/manual batch, quyền KTV, stale response và hai tab. Chỉnh test phân trang chỉ đếm `/api/v1/customers?`, không đếm RSC prefetch; sáu ca màu/copy bỏ bước Tiếp tục dư theo wizard cũ, vẫn chọn slot rõ ràng và giữ assertion màu/số tiền.
- Lịch sử chưa nghiệm thu: build `39a79f49`/`161ba572` lỗi kiểu Map/Web Locks cũ, sửa tương thích không nới strict; `07edaaaf` thiếu Suspense, đã sửa. Run `f5a26bdb-baa5-4576-ad51-1a3e352d1141`: **65 PASS/9 FAIL/1 ERROR (202.59s)**; lỗi selector trùng Next announcer/header và setup JWT ImmatureSignatureError. Run full `0e8ad9f4-d1cd-4e0a-a2f1-0e89254d4e0c`: **195 PASS/7 FAIL (757.23s)**, do prefetch bị đếm là query CRM và test wizard cũ; các ca hiệu chuẩn layout PASS. Run `88f18048-962f-456c-8504-93ef08436745`: **45 PASS/1 FAIL (130.79s)**, test mới xác minh bằng GET customer detail không tồn tại (405), đã dùng API tìm khách đúng contract. Không đổi API để chiều test, không skip/xfail/tăng timeout/sleep/nới JWT.
- **Production cuối `86d9eaf7-ae95-42eb-ae99-d6d658765eeb`: build/TypeScript PASS, full E2E 204/204 PASS (554.89s)**, không skip/xfail/setup error. Bao gồm cả 2 ca bổ sung KTV phụ trách/Push chờ quyền, Back/Forward dashboard, 7 ca đã lỗi và các regression lịch/thẻ/tiền/tenant/phiên/Operator/layout. DecodeError là invalid-token chủ ý; không dùng lượt xanh để đóng QA-04.
- **Backend isolated 88/88 PASS (196.27s)**, UUID database QA đã dọn; **unit QA harness 23/23 PASS (0.620s)**. Không sửa backend/API contract/RLS/JWT hoặc áp migration vào DB ứng dụng. Migration 0008 vẫn chờ quy trình release.
- QA-04 đã tái hiện ở setup run f5a26bdb, chưa sửa nguyên nhân. Probe chỉ đọc đồng hồ 240s ở container của run 0e8ad9f4 ghi nhận bước tiến wall time so monotonic tối đa 0.811517s, bước lùi tối đa 0.000028s. Không đo cùng lần JWT lỗi, không chứng minh nguyên nhân; không đổi leeway hay claim. Cần đối chiếu iat/đồng hồ runtime và kiểm chứng staging trước pilot.
- Cleanup cuối: runner exit 0, **3001 không còn listener, không còn container spaos-e2e-qa**. Không mở/tắt 3000 hoặc seed/migrate database ứng dụng. Không chạy collector/stress ảnh; chỉ log/proof QA thông thường.
- T12 còn: Android Chrome/iPhone Safari thật (portrait/landscape, bàn phím ảo, safe area, zoom 200%, touch/Back/offline/Push); chủ spa/KTV/khách thử luồng thực tế và ghi bấm nhầm/trợ giúp/thời gian; đóng QA-04. Không gán PASS cho các phần chưa kiểm chứng, không chốt pilot/release từ test tự động.

Lệnh kiểm chứng cuối tại root:

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features -q --tb=short --maxfail=1
docker-compose exec -T backend python -m scripts.test_isolated -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m unittest discover -s automation_test/harness_tests -v
```

### 19/10/2026 — T12: điều tra QA-04, regression và điều kiện nghiệm thu còn thiếu

- PO yêu cầu hoàn tất T12; khi làm đã xác nhận **chưa có staging HTTPS/thiết bị thật**. Không đánh dấu nghiệm thu Android/iPhone/pilot hoặc đổi kế hoạch thành 29/29. Trạng thái hiện tại **28/29**, phần tự động đã kiểm chứng; T12 chờ môi trường, thiết bị/pilot và kết luận QA-04.
- Thêm `backend/scripts/qa_clock_probe.py`: chỉ chạy ENVIRONMENT=test, tạo/kiểm tra JWT với ID ngẫu nhiên không tồn tại trong DB, không truy cập DB hoặc mạng, không in token/claims định danh. Mỗi lần từ chối được giữ nguyên kết quả, không retry để thành PASS. Giới hạn thời lượng/tần suất; container chạy override entrypoint, không chạy migration/seed/server.
- Probe 120.004s: **21.761 mẫu, 0 từ chối**; iat ahead tối đa -0.000230s, bước tiến wall-vs-monotonic tối đa +0.895351s, bước lùi tối đa -0.000148s. Tám phép đo Windows/container có khoảng lệch nằm trong -0.598..-0.067s với RTT 0.254..0.506s, không ghi nhận lệch quá 2s trong cửa sổ này. Không đo đúng lần JWT lỗi nên **không chứng minh nguyên nhân và không đóng QA-04**.
- `backend/app/core/security.py:21`, `:67`: thêm log số liệu khi strict decoder từ chối ImmatureSignatureError: server_unix, iat/nbf ahead (chỉ số hữu hạn), utc-vs-wall và wall-vs-monotonic. Giới hạn parse metadata 8KiB; không log token/sub/tenant/SĐT/payload, không dùng metadata để xác thực. Không tắt verify, sửa iat, tăng leeway hoặc đổi response 401. Token sai chữ ký không phát log claim clock.
- Thêm 4 test probe và 6 test metadata/riêng tư. Focused trước sửa log: **6/6 PASS (1.15s)**. Full backend isolated sau sửa: **98/98 PASS (201.24s)**; database QA UUID đã dọn, không thay DB ứng dụng.
- Production regression sau sửa log: **9c4b7634-752b-4cde-9222-d0dd0395c6f2 — build/TypeScript PASS, 44/44 E2E PASS (116.05s)**, không skip/xfail/setup error. Gồm Admin auth, branches, Operator, session recovery và branch work guard (hai tab/request muộn/uncertain payment/manual batch/Push). Không tái hiện QA-04; không coi vậy là bản sửa nguyên nhân. Full UI 204/204 và QA harness 23/23 là lượt trước; frontend và harness không đổi nên không chạy lại toàn bộ chỉ vì thêm log/chẩn đoán backend.
- Cleanup: các process exit 0, port 3001 không có listener, không còn container E2E/probe; không mở/tắt server 3000. Không collector/screenshot/JSON layout, không seed/migrate DB ứng dụng. API contract, JWT policy, tenant/RLS và giao dịch giữ nguyên.
- Phần cần tiếp tục khi có môi trường: thu log thời gian **cùng lần** JWT bị từ chối và đối chiếu clock runtime/host; xác nhận nguyên nhân/khắc phục, kiểm chứng staging. Sau đó Android Chrome/iPhone Safari thật với keyboard/safe area/zoom/Back/touch/offline/Push và pilot ba vai trò có ghi expected/actual. Chưa có các bằng chứng này thì T12 vẫn mở.

### QA-04 — đồng bộ giờ runtime và ngừng ghi file log (19/10/2026)

- **Chỉ thị mới của PO: không ghi file log nữa.** Chỉ thị này thay các hướng dẫn lưu log/proof cũ: runner QA không tạo `pytest.log`, `frontend.log`, `isolation.json` hoặc thư mục artifact của run. Docker container QA dùng logging driver `none` qua Compose override trong bộ nhớ; thông báo xác thực được chuyển trực tiếp ra console. Tắt pytest cache; chặn collector ghi ảnh/JSON khi chạy qua runner. Không xóa các artifact cũ. Build/config tạm cần để chạy frontend vẫn được tạo, không phải log.
- Sửa `run_ui_qa.py`, `common_setup/qa_frontend.py`, `qa_backend.py`, `layout_evidence.py`; stream stdout qua pipe để kết quả pytest/build vẫn hiển thị trên Windows khi dùng CREATE_NO_WINDOW. Harness **25/25 PASS (0.106s)**, gồm kiểm tra không tạo artifact và override Docker không lưu log. Không lấy dòng kết quả giả lập trong unit test làm số E2E thực.
- Kiểm tra HTTP thật trên API/DB QA riêng: **400/400** lượt đăng nhập rồi gọi `/auth/me` bằng token vừa cấp PASS trong 136.031s, không retry hoặc file log. Đây là cửa sổ không tái hiện, chưa chứng minh đã sửa QA-04.
- Bằng chứng runtime: Windows W32Time đang chạy nhưng Leap Indicator=3, Stratum=0, Source=Local CMOS Clock, Last Successful Sync Time=unspecified. Ubuntu trên WSL2 đồng thời bật `systemd-timesyncd`, NTP=yes, poll 32s; Docker dùng clocksource Hyper-V. Journal có **14 thông báo Clock change detected** trong chính cửa sổ run lỗi `f5a26bdb` (13:23:30–13:26:53 UTC ngày 19/10). Xác nhận môi trường có điều chỉnh giờ liên tục; **nghi ngờ hai cơ chế đồng bộ giờ cạnh tranh**, chưa có số iat/clock delta của chính token lỗi để khẳng định toàn bộ chuỗi nguyên nhân.
- NTP `time.windows.com` phản hồi 3 mẫu stripchart, offset +0.871..+0.883s. `w32tm /resync /rediscover` bị **Access is denied (0x80070005)**: terminal hiện tại không có quyền Administrator. Đã yêu cầu PO chạy lệnh này trong PowerShell Administrator; chưa đổi server NTP, tắt NTP Ubuntu, khởi động lại WSL/Docker hoặc thay đồng hồ toàn máy.
- Bước còn lại: xác nhận Windows thực sự đồng bộ thành công, sau đó xử lý NTP riêng của Ubuntu theo runbook và kiểm chứng lại clock/JWT trên console. Không tăng leeway, bỏ verify, sửa iat hoặc thêm retry/sleep để che lỗi. **QA-04/T12 vẫn mở; tổng 28/29.**
- Kiểm chứng cuối harness mới trên production frontend cô lập: **46b61dcb-79ae-41e5-9416-3f182c872152 — build/TypeScript PASS, 23/23 E2E PASS (49.23s)**, gồm Admin auth và session recovery, không skip/setup error. Kết quả đã stream trực tiếp trên console, không lưu output/proof/ảnh vào file. Đây là xác nhận runner hoạt động, không phải nghiệm thu sửa clock. Lượt trước `9650604f` exit 0 nhưng stdout con không hiển thị trên Windows nên không dùng lượt đó làm bằng chứng số test; đã sửa chuyển tiếp pipe và kiểm chứng lại bằng lượt 23/23 này.

### 20/10/2026 — Review lại 29 task UI/UX

- Đối chiếu đủ các task với source/contract/test; kết quả và file:dòng nằm ở đầu `UI_UX_REVIEW.md`, mã R29-01..05. Không chứng nhận lại toàn bộ 28 task là sạch lỗi: còn Push tiếp tục bằng phiên mới, danh sách Thu tiền cũ sau lỗi query, counter thông báo giảm lặp, failure capture che lỗi layout trong console-only, CTA spa demo ở tenant 404.
- R29-01 tái hiện bằng module TS/Node VM (A bắt đầu → B đăng nhập → subscribe bằng B); R29-02 tái hiện trên Chromium production với API mock 503 cho query B (vẫn hiện A); R29-03 chạy chính handler TS với hai response cùng ID (2 unread item nhưng counter 1). Không gọi các probe mock này là kiểm chứng backend/RLS; không sửa nghiệp vụ trong lượt review.
- Production run **23ace1c2-7b89-4960-b2c4-4a1899e6d64a: build/TypeScript PASS, 204/204 E2E PASS (903.02s)**; **3/3 regression bố cục lịch PASS (27.04s)** chạy riêng trên cùng QA đã xác minh marker, không collector; **25/25 harness PASS (0.300s)**. Không skip/xfail/setup error. Không chạy lại backend suite vì không sửa backend; 98/98 là lịch sử.
- Chỉ xuất console, không ghi log/ảnh/JSON artifact. Runner exit 0; 3001 không còn listener, không còn container E2E QA. Không mở/tắt 3000, không seed/migrate DB ứng dụng. QA-04 không tái hiện trong cửa sổ này nhưng chưa có kiểm chứng sau sửa đồng bộ giờ. T12 vẫn chờ staging HTTPS/thiết bị thật/pilot; chưa chốt release. Ưu tiên sửa R29-01/02 rồi R29-03/04/05, thêm regression trước nghiệm thu lại các task liên quan.

### 20/10/2026 — Sửa và kiểm chứng R29-01..05

- Đã sửa 5 phát hiện của lượt review: Push pin token/session generation và kiểm tra sau await (gồm auto-sync/disable/mounted/ref chống nhấn lặp); Thu tiền gắn scope/user/tenant/query/filter/page, lỗi có retry và ẩn rows cũ; hai bell dùng `use-notification-feed.ts`, serialize mark-one/read-all, lấy counter từ server, bỏ GET trước mutation; layout giữ AssertionError gốc không capture; CTA tenant 404 về chọn chi nhánh `/`.
- Thêm **18 E2E** trong `test_review_followups.py` và 1 fault-injection giữ lỗi layout; không thay API/backend/JWT/giá/giao dịch. Dev cuối `26162b99`: **20/20 PASS (73.19s)** trước hai ca Push bình thường bổ sung. Hai lượt dev chưa đạt vì assertion đếm initial GET Strict Mode và nhãn Customer “mới”; đã chỉnh đúng kiểm tra, không skip/tăng timeout. Chi tiết ở UI_UX_REVIEW.
- **Production `6253fa68-759e-4493-b281-b88b2702a1cb`: build/TypeScript PASS, 74/74 PASS (230.94s)**, không skip/xfail/setup error. Gồm 18 mới + 7 thu tiền + 20 phiên + 10 guard đổi branch + 15 màn phụ/mobile + 4 layout. **Harness 25/25 PASS (0.197s)**. Đây là hồi quy chọn lọc trên source cuối; 204/204 trước sửa là lịch sử, không gọi lượt này là full features. Backend không đổi nên không chạy lại suite backend.
- Runner exit 0; 3001 không có listener, không còn container E2E QA. Chỉ xuất console, không ghi log/ảnh/JSON artifact; không mở/tắt 3000 hoặc seed/migrate DB ứng dụng. Test bằng module TypeScript qua node_modules bị auto-review từ chối do ignore-path; đã dùng Playwright trên frontend QA để kiểm chứng, không thực thi cách bị chặn.
- **R29-01..05 đóng trong phạm vi code/Chromium; QA-04/T12 vẫn mở.** Windows kiểm tra lại vẫn Local CMOS Clock/Stratum 0/chưa sync; bước Administrator trong RELEASE_RUNBOOK chưa được thực hiện/kiểm chứng. Không nới JWT để che lỗi; staging HTTPS/Android/iPhone/pilot còn chờ môi trường.

Lệnh kiểm chứng R29 tại root (console-only):

```powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/customer_regressions/tests/test_review_followups.py automation_test/features/admin_payments automation_test/features/customer_regressions/tests/test_session_recovery.py automation_test/features/customer_regressions/tests/test_branch_work_guard.py automation_test/features/customer_regressions/tests/test_final_mobile_routes.py automation_test/reviews/test_layout_regressions.py -q --tb=short --maxfail=1
```

Lệnh kiểm chứng T12 tại root:

```powershell
docker-compose run --rm --no-deps -e ENVIRONMENT=test --entrypoint python backend -B -m scripts.qa_clock_probe --seconds 120
docker-compose exec -T backend python -m scripts.test_isolated -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features/admin_auth automation_test/features/admin_branches automation_test/features/operator_portal automation_test/features/customer_regressions/tests/test_session_recovery.py automation_test/features/customer_regressions/tests/test_branch_work_guard.py -q --tb=short --maxfail=1
```
