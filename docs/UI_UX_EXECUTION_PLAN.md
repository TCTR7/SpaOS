# Kế hoạch review và cải thiện UI/UX mobile

Ngày cập nhật: 19/10/2026. Bản 2 — ĐANG TRIỂN KHAI THEO NHÓM. Đã sửa và kiểm chứng lại T00c/T02/T04b, đóng R7-01–04; 7/29 task đạt phạm vi nghiệm thu, còn 22. Production build và 55/55 ca kiểm tra PASS; xem PROGRESS để biết phạm vi/giới hạn. T00c đạt công cụ đo, không có nghĩa mọi màn UI đã đạt. Full release gate chưa hoàn tất.

## Cách dùng cho conversation/model tiếp theo

1. Đọc AGENTS.md, mục mới nhất PROGRESS.md, MULTI_BRANCH_STRATEGY.md; đọc yêu cầu nghiệp vụ liên quan trong PRD/API_CONTRACT. Sau đó chỉ đọc task được giao, UX-ID trong UI_UX_REVIEW.md và mục thiết kế tương ứng trong MOBILE_UX_DESIGN.md.
2. PO đã cho phép triển khai theo nhóm task liên quan. Dùng các nhóm bên dưới, làm tuần tự theo dependency và kiểm chứng chung ở cuối nhóm. Khi chỉ được giao review thì mặc định KIỂM TRA; chỉ dẫn mới của người dùng ưu tiên hơn prompt mẫu.
3. Tìm lại symbol vì số dòng là mốc review. Không quét monorepo hoặc đường dẫn cấm. Không lùi/xóa chỉnh sửa của người dùng.
4. Phân biệt ĐÃ XÁC NHẬN / RỦI RO CHƯA TÁI HIỆN / KHÔNG TÁI HIỆN VỚI MẪU / ĐÃ SỬA VÀ KIỂM CHỨNG. Không đổi rủi ro thành PASS chỉ vì chưa gặp lỗi.
5. Lỗi ngoài task: ghi bằng chứng và task tiếp nhận. Thay đổi API/quyền/giao dịch phải có quyết định thiết kế và review riêng, không lẫn vào task CSS.

### Prompt bàn giao

> Đọc AGENTS.md, phần mới nhất docs/PROGRESS.md và docs/UI_UX_EXECUTION_PLAN.md. Thực hiện task T__ ở chế độ KIỂM TRA. Giới hạn theo file và UX-ID của task. Chỉ chạy runtime sau khi T00a/T00b đạt; dùng QA database riêng, không mở/tắt server 3000, không đọc các đường dẫn bị cấm hoặc secrets. Báo file:dòng, expected/actual, bằng chứng và giới hạn. Cập nhật trạng thái task và PROGRESS. Không tự sửa API/quyền/giao dịch.

Khi muốn sửa, đổi thành “TRIỂN KHAI task T__ trong phạm vi và tiêu chí đã nêu”. Nếu đã giao triển khai và đủ điều kiện đầu vào thì thực hiện, không hỏi lại quyền. Nếu vướng quyết định API chưa chốt, hoàn tất phần độc lập và ghi rõ phần còn chờ.

## Nguyên tắc giữ nguyên

- Tenant/role/customer ownership do backend kiểm soát; không trả tên/SĐT/hồ sơ ngoài quyền để làm đầy UI.
- Không hủy rồi tạo lại để sửa lịch; KTV thực hiện khác KTV phụ trách hồ sơ. Không chuyển quyền ngầm.
- Giá/thời lượng/số buổi theo snapshot/server. Không tính lại tiền ghi sổ từ giá menu hay số hiển thị.
- Retry thu tiền/cấp chủ spa khi chưa rõ kết quả phải giữ UUID và payload. Không remount component làm mất trạng thái giao dịch rồi cho gửi giao dịch mới.
- Lỗi tạm thời không được xóa token, nhưng cũng không được coi phiên chưa xác minh là hợp lệ. Không giữ dữ liệu riêng của phiên/chi nhánh cũ trên màn hình mới.
- Không seed vào database ứng dụng, không đọc/in .env hoặc credential thật. Được chạy binary đã cài, không đọc/quét node_modules, .next, venv, .venv, __pycache__, .git, dist, build, *.lock, package-lock.json.
- Không đổi framework/nâng dependency để sửa layout; không dùng any. Không sửa RLS/transaction/API payload trong task UI.
- Không dùng overflow-x-hidden toàn trang, giảm font/che tên/tiền hoặc tăng sleep/retry để làm test qua.
- Đổi copy có thể cập nhật selector/POM tương ứng; vẫn phải giữ assertion về quyền, số tiền, số buổi và dữ liệu server.

## Những chỗ đã sửa trong plan bản 2

- Bắt buộc xử lý harness tự khởi động 3000 và cô lập cả API phía Next.js server trước chạy QA. Đổi port hoặc browser route riêng chưa đủ.
- Tách task rộng thành task lá; đường dẫn types đúng là frontend/src/lib/types.ts. Sửa đường dẫn nhóm test ownership thành customer_regressions/tests/test_ownership_reschedule.py.
- Bổ sung UX-25, UX-26: lỗi mạng làm mất phiên Admin và bị báo nhầm “Spa không tồn tại”.
- Chốt phạm vi UI ban đầu, tránh model nhỏ tự thêm route/framework/chế độ lịch mới. Luồng có giao dịch không bị đổi vòng đời state chỉ vì chuyển sang sheet.
- Bổ sung các màn trước đây chưa có coverage rõ: login/register, chọn chi nhánh, settings, cấp quyền chi nhánh và Operator.
- Trạng thái 19/10: T00a/T00b/T00c/T04a/T04b/T02/T03a đạt phạm vi (7/29), R7-01–04 đã đóng. Còn 22 task. QA-04 vẫn chưa có bản sửa nguyên nhân; các lượt chạy không tái hiện không đóng blocker này.

