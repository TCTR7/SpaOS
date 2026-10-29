# Kế hoạch triển khai SpaOS dùng chung nhiều chủ spa

Ngày: 28/10/2026. **Trạng thái: PO ĐÃ DUYỆT TRIỂN KHAI P0–P6; ĐANG THỰC HIỆN.**

PO đã chỉ thị “bắt đầu triển khai”, thực hiện toàn bộ theo thứ tự và báo cáo khi hoàn tất ngày 28/10/2026. Được sửa code/migration và chạy QA riêng; không suy thành cho phép mua hosting hoặc áp migration lên DB người dùng. Tiến độ và kết quả thực tế ghi tại PROGRESS.

## 1. Phạm vi đã thống nhất

- Một hệ thống phục vụ nhiều chủ spa; mỗi chủ có không gian thương hiệu và dữ liệu riêng, có nhiều chi nhánh. Giữ FastAPI + Next.js + PostgreSQL trong đợt này.
- Operator tạo spa, nhận diện, tài khoản chủ và chi nhánh đầu. Chủ tự quản lý nhận diện, chi nhánh và nhân viên trong phạm vi mình.
- SĐT danh tính vận hành ADMIN/STAFF duy nhất toàn nền tảng; một danh tính thuộc một chủ trong MVP. Khách có thể dùng cùng SĐT ở các spa/chi nhánh khác nhau. Operator dùng danh tính/JWT riêng. Không tự gộp tài khoản cũ trùng số.
- Nhân viên có quyền ở một hoặc nhiều chi nhánh cùng chủ. Một chi nhánh thì vào thẳng; nhiều chi nhánh có dropdown. STAFF không có quyền quản trị hoặc tổng hợp của chủ.
- **Mỗi người làm tối đa một chi nhánh trong một ngày theo Asia/Ho_Chi_Minh.** Lịch tuần lặp, sửa riêng một ngày hoặc nghỉ; giờ làm được xác định trong ngày đó. Không có cấu hình thời gian di chuyển giữa chi nhánh.
- Nhân viên đăng nhập ưu tiên chi nhánh được phân công hôm nay. Chuyển dropdown không thay phân công hoặc tạo khả năng nhận lịch ở nơi khác trong cùng ngày.
- Cấp thêm quyền giữ quyền cũ. Điều chuyển/thu hồi chỉ hoàn tất sau khi bàn giao công việc liên quan; không tự hủy/dời lịch hoặc chuyển khách, thẻ, bút toán sang chi nhánh khác.
- Một PWA theo thương hiệu spa, giao diện theo vai trò; operator có cổng riêng. Mặc định link/QR theo tên spa trên địa chỉ HTTPS miễn phí của deployment. Tên miền riêng là nhu cầu bổ sung sau.
- Gói thử nghiệm 10 USD/tháng: một chủ/thương hiệu, tối đa hai chi nhánh và 10 nhân viên duy nhất; nghiệp vụ hiện tại và branding/link/QR được bao gồm. Chưa công bố hạn mức GB trước khi đo. Chưa xây cổng thu phí tự động hoặc tự khóa vì chậm phí.

## 2. Các mặc định cụ thể của kế hoạch để duyệt

- Hạn mức tính chi nhánh active và danh tính STAFF active duy nhất trong spa; cùng người ở hai chi nhánh chỉ tính một. Chủ không tính là nhân viên. Kiểm tra tạo mới/kích hoạt lại và hai request đồng thời. Dữ liệu cũ vượt gói được giữ; chỉ chặn tăng thêm và hướng dẫn liên hệ nâng gói.
- Nếu hôm nay nghỉ/chưa phân công: ưu tiên chi nhánh mặc định còn quyền, sau đó lựa chọn gần nhất hợp lệ hoặc chi nhánh còn được cấp; hiển thị không có ca hôm nay. Không còn quyền thì không mở nghiệp vụ.
- Ngoại lệ theo ngày ưu tiên hơn mẫu tuần có hiệu lực; mẫu tuần có ngày bắt đầu áp dụng. Không có phân công hợp lệ thì nhân viên không nhận lịch, không tự lấy chi nhánh đang mở làm nơi làm việc.
- Sửa phân công, giờ hoặc nghỉ phải kiểm tra tất cả booking còn chiếm chỗ trong khoảng bị ảnh hưởng, kể cả lịch xa hơn vài tuần. Xung đột thì rollback, trả thông tin theo quyền để chủ chủ động xử lý.
- Bản đầu dùng ca trong một ngày địa phương. Các ca/lịch legacy qua nửa đêm hoặc phân công chồng chi nhánh được báo để đối chiếu, không tự cắt/dời. Vẫn kiểm tra buffer và khoảng xung đột qua ranh giới ngày.
- Khi đang mở app qua ngày mới, cập nhật ca/gợi ý nhưng không tự đổi chi nhánh giữa form đang nhập. Tự chọn chi nhánh hôm nay tại lúc đăng nhập hoặc mở phiên mới.
- Khách, thẻ, dịch vụ/giá, quyền phụ trách, thu tiền và audit tiếp tục theo chi nhánh; không mở sử dụng thẻ xuyên chi nhánh.

