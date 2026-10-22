# TÀI LIỆU YÊU CẦU SẢN PHẨM & KINH DOANH (PRD & BRD)
**Dự án:** Nền tảng Quản lý và Đặt lịch Spa chuẩn SaaS
**Giai đoạn:** MVP (Minimum Viable Product) - Phiên bản 1.1 (Đã nâng cấp Kiến trúc & Lộ trình AI)
**Ngày cập nhật:** 15/10/2026

---

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)

### 1.1. Mục tiêu sản phẩm
Xây dựng một nền tảng quản lý Spa toàn diện, bắt đầu bằng việc giải quyết bài toán vận hành và chăm sóc khách hàng cho 1 Spa đối tác (Pilot Phase), sau đó định hướng đóng gói thành giải pháp SaaS (Software as a Service) để cung cấp cho hàng loạt Spa khác trên thị trường (Scale Phase).

### 1.2. Chân dung người dùng (Target Audience)
*   **End-user (Khách hàng của Spa):** Cần một công cụ đặt lịch nhanh chóng, xem được các dịch vụ, theo dõi lịch hẹn, quản lý thẻ liệu trình (gói nhiều buổi) và nhận nhắc lịch tự động. Đề cao tính tiện lợi, không muốn gọi điện hay chờ tin nhắn xác nhận.
*   **Tenant (Chủ Spa & Quản lý):** Cần một hệ thống quản lý tập trung để theo dõi lịch hẹn (chống trùng lịch), quản lý thông tin khách hàng & số buổi liệu trình còn lại, cấu hình dịch vụ/ca làm việc nhân sự. Đề cao tính dễ sử dụng, trực quan và tốc độ thao tác.

---

## 2. KIẾN TRÚC HỆ THỐNG & CÔNG NGHỆ (ARCHITECTURE & TECH STACK)

Hệ thống bắt buộc phải thiết kế theo kiến trúc **Multi-tenant (Mô hình Shared Database, Shared Schema)** ngay từ ngày đầu tiên để sẵn sàng cho việc mở rộng SaaS mà không phải đập đi xây lại.

### 2.1. Ngăn xếp công nghệ đề xuất (Tech Stack)
| Thành phần | Công nghệ | Chi tiết & Mục đích |
| :--- | :--- | :--- |
| **Web App / PWA (Khách hàng)** | Next.js (App Router / PWA) | Truy cập qua link/QR code theo từng Spa (`/[tenant_slug]`), lưu ra màn hình chính, không cần tải app từ Store. |
| **Web Admin (Chủ Spa)** | Next.js, TailwindCSS, shadcn/ui | SPA Dashboard quản trị lịch hẹn, khách hàng, thẻ liệu trình và nhân sự. |
| **Backend API** | Python (FastAPI + SQLAlchemy 2.0 Async) | Xử lý logic đặt lịch tốc độ cao, hỗ trợ Async, tự động sinh API Swagger. |
| **Database** | PostgreSQL | Relational DB mạnh mẽ, bật Row-Level Security (RLS) đảm bảo tính toàn vẹn dữ liệu Multi-tenant. |
| **Push Notification** | Web Push API / Telegram Bot | Gửi thông báo nhắc lịch qua trình duyệt PWA và báo lịch mới về Telegram của Lễ tân/Chủ Spa. |
| **E2E Automation Test** | Python (`pytest` + `playwright`) | Kiểm thử tự động toàn diện (End-to-End) trên trình duyệt cho cả Web Admin và Client PWA theo mô hình Feature-based Page Object Model (POM). |

### 2.2. Hạ tầng triển khai (Infrastructure - Target < $15/tháng cho MVP)
*   **Frontend Web:** Deploy Serverless trên Vercel hoặc Netlify (Free Tier).
*   **Backend API:** Dockerize và chạy trên VPS DigitalOcean/Hetzner (Gói cơ bản ~$5-$6/tháng).
*   **Database:** Supabase hoặc Neon.tech (Serverless Postgres - Free Tier).

---

## 3. YÊU CẦU TÍNH NĂNG (FUNCTIONAL REQUIREMENTS - MVP)

### 3.1. Web App / PWA (Dành cho Khách hàng - End User)
*Lưu ý kiến trúc: Mỗi Spa có một đường dẫn định danh riêng qua `slug` (VD: `domain.com/spa-hoa-hong`). Khi khách quét mã QR vào link này, hệ thống dựa vào `slug` để lấy `tenant_id`, hiển thị đúng Logo, Theme Color và Danh sách dịch vụ của Spa đó trước cả khi khách đăng nhập. Một SĐT khách hàng có thể đặt lịch ở nhiều Spa khác nhau mà không bị xung đột.*

