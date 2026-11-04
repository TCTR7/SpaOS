# Kế hoạch Triển khai Cải thiện Trải nghiệm Đặt lịch, Quản lý & Thu gọn Sidebar (03/11/2026)

Tài liệu này mô tả chi tiết kế hoạch kỹ thuật cho **8 hạng mục cải thiện UX/nghiệp vụ** và **hạng mục số 9 (Gộp gọn Sidebar)** đã thống nhất với PO ngày 03/11/2026. Mọi thay đổi tuân thủ nghiêm ngặt kiến trúc Multi-tenant (`tenant_id`) và PostgreSQL `FORCE RLS` hiện hành.

---

## Tổng quan 9 Hạng mục Triển khai (Đã hoàn thành 04/11/2026)

- [x] 1. **Vị trí ảnh bìa trang Khách (`/[tenant_slug]`):** Đưa ảnh bìa xuống dưới khối Hero thông tin Spa.
- [x] 2. **Ẩn Thẻ liệu trình & Thu gọn khung giờ trống:** Loại bỏ giao diện/thao tác Thẻ liệu trình ở cả phía Khách và Quản lý (giữ nguyên bảng DB); thu gọn danh sách khung giờ trống; thêm ghi chú đặt buổi đầu tiên cho liệu trình nhiều buổi.
- [x] 3. **Màn hình sau khi khách gửi yêu cầu đặt lịch (`/[tenant_slug]/request`):** Bỏ 2 nút *"Cập nhật trạng thái"* và *"Sao chép liên kết riêng"*, chỉ giữ thông báo xác nhận rõ ràng và nút về trang chủ.
- [x] 4. **Đơn giản hóa luồng "Xem giờ trống" (`/[tenant_slug]/book`):** Bố cục chọn Ngày – Giờ – KTV gọn gàng; bỏ form bắt Đăng nhập/Đăng ký chắn ngang ở bước xác nhận (chỉ cần nhập Họ tên + SĐT và tự nhớ cho lần sau qua `localStorage`).
- [x] 5. **Upload/Hiển thị Avatar Nhân viên & Điều hướng theo Role:** Thêm upload/cắt ảnh ngay trong modal Tạo/Sửa nhân viên và trang *Tài khoản của tôi*; hiển thị ảnh đại diện KTV khi khách chọn; điều hướng `STAFF` về `/admin/bookings` thay vì `/admin/dashboard`.
- [x] 6. **Đặt lại mật khẩu trực tiếp cho Khách hàng:** Bỏ mục tạo link khôi phục 30 phút (`RecoveryLink`); thêm ô đặt mật khẩu mới ngay trong popup *Sửa hồ sơ khách hàng*.
- [x] 7. **Làm rõ luồng "Đơn khách đặt chờ xác nhận" & Nút tạo lịch trong Khách hàng:** Mặc định mở sẵn danh sách đơn chờ xác nhận kèm chi tiết Dịch vụ/KTV/Giờ; thêm nút mở form Tạo lịch tại quầy đã điền sẵn (pre-fill) theo lựa chọn của khách; đổi tên nút trong hồ sơ khách thành *"+ Tạo buổi hẹn mới tại quầy"* và hiển thị rõ đơn chờ của khách.
- [x] 8. **Tự động cập nhật KTV phụ trách (`assigned_staff_id`) theo lịch hẹn mới nhất:** Khi lịch hẹn mới được tạo hoặc xác nhận có gắn KTV thực hiện (`staff_id`), tự động cập nhật `assigned_staff_id` của khách sang KTV đó.
- [x] 9. **Gộp gọn Sidebar cho Role `ADMIN` và `STAFF`:** Rút gọn Sidebar Admin từ 11 mục xuống 7 mục cốt lõi theo thứ tự vận hành và Sidebar Staff xuống 3 mục; đưa *Tài khoản của tôi* xuống thẻ hồ sơ cuối Sidebar và *Trợ giúp* lên icon góc phải Header.

---

## Chi tiết Kỹ thuật từng Hạng mục

### Hạng mục 1: Vị trí ảnh bìa trên trang Khách hàng
* **File cập nhật:** `frontend/src/app/[tenant_slug]/page.tsx`
* **Thay đổi:**
  * Di chuyển khối `<img src={branding.cover_url} ... />` xuống nằm **bên dưới** khối Hero Banner thông tin Spa (Logo, Tên Spa, Giờ mở cửa, nút *Đặt lịch hẹn ngay*).

---