## 3. Nền hiện có và các điểm tích hợp

Đã đối chiếu tài liệu và các điểm source liên quan; chưa coi đây là audit toàn repository.

- `backend/app/models/models.py`: LoginAccount, BranchMembership, StaffSchedule, StaffDateOverride, DeploymentBranding, OwnerProvision và bảng nghiệp vụ.
- `backend/app/services/branch_service.py`, `backend/app/api/v1/branches.py`: đăng nhập chung, cấp một người vào nhiều chi nhánh và chuyển chi nhánh đã có; tận dụng thay vì dựng lại.
- `backend/app/services/booking_service.py`, `manual_booking_service.py` và API staff/ca: tích hợp phân công vào slots, tạo/sửa lịch, đổi KTV, auto-assign và batch.
- Operator/branding/public directory hiện có giả định cấp deployment cần đổi sang phạm vi từng spa.
- `frontend/src/components/admin/auth-context.tsx`, `admin-shell.tsx`, `frontend/src/lib/branch-guard.ts`: phiên và dropdown.
- `frontend/src/lib/server-branding.ts`, `public-manifest.ts`, `frontend/public/sw.js`: nhận diện, manifest và cache/push cần có phạm vi spa.
- Migration quan sát tới 0011; chọn revision mới sau khi kiểm tra head thực tế lúc triển khai.

## 4. Thiết kế kỹ thuật mục tiêu

### 4.1. Cấp spa và chi nhánh

- Thêm thực thể spa/thương hiệu có ID ổn định, slug duy nhất, nhận diện, trạng thái, cấu hình gói. Gắn chi nhánh và danh tính vận hành vào spa.
- Ràng buộc account/membership không được nối tài khoản spa A vào chi nhánh spa B. Giữ nguyên tenant_id là mã chi nhánh và ID dữ liệu cũ.
- Query nghiệp vụ vẫn lọc tenant_id và được xác minh trong phạm vi spa của tài khoản. Tổng hợp chỉ đọc chi nhánh đã cấp quyền, lần lượt đặt context, không mở policy toàn database.
- Bảng cấp spa/danh tính có ENABLE/FORCE RLS và policy tương ứng; ghi rõ ngoại lệ không có tenant_id cho dữ liệu thực sự cấp spa trong hướng dẫn kiến trúc/AGENTS khi triển khai. Không gán giả vào chi nhánh đầu.
- Bootstrap SĐT và public slug chỉ được đọc dữ liệu tối thiểu cần thiết. Runtime role không bypass RLS. Operator vẫn tách JWT và không mặc nhiên được đọc CRM/tài chính tất cả spa.

### 4.2. Phân công mỗi ngày một nơi

- Dùng account ID ổn định nhận diện cùng nhân viên ở các hồ sơ staff theo chi nhánh.
- Mẫu tuần theo account, có ngày hiệu lực; mỗi thứ chọn một chi nhánh được cấp hoặc nghỉ, kèm giờ. Ngoại lệ duy nhất theo account + ngày để đổi nơi/giờ/nghỉ.
- Bản ghi ca tại chi nhánh giữ tenant_id đích; mẫu/ngày nghỉ ở cấp account/spa có policy hẹp và ngoại lệ kiến trúc được ghi rõ.
- Một hàm dùng chung giải phân công: ngoại lệ ngày → mẫu tuần hiệu lực → không có ca. UI và mọi API nhận lịch cùng dùng quy tắc này.
- Membership active, phân công đúng nơi/ngày, giờ/kỹ năng và không trùng lịch là các điều kiện đồng thời để nhận lịch.

