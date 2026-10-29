# Review code UX ngày 29/10/2026

## Cập nhật sau review — đã vá theo yêu cầu PO

- CRM: `loadCustomers` chỉ nhận khách liên kết qua tham số `initialTarget` của lần tải đầu. Tìm kiếm/làm mới sau đó không đọc lại khách từ URL.
- Form đặt lịch mới gọi `manualBatch.defer()` để tách operation trước khi reset trường. Retry trong cùng form vẫn giữ UUID; yêu cầu chưa rõ kết quả vẫn ở hàng đợi với bản nháp riêng.
- Thư viện hướng dẫn không đăng ký listener/auto-open và không mở modal; shell điều khiển hộp tour duy nhất. Lỗi hai modal được tái hiện ở Admin Help; Customer Help không có bước tour riêng và cũng được kiểm tra không tự mở modal.
- Regression source-level `node --test frontend/tests/ux-review.test.cjs`: **5/5 PASS**, API/storage/React giả lập. Bao gồm mở khách ngoài trang đầu rồi tìm B; lỗi 409; lỗi 503 → check 404 → retry cùng mã → form mới khác mã và giữ bản nháp A/B; tour Admin/Customer chỉ shell đăng ký listener.
- `npm run build` production PASS (gồm lint/TypeScript strict/tạo trang); `git diff --check` PASS. Không chạy lại backend/full E2E; DB ứng dụng local còn lỗi mount. Các phần dưới là kết quả review trước khi vá.

Phạm vi: thay đổi chưa commit của đợt UX/guest requests 29/10. Review code và chạy ba probe Node trên source thực (TypeScript transpile, API/React giả lập); không chạy lại browser E2E hoặc backend suite. `git diff --check` PASS. Không đổi code ứng dụng, DB hoặc secrets trong lần review này.

## [WARNING] P2 — CRM đọc lại deep link trong mọi lần tìm kiếm

Vị trí: `frontend/src/app/(admin)/admin/customers/page.tsx:120–126`.

Sau khi quay về `/admin/customers?customer_id=A` từ Thu tiền, người dùng về danh sách rồi tìm khách B. `loadCustomers` luôn đọc lại A từ URL, chèn A vào kết quả dù không khớp từ khóa, chọn A và mở lại chi tiết. Probe với API trả duy nhất B xác nhận kết quả `[A,B]`, selection A và một lần mở detail. Deep link cần được tiêu thụ một lần; tìm kiếm/làm mới sau đó phải tôn trọng lựa chọn hiện tại.

## [WARNING] P2 — Form mới dùng lại mã yêu cầu cũ

Vị trí: `frontend/src/lib/use-manual-batch.ts:40,54–56`; `frontend/src/app/(admin)/admin/bookings/page.tsx:654–670`.

Sau lỗi xác định hoặc check trả 404, hook giữ operation để retry an toàn. Tuy nhiên đóng form rồi bấm Tạo lịch hẹn chỉ reset các trường, không tách operation. Submit cho khách B tiếp tục dùng UUID của A và ghi đè body khôi phục. Probe xác nhận hai body khách khác nhau dùng cùng request_id. Đặc biệt nếu POST A đến muộn sau check 404, B sẽ nhận xung đột nội dung; kiểm tra mã trả kết quả A thay vì lịch mới mong muốn. Cần tách thao tác bắt đầu form mới khỏi thao tác chỉnh/retry cùng yêu cầu; giữ bản ghi A riêng để đối chiếu.

## [WARNING] P2 — Hai hộp tour cùng mở trên trang Trợ giúp

Vị trí: `frontend/src/components/screen-help.tsx:15–25`; trang admin/customer help và shell cùng mount ScreenHelp.

Khi tour active tới màn Trợ giúp, cả instance ở shell lẫn instance `library` chạy auto-open và render Modal. Probe xác nhận cả hai có open=true; đóng instance library vẫn để instance shell mở. Người dùng phải đóng/hoàn tất hai lần, trạng thái tour không đồng bộ. Library nên chỉ render danh mục và nút restart; một instance duy nhất điều khiển tour.

## [PASSED] Qua rà soát code trong phạm vi

- Guest request lọc tenant từ dependency; migration ENABLE/FORCE RLS và timestamp có timezone.
- Capability dùng token hash và so sánh constant-time, public response không trả CRM/thẻ/SĐT; không tự ghép tài khoản theo SĐT.
- Xác nhận guest dùng khóa workforce/request và reuse booking locks; create_batch/update status commit=False, commit cuối cùng ở decision.
- Logic COMPLETED vẫn khóa thẻ, kiểm tra chuyển trạng thái và trừ buổi trong transaction; thay đổi lần này không bỏ kiểm soát đó.
- Không thấy truy cập lazy relationship mới gây MissingGreenlet hoặc vòng lặp truy vấn mới trên từng dòng inbox.

Không phát hiện CRITICAL trong phần đã kiểm tra. Các nhận định PASSED là kết quả review code, không thay cho full suite hay nghiệm thu production. Ba WARNING ban đầu đã được vá ở lượt tiếp theo, xem cập nhật đầu báo cáo.
