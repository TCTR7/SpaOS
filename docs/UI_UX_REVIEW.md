# Review UI/UX trước pilot

## Review lại phạm vi 29 task — 20/10/2026

### Cập nhật sửa R29-01..05 — 20/10/2026

**ĐÃ SỬA VÀ KIỂM CHỨNG 5/5 phát hiện R29.** Production run `6253fa68-759e-4493-b281-b88b2702a1cb`: build/TypeScript PASS, **74/74 PASS (230.94s)**, không skip/xfail/setup error. Gồm 18 ca mới, 7 thu tiền, 20 phiên, 10 guard đổi branch, 15 màn phụ/mobile và 4 layout (có assertion fault injection). Harness 25/25 PASS. Runner exit 0, 3001 không có listener, không còn container E2E QA. Không ghi log/ảnh/JSON artifact, không đụng server 3000 hoặc DB ứng dụng. QA-04/T12 chưa đóng; kết quả này không phải full features sau sửa hoặc nghiệm thu thiết bị thật.

- R29-01: `web-push.ts` kiểm tra token/session generation trước và sau các bước await khi enable/disable/khôi phục subscription sẵn có. Bell hủy auto-sync khi unmount, truyền trạng thái mounted vào thao tác và dùng ref chặn nhấn lặp. Phiên thay đổi không đăng ký bằng tài khoản mới hoặc hủy subscription của phiên mới; lỗi unsubscribe server được hiển thị, không báo đã tắt thành công khi request lỗi.
- R29-02: dữ liệu Thu tiền gắn theo user/tenant/query/filter/offset, ẩn ngay khi scope đổi, lỗi danh sách tách khỏi trạng thái rỗng và có retry giữ đúng truy vấn. Request generation ngăn response cũ ghi đè sau refresh mutation.
- R29-03: `use-notification-feed.ts` dùng chung hai bell; serialize mark-one/read-all bằng ref, disable nút trong lúc xử lý, vô hiệu GET trước mutation và lấy lại counter/items từ server. GET polling trong mutation không ghi đè, response trước mutation bị bỏ, cleanup có lifetime guard.
- R29-04: regression layout assertion trực tiếp với số đo, bỏ capture trong nhánh lỗi; thêm fault injection bảo đảm AssertionError gốc được giữ nguyên, không tạo artifact. R29-05: CTA tenant 404 dẫn về `/` với nhãn Chọn chi nhánh.
- Thêm `test_review_followups.py`: lỗi query/retry, mark-one/read-all nhấn lặp + GET cũ cho hai role, tenant 404, Push pending permission/register/subscribe, auto-sync/disable chờ lookup và enable/disable hợp lệ. Regression dev cùng layout **20/20 PASS (73.19s)** trước khi thêm hai ca Push hợp lệ. Harness **25/25 PASS (0.197s)**. Production cuối đã kiểm chứng cả hai ca bổ sung và hồi quy liên quan như kết quả trên.
- Hai lượt dev trước chưa nghiệm thu: a5826d9e (1 FAIL, assertion đếm request không tính Strict Mode), 2c21854f (1 PASS/1 FAIL, nhãn Customer là “mới”, không phải “chưa đọc”). Đã sửa assertion đúng hành vi/nhãn, giữ kiểm tra retry query, pending và counter; không tăng timeout hoặc bỏ test.
- Các phát hiện bên dưới là bằng chứng trước sửa, giữ để truy vết. QA-04/T12 vẫn mở: Windows còn Local CMOS Clock/Stratum 0; chưa có nghiệm thu sau sửa clock/staging/thiết bị thật/pilot. Không thay JWT hoặc runtime clock trong lượt sửa UI này.

Đối chiếu kế hoạch với source và coverage hiện có; không coi checkbox lịch sử là chứng nhận mới. Không sửa nghiệp vụ trong lượt review này. Các kết quả test ngày 19/10 phía dưới là lịch sử. Phần nghiệm thu thiết bị thật/pilot vẫn chưa thực hiện.

### Phát hiện cần xử lý

- **[WARNING] R29-01 — Web Push tiếp tục bằng phiên mới (T07a/b, T11b/c).** `frontend/src/lib/web-push.ts:55`, `:73`, `:95`, `:113`: lấy quyền và đăng ký service worker bất đồng bộ, sau đó API helper lấy token hiện tại mà không so danh tính phiên lúc bắt đầu. Kiểm tra chạy chính module TS trong Node VM, stub browser/API, chờ permission rồi đổi A→B: đăng ký thực tế dùng B. Đây là tái hiện ở mức module, chưa phải E2E trình duyệt thật; chưa chứng minh rò rỉ dữ liệu qua RLS. Cần pin session identity từ đầu, hủy phần tiếp tục khi phiên thay đổi, bao phủ cả tự đăng ký subscription có sẵn trong bell và thao tác tắt. Test hiện có chỉ bao phủ logout cleanup muộn và chặn branch switch khi permission pending, không bao phủ enable cũ đi qua login mới.
- **[WARNING] R29-02 — Thu tiền hiển thị kết quả bộ lọc cũ sau lỗi (T06).** `frontend/src/app/(admin)/admin/payments/page.tsx:51`: request mới chỉ bật loading, không xóa/đánh dấu scope của rows; catch chỉ đặt error, finally tắt loading. Sau tìm A thành công → tìm B bị 503, các dòng A và nút xác nhận lại hiển thị dưới truy vấn B. Cần gắn scope vào kết quả hoặc ẩn rows cũ khi request mới thất bại; có nút thử lại cùng truy vấn. Backend vẫn tính invoice theo source ID; chưa thấy bằng chứng sai tiền trong DB. Phát hiện từ source, cần E2E lỗi 503 sau đổi query/filter/page trước nghiệm thu sửa.
- **[WARNING] R29-03 — Bộ đếm thông báo giảm lặp (T11c).** `frontend/src/components/admin/notification-bell.tsx:123`, `:127` và `frontend/src/components/customer/customer-notification-bell.tsx:127`, `:129`: hai PATCH cho cùng một notification đều giảm counter, dù backend mark-read idempotent. Nút không có pending guard; polling GET có thể tiếp tục ghi trạng thái cũ sau mutation. Cần khóa theo ID và đồng bộ unread_count theo response GET mới có request generation. Kiểm tra nhấn hai lần khi mạng chậm và GET cũ trả sau PATCH; không chỉ kiểm tra overflow/error/empty.
- **[WARNING] R29-04 — Failure artifact che lỗi layout gốc (T00c).** `automation_test/reviews/test_layout_regressions.py:47`: trong except AssertionError vẫn gọi capture_layout; runner hiện cấm artifact nên phát RuntimeError trước khi re-raise lỗi bố cục. Không tạo file nhưng làm chẩn đoán sai loại lỗi. Khi console-only phải giữ AssertionError/số đo trong console và bỏ capture. Ba regression lịch trong thư mục reviews cũng không thuộc lệnh chỉ chạy features; 204 bài features không đồng nghĩa chạy lại toàn bộ calibration/layout lịch.
- **[WARNING] R29-05 — Liên kết spa demo còn ở màn lỗi production (T04b/T11d).** `frontend/src/components/customer/customer-shell.tsx:65`: tenant không tồn tại dẫn người dùng tới `/spa-demo`; deployment thực không seed demo nên dễ lặp trang không tìm thấy. Đổi CTA về trang chọn chi nhánh `/` và dùng nhãn nghiệp vụ.
- **[CRITICAL — chưa đóng từ trước] QA-04/T12:** lỗi JWT ImmatureSignatureError đã từng tái hiện; các bước đồng bộ Windows/WSL và kiểm chứng sau sửa chưa hoàn tất. Không sửa JWT/leeway để làm xanh. Staging HTTPS, Android/iPhone và pilot vẫn còn thiếu. Xem PROGRESS/RELEASE_RUNBOOK; không coi test tự động xanh là đóng lỗi runtime.

### Đối chiếu đủ 29 task

Bổ sung kiểm chứng R29-02: đã tái hiện trên Chromium với production frontend của runner, API được mock trong browser để trả 503 cho query B; customer A vẫn hiển thị. R29-03: chạy chính handler TS trong Node VM với hai PATCH resolve cho cùng ID, còn 2 item chưa đọc nhưng counter=1. Probe browser riêng cho R29-03 chưa hoàn tất (selector đầu tiên chọn nhầm nút có title, timeout chờ PATCH), không tính probe đó là PASS. Các probe không ghi file hoặc thay DB ứng dụng.