### 4.3. Giao dịch và khóa

- Đặt/sửa lịch, sửa phân công và thu hồi quyền dùng cùng cơ chế serialize theo danh tính chung; không chỉ khóa staff_id riêng ở mỗi chi nhánh.
- Chốt thứ tự khóa thống nhất, giữ row locking và khóa thẻ/booking hiện hành theo thứ tự tránh deadlock. Khóa theo account là lựa chọn khởi đầu để review, phù hợp quy mô nhỏ; không tách khóa ngày mà bỏ sót thao tác sửa mẫu tuần.
- Sau khi lấy khóa, đọc lại phân công, quyền và lịch bị ảnh hưởng. Khi khách đặt đồng thời chủ đổi ca: hoặc lịch được nhận và đổi ca bị chặn, hoặc ca đổi trước và lịch sai nơi bị từ chối.
- Slots là gợi ý; mutation luôn kiểm tra lại. Không trả chi tiết khách ở chi nhánh khác chỉ để báo một nhân viên bận.

## 5. Trình tự thực hiện và điều kiện hoàn thành

### P0 — Hợp đồng kỹ thuật và phương án dữ liệu

**Làm:** rà các giả định deployment trong auth/recovery/operator, directory/ảnh, dashboard, branding, worker, seed, routes/PWA. Chốt DTO/context, schema, API dự kiến, chính sách lịch và thứ tự khóa. Chuẩn hóa SĐT trước uniqueness, báo xung đột thay vì gộp tự động.

Viết inventory/dry-run mapping chủ → spa → chi nhánh → account và lịch tuần/ngày. Liệt kê chủ chưa rõ, membership xuyên chủ, trùng SĐT và booking legacy cùng người ở hai nơi trong một ngày. Thiết kế chuyển URL/PWA/token cũ; có thể yêu cầu đăng nhập lại khi cutover.

**Bàn giao:** thiết kế schema/API dự kiến, mapping report, checklist kiểm thử và runbook migration/rollback. API_CONTRACT tiếp tục phản ánh API đã có cho đến khi code mới hoàn tất.

**Đạt khi:** không còn đường dự kiến cho phép đọc chéo chủ; trường hợp mapping mơ hồ bị chặn rõ; mọi đường ghi lịch đều nằm trong danh sách tích hợp.

### P1 — Dữ liệu nhiều chủ, RLS và đăng nhập

**Làm:** migration mở rộng cho spa/ownership/account/membership, FORCE RLS và các ràng buộc; backfill bằng mapping tường minh, chạy lại không tạo trùng. Không đổi ID nghiệp vụ hoặc đoán quan hệ bằng tên/SĐT/hash mật khẩu.

Auth/DI/token xác minh account, spa, quyền chi nhánh, trạng thái và phiên bản quyền. Giữ namespace khách theo chi nhánh và JWT operator riêng. Sửa public directory, ảnh và dashboard để không giả định mọi bản ghi thuộc một chủ. Test với runtime role thực có RLS.

**Đạt khi:** hai spa trong cùng DB QA không đọc/ghi chéo qua ID, token, public metadata, recovery, tài khoản khóa hoặc báo cáo tổng hợp; thiếu context bị chặn.

### P2 — Operator, nhận diện và gói thử nghiệm

**Làm:** tạo spa + chủ + chi nhánh đầu + nhận diện nguyên tử, có idempotency. Operator hỗ trợ đúng provision/spa; chủ sửa nhận diện của mình. Chuyển cấu hình nghiệp vụ singleton xuống spa, trang chung dùng branding nền tảng trung tính.

Sinh slug/link/QR từ origin công khai cấu hình; đổi tên không làm mất link cũ. Enforce hai chi nhánh active/10 danh tính STAFF active ở tạo và kích hoạt lại, chống request đồng thời vượt gói. Không thêm thanh toán định kỳ trong đợt này.

**Đạt khi:** hai spa khác thương hiệu; retry không tạo trùng, lỗi rollback đầy đủ; cấp cùng nhân viên vào hai nhánh chỉ tính một; dữ liệu vượt gói cũ không bị mất quyền đọc.

### P3 — Nhân viên nhiều chi nhánh và lịch làm theo ngày

