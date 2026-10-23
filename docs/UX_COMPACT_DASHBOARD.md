# Logo, hướng dẫn và Tổng quan gọn — 23/10/2026

PO phê duyệt triển khai toàn bộ kế hoạch trong chat ngày 23/10/2026. Đây là thay đổi UX trên kiến trúc hiện hành.

## Hành vi được triển khai

- Icon SpaOS PNG có biểu tượng chữ S, đồng bộ SVG; 192/512 px và Apple Touch 180 px. Manifest quản lý/khách/root dùng cùng bộ icon, purpose any/maskable và phiên bản URL mới. Giữ id/start_url/scope của ứng dụng đã cài. Logo chi nhánh không tự đổi icon ứng dụng.
- Logo chi nhánh xuất hiện cạnh dropdown trên mobile/desktop. Tổng hợp dùng nhận diện SpaOS, không mượn logo của một chi nhánh. Lưu cài đặt cập nhật context tại chỗ và giữ thông báo thành công; ảnh không tải được có fallback và cảnh báo tại biểu mẫu.
- Popup lần đầu có Xem hướng dẫn nhanh / Cài ứng dụng / Để sau và đóng bằng nút hoặc Escape. Ghi nhớ trên trình duyệt sau khi đóng/chọn. Admin/Staff chia sẻ tùy chọn qua các membership đã được API xác minh; không giải mã JWT để tạo quyền. Tôn trọng trạng thái seen v1. Khách dùng tùy chọn theo chi nhánh và tài khoản, tiếp nối tùy chọn khách vãng lai.
- Không còn nút hướng dẫn phía trên nội dung mỗi trang. Desktop quản trị có menu Trợ giúp & Cài ứng dụng; mobile quản trị/khách mở qua Thêm. Nội dung riêng tại /admin/help và /[tenant_slug]/help.
- Tổng quan gồm Lịch hẹn, Tiền đã thu, Khoản chưa thu, Thẻ liệu trình; Tất cả chi nhánh thêm Theo từng chi nhánh. Từng mục mặc định đóng, tóm tắt luôn hiện. Mở lại có thể tải dữ liệu chi tiết mới; nhiều mục được mở đồng thời. Đổi ngày/phạm vi đóng các mục và loại kết quả cũ.
- Chỉ Lịch hẹn/Tiền đã thu phụ thuộc Ngày xem. Khoản chưa thu là tất cả ngày; Thẻ liệu trình là hiện tại. Giữ tiền Decimal do server tổng hợp và quy tắc ngày Việt Nam. Giá trị dịch vụ nằm trong phần giải thích, độc lập thực thu.
- Danh sách lịch/khoản chưa thu chỉ tải khi mở mục. Lịch giữ liên kết đến chi tiết hoặc ngày/trạng thái tương ứng. Chế độ tổng hợp không có thao tác thu tiền/lịch trên chi nhánh đang ẩn.
- Thiết lập spa chỉ hiện nếu còn thiếu thông tin hoặc chưa kiểm tra được; luôn đóng mặc định. Không coi lỗi tải thiết lập là đã hoàn thành.

## Kiểm chứng

- Build frontend đầu tiên và TypeScript: PASS.
- Production QA cuối `a899884a-2fdd-4d77-a8fe-1003b108bcbc`: build/strict TypeScript PASS; **61/61 ca PASS (207.03s)**. Bao gồm logo lưu/đổi/reload và đổi chi nhánh; icon/manifest/iOS; popup/ghi nhớ/menu theo vai trò, Escape; panel thu gọn/lazy load/ngày xem và phản hồi cũ về chậm; responsive/bàn phím và hồi quy đa chi nhánh, danh mục, đặt lịch khách.
- Chưa kiểm tra trực tiếp deployment test hoặc native install/push Android/iOS thật từ phiên này. Không thay dữ liệu/credentials môi trường người dùng.

## Nghiệm thu sau deploy test

- Mở URL test qua HTTPS, xác nhận release FE/BE phù hợp; thử upload logo của hai chi nhánh, refresh/đăng nhập lại.
- Kiểm tra popup bằng trình duyệt mới; đóng rồi chuyển trang, reload, đổi chi nhánh. Mở lại qua menu.
- Android Chrome và iPhone Safari: cài từ luồng quản lý/khách tương ứng, xác nhận icon có hình và mở đúng start_url. Shortcut cũ có thể cần cài lại nếu hệ điều hành còn giữ icon cũ; không tạo id mới để ép cài trùng ứng dụng.
- Kiểm tra các panel trên điện thoại nhỏ, thao tác bàn phím, ngày quá khứ và tổng hợp nhiều chi nhánh. Khoản chưa thu/thẻ hiện tại phải có nhãn riêng.

## Kiểm tra trực quan cuối

Đã xem icon và giao diện thật tại 1366x900 và 390x844 trên QA dev độc lập, gồm popup lần đầu, Tổng quan đóng và panel mở. Ảnh local được Git ignore: [Desktop](../automation_test/artifacts/qa/compact-ux-20261023/dashboard_desktop.png), [Mobile](../automation_test/artifacts/qa/compact-ux-20261023/dashboard_mobile.png), [Popup](../automation_test/artifacts/qa/compact-ux-20261023/first_use_mobile.png). Số liệu là seed QA, không phải dữ liệu spa đang triển khai. Đây là kiểm tra trực quan bổ sung cho 61 ca production E2E, không thay nghiệm thu thiết bị thật.