### Hạng mục 2: Loại bỏ giao diện "Thẻ liệu trình" & Thu gọn khung giờ trống
* **Nguyên tắc an toàn dữ liệu:** Giữ nguyên các bảng và cột trong Database (`customer_packages`) để bảo toàn dữ liệu lịch sử/migration, chỉ ẩn hoàn toàn khỏi giao diện và luồng thao tác của Khách hàng & Nhân viên.
* **File cập nhật:**
  * `frontend/src/components/customer/customer-shell.tsx` & `frontend/src/app/[tenant_slug]/profile/page.tsx`: Đổi nhãn thanh điều hướng dưới đáy từ *"Thẻ & Hồ sơ"* $\rightarrow$ **"Tài khoản"**; ẩn danh sách thẻ liệu trình trong trang cá nhân của khách.
  * `frontend/src/app/[tenant_slug]/page.tsx` & `frontend/src/app/[tenant_slug]/book/page.tsx`:
    * Ẩn khối *"Thẻ liệu trình của bạn"* ở Bước 1.
    * Với dịch vụ có `total_sessions > 1`, hiển thị chú thích rõ ràng: *"Đặt lịch hẹn cho buổi đầu tiên"*.
    * Bọc danh sách **Khung giờ còn trống** vào khối `<details>` có thể đóng/mở (hiển thị rõ giờ đã chọn trên thanh tiêu đề để khách có thể thu gọn lại giống mục chọn KTV).
  * `frontend/src/app/(admin)/admin/customers/page.tsx`:
    * Đổi tiêu đề trang từ *"Khách hàng & Thẻ liệu trình"* $\rightarrow$ **"Khách hàng"**.
    * Ẩn nút *"Cấp thẻ liệu trình"*, modal cấp thẻ và danh sách thẻ liệu trình; tập trung hiển thị thông tin khách, ghi chú da/sức khỏe, người phụ trách và **Lịch sử các buổi hẹn**.
  * `frontend/src/app/(admin)/admin/bookings/page.tsx`:
    * Trong modal Tạo lịch hẹn tại quầy: ẩn phần chọn *"Dùng buổi từ thẻ liệu trình"*, giữ nguyên danh sách chọn Dịch vụ.

---

### Hạng mục 3: Đơn giản hóa màn hình "Yêu cầu đặt lịch của bạn"
* **File cập nhật:** `frontend/src/app/[tenant_slug]/request/page.tsx`
* **Thay đổi:**
  * Loại bỏ hoàn toàn 2 nút gây khó hiểu: *"Cập nhật trạng thái"* và *"Sao chép liên kết riêng"* (cùng link *"Mở liên kết riêng để lưu"*).
  * Hiển thị thông báo xác nhận thân thiện, rõ ràng:
    * Trạng thái: *"Đã gửi yêu cầu đặt lịch thành công — Chờ Spa liên hệ xác nhận"* (hoặc trạng thái đã xác nhận).
    * Thời gian hẹn & thông điệp hướng dẫn: *"Spa sẽ gọi điện hoặc nhắn tin qua số điện thoại của bạn để xác nhận lịch hẹn."*
    * Nút duy nhất: **"Quay về trang chủ"** (`/${slug}`).

---

### Hạng mục 4: Làm gọn luồng khi khách bấm "Xem giờ trống"
* **File cập nhật:**
  * `frontend/src/app/[tenant_slug]/book/page.tsx`
  * `frontend/src/components/customer/guest-booking.tsx`
* **Thay đổi:**
  * Khi khách bấm *"Xem giờ trống"* từ 1 dịch vụ ở trang chủ, vào thẳng màn hình chọn **Ngày hẹn $\rightarrow$ Khung giờ trống (thu gọn được) $\rightarrow$ Kỹ thuật viên (thu gọn được)** với bố cục phẳng, lược bỏ các chữ giải thích rườm rà.
  * Ở bước Xác nhận (khi khách chưa đăng nhập):
    * **Gỡ bỏ hoàn toàn** khối form *"Đăng nhập / Đăng ký nhanh tài khoản"* đang nằm chắn bên dưới.
    * Chỉ hiển thị duy nhất form nhập **Họ và tên** + **Số điện thoại** (tự động lưu/điền sẵn Tên + SĐT vào `localStorage` trên thiết bị của khách để lần sau đặt lịch không cần gõ lại) và nút bấm **"Xác nhận gửi đặt lịch"**.

---