## Nhóm triển khai theo yêu cầu PO

- A — Nền QA và UI cơ bản: T00a/T00b/T00c/T04a/T04b. Đã nghiệm thu; T00c/T04b được sửa và kiểm chứng lại ngày 19/10.
- B — Tính đúng và bố cục lịch: T02 → T03a. Đã nghiệm thu; T02 đã thêm refresh scope hiện tại sau mutation, 9 regression đổi scope/kết quả PATCH PASS.
- C — Dialog, thao tác lịch và thu tiền: T05a → T05b → T03b/T06.
- D — Phiên đăng nhập, lỗi mạng và tenant: T07a/T07b → T07c; review quyền sau sửa.
- E — Contract dữ liệu, wizard và dời lịch: T08a → T08b, T09b → T09a/T09c theo dependency. Chốt API trước sửa backend.
- F — Nhiều buổi thành công một phần: T01a → T01b. Có thể điều tra ngay sau A; không bỏ qua trước pilot.
- G — CRM, báo cáo và thẻ: T10a/T10b/T10c sau các dependency tương ứng.
- H — Shell, chi nhánh, dashboard và màn phụ: T11a/T11b/T11c/T11d theo dependency trong nhóm.
- I — Gate tổng: T12. Không coi nhóm A hoàn tất là release đã sẵn sàng.

## Trình tự và quyết định thiết kế

- Nền QA: T00a → T00b → T00c. Có thể source-review bất kỳ task trước đó; chưa chạy collector/E2E theo hướng dẫn cũ khi nền QA chưa đạt.
- Đợt UI đầu: T04a, T04b, T02, T03a. T02 và T03a làm tuần tự vì cùng file lịch; T03a phụ thuộc T02. T04b xử lý sớm credentials demo/nhãn KTV/theme.
- Sau đó: T05a → T05b → T03b/T06; T07a/T07b/T07c làm riêng và có review phiên đăng nhập.
- Điều tra T01a, T08a, T09b có thể làm sớm. Triển khai phần API chỉ sau quyết định được lưu; không coi nhóm này sẵn sàng giao sửa tự do.
- T08b → T09a; T09c sau T09b và các API cần thiết đã được kiểm chứng. T10/T11 theo dependency riêng, cuối cùng T12.
- Một người sửa một file tại một thời điểm, đặc biệt bookings/page.tsx, customer-context.tsx và shell.

Quyết định UI cho đợt đầu:
- T03a giữ nguyên URL, bộ lọc và handler. Mobile tuần dùng nhóm ngày; tablet/PC chọn layout theo không gian nội dung, có thể scroll cục bộ. Chưa thêm timeline theo 10 KTV, drag/drop hoặc thư viện lịch.
- T03b dùng chi tiết trong modal/sheet chung. Không đặt button bên trong button khi card có thao tác con; card mở chi tiết phải dùng được bằng bàn phím.
- Form dài dùng view tập trung trong route hiện tại trước; mobile toàn chiều cao khả dụng, desktop dialog có giới hạn. Chưa thêm route mới. Nút Quay lại và browser Back phải được kiểm tra, không mặc định state trong memory đã giữ qua reload.
- Thu tiền dùng một instance ledger trong luồng xác nhận; chỉ đổi bố cục/container. Dirty/pending state sống ở cấp không bị đóng sheet hoặc breakpoint làm mất.
- Chưa có dialog library trong package.json. Ưu tiên sửa primitive hiện có theo tiêu chí T05a; nếu cần thêm thư viện thì tách đề xuất dependency, không giả định shadcn/Radix đã được cài.
- Chỉ một bề mặt tương tác có thể nhận focus ở mỗi breakpoint. Không nhân đôi form mobile/desktop với cùng ID, hidden focus hoặc hai lần submit.

## T00 — Nền QA và bằng chứng

### T00a — Ngăn harness khởi động nhầm frontend

- [x] ĐÃ TRIỂN KHAI VÀ KIỂM CHỨNG 18/10/2026. Không phụ thuộc.
- Đã bỏ subprocess/start/kill khỏi fixture; preflight HTTP chỉ đọc. URL phải HTTP loopback, có port riêng khác 3000. Mặc định 127.0.0.1:3001; thiếu/sai cấu hình fail rõ.
- GET /admin/login phải 200 text/html và header X-SpaOS-QA-Run-ID khớp UUID SPAOS_QA_RUN_ID của runner. Không follow redirect/proxy môi trường, timeout 5s, không retry hay dùng tạm server khác.
- Kiểm chứng: 12/12 unittest PASS. Trước nối preflight, fixture cũ thất bại đúng 3 regression (unreachable gọi spawn, chấp nhận 404, chấp nhận HTML không có marker); mọi I/O/process đã được mock, không mở server.
- File bổ sung: automation_test/common_setup/frontend_preflight.py và automation_test/harness_tests/. isolated_backend phụ thuộc preflight để không tạo QA DB khi frontend chưa đạt.
- Giới hạn: T00b chưa tạo producer header/runner nên E2E hiện sẽ bị chặn nếu không chứng minh được frontend QA. Không tự sửa .env.test hoặc bỏ marker để chạy tạm.
- File: automation_test/conftest.py, common_setup/config.py trong automation_test; test helper nếu cần.
- Baseline đã xác nhận: ensure_frontend_server cũ gọi npm run start không truyền port; package.json cố định 3000. FRONTEND_URL=3001 không ngăn nhánh fallback mở 3000.
- Thiết kế: khi URL chỉ định không sẵn sàng, fail với thông báo rõ; không tự start trên cổng mặc định. Không nhận server bất kỳ chỉ vì trả <500 mà coi là đúng bản QA.
- Nghiệm thu: URL 3001 không hoạt động không sinh process 3000; cổng bị chiếm không bị kill/reuse ngầm; teardown chỉ quản lý PID do lượt QA tạo.

