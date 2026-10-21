# Dữ liệu trải nghiệm trên ứng dụng local

Bộ dữ liệu này được tạo theo chỉ thị PO ngày 21/10/2026 trên ứng dụng đang chạy, được giữ lại trong database để kiểm tra thủ công. Đây là các hồ sơ hư cấu, không phải thông tin khách hàng thật. Bộ test QA hiện có vẫn chạy cô lập và không được đổi guard để trỏ vào database ứng dụng.

## Tài khoản và đường dẫn

- File thông tin đăng nhập: [local-data/spaos-review-accounts.json](../local-data/spaos-review-accounts.json).
- Chủ spa và nhân viên: http://localhost:3000/admin/login.
- Khách hàng: dùng customer_login_url trong từng chi nhánh của JSON.
- JSON có một chủ spa dùng chung ba chi nhánh; mỗi chi nhánh có 10 nhân viên, 10 khách hàng, ba dịch vụ, 10 thẻ liệu trình và 10 lịch hẹn. Tổng 61 tài khoản đăng nhập, 30 nhân viên, 30 khách, chín dịch vụ, 30 thẻ và 30 lịch.
- Mật khẩu được sinh ngẫu nhiên riêng từng tài khoản. File không chứa thông tin đăng nhập operator, JWT hoặc khóa VAPID. Thư mục local-data được Git bỏ qua; không đưa file mật khẩu lên kho mã nguồn.

## Cách kiểm tra

1. Đăng nhập chủ spa, chọn chi nhánh trên dropdown; xem Tổng quan và Tất cả chi nhánh.
2. Vào Nhân viên, Khách hàng, Dịch vụ và Thẻ để kiểm tra dữ liệu của từng chi nhánh.
3. Lịch hẹn: hai lịch hoàn thành vào ngày trước thời điểm tạo; các lịch còn lại nằm trong 1–3 ngày tiếp theo. Ngày/giờ cụ thể có trong bookings[].start_time của JSON. Mỗi chi nhánh có hai COMPLETED, hai CONFIRMED, năm PENDING và một CANCELLED.
4. Thẻ của khách thứ hai đã dùng một buổi sau khi hoàn thành lịch. Các thẻ còn lại chưa dùng.
5. Đăng nhập nhân viên: chỉ thấy chi nhánh được cấp và khách/lịch trong phạm vi. Đăng nhập khách: xem lịch, thẻ và thông báo lịch được tạo tại quầy.
6. Chưa bật thông báo thiết bị hoặc kiểm chứng Web Push thật trong automation; thông báo trong ứng dụng đã được kiểm tra. Không ghi nhận thu tiền hay thực hiện chuyển khoản.

## Automation riêng cho dữ liệu được giữ lại

Tại root, lần đầu:

~~~powershell
& automation_test/.venv/Scripts/python.exe -B automation_test/scripts/create_live_review_data.py --apply --frontend-url http://localhost:3000 --api-url http://localhost:8001/api/v1 --staff-per-branch 10
~~~

Kiểm tra lại dữ liệu đã tạo, không tạo/sửa hồ sơ:

~~~powershell
& automation_test/.venv/Scripts/python.exe -B automation_test/scripts/create_live_review_data.py --verify-only --frontend-url http://localhost:3000 --api-url http://localhost:8001/api/v1 --staff-per-branch 10
~~~

Runner chỉ chấp nhận localhost/127.0.0.1. Tạo dữ liệu qua API xác thực bình thường; giữ tenant/RLS và giới hạn của operator. Không dùng seed_demo, không nới đăng ký tenant, không ghi trực tiếp database, không reset mật khẩu hay xóa dữ liệu hiện có. Các hồ sơ mới thuộc ba chi nhánh riêng của chủ mới; không gộp chủ/chi nhánh cũ.

JSON được ghi trước khi tạo tài khoản và cập nhật ID theo tiến độ. Lượt tạo dở có thể tiếp tục bằng cùng file; endpoint cấp chủ và batch giữ request_id. Khi provisioning đã hoàn tất, chạy lại chỉ xác minh. Nếu bạn thêm/sửa dữ liệu thủ công khiến số lượng/trạng thái khác kế hoạch, kiểm tra có thể báo không khớp; runner không xóa dữ liệu để ép test đạt. Mức 10 nhân viên là giới hạn của runner dữ liệu, không phải giới hạn mới áp lên sản phẩm.

Runner không tạo log, ảnh, trace hoặc video; kết quả ra console, trạng thái xác minh và thông tin tài khoản nằm trong JSON do PO yêu cầu. Kết quả và các giới hạn của lượt chạy xem PROGRESS.md.


## Các luồng UX bổ sung (21/10/2026)

Bản local đã áp migration 0009 sau backup/restore; giữ nguyên bộ tài khoản trong JSON. Không cần tạo lại dữ liệu hoặc đăng ký tài khoản khác.

- Chủ spa: vào Tổng quan để xem việc trong ngày, khoản cần thu và hướng dẫn thiết lập. Trong Cài đặt, bổ sung địa chỉ/số liên hệ hoặc chọn ảnh PNG; ảnh chỉ lưu khi nhấn Lưu.
- Nhân sự: chọn nhân viên để xem ca tuần, nghỉ/đổi giờ riêng một ngày hoặc đổi tài khoản đăng nhập. Nếu ca mới ảnh hưởng lịch đã nhận, app yêu cầu xử lý những lịch đó trước. Tài khoản chung áp dụng cho mọi chi nhánh đã cấp; đổi mật khẩu thu hồi phiên cũ.
- Hồ sơ khách: Đặt lịch cho khách và Xem khoản cần thu giữ đúng khách đang chọn; có lịch gần đây và lịch sử từng thẻ. Thẻ đã giữ hết buổi vẫn được hiển thị nhưng không chọn thêm được.
- Khách cần đăng nhập/khôi phục: chủ mở phần Giúp khách đăng nhập hoặc đặt lại mật khẩu, xác minh đúng khách ngoài app rồi nhập mật khẩu của chính chủ để cấp link. Gửi riêng link cho đúng khách; khách tự đặt mật khẩu, đăng nhập lại bằng SĐT cũ. Không ghi link/token vào báo cáo công khai. Link dùng một lần, hạn 30 phút; cấp mới hủy link cũ.
- Bàn giao: mở chi tiết lịch và ghi bàn giao riêng buổi đó. Nhân viên chỉ được giao thực hiện đọc được ghi chú này; không được sửa trạng thái hoặc xem hồ sơ sức khỏe ngoài quyền.
- Nhân viên: mở Ca làm của tôi để xem tuần và ngoại lệ ngày; liên hệ chủ khi cần điều chỉnh. Giữ nguyên quyền nhân viên, chưa có lễ tân/thu ngân.
- Khách: sửa họ tên/mật khẩu tại Thẻ & Hồ sơ, mở lịch sử từng thẻ; sau đặt lịch có thể tải tệp lịch cá nhân. Tệp tải xuống không tự đồng bộ khi dời/hủy. Nếu mất mạng sau xác nhận, dùng Kiểm tra lịch đã đặt trước khi gửi yêu cầu khác.

Tất cả thao tác thay đổi ở trên sẽ thay dữ liệu local nếu bạn chủ động xác nhận; automation hồi quy của đợt này dùng database QA riêng. Push qua HTTPS trên Android/iPhone và pilot người dùng thật vẫn cần nghiệm thu riêng.
