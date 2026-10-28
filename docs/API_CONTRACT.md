# TÀI LIỆU ĐẶC TẢ API (API CONTRACT)

*Quy tắc cho AI: Khi viết hoặc sửa bất kỳ API Endpoint nào ở Backend (FastAPI), BẮT BUỘC cập nhật Method, URL, Request Body và Response mẫu ngắn gọn vào file này để Frontend (Next.js) sử dụng ở Sprint 5 và 6.*

## 1. Xác thực & Định danh (Auth & Tenant Context)

**Hiện hành 28/10/2026:** shared SaaS theo `0012_shared_spas`; xem phần **Shared SaaS 0012** cuối tài liệu cho auth, spa, phân công, gói và directory. Các mục triển khai riêng/deployment branding 0005–0007 giữ làm lịch sử; quy tắc shared mới có ưu tiên khi khác nhau. `tenant_id` vẫn là chi nhánh, không phải thương hiệu/chủ spa.
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

Ghi chú: `phone_number` sau chuẩn hóa dạng `^\+?\d{9,15}$`; số mobile +84/84 đổi về 0 và bỏ khoảng trắng/dấu phân cách. `tenant_slug` dạng `[a-z0-9-]`. `tenant_id` luôn lấy từ JWT/slug, KHÔNG nhận tenant ghi nghiệp vụ từ body. Admin/Staff ưu tiên `/auth/login` **không** `X-Tenant-Slug`; khách đăng nhập theo nhánh với header này. Header nhánh được giữ cho tương thích management đã liên kết.
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
| GET | `/customer-packages/me` | CUSTOMER | Không nhận customer_id/tenant_id từ client; lấy từ JWT | `200` `[MyCustomerPackage]`: các trường CustomerPackage + `reserved_sessions` (PENDING/CONFIRMED/IN_PROGRESS), `available_sessions` = max(0, total-used-reserved); thẻ hết hạn/không ACTIVE trả khả dụng 0 |
| GET | `/customer-packages` | ADMIN, STAFF | query: `customer_id?`, `status?`, `limit`, `offset` | `200` `[CustomerPackage]` |
| POST | `/customer-packages` | ADMIN, STAFF | `{ customer_id, service_id, package_name?, total_sessions?, expiry_date?(tương lai; thiếu offset hiểu là Asia/Ho_Chi_Minh, lưu UTC) }` — mặc định lấy từ service; service phải `is_package=true` và active, else `422` | `201` CustomerPackage (`used_sessions=0`, `status=ACTIVE`) |

### 2.6. Booking Engine (Sprint 3)

#### Bổ sung T08a/T08b — 19/10/2026

- Quyết định: bổ sung `customer_name`, `staff_name` (string hoặc null) vào **mọi** Booking response; mỗi item thêm `service_name` (string hoặc null). Chỉ chiếu tên cho những lịch đã qua lọc quyền hiện có; không thêm SĐT/notes/hồ sơ. Tên là dữ liệu hiện hành, không thay snapshot giá/thời lượng; quan hệ thiếu trả null, UI hiện “Chưa có tên…” thay UUID. Hai truy vấn theo lô, lọc tenant_id, không lazy loading hoặc một request cho từng card.
- `GET /bookings` và `GET /customers` vẫn trả mảng như trước, giữ nguyên query/errors/quyền. Thêm response headers `X-Has-More: true|false`, `X-Next-Offset: <offset+limit>|""`; lấy tối đa limit+1 để xác định trang sau, không COUNT toàn bảng. Các điều kiện quyền áp dụng **trước** phân trang/has_more; limit 1..200, offset >=0. Bookings giữ thứ tự start_time rồi id; customers full_name rồi id. Offset là dữ liệu đang thay đổi, không phải snapshot; client bỏ trùng theo ID và tải lại trang đầu sau mutation/đổi bộ lọc. UI báo số đã tải/còn dữ liệu, chỉ tải trang tiếp khi người dùng yêu cầu.
- `GET /public/tenants/{slug}` thêm `staff: [{id, full_name}]`: chỉ KTV STAFF đang active của đúng chi nhánh, sắp tên/id, độc lập ngày hoặc slots đã lọc. Không trả phone, notes, lịch riêng, customer hay danh tính đăng nhập. Slug sai/chi nhánh không ACTIVE vẫn 404. Lỗi tải nguồn này dùng retry của public tenant; không suy ra nhân sự từ số giờ trống hôm nay.
- Tra cứu khách khi tạo lịch dùng `GET /customers?q=...&limit=50&offset=...` với phân trang có chủ ý; STAFF vẫn chỉ thấy khách đang phụ trách. Không tải tự động toàn CRM để ghép tên lịch. Không có endpoint mới hoặc migration/RLS mới. Frontend tiêu thụ header qua proxy cùng origin hiện hành.
Quy ước: `date` = `YYYY-MM-DD` theo giờ `Asia/Ho_Chi_Minh`. Slot trả về kèm offset `+07:00`; `start_time`/`end_time` của booking trả về UTC (`TIMESTAMPTZ`). `start_time` gửi lên có offset (ISO8601); nếu không có offset sẽ hiểu là giờ Asia/Ho_Chi_Minh. Lỗi: `401` thiếu/sai token, `403` sai quyền, `404` không thấy (kể cả thuộc tenant khác), `409` xung đột (trùng lịch, hết buổi, sai luồng trạng thái), `422` dữ liệu sai.

`Booking` = `{ id, tenant_id, customer_id, customer_name(string|null), staff_id, staff_name(string|null), start_time, end_time, total_duration_minutes, total_price, status("PENDING"｜"CONFIRMED"｜"IN_PROGRESS"｜"COMPLETED"｜"CANCELLED"｜"NO_SHOW"), note, created_at, items: [{ id, service_id, service_name(string|null), customer_package_id, duration_minutes, price }] }`

| Method | URL | Header / Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/bookings/available-slots` | `X-Tenant-Slug` **hoặc** `Authorization: Bearer` (mọi role) | query: `date`, `service_ids` (lặp lại: `?service_ids=a&service_ids=b`), `staff_id?` (bỏ trống = Spa tự sắp xếp) | `200` `{ date, total_duration_minutes, buffer_minutes, slot_step_minutes(15), slots: [{ start_time, end_time, available_staff_ids: [uuid] }] }`. `404` dịch vụ/KTV/slug sai; `401` thiếu cả token lẫn slug |
| POST | `/bookings` | Bearer: CUSTOMER, ADMIN, STAFF | `{ start_time, staff_id?(null = tự sắp xếp), customer_id?(bắt buộc với ADMIN/STAFF; CUSTOMER lấy từ JWT), note?, items: [{ service_id, customer_package_id? }] (1-10) }` | `201` Booking (`status=PENDING`, `price` item dùng thẻ = 0). `409` KTV không làm việc/đã có lịch/không còn KTV trống/thẻ hết buổi; `422` thẻ sai khách/sai dịch vụ/không ACTIVE/hết hạn, `start_time` quá khứ (CUSTOMER); `403` khách đặt thay người khác |
| GET | `/bookings` | Bearer: mọi role | query: `date_from?`, `date_to?`, `staff_id?`, `status?`, `customer_id?`, `scope?`(`upcoming`｜`history`), `limit`(50, max 200), `offset`. CUSTOMER luôn chỉ thấy lịch của mình | `200` `[Booking]`. `upcoming`: trạng thái PENDING/CONFIRMED/IN_PROGRESS và chưa kết thúc (sắp xếp tăng dần); `history`: còn lại (giảm dần) |
| GET | `/bookings/{id}` | Bearer: mọi role (CUSTOMER chỉ lịch của mình) | - | `200` Booking kèm `items`. `404` |
| PATCH | `/bookings/{id}/status` | Bearer: ADMIN, STAFF | `{ "status": "CONFIRMED"｜"IN_PROGRESS"｜"COMPLETED"｜"CANCELLED"｜"NO_SHOW" }` | `200` Booking. Luồng hợp lệ: `PENDING→CONFIRMED｜CANCELLED`; `CONFIRMED→IN_PROGRESS｜COMPLETED｜CANCELLED｜NO_SHOW`; `IN_PROGRESS→COMPLETED｜CANCELLED`; sai luồng `409`; gửi lại trạng thái hiện tại = no-op `200`. Khi sang `COMPLETED`: khóa thẻ theo ID trước khi khóa booking; đọc lại trạng thái dưới khóa để chống deadlock với POST và bảo đảm idempotent. item có `customer_package_id` → `used_sessions += 1` (khóa FOR UPDATE, chặn vượt `total_sessions` → `409`; bằng `total_sessions` thì thẻ → `COMPLETED`), không trừ 2 lần |
| POST | `/bookings/{id}/cancel` | Bearer: CUSTOMER (lịch của mình), ADMIN, STAFF | - | `200` Booking (`CANCELLED`, gọi lại vẫn `200`). CUSTOMER: chỉ hủy khi `PENDING/CONFIRMED` và cách giờ hẹn >= `CANCELLATION_MIN_HOURS` (mặc định 2 giờ) nếu không `409`. ADMIN/STAFF hủy được mọi lịch chưa kết thúc. Buổi thẻ liệu trình bị giữ chỗ được trả lại |

Ghi chú nghiệp vụ:
- Slot hợp lệ khi `[slot_start, slot_end]` nằm trọn trong `[max(open_time, ca.start), min(close_time, ca.end)]` và `[slot_start, slot_end + buffer)` không giao với booking (khác `CANCELLED`) của KTV (mỗi booking chiếm `[start, end + buffer)`). `day_of_week`: 0=CN … 6=Thứ 7. Slot trong quá khứ bị loại. Bước nhảy 15 phút.
- Chống Race Condition: `POST /bookings` khóa dòng `customer_packages` (nếu dùng thẻ) rồi dòng `users` của KTV và các `bookings` của KTV trong ngày bằng `SELECT ... FOR UPDATE` (thứ tự id tăng dần). "Spa tự sắp xếp" lock tuần tự các KTV có ca phù hợp và gán KTV rảnh đầu tiên.
- Số buổi khả dụng của thẻ = `total_sessions - used_sessions - số item đang nằm trong booking PENDING/CONFIRMED/IN_PROGRESS`.

### 2.7. Báo cáo Hiệu suất & Hoa hồng Kỹ thuật viên (`reports` - Sprint 4)
Quy ước: `start_date`, `end_date` = `YYYY-MM-DD` theo giờ `Asia/Ho_Chi_Minh` (quy đổi biên `[00:00:00+07:00, ngày_kế 00:00:00+07:00)` sang UTC khi lọc `bookings.start_time`). Chỉ tính các lịch hẹn `status = COMPLETED`.

| Method | URL | Quyền | Query Params | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/reports/staff-performance` | ADMIN | `start_date`, `end_date` (`end_date >= start_date`, khoảng tối đa 366 ngày, else `422`), `staff_id?` (`404` nếu KTV không thuộc Spa) | `200` `{ start_date, end_date, timezone: "Asia/Ho_Chi_Minh", staff: [{ staff_id, full_name, is_active, completed_bookings_count, completed_services_count, single_services_count, package_sessions_count, total_revenue }], totals: { completed_bookings_count, completed_services_count, single_services_count, package_sessions_count, total_revenue } }` |

