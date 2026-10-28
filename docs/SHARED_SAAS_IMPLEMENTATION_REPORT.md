# Bàn giao shared SaaS SpaOS — 28/10/2026

Phạm vi PO duyệt: P0–P6, giữ FastAPI + Next.js + PostgreSQL. Mã nguồn triển khai và kiểm chứng trên QA riêng. Chưa cutover database ứng dụng, mua hosting hoặc deploy production. Đã chốt phần triển khai mã nguồn và kiểm chứng local. P5/P6 còn các gate môi trường/thiết bị/production bên dưới; không coi đây là nghiệm thu production.

## Phần đã triển khai

- **P0:** technical design, API contract, inventory/dry-run mapping và runbook chuyển dữ liệu/quay lui. Mapping mơ hồ hoặc account nối nhiều chủ bị chặn, không tự gộp theo SĐT.
- **P1:** migration 0012 thêm spa, account scope và phân công; FORCE RLS, composite FK và membership trigger chặn xuyên spa. Giữ tenant_id là mã chi nhánh và ID nghiệp vụ cũ. Xác thực kiểm tra account/spa/membership trước nghiệp vụ; operator JWT riêng.
- **P2:** operator tạo độc lập từng spa/chủ/chi nhánh đầu/nhận diện, hỗ trợ retry idempotent. Chủ sửa tên, logo, bìa, màu và liên hệ. Gói giới hạn hai chi nhánh active và 10 danh tính STAFF active duy nhất, chủ không tính, cấp nhiều chi nhánh không đếm trùng.
- **P3:** cấp nhiều chi nhánh; mẫu tuần có ngày hiệu lực; ngoại lệ/nghỉ theo ngày và trở về mẫu tuần. Slots, auto-assign, đặt/dời lịch, đổi KTV và batch dùng cùng phân công. Thu hồi quyền yêu cầu bàn giao lịch/khách; giữ lịch sử và ca mới ở nơi còn quyền. Một người một nơi/ngày theo giờ Việt Nam. Có tạm ngưng/mở lại chi nhánh: kiểm tra lịch/khách chưa bàn giao, giữ dữ liệu, kết thúc ca tương lai tại nhánh đó và kiểm tra quota khi mở lại.
- **P4:** đăng nhập không cần slug; STAFF ưu tiên nơi làm hôm nay, owner ưu tiên lựa chọn hợp lệ gần nhất. Dropdown chỉ đổi dữ liệu đang xem. Token/storage theo spa; chặn form chưa lưu/đang gửi giữa tab; bỏ response phiên cũ. Tab bị thu hồi tự xác minh nơi còn quyền, không gửi lại thao tác. Hiển thị ca hôm nay, cập nhật khi qua ngày/đưa app lên trước, không tự chuyển nơi ghi của form.
- **P5:** URL `/s/{spa}/admin/...` và `/s/{spa}/b/{branch}/...`; manifest id ổn định theo spa, scope/worker/token riêng; SSR nhận diện từ URL đã xác minh. Link/QR/PDF/khôi phục và push deep link có scope; shell xác minh target_branch trước mở booking, chuyển nhánh giữ đích, chưa đăng nhập/hết phiên có intent theo spa dùng một lần tối đa 30 phút. Chưa chứng nhận cài/push trên Android/iOS thật.
- **P6:** runner QA tạo và dọn DB riêng, diễn tập migration/rollback/retry, tải ba spa và backup/restore; bổ sung hồi quy backend/browser. Build production Next.js 14.2.35 đã qua. Hồi quy full 265 PASS/2 ERROR do clock và nhóm shared cuối 11/11 PASS; vẫn cần full suite sạch trên môi trường clock ổn định cùng nghiệm thu thiết bị thật.

## Checklist Reviewer/QA theo AGENTS

