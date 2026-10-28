# Thiết kế SaaS dùng chung — 0012

Phạm vi được PO duyệt 28/10/2026. Trạng thái kiểm chứng cuối xem PROGRESS và báo cáo bàn giao; tài liệu này mô tả mã nguồn, không xác nhận production đã chuyển đổi.

## Ranh giới dữ liệu

- `spas.id`: thương hiệu/chủ sở hữu, slug ổn định, nhận diện, trạng thái và hạn mức gói. Đổi tên không đổi slug, URL hoặc manifest ID.
- `tenants.id` tiếp tục là **chi nhánh**. `tenant_id`, khách, thẻ, dịch vụ, bút toán và booking cũ giữ nguyên; không gộp CRM/SĐT khách giữa chi nhánh.
- `login_accounts.spa_id`: một danh tính ADMIN/STAFF thuộc một spa. SĐT được chuẩn hóa trước uniqueness toàn nền tảng; +84/84 mobile đổi về 0, bỏ khoảng trắng/dấu phân cách. Xung đột cũ cần đối chiếu, không gộp theo hash hoặc tên.
- `branch_memberships`: một user nghiệp vụ tại từng chi nhánh của account. Trigger DB từ chối account/chi nhánh khác spa hoặc chưa mapping.
- `staff_assignments`: dữ liệu cấp account/spa. `tenant_id` có thể null cho ngày nghỉ; ngoại lệ kiến trúc này không dùng chi nhánh giả. FK kép bảo đảm account và nơi làm thuộc cùng spa.

## RLS và context

Runtime dùng role NOSUPERUSER/NOBYPASSRLS. Bảng nghiệp vụ giữ `FORCE RLS` theo chi nhánh, mọi query có điều kiện tenant. Spa và phân công có ENABLE/FORCE RLS riêng; thiếu context không đọc được. Context `set_config(..., true)` chỉ sống trong transaction, phải đặt lại sau commit/rollback.

- Context spa được đặt sau khi xác minh JWT/membership và quan hệ tenant→spa. Operator có JWT riêng, chỉ thấy các provision của mình; không nhận quyền CRM/tài chính.
- Public slug chỉ mở dữ liệu nhận diện spa tương ứng. Directory `/branches/public` thiếu spa_slug trả mảng rỗng, không công khai danh sách mọi chủ.
- Context account/phone chỉ phục vụ tra danh tính và membership; không mở dữ liệu nghiệp vụ. Tổng hợp và tóm tắt bận chéo chi nhánh lần lượt đặt context các nhánh thuộc spa/quyền đã xác minh.
- Các ảnh public đã được kiểm tra PNG/JPEG, kích thước tối đa 2048×2048 và 2 MB/ảnh; response nosniff. Logo và ảnh bìa hiện lưu DB, UI thu nhỏ trước gửi.

## Một người, một nơi trong ngày

Mốc ngày dùng `Asia/Ho_Chi_Minh`, booking vẫn TIMESTAMPTZ UTC. Thứ 0 là Chủ nhật, 1 là Thứ Hai.

1. Ngoại lệ đúng account/ngày có ưu tiên cao nhất, gồm cả nghỉ.
2. Nếu không có ngoại lệ, lấy phiên bản tuần có effective_from gần nhất nhưng không sau ngày đang xét.
3. Thiếu phân công hoặc mất membership/user/chi nhánh active: không nhận lịch. Giao giờ phân công với giờ mở cửa.

Unique account/day và account/effective_from/weekday cấm hai nơi trong cùng ngày. Mẫu tuần mới có đủ bảy thứ; phiên bản cũ giữ để xem lại. Mutation không cho hiệu lực trong quá khứ. API lịch cũ được chuyển qua cùng engine, không tạo đường bỏ qua kiểm tra.

Đổi ca kiểm tra toàn bộ booking tương lai/đang thực hiện có liên quan, không chỉ 30 ngày. Thu hồi quyền hoặc ngưng nhân viên yêu cầu xử lý booking và khách đang phụ trách trước. Không tự hủy/dời lịch, chuyển khách/thẻ/bút toán. Các tham chiếu phân công tương lai đến nơi bị thu hồi được đóng trong cùng transaction, lịch sử giữ nguyên.

## Thứ tự khóa

Chọn advisory transaction lock **theo spa** cho MVP quy mô nhỏ, thay cho nhiều khóa account cần sắp thứ tự khi batch/tuần liên quan nhiều người. Spa khác vẫn ghi song song.

Thứ tự: workforce spa → khóa yêu cầu idempotency nếu có → khóa khách → khóa thẻ theo ID → hàng nhân viên theo ID → booking. Booking tiếp tục SELECT FOR UPDATE; hoàn thành thẻ giữ idempotency và chặn vượt buổi. Hạn mức được đếm lại sau khóa hàng Spa; cấp cùng account ở hai nhánh chỉ tính một STAFF active, không tính owner.

Dependency mutation chờ khóa workforce **trước** khi đọc lại user/version/membership. Các service booking/batch cũng lấy khóa đầu vào. Vì vậy yêu cầu đang đợi sau thao tác thu hồi không dùng snapshot quyền cũ. Slots là gợi ý; mọi ghi lịch đều xác minh lại phân công, kỹ năng, quyền, giờ và buffer. Tóm tắt bận nhánh khác chỉ lấy ID/timestamps/buffer, không trả tên khách.