*   **Xác thực & Hồ sơ:**
    *   Đăng ký/Đăng nhập bằng Số điện thoại + Mật khẩu hoặc Google Login (gắn kèm với `tenant_id` hiện tại).
    *   Quản lý thông tin cá nhân (Họ tên, SĐT, Ngày sinh) và xem **Thẻ liệu trình** đang sở hữu (tổng số buổi, số buổi đã dùng, số buổi còn lại).
*   **Khám phá Dịch vụ:**
    *   Hiển thị danh sách dịch vụ lẻ và gói liệu trình theo danh mục.
    *   Chi tiết dịch vụ: Tên, Mô tả, Hình ảnh, Thời lượng (phút), Giá tiền.
*   **Hệ thống Đặt lịch Đa dịch vụ (Booking Flow):**
    *   Bước 1: Chọn **1 hoặc nhiều dịch vụ** trong cùng 1 lần đặt (hoặc chọn đặt lịch trừ vào **Thẻ liệu trình** đang có). Hệ thống tự cộng dồn tổng thời gian thực hiện (`total_duration`).
    *   Bước 2: Chọn Ngày & Giờ cùng Kỹ thuật viên (tùy chọn) hoặc "Spa tự sắp xếp". Thuật toán chỉ hiển thị slot khả dụng theo ca làm và lịch đã đặt; khách tự chọn giờ, không tự chọn slot đầu. Không cho chọn ngày quá khứ.
    *   Bước 3: Xác nhận đặt lịch; khách chưa đăng nhập có thể đăng nhập/đăng ký nhanh và giữ lựa chọn trong trang. Quay lại giữ dữ liệu hợp lệ; xung đột 409 cho chọn lại giờ trong cùng luồng. Cập nhật UX theo T09a ngày 19/10/2026; trạng thái kiểm chứng thực tế xem PROGRESS.
*   **Quản lý Lịch hẹn:**
    *   Tab "Sắp tới": Các lịch hẹn chưa diễn ra.
    *   Tab "Lịch sử": Lịch đã hoàn thành, đã hủy.
    *   Chức năng Hủy lịch (Chỉ cho phép hủy trước `X` giờ so với giờ hẹn).

### 3.2. Web Admin Dashboard (Dành cho Chủ Spa & Kỹ thuật viên)
*Lưu ý bảo mật: Mọi API request từ Web Admin đều phải đính kèm JWT Auth Token. Backend dùng Dependency Injection lấy `tenant_id` từ Token và chỉ cho phép CRUD trên dữ liệu của tenant đó.*

*   **Xác thực:** Đăng nhập bằng Email/SĐT và Password.
*   **Quản lý Lịch hẹn (Booking Management):**
    *   Dashboard dạng Calendar trực quan theo Ngày/Tuần/Kỹ thuật viên.
    *   Tạo lịch hẹn thủ công (Cho khách vãng lai, khách gọi Hotline).
    *   Cập nhật trạng thái lịch: `PENDING` (Chờ xác nhận) -> `CONFIRMED` (Đã xác nhận) -> `IN_PROGRESS` (Đang làm) -> `COMPLETED` (Hoàn thành) / `CANCELLED` (Đã hủy) / `NO_SHOW` (Khách không đến).
    *   *Tự động trừ buổi liệu trình:* Khi lịch hẹn có gắn với Thẻ liệu trình chuyển sang trạng thái `COMPLETED`, hệ thống tự động cộng `+1` vào số buổi đã sử dụng (`used_sessions`).
*   **Quản lý Khách hàng & Thẻ Liệu Trình (CRM & Packages):**
    *   Danh sách khách hàng (Hiển thị Tên, SĐT, Số lần đến, Ghi chú tình trạng da/sức khỏe).
    *   **Quản lý Thẻ liệu trình (Customer Packages):** Cấp thẻ liệu trình mới cho khách (VD: Gói trị mụn 10 buổi), theo dõi tiến độ từng buổi và lịch sử trừ buổi.
*   **Quản lý Nhân sự, Ca làm việc & Dịch vụ (Tenant Settings):**
    *   CRUD Nhân viên (Kỹ thuật viên, Lễ tân).
    *   **Cấu hình Lịch làm việc (Staff Schedules):** Thiết lập giờ làm việc theo thứ trong tuần cho từng KTV và đăng ký ngày nghỉ phép (Day-off).
    *   CRUD Dịch vụ (Tên, Giá, Thời gian thực hiện, Loại dịch vụ: Lẻ / Liệu trình,Số buổi mặc định, Trạng thái Active/Inactive).
    *   Thiết lập thông tin chung: Tên Spa, URL Slug, Logo, Giờ mở/đóng cửa, Thời gian nghỉ chuyển tiếp giữa 2 ca (Buffer time, VD: 10 phút dọn giường).
