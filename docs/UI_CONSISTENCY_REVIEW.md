# Rà soát tính đồng nhất giao diện — 21/10/2026

## Phạm vi và cách đọc

Rà soát source 60 file TSX/CSS, gồm 24 file page và các thành phần dùng chung cho chủ spa, nhân viên, khách và Operator; đối chiếu Tailwind, API_CONTRACT và lịch sử kiểm chứng. Trọng tâm là hiển thị lặp, CSS, bố cục, nút/liên kết và phản hồi trạng thái. Đây không phải audit lại toàn bộ backend/bảo mật/nghiệp vụ.

Các nhận xét thẩm mỹ được ghi là vấn đề thiết kế; không coi mọi liên kết gạch chân hoặc mọi chữ nhỏ là lỗi chức năng. Không sửa source sản phẩm trong lượt review này. Kiểm thử chỉ sử dụng QA riêng, không khởi động frontend local, không ghi log/ảnh/proof.

## [CRITICAL]

Chưa xác nhận lỗi mức CRITICAL trong phạm vi rà soát này. Không suy ra toàn bộ ứng dụng không có lỗi.

## [WARNING] — Các mục cần cải thiện

### UI-01 · P1 · Phần công việc phía dưới tổng quan vẫn có trình bày thô

Nguồn: frontend/src/components/admin/dashboard-work.tsx:25–35.

Hai danh sách lịch dùng dòng liên kết gạch chân; giờ, tên khách và nhân viên không có phân cấp rõ. Link xem toàn bộ tiếp tục giống link nội dung. Khối khoản cần thu dùng border nhưng thiếu bg-card, khác hai khối lịch bên trên. Trạng thái rỗng chỉ một dòng chữ. Đây là phần chưa được thiết kế lại ở lần sửa SetupGuide trước.

Đề xuất: dùng hàng lịch có giờ nổi bật, khách/nhân viên tách dòng, trạng thái dễ nhận ra; danh sách khoản cần thu tách thông tin và số tiền; footer hành động thống nhất. Nghiệm thu cả có dữ liệu/rỗng/lỗi, tên dài và mobile.

### UI-02 · P1 · Các chỉ số tổng quan và tổng hợp chi nhánh thiếu phân cấp

Nguồn: frontend/src/app/(admin)/admin/dashboard/page.tsx:16–20,54–58.

Chín chỉ số đều gần như cùng trọng lượng thị giác. Bảy ô nhóm ngày trên lưới bốn cột tạo hàng cuối thiếu một ô. Ở chế độ tất cả, mỗi chi nhánh lặp nguyên chín ô: lặp có chủ ý về dữ liệu nhưng rất dài và khó so sánh; không phải lỗi React render trùng.

Đề xuất: ưu tiên lịch hôm nay/thực thu/cần thu, nhóm số liệu bổ sung riêng; tổng hợp dùng hàng so sánh hoặc phần mở rộng theo chi nhánh. Giữ phân biệt số liệu ngày và mọi ngày.

### UI-03 · P1 · Nút chữ dài có nguy cơ tràn trên điện thoại

Nguồn: frontend/src/components/ui/button.tsx:36; frontend/src/app/(admin)/admin/branches/page.tsx:41; frontend/src/app/(admin)/admin/staff/page.tsx:398.

Button mặc định whitespace-nowrap. Các nút “Chuyển sang thiết lập chi nhánh mới” và “Áp dụng giờ Thứ 2 cho các ngày” nằm trong khung có padding, không tự xuống dòng hoặc giới hạn chiều rộng. Đây là nguy cơ được xác định từ source; cần mở đúng trạng thái sau tạo chi nhánh/mở sao chép ca để đo, không khẳng định đã tái hiện chỉ từ trang ban đầu.

Đề xuất: rút gọn nhãn, cho xuống dòng và chiều cao tự động ở mobile; kiểm tra 320 px trong trạng thái mở.

### UI-04 · P1 · Kích thước thao tác mobile chưa đồng nhất

Nguồn: frontend/src/app/[tenant_slug]/page.tsx:162; frontend/src/components/customer/customer-shell.tsx:153; frontend/src/app/[tenant_slug]/appointments/page.tsx:249,357; frontend/src/app/(admin)/admin/customers/page.tsx:707; frontend/src/app/(admin)/admin/bookings/page.tsx:1702.

Một số CTA dùng h-8 (32 px), h-9 (36 px); hai select cấp thẻ/đổi lịch dùng h-9 text-sm cả ở mobile. Trong khi Button/Input dùng chung đã có min-h-11 và text-base cho mobile. Chênh lệch này làm cùng loại thao tác khó chạm hơn ở các luồng phụ; không coi 44 px là điều kiện WCAG tuyệt đối.

