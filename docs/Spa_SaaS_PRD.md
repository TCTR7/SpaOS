# TÀI LIỆU YÊU CẦU SẢN PHẨM & KINH DOANH (PRD & BRD)
**Dự án:** Nền tảng Quản lý và Đặt lịch Spa chuẩn SaaS[cite: 1]
**Giai đoạn:** MVP (Minimum Viable Product) - Phiên bản 1.1 (Đã nâng cấp Kiến trúc & Lộ trình AI)[cite: 1]
**Ngày cập nhật:** 15/10/2026[cite: 1]

---

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)[cite: 1]

### 1.1. Mục tiêu sản phẩm[cite: 1]
Xây dựng một nền tảng quản lý Spa toàn diện, bắt đầu bằng việc giải quyết bài toán vận hành và chăm sóc khách hàng cho 1 Spa đối tác (Pilot Phase), sau đó định hướng đóng gói thành giải pháp SaaS (Software as a Service) để cung cấp cho hàng loạt Spa khác trên thị trường (Scale Phase)[cite: 1].

### 1.2. Chân dung người dùng (Target Audience)[cite: 1]
*   **End-user (Khách hàng của Spa):** Cần một công cụ đặt lịch nhanh chóng, xem được các dịch vụ, theo dõi lịch hẹn, quản lý thẻ liệu trình (gói nhiều buổi) và nhận nhắc lịch tự động[cite: 1]. Đề cao tính tiện lợi, không muốn gọi điện hay chờ tin nhắn xác nhận[cite: 1].
*   **Tenant (Chủ Spa & Quản lý):** Cần một hệ thống quản lý tập trung để theo dõi lịch hẹn (chống trùng lịch), quản lý thông tin khách hàng & số buổi liệu trình còn lại, cấu hình dịch vụ/ca làm việc nhân sự[cite: 1]. Đề cao tính dễ sử dụng, trực quan và tốc độ thao tác[cite: 1].

---

## 2. KIẾN TRÚC HỆ THỐNG & CÔNG NGHỆ (ARCHITECTURE & TECH STACK)[cite: 1]

Hệ thống bắt buộc phải thiết kế theo kiến trúc **Multi-tenant (Mô hình Shared Database, Shared Schema)** ngay từ ngày đầu tiên để sẵn sàng cho việc mở rộng SaaS mà không phải đập đi xây lại[cite: 1].

### 2.1. Ngăn xếp công nghệ đề xuất (Tech Stack)[cite: 1]
| Thành phần | Công nghệ | Chi tiết & Mục đích |
| :--- | :--- | :--- |
| **Web App / PWA (Khách hàng)** | Next.js (App Router / PWA) | Truy cập qua link/QR code theo từng Spa (`/[tenant_slug]`), lưu ra màn hình chính, không cần tải app từ Store[cite: 1]. |
| **Web Admin (Chủ Spa)** | Next.js, TailwindCSS, shadcn/ui | SPA Dashboard quản trị lịch hẹn, khách hàng, thẻ liệu trình và nhân sự[cite: 1]. |
| **Backend API** | Python (FastAPI + SQLAlchemy 2.0 Async) | Xử lý logic đặt lịch tốc độ cao, hỗ trợ Async, tự động sinh API Swagger[cite: 1]. |
| **Database** | PostgreSQL | Relational DB mạnh mẽ, bật Row-Level Security (RLS) đảm bảo tính toàn vẹn dữ liệu Multi-tenant[cite: 1]. |
| **Push Notification** | Web Push API / Telegram Bot | Gửi thông báo nhắc lịch qua trình duyệt PWA và báo lịch mới về Telegram của Lễ tân/Chủ Spa[cite: 1]. |