### Hạng mục 5: Upload/Hiển thị Ảnh đại diện Nhân viên & Điều hướng theo Role
* **Backend API:**
  * Trong `GET /api/v1/public/tenants/{slug}` (`backend/app/api/v1/tenants.py` & `backend/app/schemas/admin.py`): bổ sung trường `photo_url` vào từng phần tử `staff: [{ id, full_name, photo_url }]` để giao diện khách hàng hiển thị được ảnh đại diện KTV.
  * Trong `POST /api/v1/staff/{staff_id}/photo` và `DELETE /api/v1/staff/{staff_id}/photo` (`backend/app/api/v1/staff.py`): cho phép cả `ADMIN` hoặc chính nhân viên đó (`user.role == UserRole.STAFF and user.id == staff_id`) tải lên / xóa ảnh đại diện của mình, giữ nguyên kiểm tra `tenant_id` và `FORCE RLS`.
* **Frontend:**
  * `frontend/src/app/(admin)/admin/staff/page.tsx`: Tích hợp bộ chọn và cắt ảnh (`ImageCropper` + `StaffAvatar`) ngay trong modal **Thêm / Cập nhật Kỹ thuật viên** (nếu tạo mới có chọn ảnh thì sau khi `createStaff` thành công sẽ tự động gọi `uploadStaffPhoto`).
  * `frontend/src/app/(admin)/admin/account/page.tsx`: Thêm mục **Ảnh đại diện của tôi** (dùng `StaffAvatar` + `ImageCropper`) để nhân viên khi đăng nhập vào *Tài khoản của tôi* có thể tự tải/đổi ảnh đại diện.
  * `frontend/src/app/[tenant_slug]/book/page.tsx`: Thay icon `<UserCheck />` cứng trong danh sách chọn KTV bằng `StaffAvatar` hiển thị `photo_url` của nhân viên.
  * **Điều hướng theo Role (`STAFF` vs `ADMIN`):**
    * Tại trang đăng nhập (`frontend/src/app/(admin)/admin/login/page.tsx`), trang gốc (`frontend/src/app/(admin)/admin/page.tsx`) và `frontend/src/app/(admin)/admin/dashboard/page.tsx`: Nếu `user.role === "STAFF"`, tự động điều hướng về **`/admin/bookings`** (Lịch hẹn làm việc) thay vì đứng ở `/admin/dashboard`.

---

### Hạng mục 6: Đặt lại mật khẩu trực tiếp cho Khách hàng trong Hồ sơ khách
* **Backend API:**
  * Trong `PATCH /api/v1/customers/{customer_id}` (`backend/app/api/v1/customers.py` & `backend/app/schemas/admin.py`): cho phép truyền thêm trường tùy chọn `password` (tối thiểu 6 ký tự). Khi `ADMIN` hoặc `STAFF` phụ trách gửi `password`, hệ thống băm mật khẩu mới, tăng `auth_version` của khách hàng đó và ghi `AuditLog` trong cùng transaction.
* **Frontend:**
  * `frontend/src/app/(admin)/admin/customers/page.tsx`:
    * **Gỡ bỏ hoàn toàn** component `<RecoveryLink />` (*"Giúp khách đăng nhập hoặc đặt lại mật khẩu"* bằng link 30 phút).
    * Trong modal **Cập nhật hồ sơ Khách hàng**, hiển thị ô **"Đặt mật khẩu mới (Để trống nếu không đổi)"** để Admin/Nhân viên đặt lại mật khẩu trực tiếp cho khách ngay tại quầy.

---

### Hạng mục 7: Làm rõ luồng "Đơn khách đặt chờ xác nhận" & Nút tạo lịch trong Khách hàng
* **File cập nhật:**
  * `frontend/src/components/admin/guest-inbox.tsx`
  * `frontend/src/app/(admin)/admin/bookings/page.tsx`
  * `frontend/src/app/(admin)/admin/customers/page.tsx`
* **Thay đổi:**
  * Trong `frontend/src/components/admin/guest-inbox.tsx` (đầu trang **Lịch hẹn**):
    * Mặc định **mở sẵn (`open`)** khi có yêu cầu của khách đang chờ (`rows.length > 0`).
    * Hiển thị ngay trên từng dòng yêu cầu: **Tên khách • SĐT • Giờ hẹn • Tên các dịch vụ khách đã chọn • Tên KTV khách đã chọn** (không phải bấm vào mới thấy).
    * Bổ sung nút **"Mở trong form Tạo lịch (điền sẵn)"** bên cạnh nút *"Xác nhận ngay"* để nếu lễ tân muốn đổi dịch vụ/giờ/KTV thì modal *Tạo lịch hẹn tại quầy* sẽ mở ra với **tất cả thông tin khách, dịch vụ, KTV và giờ đã được chọn sẵn (pre-fill)**.
  * Trong `frontend/src/app/(admin)/admin/customers/page.tsx`:
    * Đổi tên nút *"Đặt lịch cho khách"* $\rightarrow$ **"+ Tạo buổi hẹn mới tại quầy"**.
    * Nếu khách hàng đang chọn có **yêu cầu đặt lịch chờ xác nhận** (khớp SĐT trong `guest-requests`) hoặc có lịch hẹn sắp tới trong `CustomerVisits`, hiển thị thẻ thông báo nổi bật ngay đầu hồ sơ khách kèm nút xử lý/pre-fill đúng dịch vụ & KTV khách đã chọn.