### 2.8. Thông báo Web Push & In-App (`notifications` - Sprint 4)
*(Lưu ý PO: Bỏ tích hợp Telegram Bot, chỉ dùng Web Push chuẩn VAPID + In-App Notification).*
`Notification` = `{ id, title, body, type("BOOKING_CREATED"｜"BOOKING_CONFIRMED"｜"BOOKING_IN_PROGRESS"｜"BOOKING_COMPLETED"｜"BOOKING_CANCELLED"｜"BOOKING_NO_SHOW"), booking_id, is_read, created_at }`.

| Method | URL | Header / Quyền | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/notifications/vapid-public-key` | Public (không cần JWT) | - | `200` `{ "public_key": "<VAPID_PUBLIC_KEY>", "enabled": true }`; `enabled=false` nếu thiếu public hoặc private key (public_key có thể rỗng) |
| POST | `/notifications/subscribe` | Bearer: mọi role | `{ endpoint, keys: { p256dh, auth }, expirationTime? }`; user agent lấy từ header `User-Agent` | `201` `{ id, endpoint, created_at }` (serialize theo `(tenant_id, endpoint)` bằng transaction advisory lock; chuyển quyền sở hữu endpoint sang user hiện tại) |
| DELETE | `/notifications/unsubscribe` | Bearer: mọi role | `{ endpoint }` | `200` `{ "deleted": <int> }` |
| GET | `/notifications` | Bearer: mọi role | query: `unread_only=false`, `limit`(30, max 100), `offset`(0) | `200` `{ unread_count, items: [Notification] }` (mới nhất trước, chỉ của user hiện tại trong tenant) |
| PATCH | `/notifications/read-all` | Bearer: mọi role | - | `200` `{ "updated": <int> }` |
| PATCH | `/notifications/{id}/read` | Bearer: mọi role | - | `200` Notification (`is_read=true`). `404` nếu không tồn tại hoặc của user/tenant khác |

Ghi chú tự động bắn thông báo (`BackgroundTasks`, non-blocking — lỗi Web Push không bao giờ làm fail giao dịch đặt lịch; subscription trả `404/410` tự động bị xóa):
- Khách tạo/hủy/dời lịch -> thông báo in-app và Web Push cho ADMIN, KTV thực hiện lịch và KTV phụ trách hồ sơ hiện tại, chỉ trong cùng chi nhánh và đang hoạt động; không gửi người thực hiện thao tác. KTV thực hiện trùng người phụ trách chỉ nhận một lần. Kiểm tra lại quyền trước lưu và trước gửi Push.
- Admin/Staff tạo lịch (`POST /bookings`, `POST /bookings/manual-batches`), cập nhật trạng thái, hủy hoặc dời lịch -> thông báo cho CUSTOMER sở hữu lịch đang hoạt động. CREATED dùng tiêu đề “Bạn có lịch hẹn mới”; Push dẫn về `/{slug}/appointments`. Mỗi lịch trong batch có một thông báo riêng. Chỉ chạy sau commit thành công; rollback không thông báo. Retry batch cùng request_id có thể khôi phục thông báo chưa lưu, nhưng thông báo CREATED đã lưu không bị gửi lại (khóa customer + kiểm tra tenant/booking/type/user). GET kết quả không phát thông báo. Không tự retry Push đã lỗi sau khi thông báo in-app được lưu.


### Web Push: điều hướng theo người nhận
Payload push có `url`: ADMIN/STAFF → `/admin/bookings`; CUSTOMER → `/<tenant_slug>/appointments`, slug lấy từ tenant của sự kiện. Không dùng slug spa-demo mặc định.


## Quyền khách hàng cố định và sửa lịch — 17/10/2026

- UserDetail thêm assigned_staff_id (UUID hoặc null). Hồ sơ khách có KTV phụ trách cố định, độc lập với staff_id của từng booking.
- STAFF chỉ đọc/sửa khách được giao; các danh sách customers, customer-packages, bookings được lọc tại backend. Đọc/sửa ID của khách không phụ trách trả 404. KTV không tự nhận/chuyển quyền bằng request body.
- Khách mới do STAFF tạo được giao cho STAFF đó; khách chưa phân công được gán KTV của booking thành công đầu tiên. Các booking sau không đổi chủ hồ sơ. Hồ sơ chưa phân công chỉ Admin và chính khách truy cập.
- PATCH /customers/{customer_id}/assignment: ADMIN; body {assigned_staff_id: UUID|null}; 200 UserDetail. KTV đích phải active và cùng tenant (không hợp lệ 404); STAFF/CUSTOMER 403. Chuyển quyền không tự đổi KTV/giờ trong lịch đã đặt.
- PATCH /bookings/{booking_id}: ADMIN, KTV phụ trách hồ sơ, CUSTOMER sở hữu lịch. Body {start_time, staff_id?: UUID|null, note?: string|null}; **T09: bỏ staff_id giữ KTV hiện tại, explicit null = tự sắp xếp**; bỏ note = giữ nguyên, null = xóa ghi chú. Chỉ PENDING/CONFIRMED; giờ mới phải tương lai. CUSTOMER chỉ đổi trước giờ cũ tối thiểu CANCELLATION_MIN_HOURS. Trạng thái không hợp lệ/sát giờ/trùng slot 409; thẻ hết hiệu lực ở giờ mới 422; không có quyền 404.

### T01 — Tạo lịch tại quầy atomically, chống lặp — quyết định 19/10/2026

- Thay chuỗi POST riêng trong UI bằng `POST /bookings/manual-batches` (ADMIN/STAFF). Body `{request_id:UUID, customer_id?:UUID, new_customer?:{full_name,phone_number,notes?}, staff_id?:UUID|null, items:[{service_id,customer_package_id?}], start_times:[ISO8601], note?:string}`. Đúng một customer_id/new_customer; 1–10 item, 1–20 giờ khác nhau. Không nhận tenant/actor/giá/số buổi từ client. Service liệu trình chưa có thẻ được cấp đúng một thẻ theo menu tại server, dùng chung các buổi.
- Một transaction tạo khách nếu cần, cấp thẻ nếu cần, toàn bộ lịch/items/audit và kết quả request. Một buổi lỗi 409/422 hoặc lỗi trước commit: rollback tất cả, không xóa bù dữ liệu. Giá/thời lượng/số buổi theo server, dùng lại kiểm tra khóa hiện hành; prelock thẻ rồi KTV theo ID ổn định cho toàn batch trước tạo các buổi.
- Request được serialize theo tenant + actor + request_id. Cùng mã/cùng nội dung trả cùng IDs với 201; khác nội dung 409. Ghi hash nội dung và IDs kết quả, không ghi payload hồ sơ/mật khẩu vào bảng chống lặp. Bảng manual_booking_batches có tenant FK và ENABLE/FORCE RLS theo app.current_tenant_id, actor lấy JWT. Không xóa kết quả để cho tái dùng mã.
- `GET /bookings/manual-batches/{request_id}` đối chiếu kết quả (200 `{request_id,customer_id,package_ids,booking_ids}`), cùng actor/tenant và quyền khách hiện tại; 404 không có hoặc ngoài quyền. GET lấy cùng advisory lock nên đợi transaction POST cùng mã hoàn tất; không tự tạo dữ liệu hoặc replay POST. CUSTOMER 403.
- Khi mất phản hồi/5xx, UI khóa tạo mới và giữ mã/nội dung cho retry có chủ ý hoặc GET kiểm tra. sessionStorage chỉ lưu request UUID theo tenant/actor để đối chiếu sau reload; không lưu tên/SĐT/ghi chú/payload. Reload mở vùng khôi phục, chỉ GET khi bấm kiểm tra, không tự POST. GET 404 đúng thông báo không có kết quả mới cho nhập lại nhưng **giữ nguyên UUID**, vì POST cũ có thể chưa tới server; request tới muộn cùng mã không thể tạo batch thứ hai. 404 vì mất quyền không mở khóa. Khi đã commit, GET/retry trả IDs cũ, không cấp thêm thẻ/lịch. Quyền thay đổi không được dùng kết quả cũ để lộ hồ sơ.
- Trạng thái triển khai/test xem PROGRESS; quyết định contract không đồng nghĩa đã nghiệm thu T01a/b.

### T09b — Gợi ý dời lịch theo snapshot — 19/10/2026

- `GET /bookings/{booking_id}/available-slots?date=YYYY-MM-DD&staff_id=<uuid optional>`; Bearer ADMIN, STAFF phụ trách hồ sơ hoặc CUSTOMER sở hữu. Trả AvailableSlotsOut như endpoint đặt mới, nhưng duration lấy `booking.total_duration_minutes` (không đọc lại duration/is_active của menu). Query staff_id cụ thể lọc KTV đó, bỏ = xem KTV active có giờ trống. UI mặc định gửi KTV hiện tại.
- Xác minh tenant/ownership trước khi loại đúng booking_id trên path khỏi busy; không nhận exclude ID tùy ý từ public query. Chỉ PENDING/CONFIRMED, CUSTOMER phải còn trước giờ cũ >= CANCELLATION_MIN_HOURS; không đủ quyền/không tìm thấy 404, trạng thái/sát giờ 409, query sai 422. Quy đổi Asia/Ho_Chi_Minh, buffer/past giống đặt mới. Giờ cũ hợp lệ được đưa vào cả khi không trùng bước 15 phút; không coi lịch đang sửa là xung đột với chính nó.
- Gợi ý chỉ là lần đọc không khóa; PATCH vẫn khóa khách/thẻ/KTV/booking theo thứ tự hiện hành và kiểm tra xung đột dưới khóa, có thể trả 409. Không đổi ID/items/price/duration/số buổi. UI giữ giờ cũ nếu còn hợp lệ, không tự chọn giờ thay thế; hiển thị trước/sau, 409 giữ form và lịch gốc. Bàn giao hồ sơ vẫn Admin-only, mặc định false.
- Sửa trong một transaction: giữ nguyên booking ID, items, giá/thời lượng chốt, trạng thái và số buổi giữ chỗ. Thất bại giữ nguyên lịch cũ. Không nhận customer_id/items/price trong payload sửa (422).
- Mọi ghi dữ liệu khách/booking qua API và chuyển quyền serialize bằng advisory lock theo tenant+customer trước các row lock thẻ/KTV/booking.
- Thông báo gửi Admin + chủ hồ sơ hiện tại (loại actor); không broadcast cho KTV khác. Thông báo in-app cũ không còn đọc được sau chuyển quyền. Push đã giao tới thiết bị trước lúc chuyển quyền không thể thu hồi.
- Event BOOKING_RESCHEDULED cho đổi lịch; API không tạo booking mới hoặc hủy booking cũ.


## Thu tiền thủ công & nhật ký — 17/10/2026

Tất cả endpoint dưới đây chỉ dành cho ADMIN; STAFF/CUSTOMER trả 403, thiếu JWT 401. Tenant, người lập phiếu và người xác nhận lấy từ Dependency/JWT.

- POST /payments/invoices → 201 Invoice. Body đúng một trong {booking_id} hoặc {customer_package_id, legacy_amount_due?}. Chỉ một phiếu cho mỗi nguồn; gọi lặp trả phiếu cũ. Giá lịch lấy total_price đã chốt; giá thẻ mới lấy purchase_price tại lúc cấp thẻ. Với thẻ cũ purchase_price=null, Admin phải xác nhận legacy_amount_due (>=0). Không dùng giá menu hiện tại để đoán giá lịch sử; không cho đổi giá đã chốt qua request.
- GET /payments/invoices?customer_id?&limit=50&offset=0 → [Invoice], limit tối đa 200.
- GET /payments/invoices/{id} → Invoice; không thuộc tenant trả 404.
- GET /payments/invoices/{id}/entries?limit=100&offset=0 → [Entry], tối đa 200.
- POST /payments/invoices/{id}/receipts → 201 Entry. Body {amount: Decimal>0, method: CASH|BANK_TRANSFER, idempotency_key: UUID, note?: string|null}. Số tiền tối đa 12 chữ số, 2 số lẻ. Chặn tổng thu vượt khoản phải thu (409). Không nhận tenant_id, actor_id hoặc thời gian xác nhận từ client.
- POST /payments/entries/{id}/void → 201 Entry. Body {idempotency_key: UUID, reason: string không rỗng}. Ghi bút toán âm đối ứng đúng khoản thu gốc, không sửa/xóa lịch sử. Khoản thu chỉ hủy một lần; không hủy bút toán đối ứng (409).
- GET /payments/summary?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD → {date_from,date_to,timezone,cash,bank_transfer,net_received}. Khoảng tối đa 366 ngày; biên ngày theo Asia/Ho_Chi_Minh; thu/hủy tính theo thời điểm server ghi nhận. Số tiền là chuỗi Decimal. Thực thu ròng có thể âm trong ngày có hủy khoản thu cũ.
- GET /audit-logs?entity_id?&limit=50&offset=0 → [AuditEvent]; tối đa 200; mới nhất trước.

Invoice: {id,customer_id,booking_id?,customer_package_id?,amount_due,amount_paid,balance_due,status:UNPAID|PARTIAL|PAID,created_at}. Phiếu 0đ có trạng thái PAID và không cho thu thêm.
Entry: {id,invoice_id,amount,method,recorded_by,created_at,reversal_of?,note?}. Khoản hủy có amount âm và reversal_of trỏ khoản gốc.
AuditEvent: {id,actor_id?,action,entity_type,entity_id,details,created_at}.

Invariant:
- Các bảng payment_invoices/payment_entries/audit_logs có tenant_id + ENABLE/FORCE RLS. Ledger và audit bị chặn UPDATE/DELETE bằng trigger.
- Thu/hủy serialize theo mã idempotency (tenant-scoped) rồi khóa invoice FOR UPDATE; cùng mã/cùng payload trả cùng Entry, cùng mã/khác payload 409. Các mã khác nhau vẫn không thu vượt khi đồng thời.
- Mỗi thay đổi nghiệp vụ và audit được commit trong cùng transaction. Nhật ký không sao chép nội dung ghi chú sức khỏe hay mật khẩu; chỉ ghi tên trường thay đổi và dữ liệu vận hành cần thiết.
- Hủy lịch không tự hủy khoản thu; Admin đối chiếu và ghi hủy riêng. Bút toán hủy chỉ điều chỉnh sổ; thao tác hoàn tiền thực tế ở ngoài ứng dụng.
- Thẻ liệu trình thu ở phiếu bán thẻ; booking dùng thẻ có giá 0 để tránh thu thêm cho cùng buổi.
- Hiện chưa có sửa giá phiếu, giảm giá, hóa đơn thuế, tự động ngân hàng hoặc phân quyền thu ngân riêng.

## Bàn giao trong thao tác dời lịch
PATCH /bookings/{id} thêm transfer_customer?: boolean (mặc định false).
Chỉ ADMIN được gửi true (khác vai trò → 403). Sau khi giờ/KTV mới hợp lệ, hệ thống đổi KTV lịch và người phụ trách hồ sơ sang KTV đã chọn trong cùng transaction, ghi cả BOOKING_RESCHEDULED và CUSTOMER_ASSIGNED. Nếu trùng slot hoặc lỗi bất kỳ, cả lịch và quyền hồ sơ giữ nguyên. False giữ nguyên quyền cố định, kể cả khi KTV thực hiện khác.


## Danh sách thu tiền tự động — 17/10/2026
- GET /payments/collections?q=&scope=outstanding&limit=50&offset=0 → 200 [Collection]. Chỉ ADMIN; thiếu JWT 401, STAFF/CUSTOMER 403. q tối đa 100 ký tự, tìm tên/SĐT theo chuỗi literal; scope=outstanding|all, limit 1–200, offset>=0.
- Collection: {source_id,source_type:booking|package,customer_id,customer_name,phone_number,description,occurred_at,source_status,invoice_id:UUID|null,amount_due:Decimal|null,amount_paid:Decimal,balance_due:Decimal|null,status:UNPAID|PARTIAL|PAID|NEEDS_PRICE|COVERED|FREE}. Số tiền JSON dạng chuỗi; occurred_at là giờ hẹn hoặc ngày cấp thẻ. description gồm tên dịch vụ hiện tại (giá vẫn là snapshot).
- Tự kết hợp lịch hẹn và thẻ đã cấp trong tenant, không yêu cầu tạo phiếu trước; GET chỉ đọc, không ghi invoice/audit. Một query SQL có join/aggregate và phân trang, không query theo từng khách.
- outstanding chỉ gồm UNPAID/PARTIAL/NEEDS_PRICE; all gồm cả đã thu và miễn phí/dùng thẻ. Ưu tiên khoản chưa thu, sau đó thời gian nguồn giảm dần, loại nguồn và UUID để ổn định phân trang.
- Nếu đã có invoice, lấy giá đã chốt tại invoice và tổng ledger (kể cả hoàn tác); nếu chưa có, dùng Booking.total_price/CustomerPackage.purchase_price. Thẻ cũ NULL giá và chưa có invoice → NEEDS_PRICE, không đoán từ menu.
- Booking tổng 0 và tất cả items dùng thẻ → COVERED; tổng 0 còn lại → FREE. Lịch CANCELLED/NO_SHOW chưa có invoice không xuất hiện; nếu đã có invoice thì vẫn hiển thị để đối chiếu, không tự hủy khoản thu.
- UI Admin → Thu tiền: danh sách tự có dữ liệu; chọn Xác nhận đã thu để kiểm tra số tiền/phương thức, sau đó xác nhận. Invoice được chuẩn bị nội bộ qua API hiện có, không có bước lập phiếu thủ công. Mặc định thu toàn bộ balance_due; trả một phần là tùy chọn. Retry giữ nguyên body/idempotency key. Nếu ghi thành công nhưng tải lại thất bại, khóa thu tiếp cho đến khi tải lại số tiền thành công.
- Tổng thực thu hôm nay tải tự động theo ngày Việt Nam, cập nhật sau thu/hoàn tác. Nhật ký chung ở tab Lịch sử thao tác; lịch sử thu và hoàn tác nằm trong phần mở rộng của khoản đang chọn.


## Tài khoản quản trị chung và chi nhánh — 17/10/2026

tenant_id vẫn là mã chi nhánh nội bộ. Dữ liệu khách, quyền KTV phụ trách, lịch, dịch vụ/giá, thẻ và thu tiền giữ riêng từng chi nhánh; không đổi/xóa các ID cũ. login_accounts là danh tính xác thực cấp deployment (không có tenant_id vì dùng chung), có ENABLE/FORCE RLS theo account đã xác minh hoặc phone bootstrap. branch_memberships có tenant_id, FK kép tenant/user và FORCE RLS: đọc theo chi nhánh hiện tại hoặc account đã xác minh, ghi theo chi nhánh. Các bảng nghiệp vụ khác vẫn chỉ dùng RLS tenant, không nới policy để tổng hợp.

- POST /auth/login không có X-Tenant-Slug: body {phone_number,password}; 200 TokenResponse cho ADMIN/STAFF, chọn chi nhánh active đầu tiên được cấp (thứ tự membership created_at/id). Không có quyền/sai mật khẩu 401. CUSTOMER tiếp tục dùng đường dẫn chi nhánh và header hiện hành.
- POST /auth/login có X-Tenant-Slug: giữ tương thích API cũ/PWA; tài khoản quản trị đã liên kết kiểm tra mật khẩu chung. Tài khoản cũ chưa liên kết chỉ đăng nhập được bằng luồng cũ; không tự gộp theo số điện thoại.
- GET /branches → [BranchAccess {tenant:TenantOut,user:UserOut,is_owner:boolean}], chỉ danh tính quản trị đã liên kết; membership/user/tenant bị khóa được loại. CUSTOMER/unlinked 403.
- POST /branches/{branch_id}/switch → TokenResponse; thiếu quyền 404. Tenant trong JWT mới lấy từ membership được xác minh; không có quyền tự chỉ định branch_id trong các API nghiệp vụ. Token cũ không tự bị vô hiệu khi chủ spa chuyển, nhưng quyền/hoạt động được kiểm tra lại trên mỗi request.
- POST /branches → 201 BranchAccess; body {name}, extra forbid, tên 1–255 ký tự không rỗng. Chỉ ADMIN với is_owner ở chi nhánh hiện tại; tạo tenant, hồ sơ Admin và membership cùng tài khoản trong một transaction; mã đường dẫn tự sinh. Chi nhánh mới chưa có dịch vụ/nhân sự/lịch làm việc.
- POST /branches/{branch_id}/staff-access → 201 UserOut; body {source_staff_id}, extra forbid. Chỉ chủ hệ thống có quyền owner/Admin ở cả nguồn và đích; source_staff_id là STAFF active tại chi nhánh hiện tại. Cấp hồ sơ STAFF riêng tại đích nhưng cùng danh tính đăng nhập; gọi lại khôi phục hoạt động nếu đã có membership. Trùng hồ sơ SĐT khác danh tính 409; không tự gộp. Thu hồi bằng PATCH /staff/{id} is_active=false tại đích; token đích bị chặn ngay và đích biến mất khỏi danh sách.
- PATCH /staff/{id}: SĐT/mật khẩu của tài khoản một chi nhánh đồng bộ login_accounts; xung đột SĐT 409. Tài khoản đã có nhiều membership không cho đổi credentials từ API một chi nhánh (409). Tên/ghi chú/hoạt động vẫn riêng từng chi nhánh. Chưa có màn hình quản trị credentials chung.
- GET /branches/public (không JWT) → {brand_name,branches:[{id,name,slug}]}, chỉ chi nhánh ACTIVE của database deployment. Không trả người dùng, quyền hoặc thông tin tài chính. Khi deploy riêng, database phải chỉ chứa dữ liệu của đúng chủ spa; không dùng thư mục này trên database cũ chứa nhiều chủ độc lập trước khi tách dữ liệu.
- POST /auth/register-tenant: ở ENVIRONMENT=production luôn bị chặn 403, không mở lại bằng ALLOW_TENANT_REGISTRATION. Operator tạo chủ spa và chi nhánh đầu qua /operator; chủ spa tạo chi nhánh tiếp theo từ /branches sau đăng nhập. Xem mục Quản trị triển khai và cấp chủ spa bên dưới.

### Dashboard
GET /dashboard?day=YYYY-MM-DD&branch_id?&all_branches=false → DashboardOut; day mặc định hôm nay theo Việt Nam. ADMIN xem chi nhánh được cấp vai trò ADMIN; chủ có is_owner hiện tại mới được all_branches=true, chỉ tổng các chi nhánh có owner/Admin của chính account. Không chọn branch_id cùng all_branches (422), ngoài quyền 404, STAFF/CUSTOMER 403.

DashboardOut: {date,timezone:"Asia/Ho_Chi_Minh",branches:[{branch_id,name,metrics}],totals:metrics}.
metrics:
- appointments: lịch có start_time trong ngày, loại CANCELLED/NO_SHOW; in_progress và completed là số lịch theo hai trạng thái tương ứng.
- cash,bank_transfer,net_received: tổng PaymentEntry theo created_at trong ngày, gồm bút toán âm. completed_value: tổng Booking.total_price đã COMPLETED theo ngày start_time, độc lập thực thu.
- outstanding: tổng balance_due dương của toàn bộ nguồn theo quy tắc /payments/collections (không cắt ở limit 50/200); unknown_prices: số thẻ chưa đối chiếu, chưa cộng tiền ước đoán.
- active_packages: thẻ ACTIVE chưa hết buổi, chưa hết hạn tại thời điểm hiện tại (không phải snapshot ngày lịch sử).
- Các số tiền là chuỗi Decimal; tổng server cộng Decimal, không cộng tiền bằng JavaScript float.
- Backend duyệt các chi nhánh đã xác minh, gán RLS context riêng và luôn lọc tenant_id. Không dùng role bypass hay mở policy nghiệp vụ cho nhiều tenant; chi phí query tăng theo số chi nhánh.
- Giao diện “Tất cả chi nhánh” là chế độ tổng quan. Các đường dẫn ghi dữ liệu tiếp tục dùng chi nhánh cụ thể của JWT; giao diện ghi rõ chi nhánh hiện tại khi dẫn sang lịch/thu tiền.

### Chuyển đổi và giao diện
Migration 0005_branch_accounts chỉ tạo danh tính cho SĐT quản trị duy nhất trong dữ liệu cũ; không gộp cả khi password hash giống nhau. ADMIN hiện hữu được owner cho phạm vi hiện có của mình; không tự nối các tenant có chủ độc lập. Tài khoản bỏ qua do trùng số cần operator đối chiếu bằng scripts.branch_account_audit.
Đổi chi nhánh cấp token mới, hủy đăng ký Push của phiên chi nhánh trước, tải lại trang để xóa state cũ. Tab khác nhận storage event và tải lại; PWA customer giữ token riêng theo slug, URL cũ còn hoạt động.


## Quản trị triển khai và cấp chủ spa — 0006_operator_portal

### Bổ sung 0010 — quản lý chủ spa, bàn giao và phiên bản (22/10/2026)

- `GET /operator/system`: JWT operator; `{version,release_id,build_id,built_at}`, Cache-Control no-store. Swagger hiển thị version/release/build backend. `GET /api/system/version` là route Next.js (không nằm dưới /api/v1), công khai metadata build frontend đã đóng gói; không trả secrets. Bản trình duyệt nhúng metadata độc lập để phát hiện tab cũ.
- `GET /operator/owners/{provision_id}`: thông tin hiện tại `{id,full_name,phone_number,branches:[{id,name,slug,logo_url,address,active}]}`. Xác minh provision thuộc operator, membership chủ tại chi nhánh gốc và account active; không lấy tên/SĐT từ snapshot lịch sử để cập nhật. Không tự nhận quyền các tài khoản legacy chưa có provision.
- `PATCH /operator/owners/{provision_id}`: `{full_name,phone_number,current_password,identity_verified:true}`, extra forbid. Xác minh mật khẩu operator; cập nhật nguyên tử account và users tại từng membership tenant context, tăng auth_version, ghi audit. Trùng SĐT trả 409/rollback; không gộp danh tính. Trả DTO hiện tại như GET.
- `POST /operator/owners/{provision_id}/recovery-link`: `{current_password,identity_verified:true}` → `{token,expires_at}`. Xác minh chủ spa ngoài ứng dụng trước khi cấp, TTL 30 phút, token ngẫu nhiên chỉ trả một lần, DB chỉ lưu SHA256. Cấp mới vô hiệu link cũ.
- `POST /operator/recovery`: public `{token,password}` → `{updated:true}`. Không nhận account_id/tenant_id/operator_id; tra grant bằng hash hẹp, rồi xác minh account/membership. Row lock account + grant, kiểm tra hạn/consumed/auth_version; cập nhật mật khẩu mọi membership và thu hồi JWT cũ trong một transaction. Đồng thời hai claim chỉ một thành công. Đổi tài khoản/mật khẩu bình thường cũng vô hiệu grant cũ. Không tự đăng nhập.
- `GET /operator/owners/{provision_id}/events?limit=30&offset=0`: audit hỗ trợ tài khoản (limit 1–100), không chứa mật khẩu/token. Lịch sử cấp tài khoản hiện có vẫn append-only và không sửa snapshot.
- Bảng `owner_recovery_grants` có tenant_id/FK, ENABLE/FORCE RLS. Operator chỉ đọc/cấp cho provision đã xác minh; hash bootstrap chỉ đọc đúng grant, ghi consume phải đồng thời đúng tenant/hash. Không thêm quyền bypass hoặc role nghiệp vụ mới.
- UI `/admin/recover#token` bỏ fragment ngay khi đọc, token chỉ giữ trong memory; không persist hoặc đưa vào QR/tài liệu. Các bộ bàn giao tạo tại trình duyệt từ dữ liệu hiện tại và origin đang truy cập, không lưu file trên server, không chứa secrets.