- **[PASSED] Cô lập:** spa/account/membership/assignment có scope và FORCE RLS; runtime NOSUPERUSER/NOBYPASSRLS, thiếu context không đọc được. Hồi quy chặn foreign branch/account, public directory và header giả mạo thương hiệu. Không tuyên bố đây là pentest toàn hệ thống.
- **[PASSED] Lịch:** row locking, workforce lock chung, slot + buffer giờ Việt Nam, chống tranh lịch/đổi ca/thu hồi quyền và buffer qua nửa đêm. COMPLETED/NO_SHOW tiếp tục ràng buộc nơi làm của ngày đã có buổi hẹn.
- **[PASSED] Thẻ:** khóa thẻ, chặn overbooking và cộng used_sessions khi COMPLETED có idempotency; full backend bao gồm hồi quy thẻ/thu tiền/audit.
- **[PASSED] Async:** không ghi nhận MissingGreenlet trong các lượt đạt; ảnh spa deferred, auto-assign đọc windows/busy theo nhóm, verify_bookings không query phân công riêng mỗi booking. Lỗi pool được tái hiện và vá bằng transaction outbox dùng chung.
- **[WARNING] Môi trường:** clock Docker từng nhảy lùi gây từ chối JWT mới; native PWA/push và production cutover chưa được chứng nhận. Các gate cuối ghi bên dưới.

## Các lỗi quan trọng đã vá khi kiểm chứng

- **[CRITICAL — ĐÃ VÁ] Cạn pool/HTTP 500 khi tải đồng thời:** giải phóng connection đọc response trước background task, outbox dùng cùng session/savepoint thay vì giữ một connection rồi đợi connection thứ hai. Xem `backend/app/api/v1/bookings.py:76`, `backend/app/services/notification_queue.py:65`, `backend/app/services/notification_service.py:24`.
- **[CRITICAL — ĐÃ VÁ] Request ghi chờ sau thu hồi quyền:** khóa workforce trước khi đọc lại user/membership; queued mutation không tiếp tục bằng snapshot quyền cũ. Xem `backend/app/api/deps.py:81`, hồi quy `test_queued_staff_write_rechecks_revocation_after_workforce_lock`.
- **[CRITICAL — ĐÃ VÁ] Thu hồi nơi cũ ảnh hưởng mẫu mới:** chỉ kết thúc mẫu đang có hiệu lực trỏ nhánh bị thu hồi; giữ ca đã chuyển sang nhánh còn lại. Xem `backend/app/services/assignment_service.py:144`, hồi quy `test_revocation_preserves_newer_week_at_remaining_branch`.
- **[PASSED] Booking/thẻ/tiền:** giữ SELECT FOR UPDATE, transaction và khóa spa chung cho sửa ca/booking; giữ kiểm soát quota và audit nguyên tử. Các ca shared kiểm tra tranh lịch/đổi ca, lịch 90 ngày, buffer qua nửa đêm và giới hạn nhân viên đồng thời.
- **[PASSED] UI:** giữ phần chọn nhân viên khi đổi ngày, giữ thông báo và token khôi phục khi React phát triển chạy effect hai lần, đồng bộ tên/ảnh đã lưu, sửa fixture phù hợp directory theo spa và dropdown chỉ xuất hiện khi nhiều nhánh.
- **[PASSED] Dependency:** cập nhật Next.js 14.2.15 → 14.2.35 trong cùng nhánh; build/typecheck đã qua. Đây là bản vá trong nhánh hiện tại, không phải cam kết mọi dependency đều đã được audit hoặc framework còn được hỗ trợ dài hạn.

## Bằng chứng QA