Đo thực tế trang dịch vụ khách tại 320 px: nút lọc 28 px, Xem giờ trống 32 px, Đặt lịch hẹn ngay 36 px.

Đề xuất: thống nhất mục tiêu chạm mobile 44 px và cỡ chữ input/select; kiểm tra cả modal, không chỉ trang chính.

### UI-05 · P2 · Có lớp CSS không được cấu hình cho Tailwind hiện hành

Nguồn: frontend/package.json (Tailwind ^3.4.14); frontend/tailwind.config.ts; frontend/src/app/globals.css; ví dụ frontend/src/app/[tenant_slug]/page.tsx:43,79,162 và frontend/src/app/(admin)/admin/bookings/page.tsx:807.

shadow-xs và backdrop-blur-xs được dùng nhiều nơi nhưng không được khai báo mở rộng trong cấu hình/CSS hiện tại. Đã kiểm chứng computed style trong Chromium QA: boxShadow=none và backdropFilter=none khi gắn hai lớp này. Tác động chủ yếu là mất bóng/mờ dự kiến, không phải toàn bộ trang mất CSS.

Đề xuất: dùng utility đúng phiên bản hoặc định nghĩa token dùng chung; không nâng framework chỉ để sửa hiệu ứng nhỏ.

### UI-06 · P2 · Trang chi nhánh và trang chọn chi nhánh công khai chưa đồng bộ nhận diện

Nguồn: frontend/src/app/(admin)/admin/branches/page.tsx:32–34; frontend/src/app/page.tsx:26.

Danh sách hiện là tên + link gạch chân. Trang công khai chưa hiển thị logo; dễ thấy độ lệch so với header/trang dịch vụ đã nâng cấp. Các chi nhánh chưa có nhãn đang chọn hoặc CTA nổi bật tại danh sách quản trị.

Đề xuất: dùng thẻ chi nhánh với tên, liên hệ, logo khi API cung cấp, CTA rõ; đánh dấu chi nhánh hiện tại. Không giả định API danh sách đã trả logo_url.

### UI-07 · P2 · Trang tài khoản và phần chỉnh tài khoản nhân viên quá trải ngang

Nguồn: frontend/src/app/(admin)/admin/account/page.tsx:7; frontend/src/components/credential-form.tsx:25; frontend/src/app/(admin)/admin/staff/page.tsx:468–471.

Form tài khoản không có max-width; phần đổi ca/đổi tài khoản nhân viên nằm bên dưới cả lưới danh sách–chi tiết, nên trải ngang khác khối chi tiết phía trên. Đây là bất nhất bố cục desktop, không phải sai phân quyền.

Đề xuất: giới hạn chiều rộng form đọc/nhập; đặt các phần bổ sung vào đúng cột chi tiết nhân viên hoặc chia tab.

### UI-08 · P2 · Ca làm và ngoại lệ ngày chưa có cách trình bày nhất quán

Nguồn: frontend/src/app/(admin)/admin/work-hours/page.tsx:20–21; frontend/src/components/admin/date-overrides.tsx:38; frontend/src/app/(admin)/admin/reports/page.tsx:254.

Ca tuần là các đoạn p có border, ngoại lệ là p không nền/border và ngày ISO YYYY-MM-DD. Báo cáo cũng có khoảng ngày ISO thô. Cùng một ứng dụng nhưng định dạng ngày và phân biệt ngày nghỉ chưa thống nhất.

Đề xuất: ngày dd/MM/yyyy, nhãn nghỉ/làm rõ, nhóm tuần và ngoại lệ bằng một mẫu thống nhất; nhấn mạnh hôm nay khi phù hợp.

### UI-09 · P2 · Các phần mở rộng mới vẫn dùng disclosure nguyên bản

Nguồn: frontend/src/components/admin/recovery-link.tsx:14; frontend/src/components/customer/profile-editor.tsx:14; frontend/src/components/package-history.tsx:23; frontend/src/components/admin/customer-visits.tsx:18; frontend/src/components/admin/booking-handover.tsx:22.

Recovery/hồ sơ dùng summary mũi tên mặc định; lịch sử buổi là danh sách đoạn văn; lịch gần đây dùng link gạch chân. Các thành phần này đúng chức năng nhưng chưa cùng cách trình bày với SetupGuide mới. Không nên sửa bằng việc thêm icon vào mọi dòng; cần thống nhất tiêu đề, khoảng cách, nền và hành động.

### UI-10 · P2 · Thông báo lỗi/thành công không đồng nhất