### 2.2. Hạ tầng triển khai (Infrastructure - Target < $15/tháng cho MVP)[cite: 1]
*   **Frontend Web:** Deploy Serverless trên Vercel hoặc Netlify (Free Tier)[cite: 1].
*   **Backend API:** Dockerize và chạy trên VPS DigitalOcean/Hetzner (Gói cơ bản ~$5-$6/tháng)[cite: 1].
*   **Database:** Supabase hoặc Neon.tech (Serverless Postgres - Free Tier)[cite: 1].

---

## 3. YÊU CẦU TÍNH NĂNG (FUNCTIONAL REQUIREMENTS - MVP)[cite: 1]

### 3.1. Web App / PWA (Dành cho Khách hàng - End User)[cite: 1]
*Lưu ý kiến trúc: Mỗi Spa có một đường dẫn định danh riêng qua `slug` (VD: `domain.com/spa-hoa-hong`). Khi khách quét mã QR vào link này, hệ thống dựa vào `slug` để lấy `tenant_id`, hiển thị đúng Logo, Theme Color và Danh sách dịch vụ của Spa đó trước cả khi khách đăng nhập[cite: 1]. Một SĐT khách hàng có thể đặt lịch ở nhiều Spa khác nhau mà không bị xung đột.*

*   **Xác thực & Hồ sơ:**[cite: 1]
    *   Đăng ký/Đăng nhập bằng Số điện thoại + Mật khẩu hoặc Google Login (gắn kèm với `tenant_id` hiện tại)[cite: 1].
    *   Quản lý thông tin cá nhân (Họ tên, SĐT, Ngày sinh) và xem **Thẻ liệu trình** đang sở hữu (tổng số buổi, số buổi đã dùng, số buổi còn lại)[cite: 1].
*   **Khám phá Dịch vụ:**[cite: 1]
    *   Hiển thị danh sách dịch vụ lẻ và gói liệu trình theo danh mục[cite: 1].
    *   Chi tiết dịch vụ: Tên, Mô tả, Hình ảnh, Thời lượng (phút), Giá tiền[cite: 1].
*   **Hệ thống Đặt lịch Đa dịch vụ (Booking Flow):**[cite: 1]
    *   Bước 1: Chọn **1 hoặc nhiều dịch vụ** trong cùng 1 lần đặt (hoặc chọn đặt lịch trừ vào **Thẻ liệu trình** đang có)[cite: 1]. Hệ thống tự cộng dồn tổng thời gian thực hiện (`total_duration`).
    *   Bước 2: Chọn Kỹ thuật viên (tùy chọn) hoặc "Spa tự sắp xếp"[cite: 1].
    *   Bước 3: Chọn Ngày & Giờ (Thuật toán chỉ hiển thị các slot khả dụng dựa trên Ca làm việc của KTV và các lịch đã đặt)[cite: 1].
    *   Bước 4: Xác nhận đặt lịch[cite: 1].
*   **Quản lý Lịch hẹn:**[cite: 1]
    *   Tab "Sắp tới": Các lịch hẹn chưa diễn ra[cite: 1].
    *   Tab "Lịch sử": Lịch đã hoàn thành, đã hủy[cite: 1].
    *   Chức năng Hủy lịch (Chỉ cho phép hủy trước `X` giờ so với giờ hẹn)[cite: 1].

### 3.2. Web Admin Dashboard (Dành cho Chủ Spa & Kỹ thuật viên)[cite: 1]
*Lưu ý bảo mật: Mọi API request từ Web Admin đều phải đính kèm JWT Auth Token[cite: 1]. Backend dùng Dependency Injection lấy `tenant_id` từ Token và chỉ cho phép CRUD trên dữ liệu của tenant đó[cite: 1].*