### T00b — Cô lập frontend QA và API phía server

- [x] ĐÃ TRIỂN KHAI 18/10/2026. Runner production/dev dùng một backend QA; HTTP rewrite + title SSR chứng minh cùng DB tạm. Output/config/build-info QA riêng, fingerprint tsconfig/next-env giữ nguyên trong các lượt chạy. Header QA tắt ở cấu hình thường.
- Unit harness: 23/23 PASS, gồm lỗi build/start/preflight/port bị chiếm/interrupt/pytest exit code. E2E toàn bộ vẫn có lỗi JWT setup được ghi riêng; không gọi là PASS toàn suite.
- File: automation_test/conftest.py, common_setup/qa_backend.py; helper frontend QA mới trong common_setup nếu cần; frontend/next.config.mjs chỉ để tách output QA.
- Contract nối T00a: runner tạo UUID SPAOS_QA_RUN_ID mới, truyền cùng giá trị cho frontend và pytest. Chỉ frontend QA trả X-SpaOS-QA-Run-ID tại /admin/login; header không bật trên cấu hình ứng dụng thường/production. Marker xác nhận đúng lượt frontend, không thay kiểm tra backend/SSR bên dưới.
- T00b phải tổ chức lại lifecycle: hiện isolated_backend phụ thuộc preflight của T00a; không thêm chiều phụ thuộc ngược gây vòng lặp. Runner tạo một backend dùng chung trước frontend, sau đó preflight rồi mới cấp fixtures cho test, không tạo DB QA thứ hai.
- UUID header chuẩn lowercase có dấu gạch; nếu dùng Next headers()/rewrites qua build config, phải truyền UUID/backend origin trước build và giữ cùng giá trị khi start. Không chỉ truyền lúc start rồi dùng output của lượt cũ.
- Thiết kế: vòng đời QA backend bắt đầu trước frontend QA. Truyền BACKEND_INTERNAL_URL tới backend QA cho Next.js, NEXT_PUBLIC_API_URL dùng /api/v1. Rewrite/browser request và SSR metadata cùng dùng backend QA. Không lấy URL main backend từ env thật.
- Dùng output Next riêng cho QA qua cấu hình môi trường có kiểm tra đường dẫn, chẳng hạn .next-qa; mặc định ứng dụng vẫn .next. Cùng cấu hình output/backend khi build và start. Không đọc/quét output sinh ra; không build ghi đè .next của server người dùng.
- Chỉ runner sở hữu frontend QA mới được tự start/stop trên cổng dành riêng đã kiểm tra, mặc định 3001. Có thể chạy dev cho vòng sửa ngắn; gate cuối phải kiểm tra production build trong cùng môi trường QA. Không thay .env thật.
- Nghiệm thu: tenant ngẫu nhiên chỉ có trong DB QA xuất hiện đúng cả nội dung browser và title metadata; không request API tới backend chính. Kiểm tra fail setup/interrupt vẫn đóng đúng process/container, chỉ drop DB tạm có prefix/ID của lượt chạy.
- Sau triển khai phải ghi lệnh runner thực tế vào mục Lệnh kiểm chứng. Không tự đoán runner đã có. T00b chưa đạt thì chỉ review source, không chạy lại collector bằng cấu hình cũ.

### T00c — Collector và regression layout

- [x] SỬA VÀ KIỂM CHỨNG LẠI 19/10/2026 — R7-02 đóng. Gate kiểm tra viewportOutsideCount, thiếu target fail rõ; cardCount/cardSelector/measurementStatus ghi trong JSON. Collector chọn đúng modal/collection/popup/package và bắt buộc có target. Cuộn ngang/dọc khai báo riêng, không bỏ qua clip ngang hoặc clipper con. 6 calibration và 3 regression lịch PASS; 44 mẫu thường đều đo được, 14 mẫu stress qua gate. Popup thông báo 320px vẫn vượt viewport (UX-07/T11c), được báo lỗi thay vì coi là PASS UI.
- Bằng chứng lịch sử: collector 44 mẫu, stress 14 mẫu với 10 KTV/210 khách/240 lịch; artifact theo UUID. Ba ca strict xfail ban đầu nay đã PASS trong T03a. Cap 200/240 vẫn thuộc T08. Không suy diễn các màn có cards=[] đã qua kiểm tra card.
- File: automation_test/reviews/layout_probe.py; fixture customer_regressions/conftest.py; tests layout được thu thập riêng.
- Artifact có run ID/task/viewport, không ghi đè ui-review-20261018. Lưu ảnh + viewport/card bounds + route/role/dataset, không lưu token/PII thật.
- Collector hiện chỉ thu ảnh/số đo, không có assertion UI đạt. Thêm regression cho lỗi đã xác nhận: baseline thất bại vì đúng lỗi, sau sửa qua. Collector vẫn có thể giữ vai trò thu bằng chứng.
- Đo cả viewport và clipping/overlap trong card; chỉ loại trừ vùng scroll chủ ý bằng selector rõ, không loại toàn bộ bảng/lịch để làm số đẹp.
- Width 320/360/390/430/768/1024/1366; height thấp thêm cho sheet. 10 KTV, 50+ lịch/ngày, hơn 200 khách và hơn 200 lịch qua nhiều ngày khi test phân trang; tên 80 ký tự, note 280 ký tự không khoảng trắng, tiền lớn hợp lệ.
- Dữ liệu fixture không vi phạm ca/buffer/khả dụng thẻ. Thời gian Asia/Ho_Chi_Minh; không phụ thuộc múi giờ máy chạy.
- Chờ request đúng method/path/query/ID và UI đã render. Một response về chưa chứng minh React đã cập nhật. Không networkidle với polling, không sleep cố định.
- Bài kiểm tra fault-injection phải forward tới QA rõ ràng. “Mất response sau commit” phải thật sự gửi request, xác nhận server đã tạo, rồi mới làm rơi response; abort trước gửi không kiểm tra idempotency.