Nguồn: frontend/src/components/credential-form.tsx:53; frontend/src/components/customer/profile-editor.tsx:22; frontend/src/components/admin/recovery-link.tsx:30; đối chiếu frontend/src/app/(admin)/admin/settings/page.tsx:116–129.

Một số nơi lỗi và thành công chỉ là p màu chữ mặc định; cài đặt dùng hộp màu riêng. Người dùng khó nhận ra kết quả lưu trên các form mới, nhất là khi nằm cuối màn hình.

Đề xuất: thành phần phản hồi dùng chung, role phù hợp, nội dung dễ hiểu, không chỉ dùng màu; cuộn/focus hợp lý khi lỗi cần chú ý.

### UI-11 · P2 · Câu chữ và tên trang còn thiếu nhất quán

Nguồn: frontend/src/app/(admin)/admin/customers/page.tsx:323; frontend/src/components/admin/admin-shell.tsx (Cấu hình Spa); frontend/src/app/(admin)/admin/settings/page.tsx (Cài đặt spa); frontend/src/app/layout.tsx:11.

Tiêu đề khách còn “CRM”, menu/cài đặt dùng hai tên khác nhau. Metadata mô tả “nhắc lịch tự động” trong khi phần đã triển khai được mô tả là thông báo sự kiện lịch, không nên tạo kỳ vọng về nhắc trước giờ nếu chưa có tác vụ đó.

Đề xuất: bỏ mã thuật ngữ khỏi tiêu đề người dùng, đồng bộ tên điều hướng và lời mô tả đúng tính năng hiện có.

### UI-12 · P2 · Chữ phụ quá nhỏ và mẫu trạng thái rỗng còn rời rạc

Nguồn: frontend/src/app/(admin)/admin/bookings/page.tsx:819,844; frontend/src/app/[tenant_slug]/book/page.tsx:519; frontend/src/components/admin/notification-bell.tsx:234; frontend/src/components/customer/customer-notification-bell.tsx:230; dashboard-work.tsx:29,35.

Có nhiều text 10–11 px cho trạng thái/thời gian và dòng thông báo. Trong khi màn cũ có Card/Badge/empty state, màn mới có nơi chỉ dùng p. Không phải mọi chữ 11 px đều sai; cần ưu tiên tăng cỡ các thông tin dùng để quyết định thao tác.

## [PASSED] và giới hạn

- SetupGuide/DashboardWork hiện có key riêng setup/work; không tìm thấy thêm cặp sibling cùng key tương tự qua đối chiếu source. Các key trùng ở cây con khác nhau không tự là lỗi.
- Dự án có CSS toàn cục, content paths Tailwind bao phủ app/components, Button/Input/Card dùng chung. Không có căn cứ kết luận toàn bộ CSS không tải.
- Dashboard nhóm ngày và mọi ngày là phân biệt nghiệp vụ cần giữ; không xóa chỉ vì trông giống lặp.
- Kiểm thử tự động đo tràn ngang không thay thế đánh giá thẩm mỹ. Không khẳng định đã kiểm tra mọi modal, mọi dữ liệu dài hoặc thiết bị thật.
- Kết quả kiểm chứng mới được bổ sung dưới đây khi hoàn tất. Lượt QA đầu lỗi khởi động backend; lượt production tiếp theo mất phiên console trước khi thu kết quả, không tính là PASS.

## Thứ tự sửa đề xuất

1. UI-01/02: hoàn thiện toàn bộ dashboard, bao gồm phần dưới và chế độ tổng hợp.
2. UI-03/04/05: nút dài, kích thước chạm, utility CSS không hiệu lực.
3. UI-06..10: đồng bộ danh sách, form, ca làm, disclosure và phản hồi trạng thái.
4. UI-11/12: câu chữ và khả năng đọc, cùng một lượt kiểm chứng desktop/mobile.

## Kiểm chứng mới

