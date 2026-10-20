# Thiết kế trải nghiệm điện thoại trước pilot

Ngày: 18/10/2026. Trạng thái: đề xuất thiết kế từ review, CHƯA triển khai. Thứ tự thực thi và giới hạn từng đợt theo UI_UX_EXECUTION_PLAN.md bản 2; các lựa chọn UX đích dưới đây không phải lệnh thay đồng loạt kiến trúc/route. PO yêu cầu ưu tiên chất lượng phone. Tài liệu này hướng dẫn chỉnh UI trong kiến trúc hiện tại; không thay nghiệp vụ, quyền truy cập, RLS hay giao dịch. Bằng chứng/phát hiện: UI_UX_REVIEW.md.

## 1. Mục tiêu trải nghiệm

Trạng thái mới nhất 19/10/2026: T11b/T11c/T11d đã nghiệm thu phạm vi Chromium: 28/29 task, còn T12. Guard dirty/pending đổi chi nhánh cả hai tab, giữ UUID/payload giao dịch; dashboard đúng scope/Back/Forward, thông báo vừa màn hình/có retry và coverage các route còn lại. Production cuối 86d9eaf7-ae95-42eb-ae99-d6d658765eeb: build/TypeScript và full E2E 204/204 PASS (554.89s); backend isolated 88/88, unit QA harness 23/23 PASS. T12 mới đạt phần tự động; thiết bị thật/bàn phím/safe area/zoom 200% và pilot CHƯA KIỂM CHỨNG. QA-04 đã tái hiện ở run trung gian f5a26bdb, chưa đóng nguyên nhân; không nới JWT hoặc coi lượt xanh là đã sửa. Migration 0008 chưa áp dụng DB ứng dụng; chưa chốt pilot/release. Xem PROGRESS cho source, run lỗi, lệnh và cleanup. Các nhận xét trước là lịch sử/thiết kế đích.

T12 bổ sung 19/10/2026: PO xác nhận chưa có staging HTTPS/thiết bị thật. Đã thêm probe JWT chỉ đọc và log clock an toàn; backend isolated 98/98, production regression phiên/đa chi nhánh/Operator 44/44 PASS (9c4b7634). Probe 21.761 mẫu/120s không tái hiện, chưa đóng nguyên nhân QA-04. Full UI 204/204 là lượt trước, frontend không đổi. T12 vẫn mở, không nghiệm thu giả lập thay điện thoại/pilot thật; xem PROGRESS và RELEASE_RUNBOOK.
Chủ spa dùng nhanh khi đang tiếp khách; KTV nhận biết lịch và khách trong phạm vi của mình; khách tự đặt đúng dịch vụ/ngày/giờ và hiểu số buổi thẻ. Thiết kế theo tác vụ, không chỉ thu nhỏ màn hình PC.

Mỗi màn hình có một hành động chính nổi bật. Thông tin giờ/khách/số tiền đứng trước mô tả và nhật ký. Giảm lượng thông tin hiển thị bằng mở chi tiết, không giảm font để nhét vừa. Không che overflow bằng cắt cả trang.

## 2. Điều hướng và bố cục chung
- Admin mobile: thanh dưới 5 mục Tổng quan / Lịch hẹn / Khách / Thu tiền / Thêm. KTV chỉ có Lịch hẹn / Khách / Thêm theo quyền; ẩn hoàn toàn mục tài chính không được cấp. Trang Thêm chứa dịch vụ, nhân sự, báo cáo, cài đặt, chi nhánh theo vai trò.
- Header gọn: tên chi nhánh hiện tại và thông báo. Tên dài rút gọn ở header nhưng xem được đầy đủ trong bộ chọn. Không lặp tên tài khoản/role chiếm diện tích trên từng trang.
- Trang nhập liệu dài dùng màn hình riêng có Quay lại/Lưu. Khi vào luồng tập trung, thanh hành động thay thanh điều hướng dưới; không chồng hai thanh cố định. Tính safe area và khoảng trống nội dung đúng chiều cao thực.
- Mobile 360–430px: lề 16px, khoảng cách nhóm 16–24px; chữ nội dung chính 16px, thông tin phụ 14px, nhãn nhỏ tối thiểu 12px khi phù hợp. Input 16px, vùng thao tác chính 44–48px là mục tiêu thiết kế; không coi con số này là chứng nhận accessibility.
- Cột/card cần min-width:0 và quy tắc ngắt chuỗi dài. Tên dài cho xuống dòng, số tiền luôn đọc đầy đủ; mã/ghi chú dài ngắt dòng, không dùng break-all cho mọi câu tiếng Việt.