- T00a, T00b: kiểm tra marker UUID, cô lập rewrite/SSR/DB, cấm port 3000 và teardown theo process sở hữu; harness mới 25/25 PASS (0.300s). T00c: measurement/assertion có sẵn, còn R29-04 và chưa chạy lại collector theo chỉ thị không ghi artifact.
- T01a, T01b: contract atomic batch, tenant/actor/request UUID, advisory lock, rollback và RLS migration 0008 có trong source; UI giữ UUID khi response chưa rõ. T02: scope/request guard và refresh sau mutation theo scope hiện tại có trong source/test.
- T03a, T03b: agenda mobile/tuần PC, chi tiết/xác nhận và test trạng thái/thẻ có trong triển khai; phần layout lịch chuyên biệt ở reviews cần phân biệt với features. T04a: target/input responsive, strict/noImplicitAny bật; quét source không phát hiện type any hoặc ts-ignore. T04b: foreground theo màu, copy thẻ và test theme có; còn CTA demo R29-05.
- T05a, T05b: native dialog, focus/scroll/history/dirty/pending và test màn thấp có; chưa thay kiểm tra bàn phím ảo thực. T06: receipt/void giữ attempt UUID và khóa refresh-failed có; còn lỗi scope danh sách R29-02.
- T07a, T07b: token/session revision và guard 401/me/logout có; còn lifecycle Push R29-01. T07c: public tenant lỗi khác 404 và slots current-scope/ready/empty/error có.
- T08a, T08b: contract mảng + X-Has-More, tên theo lô và quyền trước phân trang, UI tải thêm/bỏ trùng có. T09a: wizard 3 bước, explicit slot/ref chống submit lặp có. T09b, T09c: available-slots theo snapshot, authorize trước exclude và giữ KTV khi omit có; mutation serialize qua customer advisory lock trước package/staff/booking.
- T10a: CRM 50/tải thêm, list/detail và request guard khách/ca làm có. T10b: bảng/card cùng DOM, phân biệt báo cáo thực thu/giá trị/hoa hồng có. T10c: exhausted/expired/held/available và chiều rộng shell có.
- T11a: nav theo role, safe area/Back/focus có. T11b: shared/exclusive Web Locks và guard giao dịch chưa rõ có; không bao phủ toàn bộ login/logout Push R29-01. T11c: modal thông báo/dashboard scope có; còn R29-03. T11d: coverage route/Operator/settings baseline có; cần thêm tenant 404 không demo. T12: chưa hoàn tất.

Trạng thái lịch sử là 28/29, nhưng **không xác nhận lại 28 task đều sạch lỗi**: các phát hiện trên mở công việc sửa/bổ sung test. Chưa có phát hiện mới đã chứng minh ở mức CRITICAL cần auto-patch; các WARNING được giữ rõ để sửa theo phạm vi.

**Kiểm chứng mới ngày 20/10:** production build/TypeScript PASS, **204/204 features PASS (903.02s)** trên run `23ace1c2-7b89-4960-b2c4-4a1899e6d64a`; không skip/xfail/setup error. Chạy riêng cùng frontend/backend QA đã xác minh marker: **3/3 regression lịch PASS (27.04s)** ở `reviews/test_layout_regressions.py`, không collector/ảnh/JSON. Harness **25/25 PASS (0.300s)**. Không chạy lại backend suite trong lượt không sửa backend; 98/98 trước đó là lịch sử. Các probe lỗi mới được phân biệt với regression suite đang xanh; chưa có test bao phủ các tình huống R29-01..03 trong suite hiện hành. QA-04 không tái hiện ở lượt này, không chứng minh đã sửa runtime. Runner exit 0, port 3001 không còn listener và không còn container E2E QA; không đụng server 3000/DB ứng dụng.

Ngày: 18/10/2026. Theo yêu cầu PO: ưu tiên UI/UX tốt trên PC và điện thoại; ghi nhận trước, tiếp tục review lịch, thẻ và nội dung tràn viền. Chưa thay đổi giao diện trong lượt này.

Trạng thái mới nhất 19/10/2026: T11b/T11c/T11d đã nghiệm thu phạm vi Chromium: 28/29 task, còn T12. Guard dirty/pending đổi chi nhánh cả hai tab, giữ UUID/payload giao dịch; dashboard đúng scope/Back/Forward, thông báo vừa màn hình/có retry và coverage các route còn lại. Production cuối 86d9eaf7-ae95-42eb-ae99-d6d658765eeb: build/TypeScript và full E2E 204/204 PASS (554.89s); backend isolated 88/88, unit QA harness 23/23 PASS. T12 mới đạt phần tự động; thiết bị thật/bàn phím/safe area/zoom 200% và pilot CHƯA KIỂM CHỨNG. QA-04 đã tái hiện ở run trung gian f5a26bdb, chưa đóng nguyên nhân; không nới JWT hoặc coi lượt xanh là đã sửa. Migration 0008 chưa áp dụng DB ứng dụng; chưa chốt pilot/release. Xem PROGRESS cho source, run lỗi, lệnh và cleanup. Các nhận xét trước là lịch sử/thiết kế đích.

T12 bổ sung 19/10/2026: PO xác nhận chưa có staging HTTPS/thiết bị thật. Đã thêm probe JWT chỉ đọc và log clock an toàn; backend isolated 98/98, production regression phiên/đa chi nhánh/Operator 44/44 PASS (9c4b7634). Probe 21.761 mẫu/120s không tái hiện, chưa đóng nguyên nhân QA-04. Full UI 204/204 là lượt trước, frontend không đổi. T12 vẫn mở, không nghiệm thu giả lập thay điện thoại/pilot thật; xem PROGRESS và RELEASE_RUNBOOK.

Nhóm E: lịch dùng customer_name/staff_name/service_name theo lô, không phụ thuộc trang CRM đầu; nguồn KTV công khai chỉ tên/ID và không co theo slots. Calendar/appointments có tải thêm/còn dữ liệu, guard trang cũ và retry giữ các dòng đã tải; bộ chọn khách tạo lịch tìm bằng API theo trang 50. Đã sửa tên KTV dài bị cắt trong thẻ lịch khách và đồng bộ readiness test 401 theo request thực. Trang CRM chính vẫn limit=100 tại admin/customers/page.tsx:92, đã đưa vào T10a. Không đổi transaction/RLS/quyền; tiếp theo T09.

Nhóm D đã xử lý lỗi mất phiên khi 503/offline, stale me/401/switch/push cleanup, thay đổi phiên giữa các tab kể cả cùng JWT, dữ liệu/dialog riêng tư còn từ phiên cũ; có retry trước xác minh quyền/chi nhánh. Public tenant chỉ 404 mới not-found; slots lỗi khác 200 rỗng, submit theo scope đã xác minh, không ghi đè lựa chọn mới bằng response cũ. Giữ draft đăng nhập nhanh từ khách chưa đăng nhập. Không thay JWT/RLS/API; QA-04 chưa đóng nguyên nhân. Nhóm tiếp theo E: T08a/T08b.

## Nghiệm thu T11b/T11c/T11d và giới hạn T12 — 19/10/2026

- [PASSED] UX-19: `frontend/src/lib/branch-guard.ts:30` và `:46` — guard form/giao dịch và Web Locks giữa các tab trước đổi branch; giữ UUID/payload khi chưa rõ kết quả, chặn gửi mutation trong lúc chuyển, không replay sang tenant mới. Caller bao gồm CRM owner, cấu hình/ca làm/cấp quyền, modal/thu tiền/manual batch và Push chờ quyền. Session đổi ngoài tab vẫn xóa UI riêng tư. Trình duyệt thiếu Web Locks bị chặn đổi branch, cần kiểm chứng HTTPS/thiết bị tại T12.
- [PASSED] UX-07/18: `frontend/src/components/admin/notification-bell.tsx:168`, `frontend/src/components/customer/customer-notification-bell.tsx:173` — dùng Modal chung thay popup cố định, kiểm tra 320/360px, tên dài, 30 thông báo, error/empty/retry/Back/focus. Dashboard đưa tác vụ chi nhánh lên trước số liệu, tổng hợp chỉ xem, query/Back/Forward đồng bộ. Không thêm chỉ số/API.
- [PASSED] T11d: root/chọn chi nhánh, login Admin/khách/Operator, customer register, branches/settings/Operator/branding ở 320/390/768/1366px. Thêm wrap/retry và giữ attempt provisioning khi lỗi mạng. Kiểm tra hình học/label và sample palette; không phải chứng nhận mọi màu hoặc bàn phím điện thoại thật.
- [PASSED] Build production/TypeScript, full E2E **204/204 PASS (554.89s)**, backend isolated **88/88**, unit harness **23/23**. Run cuối `86d9eaf7-ae95-42eb-ae99-d6d658765eeb`; run lỗi và lệnh trong PROGRESS. Không collector/stress ảnh; dùng assertion/log thay cho bộ PNG/JSON mới.
- [WARNING] T12 chưa hoàn tất: thiết bị Android/iPhone thật, keyboard/safe area/zoom/touch/Push, pilot chủ spa/KTV/khách và QA-04. QA-04 đã tái hiện ở setup run `f5a26bdb`; lượt cuối xanh không đóng nguyên nhân. Quan sát đồng hồ run khác chưa chứng minh vì sao JWT bị từ chối; không nới leeway.