Danh tính deployment_operators tách biệt UserRole và login_accounts nghiệp vụ. Mỗi deployment tối đa một operator (singleton database constraint); không có tenant_id vì là danh tính hạ tầng, có ENABLE/FORCE RLS theo operator_id hoặc phone bootstrap. owner_provisions có tenant_id, FK tenant/owner, operator_id, chống trùng request_id theo operator và append-only. Không nới RLS nghiệp vụ.

- POST /operator/login: {phone_number,password}, extra forbid. 200 {access_token,token_type:"bearer",expires_in:1800,operator:{id,full_name,phone_number}}. JWT aud=spaos-operator, scope=operator, version; sai thông tin 401, khóa sau 5 lần sai và trong 5 phút trả 429. Không có tài khoản mặc định.
- GET /operator/me → OperatorOut, operator JWT hợp lệ/active/version còn hiệu lực.
- POST /operator/logout → {logged_out:true}, tăng token_version nguyên tử, thu hồi mọi phiên operator cũ.
- GET /operator/owners?limit=50&offset=0 → [ProvisionOut], limit 1–200; chỉ lịch sử operator đã xác minh, mới nhất trước.
- POST /operator/owners → 201 ProvisionOut. Body {request_id:UUID,branch_name,owner_full_name,phone_number,password}, extra forbid; tên không rỗng/tối đa 255, password ít nhất 8 ký tự/tối đa 72 byte UTF-8. Client không gửi role/tenant_id/operator_id.
- ProvisionOut {id,tenant_id,owner_user_id,branch_name,owner_name,phone_number,created_at}; không trả password/hash/request_digest.
- POST tạo tenant, User ADMIN, LoginAccount, BranchMembership is_owner=true, OwnerProvision và audit OWNER_PROVISIONED atomically. Tenant ID sinh tại server. Advisory lock serialize khởi tạo và retry; cùng request_id/nội dung trả bản cũ, khác nội dung 409 (HMAC digest chứa request nhưng không lưu plaintext password). Trùng danh tính SĐT 409/rollback, không gộp.
- ENVIRONMENT=production: `/auth/register-tenant` bị chặn. Từ 0012, operator được tạo nhiều spa/chủ độc lập trong cùng deployment; mỗi lần tạo có spa riêng, không tự nhận tenant legacy. Chủ chỉ thêm nhánh trong spa và hạn mức của mình.
- Operator API yêu cầu token riêng; ADMIN/STAFF/CUSTOMER token trả 401. Operator token bị từ chối tại API nghiệp vụ (không có tenant_id và sai audience). Operator không tự có quyền đọc hồ sơ khách/thẻ/lịch.
- UI /operator/login và /operator dùng sessionStorage key spaos_operator_token, không ghi đè token Admin/Customer. Pending create giữ UUID/payload trong memory, khóa sửa form khi chưa rõ kết quả; retry gửi lại cùng body. Mật khẩu xóa khỏi form sau thành công.
- OPERATOR_PHONE/NAME/PASSWORD chỉ dùng bootstrap seed cấu hình; không đưa password vào URL, log hoặc response. Seed không đổi credential/active state đã tồn tại. Demo và chủ spa không được seed mặc định.
- Nhánh xác thực booking đã đồng bộ kiểm tra tenant active và membership/account của management user, tránh giữ quyền qua đường optional tenant context sau khi bị khóa.