## T01 — Tạo nhiều buổi thành công một phần

### T01a — Tái hiện và chốt cách khôi phục [review giao dịch]

- [ ] CHƯA LÀM. Sau T00c. UX-21.
- File: frontend/src/app/(admin)/admin/bookings/page.tsx handleCreateManualBooking; frontend/src/lib/api.ts; API_CONTRACT; fixture booking.
- Ca: tạo khách nhanh + thẻ + 3 buổi, buổi 2 trả 409/503; riêng ca commit thành công nhưng mất response. Đếm ID khách/thẻ/lịch trước/sau và hành vi retry/đóng form/reload.
- Đầu ra bắt buộc: quyết định atomic batch/idempotency hay recovery từng bước, contract/payload/lỗi và cách đối chiếu phần đã thành công. Chưa có quyết định trong plan này.
- Không tự xóa phần đã tạo, không Promise.all để “sửa”, không chạy lại toàn chuỗi khi chưa biết kết quả.

### T01b — Triển khai theo quyết định T01a

- [ ] CHỜ T01a. Chỉ giao khi T01a đã chốt file/API, test đồng thời và migration nếu cần.
- Nghiệm thu: không cấp thêm thẻ/lịch khi retry kết quả chưa rõ; thông báo đúng từng phần đã tạo. Backend kiểm chứng tenant/ownership/concurrency nếu có thay đổi. UI đẹp không thay thế gate này.

## T02 — Response lịch cũ và dữ liệu tham chiếu

- [x] SỬA VÀ KIỂM CHỨNG LẠI 19/10/2026 — R7-01 đóng. refreshAfterMutation dùng callback scope hiện tại, kiểm tra danh tính/chi nhánh gốc và mounted; status/create/reschedule đều dùng chung. Nhánh lỗi tải lại dữ liệu vì server có thể đã commit; thông báo lỗi vẫn hiện sau đổi lọc. 7 regression cũ + 9 ca mới (lọc/tuần/ngày × thành công/từ chối/phản hồi lỗi sau commit) PASS trên production.
- Bảy ca race/error/reference PASS trong lượt dev b1fa70d6; lượt production cuối sáu ca PASS, một ca không dựng được fixture do QA-04. Không thay API hoặc nới quyền. Test alert giới hạn trong main để tránh bắt Next route announcer.
- File: frontend/src/app/(admin)/admin/bookings/page.tsx loadBookings/loadReferenceData; automation_test/features/admin_bookings.
- Delay A → chọn B → B về trước → A về sau. Lặp A lỗi sau B thành công, đổi ngày/KTV/trạng thái, reload sau mutation khi request cũ đang chạy.
- Guard request identity bao phủ data/loading/error và cả reload thủ công. Dữ liệu ngày cũ không được hiện dưới tiêu đề mới khi request mới lỗi.
- Reference lỗi có trạng thái/Thử lại riêng; thao tác cần danh mục chưa xác minh phải bị khóa, phần độc lập vẫn dùng được. Không thay API.

## T03 — Lịch ngày/tuần

### T03a — Bố cục và chống tràn

- [x] ĐÃ TRIỂN KHAI VÀ KIỂM CHỨNG 18/10/2026. Mobile/tablet agenda theo ngày, ngày trống một dòng; PC 7 cột đủ rộng với scroll ngang cục bộ và scroll dọc trong ngày nhiều lịch. Thẻ tuần gọn, native details mở đủ dịch vụ/ghi chú/hành động; tên và giá chính không bị cắt. Note/tên/service dài wrap đúng cấp.
- Ba regression UX-01/02 PASS, cả closed/expanded. Production build PASS; 44 mẫu thường và 14 mẫu stress (10 KTV/210 khách/240 lịch) có documentWidth bằng viewport và card violations=0. Không có nghĩa mọi accessibility/phone thật đã đạt; T03b/T12 vẫn mở.
- File: frontend/src/app/(admin)/admin/bookings/page.tsx renderBookingCard/calendar body; component hiển thị mới nếu cần. Không đổi handler ghi.
- Mobile ngày/tuần đọc được giờ, khách, KTV, trạng thái; ngày trống một dòng. PC/tablet không ép nội dung vào 7 cột hẹp. Chuỗi dài ngắt đúng cấp; badge wrap.
- Ảnh trước/sau cùng dataset 768/1366 và note dài 390. Document width <= viewport+1px; card không bị che/cắt. Vùng scroll chủ ý nằm trong viewport và có cách xem hết.
- Regression admin_bookings, customer_regressions/tests/test_ownership_reschedule.py và bounds mới.