- Lượt dev QA `c363b638-7f62-4f1a-88a5-568520a87c0b`: **29 ca hồi quy PASS**, 1 ca kiểm kê mới FAIL do locator chọn heading nằm trong details đang đóng trên hồ sơ (259.29s toàn lượt). Đã sửa locator kiểm kê sang main/form; không thay source sản phẩm hoặc nới tiêu chí bố cục. Không gọi lượt này là 30/30 PASS.
- 29 ca gồm 15 màn phụ/thông báo/dashboard, 4 hồi quy lịch (có 1 ca kiểm tra harness giữ lỗi gốc), 10 điều khiển mobile/màu thương hiệu. Đây là dev Chromium, không phải chứng nhận thiết bị thật hoặc production build mới.
- Lượt trước `6551e1db-fa38-4b18-97b2-e183b2fe8ded` dừng collection vì lỗi cú pháp script kiểm kê mới; đã sửa và kiểm tra AST trước chạy lại.
- Kiểm kê sửa lại: **1/1 PASS (88.85s)**, dev QA `e8b9d20a-38f7-4bcb-a6d1-99c41c1c14c2`. Đi qua 25 tổ hợp route/vai trò ở 320 và 1366 px (50 phép đo): không thấy tràn ngang hoặc ID trùng tại thời điểm đo, không có cảnh báo same-key ghi nhận. Đo sau khi main/form xuất hiện, không phải chờ mọi API con xong; không dùng kết quả này để bảo đảm mọi trạng thái dữ liệu. Các route quản trị Operator đã đăng nhập và register-tenant cũ chỉ đối chiếu source trong lượt này.
- Xác nhận CSS shadow-xs/backdrop-blur-xs không có hiệu ứng; các CTA nhỏ phía khách được ghi tại UI-04. Kiểm kê PASS nghĩa script hoàn thành, không có nghĩa 12 vấn đề thiết kế đã được giải quyết.
- Đã dọn QA; không còn listener 3000/3001/3002, không còn container QA trong danh sách đang chạy. diff --check PASS. Chưa sửa sản phẩm; chỉ thêm kiểm kê và báo cáo.

## Triển khai theo PO — 21/10/2026

Các phát hiện phía trên là ảnh chụp trạng thái trước sửa, giữ lại để truy vết. Đã triển khai code cho UI-01..12; đang kiểm chứng QA, chưa coi đây là nghiệm thu thiết bị thật.

- UI-01: hàng lịch có giờ/khách/nhân viên tách biệt; khoản thu có số tiền nổi bật; footer và trạng thái rỗng thống nhất.
- UI-02: hai chỉ số ngày chính, các chỉ số phụ dạng danh sách; số liệu mọi ngày tách riêng. Chi nhánh tổng hợp có tóm tắt và phần mở rộng.
- UI-03/04: Button giới hạn chiều rộng, xuống dòng và chiều cao tự động; CTA/tab/select mobile tối thiểu 44 px cho các vị trí đã nêu.
- UI-05/12: thay shadow-xs/backdrop-blur-xs bằng utility phù hợp; tăng chữ 10–11 px lên 12 px, tăng chữ nhãn form và trạng thái.
- UI-06: thẻ chi nhánh, CTA và dấu nhận diện; admin có logo và nhãn đang làm việc. Public dùng chữ viết tắt vì API danh sách chưa trả logo, không tự fetch thêm mỗi chi nhánh.
- UI-07: form tài khoản giới hạn chiều rộng; phần tài khoản/ngoại lệ ca nhân viên gom về phía chi tiết.
- UI-08: ca tuần dạng thẻ, nhãn nghỉ, ngày dd/MM/yyyy cho ngoại lệ và khoảng ngày báo cáo; không thay giá trị API/input date.
- UI-09/10: mẫu disclosure/action-link/empty-state/feedback dùng chung; áp dụng cho hồ sơ, cấp liên kết, lịch sử, lịch gần đây và bàn giao.
- UI-11: bỏ CRM khỏi tiêu đề khách, menu Cài đặt spa thống nhất, metadata mô tả thông báo cập nhật lịch.

Không thêm quyền, API, migration hoặc thay dữ liệu nghiệp vụ. Chỉ đổi assertion liên quan tên/định dạng ngày trong test; không nới tiêu chí chống tràn, giao dịch hoặc quyền.

- Kiểm chứng cập nhật UI: production QA `33a06faa-75d4-4171-b393-542b4557f15a`, build/strict TypeScript PASS; **102 PASS, 1 FAIL (301.02s)** trong 103 ca. Ca mới đo nút Đặt lịch hẹn ngay còn cao 36 px; đã thêm min-h-11, đang chạy lại ca mới cùng hồi quy điều khiển/mobile/lịch trên production QA. Giữ tiêu chí >=44 px, không nới assertion.

- **Kết quả cuối:** production QA build/strict TypeScript PASS; **16/16 PASS (40.90s)**, run `9256a654-e932-4cb2-86ca-e1c37611b539`. Gồm hai ca mới (nút dài/CTA 44 px và chi nhánh mở rộng), 10 ca điều khiển/mobile và bốn ca bố cục lịch. Ca lỗi ở lượt 103 đã được sửa và kiểm chứng lại; 102 ca PASS trước đó giữ đúng phạm vi, không gọi lượt cuối là full suite 103/103. Không thay backend nên không chạy lại backend suite.
- Hoàn tất triển khai các cải thiện UI-01..12 trong phạm vi đã nêu; chi nhánh public vẫn dùng chữ viết tắt do contract danh sách không có logo. Không xem Chromium QA là nghiệm thu thiết bị thật. diff --check PASS.


