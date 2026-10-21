# Rà soát trải nghiệm SpaOS theo ba nhóm người dùng

Ngày: 21/10/2026. Trạng thái: đã xử lý phần triển khai/quyết định của 37 mục; 3 mục còn nghiệm thu thiết bị/pilot. Kết quả cuối: backend 116/116 và E2E 257/257 PASS. Các phần review ban đầu được giữ làm baseline.

## Phạm vi và độ chắc chắn

Rà soát các route hiện có của chủ spa, nhân viên và khách hàng trong frontend/src, component điều hướng/thông báo/thu tiền, đối chiếu API_CONTRACT, PRD, MULTI_BRANCH_STRATEGY và tiến độ mới nhất. Đây là review mã nguồn và luồng sản phẩm; chưa chạy thêm browser/E2E, chưa phỏng vấn người dùng hoặc đo thao tác thực trong lượt này. Không coi các vấn đề UX là lỗi CRITICAL về bảo mật; chưa phát hiện/kiểm chứng lỗi bảo mật mới để tự vá. Không sửa code hoặc dữ liệu trong lượt review.

40 mục gồm 12 cho chủ spa, 8 cho nhân viên, 12 cho khách và 8 dùng chung. Đây là toàn bộ phát hiện/đề xuất trong phạm vi đã rà, không phải cam kết đã tìm hết mọi vấn đề trên mọi thiết bị. Hiện trạng được dẫn tới file và dòng; tác động là đánh giá cần xác nhận bằng pilot. Các đề xuất API/quyền/nghiệp vụ không được xem là tính năng đã có hoặc được phê duyệt triển khai.

P1: ưu tiên đợt cải thiện cốt lõi vì cản trở công việc/đặt lịch, gây hiểu nhầm hoặc dễ thao tác sai. P2: làm sau khi luồng chính ổn định và pilot xác nhận nhu cầu. P1 không đồng nghĩa tất cả đều là lỗi hay phải triển khai cùng lúc.

## Nguyên tắc sản phẩm được ghi nhận từ PO

- Khách dễ biết dịch vụ, giá, thời lượng và giờ phù hợp trước khi xác nhận.
- Nhân viên mở app biết việc tiếp theo và có hành động phù hợp quyền.
- Chủ spa nhanh chóng biết hoạt động và việc cần xử lý của từng chi nhánh.
- Không hỏi lại dữ liệu đã biết; mặc định hợp lý nhưng cho đổi.
- Ưu tiên ngôn ngữ công việc; vẫn giải thích tác động cần thiết tới lịch, tiền và thẻ.
- Giảm công sức và nhầm lẫn, không giảm số lần bấm bằng cách bỏ xác nhận quan trọng.
- Giữ tenant/RLS, quyền hồ sơ, giao dịch, chống trùng lịch, chống ghi tiền/trừ buổi lặp.

## Những phần đã có cần giữ

- Wizard khách hiện có ba bước, chọn giờ trước và đăng nhập nhanh ở bước xác nhận; không phải app bắt đăng nhập mới xem được mọi giờ trống.
- Đã có mặc định Spa tự sắp xếp, chọn dịch vụ từ catalog và đặt từ thẻ; cần rút ngắn luồng, không xây lại từ đầu.
- Khách đã có đổi ngày/giờ, hủy với giới hạn thời gian; quản trị có trạng thái, lịch ngày/tuần và tạo nhiều buổi.
- Đã có điều hướng mobile theo quyền, retry nhiều màn, guard form/giao dịch khi đổi chi nhánh và chống response muộn trong các luồng đã sửa.
- Đã có thu tiền và phân biệt thực thu với giá trị dịch vụ hoàn thành; không ghi nhận nhầm là app chưa có thu tiền.
- Đã có thông báo in-app/Push và quyền đọc lịch được giao; Push thiết bị thật và độ bền tác vụ còn giới hạn được ghi trong PROGRESS.

## Thứ tự thực hiện đề xuất

1. Sửa vướng mắc rõ và nhỏ: KH-05 quay lại đúng trang sau login, KH-06 xác nhận hủy, DC-01 câu chữ, DC-05 nhãn/nút truy cập, NV-03/04 tên người thực hiện và hành động.
2. Giúp thấy lịch trống sớm: KH-01..04 và CS-02. Dùng availability hiện có; tìm ngày gần nhất có giới hạn, không suy giờ trống từ trang lịch phân trang.
3. Tối ưu vận hành: CS-01/03..07 và NV-01/05; quyết định NV-02/07/08 trước khi thay quyền.
4. Liên kết thông báo và phục hồi: DC-02..04/08, KH-07 và CS-12. Các thay đổi danh tính/giao dịch có thiết kế API và regression riêng.
5. Cải tiến P2 theo pilot; DC-07 bắt đầu sớm để có baseline, nghiệm thu lại sau từng đợt.

## Chủ spa

### CS-01 · P1 · Thấy việc cần xử lý ngay trên tổng quan

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Dashboard hiển thị 9 chỉ số và liên kết chung tới Lịch hẹn/Thu tiền; chưa có danh sách hành động gắn từng chỉ số.
- **Ảnh hưởng:** Chủ phải tự tìm lịch chờ xác nhận, khách sắp tới và khoản cần thu.
- **Đề xuất:** Ưu tiên lịch chờ xác nhận, khách sắp tới và khoản cần thu; bấm vào mở đúng danh sách đã lọc theo ngày/chi nhánh.
- **Nghiệm thu:** Mỗi mục dẫn đúng phạm vi; chế độ tổng hợp yêu cầu chọn chi nhánh trước khi ghi dữ liệu.
- **Nguồn:** [frontend/src/app/(admin)/admin/dashboard/page.tsx:12](../frontend/src/app/(admin)/admin/dashboard/page.tsx#L12); [frontend/src/app/(admin)/admin/dashboard/page.tsx:42](../frontend/src/app/(admin)/admin/dashboard/page.tsx#L42).

### CS-02 · P1 · Xem khoảng trống theo nhân viên

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Lịch ngày là các thẻ; lịch tuần là bảy cột ngày. Không có trục giờ theo nhân viên.
- **Ảnh hưởng:** Khó trả lời nhanh khách gọi: giờ này ai phục vụ được?
- **Đề xuất:** Thêm chế độ tìm giờ trống theo dịch vụ/ngày/nhân viên; cân nhắc bảng giờ theo nhân viên trên desktop, danh sách giờ gọn trên mobile.
- **Nghiệm thu:** Khoảng trống lấy từ nguồn availability, gồm thời lượng/ca/nghỉ chuyển tiếp; không suy từ các lịch đã tải một phần.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:1064](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1064); [frontend/src/app/(admin)/admin/bookings/page.tsx:1090](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1090).

### CS-03 · P1 · Tạo một lịch tại quầy gọn hơn

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Một modal chứa tìm/tạo khách, thẻ, dịch vụ, nhân viên, nhiều buổi và ghi chú.
- **Ảnh hưởng:** Người mới phải hiểu nhiều lựa chọn để tạo một lịch đơn.
- **Đề xuất:** Mặc định một buổi; mở phần đặt nhiều buổi khi người dùng yêu cầu. Giữ tóm tắt khách/dịch vụ/giờ/tiền gần nút xác nhận.
- **Nghiệm thu:** Luồng lịch đơn không bắt đi qua cấu hình nhiều buổi; vẫn giữ phục hồi kết quả/chống gửi trùng.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:1152](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1152); [frontend/src/app/(admin)/admin/bookings/page.tsx:1372](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1372).

### CS-04 · P1 · Tìm và chọn khách trong một thao tác

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Hiện nhập tìm kiếm → bấm Tìm khách → mở select → chọn; kết quả có nút tải thêm.
- **Ảnh hưởng:** Chậm khi đang nghe điện thoại hoặc khách xếp hàng.
- **Đề xuất:** Combobox có kết quả tên/SĐT, hỗ trợ bàn phím; tạo khách khi chưa tìm thấy và kiểm tra trùng phía server.
- **Nghiệm thu:** Chọn được khách mà không mở select thứ hai; kết quả muộn không đổi lựa chọn; không tải toàn bộ CRM.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:1218](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1218).