- Full backend trước bản vá thu hồi mẫu tuần cuối: **145 PASS / 2 FAIL**, cả hai lỗi fixture do JWT `ImmatureSignatureError` sau khi clock Docker lùi. Lượt cũ trước tối ưu cuối từng **146/146 PASS**, không dùng thay cho kết quả mã mới.
- Nhóm sau bản vá thu hồi: **17/17 PASS (49.95s)**, gồm 14 ca shared, migration và hai ca backend từng vướng clock.
- QA dev gần nhất: **15 PASS / 1 ERROR (84.53s)**, lỗi fixture do clock; các luồng settings nhiều tab, contacts/setup, ca/nghỉ, khôi phục, CRM và logo đã qua trong lượt này.
- Backend sau vòng đời chi nhánh: **150/150 PASS (292.08s)**. Sau đó bổ sung kiểm tra booking COMPLETED/NO_SHOW giữ một nơi/ngày; nhóm shared/migration/booking trên mã này **27/27 PASS (65.80s)**. Đây là hai lượt riêng, không gọi là một full run 151/151.
- Runner harness: **25/25 PASS (0.128s)**.
- Build production **PASS** với Next.js **14.2.35**, TypeScript strict giữ nguyên. Lượt production đầy đủ trước bổ sung vòng đời chi nhánh: **256 PASS / 6 FAIL / 3 ERROR (828.29s)**. Ba lỗi fixture có log clock/JWT; sáu lỗi gồm bốn overflow tên sidebar dài, một onboarding fixture che thao tác và một fixture còn dùng màu chi nhánh. Đã sửa; production build mã có vòng đời chi nhánh và nhóm hồi quy **37/37 PASS (118.86s)**, gồm bảy ca shared, branches, mobile/tên dài, nhiều tab, bàn giao và màu hộp thoại. Không gộp với lượt trước thành full pass. Lượt full production tiếp theo: **265 PASS / 2 ERROR (759.84s)**, không có assertion FAIL; cả hai ERROR tại fixture schedules có log clock/JWT đi trước 2.40/2.22 giây. Sau lượt build này bổ sung xử lý target_branch qua đăng nhập/hết phiên: production build/TypeScript PASS; nhóm liên quan **48 PASS / 1 FAIL fixture (123.54s)** vì helper QA nạp token cũ sau điều hướng. Đã sửa helper nạp một lần; lượt production shared SaaS cuối **11/11 PASS (23.38s)**, gồm active/anonymous/expired/no-membership deep link. Không có thay đổi backend sau nhóm 27/27. Không gộp các lượt thành full suite sạch của mã cuối.
- Full backend sau bản vá thu hồi mẫu tuần: **144 PASS / 4 FAIL (308.61s)**, lỗi xác thực fixture; ba ca có log clock/JWT đi trước 2.91–4.37 giây, một ca operator token bị từ chối. Sau đó đã bổ sung vòng đời chi nhánh, nhóm shared/branches **22 PASS / 2 FAIL (60.02s)**: một clock, một mã HTTP cũ 403 nay đổi 401 để resolve phiên. Đã cập nhật assertion đúng hợp đồng; nhóm tám ca kiểm tra lại **8/8 PASS (23.95s)**, gồm vòng đời/booking tranh chấp và các ca từng lỗi ở full suite. Các lượt lỗi trước được giữ để đối chiếu; kết quả mới nhất ghi ở trên.

## Ví dụ thao tác trên bản mới