### T03b — Chi tiết và hành động theo trạng thái

- [ ] CHƯA LÀM. Sau T03a/T05b. UX-01, UX-03, UX-17.
- Cùng file/component lịch. Card gọn mở chi tiết, một hành động tiếp theo rõ; menu phụ không che quyền/confirmation hiện có.
- Nội dung đủ để đối chiếu trước cập nhật trạng thái; hoàn thành thẻ/hủy/vắng mặt đúng nghiệp vụ. Keyboard và quay lại vị trí lịch; không đổi transition API.

## T04 — Primitive và copy

### T04a — Nút/input

- [x] ĐÃ TRIỂN KHAI VÀ KIỂM CHỨNG 18/10/2026. Shared targets 44–48px và input mobile 16px; desktop giữ kích thước cũ, thêm focus offset. Toolbar ngày wrap ở phone; test 320px không tràn. Các nút trạng thái trực tiếp trên card vẫn thuộc T03b.
- File: frontend/src/components/ui/button.tsx, input.tsx; chỉ caller cần điều chỉnh trực tiếp.
- Target chính 44–48px, input mobile 16px; tránh tăng global khiến bảng PC vỡ. Focus-visible/label/error/inputMode đúng; icon button có accessible name.
- Kiểm tra mobile và desktop, disabled/loading, Enter submit một lần; không viết test riêng cho từng spacing/copy.

### T04b — Theme, ngôn ngữ và dữ liệu demo

- [x] SỬA VÀ KIỂM CHỨNG LẠI 19/10/2026 — R7-03/04 đóng. Test branding qua provider, assert đúng nền/foreground cho vàng/gần trắng/xanh đậm/đen. Wizard diễn đạt dùng 1 buổi trong thẻ, nhãn thu thêm ngoài thẻ khi có thẻ; wrap nhãn dài. Hai ca thẻ riêng/thẻ + dịch vụ lẻ xác nhận số tiền dự kiến 0/125.000; E2E dùng thẻ giữ item ID/total_price/giữ chỗ PASS. Không đổi giá/payload server. Thiết bị thật vẫn thuộc T12.
- File: customer book/profile/appointments; admin bookings; admin-shell; helper theme hiện có.
- Bỏ credentials điền sẵn; “KTV thực hiện” trên lịch, “KTV phụ trách hồ sơ” trong hồ sơ; trạng thái tiếng Việt, giải thích giữ chỗ.
- Chữ phụ/icon selected dùng foreground phù hợp; thử màu vàng/gần trắng/xanh đậm/đen, focus/disabled/selected.
- Cập nhật POM theo accessible name mới, giữ kiểm tra số buổi/quyền. Không thay token, API, giá hoặc role.

## T05 — Modal và form

### T05a — Primitive dialog

- [ ] CHƯA LÀM. Sau T04a. UX-04.
- File: frontend/src/components/ui/modal.tsx và caller để thêm props/accessibility cần thiết.
- Accessible name/description, initial focus, Tab/Shift+Tab trap, restore focus (fallback khi nút mở đã mất), khóa scroll nền và tương tác nền. Cleanup đúng khi unmount.
- Escape/backdrop theo chính sách caller: cho đóng bình thường; đang ghi/kết quả chưa rõ không đóng; dirty có bỏ/tiếp tục. Không chồng dialog và không khóa focus mất lối thoát.
- Test bàn phím thật qua Playwright; riêng keyboard ảo/iPhone là gate thiết bị T12.

### T05b — Form dài trên điện thoại

- [ ] CHƯA LÀM. Sau T05a. UX-04, UX-08, UX-12.
- Phạm vi lần đầu: container dùng chung và caller tạo lịch thủ công; customer-shell chỉ cho safe area. Các caller dời lịch/CRM/staff áp dụng container ở T09/T10, không sửa gộp ở đây. Không đổi field/API.
- View tập trung trong route hiện tại, header/footer truy cập được với màn thấp; không chồng nav/CTA, không che input cuối. Giữ form khi lỗi/409.
- Đóng/hủy/back trong lúc pending không làm mất state cần retry; resize không remount giao dịch. Phân biệt browser Back, nút Back và reload.

## T06 — Thu tiền mobile

- [ ] CHƯA LÀM. Sau T05b. UX-05.
- File: frontend/src/app/(admin)/admin/payments/page.tsx, components/admin/payment-ledger.tsx; lib/payment-api.ts chỉ đọc; automation_test/features/admin_payments.
- Ô tìm kiếm toàn hàng, tên/tiền không bị nút ép nhỏ, nút mobile dưới thông tin. Chọn dòng thứ 30 mở đúng khách/chi nhánh và CTA có tiền; trở về đúng vị trí sau thành công.
- Không đổi UUID/payload/retry/amount calculation. Sheet đóng hoặc breakpoint không tạo ledger mới mất pending state.
- Regression đủ/một phần/hoàn tác, mất response sau commit, refresh lỗi sau commit, STAFF bị từ chối. Kiểm tra count/số tiền server, không chỉ toast. Thay logic ledger phải tách review.

## T07 — Lỗi mạng, xác thực và tải slots

### T07a — Phiên Customer [review ranh giới quyền]

