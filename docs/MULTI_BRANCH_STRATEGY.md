# Định hướng SpaOS: triển khai riêng từng chủ spa, hỗ trợ nhiều chi nhánh

- Ngày ghi nhận: 17/10/2026.
- Trạng thái: **ĐÃ TRIỂN KHAI BẢN ĐẦU VÀ KIỂM CHỨNG LOCAL (17/10/2026)**.
- Phạm vi được phép hiện tại: triển khai theo chỉ thị PO ngày 17/10/2026; xem mục Phê duyệt triển khai và PROGRESS.
- Tài liệu gồm định hướng ban đầu và quyết định triển khai; kết quả thực tế/kiểm thử nằm trong PROGRESS và API_CONTRACT.
- PO đã xem bản lưu và cho bắt đầu triển khai. Không suy từ đó rằng đã cho phép deploy production hoặc gộp dữ liệu các chủ khác nhau.

## 1. Bối cảnh và mục tiêu

Khách hàng mục tiêu là spa vừa và nhỏ, khoảng 10 nhân viên; một chủ spa có thể sở hữu nhiều chi nhánh. PO thấy ô tenant slug khó hiểu và muốn thao tác gần với cách vận hành thực tế:
- Đăng nhập bằng số điện thoại và mật khẩu.
- Sau đăng nhập, chuyển chi nhánh bằng dropdown tên chi nhánh.
- Dashboard cho từng chi nhánh và tổng tất cả chi nhánh của cùng chủ spa.
- Các chủ spa khác nhau được bán và triển khai trên hệ thống riêng; dùng cấu hình để cá nhân hóa từng hệ thống.

## 2. Hướng thiết kế đã trao đổi

1. Một chủ spa/thương hiệu sử dụng một deployment riêng, database, tên miền và secrets riêng.
2. Nhiều chi nhánh hoạt động trong deployment đó. Dữ liệu nghiệp vụ vẫn được cô lập theo chi nhánh.
3. Một codebase và quy trình deploy dùng chung cho các khách hàng; tránh tách bản code riêng cho từng chủ spa.
4. Giao diện dùng thuật ngữ “Chi nhánh”. Slug nếu còn cần sẽ là mã/đường dẫn kỹ thuật, không phải thông tin người dùng phải nhớ để đăng nhập.
5. Chủ spa đăng nhập một lần, chọn chi nhánh được cấp quyền. Nhân viên chỉ thấy chi nhánh được phép.
6. Lựa chọn “Tất cả chi nhánh” dành cho người có quyền tổng hợp; không có nghĩa là xem dữ liệu các chủ spa khác trên deployment khác.

Các điểm trên là hướng PO yêu cầu lưu để cân nhắc triển khai. Chi tiết schema, API, migration và các mặc định nghiệp vụ bên dưới chưa được phê duyệt riêng.

## 3. Tài khoản, quyền và dữ liệu

- Đề xuất tách danh tính đăng nhập dùng chung trong deployment khỏi quyền thành viên tại từng chi nhánh.
- Đăng nhập không cần slug đòi hỏi sửa backend xác thực; không chỉ ẩn trường trên frontend.
- Phải có kế hoạch xử lý số điện thoại trùng giữa các tenant hiện tại. Không tự gộp tài khoản, mật khẩu hoặc hồ sơ chỉ vì cùng số điện thoại.
- Backend xác minh quyền chi nhánh cho mọi request và thao tác chuyển chi nhánh. ID/header từ client không tự tạo quyền.
- Giữ RLS và điều kiện lọc phạm vi dữ liệu. Tổng hợp đa chi nhánh phải có đường truy cập được kiểm soát; không tắt RLS hoặc dùng role bypass để làm dashboard.
- Quy tắc đã triển khai về KTV phụ trách cố định vẫn cần được giữ: chỉ người phụ trách và Admin có quyền phù hợp được xem/sửa hồ sơ; đổi người thực hiện lịch không tự chuyển quyền.
- Đề xuất bản đầu: hồ sơ khách, thẻ liệu trình và KTV phụ trách thuộc từng chi nhánh. Thẻ dùng xuyên chi nhánh và hồ sơ khách chung cần PO chốt quy tắc trước.
- “Tất cả chi nhánh” là chế độ xem tổng hợp; thao tác tạo/sửa nghiệp vụ cần xác định chi nhánh cụ thể.