### UX-28 — [WARNING] Ngăn lưu cấu hình mặc định sau GET lỗi — ĐÃ SỬA VÀ KIỂM CHỨNG

- `frontend/src/app/(admin)/admin/settings/page.tsx:67`, `:218`: trước sửa, GET lỗi kết thúc loading và có thể submit giá trị mặc định chưa được xác minh. Hiện handler và nút Lưu yêu cầu baseline từ GET thành công; hiển thị lỗi/tải lại, không ghi đè cấu hình từ form mặc định.
- `automation_test/features/customer_regressions/tests/test_final_mobile_routes.py`: inject GET 503, xác nhận không lưu được, retry lấy đúng cấu hình và mở lại thao tác. PASS trong full 204. Không thay API hay dữ liệu database ứng dụng.

## Phương pháp và giới hạn
- Rà source frontend, kiểm chứng layout bằng Chromium/Playwright trên frontend build hiện có, API/database QA tạm riêng; không nhập dữ liệu vào database người dùng.
- Chiều rộng mục tiêu: 360, 390, 768, 1024, 1366px; viewport cao 844px. Thu ảnh và DOM bounds; số phần tử nhỏ là chỉ báo review, không tự kết luận mọi nút vi phạm accessibility.
- Chạy riêng: python -m pytest reviews/layout_probe.py -s (tại automation_test). Đây là công cụ thu bằng chứng, không phải gate xác nhận UI đạt chuẩn. Không được gọi pytest collector PASS là UI PASS.
- Bằng chứng tại automation_test/artifacts/ui-review-20261018/. Chưa kiểm tra thiết bị iOS/Android thật, bàn phím ảo, landscape, zoom 200%, screen reader và mọi trạng thái nghiệp vụ.

## Backlog có ưu tiên

### UX-01 — P1: Lịch tuần dùng thẻ quá chi tiết trong 7 cột
- frontend/src/app/(admin)/admin/bookings/page.tsx:1008 và :689. Từ md (768px), lịch 7 cột cùng sidebar 256px; thẻ lịch tuần dùng chung toàn bộ nội dung/nút với lịch ngày.
- Hướng sửa: thẻ tuần gọn giờ + tên + trạng thái; mở chi tiết để thao tác. Quyết định số cột theo không gian nội dung thực, có chiều rộng tối thiểu và cuộn cục bộ nếu cần; mobile ưu tiên lịch ngày/danh sách theo ngày.
- Nghiệm thu: với 10 KTV và nhiều lịch/ngày, không tràn toàn trang, không phải đọc chữ quá nhỏ; bộ lọc KTV/ngày dễ thấy.

### UX-02 — P1: Nội dung dài chưa được bảo vệ khỏi tràn
- bookings/page.tsx:707 dòng giờ/thời lượng/badge không wrap; :775 ghi chú không có quy tắc ngắt chuỗi dài. Tên khách/dịch vụ/tiền cần kiểm tra cả min-width của flex/grid con.
- Hướng sửa: min-w-0 đúng cấp, wrap cho nhóm badge, overflow-wrap cho nội dung tự do; ưu tiên giữ đầy đủ tên và tiền cần đối chiếu, chỉ rút gọn nội dung phụ kèm cách xem hết.
- Không dùng overflow-x-hidden toàn trang để che lỗi.

### UX-03 — P1: Vùng bấm nhỏ, thao tác trạng thái dễ nhầm
- frontend/src/components/ui/button.tsx:29 (32–36px); bookings/page.tsx:795 (nút trạng thái chữ 11px); :1292 nút cao 28px.
- Hướng sửa: thao tác chính mobile khoảng 44–48px, khoảng cách rõ; đưa thao tác phụ vào menu. Xác nhận hành động tác động dữ liệu quan trọng, trình bày rõ khách/lịch/buổi bị tác động, không thêm xác nhận cho mọi click.

### UX-04 — P1: Modal chưa quản lý focus và cuộn nền
- frontend/src/components/ui/modal.tsx:24: hiện xử lý Escape nhưng thiếu initial focus, focus trap, trả focus về nút mở, khóa cuộn nền và liên kết aria-labelledby/description.
- Hướng sửa: primitive dialog phù hợp; mobile dùng chiều cao khả dụng, header/footer rõ; kiểm tra bàn phím ảo và nội dung dài. Xem xét chặn đóng khi đang lưu hoặc có thay đổi chưa lưu.
- Hiện có role=dialog, aria-modal, giới hạn cao và cuộn trong modal; chưa đủ để chốt accessibility.

### UX-05 — P1: Xác nhận thu tiền tách xa dòng vừa chọn
- frontend/src/app/(admin)/admin/payments/page.tsx:79, :130: chọn dòng chỉ set state; khu vực xác nhận nằm trước danh sách, không chuyển focus/scroll tới đó.
- Hướng sửa: sheet/dialog riêng hoặc mở tại dòng; giữ tên khách, dịch vụ và số tiền cần thu luôn rõ; quay lại đúng dòng sau xác nhận. Test chọn dòng cuối danh sách dài.

### UX-06 — P1: Form đặt lịch còn điền sẵn tài khoản demo
- frontend/src/app/[tenant_slug]/book/page.tsx:66–68; :612 còn “Phiếu Đặt lịch”.
- Hướng sửa: để trống tài khoản/mật khẩu, autocomplete phù hợp; dùng “Xác nhận lịch hẹn”. Bỏ “Calendar” khỏi điều hướng, diễn đạt trạng thái bằng ngôn ngữ chủ tiệm.

### UX-07 — P2: Popup thông báo có chiều rộng cố định
- frontend/src/components/admin/notification-bell.tsx: popup w-80/sm:w-96; customer/customer-notification-bell.tsx:180 w-80, neo phải theo nút.
- Cần đối chiếu bounds trên màn hình nhỏ/tên chi nhánh dài; giới hạn theo viewport hoặc dùng sheet mobile. Không kết luận đã tràn trên tất cả kích thước chỉ từ class.

### UX-08 — P2: Thanh điều hướng khách chưa có safe-area
- frontend/src/components/customer/customer-shell.tsx:168 fixed bottom, padding cố định; cần tính safe-area-inset-bottom trên thiết bị có home indicator và đồng bộ khoảng trống nội dung.

### UX-09 — P2: Bảng báo cáo/dịch vụ vẫn ưu tiên desktop
- frontend/src/app/(admin)/admin/reports/page.tsx:231; services/page.tsx:180: bảng cuộn ngang cục bộ là chủ ý, không tự coi là lỗi tràn toàn trang.
- Mobile nên có thẻ tóm tắt nhân viên/dịch vụ và mở chi tiết; giữ số tiền, trạng thái và hành động dễ đối chiếu.

### UX-10 — P2: CRM/nhân sự hai cột đổi thành cuộn dọc dài
- frontend/src/app/(admin)/admin/customers/page.tsx:354 danh sách cuộn riêng tối đa 540px; :419 panel hồ sơ nằm sau danh sách khi mobile, lời nhắc vẫn “bên trái”. Dòng chọn khách là div onClick, chưa có semantics/keyboard selection.
- Hướng sửa: mobile chuyển danh sách → chi tiết có nút quay lại, giữ vị trí/từ khóa; dùng button/link phù hợp cho lựa chọn hồ sơ.

### UX-11 — P2: Trang khách trên PC quá hẹp
- frontend/src/components/customer/customer-shell.tsx:102 max-w-md ở mọi viewport. Không phải overflow nhưng lãng phí không gian PC.
- Hướng sửa: danh mục dịch vụ rộng hơn trên PC, khu vực đặt lịch/thông tin tóm tắt giữ độ rộng dễ đọc.

### UX-12 — P2: Form, nhãn và trạng thái cần kiểm tra thống nhất
- frontend/src/components/ui/input.tsx:14 input cao 36px/chữ nhỏ; Label uppercase/text-xs. Rà lỗi inline, focus lỗi đầu tiên, loading, empty/error state, long prices, double-submit, trường required và bàn phím SĐT/tiền.
- Cần kiểm tra Safari focus input, không tự coi giả lập Chromium là đã kiểm chứng iPhone.

## Tiêu chí chốt trước pilot
- Không cuộn ngang toàn trang ở viewport mục tiêu; cuộn ngang chỉ xuất hiện ở vùng chủ ý, có dấu hiệu nhận biết.
- Tên 80 ký tự, tên dịch vụ dài, ghi chú không khoảng trắng 280 ký tự, tiền lớn, nhiều badge không vượt card/che nút.
- Lịch ngày/tuần với ít và nhiều dữ liệu; dễ nhận ra giờ, khách, KTV, trạng thái; không phụ thuộc màu đơn thuần.
- Modal dùng được bằng bàn phím; focus đúng, nền không cuộn, không mất dữ liệu khi click nhầm.
- Thu tiền với 30+ dòng: chọn đúng khách, số tiền rõ, trạng thái cập nhật, không tạo xác nhận trùng.
- Có bằng chứng thiết bị thật Android/iOS và PC; không dùng số lượng test nghiệp vụ thay cho đánh giá usability.