- [ ] CHƯA LÀM. Sau T00c. UX-14.
- File: frontend/src/components/customer/customer-context.tsx, frontend/src/lib/customer-api.ts; customer_regressions.
- auth/me 503/network giữ token, xóa/ẩn dữ liệu chưa được xác minh, có Thử lại; không enable ghi dữ liệu trước xác minh.
- 401 của phiên hiện tại chỉ xóa token đúng slug; không ảnh hưởng Admin/slug khác. Response cũ sau đổi slug/logout/đăng nhập lại không set user hay xóa token mới; guard ở cả context và API helper.
- Review sau sửa; không sửa JWT/middleware/backend permission.

### T07b — Phiên Admin [review ranh giới quyền]

- [ ] CHƯA LÀM. Sau T00c. UX-25.
- File: frontend/src/components/admin/auth-context.tsx, frontend/src/lib/api.ts; admin_auth/admin_branches.
- Cùng ma trận 503/network/401 và response muộn như T07a, thêm đổi branch, tab khác logout/switch. Không lưu lại token cũ sau response muộn.
- fetchBranches lỗi khác “không có chi nhánh”: có retry, không trình bày empty như quyền đã được xác minh. Giữ backend là nơi quyết định quyền.

### T07c — Tenant công khai và slots lỗi

- [ ] CHƯA LÀM. Sau T07a; phối hợp T02 cho lịch Admin. UX-14, UX-24, UX-26.
- File: customer-context/customer-shell, customer book/appointments, admin slots loader.
- Tenant 404 mới hiện không tìm thấy; 503/offline có thông báo và retry. Loading/error khi đổi slug không hiển thị chi nhánh cũ.
- Slots 200 rỗng khác 503/offline; giữ lựa chọn còn hợp lệ, khóa submit khi slots chưa xác minh. Response ngày/KTV cũ không ghi đè lựa chọn mới.
- Không đổi backend contract để chỉ phân loại lỗi HTTP đã có.

## T08 — Tên hiển thị và phân trang

### T08a — Chốt contract [API review]

- [ ] CHƯA LÀM. Sau T00c. UX-13, UX-16.
- File: frontend/src/lib/types.ts, api.ts/customer-api.ts; customer book/admin bookings; docs/API_CONTRACT.md. Backend chỉ mở phạm vi endpoint/schema liên quan.
- Quyết định cụ thể: display fields trong booking hay batch lookup theo quyền; nguồn KTV công khai độc lập slots đã lọc; phân trang lịch theo contract thực.
- Dữ liệu >200 khách, khách ngoài trang đầu, >200 lịch trong khoảng ngày, KTV hết giờ hôm nay nhưng còn ngày mai. Không tải vô hạn toàn CRM.
- Lưu method/path/query/DTO/errors/quyền, hành vi dữ liệu thiếu và test tenant/STAFF ownership/N+1. Không trả SĐT/notes/hồ sơ trong public staff DTO. Chưa có quyết định API cuối cùng ở bản plan này.

### T08b — API đã duyệt và UI tiêu thụ

- [ ] CHỜ T08a. Tách lượt backend và frontend nếu quyết định cần đổi cả hai.
- Backend tests quyền/cross-tenant trước; cập nhật API_CONTRACT rồi type/client. Không gọi thêm một request riêng cho mỗi card.
- UI hiện tên đúng quyền, có “còn dữ liệu”/phân trang rõ; không trình bày 200 kết quả như toàn bộ và không dùng UUID thay tên như trạng thái bình thường.

## T09 — Đặt lịch và dời lịch

### T09a — Wizard 3 bước

- [ ] CHƯA LÀM. Sau T05b/T07c/T08b. UX-13, UX-15.
- File: frontend/src/app/[tenant_slug]/book/page.tsx; automation_test/features/client_pwa_booking/pages/booking_wizard_page.py và tests liên quan.
- Dịch vụ/thẻ → Ngày giờ/KTV → Xác nhận. Không auto chọn slot hoặc nhảy bước thiếu dữ liệu; ngày quá khứ bị chặn cả mũi tên.
- Danh sách KTV không co theo slots đã lọc; đổi lựa chọn xóa slot không tương thích, Back giữ dữ liệu hợp lệ. Đăng nhập giữ lựa chọn, dùng thẻ vẫn cần auth.
- POM theo 3 bước, giữ assert server 409/ownership/thẻ. Submit nhanh hai lần không tạo hai lịch; slot stale có cách chọn lại trong cùng luồng.

### T09b — Chốt gợi ý giờ khi sửa lịch [API/concurrency review]

- [ ] CHƯA LÀM. Sau T00c, phối hợp T08a. UX-23.
- File: admin/customer reschedule, API_CONTRACT; booking endpoint/service/schema chỉ trong phạm vi sửa bug.
- Kiểm tra sửa note không đổi giờ; đổi KTV cùng giờ; menu đổi duration sau booking; giữ KTV khi không yêu cầu đổi; booking đã chuyển trạng thái không còn sửa được.
- Chốt API đề xuất nếu cần dùng snapshot và loại đúng booking đang sửa: xác minh tenant/ownership trước exclude, không nhận ID tùy ý để nới khả dụng. API gợi ý không thay kiểm tra lock/409 lúc PATCH.
- Lưu quyết định method/path/DTO/lỗi/tests; không giao model nhỏ tự suy ra cách sửa snapshot/locking.

### T09c — UI dời lịch theo contract đã chốt

- [ ] CHỜ T09b và backend cần thiết đã kiểm chứng; sau T05b/T07c.
- Giữ KTV hiện tại nếu không chọn đổi; không tự nhảy sang giờ đầu khác. Preview trước/sau, 409 giữ form và lịch gốc.
- Bàn giao chủ hồ sơ riêng, Admin-only, mặc định tắt. Kiểm tra ID/items/price/duration snapshot giữ nguyên và thẻ không bị giữ/trừ thêm ngoài nghiệp vụ.
- Regression customer_regressions/tests/test_ownership_reschedule.py + admin_bookings.