## Màu thương hiệu cấp deployment — 0007_branding
- GET /branding (public, Cache-Control: no-store) → {theme_color:"#rrggbb",configured:boolean}. Chỉ công khai màu; không trả operator, khách hàng hoặc tài chính. Chưa cấu hình trả #be185d/configured=false.
- GET /operator/branding → cùng DTO; POST /operator/branding body {theme_color:"#rrggbb"} → 200 cùng DTO. Yêu cầu JWT Operator hợp lệ; thiếu/sai loại token 401. Chỉ nhận HEX đủ 6 ký tự, chuẩn hóa chữ thường; trường lạ/mã màu sai 422. Lưu bằng transaction và advisory lock; không nhận tenant_id từ client.
- POST /operator/owners thêm theme_color?:string|null. Có màu thì lưu cùng transaction tạo chủ/chi nhánh, xung đột rollback cả hai. Retry giữ cùng UUID/payload; màu tham gia digest khi được gửi, request cũ bỏ màu vẫn tương thích.
- deployment_branding là cấu hình giao diện singleton cấp deployment, không phải dữ liệu nghiệp vụ theo tenant. ENABLE/FORCE RLS: public chỉ đọc cấu hình màu, ghi yêu cầu operator active đã xác minh. Không nới policy bảng nghiệp vụ.
- Một chủ spa/deployment: màu chung mọi chi nhánh. GET /public/tenants/{slug} trả màu deployment nếu đã cấu hình; nếu chưa thì giữ màu chi nhánh cũ. Admin không sửa màu chung qua cài đặt chi nhánh; trường màu cũ chỉ còn phục vụ tương thích trước khi Operator cấu hình.
- Frontend áp dụng CSS variables cho đăng nhập/Admin/khách; nền giữ màu đã chọn, chữ nút tự chọn đen/trắng và chữ nhấn được làm đậm để dễ đọc. Metadata và manifest lấy màu từ backend nội bộ khi render; tab đang mở đồng bộ khi focus/storage event. Lỗi mạng giữ màu đã biết/default.