## Kết quả đo trực tiếp
Đã thu 31 ảnh/đo DOM trong một lượt collector hoàn tất (58.80s), dữ liệu QA riêng. Collector trả thành công chỉ nghĩa là thu được bằng chứng; UI vẫn có lỗi dưới đây.

- **UX-01 xác nhận P1:** ảnh 768-calendar-week.png và 1366-calendar-week.png cho thấy giờ/tên khách/badge tràn khỏi thẻ hoặc bị cột kế bên che, nút bị ép xuống nhiều dòng. PC 1366px cũng gặp. Cần sửa trước pilot.
- **UX-02 xác nhận P1:** 390-calendar-long-note.png: ghi chú 280 ký tự không khoảng trắng kéo document từ 390px lên 1821px. Nội dung này hợp lệ về độ dài; cần ngắt chuỗi và min-width đúng cấp layout.
- **Mobile tuần lãng phí chiều cao:** 390-booking-modal.png chụp full page cho thấy tuần chỉ có một booking nhưng 7 khối ngày (min-height 260px) khiến trang dài khoảng 2462px; nhiều phần “Trống”. Đây là bố cục cần thiết kế lại, không chỉ tăng font.
- **Thu tiền 360px:** ảnh 360-notifications.png cho thấy nút nằm cạnh cột thông tin quá hẹp, tên thẻ và tiền/ngày xuống nhiều dòng; ô tìm kiếm cũng rất hẹp. Ưu tiên nút toàn chiều rộng phía dưới thông tin, ô tìm kiếm trên một hàng riêng.
- **Thẻ liệu trình 390px:** 390-customer-package.png không tràn với dữ liệu mẫu ngắn, nhưng badge còn ACTIVE; “Khả dụng: 0 buổi” màu đỏ cạnh “Còn lại: 1 buổi” dễ gây hiểu nhầm khi một buổi đang giữ chỗ. Nên ghi “Còn 1 buổi, đã đặt lịch 1 buổi; có thể đặt thêm 0 buổi”, trạng thái “Đang sử dụng”, dùng màu trung tính khi chỉ đang giữ chỗ.
- **Popup thông báo Admin 360px:** nằm trong viewport với mẫu đã kiểm tra; chưa đủ bằng chứng gọi nó là lỗi tràn. Giữ UX-07 là kiểm tra biên ở màn hình hẹp hơn/tên dài/customer popup.
- 30 ảnh trạng thái thông thường có pageWidth bằng viewport. Điều này KHÔNG có nghĩa nội dung trong card không tràn/cắt: lịch tuần ở trên là ví dụ rõ. Phải kiểm tra bounds từng card và ảnh bên cạnh scrollWidth toàn trang.
- Modal có cuộn nội bộ và không làm rộng trang trong các mẫu này. Thiếu focus trap/scroll lock là phát hiện source, chưa kiểm chứng bàn phím ảo hoặc focus bằng thiết bị thật.

Ảnh: [lịch tuần PC](../automation_test/artifacts/ui-review-20261018/1366-calendar-week.png), [lịch tuần tablet](../automation_test/artifacts/ui-review-20261018/768-calendar-week.png), [ghi chú dài](../automation_test/artifacts/ui-review-20261018/390-calendar-long-note.png), [thu tiền mobile](../automation_test/artifacts/ui-review-20261018/360-notifications.png), [thẻ khách](../automation_test/artifacts/ui-review-20261018/390-customer-package.png). Số đo gốc: [results.json](../automation_test/artifacts/ui-review-20261018/results.json).

## Thứ tự triển khai đề xuất
1. Sửa lịch tuần, chặn tràn chuỗi dài và chỉnh vùng bấm; thêm regression đo cả card lẫn viewport.
2. Thu tiền mobile: bố cục thông tin/nút, vị trí xác nhận, tìm kiếm.
3. Modal/focus/scroll, CRM trên mobile và ngôn ngữ thẻ/trạng thái; bỏ credentials demo.
4. Tối ưu báo cáo và không gian PC; kiểm chứng bàn phím ảo/safe area, dữ liệu dài, 10 KTV và nhiều booking trên thiết bị thật.

Chưa thay đổi UI ứng dụng trong lượt review này; các hạng mục vẫn cần được triển khai và nghiệm thu.


## Review sâu luồng điện thoại — 18/10/2026
Phạm vi lượt tiếp theo: review source và thiết kế tương tác, dùng bằng chứng visual của lượt trước. Chưa chạy thêm bộ thiết bị hoặc kiểm thử lỗi mạng trong lượt này. P1 là cần xử lý trước pilot; không đồng nghĩa mọi mục là lỗi bảo mật CRITICAL.

### UX-13 — P1: Chọn KTV bằng mã, dữ liệu lựa chọn phụ thuộc sai bước
- frontend/src/app/[tenant_slug]/book/page.tsx:145, :458, :481: danh sách KTV suy ra từ slots của ngày đang chọn, nhưng bước KTV đứng trước bước ngày. Chọn một KTV lại tải slots lọc theo KTV đó, khiến tập lựa chọn có thể co lại.
- Hiển thị Kỹ thuật viên #1 (mã rút gọn), xác nhận cũng bằng ID (:640); khách không nhận ra nhân viên quen.
- Hướng xử lý: dịch vụ → ngày/giờ và lựa chọn KTV chung một bước → xác nhận. Cho phép “Spa sắp xếp” hoặc tên hiển thị công k hai. Tập nhân viên lựa chọn độc lập với kết quả slots đã lọc; nhân viên hết giờ trống vẫn có lời giải thích/đề xuất đổi ngày. Nếu cần API tên công khai, chỉ trả ID/tên được phép hiển thị trong chi nhánh active, không trả SĐT/hồ sơ riêng.

### UX-14 — P1: Mất mạng bị diễn giải thành hết lịch hoặc mất phiên
- book/page.tsx:130: catch tải slots chỉ xóa danh sách; màn hình :547 dùng cùng trạng thái rỗng cho không có giờ trống.
- components/customer/customer-context.tsx:85–86: mọi lỗi fetchCustomerMe đều xóa token. Lớp lib/customer-api.ts đã phân biệt 401 nhưng context lại xóa trên cả lỗi mạng/5xx.
- Hướng xử lý: tách loading/empty/error; lỗi mạng báo “Chưa tải được giờ trống” + Thử lại. Chỉ xóa phiên khi xác thực thực sự thất bại; lỗi tạm giữ token, hiển thị trạng thái chưa xác minh và khóa thao tác cần quyền đến khi xác minh lại. Không tiếp tục dùng dữ liệu riêng của phiên/chi nhánh cũ.

### UX-15 — P1: Tự chọn giờ đầu tiên và cho nhảy bước chưa hoàn tất
- book/page.tsx:128 tự gán slot đầu; :276 chỉ kiểm tra đã chọn dịch vụ để nhảy bước bất kỳ.
- Rủi ro: người dùng vào xác nhận mà chưa chủ động chọn giờ. Đây là rủi ro ý định người dùng, chưa kết luận backend cho đặt lịch không hợp lệ.
- Hướng xử lý: không mặc định chọn giờ thay khách; bước sau chỉ mở khi dữ liệu cần thiết hợp lệ. Đổi ngày/KTV/dịch vụ thì xóa giờ cũ, nêu rõ cần chọn lại. Back giữ thông tin không bị ảnh hưởng.

### UX-16 — P1: Tên khách trong lịch phụ thuộc danh sách 200 hồ sơ
- admin/bookings/page.tsx:195 tải khách limit 200, :691/:727 lookup rồi fallback UUID. Khi khách không thuộc trang tham chiếu đầu, lịch có thể hiện mã thay tên; tổng danh sách lịch cũng limit 200 (:233) chưa có điều hướng phân trang rõ tại màn hình này.
- Hướng xử lý: dữ liệu lịch có display fields được backend kiểm soát quyền hoặc fetch batch đúng tập ID hiện có; không tải toàn bộ CRM để tra tên. Phân trang/nhóm ngày với dấu hiệu còn dữ liệu, không âm thầm coi 200 lịch là toàn bộ.
- Cần regression >200 khách và lịch với quyền STAFF; không nới quyền hồ sơ để làm đẹp UI.

### UX-17 — P1: “KTV phụ trách” đang gắn cho nhân viên thực hiện lịch
- admin/bookings/page.tsx:692, :730 lookup booking.staff_id nhưng nhãn là “KTV phụ trách”. Theo nghiệp vụ, chủ hồ sơ cố định và nhân viên thực hiện lịch có thể khác nhau.
- Hướng xử lý: “KTV thực hiện” trên lịch; “KTV phụ trách hồ sơ” trong hồ sơ. Dời lịch đổi KTV không ngầm chuyển quyền; checkbox bàn giao riêng cho Admin và mặc định tắt phải giữ nguyên.

