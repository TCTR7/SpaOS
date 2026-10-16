# TÀI LIỆU ĐẶC TẢ API (API CONTRACT)

*Quy tắc cho AI: Khi viết hoặc sửa bất kỳ API Endpoint nào ở Backend (FastAPI), BẮT BUỘC cập nhật Method, URL, Request Body và Response mẫu ngắn gọn vào file này để Frontend (Next.js) sử dụng ở Sprint 5 và 6.*

## 1. Xác thực & Định danh (Auth & Tenant Context)
- **Header bắt buộc cho Admin/Staff:** `Authorization: Bearer <jwt_token>`
- **Header/Param cho Khách hàng (Public/PWA):** Truyền `X-Tenant-Slug: <slug>` hoặc qua URL.

## 2. Danh sách Endpoints (AI tự động cập nhật khi code Backend)
Base URL: `http://localhost:8000/api/v1`. Lỗi trả về dạng `{"detail": "..."}`. `GET /health` (không prefix) -> `{"status":"ok"}`.

### 2.1. Auth (Sprint 1)
JWT payload: `sub` (user_id), `tenant_id`, `role` (`ADMIN|STAFF|CUSTOMER`), `exp`. Mọi response token có dạng:
```json
{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600,
  "user": { "id": "uuid", "tenant_id": "uuid", "role": "ADMIN", "full_name": "...", "phone_number": "...", "is_active": true } }
```

| Method | URL | Header | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| POST | `/auth/register-tenant` | - | `{ "tenant_name", "tenant_slug", "admin_full_name", "phone_number", "password"(>=6) }` | `201` Token (user.role=`ADMIN`). `409` nếu slug trùng |
| POST | `/auth/register` | `X-Tenant-Slug` | `{ "full_name", "phone_number", "password"(>=6) }` | `201` Token (role=`CUSTOMER`). `409` trùng SĐT trong Spa, `404` slug sai |
| POST | `/auth/login` | `X-Tenant-Slug` | `{ "phone_number", "password" }` | `200` Token. `401` sai thông tin, `404` slug sai |
| GET | `/auth/me` | `Authorization: Bearer` | - | `200` `{ "user": {...}, "tenant": { "id","slug","name","logo_url","theme_color","buffer_minutes","status" } }`. `401` token sai/hết hạn |

Ghi chú: `phone_number` dạng `^\+?\d{9,15}$`; `tenant_slug` dạng `[a-z0-9-]`. `tenant_id` luôn lấy từ JWT/slug, KHÔNG gửi trong body. Admin/Staff đăng nhập cũng dùng `/auth/login` với `X-Tenant-Slug` của Spa.
### 2.2. Public & Tenant Settings (Sprint 2)
Mọi endpoint dưới đây (trừ Public) cần `Authorization: Bearer <jwt>`. Quyền: ADMIN = chủ Spa, STAFF = kỹ thuật viên/lễ tân. Sai quyền -> `403`, không tìm thấy (kể cả thuộc tenant khác) -> `404`, dữ liệu sai -> `422`, trùng SĐT -> `409`. PATCH chỉ cập nhật các field được gửi; field bắt buộc không được gửi `null`.

| Method | URL | Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/public/tenants/{slug}` | Public | - | `200` `{ id, slug, name, logo_url, theme_color, open_time, close_time, buffer_minutes, services: [Service] }` (chỉ dịch vụ `is_active=true`). `404` slug sai/tenant không active |
| GET | `/tenants/me` | ADMIN | - | `200` `{ id, slug, name, logo_url, theme_color, open_time, close_time, buffer_minutes, status }` |
| PATCH | `/tenants/me` | ADMIN | `{ name?, logo_url?, theme_color?, open_time?("HH:MM:SS"), close_time?, buffer_minutes?(0-180) }` | `200` như trên. `422` nếu `close_time <= open_time` |

### 2.3. Dịch vụ (`services`)
`Service` = `{ id, name, description, duration_minutes, price("350000.00"), is_package, total_sessions, is_active }`. Dịch vụ lẻ luôn có `total_sessions=1`.

| Method | URL | Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/services` | ADMIN, STAFF | query: `is_active?`, `is_package?` | `200` `[Service]` |
| POST | `/services` | ADMIN | `{ name, description?, duration_minutes(>0), price(>=0), is_package=false, total_sessions=1, is_active=true }` | `201` Service |
| PATCH | `/services/{id}` | ADMIN | các field trên (tùy chọn) | `200` Service |
| DELETE | `/services/{id}` | ADMIN | - | `200` `{ id, deleted: true, mode: "hard"｜"soft" }`. `soft` (chuyển `is_active=false`) khi dịch vụ đã nằm trong `booking_items`/`customer_packages` |