## T10 — Danh sách, chi tiết và báo cáo

### T10a — CRM/nhân sự

- [ ] CHƯA LÀM. Sau T05b. UX-10, UX-12.
- File: admin/customers/page.tsx và admin/staff/page.tsx (đầy đủ dưới frontend/src/app/(admin)); tách hai lượt nếu đổi nhiều.
- Danh sách → chi tiết có Quay lại, giữ tìm kiếm/vị trí, selection có keyboard semantics. Không thêm quyền truy cập chỉ để mở hồ sơ.
- Regression admin_crm_packages, admin_catalog/tests/test_staff_schedules.py, ownership.

### T10b — Dịch vụ/báo cáo

- [ ] CHƯA LÀM. Sau T04a. UX-09.
- File: admin/services/page.tsx, admin/reports/page.tsx.
- Mobile cards đọc đủ tiền/trạng thái, desktop giữ bảng hợp lý. Không duplicate focus/ID giữa hai layout.
- Commission là ước tính; thực thu khác giá trị dịch vụ, bộ lọc và kỳ báo cáo rõ. Regression admin_catalog/tests/test_services.py, admin_reports.

### T10c — Thẻ khách và màn rộng

- [ ] CHƯA LÀM. Sau T04b/T07c. UX-11, UX-12.
- File: frontend/src/app/[tenant_slug]/profile/page.tsx; customer-shell; customer home nếu cần breakpoint.
- Đã dùng/giữ chỗ/có thể đặt thêm/hạn dùng rõ; expired/hết buổi/giữ hết buổi khác nhau. “Dùng 1 buổi” không hàm ý thẻ đã thu tiền.
- Mở rộng PC hợp lý, vẫn đọc tốt phone. Regression automation_test/features/client_pwa_booking/tests/test_customer_package.py và automation_test/features/customer_regressions/tests/test_customer_safety.py.

## T11 — Shell, chuyển chi nhánh và các màn phụ

### T11a — Điều hướng và safe area

- [ ] CHƯA LÀM. Sau T03b/T06/T10a, dùng T05a. UX-08.
- File: admin-shell, customer-shell. Admin 5 mục, STAFF chỉ mục được phép; “Thêm” dùng menu/sheet trong shell, không tự tạo hệ route mới.
- Tất cả màn hiện có vẫn truy cập được; active tab đúng, Back/focus đúng; không chồng nav với form/action footer.
- Test deep link, reload, mobile landscape; safe area/keyboard thật tại T12.

### T11b — Guard chuyển chi nhánh [review phiên/giao dịch]

- [ ] CHƯA LÀM. Sau T07b/T05b/T06. UX-19.
- File: admin-shell/auth-context và caller khai báo dirty/pending.
- Dirty cho bỏ/tiếp tục; pending chưa rõ kết quả không đổi branch ngầm. Không lưu draft nhạy cảm vào localStorage.
- Giữ cơ chế clear state/token giữa các tab; không replay submit cũ vào branch mới. Test hai tab và request muộn, không chỉ dropdown một tab.

### T11c — Dashboard và popup thông báo

- [ ] CHƯA LÀM. Sau T11a/T07b; chia theo màn nếu cần. UX-07, UX-18.
- File: admin/dashboard, notification-bell hai phía.
- Tác vụ hôm nay sớm, metric chỉ dùng dữ liệu đã có và ghi rõ phạm vi; không tự thêm API/chỉ số chưa tồn tại. Tổng chi nhánh chỉ xem.
- Popup 320/360px và tên dài không tràn; danh sách rỗng/lỗi/nhiều thông báo, focus/đóng/retry. Đã xác nhận popup Admin tràn trái ở 320px ngày 19/10, 5 phần tử ngoài viewport; xem artifact run 76d5ebba, T00c-collector/320x844-notifications. Không suy diễn mọi popup đều lỗi.

### T11d — Coverage các màn còn lại

- [ ] CHƯA LÀM. Sau T04/T07/T11a tương ứng; kiểm tra từng màn, không sửa gộp mọi route.
- File: trang chọn chi nhánh /, admin/login, customer login/register, admin/branches, admin/settings, operator/login và operator/page; components branding.
- Xác nhận 320/390/768/1366, tên/SĐT/lỗi dài, bàn phím/label/loading/error, theme sáng/tối. Đây là checklist coverage, chưa gán lỗi khi chưa có bằng chứng.
- Admin không đăng ký tenant trên production; Operator riêng tạo chủ spa, customer register giữ luồng hiện tại. Không mở lại public owner signup theo tài liệu cũ.
- Giữ pending UUID/payload provisioning, logout/brand preview; không remount làm mất attempt. Regression admin_auth/admin_branches/operator_portal.
- Lỗi phát hiện mới phải ghi UX-ID/ảnh rồi giao task sửa có phạm vi, không coi “chưa kiểm” là “đã đạt”.

## T12 — Gate tổng hợp và pilot