### UX-18 — P2: Dashboard đặt mọi chỉ số cùng mức ưu tiên
- admin/dashboard/page.tsx:12–20: 9 thẻ số liệu một cột dưới sm, rồi mới có link tác vụ phía dưới. Chế độ mọi chi nhánh lặp lại cả bộ chỉ số.
- Hướng xử lý: ưu tiên việc hôm nay và số tiền thực thu; dữ liệu còn thiếu/toàn thời gian gắn rõ phạm vi, phần chi tiết thu gọn. Lối vào lịch/thu tiền xuất hiện sớm. Không dùng biểu đồ trang trí thay hành động cần làm.

### UX-19 — P2: Chuyển chi nhánh có thể bỏ dở form
- admin/auth-context.tsx: changeBranch lưu token và location.assign; header luôn có dropdown. Chưa có kiểm tra form dirty trong đường này.
- Hướng xử lý: xác nhận khi có thay đổi chưa lưu; chặn chuyển khi giao dịch thu tiền chưa xác định kết quả. Thể hiện chi nhánh trên xác nhận lịch/thu tiền. Không auto-save dữ liệu nhạy cảm vào localStorage để giải quyết vấn đề.

### UX-20 — P1 với theme sáng: Chữ phụ ở slot vẫn màu trắng
- book/page.tsx:584–592: slot selected có “KTV trống” dùng text-white/85, trong khi background có thể vàng hoặc màu sáng do Operator chọn.
- Hướng xử lý: toàn bộ chữ/icon trong trạng thái selected dùng foreground tương ứng, không chỉ chữ chính. Kiểm tra hover/disabled/focus/selected trên màu sáng và tối.

Thiết kế xử lý chi tiết: [MOBILE_UX_DESIGN.md](MOBILE_UX_DESIGN.md). Các mục chưa được triển khai hoặc nghiệm thu.


## Review bổ sung trước lập kế hoạch bàn giao — 18/10/2026
Nguồn: đọc source và đối chiếu luồng; CHƯA mô phỏng runtime các trường hợp UX-21–24 trong lượt này. Không suy từ rủi ro source rằng đã xác nhận dữ liệu trùng.

### UX-21 — P1, cần reviewer nghiệp vụ: Đặt nhiều buổi có thể thành công một phần
- frontend/src/app/(admin)/admin/bookings/page.tsx:566–680: tạo khách nhanh → cấp thẻ mới → gọi createBooking từng dòng; catch chỉ báo lỗi chung, chưa ghi trạng thái từng phần thành công vào form để đối chiếu.
- Nếu buổi thứ hai lỗi/xung đột sau buổi đầu thành công, form có thể khiến người dùng tưởng toàn bộ thất bại. Thử lại có rủi ro cấp thêm thẻ hoặc gặp lỗi khách đã tồn tại. Chưa runtime xác nhận chuỗi cụ thể.
- Bắt buộc tái hiện trong QA: 3 buổi, buổi 2 trả 409/503; ghi ID khách/thẻ/lịch trước/sau, kiểm tra retry. Không sửa bằng cách tự hủy lịch/xóa thẻ đã tạo hoặc chạy lại toàn bộ chuỗi không đối chiếu.
- Quyết định giao dịch batch/idempotency hoặc recovery từng bước phải được review nghiệp vụ/concurrency trước khi giao model nhỏ triển khai. UI cần báo rõ phần nào đã tạo và phần nào cần xử lý.

### UX-22 — P1: Response cũ có thể ghi đè lịch của ngày vừa chọn
- admin/bookings/page.tsx:222–248: loadBookings không có request sequence/cancel guard. Đổi ngày A→B mà response A về sau B có thể hiển thị dữ liệu A dưới ngày B; lỗi fetch giữ bookings cũ.
- Cần test delay đảo thứ tự, đổi KTV/trạng thái và mutation trong lúc reload; guard phải áp dụng cả setBookings/setLoading/setError. Không chỉ cancel effect mà bỏ sót load thủ công sau thao tác.

### UX-23 — P1: Dời lịch chưa giữ rõ ý định người dùng
- admin/bookings/page.tsx:381–392 lấy available slots của dịch vụ hiện tại rồi ưu tiên cùng giờ hoặc tự chọn giờ đầu. Thời gian booking hiện tại vẫn là lịch đang chiếm chỗ; UI có thể không cho giữ giờ cũ để chỉ sửa ghi chú/đổi KTV. Giá/thời lượng snapshot của booking có thể khác menu hiện tại.
- customer appointments/page.tsx: openRescheduleModal đặt rescheduleKeepStaff=false, effect tự chọn slot đầu; khách chỉ muốn đổi ngày có thể vô tình đổi KTV. Chưa runtime xác nhận mọi tình huống.
- Giữ KTV hiện tại nếu người dùng chưa chọn đổi; không auto chọn giờ khác khi giờ cũ không hợp lệ. Preview trước/sau rõ. API gợi ý dời lịch nếu bổ sung phải xác minh quyền booking, loại đúng booking đang sửa và dùng duration snapshot; không cho tùy ý exclude ID ngoài quyền.

### UX-24 — P2: Tải dữ liệu phụ lỗi bị bỏ qua, khiến nội dung trông như thiếu
- admin/bookings/page.tsx:191–219 catch bỏ lỗi loadReferenceData; modal/reference có thể thiếu tên/dịch vụ mà không có hướng thử lại. Khi đã tải một phần, cần trình bày rõ phần nào tạm chưa tải được.
- Không hiển thị fallback mã như dữ liệu hoàn chỉnh; không cho tạo lịch nếu danh mục cần thiết chưa được xác minh. Có lỗi riêng và Thử lại cho khối phụ, không chặn các thao tác độc lập đã đủ dữ liệu.

Kế hoạch kiểm tra/triển khai chia task tại [UI_UX_EXECUTION_PLAN.md](UI_UX_EXECUTION_PLAN.md). Mặc định bàn giao model nhỏ ở chế độ KIỂM TRA; không tự coi kế hoạch là lệnh sửa code.


## Rà soát cuối plan trước giao model nhỏ — 18/10/2026

Lượt này đối chiếu source, fixture/test và tài liệu; không chạy lại frontend, collector hay E2E. Không có ảnh thiết bị mới. Bằng chứng visual ở trên giữ nguyên phạm vi 31 mẫu; các phát hiện dưới là source review, chưa fault-injection runtime. Không phát hiện mới nào trong lượt này được kết luận là lỗi bảo mật CRITICAL đã tái hiện.

### UX-25 — [WARNING] P1: Admin cũng mất phiên khi lỗi mạng tạm thời

- frontend/src/components/admin/auth-context.tsx:79–85: catch của refreshMe xóa phiên và điều hướng login cho mọi lỗi fetchMe, bao gồm network/5xx; không chỉ Customer như UX-14.
- :78 fetchBranches lỗi bị biến thành mảng rỗng, khiến tải quyền/chi nhánh thất bại trông như không có chi nhánh.
- Hướng xử lý: giữ token khi lỗi tạm, hiển thị chưa xác minh/Thử lại, khóa thao tác cần quyền và không hiển thị dữ liệu riêng của phiên trước. 401 và role không hợp lệ vẫn xử lý xác thực theo đúng phạm vi.
- Bổ sung test response cũ sau logout/đăng nhập lại/chuyển branch. frontend/src/lib/api.ts:84 và frontend/src/lib/customer-api.ts:64 cũng cần kiểm tra identity request trước khi xóa token: không chỉ guard setState ở context.
- Tiếp nhận: T07b, T07a cho helper Customer; T11b giữ hành vi giữa các tab.

### UX-26 — [WARNING] P1: Lỗi tải chi nhánh bị báo “Spa không tồn tại”

- frontend/src/components/customer/customer-context.tsx:59–62: mọi lỗi fetchPublicTenant đặt tenantNotFound=true.
- frontend/src/components/customer/customer-shell.tsx:41–52: hiển thị “Không tìm thấy Spa”/“Đường dẫn Spa không tồn tại hoặc đã ngưng hoạt động”. Network/503 vì vậy bị phân loại như slug sai.
- Hướng xử lý: phân biệt loading/404/error; lỗi tạm có Thử lại, không để thương hiệu/dữ liệu slug trước hiện dưới URL mới. Không thay API để xử lý các HTTP status đã có.
- Tiếp nhận: T07c; test 404/503/offline/retry và chuyển slug trong lúc response cũ còn chờ.

### QA-01 — [WARNING]: Fixture có thể khởi động sai port