*   **Báo cáo & Thống kê (Simple Report):**
    *   Lọc và thống kê tổng số lượng dịch vụ và tổng giá trị dịch vụ mà từng Kỹ thuật viên đã hoàn thành (`COMPLETED`) theo khoảng thời gian (Ngày/Tuần/Tháng) để chủ Spa tính hoa hồng.

---

## 4. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL REQUIREMENTS)

*   **Bảo mật Multi-tenant 2 lớp (Bắt buộc):**
    1. *Tầng Application (FastAPI):* Sử dụng Dependency Injection tự động lọc `WHERE tenant_id = current_tenant_id` cho mọi Query.
    2. *Tầng Database (PostgreSQL):* Kích hoạt Row-Level Security (RLS) trên toàn bộ các bảng có `tenant_id` thông qua biến session `app.current_tenant_id`.
*   **Chống xung đột (Concurrency Control):** Backend bắt buộc dùng Database Transaction + Row Locking (`SELECT ... FOR UPDATE`) trên lịch của Kỹ thuật viên khi xử lý API Booking. Đảm bảo nếu 2 khách đặt cùng 1 slot của 1 KTV trong cùng 1 mili-giây, chỉ 1 người thành công.
*   **Hiệu năng:** Thời gian phản hồi API (Latency) < 300ms.

---

## 5. CẤU TRÚC CƠ SỞ DỮ LIỆU CỐT LÕI (CORE DATABASE SCHEMA)

*(Mọi bảng đều có `id` (UUID/BigInt PK), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ)).*

1.  **Bảng `tenants`** (Thông tin các Spa dùng SaaS)
    *   `id` (PK), `slug` (Unique Index - VD: `spa-hoa-hong`), `name`, `logo_url`, `theme_color`, `open_time`, `close_time`, `buffer_minutes` (Default: 10), `status`.
2.  **Bảng `users`** (Tài khoản Khách & Staff thuộc từng Spa)
    *   `id` (PK), `tenant_id` (FK -> tenants), `role` (`ADMIN`, `STAFF`, `CUSTOMER`), `full_name`, `phone_number`, `password_hash`, `notes`, `is_active`.
    *   *Constraint:* Unique(`tenant_id`, `phone_number`) -> Cho phép 1 SĐT có thể làm khách ở nhiều Spa khác nhau.
3.  **Bảng `staff_schedules`** (Ca làm việc của Kỹ thuật viên)
    *   `id` (PK), `tenant_id` (FK), `staff_id` (FK -> users), `day_of_week` (0=CN .. 6=Thứ 7), `start_time` (Time), `end_time` (Time), `is_day_off` (Boolean).
4.  **Bảng `services`** (Danh mục dịch vụ & Gói liệu trình)
    *   `id` (PK), `tenant_id` (FK), `name`, `description`, `duration_minutes`, `price`, `is_package` (Boolean - Là thẻ liệu trình?), `total_sessions` (Số buổi nếu là package, Default: 1), `is_active`.
5.  **Bảng `customer_packages`** (Thẻ liệu trình khách hàng đã mua)
    *   `id` (PK), `tenant_id` (FK), `customer_id` (FK -> users), `service_id` (FK -> services), `package_name`, `total_sessions` (Tổng số buổi), `used_sessions` (Số buổi đã làm, Default: 0), `expiry_date` (TIMESTAMPTZ, nullable), `status` (`ACTIVE`, `COMPLETED`, `EXPIRED`).