### Dung sai đồng hồ JWT
Token nghiệp vụ và Operator dùng leeway cố định 2 giây cho kiểm tra thời gian (iat/nbf/exp), nhằm chịu được hiệu chỉnh đồng hồ nhỏ. Vẫn xác minh chữ ký, audience, scope, version và quyền dữ liệu; token phát trước thời gian quá 2 giây hoặc hết hạn ngoài khoảng này bị từ chối. Không thay đổi thời lượng phiên.


### 21/10/2026 — Thông báo tạo lịch và lịch được giao

- `BookingOut` bổ sung `can_manage: boolean`: ADMIN và người phụ trách hồ sơ có thể quản lý theo quyền hiện hành; STAFF chỉ được giao thực hiện lịch của khách khác nhận `false`. Đây là thông tin giao diện, backend vẫn kiểm tra quyền trên từng mutation.
- STAFF đọc `GET /bookings` và `GET /bookings/{id}` nếu đang phụ trách khách hoặc là `staff_id` hiện tại của lịch. Việc được giao thực hiện chỉ mở quyền đọc chính lịch đó (gồm thông tin lịch/dịch vụ/ghi chú lịch); không mở CRM, thẻ, hồ sơ sức khỏe, sửa/hủy/dời/đổi trạng thái hoặc quyền đối chiếu batch. Endpoint slots để sửa lịch vẫn theo quyền chủ hồ sơ.
- Thông báo STAFF (danh sách, đếm, đọc một/tất cả) cùng phạm vi đọc lịch. Mất cả phụ trách hồ sơ và giao thực hiện thì thông báo cũ bị ẩn; không có quyền chéo tenant.
- Không yêu cầu migration hoặc endpoint mới. VAPID chỉ bật Push ngoài ứng dụng; thiếu khóa vẫn lưu in-app. Runner QA đặt khóa rỗng mặc định, test Push dùng mock, không gửi bằng secrets deployment.