**Làm:** form chọn nhiều chi nhánh, mặc định chi nhánh đang quản lý. UI lịch tuần bảy ngày chọn một nơi/nghỉ + giờ, ngày bắt đầu hiệu lực và sửa riêng ngày.

Chuyển lịch cũ theo mapping; một nhánh chuyển tương ứng, nhiều nhánh mâu thuẫn phải đối chiếu. Tích hợp phân công vào danh sách KTV theo ngày, slots, booking khách/admin/batch/auto-assign và dời lịch/đổi người.

Hoàn thiện cấp thêm/điều chuyển. Thu hồi quyền, khóa nhân viên hoặc đóng chi nhánh đều kiểm tra công việc bị ảnh hưởng, không có đường vòng bỏ qua bàn giao. Sửa/đóng các phân công tương lai trỏ nơi bị thu hồi trong giao dịch hợp lệ; giữ lịch sử.

**Đạt khi:** khách chỉ đặt Lan tại Quận 1 hôm nay và Quận 7 ngày mai đúng phân công. Hai thao tác đồng thời đổi ca/thu hồi và đặt lịch không tạo lịch sai. Cùng người không có hai nơi trong ngày; dữ liệu thiếu phân công không tự nhận lịch.

### P4 — Tự điều hướng, dropdown và phiên

**Làm:** login chung xác minh rồi vào đúng spa; login bên trong PWA một spa phải kiểm tra tài khoản đúng spa đó. STAFF ưu tiên phân công hôm nay, owner ưu tiên lựa chọn hợp lệ gần nhất. Một nhánh ẩn dropdown; STAFF không có tổng hợp của chủ.

Chuyển context đồng bộ token/branding/dữ liệu, hủy request cũ, bỏ response muộn và xử lý bản nháp rõ ràng. API chặn quyền cũ ngay; UI đồng bộ qua thông báo/kiểm tra phiên. Xử lý nhiều tab, logout, offline và qua ngày mới mà không đổi nơi ghi của form đang mở.

**Đạt khi:** vào đúng spa không cần mã; mở phiên ngày mai ưu tiên nơi làm ngày mai; manual dropdown không thay lịch nhận khách; tab cũ không ghi được sau thu hồi quyền và không gửi nhầm sang nhánh mới.

### P5 — PWA thương hiệu, QR và push

**Làm:** routes canonical dưới /s/{spa_slug}/, gồm lối vào public/login/admin/customer. Một manifest theo spa với id ổn định, name/icon, start_url/scope tương ứng. Giao diện sau đăng nhập theo vai trò; tách rõ ý định đăng nhập khách/quản lý nếu cùng SĐT có ở hai namespace.

Phân phạm vi service worker/cache/storage/push; không cache dữ liệu riêng tư bằng URL thiếu người dùng/phạm vi. Push/deep link mở đúng spa/nhánh/lịch nếu còn quyền. Link/QR/recovery cũ có mapping; ghi hướng dẫn cài lại PWA nếu origin/scope đổi, không hứa redirect giữ mọi phiên/biểu tượng.

**Đạt khi:** build/TypeScript, E2E và kiểm tra Android/iOS thật đạt các ca cài/mở lại/hết phiên, hai spa trên một máy, đổi tài khoản, logo và push/deep link. Thiếu thiết bị/access thì báo gate chưa đạt, không thay bằng kết quả mô phỏng.

### P6 — Hồi quy, chuyển dữ liệu và pilot

**Làm:** chạy backend toàn bộ bằng `python -m scripts.test_isolated`, build frontend và E2E production QA riêng. Fixture tối thiểu hai spa × hai chi nhánh, nhân viên một/nhiều nhánh, lịch tuần/ngoại lệ/nghỉ và quyền bị thu hồi. Hồi quy thẻ/thu tiền/audit/operator/recovery.

Diễn tập migration trên bản sao, so ID/số dòng/FK/policies, backup/restore và retry/rollback. Đo RAM/CPU/DB/ảnh/worker/latency, kịch bản pilot ba spa × tối đa 10 nhân viên/spa; dự toán từ số đo, không cam kết sức chứa/lợi nhuận.

Chọn hosting/gói từ kết quả, chuẩn bị backup ngoài môi trường ứng dụng, theo dõi lỗi/chi phí và runbook cutover. Bàn giao release và bằng chứng kiểm thử để review trước deploy thật.