### 2.4. Nhân sự & Ca làm việc (`staff`, `staff_schedules`)
`Staff/Customer` (UserDetail) = `{ id, tenant_id, role, full_name, phone_number, notes, is_active, created_at }`. `day_of_week`: 0=CN … 6=Thứ 7.

| Method | URL | Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/staff` | ADMIN | - | `200` `[UserDetail]` (role STAFF) |
| POST | `/staff` | ADMIN | `{ full_name, phone_number, password(>=6), notes? }` | `201` UserDetail. `409` trùng SĐT |
| PATCH | `/staff/{id}` | ADMIN | `{ full_name?, phone_number?, password?, notes?, is_active? }` | `200` UserDetail |
| GET | `/staff/{staff_id}/schedules` | ADMIN | - | `200` `[{ id, staff_id, day_of_week, start_time, end_time, is_day_off }]` sắp theo ngày |
| PUT | `/staff/{staff_id}/schedules` | ADMIN | `{ "schedules": [{ day_of_week(0-6), start_time, end_time, is_day_off=false }] }` (tối đa 7, không trùng `day_of_week`, `end_time > start_time` trừ khi `is_day_off`) | `200` danh sách mới. **Ghi đè toàn bộ** lịch cũ |

### 2.5. Khách hàng & Thẻ liệu trình (`customers`, `customer_packages`)
`CustomerPackage` = `{ id, tenant_id, customer_id, service_id, package_name, total_sessions, used_sessions, remaining_sessions, expiry_date, status("ACTIVE"｜"COMPLETED"｜"EXPIRED"), created_at }`.

| Method | URL | Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/customers` | ADMIN, STAFF | query: `q?` (tìm theo SĐT/họ tên), `limit`(50, max 200), `offset` | `200` `[UserDetail]` |
| POST | `/customers` | ADMIN, STAFF | `{ full_name, phone_number, notes?, password? }` (không có password -> sinh ngẫu nhiên) | `201` UserDetail. `409` trùng SĐT |
| PATCH | `/customers/{id}` | ADMIN, STAFF | `{ full_name?, notes? }` | `200` UserDetail |
| GET | `/customers/{customer_id}/packages` | ADMIN, STAFF | - | `200` `[CustomerPackage]` |
| GET | `/customer-packages` | ADMIN, STAFF | query: `customer_id?`, `status?`, `limit`, `offset` | `200` `[CustomerPackage]` |
| POST | `/customer-packages` | ADMIN, STAFF | `{ customer_id, service_id, package_name?, total_sessions?, expiry_date?(tương lai) }` — mặc định lấy từ service; service phải `is_package=true` và active, else `422` | `201` CustomerPackage (`used_sessions=0`, `status=ACTIVE`) |

### 2.6. Booking Engine (Sprint 3)
Quy ước: `date` = `YYYY-MM-DD` theo giờ `Asia/Ho_Chi_Minh`. Slot trả về kèm offset `+07:00`; `start_time`/`end_time` của booking trả về UTC (`TIMESTAMPTZ`). `start_time` gửi lên có offset (ISO8601); nếu không có offset sẽ hiểu là giờ Asia/Ho_Chi_Minh. Lỗi: `401` thiếu/sai token, `403` sai quyền, `404` không thấy (kể cả thuộc tenant khác), `409` xung đột (trùng lịch, hết buổi, sai luồng trạng thái), `422` dữ liệu sai.