### 21/10/2026 — Luồng UX theo vai trò (migration 0009, đang kiểm chứng)

Các endpoint dưới đây thuộc /api/v1, giữ tenant/JWT/RLS hiện hành. Ngoại lệ quyền đọc lịch được giao không mở CRM, thẻ hoặc thu tiền. Quyết định PO: không thêm lễ tân/thu ngân; bàn giao riêng từng lịch; spa xác minh khách rồi cấp liên kết một lần.

- PublicTenantOut, TenantOut/TenantDetailOut và GET /branches/public bổ sung address (nullable, tối đa 500) và contact_phone (nullable, + tùy chọn, 9–15 chữ số). PATCH /tenants/me (ADMIN) nhận hai trường này; null xóa dữ liệu liên hệ.
- PATCH /tenants/me nhận logo_data base64 PNG (tối đa 256 KB giải mã, kích thước 2048×2048, kiểm tra chữ ký/chunk/CRC), lưu cùng giao dịch với metadata. Logo không gửi vào audit. POST /tenants/me/logo là lựa chọn upload độc lập, body {data: base64}; ADMIN. GET /public/tenants/{slug}/logo trả image/png, chỉ chi nhánh ACTIVE, nosniff. URL ảnh thuộc cùng ứng dụng; không có bucket công khai hay upload SVG.
- GET /tenants/me/setup (ADMIN): {services, staff, staff_with_hours, contact_ready, slug}. Đếm dữ liệu thật theo chi nhánh. Có ca tuần không đồng nghĩa mọi dịch vụ/ngày đều còn giờ; người dùng kiểm tra bằng available-slots.
- GET /customers/{id} (ADMIN/STAFF phụ trách hồ sơ): đọc đúng một khách đã kiểm tra quyền, hỗ trợ liên kết CRM → đặt lịch mà không cần tải hết CRM. STAFF chỉ được giao lịch không có quyền này.
- GET /payments/collections thêm customer_id UUID tùy chọn, kết hợp q/scope/limit/offset, vẫn chỉ ADMIN và đúng tenant.
- GET /customers/{id}/packages trả thêm reserved_sessions và available_sessions giống GET /customer-packages/me. remaining_sessions = tổng − đã dùng; available_sessions = max(0, tổng − đã dùng − đang giữ) nếu thẻ còn hiệu lực/ACTIVE, ngược lại 0. Giữ buổi theo PENDING/CONFIRMED/IN_PROGRESS, không trừ used_sessions trước COMPLETED.
- GET /customer-packages/{id}/history?limit=30&offset=0: các {booking_id, start_time, status} thực sự dùng thẻ, mới nhất trước; limit 1–100. CUSTOMER chỉ thẻ của mình; ADMIN hoặc STAFF phụ trách hồ sơ; không mở cho KTV chỉ được giao lịch.
- PATCH /account/profile (CUSTOMER): chỉ {full_name}, trim, bắt buộc không rỗng. Cấm trường khác; không đổi SĐT/role/tenant qua hồ sơ.
- PATCH /account/credentials: {current_password, password, phone_number?}; mật khẩu mới 8 ký tự tối thiểu và 72 byte tối đa. Xác minh mật khẩu hiện tại, trả TokenResponse mới. Với quản trị chung, cập nhật nguyên tử login_accounts và users tại mọi membership; giữ từng tenant context, auth_version tăng và JWT cũ bị từ chối trên mọi chi nhánh. Khách tự đổi mật khẩu; đổi SĐT khách bị từ chối để xác minh riêng. Không tự gộp danh tính theo SĐT; trùng số trả 409 và rollback.
- PATCH /staff/{id}/account (ADMIN): cùng body nhưng current_password là mật khẩu của người thực hiện. Chỉ được sửa tài khoản nhân viên nếu actor là chủ của TẤT CẢ chi nhánh tài khoản đó; không sửa owner qua endpoint này. Cập nhật nguyên tử và thu hồi phiên cũ; trả {updated:true}. Sửa thông tin hồ sơ/ca riêng chi nhánh vẫn qua endpoint cũ.
- POST /customers/{id}/recovery-link (ADMIN): {current_password, identity_verified:true}. Spa phải xác minh khách ngoài ứng dụng trước khi tích xác nhận. Trả {token, expires_at} một lần, hạn 30 phút; cấp mới thu hồi liên kết trước. DB chỉ lưu SHA256 token; audit chỉ lưu việc cấp, không lưu token/mật khẩu. Chỉ khách active trong chi nhánh.
- POST /auth/recovery (public, X-Tenant-Slug): {token,password}. Đúng chi nhánh, đúng khách active, chưa dùng/chưa hết hạn mới được đặt mật khẩu và tăng auth_version. Đồng thời hai request chỉ một request thành công. Không tự đăng nhập, không tạo khách hoặc gộp hồ sơ. Sau thành công frontend chuyển sang /{slug}/login?password_set=1; cờ này chỉ hiển thị hướng dẫn, không cấp quyền đăng nhập. Frontend giữ token trong fragment, bỏ khỏi URL ngay khi đọc; không lưu token trong localStorage/sessionStorage.
- GET /staff/me/work-hours (STAFF): {week:[day_of_week,start_time,end_time,is_day_off],overrides:[day,start_time,end_time,is_day_off]}, tối đa 100 ngoại lệ từ hôm nay. Chỉ đọc ca chính mình; ADMIN quản lý qua API hiện hành.
- GET /staff/{id}/date-overrides (ADMIN): ngoại lệ hôm nay/tương lai, tối đa 100. PUT cùng path nhận {day,start_time?,end_time?,is_day_off}; DELETE /staff/{id}/date-overrides/{day} trở về ca tuần. Ngoại lệ thay ca của riêng ngày đó, giao với giờ mở cửa. Dùng cùng khóa staff row với booking engine. Nếu lịch PENDING/CONFIRMED/IN_PROGRESS không vừa ca sau thay đổi, trả 409 kèm số lịch ảnh hưởng và rollback; người dùng phải chủ động dời/hủy lịch trước. Không tự hủy lịch, không thay cả tuần.
- GET /bookings/{id}/handover (ADMIN/STAFF trong phạm vi đọc lịch): {note,updated_at}; KTV chỉ được giao lịch đọc được. PUT cùng path chỉ ADMIN/người phụ trách hồ sơ, {note} tối đa 1000 ký tự; lưu riêng booking_handovers, không tự sao chép hồ sơ sức khỏe, không đưa vào BookingOut/customer API/Push. Mất phạm vi đọc lịch thì mất quyền đọc note.
- POST /booking-requests (CUSTOMER): BookingCreate + request_id UUID, trả BookingOut/201. Khóa theo tenant/actor/request, lưu booking + biên nhận + sự kiện thông báo cùng transaction. Cùng ID/cùng payload trả lại lịch cũ; khác payload trả 409; rollback không có biên nhận. GET /booking-requests/{request_id} chỉ đúng actor/tenant; chờ khóa request đang chạy, trả lịch đã lưu hoặc 404. GET không tạo lịch/thông báo. Frontend chỉ lưu UUID theo slug/user; payload retry giữ trong bộ nhớ; reload kiểm tra kết quả trước cho đặt tiếp.

JWT nghiệp vụ bổ sung ver; token cũ thiếu ver được hiểu là 0 để giữ phiên trước migration. Mỗi lần đổi mật khẩu/khôi phục tăng users.auth_version, xác minh cả get_current_user và optional booking auth. JWT Operator không đổi.