*   **Xác thực:** Đăng nhập bằng Email/SĐT và Password[cite: 1].
*   **Quản lý Lịch hẹn (Booking Management):**[cite: 1]
    *   Dashboard dạng Calendar trực quan theo Ngày/Tuần/Kỹ thuật viên[cite: 1].
    *   Tạo lịch hẹn thủ công (Cho khách vãng lai, khách gọi Hotline)[cite: 1].
    *   Cập nhật trạng thái lịch: `PENDING` (Chờ xác nhận) -> `CONFIRMED` (Đã xác nhận) -> `IN_PROGRESS` (Đang làm) -> `COMPLETED` (Hoàn thành) / `CANCELLED` (Đã hủy) / `NO_SHOW` (Khách không đến)[cite: 1].
    *   *Tự động trừ buổi liệu trình:* Khi lịch hẹn có gắn với Thẻ liệu trình chuyển sang trạng thái `COMPLETED`, hệ thống tự động cộng `+1` vào số buổi đã sử dụng (`used_sessions`).
*   **Quản lý Khách hàng & Thẻ Liệu Trình (CRM & Packages):**[cite: 1]
    *   Danh sách khách hàng (Hiển thị Tên, SĐT, Số lần đến, Ghi chú tình trạng da/sức khỏe)[cite: 1].
    *   **Quản lý Thẻ liệu trình (Customer Packages):** Cấp thẻ liệu trình mới cho khách (VD: Gói trị mụn 10 buổi), theo dõi tiến độ từng buổi và lịch sử trừ buổi.
*   **Quản lý Nhân sự, Ca làm việc & Dịch vụ (Tenant Settings):**[cite: 1]
    *   CRUD Nhân viên (Kỹ thuật viên, Lễ tân)[cite: 1].
    *   **Cấu hình Lịch làm việc (Staff Schedules):** Thiết lập giờ làm việc theo thứ trong tuần cho từng KTV và đăng ký ngày nghỉ phép (Day-off).
    *   CRUD Dịch vụ (Tên, Giá, Thời gian thực hiện, Loại dịch vụ: Lẻ / Liệu trình,Số buổi mặc định, Trạng thái Active/Inactive)[cite: 1].
    *   Thiết lập thông tin chung: Tên Spa, URL Slug, Logo, Giờ mở/đóng cửa, Thời gian nghỉ chuyển tiếp giữa 2 ca (Buffer time, VD: 10 phút dọn giường)[cite: 1].
*   **Báo cáo & Thống kê (Simple Report):**[cite: 1]
    *   Lọc và thống kê tổng số lượng dịch vụ và tổng giá trị dịch vụ mà từng Kỹ thuật viên đã hoàn thành (`COMPLETED`) theo khoảng thời gian (Ngày/Tuần/Tháng) để chủ Spa tính hoa hồng[cite: 1].

---

## 4. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL REQUIREMENTS)[cite: 1]

*   **Bảo mật Multi-tenant 2 lớp (Bắt buộc):**[cite: 1]
    1. *Tầng Application (FastAPI):* Sử dụng Dependency Injection tự động lọc `WHERE tenant_id = current_tenant_id` cho mọi Query[cite: 1].
    2. *Tầng Database (PostgreSQL):* Kích hoạt Row-Level Security (RLS) trên toàn bộ các bảng có `tenant_id` thông qua biến session `app.current_tenant_id`.
*   **Chống xung đột (Concurrency Control):** Backend bắt buộc dùng Database Transaction + Row Locking (`SELECT ... FOR UPDATE`) trên lịch của Kỹ thuật viên khi xử lý API Booking[cite: 1]. Đảm bảo nếu 2 khách đặt cùng 1 slot của 1 KTV trong cùng 1 mili-giây, chỉ 1 người thành công[cite: 1].
*   **Hiệu năng:** Thời gian phản hồi API (Latency) < 300ms[cite: 1].

---

## 5. CẤU TRÚC CƠ SỞ DỮ LIỆU CỐT LÕI (CORE DATABASE SCHEMA)[cite: 1]

*(Mọi bảng đều có `id` (UUID/BigInt PK), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ))[cite: 1].*

1.  **Bảng `tenants`** (Thông tin các Spa dùng SaaS)[cite: 1]
    *   `id` (PK), `slug` (Unique Index - VD: `spa-hoa-hong`), `name`, `logo_url`, `theme_color`, `open_time`, `close_time`, `buffer_minutes` (Default: 10), `status`[cite: 1].