---

### Hạng mục 8: Tự động cập nhật KTV phụ trách (`assigned_staff_id`) theo lịch hẹn mới nhất
* **Backend (`backend/app/services/booking_service.py` & `backend/app/api/v1/guest_requests.py`):**
  * Khi tạo lịch hẹn mới (`POST /api/v1/bookings`, `POST /api/v1/booking-requests`, `POST /api/v1/bookings/manual-batches`) hoặc khi xác nhận yêu cầu đặt lịch của khách (`POST /api/v1/guest-requests/{id}/decision` với `action="confirm"`):
    * Nếu buổi hẹn có KTV thực hiện (`booking.staff_id IS NOT NULL`), cập nhật `customer.assigned_staff_id = booking.staff_id` ngay trong cùng Database Transaction.
  * Nhờ đó, khi khách chọn KTV **Phạm Ngọc Ngân**, hồ sơ khách sẽ tự động chuyển về cho **Phạm Ngọc Ngân** phụ trách (Ngân đăng nhập vào sẽ thấy khách trong mục *Khách hàng*, còn KTV cũ không còn thấy khách đó nữa).

---

### Hạng mục 9: Gộp gọn Sidebar cho Role `ADMIN` và `STAFF`
* **File cập nhật:**
  * `frontend/src/components/admin/admin-shell.tsx`
  * `frontend/src/app/(admin)/admin/dashboard/page.tsx`
  * `frontend/src/app/(admin)/admin/settings/page.tsx`
  * `frontend/src/app/(admin)/admin/work-hours/page.tsx`
* **Cấu trúc Sidebar mới:**
  1. **Cho `ADMIN` (Rút gọn và sắp xếp đúng thứ tự vận hành):**
     * **Tổng quan & Báo cáo** (`/admin/dashboard` — tích hợp bộ chuyển tab *Tổng quan trong ngày* và *Báo cáo hiệu suất KTV*; đường dẫn `/admin/reports` vẫn hoạt động tương thích).
     * **Lịch hẹn** (`/admin/bookings`)
     * **Khách hàng** (`/admin/customers`)
     * **Thu tiền** (`/admin/payments`)
     * **Dịch vụ** (`/admin/services`)
     * **Nhân sự & Ca làm** (`/admin/staff`)
     * **Cài đặt & Chi nhánh** (`/admin/settings` — tích hợp 3 tab ngang trên đầu trang: *Cài đặt chi nhánh* | *Thương hiệu & Gói* | *Quản lý chi nhánh*; các đường dẫn `/admin/brand` và `/admin/branches` vẫn giữ tương thích).
  2. **Cho `STAFF` (Rút gọn còn 3 mục chính):**
     * **Lịch hẹn** (`/admin/bookings`)
     * **Khách hàng** (`/admin/customers`)
     * **Ca làm & Dịch vụ** (`/admin/work-hours` — có tab xem *Ca làm của tôi* và *Bảng giá Dịch vụ*).
  3. **Chân Sidebar & Header:**
     * Bấm vào khối **Avatar + Họ tên + SĐT** ở dưới cùng Sidebar sẽ dẫn tới trang **Tài khoản của tôi** (`/admin/account`).
     * Đưa nút **Trợ giúp** (`?`) lên góc phải Header cạnh chuông thông báo (không chiếm dòng trên Sidebar chính).

---

## Kiểm thử & Xác minh sau khi Code
1. **Backend Tests:** Chạy kiểm thử cô lập `python -m scripts.test_isolated` cho các luồng tạo lịch, xác nhận guest request, cập nhật `assigned_staff_id`, đặt mật khẩu khách hàng và upload avatar nhân viên.
2. **Frontend Build & Typecheck:** Chạy `cd frontend && npm run build` bảo đảm 100% TypeScript strict (không dùng `any`).
3. **Cập nhật Tài liệu:** Đồng bộ `docs/API_CONTRACT.md` và `docs/PROGRESS.md` theo đúng quy tắc trong `AGENTS.md`.