Thông báo: booking mutation ghi notification_events cùng transaction; worker trong lifespan (không chạy tự động ở ENVIRONMENT=test) xử lý mỗi tenant bằng context riêng, mỗi vòng 5 giây, tối đa 30 event/job. Event và notification_dispatches lưu DB; lỗi tạm thời retry với backoff tối đa 1 giờ; worker khác dùng SKIP LOCKED. In-app dedupe theo event/user, CREATED giữ chống lặp lịch/user hiện hành. Push kiểm tra lại user active + phạm vi lịch dưới customer advisory lock trước gửi, xóa subscription hết hạn 404/410. Payload chứa notification_id và URL tới booking_id; không chứa bàn giao/hồ sơ sức khỏe. Provider Push có cơ chế giao ít nhất một lần khi mất xác nhận mạng; không cam kết đúng một lần trên thiết bị. Thẻ thông báo trình duyệt theo booking giúp gộp thông báo đang hiện. Nhấn Push mở cửa sổ riêng để giữ form đang nhập.

Runner backend và server QA E2E xóa VAPID khỏi môi trường test; kiểm thử Push dùng mock. Môi trường thật cần HTTPS, quyền trình duyệt và kiểm chứng thiết bị. Schema 0009 chỉ thêm cột/bảng; không seed/reset credentials hay chuyển tenant ID.

### Startup readiness — 0.2.1
API không nhận thêm endpoint trong hotfix này. Lifespan kiểm tra revision DB runtime khớp migration head và các cột address/contact_phone trước khi mở API/notification worker. Schema cũ hoặc stamp sai thiếu cột làm startup thất bại, do đó /health không trả 200 cho bản chưa sẵn sàng. Entry native Render/Docker: python -m scripts.start_service, chạy migration bằng MIGRATION_DATABASE_URL trước API; advisory lock serialize migration theo database. Hướng dẫn ở RENDER_DEPLOYMENT.md.


## Hồ sơ nhân viên, ảnh và kỹ năng — 23/10/2026
- `GET /staff` (ADMIN) và `POST/PATCH /staff` trả `StaffDetail` = UserDetail + `job_title`, `bio`, `experience_years` (0-60), `experience_detail`, `photo_url`, `skill_service_ids: [UUID]`. `PATCH /staff/{id}` nhận thêm `job_title` (<=100), `bio` (<=2000), `experience_years`, `experience_detail` (<=4000); các trường này được đặt `null`.
- `PUT /staff/{id}/skills` (ADMIN) `{service_ids:[UUID]}` thay toàn bộ kỹ năng; trả `StaffDetail`. `422` nếu có dịch vụ không thuộc chi nhánh; `404` nếu KTV thuộc chi nhánh khác. Bảng `staff_services` có `tenant_id` và FORCE RLS.
- `POST /staff/{id}/photo` (ADMIN) `{data: base64}` PNG hoặc JPEG, tối đa 256 KB và 2048x2048, kiểm tra cấu trúc file (`422` nếu sai). `DELETE /staff/{id}/photo` xóa ảnh. Cả hai trả `StaffDetail`.
- `GET /public/tenants/{slug}/staff/{staff_id}/photo` (công khai, chỉ trả ảnh của chi nhánh ACTIVE theo slug, RLS theo tenant); `photo_url` đã kèm `?v=` để làm mới cache. Ảnh nằm ở `staff_photos` (FORCE RLS).
- Lọc theo kỹ năng: `GET /bookings/available-slots`, `GET /bookings/{id}/available-slots`, tự xếp KTV trong `POST /bookings`, `POST /bookings/manual-batches` và dời lịch chỉ xét KTV có kỹ năng cho TẤT CẢ dịch vụ của lịch. KTV chưa khai báo kỹ năng nào vẫn được xét (tương thích dữ liệu cũ). Chỉ định trực tiếp `staff_id` không bị chặn ở backend; giao diện Admin chỉ gợi ý KTV phù hợp.

- Giới hạn ảnh logo (`POST /tenants/me/logo`, `PATCH /tenants/me` `logo_data`) và ảnh nhân viên (`POST /staff/{id}/photo`): nâng trần kích thước lên tối đa 2 MB (2.097.152 bytes) và 3.000.000 ký tự base64. Client tích hợp công cụ cắt chỉnh canvas kéo thả (`ImageCropper`) để tự căn chỉnh và tối ưu dung lượng trước khi gửi.

## Shared SaaS 0012 — 28/10/2026

Phần này thay thế giả định một chủ/deployment và phân công độc lập theo staff_id chi nhánh trong các mục lịch sử. Production cutover xem SHARED_SAAS_MIGRATION_RUNBOOK; schema có thể đã nâng nhưng tenant chưa mapping vẫn bị chặn 409. Spa/chi nhánh inactive bị chặn. Không tin spa_id/tenant_id tự gửi để chọn context ghi.

### Auth và điều hướng

- `POST /auth/login`, body `{phone_number,password}`, không header nhánh → TokenResponse thêm `spa_slug`. Một SĐT vận hành duy nhất, một spa/account. STAFF ưu tiên nhánh phân công hôm nay theo Asia/Ho_Chi_Minh; nếu không có ca lấy default hợp lệ/nhánh còn quyền. Owner ưu tiên default được lưu khi switch. Sai credentials/không nhánh active 401. CUSTOMER tiếp tục dùng header X-Tenant-Slug và namespace khách của nhánh.
- `GET /auth/me` → `{user,tenant,spa}`; tenant thêm `spa_id`; spa = `{id,slug,name,theme_color,logo_url,cover_url,contact_phone}`. Không trả dữ liệu ảnh/base64 hoặc credential.
- `POST /auth/resolve`, Authorization token còn chữ ký/thời hạn, không body → TokenResponse kèm spa_slug cho nhánh còn quyền. Xác minh user/auth_version ở nhánh gốc và account/spa, rồi chọn lại từ membership active. Nguồn đã thu hồi không được dùng business API. Credential thay đổi/hết hạn/không còn quyền 401; không phải cơ chế refresh cho token hết hạn.
- `POST /branches/{id}/switch` kiểm tra quyền và lưu default của account, trả TokenResponse của nhánh đích. Không thay lịch làm hoặc khả năng nhận lịch. Không có quyền 404.
- Mutation chờ khóa workforce trước khi đọc user/membership/version, tránh dùng quyền cũ sau thao tác thu hồi. Client đổi context phải bỏ response cũ, không replay mutation.

### Spa, nhận diện và gói

- `GET /spas/public/{slug}` public/no-store → public spa DTO ở trên và `branches:[{id,slug,name,address,contact_phone}]`, chỉ ACTIVE. Sai slug 404. Không trả hạn mức/quyền/người dùng/tài chính.
- `GET /branches/public?spa_slug={slug}` → `{brand_name,branches:[{id,name,slug,address,contact_phone}]}` chỉ trong spa đó. Thiếu spa_slug trả `{brand_name:<platform>,branches:[]}`; không dùng để liệt kê mọi chủ.
- `GET /spas/public/{slug}/logo` hoặc `/cover` → PNG/JPEG, nosniff/no-cache; chưa có ảnh 404. Chỉ tải cột ảnh khi phục vụ endpoint ảnh, không eager-load BLOB trong auth/booking.
- `GET /spas/me` management → public spa DTO + `is_owner`; nếu owner ADMIN thêm `plan:{price_usd:10,branch_limit,staff_limit,branches,staff}`. Giá chỉ mô tả gói thử nghiệm, chưa tạo hóa đơn/thu phí SaaS.
- `PATCH /spas/me` chỉ owner ADMIN: `{name,theme_color,logo_data?,cover_data?,cover_url?,contact_phone?}`; name/color bắt buộc. PNG/JPEG base64 tối đa 3 triệu ký tự, ảnh tối đa 2 MB/2048×2048. cover_url chỉ cùng hệ thống; contact_phone chuẩn hóa. Bỏ field tùy chọn giữ giá trị cũ; null contact/cover_url xóa giá trị tương ứng; logo_data/cover_data null không thay ảnh. Trả public spa DTO, không đổi slug. Lỗi ảnh rollback toàn bộ; STAFF/non-owner 403, dữ liệu sai 422.
- `POST /operator/owners` thêm `spa_name?` (thiếu dùng tên nhánh đầu), `theme_color?`, `logo_data?`, `cover_data?`, `logo_url?`, `cover_url?` same-origin. Tạo Spa + chi nhánh + owner/account/membership/provision/audit trong một transaction. Nhiều chủ độc lập được phép trên production; vẫn giữ idempotency request_id/payload, duplicate identity 409. Màu không còn ghi deployment_branding. `GET /operator/owners/{id}` thêm `spa` public DTO cho bàn giao URL/QR đúng thương hiệu.
- `POST /branches` gán spa từ owner đã xác minh, khóa/đếm nhánh ACTIVE trước tạo, mặc định tối đa 2. `POST /staff` và kích hoạt/cấp quyền kiểm tra tối đa 10 account STAFF active duy nhất; owner không tính, một account nhiều nhánh chỉ tính một. Chạm hạn mức 409; dữ liệu cũ vượt gói không bị xóa hay tự khóa đọc.
- `/branding` và `/operator/branding` còn phục vụ giao diện nền tảng trung tính/tương thích, không là nguồn nhận diện mọi spa. Các route canonical lấy branding theo spa.