## 3. Lịch hẹn — ưu tiên cao nhất
### Điện thoại
- Mở mặc định ngày hôm nay: tiêu đề Hôm nay + ngày/tháng, nút chọn ngày; dải ngày gọn có số lịch, vẫn có nút tháng/ngày để đi xa. Có Hôm nay để quay về.
- Bộ lọc KTV/trạng thái trong sheet “Lọc”; trên màn hình chỉ giữ chip bộ lọc đang dùng và Xóa lọc. Trạng thái rỗng phải nói rõ rỗng do bộ lọc hay không có lịch.
- Lịch dạng agenda theo giờ, mỗi card: giờ bắt đầu–kết thúc; tên khách; dịch vụ và KTV thực hiện; trạng thái có chữ. Badge/tiền/ghi chú phụ đưa vào chi tiết khi cần, tránh lặp đầy đủ mọi thông tin.
- Chạm card mở chi tiết. Một hành động tiếp theo theo trạng thái; Dời lịch/Hủy/Vắng mặt đặt trong tác vụ phụ rõ tên. Không dùng vuốt làm cách duy nhất cho hành động quan trọng.
- Hoàn thành ghi rõ tác động thẻ nếu có. Hủy/vắng mặt cần phân biệt; không đổi lịch bằng hủy rồi tạo mới. Bàn giao quyền hồ sơ giữ là lựa chọn Admin riêng.
- Chế độ tuần mobile là danh sách nhóm theo ngày, ngày trống gọn một dòng; không dùng 7 khối cao tối thiểu 260px. Không ép bảng 7 cột vào màn hình phone.
### PC/tablet
- Thẻ tuần riêng dạng gọn; mỗi cột đủ chiều rộng, mở chi tiết để chỉnh. Bố cục dựa vào chiều rộng vùng nội dung, tính cả sidebar. Nếu cần cuộn ngang lịch tuần thì cuộn cục bộ có chỉ dẫn, không làm rộng trang.
- Với 10 nhân viên, lọc theo KTV và trạng thái phải dễ thấy; chỉ bổ sung chế độ trục nhân viên nếu thử nghiệm thực tế chứng minh cần, không tự mở rộng thành module lịch phức tạp.
### Dời lịch
Màn hình tập trung: khách + lịch hiện tại → ngày mới/KTV thực hiện → giờ mới → xác nhận “Dời sang …”. Giữ dịch vụ/thẻ và nội dung khi xung đột, tải lại giờ phù hợp, không bắt nhập lại. Việc đổi KTV khác chuyển quyền hồ sơ phải diễn đạt riêng.