- [ ] CHƯA LÀM. Các task trong phạm vi release đã kiểm chứng; T01/T08/T09 phải có kết luận hoặc ghi blocker, không lờ đi vì UI đã đẹp.
- Build production trong môi trường QA; full E2E + regression layout. Backend isolated khi đổi API/quyền/giao dịch. Không gọi collector PASS là UI PASS.
- Android Chrome/iPhone Safari thật: portrait/landscape, bàn phím ảo, safe area, 200% zoom, mất mạng, Back, touch. Chưa có thiết bị thì ghi CHƯA KIỂM CHỨNG.
- Dữ liệu T00c; cả ADMIN/STAFF/CUSTOMER/OPERATOR; đổi chi nhánh và khách ngoài quyền không lộ qua UI.
- Chủ spa/KTV/khách thử tìm lịch, dời lịch, dùng thẻ, thu đủ/một phần. Ghi bấm nhầm/trợ giúp/thời gian thực tế, không tự gán điểm UX khi chưa có baseline.
- Chỉ chốt pilot khi không còn P1 trong phạm vi thiết yếu; P2 được PO chấp nhận có danh sách cụ thể. Đây là gate UI/UX, không thay RELEASE_RUNBOOK về backup/RLS/runtime/deploy.

## Lệnh kiểm chứng

Unit test harness chạy độc lập tại root; không load .env.test, không gọi fixtures DB/browser hoặc mở server:
~~~powershell
& automation_test/.venv/Scripts/python.exe -B -m unittest discover -s automation_test/harness_tests -v
~~~
Kết quả mới nhất ngày 18/10/2026: 23/23 PASS. Không chạy nhóm này bằng pytest thông thường vì sẽ tải conftest E2E.

Runner đã có và đã chạy thực tế, tại root:
~~~powershell
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/features -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa --mode dev -- automation_test/reviews/layout_probe.py automation_test/reviews/test_layout_regressions.py -q -s --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/reviews/layout_stress.py automation_test/reviews/test_mobile_controls.py -q --tb=short
~~~
Mặc định production build mới cho mỗi run; --mode dev dành vòng sửa ngắn. Các lệnh pytest trực tiếp bên dưới chỉ dành tiến trình do runner quản lý. Không tự đặt marker rồi trỏ vào server người dùng. Runner ghi frontend.log/pytest.log/isolation.json dưới automation_test/artifacts/qa/<run-id>/; ảnh/bounds dưới artifacts/ui-review/<run-id>/<task>/.

Kết quả thực tế nhóm A: production build PASS, full lần gần nhất 42 PASS/2 setup ERROR (44 bài gồm 38 functional + 5 mobile + stress). Lượt kiểm chứng cuối 7 PASS/3 strict XFAIL/1 setup ERROR; cả 6 ca mobile mới PASS, ba XFAIL vẫn là UX-01/02. Lỗi setup JWT ImmatureSignatureError tái diễn; không gọi full E2E là PASS, không tăng leeway/retry để che lỗi. Xem QA-04 trong UI_UX_REVIEW và PROGRESS.

CHƯA chạy build/E2E trong lượt chốt plan hoặc T00a. Lệnh cũ “npm run start” hoặc tự chạy frontend 3001 rồi route browser sang QA không còn là hướng dẫn môi trường đầy đủ.

Runner truyền cấu hình QA cho cùng tiến trình pytest, không phụ thuộc biến môi trường của một terminal cũ. Những dòng yêu cầu T00b chưa có runner ở các mốc trước là lịch sử và được thay thế bởi kết quả nhóm A ở trên.

Ví dụ đối số pytest tại root, sau khi runner đã thiết lập môi trường:
~~~powershell
& automation_test/.venv/Scripts/python.exe -m pytest automation_test/features/admin_bookings automation_test/features/customer_regressions -q --tb=short
& automation_test/.venv/Scripts/python.exe -m pytest automation_test/reviews/layout_probe.py -q -s --tb=short
~~~

Gate tổng:
~~~powershell
& automation_test/.venv/Scripts/python.exe -m pytest automation_test/features -q --tb=short
~~~

Backend khi có thay đổi API/quyền/giao dịch (Compose backend cần đang sẵn sàng):
~~~powershell
docker-compose exec -T backend python -m scripts.test_isolated -q --tb=short
~~~

Frontend build: npm.cmd run build tại frontend, nhưng chỉ với output/backend QA đã cấu hình bởi T00b; không ghi đè output server 3000. Không cần build/test toàn suite sau sửa tài liệu/copy nhỏ nếu chưa có thay đổi cần broaden. Không mở/tắt server người dùng để tiện kiểm thử.

## Mẫu kết quả mỗi task

- Task lá/mode/phạm vi/file:dòng/UX-ID; trạng thái checkbox và dependency.
- Expected/actual, bước tái hiện, dataset/role/viewport; source hay runtime, ảnh/response/assertion.
- Nếu sửa: thay đổi và invariant, lệnh/test/kết quả thực tế, lỗi còn lại và cleanup QA.
- Chỉ tick task hoàn tất khi acceptance đã kiểm chứng; task lá CHỜ quyết định không được tick vì “đã viết code”.
- Cập nhật PROGRESS, review/design khi quyết định thay đổi; API_CONTRACT khi đổi endpoint. Không lấy số test lịch sử làm kết quả hiện tại.

## Mốc chuyển model nhỏ

R7-01–04 đã đóng ngày 19/10. Các regression chạy trong features/admin_bookings và features/ui_quality; seven_task_recheck.py giữ làm entry point tương thích. Tiếp theo C (T05a → T05b → T03b/T06), theo nhóm/dependency PO đã cho phép. T01a/T08a/T09b cần reviewer chốt giao dịch/contract; T07/T11b cần review phiên/quyền. Popup 320px được ghi vào T11c; QA-04 vẫn phải điều tra nguyên nhân trước gate tổng, không nới xác thực/retry để làm xanh.