## 4. Dashboard dự kiến

Một dashboard có bộ chọn chi nhánh hoặc “Tất cả chi nhánh”, có thể gồm:
- Lịch hẹn hôm nay và khách đang phục vụ.
- Tiền thực thu, chia tiền mặt/chuyển khoản.
- Khoản chưa thu và tình trạng thẻ liệu trình.
- Tổng hợp và so sánh giữa các chi nhánh được cấp quyền.

Phải tách tiền thực thu khỏi giá trị dịch vụ hoàn thành. Chốt công thức chỉ số, khoảng ngày theo Asia/Ho_Chi_Minh, cách tính hoàn tác và cách đếm khách trước khi triển khai. Không cộng trùng cùng một khoản khi tổng hợp.

## 5. Luồng khách đặt lịch dự kiến

- Tên miền thương hiệu dẫn tới lựa chọn chi nhánh bằng tên dễ hiểu.
- Khách không cần tự nhập slug để đăng nhập.
- Cách dùng chung tài khoản khách giữa chi nhánh, chọn chi nhánh trước/sau đăng nhập và tương thích các đường dẫn PWA cũ cần được thiết kế và chốt.
- Xử lý token/cache/service worker và thông báo khi đổi chi nhánh để không hiển thị dữ liệu chi nhánh trước.

## 6. Cấu hình và vận hành

- Biến môi trường dành cho kết nối database, tên miền, secrets, cấu hình hạ tầng và giá trị khởi tạo phù hợp.
- Tên, địa chỉ, giờ mở cửa của chi nhánh, nhân viên và quyền truy cập quản lý trong ứng dụng/database.
- Chưa quy định tên biến môi trường mới hoặc khẳng định ứng dụng đã hỗ trợ chúng.
- Mỗi deployment cần backup, giám sát, cập nhật phiên bản và rollback riêng; tự động hóa quy trình dùng chung.
- Triển khai riêng không thay thế kiểm soát quyền hoặc bảo mật dữ liệu giữa các chi nhánh.

## 7. Hiện trạng cần phân biệt

Bản đầu đã triển khai bằng migration 0005_branch_accounts: danh tính quản trị chung, dropdown chi nhánh theo quyền và dashboard riêng/tổng hợp. tenant_id, URL/API cũ và PWA theo chi nhánh được giữ. Xem API_CONTRACT để biết endpoint hiện hành và PROGRESS để biết kết quả kiểm thử/giới hạn.

Các kết quả test đã ghi trong PROGRESS chỉ xác nhận code tại các mốc tương ứng; không chứng minh thiết kế đa chi nhánh mới đã chạy đúng. Các yêu cầu staging HTTPS, backup và vận hành production trong RELEASE_RUNBOOK vẫn còn hiệu lực.

Không tự đổi tenant_id thành branch_id, gộp tenant hoặc xóa cơ chế cũ trước khi có thiết kế chuyển đổi dữ liệu đã được thống nhất.

## 8. Các điểm cần chốt khi PO cho phép triển khai

- Quyền chủ thương hiệu, Admin chi nhánh và nhân viên; nhân viên làm ở nhiều chi nhánh.
- Danh tính khách dùng chung hay riêng; phạm vi hồ sơ và việc dùng thẻ xuyên chi nhánh.
- Quy tắc gộp/xử lý tài khoản cũ trùng số điện thoại và các tenant đang có dữ liệu.
- Dịch vụ, giá, lịch làm việc và nhân sự được quản lý riêng hay dùng mẫu chung.
- Chỉ số dashboard, quyền xem tổng hợp và phạm vi thao tác trong chế độ “Tất cả”.
- Tương thích API/URL/token cũ, kế hoạch migration, backup và rollback.

