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

Danh tính deployment_operators tách biệt UserRole và login_accounts nghiệp vụ. Mỗi deployment tối đa một operator (singleton database constraint); không có tenant_id vì là danh tính hạ tầng, có ENABLE/FORCE RLS theo operator_id hoặc phone bootstrap. owner_provisions có tenant_id, FK tenant/owner, operator_id, chống trùng request_id theo operator và append-only. Không nới RLS nghiệp vụ.

- POST /operator/login: {phone_number,password}, extra forbid. 200 {access_token,token_type:"bearer",expires_in:1800,operator:{id,full_name,phone_number}}. JWT aud=spaos-operator, scope=operator, version; sai thông tin 401, khóa sau 5 lần sai và trong 5 phút trả 429. Không có tài khoản mặc định.
- GET /operator/me → OperatorOut, operator JWT hợp lệ/active/version còn hiệu lực.
- POST /operator/logout → {logged_out:true}, tăng token_version nguyên tử, thu hồi mọi phiên operator cũ.
- GET /operator/owners?limit=50&offset=0 → [ProvisionOut], limit 1–200; chỉ lịch sử operator đã xác minh, mới nhất trước.
- POST /operator/owners → 201 ProvisionOut. Body {request_id:UUID,branch_name,owner_full_name,phone_number,password}, extra forbid; tên không rỗng/tối đa 255, password ít nhất 8 ký tự/tối đa 72 byte UTF-8. Client không gửi role/tenant_id/operator_id.
- ProvisionOut {id,tenant_id,owner_user_id,branch_name,owner_name,phone_number,created_at}; không trả password/hash/request_digest.
- POST tạo tenant, User ADMIN, LoginAccount, BranchMembership is_owner=true, OwnerProvision và audit OWNER_PROVISIONED atomically. Tenant ID sinh tại server. Advisory lock serialize khởi tạo và retry; cùng request_id/nội dung trả bản cũ, khác nội dung 409 (HMAC digest chứa request nhưng không lưu plaintext password). Trùng danh tính SĐT 409/rollback, không gộp.
- ENVIRONMENT=production: nếu database đã có tenant, tạo chủ độc lập mới bị từ chối 409; chủ hiện tại vẫn tạo thêm chi nhánh. /auth/register-tenant luôn bị chặn trên production, không còn mở bằng ALLOW_TENANT_REGISTRATION.
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