1. Operator tạo Spa Sen xanh và Mai Beauty hồng với hai tài khoản chủ khác nhau. Mỗi chủ nhận link đăng nhập/QR dưới `/s/{spa}/`, chỉ thấy nhận diện và dữ liệu của mình.
2. Chủ Spa Sen thêm Quận 7 từ chi nhánh Quận 1, cấp Lan vào cả hai. Trong “Nhân sự & Ca làm việc”, phân Thứ Hai Quận 1, Thứ Ba Quận 7; lưu mẫu tuần từ ngày đã chọn.
3. Lan đăng nhập Thứ Hai vào Quận 1; hôm sau vào phiên mới ưu tiên Quận 7. Dropdown thay nơi đang xem; thông tin ca hôm nay và backend vẫn quyết định nơi nhận lịch. Đổi dropdown không cho khách đặt Lan sai nơi.
4. Chủ muốn đổi ngày đã có lịch: hệ thống chặn, cần xử lý lịch trước. Ngay cả buổi đã COMPLETED/NO_SHOW cũng giữ nơi làm của ngày đó, không chuyển giữa ngày bằng sửa ca.
5. Chủ bàn giao khách/lịch rồi thu hồi quyền Quận 1. Tab cũ bị chặn nghiệp vụ; tự xác minh Quận 7 còn được cấp, thông báo quyền đã thay đổi và không gửi lại thao tác đang dở.
6. Chủ đang ở Quận 7 có thể tạm ngưng Quận 1 khi không còn lịch/khách cần bàn giao. ID/lịch sử/thẻ/tiền giữ nguyên. Mở lại kiểm tra số nhánh active và cần phân công ca nhận khách mới.
7. Push lịch hẹn Quận 7 được mở khi đang ở Quận 1: giao diện xác minh quyền rồi đưa nút mở đúng chi nhánh; đăng nhập lại vẫn giữ đích hợp lệ. Không còn quyền thì dừng tại thông báo, không tải booking bằng ngữ cảnh nhánh khác.

## Tải và phục hồi

Ba spa × 10 nhân viên, 60 request tranh giờ: **30×201 + 30×409**, đúng 10 booking được nhận mỗi spa, **600/600 reads 200**, không HTTP 500. p95 booking từng spa **3,746.0 / 4,599.3 / 4,199.5 ms**, p95 đọc lớn nhất **2,534.0 ms**, đạt ngân sách thử local 5,000 ms. Bài tải chạy sau sửa pool/auto-assign, trước phần vòng đời chi nhánh và điều chỉnh cuối với booking đã hoàn thành. Đây là kiểm thử trên máy local có tác vụ QA khác, không xác nhận sức chứa production.

Snapshot backend sau tải **137.3 MiB / CPU 5.80%**; DB QA **10,681,367 bytes**, có dữ liệu demo và chưa đại diện ảnh/lưu trữ dài hạn. Không phải peak RAM/CPU hoặc dự toán GB/chi phí.

Backup QA **197,226 bytes**; restore PostgreSQL 16 tạm, **31 bảng khớp row counts, RLS flags/policies và context probes PASS** với role không bypass. Dump/temp container/DB QA đã dọn. Rehearsal không sao chép roles/grants/secrets; production phải diễn tập phần đó riêng.

## Gate còn mở trước triển khai thật

1. **Clock Docker và hồi quy:** đã ghi nhận token vừa cấp đi trước clock xác minh đến 5.68 giây, vượt tolerance hai giây hiện có. Không tăng tolerance, tắt `iat` hoặc tự retry mutation để che lỗi. Cần môi trường clock ổn định và một lượt hồi quy sạch trước chứng nhận release.
2. **Native PWA/HTTPS/push:** thiết bị Android/iOS thật, hai spa trên một máy, cài/mở lại/hết phiên/đổi tài khoản, logo, scope, offline và push mở đúng booking/nhánh còn quyền. Browser E2E không thay gate này.
3. **Môi trường đích:** chọn hosting/ngân sách, backup ngoài server và retention, restore roles/secrets, giám sát lỗi/dung lượng/chi phí, đo lại tải trên cấu hình đích. Chưa suy ra số spa tối đa hoặc lợi nhuận từ số đo local.
4. **Dữ liệu thật:** inventory/mapping từng chủ được đối chiếu trên bản sao; cutover/mua dịch vụ/deploy thực hiện theo chỉ thị riêng. Không tự áp schema/mapping vào database đang dùng.

Thao tác vận hành xem [runbook](SHARED_SAAS_MIGRATION_RUNBOOK.md), chi tiết kiến trúc xem [technical design](SHARED_SAAS_TECHNICAL_DESIGN.md), endpoint xem [API_CONTRACT](API_CONTRACT.md).