### CS-05 · P1 · Nối hồ sơ khách với đặt lịch và thu tiền

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Chi tiết khách tập trung hồ sơ, phân công và thẻ; lịch và thu tiền ở trang riêng.
- **Ảnh hưởng:** Phải tìm lại cùng một khách khi chuyển công việc.
- **Đề xuất:** Thêm hành động Đặt lịch cho khách và Xem khoản cần thu, giữ đúng khách/chi nhánh; tóm tắt lần hẹn gần nhất khi được phép.
- **Nghiệm thu:** Đi tiếp không phải tìm lại khách; không đưa thông tin riêng tư vào URL.
- **Nguồn:** [frontend/src/app/(admin)/admin/customers/page.tsx:470](../frontend/src/app/(admin)/admin/customers/page.tsx#L470); [frontend/src/app/(admin)/admin/payments/page.tsx:142](../frontend/src/app/(admin)/admin/payments/page.tsx#L142).

### CS-06 · P1 · Dễ hiểu số buổi còn lại và số buổi có thể đặt

- **Loại:** Cải thiện UX.
- **Hiện trạng:** CRM và modal đặt tại quầy hiển thị remaining_sessions; trang thẻ khách có available_sessions và số buổi giữ.
- **Ảnh hưởng:** Chủ và khách có thể thấy con số khác nhau nhưng không hiểu lý do.
- **Đề xuất:** Thống nhất Đã dùng / Đã đặt trước / Có thể đặt; giải thích ngắn khi buổi đang được giữ cho lịch khác.
- **Nghiệm thu:** Với thẻ 5 buổi, đã dùng 1 và đặt trước 2, mọi màn hình thể hiện đúng cùng ý nghĩa.
- **Nguồn:** [frontend/src/app/(admin)/admin/customers/page.tsx:560](../frontend/src/app/(admin)/admin/customers/page.tsx#L560); [frontend/src/app/(admin)/admin/bookings/page.tsx:1285](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1285); [frontend/src/app/[tenant_slug]/profile/page.tsx:164](../frontend/src/app/[tenant_slug]/profile/page.tsx#L164).

### CS-07 · P1 · Thiết lập spa lần đầu theo trình tự

- **Loại:** Đề xuất bổ sung.
- **Hiện trạng:** Dịch vụ, nhân sự, ca và giờ mở cửa đang ở các trang riêng.
- **Ảnh hưởng:** Spa mới có thể không có giờ trống mà không biết cấu hình nào còn thiếu.
- **Đề xuất:** Checklist thiết lập: giờ mở cửa → dịch vụ → nhân viên/ca → xem thử đặt lịch → chia sẻ đường dẫn.
- **Nghiệm thu:** Checklist dựa dữ liệu thật, phân biệt chưa thiết lập với lỗi tải; hoàn tất khi có thể đặt một dịch vụ phù hợp.
- **Nguồn:** [frontend/src/app/(admin)/admin/settings/page.tsx:177](../frontend/src/app/(admin)/admin/settings/page.tsx#L177); [frontend/src/app/(admin)/admin/staff/page.tsx:344](../frontend/src/app/(admin)/admin/staff/page.tsx#L344); [frontend/src/app/(admin)/admin/branches/page.tsx:32](../frontend/src/app/(admin)/admin/branches/page.tsx#L32).

### CS-08 · P2 · Sao chép ca và xử lý nghỉ theo ngày cụ thể

- **Loại:** UX + cần thiết kế nghiệp vụ.
- **Hiện trạng:** Màn hình có bảy ngày trong tuần; API schedules là day_of_week, không phải lịch nghỉ theo ngày cụ thể.
- **Ảnh hưởng:** Nhập lặp nhiều nhân viên; nhãn nghỉ phép dễ bị hiểu thành nghỉ một ngày thay vì nghỉ lặp hằng tuần.
- **Đề xuất:** Trước mắt đổi nhãn Nghỉ hằng tuần và thêm sao chép ca có preview. Thiết kế riêng nghỉ ngày cụ thể/ca tách nếu pilot cần.
- **Nghiệm thu:** Không sửa cả tuần khi chỉ xin nghỉ một ngày; báo lịch bị ảnh hưởng trước áp dụng; phần ngoại lệ ngày cần API/nghiệp vụ mới.
- **Nguồn:** [frontend/src/app/(admin)/admin/staff/page.tsx:386](../frontend/src/app/(admin)/admin/staff/page.tsx#L386); [frontend/src/app/(admin)/admin/staff/page.tsx:440](../frontend/src/app/(admin)/admin/staff/page.tsx#L440).

### CS-09 · P2 · Nhìn rõ bước tiếp theo sau khi thêm chi nhánh

- **Loại:** Đề xuất bổ sung.
- **Hiện trạng:** Trang chi nhánh có tạo chi nhánh và cấp quyền nhân viên; chưa có checklist cấu hình riêng chi nhánh mới.
- **Ảnh hưởng:** Tạo xong nhưng vẫn chưa thể nhận lịch.
- **Đề xuất:** Sau khi tạo, dẫn sang thiết lập của chi nhánh mới; cho sao chép cấu hình có chọn lọc nếu được duyệt.
- **Nghiệm thu:** Chỉ sao chép mục đã chọn, không tự gộp hồ sơ/thẻ/nhân viên hoặc dữ liệu cũ.
- **Nguồn:** [frontend/src/app/(admin)/admin/branches/page.tsx:29](../frontend/src/app/(admin)/admin/branches/page.tsx#L29).

### CS-10 · P2 · Báo cáo dễ chọn kỳ và hiểu phạm vi

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Báo cáo dùng hai ô ngày và tỷ lệ hoa hồng ước tính; tổng quan có chỉ số theo ngày lẫn thẻ còn hiệu lực hiện tại.
- **Ảnh hưởng:** Dễ hiểu mọi số liệu là cùng kỳ hoặc coi hoa hồng ước tính là lương đã chốt.
- **Đề xuất:** Preset hôm nay/tuần này/tháng này; nhóm rõ thực thu, giá trị dịch vụ và số liệu hiện tại; giữ chú thích ước tính ngắn.
- **Nghiệm thu:** Kỳ và công thức hiển thị rõ; không đổi định nghĩa doanh thu/thu tiền để làm UI đơn giản hơn.
- **Nguồn:** [frontend/src/app/(admin)/admin/reports/page.tsx:97](../frontend/src/app/(admin)/admin/reports/page.tsx#L97); [frontend/src/app/(admin)/admin/reports/page.tsx:110](../frontend/src/app/(admin)/admin/reports/page.tsx#L110); [frontend/src/app/(admin)/admin/dashboard/page.tsx:12](../frontend/src/app/(admin)/admin/dashboard/page.tsx#L12).

### CS-11 · P2 · Cài đặt bằng thao tác quen thuộc

- **Loại:** UX + đề xuất bổ sung.
- **Hiện trạng:** Cài đặt yêu cầu Logo URL và có Theme Color; màu có thể do đơn vị triển khai quản lý.
- **Ảnh hưởng:** Chủ phải biết địa chỉ ảnh hoặc gặp ô chỉnh sửa không dùng được.
- **Đề xuất:** Đổi nhãn dễ hiểu; bổ sung tải ảnh và preview khi có hạ tầng upload; màu không được sửa chỉ hiển thị cùng đường dẫn hỗ trợ.
- **Nghiệm thu:** Upload có kiểm tra loại/kích thước/quyền; không hiển thị ô nhập HEX bắt buộc với người dùng phổ thông.
- **Nguồn:** [frontend/src/app/(admin)/admin/settings/page.tsx:146](../frontend/src/app/(admin)/admin/settings/page.tsx#L146).

### CS-12 · P1 · Quản lý tài khoản làm nhiều chi nhánh

- **Loại:** Cần API/quyết định danh tính.
- **Hiện trạng:** Contract chặn sửa SĐT/mật khẩu ở API chi nhánh khi tài khoản có nhiều membership; chưa có màn quản trị credentials chung.
- **Ảnh hưởng:** Chủ dễ gặp lỗi khi muốn đổi mật khẩu nhân viên làm nhiều cơ sở.
- **Đề xuất:** Thiết kế quản lý tài khoản chung với xác minh và quyền rõ; tại form chi nhánh dẫn đúng nơi thay đổi.
- **Nghiệm thu:** Tài khoản dùng được ở các chi nhánh đã cấp; đổi thông tin không tạo tài khoản trùng hoặc gộp theo SĐT.
- **Nguồn:** [frontend/src/app/(admin)/admin/staff/page.tsx:484](../frontend/src/app/(admin)/admin/staff/page.tsx#L484).

## Nhân viên

### NV-01 · P1 · Trang Lịch của tôi thay cho màn điều phối chung

- **Loại:** Cải thiện UX.
- **Hiện trạng:** STAFF được đưa vào /admin/bookings, cùng tiêu đề điều phối và bộ lọc Tất cả Kỹ thuật viên; dữ liệu quyền đọc gồm được giao thực hiện hoặc phụ trách hồ sơ.
- **Ảnh hưởng:** Nhân viên khó phân biệt lịch mình làm với lịch mình chỉ phụ trách khách.
- **Đề xuất:** Mặc định Lịch tôi thực hiện; tách Khách tôi phụ trách nếu cần; đưa lịch kế tiếp/đang làm lên đầu.
- **Nghiệm thu:** Hai nhóm không bị nhầm; bộ lọc không mở quyền đọc mới.
- **Nguồn:** [frontend/src/app/(admin)/admin/login/page.tsx:46](../frontend/src/app/(admin)/admin/login/page.tsx#L46); [frontend/src/app/(admin)/admin/bookings/page.tsx:889](../frontend/src/app/(admin)/admin/bookings/page.tsx#L889); [frontend/src/app/(admin)/admin/bookings/page.tsx:991](../frontend/src/app/(admin)/admin/bookings/page.tsx#L991).

### NV-02 · P1 · Chốt ai được bắt đầu/hoàn thành lịch được giao

- **Loại:** Cần quyết định nghiệp vụ.
- **Hiện trạng:** can_manage=false ẩn thao tác khi nhân viên chỉ được giao thực hiện, không phụ trách hồ sơ.
- **Ảnh hưởng:** Người trực tiếp phục vụ có thể phải nhờ chủ cập nhật lịch.
- **Đề xuất:** Chốt nghiệp vụ: cho người thực hiện cập nhật các trạng thái cụ thể, hoặc có luồng báo hoàn thành để người có quyền xác nhận. Trước khi chốt, hiển thị hướng xử lý ngắn trong chi tiết.
- **Nghiệm thu:** Không tự mở CRM/thẻ; nếu mở cập nhật trạng thái phải có API quyền hẹp, audit và kiểm chứng trừ buổi đúng một lần.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:835](../frontend/src/app/(admin)/admin/bookings/page.tsx#L835).

### NV-03 · P1 · Phân biệt người thực hiện và người phụ trách hồ sơ

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Một số nhãn đặt/dời lịch gọi KTV phụ trách dù đang chọn staff_id thực hiện; CRM có người phụ trách riêng.
- **Ảnh hưởng:** Có thể nghĩ đổi người làm sẽ chuyển luôn hồ sơ khách.
- **Đề xuất:** Dùng Nhân viên thực hiện trong lịch; Người phụ trách khách trong CRM; bàn giao hồ sơ là thao tác riêng rõ tác động.
- **Nghiệm thu:** Đổi người thực hiện không làm người dùng hiểu là đã bàn giao hồ sơ.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:1353](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1353); [frontend/src/app/(admin)/admin/bookings/page.tsx:1651](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1651); [frontend/src/app/(admin)/admin/customers/page.tsx:491](../frontend/src/app/(admin)/admin/customers/page.tsx#L491).

### NV-04 · P1 · Hành động theo việc, không theo tên trạng thái

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Nút hiện dạng → Đã xác nhận, → Đang làm, → Hoàn thành.
- **Ảnh hưởng:** Người mới phải suy luận mình đang đổi trạng thái hay ghi nhận một việc.
- **Đề xuất:** Nhãn Xác nhận lịch / Bắt đầu phục vụ / Hoàn thành buổi; bước ảnh hưởng thẻ hiện tác động trước xác nhận.
- **Nghiệm thu:** Hành động phù hợp trạng thái/quyền; hủy/no-show không ngang mức nổi bật với thao tác thường dùng.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:841](../frontend/src/app/(admin)/admin/bookings/page.tsx#L841).

### NV-05 · P1 · Tạo lịch có mặc định phù hợp quyền của mình

- **Loại:** Cần xác minh luồng + UX.
- **Hiện trạng:** Danh sách nhân viên của STAFF chỉ chứa bản thân, nhưng modal vẫn có lựa chọn Spa tự sắp xếp.
- **Ảnh hưởng:** Giao diện gợi lựa chọn rộng hơn phạm vi làm việc, cần đối chiếu thực tế API trước thay đổi.
- **Đề xuất:** Nếu chỉ được tạo cho mình, hiện sẵn tên mình; ẩn bộ chọn dư. Nếu được điều phối, thiết kế quyền riêng rõ.
- **Nghiệm thu:** UI mô tả đúng kết quả server; không suy rằng STAFF được điều phối toàn spa.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:242](../frontend/src/app/(admin)/admin/bookings/page.tsx#L242); [frontend/src/app/(admin)/admin/bookings/page.tsx:1355](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1355).

### NV-06 · P2 · Xem ca làm của bản thân

- **Loại:** Cần API quyền hẹp.
- **Hiện trạng:** Điều hướng STAFF không có ca làm; API schedules hiện dành ADMIN.
- **Ảnh hưởng:** Nhân viên phải hỏi lại giờ trực dù chủ đã nhập trong app.
- **Đề xuất:** Thêm xem ca cá nhân chỉ đọc; yêu cầu đổi ca/nghỉ là phần mở rộng sau khi chốt quy trình.
- **Nghiệm thu:** Chỉ đọc ca của mình ở chi nhánh được cấp; không có nút tự sửa lịch của người khác.
- **Nguồn:** [frontend/src/components/admin/admin-shell.tsx:56](../frontend/src/components/admin/admin-shell.tsx#L56); [frontend/src/app/(admin)/admin/staff/page.tsx:344](../frontend/src/app/(admin)/admin/staff/page.tsx#L344).

### NV-07 · P1 · Bàn giao thông tin cần thiết khi phục vụ thay

- **Loại:** Cần quyết định nghiệp vụ/quyền dữ liệu.
- **Hiện trạng:** Người được giao lịch chỉ đọc thông tin lịch, không tự được đọc ghi chú sức khỏe/CRM của khách khác.
- **Ảnh hưởng:** Cần cơ chế bàn giao để nhân viên đủ thông tin làm việc mà vẫn giữ riêng tư.
- **Đề xuất:** Xác định thông tin phục vụ tối thiểu được phép chia sẻ và người xác nhận bàn giao; UI chỉ hiển thị trong đúng lịch.
- **Nghiệm thu:** Có phê duyệt phạm vi; không sao chép toàn hồ sơ vào note lịch hoặc thông báo Push.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:828](../frontend/src/app/(admin)/admin/bookings/page.tsx#L828).

### NV-08 · P2 · Phân biệt nhu cầu lễ tân và kỹ thuật viên

- **Loại:** Cần khảo sát và thiết kế quyền.
- **Hiện trạng:** Contract gộp STAFF; thu tiền chỉ ADMIN, CRM STAFF theo người phụ trách.
- **Ảnh hưởng:** Nếu lễ tân sử dụng, họ có thể không đủ công cụ phục vụ khách chung.
- **Đề xuất:** Pilot riêng người trực quầy và kỹ thuật viên; chốt tập quyền lễ tân/thu ngân nếu thực sự cần.
- **Nghiệm thu:** Không cấp toàn quyền chủ spa chỉ để lễ tân làm việc; mỗi quyền được kiểm chứng theo chi nhánh.
- **Nguồn:** [frontend/src/app/(admin)/admin/payments/page.tsx:124](../frontend/src/app/(admin)/admin/payments/page.tsx#L124); [frontend/src/components/admin/admin-shell.tsx:34](../frontend/src/components/admin/admin-shell.tsx#L34).

## Khách hàng

### KH-01 · P1 · Xem giờ trống từ dịch vụ

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Trang dịch vụ chỉ có Chọn đặt lịch; link chọn sẵn dịch vụ nhưng wizard vẫn khởi tạo ở bước 1.
- **Ảnh hưởng:** Khách phải đi tiếp mới biết có giờ phù hợp.
- **Đề xuất:** Thêm Xem giờ trống; với dịch vụ đã chọn hợp lệ đi thẳng tới ngày/giờ, vẫn cho đổi/thêm dịch vụ.
- **Nghiệm thu:** Không bắt đăng nhập để xem; thời lượng và dịch vụ luôn đi cùng lịch trống.
- **Nguồn:** [frontend/src/app/[tenant_slug]/page.tsx:150](../frontend/src/app/[tenant_slug]/page.tsx#L150); [frontend/src/app/[tenant_slug]/book/page.tsx:48](../frontend/src/app/[tenant_slug]/book/page.tsx#L48); [frontend/src/app/[tenant_slug]/book/page.tsx:77](../frontend/src/app/[tenant_slug]/book/page.tsx#L77).

### KH-02 · P1 · Tìm ngày gần nhất còn chỗ

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Khi hết giờ, màn hình yêu cầu chọn ngày tiếp theo; chưa tự gợi ngày còn chỗ.
- **Ảnh hưởng:** Khách phải dò từng ngày.
- **Đề xuất:** Hôm nay/Ngày mai và Tìm giờ gần nhất trong khoảng hữu hạn; tùy chọn buổi sáng/chiều nếu hữu ích.
- **Nghiệm thu:** Phân biệt hết chỗ và lỗi tải; không gửi truy vấn không giới hạn; chọn lại giờ khi có xung đột.
- **Nguồn:** [frontend/src/app/[tenant_slug]/book/page.tsx:471](../frontend/src/app/[tenant_slug]/book/page.tsx#L471); [frontend/src/app/[tenant_slug]/book/page.tsx:532](../frontend/src/app/[tenant_slug]/book/page.tsx#L532).

### KH-03 · P1 · Ưu tiên ngày/giờ, thu gọn chọn nhân viên

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Bước 2 trình bày lựa chọn tự sắp xếp và danh sách nhân viên trước ngày/giờ.
- **Ảnh hưởng:** Khách không có người quen phải đọc và cuộn qua lựa chọn ít cần thiết.
- **Đề xuất:** Giữ mặc định Spa sắp xếp; đưa ngày/giờ lên trước, mở Chọn nhân viên quen khi cần.
- **Nghiệm thu:** Đổi nhân viên làm mới giờ trống và bỏ slot không còn hợp lệ; không tự chọn slot đầu.
- **Nguồn:** [frontend/src/app/[tenant_slug]/book/page.tsx:385](../frontend/src/app/[tenant_slug]/book/page.tsx#L385); [frontend/src/app/[tenant_slug]/book/page.tsx:466](../frontend/src/app/[tenant_slug]/book/page.tsx#L466).

### KH-04 · P1 · Đặt buổi tiếp theo từ thẻ nhanh hơn

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Thẻ đã có nút Dùng 1 buổi trong thẻ và link service_id/package_id nhưng vẫn vào bước chọn dịch vụ.
- **Ảnh hưởng:** Chọn lại bước app đã biết.
- **Đề xuất:** Đưa thẳng tới giờ trống với thẻ hợp lệ, hiển thị thẻ đang dùng; cho quay lại đổi dịch vụ.
- **Nghiệm thu:** Kiểm tra quyền sở hữu/hạn/số buổi; không tự chọn giờ hoặc tự đặt lịch.
- **Nguồn:** [frontend/src/app/[tenant_slug]/profile/page.tsx:232](../frontend/src/app/[tenant_slug]/profile/page.tsx#L232); [frontend/src/app/[tenant_slug]/book/page.tsx:77](../frontend/src/app/[tenant_slug]/book/page.tsx#L77).

### KH-05 · P1 · Đăng nhập xong quay về việc đang làm

- **Loại:** Sai lệch luồng xác định từ code.
- **Hiện trạng:** Trang login/register luôn router.push tới /book; trang lịch và hồ sơ có link đăng nhập không giữ đích.
- **Ảnh hưởng:** Khách muốn xem lịch hoặc thẻ lại bị đưa sang tạo lịch mới.
- **Đề xuất:** Giữ returnTo nội bộ hợp lệ theo chi nhánh; quay đúng trang và lịch được mở từ thông báo.
- **Nghiệm thu:** Kiểm thử đăng nhập từ lịch, thẻ và deep link; chặn open redirect và không đặt thông tin nhạy cảm trong URL.
- **Nguồn:** [frontend/src/app/[tenant_slug]/login/page.tsx:45](../frontend/src/app/[tenant_slug]/login/page.tsx#L45); [frontend/src/app/[tenant_slug]/register/page.tsx:47](../frontend/src/app/[tenant_slug]/register/page.tsx#L47); [frontend/src/app/[tenant_slug]/appointments/page.tsx:212](../frontend/src/app/[tenant_slug]/appointments/page.tsx#L212); [frontend/src/app/[tenant_slug]/profile/page.tsx:70](../frontend/src/app/[tenant_slug]/profile/page.tsx#L70).

### KH-06 · P1 · Xác nhận trước khi hủy lịch

- **Loại:** Rủi ro thao tác.
- **Hiện trạng:** Nút hủy gọi handleCancel, hàm gửi API ngay; chưa có bước xác nhận.
- **Ảnh hưởng:** Một lần chạm nhầm có thể mất giờ đã đặt.
- **Đề xuất:** Dialog ngắn nêu dịch vụ/ngày/giờ, Giữ lịch và Xác nhận hủy; sau thành công thông báo rõ.
- **Nghiệm thu:** Bấm Giữ lịch không gửi mutation; chống gửi lặp; giải thích liên hệ spa khi đã sát giờ.
- **Nguồn:** [frontend/src/app/[tenant_slug]/appointments/page.tsx:131](../frontend/src/app/[tenant_slug]/appointments/page.tsx#L131); [frontend/src/app/[tenant_slug]/appointments/page.tsx:415](../frontend/src/app/[tenant_slug]/appointments/page.tsx#L415).

### KH-07 · P1 · Quên mật khẩu và kích hoạt tài khoản khách tại quầy

- **Loại:** Cần thiết kế danh tính/API.
- **Hiện trạng:** Login không có luồng quên mật khẩu; POST customers có thể tạo mật khẩu ngẫu nhiên khi không nhập.
- **Ảnh hưởng:** Khách đã có hồ sơ/thẻ có thể không biết cách đăng nhập; đăng ký lại gặp trùng SĐT.
- **Đề xuất:** Thiết kế nhận/kích hoạt tài khoản và khôi phục có xác minh; trước mắt cung cấp hướng dẫn liên hệ spa rõ ràng.
- **Nghiệm thu:** Không yêu cầu chủ gửi mật khẩu dùng chung; không tạo hồ sơ trùng hoặc gộp SĐT xuyên chi nhánh.
- **Nguồn:** [frontend/src/app/[tenant_slug]/login/page.tsx:96](../frontend/src/app/[tenant_slug]/login/page.tsx#L96); [frontend/src/app/(admin)/admin/customers/page.tsx:632](../frontend/src/app/(admin)/admin/customers/page.tsx#L632).

### KH-08 · P2 · Nhận diện chi nhánh bằng địa chỉ và liên hệ

- **Loại:** Cần dữ liệu chi nhánh/API.
- **Hiện trạng:** Danh sách chi nhánh dùng id/name/slug; header khách có tên và giờ mở cửa.
- **Ảnh hưởng:** Khách mới khó biết cơ sở nào gần mình hoặc liên hệ khi cần đổi sát giờ.
- **Đề xuất:** Bổ sung địa chỉ, số liên hệ, đường đi và chọn lại chi nhánh có chủ ý.
- **Nghiệm thu:** Chi nhánh hiện rõ trước xác nhận; không ngụ ý thẻ/tài khoản khách dùng chung giữa chi nhánh.
- **Nguồn:** [frontend/src/app/page.tsx:7](../frontend/src/app/page.tsx#L7); [frontend/src/components/customer/customer-shell.tsx:135](../frontend/src/components/customer/customer-shell.tsx#L135).

### KH-09 · P2 · Tìm dịch vụ và hiểu lựa chọn liệu trình

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Catalog có lọc tất cả/lẻ/liệu trình, chưa có tìm kiếm tên; giao diện dùng giá dịch vụ/gói và thời lượng buổi.
- **Ảnh hưởng:** Danh mục dài khó tìm; khách cần biết đang đặt một buổi hay đăng ký gói.
- **Đề xuất:** Thêm tìm tên khi danh mục đủ lớn; thống nhất nhãn giá cả gói, thời lượng mỗi buổi và điều kiện dùng thẻ theo nghiệp vụ hiện hành.
- **Nghiệm thu:** Demo khách mới chọn gói và khách có thẻ cho kết quả tiền/buổi đúng; không hứa thanh toán online nếu chưa có.
- **Nguồn:** [frontend/src/app/[tenant_slug]/page.tsx:19](../frontend/src/app/[tenant_slug]/page.tsx#L19); [frontend/src/app/[tenant_slug]/book/page.tsx:126](../frontend/src/app/[tenant_slug]/book/page.tsx#L126); [frontend/src/app/[tenant_slug]/book/page.tsx:634](../frontend/src/app/[tenant_slug]/book/page.tsx#L634).

### KH-10 · P2 · Sau đặt lịch biết lịch nào vừa tạo và bước tiếp theo

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Tạo thành công chuyển tới appointments?booked=1, không mang ID lịch vừa tạo.
- **Ảnh hưởng:** Khách có nhiều lịch phải tự tìm lại; cần phân biệt đã gửi yêu cầu và spa đã xác nhận.
- **Đề xuất:** Nổi bật chính lịch vừa tạo, trạng thái hiện tại, hướng dẫn tiếp theo; cân nhắc thêm vào lịch cá nhân.
- **Nghiệm thu:** Dùng booking ID trả về, kiểm tra quyền khi mở; không báo Đã xác nhận nếu lịch còn chờ.
- **Nguồn:** [frontend/src/app/[tenant_slug]/book/page.tsx:202](../frontend/src/app/[tenant_slug]/book/page.tsx#L202); [frontend/src/app/[tenant_slug]/appointments/page.tsx:227](../frontend/src/app/[tenant_slug]/appointments/page.tsx#L227).

### KH-11 · P2 · Tự kiểm tra hồ sơ và lịch sử từng buổi

- **Loại:** Đề xuất bổ sung/API.
- **Hiện trạng:** Profile hiển thị tên/SĐT, đăng xuất và thẻ; chưa có sửa hồ sơ hay lịch sử dùng theo từng thẻ trong màn này.
- **Ảnh hưởng:** Khách phải hỏi spa để sửa tên hoặc đối chiếu một buổi đã trừ.
- **Đề xuất:** Cho sửa trường được phép; xem các buổi đã dùng/đã đặt gắn với thẻ; thay SĐT cần xác minh riêng.
- **Nghiệm thu:** Lịch sử đọc dữ liệu nghiệp vụ thật, không suy diễn chỉ từ bộ đếm; không thay định danh bằng form hồ sơ đơn giản.
- **Nguồn:** [frontend/src/app/[tenant_slug]/profile/page.tsx:92](../frontend/src/app/[tenant_slug]/profile/page.tsx#L92); [frontend/src/app/[tenant_slug]/profile/page.tsx:164](../frontend/src/app/[tenant_slug]/profile/page.tsx#L164).

### KH-12 · P2 · Có lối xử lý khi không thể đặt/đổi lịch

- **Loại:** UX + mở rộng tùy pilot.
- **Hiện trạng:** Hết chỗ yêu cầu chọn ngày khác; đổi/hủy bị giới hạn trước giờ hẹn; chưa có thông tin liên hệ trong luồng.
- **Ảnh hưởng:** Khách bị dừng mà không có cách tiếp tục phù hợp.
- **Đề xuất:** Gợi ngày khác, bỏ ưu tiên nhân viên nếu khách đồng ý, hoặc liên hệ chi nhánh. Danh sách chờ chỉ làm khi spa có quy trình phản hồi.
- **Nghiệm thu:** Không nới quy định hủy/đổi; luôn có hướng đi phù hợp và không tự gọi/gửi tin thay khách.
- **Nguồn:** [frontend/src/app/[tenant_slug]/book/page.tsx:532](../frontend/src/app/[tenant_slug]/book/page.tsx#L532); [frontend/src/app/[tenant_slug]/appointments/page.tsx:231](../frontend/src/app/[tenant_slug]/appointments/page.tsx#L231).

## Dùng chung

### DC-01 · P1 · Dọn hết câu chữ kỹ thuật còn sót

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Còn is_package = true, Available Slots, Day-off, Active, COMPLETED, Asia/Ho_Chi_Minh, Theme Color và mã chống lặp trong nội dung hiển thị.
- **Ảnh hưởng:** Làm người dùng phải hiểu cách lập trình thay vì công việc.
- **Đề xuất:** Thay bằng gói liệu trình, giờ trống, nghỉ hằng tuần, đang làm việc, đã hoàn thành, giờ Việt Nam, màu thương hiệu; mô tả kết quả chưa rõ bằng việc cần làm.
- **Nghiệm thu:** Rà từng màn kể cả lỗi/empty state; giữ giải thích nghiệp vụ cần thiết về tiền/thẻ, bỏ chi tiết kỹ thuật.
- **Nguồn:** [frontend/src/app/(admin)/admin/customers/page.tsx:672](../frontend/src/app/(admin)/admin/customers/page.tsx#L672); [frontend/src/app/(admin)/admin/staff/page.tsx:315](../frontend/src/app/(admin)/admin/staff/page.tsx#L315); [frontend/src/app/(admin)/admin/staff/page.tsx:364](../frontend/src/app/(admin)/admin/staff/page.tsx#L364); [frontend/src/app/(admin)/admin/reports/page.tsx:92](../frontend/src/app/(admin)/admin/reports/page.tsx#L92); [frontend/src/app/(admin)/admin/settings/page.tsx:156](../frontend/src/app/(admin)/admin/settings/page.tsx#L156); [frontend/src/app/(admin)/admin/bookings/page.tsx:1156](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1156).

### DC-02 · P1 · Thông báo mở đúng lịch liên quan

- **Loại:** Cải thiện UX.
- **Hiện trạng:** Hai bell hiển thị nội dung và thao tác đã đọc; chưa có điều hướng trực tiếp tới lịch trong phần render hiện tại.
- **Ảnh hưởng:** Người dùng phải đóng thông báo rồi tìm lịch thủ công.
- **Đề xuất:** Thêm Xem lịch hẹn mở đúng chi tiết; xử lý lịch đã hủy/đổi quyền/khác chi nhánh bằng thông báo dễ hiểu.
- **Nghiệm thu:** Không tiết lộ dữ liệu qua deep link; không tự đổi chi nhánh khi còn form hoặc giao dịch dang dở.
- **Nguồn:** [frontend/src/components/admin/notification-bell.tsx:210](../frontend/src/components/admin/notification-bell.tsx#L210); [frontend/src/components/customer/customer-notification-bell.tsx:211](../frontend/src/components/customer/customer-notification-bell.tsx#L211).

### DC-03 · P1 · Trạng thái bật thông báo dễ tìm và có hướng dẫn

- **Loại:** UX + nghiệm thu thiết bị.
- **Hiện trạng:** Cài đặt thiết bị nằm trong bell, chỉ hiện khi pushSupported; trường hợp không hỗ trợ thiếu điểm hướng dẫn tại đó.
- **Ảnh hưởng:** Người dùng không biết vì sao không nhận được thông báo.
- **Đề xuất:** Đưa trạng thái nhận thông báo vào vị trí dễ tìm; giải thích chưa bật/bị chặn/chưa hỗ trợ; chỉ xin quyền sau hành động có chủ ý.
- **Nghiệm thu:** Kiểm chứng thiết bị thật/HTTPS; không coi bật nút thành công là bảo đảm mọi Push được nhận.
- **Nguồn:** [frontend/src/components/admin/notification-bell.tsx:166](../frontend/src/components/admin/notification-bell.tsx#L166); [frontend/src/components/customer/customer-notification-bell.tsx:168](../frontend/src/components/customer/customer-notification-bell.tsx#L168); [frontend/src/lib/web-push.ts:81](../frontend/src/lib/web-push.ts#L81).

### DC-04 · P1 · Biết dữ liệu có mới và xử lý mạng yếu

- **Loại:** Đề xuất + cần kiểm thử mạng.
- **Hiện trạng:** Lịch có nút làm mới; bell dùng feed riêng. Lịch và thông báo không nên được coi luôn đồng bộ chỉ vì có Push.
- **Ảnh hưởng:** Khách/nhân viên có thể nhìn lịch cũ sau khi người khác thay đổi.
- **Đề xuất:** Hiển thị đang cập nhật/cập nhật lần cuối khi cần, refresh khi quay lại app và cơ chế đồng bộ phù hợp; trạng thái offline rõ.
- **Nghiệm thu:** Response cũ không ghi đè chi nhánh mới; không tự gửi lại mutation; mạng yếu phân biệt chưa biết kết quả với thất bại chắc chắn.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:897](../frontend/src/app/(admin)/admin/bookings/page.tsx#L897); [frontend/src/lib/use-notification-feed.ts:27](../frontend/src/lib/use-notification-feed.ts#L27).

### DC-05 · P1 · Form có nhãn, nút có tên và lỗi đúng chỗ

- **Loại:** Khoảng trống khả năng tiếp cận.
- **Hiện trạng:** Quick-create khách dùng placeholder thay label; nút sửa nhân viên chỉ icon; input giờ ca cần tên truy cập gắn ngày.
- **Ảnh hưởng:** Khó dùng khi nhập rồi mất gợi ý, dùng bàn phím hoặc trình đọc màn hình.
- **Đề xuất:** Label bền vững, aria-label cho icon, lỗi sát field và focus lỗi đầu; bổ sung hiện/ẩn mật khẩu.
- **Nghiệm thu:** Kiểm tra bàn phím/screen reader/zoom 200%; không đánh dấu đạt chỉ bằng kiểm tra source.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:1195](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1195); [frontend/src/app/(admin)/admin/staff/page.tsx:327](../frontend/src/app/(admin)/admin/staff/page.tsx#L327); [frontend/src/app/(admin)/admin/staff/page.tsx:401](../frontend/src/app/(admin)/admin/staff/page.tsx#L401); [frontend/src/app/[tenant_slug]/login/page.tsx:99](../frontend/src/app/[tenant_slug]/login/page.tsx#L99).

### DC-06 · P1 · Chỉ hướng bước tiếp theo khi rỗng, lỗi hoặc mất quyền

- **Loại:** Rà soát nghiệm thu bổ sung.
- **Hiện trạng:** Đã có nhiều retry/guard; vẫn cần rà theo ngữ cảnh: chưa có dịch vụ/ca, không có lịch theo bộ lọc, không đủ quyền.
- **Ảnh hưởng:** Người dùng có thể hiểu lỗi tải là không có dữ liệu hoặc không biết gỡ bộ lọc.
- **Đề xuất:** Mỗi trạng thái nêu đúng nguyên nhân và một hành động chính; lỗi cần thông tin nào thì chỉ khóa thao tác phụ thuộc.
- **Nghiệm thu:** Kiểm thử lỗi từng nguồn độc lập, danh sách rỗng, phân trang và mất quyền; không hiển thị dữ liệu cũ như kết quả mới.
- **Nguồn:** [frontend/src/app/(admin)/admin/bookings/page.tsx:1020](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1020); [frontend/src/app/(admin)/admin/bookings/page.tsx:1033](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1033); [frontend/src/app/(admin)/admin/bookings/page.tsx:1071](../frontend/src/app/(admin)/admin/bookings/page.tsx#L1071).

### DC-07 · P1 · Đo trải nghiệm thật của cả ba nhóm

- **Loại:** Cần nghiệm thu thực tế.
- **Hiện trạng:** PROGRESS còn T12/QA-04, thiết bị thật và pilot chưa hoàn tất; kết quả tự động trước đây không chứng minh người mới dùng dễ.
- **Ảnh hưởng:** Không biết nút nào khó tìm, bước nào phải nhờ hỗ trợ.
- **Đề xuất:** Pilot nhiệm vụ thực tế với chủ, người trực quầy, kỹ thuật viên và khách; ghi thời gian, lỗi, số lần cần trợ giúp theo nhóm.
- **Nghiệm thu:** Có kết quả từng nhiệm vụ trên Android/iPhone thật và bàn phím ảo; đặt mục tiêu sau baseline, không tự tuyên bố đạt.
- **Nguồn:** [docs/PROGRESS.md:1](../docs/PROGRESS.md#L1).

### DC-08 · P1 · Kết quả lịch và thông báo đáng tin cậy

- **Loại:** Độ tin cậy cần thiết kế/kiểm chứng.
- **Hiện trạng:** PROGRESS ghi BackgroundTasks chưa có durable outbox; khách đặt lịch xử lý lỗi chung và 409, chưa có màn phục hồi như manual batch.
- **Ảnh hưởng:** Mất phản hồi có thể khiến người dùng không biết đã đặt chưa; thông báo có thể bỏ lỡ nếu tiến trình dừng.
- **Đề xuất:** Thiết kế phục hồi kết quả đặt lịch khách và bảo đảm tác vụ thông báo có retry/dedupe; UI cho kiểm tra kết quả trước tạo lại.
- **Nghiệm thu:** Mô phỏng mất response sau commit và restart tác vụ trên QA; một lịch/đúng số buổi/thông báo không nhân đôi; chưa kết luận bug giao dịch nếu chưa tái hiện.
- **Nguồn:** [frontend/src/app/[tenant_slug]/book/page.tsx:202](../frontend/src/app/[tenant_slug]/book/page.tsx#L202); [docs/PROGRESS.md:1](../docs/PROGRESS.md#L1).

## Kịch bản nghiệm thu UX theo vai trò

### Chủ spa

- Spa mới thiết lập dịch vụ/nhân viên/ca và tự tìm được lý do nếu chưa có giờ trống.
- Khách gọi điện hỏi giờ: tìm nhân viên phù hợp, tạo khách hoặc chọn khách cũ, tạo một lịch.
- Khách mua gói: cấp thẻ, ghi nhận tiền đã nhận, đặt buổi đầu; đọc đúng buổi còn có thể đặt.
- Khách đổi nhân viên: đổi người thực hiện và xác định rõ có bàn giao hồ sơ hay không.
- Xem tổng hợp rồi vào đúng chi nhánh để thao tác; không mất form hoặc ghi nhầm chi nhánh.

### Nhân viên

- Đăng nhập biết ngay khách kế tiếp và phân biệt lịch mình làm với khách mình phụ trách.
- Mở thông báo lịch mới đến đúng lịch; trường hợp chỉ xem phải biết ai xử lý tiếp.
- Bắt đầu/hoàn thành đúng quyền; kiểm tra số buổi chỉ trừ một lần.
- Phục vụ thay được bàn giao thông tin phù hợp, không truy cập toàn hồ sơ ngoài quyền.

### Khách

- Khách mới xem dịch vụ và giờ còn trống trước đăng nhập; ngày hết chỗ có lựa chọn tiếp theo.
- Khách có thẻ đặt buổi tiếp theo mà không chọn lại dịch vụ.
- Đăng nhập để xem lịch/thẻ quay về đúng đích; khách được tạo tại quầy có đường kích hoạt rõ.
- Đổi lịch, bấm nhầm Hủy rồi giữ lịch; biết cách liên hệ khi sát giờ.
- Mạng mất sau xác nhận: kiểm tra kết quả mà không tạo lịch trùng.

### Cách ghi nhận

Ghi số người hoàn thành/đã thử, thời gian, thao tác nhầm, số lần cần trợ giúp, bước bỏ cuộc và lời nhận xét theo từng nhiệm vụ. Chưa có baseline nên chưa đặt tỷ lệ cải thiện hoặc khẳng định hoàn thành trong bao nhiêu giây. Thực hiện trên QA riêng khi có mutation/fault injection; pilot dùng dữ liệu được spa cho phép. Tôn trọng chỉ thị không tạo file log/ảnh/proof; tài liệu này là ghi chú review được PO yêu cầu.

## Những việc không tự mở rộng trong đợt UX

Không tự gộp tài khoản/hồ sơ giữa chi nhánh, mở quyền nhân viên, thêm thu ngân toàn quyền, thay chính sách hủy, xây kế toán/kho/lương hoàn chỉnh hoặc coi lịch trống là cam kết giữ chỗ. Các tính năng nhắc lịch tự động/danh sách chờ/ca ngoại lệ cần chốt quy trình và dữ liệu trước. API luôn kiểm tra lại lúc xác nhận.

## Cập nhật triển khai — 21/10/2026

PO chỉ thị “ok tiến hành update đi”. Đợt hiện tại tập trung các cải thiện có thể triển khai bằng API hiện hành. Không coi toàn bộ 40 mục đã hoàn thành.

**Quyết định NV-02:** PO chọn “Chỉ xem lịch; chủ spa hoặc người phụ trách xác nhận trạng thái”. Giữ can_manage và quyền backend hiện hành, thêm hướng dẫn trong chi tiết lịch được giao. NV-07 không tự mở ghi chú sức khỏe; NV-08 không tự tạo quyền lễ tân/thu ngân.

### Đã triển khai và kiểm chứng trong đợt UX cốt lõi

- KH-01/04: link từ dịch vụ hoặc thẻ hợp lệ mở bước chọn giờ, không tự chọn slot; bước quay lại giữ lựa chọn. Không reset draft khi public tenant refresh.
- KH-02/03: Hôm nay/Ngày mai, tìm ngày có giờ trong tối đa 7 ngày kế tiếp; hủy kết quả muộn theo scope, dừng khi lỗi. Chọn nhân viên quen nằm trong phần mở rộng sau giờ trống.
- KH-05: returnTo chỉ chấp nhận màn khách hợp lệ của cùng chi nhánh; login/register quay lại lịch hoặc thẻ; không nhận URL ngoài/nhánh khác.
- KH-10 (một phần): sau đặt lịch mở tóm tắt đúng booking ID vừa tạo và trạng thái thực; sau hủy/dời cập nhật lại tóm tắt. Chưa thêm lịch cá nhân.
- KH-06: hủy cần xác nhận, có Giữ lịch, chặn nhấn lặp và kiểm tra identity sau await.
- KH-09 (một phần): tìm tên dịch vụ, CTA Xem giờ trống. Chưa nghiệm thu lại toàn bộ cách khách hiểu giá gói.
- CS-02: chủ tra giờ theo dịch vụ/ngày/nhân viên, thấy tên người còn giờ, chọn giờ để mở tạo lịch; không suy lịch trống từ booking list phân trang.
- CS-04 (một phần): chọn trực tiếp kết quả khách theo tên/SĐT thay dropdown thứ hai, không tự chọn khách đầu. Giữ tìm kiếm server và tải thêm; chưa có combobox tự tìm khi gõ.
- CS-01 (một phần): tổng quan chi nhánh thêm tối đa 5 lịch chờ xác nhận và 5 đã xác nhận, mở đúng chi tiết hoặc danh sách theo ngày/trạng thái. Không thêm thao tác ghi từ tổng hợp; chưa có danh sách khoản cần thu trực tiếp trên dashboard.
- NV-05 (một phần): nhân viên tạo lịch mặc định chọn chính mình thực hiện; vẫn giữ lựa chọn sắp xếp theo quyền/API hiện hành.
- NV-01: STAFF mặc định Lịch tôi thực hiện; tùy chọn xem cả lịch khách phụ trách và được giao. NV-02 giữ quyền chỉ đọc theo PO; NV-03 phân biệt người thực hiện với phụ trách hồ sơ; NV-04 nút dùng động từ theo công việc.
- CS-08 (một phần): nhãn Nghỉ hằng tuần; sao chép giờ Thứ 2 cho cả tuần trong draft, giữ ngày nghỉ, phải kiểm tra rồi Lưu. Chưa có nghỉ theo ngày cụ thể/ca tách.
- CS-10 (một phần): kỳ báo cáo Hôm nay/Tuần này/Tháng này, giữ cách tính tiền và hoa hồng ước tính.
- DC-01: dọn các câu kỹ thuật được chỉ ra trong review. DC-02: nút Xem lịch hẹn từ bell, đọc đúng lịch qua API detail và lỗi khi mất quyền; bảo vệ công việc quản trị dang dở trước điều hướng.
- DC-03/DC-05 (một phần): hướng dẫn trường hợp không hỗ trợ Push; hiện/ẩn mật khẩu ở login/wizard; tên truy cập cho nhập khách, sửa nhân viên và giờ ca. KH-07 mới có hướng dẫn liên hệ, chưa có khôi phục/kích hoạt tài khoản có xác minh.

### Còn trong backlog

CS-03/05/06/07/09/11/12, phần còn lại CS-01/04/08/10; NV-06/07/08 và phần còn lại NV-05; KH-07/08/11/12 và phần còn lại KH-10 và phần còn lại KH-09; DC-04/06/07/08 và nghiệm thu đầy đủ DC-03/05. Các mục này cần thêm thiết kế/API/nghiệp vụ hoặc môi trường/thiết bị/pilot; không đánh dấu hoàn thành bằng thay câu chữ. Không triển khai upload ảnh, nghỉ theo ngày, phục hồi mật khẩu hay outbox dưới dạng giả lập frontend.

Các mốc file:dòng ở phần review là baseline trước sửa, có thể xê dịch sau cập nhật. Kết quả QA được ghi ở PROGRESS sau khi runner kết thúc.

### Kết quả QA của đợt UX cốt lõi

Production QA `185afa1f-5534-43bb-9bb7-4712d4e99fa9`: build/strict TypeScript PASS; **78/78 E2E PASS (446.54s)**, không skip/xfail/setup error. Có 18 ca mới trong test_role_ux_updates.py và các hồi quy wizard, hủy/thẻ, phân trang/response muộn, thông báo/quyền chỉ xem, modal/keyboard/mobile, manual batch, calendar và client PWA/tenant isolation. Đây là bộ chọn lọc, chưa phải full features hoặc nghiệm thu thiết bị thật/pilot.


## Đợt hoàn thiện backlog theo PO — 21/10/2026

Mục này cập nhật trạng thái sau baseline và đợt cốt lõi phía trên. PO yêu cầu hoàn thiện phần còn lại. Code/API đã được bổ sung; đang chạy nghiệm thu toàn bộ, kết quả cuối xem PROGRESS. Không dùng chữ hoàn thành cho kiểm chứng thiết bị/pilot chưa diễn ra.

### Chủ spa: phần triển khai

- CS-01: tổng quan có lịch chờ, lịch sắp tới theo ngày và khoản cần thu hiện tại (mọi ngày); các liên kết giữ khách/chi nhánh. Tổng hợp tiếp tục chỉ đọc.
- CS-02: tra giờ từ availability theo dịch vụ/ngày/người thực hiện, không suy từ lịch đã tải.
- CS-03: một buổi mặc định; nhiều buổi nằm trong tùy chọn mở rộng; footer tóm tắt khách, số buổi, dịch vụ, giờ đầu và giá trị dự kiến/chưa thu; giữ biên nhận batch và chống gửi trùng.
- CS-04: tự tìm sau khi gõ 300 ms, chọn trực tiếp tên/SĐT, Enter và phím lên/xuống; server tìm kiếm/phân trang, kết quả cũ không thay lựa chọn.
- CS-05: hồ sơ có Đặt lịch cho khách, Xem khoản cần thu, lịch sắp tới/lịch sử gần nhất. URL chỉ chứa UUID; API kiểm tra lại quyền, khách ngoài trang CRM đầu vẫn được nạp đúng theo ID.
- CS-06: cùng dữ liệu số buổi Đã dùng/Đã đặt trước/Có thể đặt giữa CRM, đặt tại quầy và thẻ khách; không đổi nghiệp vụ trừ buổi.
- CS-07: checklist dữ liệu thật cho liên hệ/giờ mở cửa, dịch vụ, nhân viên/ca, kiểm tra giờ trống và chia sẻ link; lỗi tải có retry. Không tự khẳng định có thể nhận mọi lịch chỉ vì đã có ca tuần.
- CS-08: sao chép ca tuần trong draft; API ngoại lệ ngày riêng, khóa cùng nhân viên với booking. Nếu ảnh hưởng lịch đã nhận thì báo số lịch/409, chưa áp dụng; chủ tự dời/hủy lịch trước. Chưa mở rộng ca tách, do đề xuất ban đầu chỉ cân nhắc theo pilot.
- CS-09: tạo chi nhánh có bước tiếp theo và nút chuyển sang chi nhánh mới để thiết lập; không sao chép khách/thẻ/cấu hình hoặc gộp dữ liệu. Sao chép cấu hình có chọn lọc chưa được PO chọn nên không thuộc đợt này.
- CS-10: preset kỳ báo cáo, nhóm rõ số liệu theo ngày và hiện tại, khoản thực thu/giá trị dịch vụ, hoa hồng ước tính.
- CS-11: chọn ảnh PNG có preview/giới hạn và kiểm tra server, lưu cùng metadata; màu do triển khai quản lý chỉ hiển thị mẫu màu/hướng liên hệ.
- CS-12: form quản lý tài khoản chung có xác minh mật khẩu; chủ chỉ sửa nhân viên nếu làm chủ toàn bộ chi nhánh liên quan. Đổi nguyên tử, thu hồi phiên cũ, không gộp tài khoản trùng số.

### Nhân viên: phần triển khai và quyết định

- NV-01: mặc định lịch mình thực hiện, phân biệt khách phụ trách; không mở quyền đọc mới.
- NV-02: đóng theo lựa chọn PO — người chỉ được giao lịch tiếp tục chỉ xem; chủ/người phụ trách xác nhận trạng thái.
- NV-03/04: nhãn người thực hiện/người phụ trách phân biệt, nút hành động theo việc và tác động thẻ.
- NV-05: mặc định chính mình khi nhân viên tạo lịch; xác minh API hiện hành vẫn cho spa sắp xếp người rảnh nên giữ lựa chọn này, không tự thu hẹp hoặc mở rộng quyền.
- NV-06: Ca làm của tôi chỉ đọc ca tuần và ngoại lệ ngày của chính tài khoản/chi nhánh, lỗi có retry.
- NV-07: ghi chú bàn giao riêng lịch theo PO; chỉ chủ/người phụ trách ghi, KTV được giao đọc, không tự sao chép hồ sơ sức khỏe và không gửi note qua Push.
- NV-08: đóng theo quyết định PO — giữ quyền hiện hành, chưa thêm lễ tân/thu ngân. Không tính việc tạo một role mới là điều kiện hoàn tất.

### Khách: phần triển khai

- KH-01..04: đi từ dịch vụ/thẻ sang giờ trống, ngày gần nhất trong phạm vi 7 ngày, giờ trước/chọn nhân viên sau; không tự chọn slot.
- KH-05/06: quay đúng trang sau đăng nhập cùng chi nhánh, chặn URL ngoài; hủy có xác nhận/giữ lịch.
- KH-07: spa xác minh rồi chủ cấp liên kết một lần/hạn 30 phút; khách tự đặt mật khẩu, không tạo hồ sơ trùng, không mật khẩu dùng chung. Cấp mới thu hồi link cũ và đổi mật khẩu thu hồi phiên cũ. Token chỉ được đưa vào fragment và gỡ khỏi URL sau khi đọc.
- KH-08/12: địa chỉ, gọi spa và đường đi từ thông tin chi nhánh, giữ lựa chọn tìm ngày/đổi ưu tiên người thực hiện. Không tự gọi, nới chính sách đổi/hủy hoặc tạo danh sách chờ không có quy trình.
- KH-09: tìm tên, giá cả gói và thời lượng mỗi buổi; chưa hứa thanh toán online.
- KH-10: mở đúng ID lịch đã tạo/trạng thái thật; tải lịch cá nhân có cảnh báo tệp không tự cập nhật khi đổi/hủy.
- KH-11: sửa họ tên, đổi mật khẩu có xác minh; lịch sử từng thẻ đọc booking thực, gồm trạng thái giữ chỗ/hoàn thành/hủy. SĐT vẫn cần spa xác minh riêng.

### Dùng chung

- DC-01/02: câu chữ nghiệp vụ, bell mở đúng lịch và kiểm tra quyền; Push mở cửa sổ riêng để giữ form đang nhập.
- DC-03: đã có trạng thái bật/chưa bật/bị chặn/không hỗ trợ và hướng dẫn sau thao tác chủ ý. **Chưa nghiệm thu Push trên thiết bị Android/iPhone thật qua HTTPS.**
- DC-04: offline rõ; làm mới GET khi quay lại/focus/online ở lịch, thời điểm cập nhật; không tự gửi lại mutation. Chi tiết khách mở từ deep link được nạp lại khi danh sách cập nhật.
- DC-05: nhãn bền vững, tên nút, hiện/ẩn mật khẩu, bàn phím/zoom và bố cục được kiểm thử tự động theo các ca phù hợp. **Chưa nghiệm thu trình đọc màn hình/bàn phím ảo trên thiết bị thật.**
- DC-06: lỗi từng nguồn có retry, trạng thái rỗng có hướng tiếp tục, không nhầm lỗi thành hết dữ liệu; kết quả phân trang/response muộn giữ kiểm tra phạm vi. Đang đối chiếu bộ E2E đầy đủ.
- DC-07: **chưa hoàn tất pilot người thật.** Bộ nhiệm vụ và cách ghi nhận đã có bên dưới; không tự tạo số liệu hoàn thành/thời gian hay đánh dấu QA-04/T12 đạt từ E2E.
- DC-08: customer booking request có UUID/biên nhận giao dịch, kiểm tra kết quả sau mất response/reload; sự kiện outbox và job Push lưu DB, retry/dedupe in-app, kiểm tra lại quyền trước Push. Không cam kết provider giao đúng một lần nếu mất xác nhận mạng.

### Ba mục cần nghiệm thu ngoài automation

DC-03, DC-05 và DC-07 chưa được gọi là hoàn thành tiêu chí nghiệm thu. Các phần code tương ứng đã làm hoặc đã có kế hoạch pilot; cần thiết bị thật và người đại diện ba nhóm. Những ý tưởng có điều kiện như ca tách, SMS OTP, lễ tân/thu ngân, chờ lịch và sao chép cấu hình không được tự thêm ngoài quyết định PO.


### Kết quả nghiệm thu tự động cuối đợt hoàn thiện

Toàn bộ E2E features **257/257 PASS (1089.36s)**, production QA 939fc716-e9f1-4df5-a349-21d2bdb52590; backend **116/116 PASS (298.97s)**; frontend build/strict TypeScript PASS. Nhóm 15 ca mới kiểm tra liên hệ/setup, lỗi/retry, ca cá nhân/ngoại lệ ngày, bàn giao chỉ đọc, recovery một lần, sửa họ tên, lịch sử thẻ, link CRM, offline, mất phản hồi/reload, lịch cá nhân, phản hồi mật khẩu muộn, logo chỉ lưu khi xác nhận và giới hạn số buổi/giá gói.

Các mục có phần triển khai trong phạm vi đã được kiểm thử; **37 mục đã xử lý phần triển khai/quyết định nghiệp vụ, 3 mục DC-03/DC-05/DC-07 còn nghiệm thu thực tế** như mô tả phía trên. Không ghi 40/40 đạt và không suy pilot hay Push vật lý từ E2E. Bản local đã cập nhật, giữ nguyên bộ tài khoản/dữ liệu để PO kiểm tra; hướng dẫn tại LOCAL_REVIEW_DATA.md.