- Cập nhật T00a 18/10/2026: ĐÃ SỬA VÀ KIỂM CHỨNG bằng 12/12 unit test; fixture không còn start/stop process, yêu cầu URL QA và marker đúng lượt. Ba lỗi baseline được test bắt trước sửa bằng I/O mock. Các dòng source dưới là bằng chứng phiên bản trước vá. QA-02/03 vẫn chưa xử lý.

- automation_test/conftest.py:27–36: nếu config.frontend_url chưa sẵn sàng, subprocess chạy npm run start không kèm port. frontend/package.json:8 cố định start ở 3000.
- Cấu hình FRONTEND_URL=3001 không kiểm soát lệnh start này. Rủi ro được xác định từ source; không thử mở server để tái hiện vì không cần ảnh hưởng server người dùng.
- T00a phải fail rõ nếu URL ngoài runner chưa sẵn sàng; chỉ runner sở hữu process mới được quản lý frontend QA. Không kill server theo tên node.exe hoặc chiếm lại port.

### QA-02 — [WARNING]: Browser routing chưa cô lập API phía Next.js server

- automation_test/conftest.py:110 chỉ route request trong browser context.
- frontend/src/app/[tenant_slug]/layout.tsx:6–17 gọi API public tenant trực tiếp từ Next.js server; frontend/next.config.mjs:3 có fallback backend chính localhost:8001.
- Do đó có thể có browser dùng tenant QA nhưng title/theme metadata theo môi trường khác. Đây là thiếu sót cô lập/evidence; không phải bằng chứng test đã ghi dữ liệu vào DB chính.
- T00b cần cùng QA origin cho SSR/rewrite/browser và output build riêng. Chỉ đổi port sang 3001 không tách .next; không build ghi đè output server người dùng.

### QA-03 — [WARNING]: Collector chưa đủ làm regression gate

- automation_test/reviews/layout_probe.py:9 ghi cùng thư mục cố định; :18–34 thu số đo/ảnh nhưng không assert clipping/overlap trong card.
- T00c thêm run ID, assertions cho lỗi đã xác nhận và dữ liệu biên. Tiếp tục phân biệt collector chạy xong với UI đã đạt.
- Các test nghiệp vụ hiện có đã dùng expect_response và locator assertions ở nhiều luồng, có ca mất response sau commit thu tiền. Không quy chụp toàn suite flaky; phần thiếu là coverage UI/mạng/auth và thiết bị, không đơn thuần tăng số test.

### Kết luận về kế hoạch

- [PASSED] Plan bản 2 đã có task lá, dependency, ranh giới quyền/giao dịch, tiêu chí chứng minh trước/sau và phạm vi kiểm tra các màn còn thiếu.
- [WARNING] T01a/T08a/T09b vẫn cần quyết định giao dịch/API cụ thể; chưa đủ điều kiện giao model nhỏ tự triển khai backend.
- [WARNING] QA runtime phải qua T00a/T00b trước. Chưa có kết quả chạy mới và chưa thể kết luận mobile đạt chuẩn hoặc production sẵn sàng.
- Tài liệu API có mô tả cũ cho phép mở đăng ký tenant production bằng biến môi trường; đã chỉnh cho khớp backend/app/api/v1/auth.py:37 và phần Operator hiện hành. Không đổi endpoint.
- Thứ tự triển khai trong [UI_UX_EXECUTION_PLAN.md](UI_UX_EXECUTION_PLAN.md) bản 2 thay cho danh sách ưu tiên sơ bộ ở các phần trước. [MOBILE_UX_DESIGN.md](MOBILE_UX_DESIGN.md) mô tả UX đích; plan quy định từng bước được triển khai.

Chỉ tài liệu được cập nhật trong lượt này. Toàn bộ UX-01–26 vẫn phải được thực thi/kiểm chứng theo task tương ứng; “plan đã rà” không có nghĩa “UI đã sửa”.


## Triển khai T00a — 18/10/2026

Đã sửa riêng harness preflight và thêm unit tests, chưa thay UI ứng dụng. Đã bỏ tự khởi động/kill frontend; không chấp nhận HTTP 404/redirect hoặc server không có marker QA đúng lượt. Unit tests không tải .env.test, không tạo browser/DB/server. T00b còn cần runner/header và cô lập API SSR; chưa chạy lại E2E/collector và chưa bổ sung ảnh visual.

## Triển khai nhóm A — 18/10/2026

- [PASSED] T00b: runner đã kiểm chứng rewrite/SSR bằng tenant QA duy nhất, output/config riêng, production build PASS; QA-02 đã xử lý. T00c đã có 44 mẫu thường + 14 mẫu stress, run ID riêng và assertions clipping/overlap; QA-03 đã xử lý trong phạm vi công cụ đo.
- [PASSED] T04a/b: targets/input mobile, copy thẻ/KTV, bỏ demo credentials và selected foreground đã triển khai; 6 ca mobile mới PASS, gồm viewport 320/390/1366 và màu vàng/xanh đậm. Thẻ 390px đã xem ảnh: chữ/số buổi không tràn với mẫu ngắn. UX-03 chỉ xử lý primitive/caller; nút trạng thái card vẫn chờ T03b.
- [WARNING] UX-01/02 vẫn tái hiện bằng 3 strict xfail; chưa sửa lịch tuần/note dài. Các lỗi card được đo dù documentWidth bằng viewport. 320/360 từng tràn toolbar trong collector, đã wrap và kiểm chứng DOM 320px ở lượt focused cuối; chưa chụp lại toàn bộ collector sau sửa này.
- [WARNING] Dữ liệu stress tuần có 240 lịch nhưng UI hiện 200; giữ UX-16/T08 là hạng mục phải xử lý, không coi kết quả cap là dữ liệu đủ.

### UX-27 — [WARNING] P1: Lựa chọn KTV phụ trách bị effect khởi tạo ghi đè — ĐÃ SỬA

- frontend/src/app/(admin)/admin/customers/page.tsx:55: selectCustomer khởi tạo ownerId cùng hồ sơ, thay effect đồng bộ chạy sau render. Baseline E2E gửi assignment với người cũ dù đã chọn người mới; sau sửa regression quyền chuyển giao PASS.
- Đây là sửa race UI trong đợt T04, không thay quyền backend và không đánh dấu toàn T10a đã xong. Người phụ trách hồ sơ tiếp tục khác KTV thực hiện lịch.

### QA-04 — [WARNING] P1: Setup E2E bị JWT ImmatureSignatureError — CHƯA XỬ LÝ

- backend/app/core/security.py:37–39 kiểm tra JWT với leeway 2s; backend log ghi ImmatureSignatureError khi token Admin mới được dùng để tạo service/customer-package. Chưa xác định được nguyên nhân thời gian runtime; không kết luận đã sửa chỉ vì các ca khác qua.
- automation_test/features/customer_regressions/conftest.py:28–31 là nơi lỗi setup lộ ra, không phải assertion thanh toán/tenant đã thất bại. Full production run: 42 PASS/2 ERROR; focused: 7 PASS/3 XFAIL/1 ERROR. Các API/auth check vẫn được giữ nguyên, không auto-retry.
- Điều tra claim iat và đồng hồ container/host trước T12; cần review riêng nếu định thay xác thực. Không mở rộng leeway trong task layout. Log đầy đủ và lệnh chạy nằm trong PROGRESS/plan.

Nhóm tiếp theo: T02/T03a. Toàn bộ kế hoạch hiện hoàn tất 5/29 task, còn 24; không có kết luận production hoặc phone đã đạt chuẩn cuối cùng.

## Triển khai nhóm B — 18/10/2026

- [PASSED] UX-22/24 (T02): frontend/src/app/(admin)/admin/bookings/page.tsx:90 — scope/request identity cho lịch và tham chiếu, error/retry rõ, khóa thao tác phụ thuộc dữ liệu chưa tải. Late success/error không ghi đè scope mới; reload sau status mutation cũng có guard. Bảy race/reference E2E đã PASS trong run dev; một ca bị QA-04 chặn setup ở run production sau đó.
- [PASSED] UX-01/02 (T03a): thẻ tuần có bố cục riêng gọn, mở details để xem/thao tác; mobile agenda, ngày trống một dòng. PC cuộn trong vùng lịch và từng ngày nhiều dữ liệu. Tên/note/service dài ngắt dòng, lọc KTV tên 80 ký tự không làm rộng trang. Ba regression trước đây strict xfail nay là test thường PASS, gồm expanded details.
- [PASSED] Bằng chứng mới: 44 mẫu thường + 14 mẫu stress, documentWidth=viewport và card violations=0 ở 7 width. Stress 10 KTV/210 khách/240 lịch (60/ngày). Detector đã hiệu chuẩn closed details và overlap trong cùng card, không dùng overflow-hidden toàn trang hay giảm font để đạt số đo.
- [WARNING] QA-04 vẫn tái hiện ở setup /services: production run a1fe3aeb-5aff-4bec-8db2-f6861f905ba3 có 18 PASS/1 ERROR, chưa phải suite xanh. Không nới JWT/retry. Cap 200/240 lịch và tên khách ngoài trang tham chiếu vẫn thuộc UX-16/T08; bố cục đã sửa không làm các thiếu sót dữ liệu này tự hết.
- [WARNING] Native details là bước bố cục hiện tại; action hierarchy/focus/feedback khi cập nhật còn T03b. Modal/accessibility/phone thật còn T05/T12, chưa kết luận UI hoàn thiện.