## Review sau triển khai 12 nhóm — 21/10/2026

Kết luận: chưa phát hiện CRITICAL trong phạm vi UI được kiểm tra; còn hai WARNING P2 đã tái hiện. Vì vậy trạng thái triển khai UI-01..12 phía trên không đồng nghĩa tất cả tiêu chí đã được nghiệm thu. Không sửa source sản phẩm trong lượt review này.

### [WARNING][P2] UI-10: thông báo lưu hồ sơ khách bị mất khi refresh

- Vị trí: `frontend/src/components/customer/profile-editor.tsx:17`, kết hợp refreshCustomer và Fragment key trong `customer-context.tsx`.
- Sau PATCH thành công, refreshCustomer làm cây con remount; setMessage trên instance cũ không hiển thị. Khách thấy tên mới nhưng khung chỉnh sửa đóng lại và không có xác nhận đã lưu. Đây là vấn đề tồn tại trước đợt đổi giao diện; bổ sung feedback-success chưa giải quyết được.
- QA: sửa họ tên thành công, `success_visible: false`, `editor_open: null`.
- Đề xuất: giữ phản hồi ở nơi không bị remount, hoặc giữ vòng đời form khi chỉ tải lại hồ sơ; vẫn giữ cơ chế xóa state khi đổi danh tính/chi nhánh. Bổ sung assertion thông báo hiện sau lưu.

### [WARNING][P2] UI-09: form cấp liên kết mất khoảng cách

- Vị trí: `frontend/src/components/admin/recovery-link.tsx:14–20`.
- Đổi wrapper từ space-y-2 sang disclosure làm mất khoảng cách giữa các phần tử; disclosure không có gap/space-y. PasswordInput và nút cấp liên kết chạm nhau. Đây là hồi quy bố cục trong đợt cập nhật.
- QA desktop 1366 px đo khoảng cách input–button bằng **0 px**.
- Đề xuất: bọc nội dung form bằng space-y-3 hoặc bổ sung spacing riêng cho component, tránh thay tất cả disclosure ngoài ý muốn.

### [PASSED] Kiểm chứng và giới hạn

- Dev QA riêng `d0820213-2660-4acb-9e13-c916e8012fe3`: 3/3 phép thăm dò hoàn tất (19.05s). Hai phép đầu ghi nhận lỗi nêu trên; PASS chỉ nghĩa script chạy xong, không phải hai hành vi đã đạt.
- Với màu thương hiệu #ffff00, action-link thực tế hiển thị rgb(89,89,0) trên trắng; không xác nhận nghi vấn chữ vàng thiếu tương phản.
- Kết quả production build và hồi quy của lượt triển khai giữ nguyên phạm vi đã ghi phía trên; lượt review này không chạy lại toàn bộ suite hoặc chứng nhận thiết bị thật. Không audit lại backend/RLS/concurrency vì đợt UI không thay các phần đó.
- Frontend local vẫn tắt; không còn listener 3000/3001/3002 hoặc container QA đang chạy. Không ghi ảnh/log/trace.


### Sửa hai WARNING sau review — 21/10/2026

- UI-10: thêm reloadCustomerProfile chỉ tải lại hồ sơ trong cùng phiên đã xác minh, kiểm tra session/request/user/tenant trước khi cập nhật. Form sửa họ tên giữ state và hiển thị xác nhận sau lưu; refreshCustomer khi đổi phiên vẫn giữ cơ chế remount/xóa bản nháp riêng.
- UI-09: bọc nội dung cấp liên kết bằng space-y-3, giữ spacing riêng tại component.
- Chuyển hai phép quan sát thành regression assertion: tên mới tồn tại sau reload, thông báo thành công hiển thị và form còn mở; khoảng cách password–button >=12 px. Đang chạy production QA cùng hồi quy phiên và role experience.

- Kết quả sửa warning: production build/TypeScript PASS; **38/38 ca PASS (106.95s)** trên QA riêng `a3caccde-a19a-4f7f-90a4-8a40ae03168d`: 3 ca UI review (hai regression và một probe màu), 20 ca phiên đăng nhập, 15 ca role experience. Hai WARNING UI-09/UI-10 nêu trên đã sửa và kiểm chứng; không thay backend/API hay dữ liệu local.