**Đạt khi:** các gate nhiều chủ/phân công ngày/booking/thẻ/tiền đều đạt; có phương án phục hồi dữ liệu, kết quả native PWA rõ ràng. Mua dịch vụ, áp migration DB thật và deploy pilot theo chỉ thị riêng khi môi trường đã xác định.

## 6. Migration và phương án quay lui

1. Inventory read-only/dry-run; backup và thử restore ở DB riêng. Không in secrets hoặc dữ liệu khách nhạy cảm.
2. Mở rộng schema, backfill mapping đã đối chiếu, kiểm tra mỗi chi nhánh/account có đúng chủ. Không import mù hay gộp theo SĐT.
3. Branding singleton cũ được phân bổ theo mapping xác nhận; không áp màu/logo một chủ cho tất cả. Lịch mâu thuẫn cần xử lý trước cutover.
4. Giữ bảng/cột cũ cần tương thích đến khi nghiệm thu; không drop hoặc chạy downgrade phá dữ liệu trong giai đoạn đầu.
5. Diễn tập tạm dừng ghi, migrate/backfill/verify, kiểm tra token/context/URL rồi mở ghi lại. Thực hiện DB thật chỉ theo runbook được duyệt.
6. Sau khi có dữ liệu mới, không restore/downgrade mù làm mất phát sinh: dừng ghi, sao lưu trạng thái mới, đối chiếu và forward-fix hoặc phục hồi có reconciliation được duyệt.

## 7. Cách bàn giao và phạm vi duyệt

- Mỗi P là một nhóm thay đổi review được, có file/schema/API/UI liên quan, ca kiểm thử và giới hạn còn lại. Phần RLS/auth/transaction review theo checklist AGENTS trước bước tiếp theo.
- Cập nhật API_CONTRACT khi endpoint thực sự đổi; PROGRESS chỉ đánh dấu đúng code/test đã hoàn tất. Test dùng QA riêng, không seed/reset DB hoặc credentials người dùng.
- Khi PO duyệt kế hoạch: bắt đầu P0, sau đó thực hiện lần lượt P1–P6 và báo kết quả từng chặng. Hosting/dung lượng chưa chốt không chặn P0–P5.
- Ngoài phạm vi: đổi framework; nhân viên thuộc nhiều chủ; làm hai chi nhánh cùng ngày; thẻ/khách dùng chung xuyên nhánh; tự gộp dữ liệu; travel-time/bản đồ; tính lương/chấm công mới; SMS/tên miền riêng; tự thu phí SaaS và khóa vì nợ.
- AGENTS, tài liệu kiến trúc/PRD/chiến lược được đồng bộ với phạm vi mới khi triển khai sau duyệt. Không suy phê duyệt kiến trúc cũ 17/10 thành phê duyệt plan này.

## 8. Ví dụ nghiệm thu xuyên suốt

Operator tạo Spa Sen xanh và Mai Beauty hồng → chị Hương chỉ thấy Spa Sen → tạo Quận 1/Quận 7 và Lan ở cả hai → phân Lan thứ Hai Quận 1, thứ Ba Quận 7 → Lan đăng nhập thứ Hai vào Quận 1, đổi dropdown không đổi ca → khách thứ Hai chỉ đặt Lan tại Quận 1 → chủ đổi thứ Hai sang Quận 7 khi còn booking bị chặn → xử lý lịch/khách cần bàn giao rồi điều chuyển → quyền cũ bị chặn ở cả tab cũ → lịch sử giữ nguyên → PWA và push của hai thương hiệu không lẫn nhau.


## 9. Đối chiếu bàn giao mã nguồn ngày 28/10/2026

P0–P4 đã có code/tài liệu và kiểm thử QA theo phạm vi. P5 đã có canonical routes, phiên, manifest/worker/QR/push scope; native Android/iOS còn mở. P6 đã có diễn tập migration/rollback/retry, tải ba spa, backup/restore, build và hồi quy local; full E2E có 265 ca đạt/hai lỗi fixture clock; sau phần deep link cuối đã build và shared E2E 11/11 PASS. Còn cần full suite sạch trên clock ổn định, nghiệm thu native và đo/cutover trên hạ tầng đích. Không đánh dấu toàn bộ P5/P6 đã đạt chỉ từ browser QA. Chi tiết và số liệu cuối xem [báo cáo triển khai](SHARED_SAAS_IMPLEMENTATION_REPORT.md).