Ảnh sau sửa: [tuần phone](../automation_test/artifacts/ui-review/a1fe3aeb-5aff-4bec-8db2-f6861f905ba3/T00c-collector/390x844-calendar-week.png), [tuần PC mở chi tiết](../automation_test/artifacts/ui-review/a1fe3aeb-5aff-4bec-8db2-f6861f905ba3/UX-01-regression/1366x844-week-expanded.png), [note dài](../automation_test/artifacts/ui-review/a1fe3aeb-5aff-4bec-8db2-f6861f905ba3/UX-02-regression/390x844-long-note.png). Xem PROGRESS để lấy lệnh/run ID và phạm vi kiểm chứng. Hiện 7/29 task hoàn tất, còn 22.

## Review lại 7 task đã triển khai — 18/10/2026

Phạm vi T00a/T00b/T00c/T04a/T04b/T02/T03a. Không thay mã ứng dụng; thêm ca tái hiện và sửa trạng thái tài liệu. Chưa thấy lỗi [CRITICAL] mới trong phạm vi này; không kết luận bảo mật/giao dịch toàn hệ thống từ review frontend.

### R7-01 — [WARNING] P1 — T02: Lưu xong sau đổi bộ lọc không cập nhật lịch đang xem

- `frontend/src/app/(admin)/admin/bookings/page.tsx:256` và `:502`: handler mutation giữ callback loadBookings của scope cũ; callback trả về ngay nếu scope hiện tại đã đổi. Không có invalidation cho scope mới sau commit.
- Tái hiện runtime: giữ PATCH xác nhận lịch, chọn lọc PENDING và đợi GET trả dữ liệu trước commit, rồi cho PATCH chạy. API GET trực tiếp xác nhận trạng thái CONFIRMED nhưng thẻ trên màn hình vẫn Chờ xác nhận trong bộ lọc PENDING. Không phải dữ liệu DB bị cập nhật sai.
- Reproducer `automation_test/reviews/seven_task_recheck.py:18` FAIL đúng assertion card phải rời danh sách; [ảnh sau commit](../automation_test/artifacts/ui-review/010d1f34-5f0a-424b-8815-07bfaabe5171/seven-task-review/390x844-status-filter-after-commit.png).
- Hướng sửa: sau mutation, invalidate/tải scope đang xem trong cùng danh tính/chi nhánh, giữ cơ chế chặn response cũ; không áp dụng dữ liệu mutation cũ sang phiên mới. Bổ sung đổi lọc/ngày/chế độ khi PATCH đang chờ và nhánh lỗi; rà cả create/reschedule dùng cùng callback.

### R7-02 — [WARNING] P2 — T00c: Gate bỏ qua nội dung ngoài viewport, collector chưa đo card ngoài lịch

- `automation_test/common_setup/layout_evidence.py:192`: assert_layout_contained chỉ kiểm tra có card, documentWidth và cardViolationCount; không dùng viewportOutsideCount đã được tính ở `:129`. Một nút fixed bị cắt bên trái màn hình vẫn được hàm này chấp nhận nếu card lịch bên cạnh nằm gọn.
- Reproducer `automation_test/reviews/seven_task_recheck.py:61` dùng HTML kiểm chuẩn: viewportOutsideCount > 0, documentWidth không tăng, cardViolationCount = 0; assertion mong gate từ chối FAIL. Đây là lỗi độ phủ công cụ đo, chưa phải bằng chứng ứng dụng hiện có nút fixed đó.
- `automation_test/reviews/layout_probe.py:14` không truyền card_selector theo màn; mặc định ở `layout_evidence.py:170` chỉ chọn booking. JSON 390px của run a1fe3aeb cho payments/notifications/customer-package đều có cards=[]; booking-modal chỉ đo thẻ lịch phía sau. Số 0 card violations ở các mẫu này không xác nhận nội dung bên trong chúng.
- Hướng sửa: gate cả phần ngoài viewport không được cho phép; chọn root/card/popup/modal đúng màn, báo rõ số phần tử đo và thêm ca âm/ca dương cho clipping/scroll. Giữ kiểm tra nội dung bên trong card khi ancestor cuộn chủ ý; không mở rộng exclude để test qua.

### R7-03 — [WARNING] P2 — T04b: Hai test màu cũ không chạy với màu được khai báo

- `automation_test/reviews/test_mobile_controls.py:56`: sửa CSS variables trên html nhưng `frontend/src/components/customer/customer-shell.tsx:99` đặt brandStyle tại ancestor gần hơn. Hai ca vàng/xanh đậm đều vẫn có nền slot `rgb(190, 24, 93)`; assertion `:60` chỉ so màu hai dòng chữ nên vẫn PASS.
- Hai reproducer tại `automation_test/reviews/seven_task_recheck.py:45` FAIL khi kiểm tra màu nền thực tế. Vì vậy rút lại kết luận lịch sử “đã kiểm chứng màu vàng/xanh đậm” dựa riêng trên test cũ.
- Kiểm chứng bổ sung đưa response branding qua provider thực tế: cả vàng, gần trắng, xanh đậm và đen PASS màu nền + foreground của hai dòng chữ slot. Đây là xác nhận phần sửa selected subtitle hoạt động; không chứng minh mọi màn/disabled/focus đã đủ contrast.
- Hướng sửa test chính: cấu hình branding qua provider/API QA, assert đúng màu nền trước khi so foreground; bổ sung trạng thái cần nghiệm thu. Không cần sửa thuật toán theme theo lỗi fixture này.

### R7-04 — [WARNING] P2 — T04b: Copy dùng thẻ còn thiếu ở wizard

- `frontend/src/app/[tenant_slug]/book/page.tsx:313`, `:343`, `:663` vẫn dùng “Giá 0₫”, “Dùng thẻ (0₫)”/“Đã chọn (0₫)” và “Trừ thẻ (0 ₫)”, dù profile/lịch đã chuyển sang diễn đạt dùng buổi thẻ. Phần này chưa đạt tiêu chí T04b, dễ khiến khách hiểu là dịch vụ miễn phí.
- Reproducer `automation_test/reviews/seven_task_recheck.py:101` xác nhận thẻ trong bước chọn vẫn có “Dùng thẻ (0₫)”. Đồng bộ nhãn theo “Dùng 1 buổi trong thẻ” và giải thích khoản cần thu thêm nếu có; giữ giá snapshot/payload server và phân biệt lịch có cả dịch vụ lẻ lẫn thẻ.

### Phần đạt và bằng chứng mới

- [PASSED] T00a: preflight không mở/tắt server, chặn 3000, HTTP/HTML/run UUID không khớp. T00b: 23 unit harness PASS; production build PASS, HTTP rewrite và SSR proof cùng QA DB, không đổi tsconfig/next-env. Kiểm chứng cleanup chỉ trên Windows hiện tại; test lỗi lifecycle chủ yếu dùng mock.
- [PASSED] T02 phần đọc: 7 regression cũ PASS (response ngày/lọc cũ, lỗi/retry, read chồng mutation trong cùng scope, reference lỗi); chưa bao phủ trường hợp R7-01 nên task mở lại.
- [PASSED] T03a: ba regression layout trước đây xfail vẫn PASS, gồm details đóng/mở 768/1366 và note dài 390; hai calibration cũ PASS. Lần này không chạy lại stress 240 lịch; kết quả stress trước giữ nguyên là bằng chứng lịch sử, cap 200 vẫn thuộc T08.
- [PASSED] T04a trong phạm vi primitive/toolbar: 320/390/1366, height/font/không tràn đều PASS. Chưa kiểm chứng thiết bị thật/bàn phím ảo/screen reader; nút trạng thái và dialog tiếp tục thuộc task sau.
- Production run `010d1f34-5f0a-424b-8815-07bfaabe5171`: **19 PASS, 4 FAIL** (48.67s): test cũ đều PASS, bốn ca bổ sung xác nhận R7-01/02/03. Có log Playwright `Target closed` lúc teardown sau ca tái hiện; assertion chính đã fail trước teardown, không dùng log này để kết luận lỗi ứng dụng.
- Dev run `1ad3e8e9-c939-4d3f-82b7-60176936e8bb`: **4 PASS, 1 FAIL, 4 deselected** (25.60s): bốn màu qua branding provider PASS, copy dùng thẻ FAIL. Không có setup JWT error ở hai lượt này; QA-04 chưa đóng vì chưa sửa/xác định nguyên nhân. Không chạy backend suite hoặc full E2E trong lượt review.
- Reproducer chạy tường minh qua runner, không nằm trong discovery mặc định. Không xfail/skip các lỗi; sau vá đưa regression phù hợp vào suite thường. Lệnh và artifact tại mục cuối PROGRESS.