2.  **Bảng `users`** (Tài khoản Khách & Staff thuộc từng Spa)[cite: 1]
    *   `id` (PK), `tenant_id` (FK -> tenants), `role` (`ADMIN`, `STAFF`, `CUSTOMER`), `full_name`, `phone_number`, `password_hash`, `notes`, `is_active`[cite: 1].
    *   *Constraint:* Unique(`tenant_id`, `phone_number`) -> Cho phép 1 SĐT có thể làm khách ở nhiều Spa khác nhau.
3.  **Bảng `staff_schedules`** (Ca làm việc của Kỹ thuật viên)
    *   `id` (PK), `tenant_id` (FK), `staff_id` (FK -> users), `day_of_week` (0=CN .. 6=Thứ 7), `start_time` (Time), `end_time` (Time), `is_day_off` (Boolean).
4.  **Bảng `services`** (Danh mục dịch vụ & Gói liệu trình)[cite: 1]
    *   `id` (PK), `tenant_id` (FK), `name`, `description`, `duration_minutes`, `price`, `is_package` (Boolean - Là thẻ liệu trình?), `total_sessions` (Số buổi nếu là package, Default: 1), `is_active`[cite: 1].
5.  **Bảng `customer_packages`** (Thẻ liệu trình khách hàng đã mua)
    *   `id` (PK), `tenant_id` (FK), `customer_id` (FK -> users), `service_id` (FK -> services), `package_name`, `total_sessions` (Tổng số buổi), `used_sessions` (Số buổi đã làm, Default: 0), `expiry_date` (TIMESTAMPTZ, nullable), `status` (`ACTIVE`, `COMPLETED`, `EXPIRED`).
6.  **Bảng `bookings`** (Phiên đặt lịch tổng)[cite: 1]
    *   `id` (PK), `tenant_id` (FK), `customer_id` (FK -> users), `staff_id` (FK -> users, nullable), `start_time` (TIMESTAMPTZ), `end_time` (TIMESTAMPTZ), `total_duration_minutes`, `total_price`, `status` (`PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `NO_SHOW`), `note`[cite: 1].
7.  **Bảng `booking_items`** (Chi tiết đa dịch vụ trong 1 lần đặt lịch)
    *   `id` (PK), `tenant_id` (FK), `booking_id` (FK -> bookings), `service_id` (FK -> services), `customer_package_id` (FK -> customer_packages, nullable - Nếu dùng thẻ liệu trình để đặt), `duration_minutes`, `price` (Giá tại thời điểm đặt; bằng 0 nếu trừ thẻ liệu trình).

---

## 6. CHIẾN LƯỢC KINH DOANH & PHÁT TRIỂN (BUSINESS ROADMAP)[cite: 1]

*   **Giai đoạn 1 (Tháng 1 - Tháng 3) - Pilot & Co-create:** Triển khai thực tế tại Spa của bạn bè, miễn phí Setup, thu phí chia sẻ Server, tinh chỉnh UX/UI cho Lễ tân và Khách hàng[cite: 1].
*   **Giai đoạn 2 (Tháng 4 trở đi) - SaaS Commercialization:** Đóng gói bảng giá Basic (399K/tháng) và Pro (799K/tháng), mở rộng tích hợp Zalo ZNS / Zalo Mini App[cite: 1].

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
    > 2. Xây dựng luồng Đặt lịch 4 bước (Wizard): Chọn 1 hoặc nhiều dịch vụ (hoặc chọn dùng Thẻ liệu trình đang có) -> Chọn Kỹ thuật viên -> Chọn Ngày & Giờ trống -> Xác nhận.
    > 3. Xây dựng trang Cá nhân của khách: Xem lịch hẹn Sắp tới (cho phép Hủy nếu trước giờ quy định), Lịch sử làm đẹp, và Xem số buổi còn lại trong Thẻ liệu trình."