Response booking được chuyển sang DTO rồi kết thúc transaction đọc trước khi chạy background. Outbox và notification/dispatch dùng chung một session/transaction, savepoint bảo vệ retry lỗi; gửi push sau khi transaction này đã đóng. Không giữ một connection trong lúc đợi connection thứ hai, tránh cạn pool khi nhiều spa đặt đồng thời. Kiểm tra booking khi đổi ca tải phân công account một lần, không query riêng cho từng lịch hẹn.

## Auth, điều hướng và PWA

- Login chung xác thực account rồi trả `spa_slug`. STAFF ưu tiên nơi làm hôm nay; nếu nghỉ dùng default hợp lệ rồi nhánh còn quyền đầu tiên. Owner dùng default đã lưu khi switch. Dropdown chỉ thay context, không thay nơi nhận booking.
- JWT nghiệp vụ vẫn gắn branch/user/version. `/auth/resolve` chỉ nhận token còn chữ ký/thời hạn và version credential đúng; từ bản ghi user/membership cũ tìm danh tính rồi xác minh các nhánh còn quyền. Nhánh đã thu hồi không mở lại quyền nghiệp vụ. Đổi credentials tăng version ở mọi hồ sơ, kể cả membership không active, nên token cũ không resolve được.
- Admin storage theo spa; session version, guard bản nháp, bỏ response cũ và kiểm tra nhiều tab vẫn giữ. Focus/visibility và kiểm tra định kỳ 30 giây cập nhật quyền; lỗi 401 resolve sang nơi còn quyền, không tự replay mutation. Thay ngày làm không tự chuyển form đang mở sang nhánh khác; lần đăng nhập mới ưu tiên lịch hôm nay.
- `/s/{spa_slug}/` là lối vào spa; `/s/{spa_slug}/admin/...` quản lý; `/s/{spa_slug}/b/{branch_slug}/...` khách. Một nhánh public có thể vào thẳng nhánh đó. `/admin/login` trung tính để nhập SĐT/mật khẩu và tìm spa sau xác thực.
- Middleware lấy spa từ URL, xóa header spa do client tự gửi; rewrite tương đối ở next.config giữ context SSR/metadata. Backend luôn tự kiểm tra quyền, không tin header frontend này.
- Manifest ID `/pwa/spa/{uuid}`, scope `/s/{slug}/`, start_url `/s/{slug}/?launch=1`; khi mở từ PWA, phiên quản lý còn hợp lệ đi vào giao diện đúng vai trò, khách/anonymous vào chọn nhánh. Link chia sẻ bình thường vẫn mở phần public. Worker riêng scope spa và không cache API/HTML riêng tư. Payload push theo thương hiệu và deep link canonical; đích vẫn phải xác minh quyền khi mở.
- URL chi nhánh cũ tiếp tục hoạt động cho tương thích; login chung đi đến canonical. Cần đăng nhập/cài lại PWA khi đổi origin/scope; không hứa giữ installation hoặc push subscription cũ.

## Những phần không nằm trong bản này

Thu phí SaaS tự động, SMS trả phí, làm hai nơi cùng ngày, thẻ/CRM xuyên nhánh, account làm cho nhiều chủ, tự gộp dữ liệu và chuyển framework. Production migration, mua hosting và native Android/iOS là các gate vận hành riêng trong runbook.


## Vòng đời chi nhánh và ca hôm nay

Owner xem cả nhánh tạm ngưng qua `/branches/manage`, dropdown và directory chỉ trả ACTIVE. Đổi trạng thái dùng khóa workforce/spa chung với tạo/mở lại/booking. Không tạm ngưng nhánh đang mở; cần một nhánh hoạt động khác. Lịch còn chiếm chỗ và khách có người phụ trách chặn thao tác; trả về chủ để đóng trách nhiệm trước, không chuyển dữ liệu xuyên nhánh. Tạm ngưng chỉ kết thúc phân công tương lai tại nơi đó; lịch sử và dữ liệu nghiệp vụ giữ nguyên. Kích hoạt lại kiểm tra quota và yêu cầu thiết lập ca mới.

Staff có thông tin nơi/giờ làm hôm nay hoặc nghỉ/chưa phân công. App đọc lại trên focus/visibility và mỗi 30 giây khi đang hiển thị, tính ngày Asia/Ho_Chi_Minh. Qua ngày mới chỉ cập nhật thông tin, không điều hướng giữa form. Phân công do backend quyết định nhận lịch; trạng thái UI không tạo quyền.


Quy tắc một nơi/ngày cũng giữ sau khi một booking đã COMPLETED hoặc NO_SHOW: sửa phân công từ ngày đó không được chuyển sang chi nhánh khác hoặc làm booking cũ nằm ngoài ca. Chỉ booking CANCELLED được loại khỏi kiểm tra phân công; lịch sử trước ngày hiệu lực không bị sửa. Không dùng hoàn thành buổi để chuyển người sang nơi khác trong cùng ngày.


## Deep link khác chi nhánh và phiên hết hạn

Payload push đã mang target_branch. Shell chặn mount trang booking nếu nhánh đích khác nhánh JWT, xác minh đích trong branches đã cấp rồi cho chuyển chủ động; không có quyền thì dừng tại thông báo. Chuyển thành công giữ hai UUID đích, không dùng URL tùy ý, không phát lại thao tác. Khi không có phiên hoặc JWT hết hạn, intent gồm booking_id/target_branch nằm sessionStorage theo spa trong 30 phút và dùng một lần sau đăng nhập; backend tiếp tục xác minh dữ liệu thực sự. Luồng này được kiểm tra bằng booking/branch thật trong E2E, tách khỏi gate giao nhận push trên thiết bị thật.