Đây là danh sách việc thiết kế, không phải yêu cầu hỏi lại toàn bộ ngay khi đọc tài liệu.

## 9. Trình tự dự kiến sau khi được phép

1. Đọc lại trạng thái thực tế; chốt phạm vi và các điểm còn mở có ảnh hưởng trực tiếp.
2. Thiết kế tài khoản/quyền chi nhánh, hợp đồng API và phương án migration/rollback.
3. Triển khai backend và test phân quyền, cô lập dữ liệu, thu hồi quyền, đăng nhập và chuyển chi nhánh.
4. Triển khai giao diện đăng nhập/dropdown/dashboard và luồng khách đặt lịch.
5. Chạy regression booking/thẻ/thu tiền/thông báo; E2E chuyển chi nhánh và tổng hợp; kiểm thử dữ liệu chuyển đổi.
6. Cập nhật PRD/API_CONTRACT/PROGRESS/RELEASE_RUNBOOK và kiểm chứng staging trước phát hành.

## 10. Chỉ dẫn cho conversation tiếp theo

- Đọc AGENTS.md → PROGRESS.md → tài liệu này khi bắt đầu task; đọc PRD/API_CONTRACT theo phạm vi.
- Luôn phân biệt trạng thái đang có, định hướng dự kiến và phần đã được PO cho phép triển khai.
- Khi chưa có chỉ thị triển khai mới từ PO, chỉ làm task được giao; không tự tiến hành chuyển đổi đa chi nhánh.
- Nếu PO cho phép triển khai trong conversation sau, ghi nhận phạm vi/ngày phê duyệt ở đây và PROGRESS; tiếp tục trong phạm vi đã được phép, không xin lại quyền đã có.
- Nếu định hướng thay đổi, cập nhật tài liệu này làm nguồn tham chiếu thống nhất, giữ lại lý do và trạng thái quyết định.

## Phê duyệt triển khai — 17/10/2026
PO đã chỉ thị “ok bắt đầu triển khai đi”. Phạm vi: tài khoản quản trị chung, chi nhánh theo quyền, dashboard riêng/tổng hợp, danh sách chi nhánh cho khách, cấu hình deployment riêng. Giữ tenant_id làm mã chi nhánh nội bộ; hồ sơ/thẻ/dịch vụ/giá/nhân sự theo chi nhánh; không tự gộp tài khoản trùng số. Các đoạn chờ phê duyệt phía trên là lịch sử đề xuất và được thay thế bởi mục này.

## Kết quả bản đầu
Đã kiểm chứng local: backend 62/62, E2E 34/34, build và backup/restore PASS. Không tự hợp nhất các tenant/owner cũ; người vận hành cần đối chiếu tài khoản chưa chuyển đổi. Thẻ/hồ sơ/dịch vụ/giá vẫn riêng theo chi nhánh. Credentials tài khoản nhiều chi nhánh chưa có luồng sửa chung; không gọi phần đó là đã hoàn thành. Staging/production deployment và các gate trong RELEASE_RUNBOOK chưa được thực hiện thay cho người dùng.

## Điều chỉnh onboarding theo PO — 17/10/2026
PO yêu cầu seed duy nhất tài khoản quản trị triển khai của mình và có màn hình riêng để tạo tài khoản chủ spa. Đã chuyển sang /operator/login và /operator trong từng deployment; chủ spa giữ /admin/login và luồng đa chi nhánh hiện có. Điều này thay thế bootstrap chủ spa bằng terminal trong các mô tả cũ. Secrets operator cấu hình một lần, không có mật khẩu mẫu; không tạo demo mặc định. Không tự gộp owner/tenant cũ, không tạo control plane xuyên các deployment.