### Nhân viên và phân công

- `POST /staff` thêm `branch_ids?:UUID[]`: chi nhánh hiện tại luôn được cấp, thêm các nhánh owner được phép trong cùng spa. Tạo account/hồ sơ/membership toàn bộ nguyên tử; một nhánh sai rollback cả yêu cầu. Mặc định chưa phân công không có slot, chủ cần lưu lịch tuần/ngày.
- `GET /workforce/staff/{staff_id}` owner ADMIN hoặc chính STAFF ở nhánh hiện tại → `{account_id,default_branch_id,branches:[{id,name,staff_id}],assignments:[{id,tenant_id,day,weekday,effective_from,start_time,end_time}]}`. Danh sách branch chỉ còn user/membership/tenant active. Không có danh tính/membership hợp lệ 409; sai quyền 403.
- `PUT /workforce/staff/{staff_id}/week`, owner: `{effective_from:"YYYY-MM-DD",days:[{weekday:0..6,tenant_id:UUID|null,start_time?:"HH:MM",end_time?:"HH:MM"}]}`. Cần đúng bảy thứ khác nhau; ngày nghỉ tenant_id=null và không có giờ. Phiên bản ngày hiệu lực được thay nguyên tử, các phiên bản khác giữ nguyên.
- `PUT /workforce/staff/{staff_id}/day`, owner: `{day:"YYYY-MM-DD",tenant_id:UUID|null,start_time?,end_time?}`. Một ngoại lệ/account/ngày; không gửi weekday. Ngoại lệ ngày ưu tiên mẫu tuần hiệu lực gần nhất. Ngày/hiệu lực từ hôm nay, giờ local không có offset, cùng một ngày và start<end. Sai schema/chưa có quyền nhánh 422; lịch hẹn bị ảnh hưởng 409. Thành công `{updated:true}`.
- `DELETE /workforce/staff/{staff_id}/day/{YYYY-MM-DD}`, owner: không body → `{removed:true}`, trở về mẫu tuần. Không xóa quá khứ (422); xác minh lại toàn bộ booking liên quan trước commit, có lịch không khớp thì 409/rollback. Không tự dời/hủy booking.
- `PUT /workforce/staff/{staff_id}/access`, owner: `{branch_ids:[UUID],default_branch_id:UUID}`. Mảng không rỗng; default nằm trong mảng; mọi nhánh thuộc owner/spa. Cấp thêm hoặc khôi phục membership; loại nhánh chỉ sau xử lý lịch tương lai/đang thực hiện và khách đang phụ trách, nếu chưa xử lý 409/rollback toàn bộ. Đóng tham chiếu phân công tương lai đến nhánh bị thu hồi, không đổi ID hoặc chuyển CRM/booking/thẻ/bút toán lịch sử. Trả `{updated:true}`. JWT nguồn bị chặn ngay; có thể resolve đến nhánh còn quyền nếu credentials còn hợp lệ.
- `PATCH /staff/{id}` is_active=false cũng dùng cùng kiểm tra bàn giao, không phải đường bỏ qua. Kích hoạt lại chịu hạn mức và kiểm tra quan hệ spa.
- `PUT /staff/{id}/schedules` tương thích: chuyển đủ tuần sang engine phân công với ngày hiệu lực hôm nay; ngày thiếu thành nghỉ. `PUT/DELETE /staff/{id}/date-overrides` cũng xác minh qua engine mới. `GET /account/work-hours` legacy không phải nguồn phân công liên chi nhánh; UI mới dùng `/workforce/staff/{id}`.

### Booking, public staff và push

- `GET /public/tenants/{branch_slug}?day=YYYY-MM-DD` thêm spa_slug; có day chỉ trả staff có phân công làm tại nhánh/ngày đó. day sai 422. Bỏ day giữ danh bạ public tương thích; không dùng danh bạ này thay điều kiện nhận lịch.
- Slots, tạo lịch khách/quầy, booking request/batch, auto-assign và dời lịch đều dùng phân công account chung + membership/user active + giờ mở cửa + điều kiện kỹ năng hiện hành + busy/buffer. Một người không nhận ở hai nhánh cùng ngày; dropdown không thay điều này. Buffer tiếp tục được xét qua nửa đêm khi hôm sau làm nhánh khác.
- Sửa phân công kiểm tra booking tương lai không giới hạn 30 ngày; mutation và booking serialize theo spa rồi giữ row locking/quy tắc thẻ hiện có. Mất quyền trong lúc chờ phải bị chặn khi đọc lại identity.
- Push thêm tên/logo spa và URL `/s/{spa}/admin/bookings?booking_id=...&target_branch=...` hoặc `/s/{spa}/b/{branch}/appointments?...`. Không mở dữ liệu ngoài quyền hiện tại khi click.
- Frontend manifest `/s/{spa}/manifest.webmanifest`: id ổn định `/pwa/spa/{uuid}`, name/icon của spa, scope `/s/{spa}/`, start_url `/s/{spa}/?launch=1` để mở lại theo phiên/vai trò quản lý đã xác minh hoặc vào public nếu anonymous/khách. Worker `/s/{spa}/sw.js` đúng scope và không cache API/HTML nghiệp vụ. Cổng operator giữ riêng.


### Quản lý trạng thái chi nhánh trong spa (28/10/2026)

- `GET /api/v1/branches/manage`: chỉ owner ADMIN; trả cùng BranchOut như `/branches` nhưng gồm cả nhánh tạm ngưng thuộc chính spa/tài khoản chủ. Danh sách `/branches` cho dropdown và public directory vẫn chỉ có nhánh ACTIVE.
- `PATCH /api/v1/branches/{branch_id}/status`, body `{"status":"ACTIVE"}` hoặc `{"status":"INACTIVE"}`; chỉ owner của nhánh đích trong spa hiện tại, không nhận scope từ body. Idempotent khi đã cùng trạng thái. Mở lại kiểm tra quota nhánh ACTIVE dưới cùng khóa workforce/spa với tạo mới.
- Tạm ngưng nhánh đang mở trả 409; chủ phải chuyển sang một nhánh ACTIVE khác trước. Còn lịch PENDING/CONFIRMED tương lai, bất kỳ IN_PROGRESS hoặc khách có assigned_staff_id thì 409, rollback đầy đủ. Chủ xử lý lịch và bàn giao khách về chủ (`assigned_staff_id:null`) trước; không tự chuyển CRM/thẻ giữa nhánh.
- Tạm ngưng hợp lệ kết thúc các ca tương lai trỏ nhánh đó, giữ mẫu/ngoại lệ lịch sử và ca ở nhánh còn lại. Giữ user/membership và mọi ID nghiệp vụ; tenant INACTIVE bị chặn nghiệp vụ ngay. Phiên quản lý có thể `/auth/resolve` sang nơi còn quyền. Mở lại cần phân công ca mới trước nhận khách.
- Endpoint và booking dùng cùng khóa để không nhận lịch sau khi nhánh đã tạm ngưng; thay đổi ghi audit nguyên tử. Không có thao tác xóa chi nhánh.


Quy tắc một nơi/ngày cũng giữ sau khi một booking đã COMPLETED hoặc NO_SHOW: sửa phân công từ ngày đó không được chuyển sang chi nhánh khác hoặc làm booking cũ nằm ngoài ca. Chỉ booking CANCELLED được loại khỏi kiểm tra phân công; lịch sử trước ngày hiệu lực không bị sửa. Không dùng hoàn thành buổi để chuyển người sang nơi khác trong cùng ngày.


### Đích thông báo quản lý theo chi nhánh

Deep link quản lý có dạng `/s/{spa}/admin/bookings?booking_id={uuid}&target_branch={uuid}`. Nếu phiên đang ở nhánh khác, shell không mount nội dung booking trước khi xác minh target thuộc danh sách quyền; người dùng chọn “Mở lịch tại …” để chuyển bằng API hiện hành. Không còn quyền thì thông báo rõ và không tải chi tiết bằng phiên nhánh khác. Chuyển nhánh giữ booking_id/target_branch đã kiểm tra UUID, tiếp tục dùng guard form/pending nhiều tab; không phát lại mutation.

Khi chưa đăng nhập hoặc hết phiên, chỉ hai UUID của đích hợp lệ được lưu trong sessionStorage theo spa, tối đa 30 phút, dùng một lần sau đăng nhập đúng spa. Không lưu token/khách vào intent này, không nhận URL tùy ý làm return target. Backend vẫn kiểm tra quyền/tenant/booking ở lần tải thật. In-app notification hiện thuộc nhánh đang xem; push có target_branch để xử lý sau khi người dùng đã đổi nhánh.