6.  **Bảng `bookings`** (Phiên đặt lịch tổng)
    *   `id` (PK), `tenant_id` (FK), `customer_id` (FK -> users), `staff_id` (FK -> users, nullable), `start_time` (TIMESTAMPTZ), `end_time` (TIMESTAMPTZ), `total_duration_minutes`, `total_price`, `status` (`PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `NO_SHOW`), `note`.
7.  **Bảng `booking_items`** (Chi tiết đa dịch vụ trong 1 lần đặt lịch)
    *   `id` (PK), `tenant_id` (FK), `booking_id` (FK -> bookings), `service_id` (FK -> services), `customer_package_id` (FK -> customer_packages, nullable - Nếu dùng thẻ liệu trình để đặt), `duration_minutes`, `price` (Giá tại thời điểm đặt; bằng 0 nếu trừ thẻ liệu trình).

---

## 6. CHIẾN LƯỢC KINH DOANH & PHÁT TRIỂN (BUSINESS ROADMAP)

*   **Giai đoạn 1 (Tháng 1 - Tháng 3) - Pilot & Co-create:** Triển khai thực tế tại Spa của bạn bè, miễn phí Setup, thu phí chia sẻ Server, tinh chỉnh UX/UI cho Lễ tân và Khách hàng.
*   **Giai đoạn 2 (Tháng 4 trở đi) - SaaS Commercialization:** Đóng gói bảng giá Basic (399K/tháng) và Pro (799K/tháng), mở rộng tích hợp Zalo ZNS / Zalo Mini App.

---

## 7. LỘ TRÌNH TRIỂN KHAI VỚI AI AGENT (PROMPT ROADMAP CHO ANTIGRAVITY)

*(Hướng dẫn sử dụng: Copy từng Prompt tương ứng với từng Sprint bên dưới để giao việc cho AI theo thứ tự. Không chạy gộp nhiều Sprint cùng lúc).*

### Sprint 1: Khởi tạo Hạ tầng, Database Schema & Bảo mật Multi-tenant
*   **Model khuyến nghị:** **Model Argon** (Cần tư duy kiến trúc chuẩn ngay từ đầu).
*   **Mục tiêu:** Dựng khung project Backend FastAPI, Docker Postgres, toàn bộ 7 bảng SQLAlchemy Models, Alembic Migration, RLS và JWT Auth.
*   **Prompt mẫu để gõ vào AI:**
    > "Hãy đọc file `.antigravityrules` và `Spa_SaaS_PRD.md`. Thực hiện **Sprint 1**:
    > 1. Khởi tạo cấu trúc thư mục Backend FastAPI chuẩn production và file `docker-compose.yml` cho PostgreSQL.
    > 2. Viết SQLAlchemy 2.0 Async Models cho toàn bộ 7 bảng ở Mục 5 của PRD (`tenants`, `users`, `staff_schedules`, `services`, `customer_packages`, `bookings`, `booking_items`).
    > 3. Thiết lập Alembic và tạo file migration đầu tiên, bao gồm cả câu lệnh SQL kích hoạt PostgreSQL Row-Level Security (RLS) theo `tenant_id`.
    > 4. Viết module Auth (JWT) và Dependency `get_current_tenant` đảm bảo cô lập dữ liệu Multi-tenant."

### Sprint 2: Xây dựng API Quản trị cơ bản (Tenant, Dịch vụ, Nhân sự, Thẻ liệu trình)
*   **Model khuyến nghị:** Model tiêu chuẩn / Nhanh (Hoặc Argon nếu muốn).
*   **Mục tiêu:** Hoàn thiện các API CRUD danh mục để có dữ liệu phục vụ đặt lịch.
*   **Prompt mẫu để gõ vào AI:**
    > "Thực hiện **Sprint 2** dựa trên `Spa_SaaS_PRD.md`:
    > 1. Viết API Public lấy thông tin Spa và danh sách dịch vụ theo `slug` (`GET /api/v1/public/tenants/{slug}`).
    > 2. Viết các API CRUD cho Admin (yêu cầu JWT + `tenant_id`): Quản lý Dịch vụ (`services`), Quản lý Nhân viên & Ca làm việc (`users`, `staff_schedules`).
    > 3. Viết API Quản lý Khách hàng và Cấp/Theo dõi Thẻ liệu trình (`customer_packages`).
    > 4. Tạo 1 script `seed.py` tạo sẵn 1 Spa mẫu (`slug='spa-demo'`), 3 kỹ thuật viên có lịch làm việc, 5 dịch vụ lẻ và 2 gói liệu trình để phục vụ test."

### Sprint 3: Core Booking Engine (Thuật toán Slot khả dụng & Chống trùng lịch)
*   **Model khuyến nghị:** **BẮT BUỘC DÙNG MODEL ARGON** (Xử lý thuật toán thời gian & Concurrency phức tạp nhất dự án).
*   **Mục tiêu:** Tính đúng giờ trống và khóa dòng chống đặt trùng, tự động trừ buổi liệu trình.
*   **Prompt mẫu để gõ vào AI:**
    > "Thực hiện **Sprint 3** dựa trên `Spa_SaaS_PRD.md`:
    > 1. Viết API tìm kiếm khung giờ trống (`GET /api/v1/bookings/available-slots`): Nhận vào `tenant_id`, danh sách `service_ids` (tính tổng `duration_minutes`), `date`, và `staff_id` (tùy chọn). Đối chiếu với `open_time/close_time` của Spa, `staff_schedules` và các `bookings` hiện có (cộng thêm `buffer_minutes`) để trả về danh sách các slot giờ khả dụng.
    > 2. Viết API Đặt lịch (`POST /api/v1/bookings`) hỗ trợ đặt đa dịch vụ (`booking_items`) và áp dụng Thẻ liệu trình (`customer_package_id`). BẮT BUỘC dùng Transaction + `SELECT ... FOR UPDATE` để chống Race Condition khi 2 người đặt trùng giờ của cùng 1 KTV.
    > 3. Viết API Cập nhật trạng thái lịch hẹn: Khi chuyển sang `COMPLETED`, nếu `booking_items` có gắn với `customer_package_id`, tự động tăng `used_sessions` thêm 1 (nếu bằng `total_sessions` thì đổi trạng thái thẻ sang `COMPLETED`).
    > 4. Viết file `test_booking_concurrency.py` bằng `pytest` giả lập 5 requests chạy song song đặt cùng 1 KTV vào cùng 1 giờ, chứng minh chỉ có 1 request thành công."

### Sprint 4: Báo cáo Thống kê Hoa hồng & Thông báo
*   **Model khuyến nghị:** Model tiêu chuẩn / Nhanh.
*   **Mục tiêu:** Hoàn tất phần Backend với API Báo cáo và Webhook/Push thông báo.
*   **Prompt mẫu để gõ vào AI:**
    > "Thực hiện **Sprint 4** dựa trên `Spa_SaaS_PRD.md`:
    > 1. Viết API Báo cáo hiệu suất Kỹ thuật viên (`GET /api/v1/reports/staff-performance`) lọc theo `start_date`, `end_date`: Thống kê tổng số dịch vụ đã hoàn thành (`COMPLETED`) và tổng doanh thu mang lại của từng KTV.
    > 2. Viết module gửi thông báo qua Telegram Bot (gửi tin nhắn cho Chủ Spa ngay khi có khách đặt lịch mới) và cấu trúc cơ bản cho Web Push Notification."

### Sprint 5: Xây dựng Web Admin Dashboard (Next.js)
*   **Model khuyến nghị:** Model tiêu chuẩn (Tiết kiệm Quota cho việc dựng UI/CSS).
*   **Mục tiêu:** Giao diện quản lý trực quan cho Chủ Spa & Lễ tân.
*   **Prompt mẫu để gõ vào AI:**
    > "Thực hiện **Sprint 5** dựa trên `Spa_SaaS_PRD.md`:
    > 1. Khởi tạo project Frontend Next.js (App Router, TypeScript, TailwindCSS, shadcn/ui).
    > 2. Xây dựng phân hệ Admin (`/admin/*`): Trang Đăng nhập, Trang Dashboard Lịch hẹn dạng Calendar (hiển thị theo Ngày/Tuần, đổi màu theo trạng thái lịch, cho phép tạo lịch thủ công và đổi trạng thái nhanh).
    > 3. Xây dựng các trang: Quản lý Khách hàng & Cấp Thẻ liệu trình, Quản lý Dịch vụ, Quản lý Nhân sự & Ca làm việc, và Trang Báo cáo Hoa hồng KTV."

### Sprint 6: Xây dựng Client PWA Đặt lịch cho Khách hàng
*   **Model khuyến nghị:** Model tiêu chuẩn.
*   **Mục tiêu:** Giao diện Mobile-first siêu mượt khi khách quét mã QR tại Spa.
*   **Prompt mẫu để gõ vào AI:**
    > "Thực hiện **Sprint 6** dựa trên `Spa_SaaS_PRD.md`:
    > 1. Xây dựng phân hệ Khách hàng theo Dynamic Route `/[tenant_slug]` tối ưu giao diện Mobile-first và cấu hình `manifest.json` chuẩn PWA.
    > 2. Xây dựng luồng Đặt lịch 3 bước (Wizard, cập nhật T09a 19/10/2026): Chọn dịch vụ/thẻ -> Chọn Ngày giờ/Kỹ thuật viên -> Xác nhận. Không tự chọn giờ hoặc nhảy bước khi thiếu dữ liệu.
    > 3. Xây dựng trang Cá nhân của khách: Xem lịch hẹn Sắp tới (cho phép Hủy nếu trước giờ quy định), Lịch sử làm đẹp, và Xem số buổi còn lại trong Thẻ liệu trình."

### Sprint 7: Xây dựng Bộ Kiểm thử Tự động E2E (`automation_test/`)
*   **Model khuyến nghị:** Model tiêu chuẩn.
*   **Mục tiêu:** Tự động hóa kiểm thử giao diện và luồng nghiệp vụ End-to-End bằng `pytest` + `playwright` theo kiến trúc Feature-based POM.
*   **Prompt mẫu để gõ vào AI:**
    > "Thực hiện **Sprint 7** dựa trên Mục 8 của `Spa_SaaS_PRD.md`:
    > 1. Khởi tạo thư mục `automation_test/` ngang hàng với `backend/` và `frontend/`, thiết lập `requirements.txt`, `pytest.ini`, `.env.test` và `conftest.py`.
    > 2. Xây dựng thư mục `common_setup/` gồm `config.py`, `base_page.py` (Page Object cơ sở), `api_helper.py` và `auth_setup.py` (tách biệt BrowserContext giữa Admin và Customer PWA).
    > 3. Xây dựng thư mục `features/` chia theo từng module nghiệp vụ (`admin_auth`, `admin_catalog`, `admin_crm_packages`, `admin_bookings`, `client_pwa_booking`), mỗi module bắt buộc có thư mục `pages/` và `tests/` riêng biệt."

---

## 8. KIẾN TRÚC KIỂM THỬ TỰ ĐỘNG E2E (AUTOMATION TEST ARCHITECTURE)

Hệ thống sử dụng bộ kiểm thử tự động End-to-End (E2E) độc lập đặt tại thư mục `automation_test/` (ngang hàng với `backend/` và `frontend/`), sử dụng **`pytest`** kết hợp với **`playwright`** theo mô hình **Feature-based / Modular Page Object Model (POM)**.

### 8.1. Nguyên tắc thiết kế
1.  **Cô lập hoàn toàn (Decoupled E2E):** Thư mục `automation_test/` hoạt động độc lập, đóng vai trò như người dùng thực tế tương tác trên trình duyệt với `frontend/` và gọi API tới `backend/`, không làm ảnh hưởng tới bộ unit/integration test nội bộ trong `backend/tests/`.
2.  **Tổ chức theo Module Nghiệp vụ (Feature-based POM):** Mỗi tính năng trong `features/` là một module khép kín, tự chứa thư mục `pages/` (định nghĩa Locators & Page Actions) và `tests/` (chứa kịch bản kiểm thử `test_*.py`) của riêng module đó.
3.  **Tách biệt Context Đa vai trò (Multi-Context Isolation):** Hỗ trợ chạy song song 2 `BrowserContext` độc lập trong cùng một kịch bản test (1 Context Desktop cho Admin/Lễ tân tại `/admin/*` và 1 Context giả lập Mobile cho Khách hàng tại `/[tenant_slug]/*`) để kiểm thử luồng tương tác thời gian thực.

### 8.2. Cấu trúc thư mục chuẩn (`automation_test/`)
```text
SpaOS/
├── backend/
├── frontend/
├── docs/
├── docker-compose.yml
└── automation_test/                  # Thư mục gốc E2E Automation Test
    ├── pytest.ini                    # Cấu hình pytest (base_url, browser, markers, testpaths)
    ├── requirements.txt              # pytest, pytest-playwright, python-dotenv, httpx/requests
    ├── .env.test                     # Biến môi trường test (FRONTEND_URL, BACKEND_URL, tài khoản spa-demo)
    ├── conftest.py                   # Root fixtures của pytest (khởi tạo BrowserContext, Auth, Seed Data)
    │
    ├── common_setup/                 # Thư mục chứa các setup, cấu hình và tiện ích dùng chung
    │   ├── __init__.py
    │   ├── config.py                 # Đọc biến môi trường từ .env.test
    │   ├── base_page.py              # BasePage chứa các phương thức bọc Playwright dùng chung (click, fill, wait...)
    │   ├── api_helper.py             # Helper gọi nhanh API Backend để chuẩn bị/dọn dẹp dữ liệu test
    │   └── auth_setup.py             # Quản lý đăng nhập và lưu/load storage_state cho Admin & Customer
    │
    └── features/                     # Chứa các module kiểm thử chia theo nghiệp vụ
        ├── admin_auth/               # Module: Đăng nhập / Đăng ký Tenant (Admin)
        │   ├── pages/
        │   │   └── login_page.py
        │   └── tests/
        │       └── test_admin_login.py
        │
        ├── admin_catalog/            # Module: Quản lý Dịch vụ, Nhân sự & Ca làm việc
        │   ├── pages/
        │   │   ├── service_page.py
        │   │   └── staff_page.py
        │   └── tests/
        │       ├── test_services.py
        │       └── test_staff_schedules.py
        │
        ├── admin_crm_packages/       # Module: Quản lý Khách hàng & Cấp Thẻ liệu trình
        │   ├── pages/
        │   │   └── customer_package_page.py
        │   └── tests/
        │       └── test_issue_package.py
        │
        ├── admin_bookings/           # Module: Calendar Lịch hẹn & Tự động trừ buổi liệu trình
        │   ├── pages/
        │   │   └── booking_calendar_page.py
        │   └── tests/
        │       └── test_booking_status_and_deduct_session.py
        │
        └── client_pwa_booking/       # Module: Khách hàng đặt lịch qua PWA (/[tenant_slug])
            ├── pages/
            │   ├── tenant_home_page.py
            │   ├── booking_wizard_page.py
            │   └── my_appointments_page.py
            └── tests/
                ├── test_pwa_booking_flow.py
                └── test_multi_tenant_isolation_ui.py

## Bổ sung được PO xác nhận — 17/10/2026
- Khách có một KTV phụ trách hồ sơ cố định. Admin có toàn quyền và là người duy nhất chuyển/gỡ người phụ trách; KTV khác không được đọc/sửa hồ sơ, thẻ hoặc lịch của khách qua UI hay API. Khách vẫn xem và thao tác dữ liệu của mình.
- KTV thực hiện một booking và KTV phụ trách hồ sơ là hai khái niệm độc lập. Đổi KTV trên lịch không chuyển quyền hồ sơ; muốn người mới quản lý khách, Admin phải chuyển quyền tại CRM.
- Dời lịch phải atomic, không hủy booking cũ rồi tạo booking mới; giữ giá/thời lượng/items đã chốt và buổi liệu trình đang giữ. Chỉ sửa PENDING/CONFIRMED; khách đổi trước hạn hủy.
- Thanh toán ưu tiên xác nhận thủ công: tách phải thu và thực thu, ghi phương thức, người xác nhận, thời gian; theo dõi chưa thu/một phần/đã thu và lịch sử sửa. QR và đối soát ngân hàng tự động nằm ngoài đợt triển khai này.

### Ghi nhận triển khai thu tiền thủ công (17/10/2026)
Đã triển khai phiếu phải thu theo lịch/thẻ, thu nhiều phần, bút toán hủy có lý do, chống ghi trùng và nhật ký Admin. Giá bán thẻ mới được chốt lúc cấp; thẻ cũ cần xác nhận giá lịch sử. Thực thu theo ngày được tách khỏi giá trị dịch vụ hoàn thành. Admin có thể bàn giao hồ sơ cùng lúc dời lịch bằng lựa chọn rõ ràng, mặc định không chuyển quyền.

### Luồng thu tiền đơn giản theo PO (17/10/2026)
Admin xem danh sách khách cùng dịch vụ/thẻ đã có sẵn, xác nhận tiền mặt/chuyển khoản với số tiền mặc định bằng khoản còn thiếu. Không có bước lập/mở phiếu trên giao diện; tự cộng tổng hôm nay. Trả một phần, hoàn tác có lý do và lịch sử là thao tác phụ. Lịch dùng thẻ không thu thêm; giá giao dịch được giữ theo snapshot; thẻ cũ thiếu giá cần đối chiếu.

## Định hướng chiến lược đang chờ quyết định — 17/10/2026
Xem [MULTI_BRANCH_STRATEGY.md](MULTI_BRANCH_STRATEGY.md) về deployment riêng từng chủ spa và nhiều chi nhánh. PO hiện chỉ yêu cầu lưu định hướng, chưa cho triển khai. Nội dung này chưa thay thế schema/API và các tính năng đang chạy được mô tả ở trên. Conversation mới đọc AGENTS.md, PROGRESS.md và tài liệu chiến lược trước khi bắt đầu task.

## Triển khai đa chi nhánh được PO phê duyệt — 17/10/2026
Đã được phép triển khai sau bước lưu chiến lược. tenant_id giữ vai trò mã chi nhánh nội bộ; danh tính quản trị dùng chung qua login_accounts và branch_memberships. Tài khoản quản trị đăng nhập SĐT/mật khẩu, chủ chuyển chi nhánh và xem dashboard tổng hợp; STAFF chỉ có chi nhánh được cấp. Khách chọn chi nhánh theo tên, hồ sơ/thẻ/dịch vụ/giá vẫn riêng. Migration không gộp SĐT trùng; operator đối chiếu. Xem API_CONTRACT, MULTI_BRANCH_STRATEGY và tiến độ kiểm chứng mới nhất.

## Cấp tài khoản chủ spa theo PO — 17/10/2026
Đơn vị triển khai có danh tính quản trị riêng, seed từ secrets cấu hình; màn hình /operator tạo chủ spa và chi nhánh đầu tiên bằng form web Unicode. Chủ spa/nhân viên không đăng nhập cổng này, tiếp tục /admin/login. Seed mặc định không tạo dữ liệu demo; không dùng mật khẩu mặc định cho operator. Production một chủ spa/deployment, thêm chi nhánh qua quyền chủ như hiện hành.


### Bổ sung sau Sprint: thương hiệu theo deployment
Operator chọn/xem trước/lưu màu chủ đạo; áp dụng trang Admin, đăng nhập, PWA khách và các chi nhánh cùng chủ. Mỗi deployment độc lập; Admin chi nhánh không đổi màu chung. Chưa cấu hình giữ tương thích màu chi nhánh cũ.


### Điều chỉnh thông báo theo PO — 21/10/2026

- Khách tự đặt lịch: báo admin, kỹ thuật viên thực hiện và người phụ trách hồ sơ trong chi nhánh. Nhân viên/admin tạo lịch cho tài khoản khách: khách nhận thông báo lịch mới, gồm tạo nhiều buổi tại quầy, không gửi trùng khi retry cùng yêu cầu.
- Ngoại lệ đọc lịch được giao: KTV thực hiện được đọc chính lịch được phân công và thông báo liên quan dù chưa phụ trách hồ sơ. Quy định này thay phần cấm đọc lịch của khách khác ở trên trong phạm vi chỉ đọc; quyền CRM/thẻ/sửa lịch và chuyển người phụ trách không đổi.
- Không coi Push là chắc chắn giao được; in-app được lưu trước khi gửi. Giới hạn BackgroundTasks và kiểm chứng thiết bị thật vẫn áp dụng.


### Cải thiện UX theo vai trò — phê duyệt 21/10/2026
PO cho phép cập nhật theo UX_ROLE_REVIEW. Link dịch vụ/thẻ hợp lệ có thể bỏ qua bước chọn dịch vụ để tới chọn giờ, nhưng khách phải tự chọn slot. Giữ ba bước cho trường hợp chưa chọn dịch vụ. Tìm ngày có chỗ kiểm tra tối đa bảy ngày kế tiếp, không giữ chỗ trước xác nhận. Khách hủy lịch phải xác nhận rõ. Nhân viên chỉ được giao thực hiện tiếp tục chỉ xem lịch; chủ spa/người phụ trách hồ sơ xác nhận trạng thái theo PO. Xem UX_ROLE_REVIEW và PROGRESS để biết phần đã triển khai/kiểm chứng và phần còn trong backlog.


### Điều chỉnh trải nghiệm theo PO — 21/10/2026

PO cho phép hoàn thiện UX_ROLE_REVIEW. Giữ STAFF hiện hành, không thêm lễ tân/thu ngân. Nhân viên chỉ được giao thực hiện tiếp tục chỉ xem; chủ spa/người phụ trách cập nhật trạng thái. Bàn giao là ghi chú riêng từng booking, không sao chép hồ sơ sức khỏe hoặc gửi note qua Push. Khách quên mật khẩu/kích hoạt hồ sơ tại quầy: spa xác minh rồi chủ cấp liên kết dùng một lần, hạn 30 phút, khách tự đặt mật khẩu; không SMS OTP, không mật khẩu chung.

Phạm vi bổ sung: địa chỉ/liên hệ chi nhánh; ảnh logo kiểm tra định dạng; setup dựa dữ liệu thật; ca tuần chỉ đọc cho nhân viên và ngoại lệ ngày do chủ quản lý; quản lý tài khoản chung có xác minh và thu hồi phiên; thống nhất buổi đã dùng/đang giữ/có thể đặt; lịch sử thực tế của thẻ; sửa họ tên khách; phục hồi kết quả đặt lịch khách; outbox sự kiện/thông báo và retry Push. Mọi giao dịch tiếp tục cô lập tenant/RLS và khóa chống trùng hiện hành. Phạm vi API ở API_CONTRACT; trạng thái kiểm chứng ở PROGRESS. Thiết bị thật/HTTPS/pilot chưa được suy là đạt từ code hay E2E.

### Cổng vận hành, bàn giao và hướng dẫn — 0.2.0 (22/10/2026)
- [x] Version/release/build FE/BE đóng gói trước build, Swagger và operator đối chiếu browser/server/backend.
- [x] Cổng khách/quản lý/operator có link rõ ràng; một chi nhánh đi thẳng, nhiều chi nhánh chọn theo tên.
- [x] Operator sửa thông tin tài khoản chủ spa đã cấp và cấp link khôi phục 30 phút một lần; xác minh danh tính/mật khẩu operator, giữ RLS và thu hồi phiên cũ.
- [x] Bộ bàn giao PNG/PDF/tin nhắn/QR tạo trong trình duyệt, tách nội dung quản lý và khách; không chứa mật khẩu hoặc recovery token.
- [x] Manifest riêng quản lý/chi nhánh; hướng dẫn cài Android/iOS và chuỗi hướng dẫn ba vai trò có thể bỏ qua/mở lại.
- [ ] Nghiệm thu native install/start_url/push trên Android/iOS thật qua HTTPS và các gate phát hành còn mở trong RELEASE_RUNBOOK. Icon PWA hiện dùng asset ứng dụng; chưa thay thành icon riêng cho từng spa.

### Hotfix vận hành 0.2.1 — 22/10/2026
Màu chung chỉ được chỉnh tại một nơi theo giai đoạn: trong form cấp chủ đầu tiên hoặc mục Cài đặt giao diện sau khi đã có chủ. Render/Docker dùng start_service để nâng schema trước mở API; schema guard phát hiện revision cũ/mất cột và ngăn worker chạy với DB chưa sẵn sàng. Không tự thay settings Render từ code; xem RENDER_DEPLOYMENT.md.