`Booking` = `{ id, tenant_id, customer_id, staff_id, start_time, end_time, total_duration_minutes, total_price, status("PENDING"｜"CONFIRMED"｜"IN_PROGRESS"｜"COMPLETED"｜"CANCELLED"｜"NO_SHOW"), note, created_at, items: [{ id, service_id, customer_package_id, duration_minutes, price }] }`

| Method | URL | Header / Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/bookings/available-slots` | `X-Tenant-Slug` **hoặc** `Authorization: Bearer` (mọi role) | query: `date`, `service_ids` (lặp lại: `?service_ids=a&service_ids=b`), `staff_id?` (bỏ trống = Spa tự sắp xếp) | `200` `{ date, total_duration_minutes, buffer_minutes, slot_step_minutes(15), slots: [{ start_time, end_time, available_staff_ids: [uuid] }] }`. `404` dịch vụ/KTV/slug sai; `401` thiếu cả token lẫn slug |
| POST | `/bookings` | Bearer: CUSTOMER, ADMIN, STAFF | `{ start_time, staff_id?(null = tự sắp xếp), customer_id?(bắt buộc với ADMIN/STAFF; CUSTOMER lấy từ JWT), note?, items: [{ service_id, customer_package_id? }] (1-10) }` | `201` Booking (`status=PENDING`, `price` item dùng thẻ = 0). `409` KTV không làm việc/đã có lịch/không còn KTV trống/thẻ hết buổi; `422` thẻ sai khách/sai dịch vụ/không ACTIVE/hết hạn, `start_time` quá khứ (CUSTOMER); `403` khách đặt thay người khác |
| GET | `/bookings` | Bearer: mọi role | query: `date_from?`, `date_to?`, `staff_id?`, `status?`, `customer_id?`, `scope?`(`upcoming`｜`history`), `limit`(50, max 200), `offset`. CUSTOMER luôn chỉ thấy lịch của mình | `200` `[Booking]`. `upcoming`: trạng thái PENDING/CONFIRMED/IN_PROGRESS và chưa kết thúc (sắp xếp tăng dần); `history`: còn lại (giảm dần) |
| GET | `/bookings/{id}` | Bearer: mọi role (CUSTOMER chỉ lịch của mình) | - | `200` Booking kèm `items`. `404` |
| PATCH | `/bookings/{id}/status` | Bearer: ADMIN, STAFF | `{ "status": "CONFIRMED"｜"IN_PROGRESS"｜"COMPLETED"｜"CANCELLED"｜"NO_SHOW" }` | `200` Booking. Luồng hợp lệ: `PENDING→CONFIRMED｜CANCELLED`; `CONFIRMED→IN_PROGRESS｜COMPLETED｜CANCELLED｜NO_SHOW`; `IN_PROGRESS→COMPLETED｜CANCELLED`; sai luồng `409`; gửi lại trạng thái hiện tại = no-op `200`. Khi sang `COMPLETED`: item có `customer_package_id` → `used_sessions += 1` (khóa FOR UPDATE, chặn vượt `total_sessions` → `409`; bằng `total_sessions` thì thẻ → `COMPLETED`), không trừ 2 lần |
| POST | `/bookings/{id}/cancel` | Bearer: CUSTOMER (lịch của mình), ADMIN, STAFF | - | `200` Booking (`CANCELLED`, gọi lại vẫn `200`). CUSTOMER: chỉ hủy khi `PENDING/CONFIRMED` và cách giờ hẹn >= `CANCELLATION_MIN_HOURS` (mặc định 2 giờ) nếu không `409`. ADMIN/STAFF hủy được mọi lịch chưa kết thúc. Buổi thẻ liệu trình bị giữ chỗ được trả lại |

Ghi chú nghiệp vụ:
- Slot hợp lệ khi `[slot_start, slot_end]` nằm trọn trong `[max(open_time, ca.start), min(close_time, ca.end)]` và `[slot_start, slot_end + buffer)` không giao với booking (khác `CANCELLED`) của KTV (mỗi booking chiếm `[start, end + buffer)`). `day_of_week`: 0=CN … 6=Thứ 7. Slot trong quá khứ bị loại. Bước nhảy 15 phút.
- Chống Race Condition: `POST /bookings` khóa dòng `customer_packages` (nếu dùng thẻ) rồi dòng `users` của KTV và các `bookings` của KTV trong ngày bằng `SELECT ... FOR UPDATE` (thứ tự id tăng dần). "Spa tự sắp xếp" lock tuần tự các KTV có ca phù hợp và gán KTV rảnh đầu tiên.
- Số buổi khả dụng của thẻ = `total_sessions - used_sessions - số item đang nằm trong booking PENDING/CONFIRMED/IN_PROGRESS`.

### 2.7. Báo cáo Hiệu suất & Hoa hồng Kỹ thuật viên (`reports` - Sprint 4)
Quy ước: `start_date`, `end_date` = `YYYY-MM-DD` theo giờ `Asia/Ho_Chi_Minh` (quy đổi biên `[00:00:00+07:00, ngày_kế 00:00:00+07:00)` sang UTC khi lọc `bookings.start_time`). Chỉ tính các lịch hẹn `status = COMPLETED`.

| Method | URL | Quyền | Query Params | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/reports/staff-performance` | ADMIN | `start_date`, `end_date` (`end_date >= start_date`, else `422`), `staff_id?` (`404` nếu KTV không thuộc Spa) | `200` `{ start_date, end_date, total_completed_bookings, total_completed_services, total_revenue("500000.00"), items: [{ staff_id, full_name, phone_number, is_active, completed_bookings_count, completed_services_count, single_services_count, package_sessions_count, total_revenue }] }` |