Kết luận nghiệm thu: 4/7 task đã triển khai đạt phạm vi (T00a/T00b/T04a/T03a); mở lại T00c/T02/T04b. Tổng plan: 4/29 đã nghiệm thu, 3 cần sửa lại, 22 chưa triển khai. Ưu tiên đóng R7-01–04 trước nhóm C.

## Vá và nghiệm thu lại T02/T00c/T04b — 19/10/2026

- [PASSED] **R7-01 / T02:** callback refresh sau mutation trỏ tới scope đang hiển thị; chỉ hoạt động nếu vẫn mounted và cùng danh tính/chi nhánh của mutation. Chặn response cũ vẫn giữ nguyên. Status/create/reschedule dùng chung; lỗi PATCH cũng đối chiếu lại server trước khi hiển thị thông báo lỗi. 16 ca calendar loading PASS, gồm 9 ca mới: đổi lọc/ngày/tuần trong lúc PATCH chờ × thành công/từ chối/phản hồi lỗi sau commit. Test xác minh trạng thái server và GET scope mới, không chỉ kiểm tra chữ trên màn hình.
- [PASSED] **R7-02 / T00c:** gate từ chối phần ngoài viewport không được phép và target rỗng. JSON ghi cardCount/cardSelector/measurementStatus; collector đo đúng modal, collection, notification, package. Cuộn dọc modal khai báo riêng, chỉ loại việc cắt ở scroll container đó; vẫn bắt tràn ngang/clipper con. 6 calibration PASS; 44 mẫu có target thực, 14 mẫu stress qua gate (10 KTV/210 khách/240 lịch, 7 width). 0 card violations; cap tuần 200/240 vẫn thuộc T08, không được gọi là đã hiển thị đủ lịch.
- [PASSED] **R7-03/04 / T04b:** fixture dùng branding response qua provider; assert nền và foreground thực tế ở vàng/gần trắng/xanh đậm/đen. Wizard chọn/xác nhận dùng thẻ chuyển sang buổi thẻ; tiền tổng là khoản dự kiến thu thêm ngoài thẻ khi có thẻ. Ca thẻ riêng và thẻ + dịch vụ lẻ PASS với 0/125.000; E2E đặt thẻ giữ item/package ID, giá 0 và số buổi giữ chỗ PASS. Chỉ thay copy/bố cục nhỏ, không đổi payload/giá/giao dịch.
- [PASSED] Regression đưa vào suite thường: `features/admin_bookings/tests/test_calendar_loading.py` và `features/ui_quality/tests/test_ui_quality.py`; entry point review cũ chuyển sang import các test thực, không giữ test fail/xfail riêng. Production build PASS, **55/55 PASS** (220.91s); **23 unit harness PASS**. Lượt dev trước đó 40/40 PASS (151.31s), sau đó bổ sung hiệu chuẩn cuộn dọc và chạy lại trên production. Không chạy full backend suite hoặc toàn bộ tính năng E2E vì phạm vi không đổi backend.
- [WARNING] **UX-07 / T11c:** popup Admin 320px tràn trái, có 5 phần tử ngoài viewport dù documentWidth = 320 và nội dung trong card không tràn. Detector mới ghi nhận đúng thay vì bỏ lọt. [Ảnh](../automation_test/artifacts/ui-review/76d5ebba-de8f-4832-9f18-b1f1b6b29e7d/T00c-collector/320x844-notifications.png), source `frontend/src/components/admin/notification-bell.tsx:173`. Các mẫu 360px trở lên không tái hiện với dataset này. Lỗi được giao T11c, chưa vá trong phạm vi công cụ đo.
- QA-04 không tái hiện ở các lượt này nhưng chưa đóng vì chưa có bản sửa nguyên nhân. Log DecodeError thuộc test token sai chủ ý; không nhầm với lỗi setup JWT thời gian. Thiết bị thật, bàn phím ảo, screen reader và các task còn lại chưa nghiệm thu.

Bằng chứng production: `automation_test/artifacts/qa/76d5ebba-de8f-4832-9f18-b1f1b6b29e7d/` và `automation_test/artifacts/ui-review/76d5ebba-de8f-4832-9f18-b1f1b6b29e7d/`. Đã xem ảnh popup 320px và kiểm tra JSON coverage. Kết luận: **7/7 task đã triển khai đạt phạm vi nghiệm thu, tổng 7/29; còn 22 task**. Không suy diễn thành UI/UX toàn sản phẩm hoặc release đã sẵn sàng.

## Nhóm C — Nghiệm thu phạm vi dialog, lịch và thu tiền — 19/10/2026

- [PASSED] **T05a / UX-04:** native dialog có tên/mô tả, Tab/Shift+Tab, focus ban đầu/restore/fallback và khóa nền/scroll. Dirty có bỏ/tiếp tục, pending/chưa rõ kết quả không Escape/backdrop đóng. Manual/payment có history guard; không nhân đôi form theo breakpoint. Đã sửa return focus khi opener bị khóa lúc chuẩn bị khoản thu và giữ theme shell qua portal. Các caller ngoài nhóm C còn phần policy nghiệp vụ riêng tại T09/T10.
- [PASSED] **T05b / UX-04/08/12:** manual dùng header/footer riêng và body cuộn; CTA/close trong viewport 320x480, 390x844, 1366x768. Input cuối tiếp cận được, select mobile đủ height/font, slot min 44px; customer nav có safe area. Pending giữ field và chặn đóng; 409 giữ lựa chọn; 503/đã có thay đổi một phần chuyển sang đối chiếu thủ công, không tự gửi lại. Có thể xem lịch rồi trở lại draft trong trang. Reload được kiểm tra riêng: không giữ draft và không replay request. Recovery nhiều buổi/idempotency tự động vẫn thuộc T01, chưa được giải quyết bởi container này.
- [PASSED] **T03b / UX-01/03/17:** một hành động tiếp theo trên card, các thao tác khác trong Modal chi tiết có đủ khách/giờ/dịch vụ/thẻ. Hoàn thành/hủy/vắng mặt có xác nhận; kiểm tra hoàn thành dùng đúng 1 buổi, hủy xác nhận không đổi server. Giữ vị trí cuộn sau mutation trong cùng scope; regression 30 lịch thật kiểm tra scroll và trạng thái API. Giữ request/scope guard của T02, không sửa API transition.
- [PASSED] **T06 / UX-05:** ô tìm kiếm toàn hàng mobile, tên/tiền và nút không tranh chỗ; chọn dòng mở Modal cùng một ledger, header có khách/dịch vụ, CTA có số tiền. Row30 đúng customer/package ID, sau resize/thu một phần/đóng vẫn giữ vị trí và focus. Mất response sau commit thử lại cùng UUID/body, entries không trùng; refresh lỗi khóa thu tiếp, đủ/một phần/hoàn tác/STAFF403 đều PASS. Không đổi thuật toán tiền, receive/reverse hoặc API payload.
- Production cuối **05e51f6a-7512-4a87-8c72-137fc391bf81: build PASS, 73/73 PASS (171.35s)**; unit harness 23/23 PASS. Trước đó 71/71 production PASS và 2 focused dev PASS; các lỗi phát hiện trong vòng sửa được lưu tại PROGRESS, không xfail/retry để che lỗi. Lỗi prepare cũ được thêm readiness trước fault injection; không suy diễn từ một lượt xanh rằng QA-04 đã hết.
- Theo PO giảm artifacts: regression layout chỉ đo DOM khi PASS, chỉ ghi PNG/JSON nếu assertion lỗi; đợt này không chạy collector ảnh/stress hàng loạt. Log và HTTP rewrite/SSR proof vẫn giữ theo run ID; không xóa ảnh lịch sử. Vùng cuộn modal mới dùng data-modal-scroll trong phép đo, vẫn bắt clip ngang/clipper con.
- [WARNING] Chưa kiểm chứng iOS/Android thật, bàn phím ảo, screen reader và toàn bộ caller; T12 tiếp nhận. UX-07 popup 320px còn T11c; T01 và T07/T11b giữ các gate recovery/phiên/đổi chi nhánh. Backend/RLS/ownership/giá/UUID business không thay đổi trong nhóm C.

Tiến độ: **11/29 task nghiệm thu trong phạm vi; còn 18**. Nhóm tiếp theo D (T07a/T07b/T07c) cần review phiên/quyền. Bằng chứng tại automation_test/artifacts/qa/05e51f6a-7512-4a87-8c72-137fc391bf81/; lệnh chạy tại cuối PROGRESS.