## 4. Thu tiền — thông tin đối chiếu luôn rõ
- Danh sách mặc định Còn cần thu; ô tìm kiếm riêng toàn hàng, gợi ý Tên hoặc số điện thoại. Bộ lọc phụ gọn; nhãn số liệu “Đã thu hôm nay” và “Còn phải thu” có phạm vi rõ.
- Card: tên khách → dịch vụ/thẻ → dòng Còn phải thu với số tiền nổi bật; đã thu/tổng tiền là thông tin phụ. Nút xác nhận full-width trên mobile, không ép cột tên/tiền cạnh nút.
- Chọn khoản thu mở sheet (trường hợp đơn giản) hoặc màn hình xác nhận riêng (nội dung dài). Hiện khách, chi nhánh, dịch vụ, số tiền, Tiền mặt/Chuyển khoản; tùy chọn “Khách trả một phần” mới mở nhập số tiền.
- CTA cuối: “Xác nhận đã nhận 250.000đ”. Số tiền lấy từ server, không tự tính lại theo menu. Sau thành công hiển thị đã nhận bao nhiêu, còn thiếu bao nhiêu, quay đúng vị trí danh sách.
- Mất response: “Đang đối chiếu khoản thu”/Thử lại cùng giao dịch; giữ UUID idempotency và payload. Không mở nút tạo khoản thu mới khi kết quả chưa rõ. Lỗi tải lại sau thành công phải phân biệt với thu thất bại.
- Hoàn tác nằm trong lịch sử khoản thu, có lý do và xác nhận số tiền; nói rõ đây là điều chỉnh sổ thu, không tự hoàn tiền ngân hàng.

## 5. Khách hàng và thẻ liệu trình
- Mobile: danh sách → hồ sơ riêng, có Quay lại giữ tìm kiếm/vị trí cuộn. Không bắt cuộn qua danh sách dài để đến hồ sơ bên dưới. Chọn hồ sơ bằng control có semantics bàn phím.
- Hồ sơ: tên/SĐT, KTV phụ trách hồ sơ, thao tác Đặt lịch; tiếp đến thẻ/lịch sử. Ghi chú sức khỏe và thao tác chuyển người phụ trách tuân thủ quyền hiện tại.
- Thẻ hiển thị rõ: tên thẻ, Đã dùng X/Y, Đang giữ chỗ Z, Có thể đặt thêm N, hạn dùng. Trạng thái tiếng Việt; khi hết khả dụng do giữ chỗ, giải thích và dẫn đến lịch đã đặt, không tô đỏ như lỗi hệ thống.
- “Dùng 1 buổi trong thẻ” thay cho “Giá 0đ” khi nói về một buổi; tránh gây hiểu nhầm rằng thẻ đã thanh toán hoặc dịch vụ miễn phí. Công nợ thẻ vẫn là nghiệp vụ riêng.

## 6. Khách tự đặt lịch
Đề xuất 3 bước: Dịch vụ/thẻ → Ngày giờ và KTV → Kiểm tra & xác nhận. Không bỏ kiểm tra auth hoặc giá ở server.
- Dịch vụ: tên/giá/thời lượng rõ, thẻ của khách ở vị trí dễ thấy; chọn dùng thẻ hay trả theo lượt rõ ràng, không tự chọn thay khách.
- Ngày giờ/KTV: Spa sắp xếp là lựa chọn mặc định; nếu chọn người cụ thể thì hiển thị tên được phép công khai. Ngày hôm nay/ngày mai dễ chọn, disable ngày quá khứ cả ô ngày lẫn nút mũi tên.
- Giờ nhóm Sáng/Chiều/Tối; chưa chọn giờ thì chưa mở bước xác nhận. Không tự chọn slot đầu khi đổi lựa chọn. Đổi dịch vụ/ngày/KTV xóa slot không còn tương thích và thông báo ngắn.
- Lỗi tải giờ khác “Hết giờ trống”: có Thử lại, giữ ngày và lựa chọn. Hết giờ thì gợi ý đổi ngày/KTV; không hiển thị lịch trống giả khi mạng lỗi.
- Xác nhận: dịch vụ, ngày, giờ, KTV, chi nhánh, thời lượng, tiền dự kiến hoặc số buổi dùng thẻ. Khách chưa đăng nhập nhập SĐT/mật khẩu ở bước này, giữ lựa chọn khi đăng nhập thành công; không điền credentials demo.
- Đặt thành công có trang/tóm tắt lịch và hành động Xem lịch hẹn; xung đột slot cho chọn giờ khác trong cùng luồng, giữ phần dữ liệu còn hợp lệ.