### 2.8. Thông báo Web Push & In-App (`notifications` - Sprint 4)
*(Lưu ý PO: Bỏ tích hợp Telegram Bot, chỉ dùng Web Push chuẩn VAPID + In-App Notification).*
`Notification` = `{ id, tenant_id, user_id, title, body, type("BOOKING_CREATED"｜"BOOKING_CONFIRMED"｜"BOOKING_IN_PROGRESS"｜"BOOKING_COMPLETED"｜"BOOKING_CANCELLED"｜"BOOKING_NO_SHOW"), booking_id, is_read, created_at }`.

| Method | URL | Header / Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/notifications/vapid-public-key` | Public (không cần JWT) | - | `200` `{ "public_key": "<VAPID_PUBLIC_KEY>", "enabled": true｜false }` |
| POST | `/notifications/subscribe` | Bearer: mọi role | `{ endpoint, keys: { p256dh, auth }, user_agent? }` | `201` `{ id, endpoint, user_id, tenant_id, created_at }` (idempotent upsert theo `(tenant_id, endpoint)`) |
| DELETE | `/notifications/unsubscribe` | Bearer: mọi role | `{ endpoint }` | `200` `{ "unsubscribed": true｜false }` |
| GET | `/notifications` | Bearer: mọi role | query: `unread_only=false`, `limit`(30, max 100), `offset`(0) | `200` `{ unread_count, items: [Notification] }` (mới nhất trước, chỉ của user hiện tại trong tenant) |
| PATCH | `/notifications/read-all` | Bearer: mọi role | - | `200` `{ "marked_read": <int> }` |
| PATCH | `/notifications/{id}/read` | Bearer: mọi role | - | `200` Notification (`is_read=true`). `404` nếu không tồn tại hoặc của user/tenant khác |

Ghi chú tự động bắn thông báo (`BackgroundTasks`, non-blocking — lỗi Web Push không bao giờ làm fail giao dịch đặt lịch; subscription trả `404/410` tự động bị xóa):
- Khách tạo lịch (`POST /bookings`) hoặc khách hủy lịch (`POST /bookings/{id}/cancel`) -> Tạo thông báo in-app & bắn Web Push tới toàn bộ `ADMIN` và `STAFF` đang active của Spa (KTV được giao lịch nhận tiêu đề riêng).
- Admin/Staff cập nhật trạng thái (`PATCH /bookings/{id}/status` sang `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `NO_SHOW`) hoặc hủy lịch -> Tạo thông báo in-app & bắn Web Push tới `CUSTOMER` sở hữu lịch hẹn.