## 7. Tổng quan và thông báo
- Tổng quan mobile ưu tiên lịch hôm nay, đang phục vụ, thực thu; tác vụ Xem lịch/Thu tiền nằm sớm. Phần tiền mặt/chuyển khoản/giá trị dịch vụ và số liệu toàn thời gian mở chi tiết; không bắt người dùng cuộn qua 9 thẻ mới đến tác vụ.
- Toàn chi nhánh là chế độ xem tổng, không phải phạm vi ghi tiền/đặt lịch. Khi đi vào thao tác ghi phải hiện rõ chi nhánh cụ thể.
- Thông báo mobile dùng sheet/drawer giới hạn theo viewport, target rõ, đọc chưa đọc có chữ/icon. Không hiển thị lời nhắc bật Push ở mọi màn hình; xin quyền khi người dùng chọn nhận nhắc lịch.

## 8. Trạng thái, accessibility và dữ liệu nhạy cảm
- Tách loading, chưa có dữ liệu, không có kết quả lọc, mất mạng và không có quyền. Có hành động khôi phục thích hợp; thông báo lỗi nằm gần trường hoặc vùng liên quan, focus tới lỗi đầu tiên khi submit.
- Lỗi mạng/5xx không xóa phiên; 401 xử lý xác thực. Chưa xác minh auth thì không cho ghi dữ liệu; không dùng màn hình cũ để lộ thông tin sau chuyển tài khoản/chi nhánh.
- Dialog có tên truy cập, initial focus/focus trap, Escape và trả focus, khóa cuộn nền. Nút chỉ icon có accessible name. Form đang lưu hoặc giao dịch chưa rõ kết quả không đóng/chuyển chi nhánh tùy tiện.
- Không lưu hồ sơ sức khỏe, credential hoặc draft thanh toán vào localStorage để “giữ trạng thái”. Dữ liệu form giữ trong luồng phù hợp và xác nhận trước khi bỏ thay đổi.
- Màu thương hiệu không thay màu trạng thái nghiệp vụ. Kiểm tra chữ phụ/icon/selected/focus trên màu vàng, trắng gần trắng, xanh đậm và đen; không chỉ kiểm tra nút chính.

## 9. Nghiệm thu và trình tự triển khai
### Thứ tự thực thi hiện hành
Theo [UI_UX_EXECUTION_PLAN.md](UI_UX_EXECUTION_PLAN.md) bản 2: nền QA trước; sửa lịch/copy/primitive theo task lá; modal trước các sheet; phiên/mạng và contract dữ liệu trước wizard/dời lịch. T01/T08/T09 có gate quyết định nghiệp vụ/API. Không coi danh sách ưu tiên UX là cho phép bỏ dependency.

### Kiểm chứng thực tế
- Chromium 360/390/430/768/1024/1366px; 320px là ca biên. PC dùng chuột/bàn phím; Android Chrome và iPhone Safari thật, portrait/landscape, bàn phím ảo, safe area, zoom 200%.
- 10 KTV, 50+ lịch/ngày và 200+ khách; tên 80 ký tự, dịch vụ dài, note không khoảng trắng 280 ký tự, tiền lớn. Dữ liệu QA riêng.
- Ảnh + bounds viewport VÀ từng card, kiểm tra cả nội dung bị che/cắt dù document không tràn. Sticky CTA không che trường cuối hay footer khi mở bàn phím.
- Mạng chậm/503/401, submit liên tiếp, mất response thu tiền, slot bị chiếm, đổi chi nhánh giữa form. Không reset lựa chọn hoặc mất phiên vì lỗi tạm.
- Nhờ chủ spa/KTV/khách thử: tìm lịch sắp tới, dời lịch, xem buổi còn đặt được, thu đủ/một phần. Ghi lỗi bấm nhầm, số lần cần trợ giúp và thời gian; chỉ chốt đạt sau quan sát, không tự gán điểm UX 9/10.

Không dùng một lượt collector hoàn tất hoặc E2E nghiệp vụ PASS để gọi giao diện “tốt nhất”. Chốt dựa trên các ca nghiệm thu và người dùng thử thật.
