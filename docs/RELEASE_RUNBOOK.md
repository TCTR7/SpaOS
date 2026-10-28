# Chạy thử trước phát hành SpaOS

## Shared SaaS 0012 — hướng dẫn hiện hành (28/10/2026)

Đợt triển khai mới dùng một deployment nhiều chủ, từng spa có scope/nhận diện/PWA. Trước thao tác release/migration, ưu tiên [runbook shared SaaS](SHARED_SAAS_MIGRATION_RUNBOOK.md) và [báo cáo QA](SHARED_SAAS_IMPLEMENTATION_REPORT.md). Các mục deployment riêng/0005 và đường dẫn cũ bên dưới là lịch sử, không phải lệnh cutover 0012.

QA hiện hành: backend dùng `docker compose exec -T backend python -m scripts.test_isolated`; E2E dùng `python -B -m automation_test.run_ui_qa`; tải ba spa + backup/restore chỉ trên QA tạm dùng `python -B -m automation_test.run_shared_pilot` (Python có dependencies tại `automation_test/.venv/Scripts/python.exe`). Không chạy seed_demo/test/load hoặc rehearsal dump trên DB ứng dụng như một phần kiểm thử mặc định.

PWA/push mới phải mở `/s/{spa_slug}/admin/bookings` hoặc `/s/{spa_slug}/b/{branch_slug}/appointments`, xác minh còn quyền trước xem dữ liệu. Kiểm tra hai spa trên cùng thiết bị với scope/worker riêng. Cần nghiệm thu Android/iOS thật trên HTTPS; browser QA không thay bằng chứng này.


## Kiểm thử tải local/staging

Chạy từ root sau khi backend và PostgreSQL đã sẵn sàng:

~~~powershell
docker-compose exec -T backend python scripts/release_load_check.py
~~~

Công cụ tạo tenant riêng tên load-*, 10 KTV và 20 khách thử nghiệm; không dùng tài khoản khách thật. Sau 20 request đặt cùng giờ, yêu cầu đúng 10 thành công trên 10 KTV khác nhau và 10 response 409. Sau đó chạy 200 request đọc với mức đồng thời 10, yêu cầu toàn bộ 200. Kiểm tra slot đã kín và hủy các booking thành công sau lượt chạy.

Ngưỡng mặc định: p95 mỗi nhóm <= 2000ms. Chỉnh bằng --max-p95-ms; số lượt đọc --reads (20–2000). Tenant thử được giữ lại để điều tra; nếu kiểm tra bị lỗi giữa chừng, booking có thể còn tồn tại trong tenant thử đó. Công cụ kết thúc mã lỗi khi không đạt điều kiện.

Đây là bài tải ngắn trên HTTP thật, không phải chứng nhận sức chứa production. Chạy lại trên staging có cấu hình tương đương production trước pilot, gồm dữ liệu lịch sử đại diện; kiểm tra CPU/RAM, pool kết nối, lỗi 5xx và thời gian phản hồi. Không chạy đăng ký tenant thử trên production khi chưa lên lịch.

## Backup và diễn tập khôi phục

Chạy khi không còn tác vụ test/ghi dữ liệu để so sánh inventory trước/sau dump chính xác. pg_dump dùng snapshot nhất quán; kiểm tra inventory bổ sung sẽ dừng nếu số dòng thay đổi. Lệnh dưới dùng Python sẵn có của môi trường E2E; cũng có thể dùng Python 3.9+ hệ thống:

~~~powershell
.\automation_test\.venv\Scripts\python.exe scripts/db_recovery_check.py --output backups/recovery-check.dump
~~~

Mỗi lượt dùng tên output mới; công cụ từ chối ghi đè. Cần Docker Compose và image postgres:16 sẵn có. Công cụ:
1. Tạo dump custom-format nhị phân bằng pg_dump trong service db.
2. Mở PostgreSQL tạm không có network/host port, restore với --exit-on-error.
3. So sánh số dòng từng bảng, ENABLE/FORCE RLS và nội dung chính sách.
4. Tạo role probe NOSUPERUSER/NOBYPASSRLS; kiểm tra không có tenant context thì không thấy dữ liệu nghiệp vụ, có context thì thấy đúng số dòng tenant.
5. Xóa container và volume tạm trong finally; giữ file backup.

Dump chứa dữ liệu nhạy cảm. backups/ và *.dump được bỏ qua bởi .gitignore; cần giới hạn quyền đọc, mã hóa khi lưu/chuyển và lưu bản sao ngoài máy chủ. Đây là dump một database; không chứa role/password PostgreSQL hoặc secrets ứng dụng. Lượt diễn tập bỏ qua owner/grants khi restore nên chưa kiểm chứng toàn bộ quyền đăng nhập runtime.

Khi phục hồi môi trường thực: chuẩn bị database mới và các role owner/runtime theo cấu hình, runtime phải NOSUPERUSER/NOBYPASSRLS; khôi phục quyền đúng với tên role triển khai, chạy migration và smoke test đăng nhập/đặt lịch bằng runtime role trước chuyển kết nối. Giữ JWT secret, VAPID keys và cấu hình triển khai trong kho secrets riêng. Không ghi đè database đang phục vụ.

Trước pilot cần thiết lập lịch backup tự động, lưu ngoài máy chủ và cảnh báo khi job thất bại. Thống nhất RPO/RTO với chủ spa; ghi thời gian restore thực tế trên cấu hình production.

## Kiểm tra Web Push thiết bị thật

Dùng bản staging HTTPS, VAPID public/private key cùng cặp và VAPID_SUBJECT hợp lệ. Endpoint GET /api/v1/notifications/vapid-public-key phải trả enabled=true. Giữ private key ở backend. Bài kiểm tra cần trình duyệt/thiết bị hỗ trợ Push API, Service Worker và cho phép thông báo.

1. Đăng nhập Admin và Customer trên hai thiết bị hoặc browser profile riêng. Mở chuông thông báo, bấm Bật Push và cấp quyền.
2. Khách tạo booking: Admin nhận thông báo; bấm thông báo mở /admin/bookings.
3. Admin xác nhận booking: Customer nhận thông báo; bấm mở /<tenant_slug>/appointments đúng spa.
4. Khách hủy booking: Admin nhận thông báo hủy. Admin hủy lịch khác: Customer nhận thông báo hủy.
5. Kiểm tra lại khi trang ở background; ghi rõ hệ điều hành, trình duyệt, thời gian nhận và URL đích. In-app notification vẫn phải có khi push lỗi.
6. Bấm Tắt Push và xác nhận thiết bị không còn nhận push mới. Kiểm tra trên hai tenant khác nhau bằng profile riêng; lưu ý một subscription trình duyệt thuộc tài khoản đang đăng ký nó.

Chưa có kết quả kiểm tra thiết bị thật trong phiên local này. Không coi mock push hoặc mô phỏng Service Worker là kiểm tra giao nhận push thực tế.


## Thu tiền thủ công và bàn giao KTV

- Menu Admin → Thu tiền tự hiển thị khách và dịch vụ/thẻ đã mua, giá đã chốt, đã thu và còn thiếu. Mặc định lọc Còn cần thu; dùng tên/SĐT để tìm khách hoặc chọn Tất cả để xem khoản đã thu và lịch dùng thẻ.
- Bấm Xác nhận đã thu tại dòng của khách, kiểm tra số còn thiếu, chọn Tiền mặt/Chuyển khoản rồi xác nhận. Hệ thống mặc định ghi nhận toàn bộ số còn thiếu, tự cập nhật trạng thái và tổng thu hôm nay. Chỉ xác nhận khi thực nhận tiền; ứng dụng không kết nối ngân hàng.
- Nếu khách trả một phần, bật Nhập số tiền khác và điền số tiền thực nhận; hệ thống tự trừ số đã thu và chặn vượt số còn thiếu.
- Khi mất response, dùng Thử lại xác nhận để gửi lại cùng mã. Nếu đã ghi thành công nhưng chưa tải lại được số dư, dùng Tải lại số tiền trước khi thu tiếp.
- Nếu ghi nhầm, mở Lịch sử thu tiền và hoàn tác, chọn Hoàn tác ghi nhận và nhập lý do. Khoản gốc vẫn được giữ, tổng thu được điều chỉnh; việc hoàn tiền thực tế cần thực hiện và đối chiếu riêng.
- Thẻ mới dùng giá bán lúc cấp. Thẻ cũ chưa có giá cần chọn Đối chiếu giá cũ và xác nhận giá lịch sử đã thỏa thuận, không lấy giá menu hiện tại. Lịch dùng thẻ ghi Dùng thẻ — không thu thêm.
- Tổng thu hôm nay tự tải theo giờ Việt Nam; hoàn tác tính giảm vào ngày thực hiện. Lịch đã hủy/khách không đến chưa có khoản thu nội bộ không xuất hiện; nếu đã có thì vẫn giữ để đối chiếu, không tự hủy tiền.
- Nhật ký nằm ở tab Lịch sử thao tác. Invoice/ledger/audit vẫn được lưu nội bộ để bảo vệ số liệu; không yêu cầu chủ spa lập phiếu. Không sửa/xóa trực tiếp các bảng audit/ledger.
- Khi dời lịch và chọn KTV khác, Admin có tùy chọn Chuyển quyền hồ sơ cho KTV của giờ hẹn mới. Chỉ bật khi người mới tiếp quản hồ sơ khách; nếu không, quyền cố định giữ nguyên. Nếu giờ mới trùng hoặc lỗi, cả lịch và quyền giữ nguyên.
- Migration mới: 0004_manual_payments. Backup/recovery cần giữ cả 3 bảng payment_invoices/payment_entries/audit_logs và function/trigger bất biến; probe RLS đã được mở rộng cho 11 bảng nghiệp vụ.


## Triển khai riêng và chuyển đổi đa chi nhánh (0005_branch_accounts)

Một chủ spa/thương hiệu dùng một Compose project, database/volume, tên miền và bộ secrets riêng. Code/image dùng chung; không sao chép database hoặc secrets giữa khách. Compose đã bỏ container_name cố định để hỗ trợ nhiều project; dùng tên project ổn định và không đổi tùy tiện vì sẽ trỏ sang volume khác. Những container local cũ có tên cố định chỉ nên thay trong lượt bảo trì đã lên lịch; không xóa volume dữ liệu.

Ví dụ dùng file cấu hình riêng (không đưa secrets vào source):

~~~powershell
docker-compose --env-file .env.client-a -p spaos-client-a up -d
docker-compose --env-file .env.client-a -p spaos-client-a exec -T backend alembic upgrade head
~~~

Các biến mới: ENVIRONMENT=production, ALLOW_TENANT_REGISTRATION=false, BRAND_NAME=<tên thương hiệu>. Giữ DATABASE_URL/MIGRATION_DATABASE_URL, POSTGRES_DB, credentials, JWT_SECRET_KEY, VAPID và domain/proxy riêng. Compose tự xây URL database theo POSTGRES/APP_DB variables. Mỗi project dùng host port riêng hoặc reverse proxy/network riêng; cấu hình TLS/CORS theo domain thật. BRANCH/nhân viên/giờ mở cửa/giá là dữ liệu trong ứng dụng, không đặt từng chi nhánh trong biến môi trường.

Production database mới: chạy migration rồi khởi tạo chủ và chi nhánh đầu bằng terminal tương tác (mật khẩu nhập kín, không dùng seed):

~~~powershell
docker-compose --env-file .env.client-a -p spaos-client-a exec backend python -m scripts.bootstrap_deployment
~~~

CLI từ chối nếu database đã có tenant. Đăng ký public bị tắt trong production; sau đăng nhập dùng Chi nhánh → Tạo chi nhánh. Chủ chỉ nhập tên, mã đường dẫn tự sinh. Mỗi chi nhánh tự thiết lập dịch vụ, giá, nhân viên và ca làm; không tự nhân bản dữ liệu kinh doanh.

### Nâng cấp database đang có dữ liệu

1. Backup và diễn tập restore trước khi chạy migration trên môi trường thật. Không diễn tập ghi đè database phục vụ.
2. Kiểm kê database có chứa nhiều chủ độc lập không. Nếu có, cần tách deployment/dữ liệu có kiểm chứng trước khi công bố trang chọn chi nhánh; không coi tất cả tenant cũ là một chủ. Migration không tự hợp nhất chúng.
3. Chạy 0005_branch_accounts. Giữ tenant_id và tất cả ID nghiệp vụ. Tài khoản ADMIN/STAFF có SĐT duy nhất được tạo danh tính chung; SĐT trùng bị bỏ qua để đối chiếu, không tự gộp.
4. Báo cáo tài khoản chưa liên kết bằng công cụ operator (output có SĐT, chỉ lưu ở nơi hạn chế quyền):

~~~powershell
docker-compose exec -T backend python -m scripts.branch_account_audit
~~~

5. Sau đối chiếu người dùng thật, chuyển đúng một tài khoản chưa liên kết. Dùng SĐT riêng nếu cần giải quyết trùng; không đổi mật khẩu hoặc user ID. Ví dụ (thay UUID/SĐT trước khi chạy):

~~~powershell
docker-compose exec -T backend python -m scripts.branch_account_audit --apply --tenant-id <UUID> --user-id <UUID> --phone <SDT_DA_DOI_CHIEU>
~~~

Công cụ dùng migration credential, không đưa ra API public. Chỉ chạy sau kiểm kê; không tự thực thi hàng loạt theo báo cáo. Nếu còn trùng giữa tài khoản quản trị thì từ chối. Các hồ sơ khách vẫn riêng theo chi nhánh.
6. Smoke test đăng nhập không slug; chủ tạo/chuyển chi nhánh; STAFF chỉ thấy chi nhánh được cấp; tắt STAFF tại đích thì token đích bị chặn; dashboard tổng không chứa dữ liệu chủ khác.
7. Chạy lại regression booking/thẻ/thu tiền và test push trên thiết bị thật sau chuyển chi nhánh. Push cũ được hủy đăng ký; người dùng bật Push ở chi nhánh mới khi cần.
8. Backup/restore phải có login_accounts, branch_memberships và RLS policies, cùng bảng nghiệp vụ cũ. Recovery probe kiểm tra cả FORCE RLS của danh tính và tenant/account scopes.

Rollback: không chạy downgrade trực tiếp trên production đã có ghi đa chi nhánh mà chưa đối chiếu. Dừng ghi theo lịch bảo trì, giữ bản backup sau nâng cấp để truy vết, dùng bản ứng dụng/schema tương thích hoặc phục hồi vào database riêng từ backup trước nâng cấp và đối chiếu phần phát sinh. Không thể mặc định restore cũ mà không mất các giao dịch mới. Công cụ restore local vẫn bỏ owner/grants, cần thử role runtime đầy đủ trên staging.

### Giới hạn bản đa chi nhánh đầu
- Khách/hồ sơ/KTV phụ trách/thẻ thuộc từng chi nhánh; không dùng thẻ xuyên chi nhánh. Khách chọn tên chi nhánh trên trang chủ và đăng nhập SĐT/mật khẩu tại đường dẫn đó.
- Không gộp lịch sử khách hoặc nhân viên giữa các chi nhánh.
- Đổi SĐT/mật khẩu tài khoản nhân viên đã dùng nhiều chi nhánh chưa có luồng quản trị chung; API chi nhánh từ chối để tránh thay đổi credential ngoài ý muốn.
- Dashboard “Tất cả” chỉ cho chủ và chỉ xem tổng hợp; khi tạo/sửa/thu tiền cần chọn chi nhánh cụ thể.
- Chi phí dashboard tăng theo số chi nhánh; kết quả tải local trước đây không chứng nhận sức tải phiên bản mới. Staging HTTPS, backup tự động ngoài máy chủ, giám sát và tải production vẫn là điều kiện phát hành.

Với deployment riêng, chỉ định đúng project và file cấu hình cho công cụ recovery (tránh backup nhầm khách hàng):

~~~powershell
.\automation_test\.venv\Scripts\python.exe scripts/db_recovery_check.py --compose-project spaos-client-a --env-file .env.client-a --output backups/client-a-rehearsal.dump
~~~


## Cấp tài khoản chủ spa qua quản trị triển khai — thay luồng CLI (17/10/2026)

Luồng hiện hành:
1. Khi cài mỗi deployment riêng, cấu hình một lần OPERATOR_PHONE, OPERATOR_NAME và OPERATOR_PASSWORD trong file secrets/.env UTF-8. Mật khẩu không có giá trị mặc định; ít nhất 12 ký tự, tối đa 72 byte UTF-8. Không gửi mật khẩu qua chat hoặc commit vào source.
2. Khởi động/rebuild backend để nhận biến môi trường mới. Dockerfile chạy migration và python -m app.seed trước API. Với deployment riêng phải giữ đúng --env-file và -p như lúc cài:

~~~powershell
docker-compose --env-file .env.client-a -p spaos-client-a up -d --build backend
~~~

Local đang dùng project mặc định: docker-compose up -d --build backend. Không chạy lại bằng project khác vì sẽ trỏ nhầm container/volume.
3. Bạn đăng nhập tại /operator/login bằng tài khoản quản trị triển khai. Mở /operator, nhập tên chủ spa, SĐT, mật khẩu bàn giao và tên chi nhánh đầu. Toàn bộ tên tiếng Việt được nhập qua trình duyệt.
4. Chủ spa đăng nhập /admin/login bằng tài khoản vừa cấp, quản lý nhân viên và chi nhánh như hiện tại. Nhân viên/khách/chủ spa không được truy cập API quản trị triển khai.
5. Bàn giao mật khẩu qua kênh riêng. Màn hình không lưu hoặc hiển thị lại mật khẩu trong danh sách đã cấp.

### Seed và tương thích
- python -m app.seed nay CHỈ seed danh tính quản trị triển khai đã cấu hình; thiếu cả SĐT/mật khẩu thì không tạo tài khoản mẫu. Seed idempotent, không thay mật khẩu hoặc mở lại quyền của tài khoản đã tồn tại.
- Không hardcode mật khẩu “super admin”. OPERATOR_PASSWORD dùng SecretStr trong settings; database chỉ lưu bcrypt hash. Nếu cấu hình chưa hợp lệ, seed báo gọn, không in password.
- Đổi mật khẩu trong env rồi restart không tự ghi đè mật khẩu hiện có. Không dùng seed như chức năng reset tài khoản.
- Demo cũ chuyển sang python -m app.seed_demo, CHỈ môi trường development/test. Không xóa dữ liệu demo đã tồn tại vì có thể đang được dùng; dọn/tách deployment là thao tác riêng.
- scripts.bootstrap_deployment không còn hỏi nhập thông tin hay tạo chủ spa; chỉ hướng dẫn mở /operator/login. Điều này thay thế các hướng dẫn CLI cũ ở trên. Lỗi surrogate Unicode từ terminal không được “sửa” bằng cách mất dấu/nuốt byte; luồng nhập liệu chuyển sang web UTF-8.
- Migration 0006_operator_portal đã thêm deployment_operators và owner_provisions; giữ nguyên dữ liệu/tài khoản chủ spa cũ. owner_provisions chỉ là lịch sử được cấp qua cổng mới, không tự nhận/gộp các owner cũ.

### Phạm vi và bảo vệ production
- Cổng này nằm trong TỪNG deployment của khách; chưa phải một cổng trung tâm điều khiển các server khách hàng.
- Production chặn đăng ký chủ spa public, kể cả biến ALLOW_TENANT_REGISTRATION=true. Tạo chủ qua operator trên database mới; production đã có tenant thì từ chối tạo thêm chủ độc lập. Chi nhánh bổ sung vẫn do chủ tạo qua /admin/branches.
- Operator dùng JWT audience/scope riêng (30 phút), token_version kiểm tra mỗi request, không được tái sử dụng tại API khách/booking/chi nhánh. Đăng xuất thu hồi toàn bộ phiên operator đang mở. Sai mật khẩu 5 lần cho tài khoản hiện có khóa đăng nhập 5 phút.
- Tài khoản operator không phải PostgreSQL superuser và không bypass RLS. deployment_operators có FORCE RLS theo operator/phone bootstrap; owner_provisions có tenant_id và FORCE RLS, append-only.
- Tạo tenant + owner + danh tính đăng nhập + membership + lịch sử cấp + audit trong cùng transaction. UUID request_id chống tạo trùng khi mất response; cùng mã/nội dung khác trả 409. Không tự gộp SĐT đã có.
- Production cần HTTPS và cấu hình proxy giới hạn truy cập/tốc độ cho /operator và /api/v1/operator, cùng secrets riêng/backup/giám sát như checklist hiện hành. Một cổng quản trị không tự làm hệ thống production-ready.

### Kiểm thử không tạo operator QA trong database ứng dụng

~~~powershell
docker-compose exec -T backend python -m scripts.test_isolated -q --tb=short
~~~

Công cụ tạo database spaos_qa_<UUID>, chạy toàn bộ migration và pytest, rồi xóa CHỈ database vừa tạo. Cần migration role có quyền tạo database trong môi trường QA; không chạy suite trên production.

Toàn bộ E2E tự mở API container/DB spaos_e2e_<UUID> trên loopback port tạm, seed demo và operator QA riêng. Browser và ApiHelper dùng API thật tạm; feature operator kiểm tra Unicode, chủ spa đăng nhập thật và retry sau response bị mất. Teardown dọn container/database; không seed QA vào hệ thống người dùng.


## QA-04: đồng bộ giờ Windows/WSL, không lưu file log

Chỉ thị PO ngày 19/10/2026 thay quy trình lưu artifact/log cũ: chạy `automation_test.run_ui_qa` và đọc console; không chuyển output sang file, bật collector ảnh/JSON hoặc yêu cầu gửi JWT/credentials. Runner dùng Docker logging driver `none`, không tạo `pytest.log`, `frontend.log`, `isolation.json`, không ghi pytest cache. Không tự xóa dữ liệu QA lịch sử. Các chẩn đoán số liệu xác thực chỉ xuất console.

Đã quan sát Windows chưa đồng bộ (Local CMOS Clock/Stratum 0), Ubuntu WSL bật NTP riêng và 14 lần thay đổi clock trong cửa sổ QA-04 lỗi. Đây là hướng xử lý runtime; không sửa xác thực để chấp nhận token sai thời gian. Việc điều chỉnh giờ ảnh hưởng cả máy, không chỉ SpaOS.

1. Mở PowerShell **Run as administrator**, dùng cấu hình NTP hiện có:

   ```powershell
   w32tm /resync /rediscover
   w32tm /query /status
   ```

   Chỉ tiếp tục khi Windows có nguồn đồng bộ hợp lệ, Last Successful Sync Time mới, Stratum khác 0 và không còn Leap Indicator 3. Nếu access denied thì vẫn thiếu quyền Administrator. Nếu không có dữ liệu thời gian, kiểm tra dịch vụ/DNS/UDP 123/cấu hình của máy; không coi stripchart thành công là chứng minh dịch vụ đã đồng bộ.

2. **Sau khi giờ Windows đã đồng bộ**, loại bỏ NTP độc lập trong Ubuntu WSL để dùng đồng bộ giờ của nền tảng. Lệnh này thay cấu hình hệ thống Ubuntu; người vận hành cần xác nhận phạm vi trước khi thực hiện:

   ```powershell
   wsl -d Ubuntu -u root -- timedatectl set-ntp false
   wsl -d Ubuntu -- timedatectl show -p NTP -p NTPSynchronized
   ```

   Trạng thái trước can thiệp: NTP Ubuntu=yes. Nếu cần hoàn nguyên cấu hình Ubuntu: `wsl -d Ubuntu -u root -- timedatectl set-ntp true`. Không tắt NTP guest khi Windows vẫn chưa đồng bộ; không tự shutdown WSL/Docker hoặc dừng server ứng dụng. Tham khảo báo cáo hiện tượng clock skew ở [Microsoft WSL issue #11790](https://github.com/microsoft/WSL/issues/11790); đây là thông tin hỗ trợ, không thay bằng chứng đo trên máy.

3. Đo lại Windows/Ubuntu/Docker theo thời gian, gồm qua nhiều chu kỳ 32s từng quan sát và sau sleep/resume. Chạy lại strict JWT probe/HTTP auth và hồi quy auth/session qua runner cô lập; xem trực tiếp console. Xác nhận không còn bước lùi làm token vừa cấp bị từ chối, không tăng JWT leeway, retry hay lùi `iat`. Lưu kết luận ngắn trong PROGRESS, không lưu output thô thành file.

4. Chỉ đóng QA-04 khi đã thực hiện thay đổi runtime và có kiểm chứng sau sửa; các lượt 400/400 HTTP, 21.761 mẫu probe hoặc E2E xanh trước can thiệp không đủ. T12 vẫn cần staging HTTPS, Android/iPhone thật và pilot. Hướng dẫn lệnh Windows chính thức: [Windows Time tools](https://learn.microsoft.com/en-us/windows-server/networking/windows-time-service/Windows-Time-Service-Tools-and-Settings).

## Tùy chỉnh màu thương hiệu
1. Chạy migration tới 0007_branding và triển khai frontend/backend cùng phiên bản.
2. Đăng nhập /operator/login → Màu thương hiệu của spa → chọn màu hoặc nhập HEX, xem trước → Lưu màu thương hiệu. Có thể chọn màu ngay trong form cấp chủ spa.
3. Màu dùng chung cho chi nhánh/Admin/trang đặt lịch của deployment này. Spa trên deployment khác có cấu hình độc lập. Chủ spa vẫn đăng nhập /admin/login như cũ.
4. BACKEND_INTERNAL_URL của frontend phải trỏ đúng backend cùng deployment để màu render đầu/manifest đúng; API lỗi sẽ dùng màu mặc định. PWA đã cài có thể cần trình duyệt cập nhật manifest để đổi màu thanh hệ thống.

### E2E cô lập toàn bộ backend
Chạy pytest trong automation_test như hiện tại. Harness tự tạo container API và database spaos_e2e_<UUID>, migrate rồi seed demo/Operator QA CHỈ trong database tạm. Mọi API của browser và ApiHelper đi vào backend tạm; credentials demo trong fixture không lấy tài khoản thật. Teardown dọn đúng container/database được tạo. Cần Docker Compose và migration role có quyền CREATE DATABASE trong QA. Không chạy trên production.
Frontend vẫn dùng FRONTEND_URL (nên chọn server thử riêng); SSR metadata dùng BACKEND_INTERNAL_URL của frontend, nên kiểm tra metadata/manifest thật tại deployment đúng cấu hình bên cạnh E2E client. Không seed spa-demo vào database ứng dụng để chạy lại bộ test.


### Đồng bộ đồng hồ và lỗi 401
Regression đã ghi nhận ImmatureSignatureError khi token mới bị coi là phát trong tương lai. Backend chấp nhận clock skew tối đa 2 giây cho cả token nghiệp vụ/Operator; vẫn cần đồng bộ NTP cho host/container. Log chỉ ghi loại lỗi xác thực, không ghi token/password. Token sai chữ ký/audience/scope/version hoặc vượt dung sai vẫn bị chặn.

### Tạo lịch nhiều buổi và kiểm tra kết quả — T01, 19/10/2026

- Backend/frontend cần triển khai cùng phiên bản và migrate tới `0008_manual_booking_batches` theo quy trình backup/migration hiện hành. Chưa chạy migration này trên database ứng dụng trong đợt QA.
- Tại quầy, một lần xác nhận tạo toàn bộ khách mới nếu có, thẻ mới nếu có và danh sách lịch trong một giao dịch. Một buổi xung đột/hết buổi sẽ rollback toàn bộ lần tạo; không có bước tự xóa bù dữ liệu.
- Nếu mất phản hồi, dùng **Kiểm tra kết quả** hoặc **Thử lại cùng yêu cầu**; cùng mã và nội dung không tạo thêm dữ liệu. **Kiểm tra sau** đóng vùng khôi phục nhưng giữ mã. Sau reload/quay lại trang Lịch, kiểm tra kết quả trước khi tạo mới; không tự gửi POST.
- Browser chỉ lưu UUID yêu cầu trong sessionStorage theo chi nhánh/người thao tác; không lưu hồ sơ khách. Không tự xóa mã hoặc thay trình duyệt để thử lại khi chưa rõ kết quả. Đóng hẳn tab/xóa browser storage làm mất tham chiếu khôi phục phía trình duyệt; phải đối chiếu khách/thẻ/lịch với Admin trước khi tạo lần mới.
- Giữ bảng `manual_booking_batches` trong backup và restore cùng dữ liệu khách/thẻ/lịch/audit; không xóa bản ghi chống lặp để tái dùng mã. Bảng có ENABLE/FORCE RLS theo tenant; GET kết quả kiểm tra lại actor và quyền hồ sơ hiện hành.
## Gate UI/UX cập nhật 19/10/2026

- Cập nhật T12: PO xác nhận chưa có staging HTTPS/thiết bị thật. Sau bổ sung log clock, backend isolated 98/98 và production regression auth/branches/operator/session/guard 44/44 PASS (run 9c4b7634); frontend không đổi. T12 vẫn mở, không dùng kiểm tra giả lập thay nghiệm thu thật.
- T11a/b/c/d đã đạt phạm vi Chromium, kế hoạch có 28/29 task hoàn tất. Production QA `86d9eaf7-ae95-42eb-ae99-d6d658765eeb`: build/TypeScript, full E2E 204/204 PASS; backend isolated 88/88, QA harness 23/23 PASS. Xem `PROGRESS.md` và `UI_UX_EXECUTION_PLAN.md` cho source/lệnh/run lỗi; không cần chạy lại chỉ vì sửa tài liệu.
- **Chưa chốt pilot/release:** T12 còn thiết bị Android Chrome/iPhone Safari thật, bàn phím ảo/safe area/zoom 200%/touch/Back/offline/Push và thử nghiệm cùng chủ spa/KTV/khách. Ghi thiết bị/OS/trình duyệt, vai trò, ngày, expected/actual và vấn đề; không thay bằng viewport Chromium.
- **QA-04 chưa đóng:** ImmatureSignatureError tái hiện setup run f5a26bdb. Cần đối chiếu iat/đồng hồ runtime khi lỗi và kiểm chứng staging; không tăng JWT leeway, sleep/retry để làm xanh. Probe đồng hồ ở run khác chỉ là quan sát, chưa chứng minh nguyên nhân.
- Khi QA-04 tái hiện, lấy dòng `Authentication clock validation rejected (ImmatureSignatureError)` và thời điểm/run tương ứng. Log chỉ gồm server_unix, iat/nbf ahead, utc-vs-wall, wall-vs-monotonic; không gửi JWT/credentials/claims định danh. Đối chiếu clock host/runtime ngay cùng sự cố; số liệu của run khác không đủ kết luận.
- Probe độc lập: `docker-compose run --rm --no-deps -e ENVIRONMENT=test --entrypoint python backend -B -m scripts.qa_clock_probe --seconds 120`. Override entrypoint nên không chạy migration/seed/server; probe không truy cập DB, không phát JWT cho tài khoản thật. Kết quả 21.761 mẫu không lỗi chỉ chứng minh cửa sổ đo đó, không đóng QA-04.
- Biên bản thiết bị/pilot khi có staging: ghi thiết bị/OS/trình duyệt, ngày/role, portrait/landscape; thử bàn phím ở form cuối, zoom 200%, safe area, Back/touch/offline/Push. Chủ spa thử tạo/dời lịch, dùng thẻ, thu đủ/một phần và đổi chi nhánh; KTV thử hồ sơ được giao/ngoài quyền; khách thử đặt/dời/hủy. Ghi expected/actual, bấm nhầm/trợ giúp/thời gian quan sát; không điền PASS nếu chưa thực hiện.
- Đổi chi nhánh dùng Web Locks để phối hợp form/giao dịch giữa các tab; trình duyệt thiếu API này bị chặn đổi với thông báo. Kiểm chứng trên HTTPS và trình duyệt hỗ trợ trước bàn giao. Backend JWT/tenant/RLS/row locks vẫn bắt buộc, không coi Web Locks là kiểm soát bảo mật dữ liệu.
- Database ứng dụng chưa áp migration 0008 trong các lượt QA; các yêu cầu backup/restore/RLS/staging/migration và vận hành bên dưới vẫn phải hoàn tất riêng. Không deploy từ kết quả UI xanh.



### UX theo vai trò — migration 0009 (21/10/2026)

Backend/frontend phải phát hành cùng phiên bản. Sao lưu trước nâng cấp, diễn tập restore vào PostgreSQL riêng, rồi chạy alembic upgrade head; không chạy seed_demo hoặc reset dữ liệu. 0009 thêm dữ liệu liên hệ, auth_version và 7 bảng theo tenant (ca ngoại lệ, logo, recovery grant, biên nhận đặt lịch khách, bàn giao, sự kiện và job thông báo). Giữ các bảng này trong backup; công cụ recovery kiểm tra RLS thêm cho bảng hiện diện ở phiên bản đang phục hồi. Không xóa biên nhận/sự kiện để tái dùng UUID. Downgrade chỉ theo kế hoạch bảo trì và đối chiếu giao dịch, không tự hủy dữ liệu mới để rollback giao diện.

Worker thông báo chạy theo lifespan backend, xử lý tenant lần lượt bằng runtime context, retry từ DB; không cần quyền bypass RLS. Giám sát hàng đợi chưa xử lý/lỗi kéo dài và việc worker tiếp tục chạy sau khởi động. Khi VAPID trống vẫn lưu in-app; jobs Push chỉ gửi khi cấu hình đủ. Provider có thể giao lại sau mất xác nhận mạng; thiết bị phải mở lịch để lấy trạng thái mới nhất. QA đặt VAPID rỗng và dùng mock, không chứng minh Push thật.

Liên kết khôi phục: spa xác minh đúng khách trước khi chủ cấp; gửi riêng, hạn 30 phút, một lần; không ghi token/link/password vào logs hay ticket công khai. Cấp mới hủy liên kết cũ. Khôi phục/đổi mật khẩu tăng version, phiên cũ bị từ chối. Không sử dụng link khi chưa đối chiếu khách.

Trước nghiệm thu ngoài local: HTTPS và Android/iPhone thật (quyền thông báo, ứng dụng màn hình chính, app đóng, thiết bị offline/rồi online); trình đọc màn hình/zoom/bàn phím ảo; pilot chủ/nhân viên/khách với nhiệm vụ UX_ROLE_REVIEW. Chưa có các kết quả này thì DC-03/DC-05/DC-07 và QA-04/T12 không tự đóng từ E2E.

## Phát hành 0.2.0 — cổng vận hành, bàn giao và hướng dẫn

1. Từ cùng source snapshot, chạy `python scripts/prepare_release.py --version 0.2.0 --release-id <ma-duy-nhat>`. Lệnh đóng dấu version/release/time và build ID riêng FE/BE vào source artifact trước build; không dùng secrets, không ghi tại startup. Không sửa lại metadata sau build hoặc dùng cùng release-id cho code khác.
2. Backup database và diễn tập restore theo quy trình hiện hành. Migration 0010_owner_recovery thêm duy nhất bảng grant chủ spa, giữ toàn bộ dữ liệu cũ. Không seed_demo/reset credentials. Rollback UI không xóa grant/audit phát sinh.
3. Build/deploy cả frontend và backend từ snapshot đã stamp; backend cần restart để nhận metadata mới. Không dùng mount source development hoặc --reload trong production. `.env` một mình không đổi được version đã build.
4. Đăng nhập /operator/login → Hệ thống & Phiên bản. Đối chiếu release mong đợi với browser/server/backend. Bản development không được coi đã xác nhận release; tab cũ cần lưu công việc rồi reload. Check migration, health và smoke nghiệp vụ riêng; cùng version không thay cho readiness.
5. Trong Swagger /docs, xem version ở tiêu đề; POST /api/v1/operator/login rồi Authorize bằng access_token trả về để gọi GET /api/v1/operator/system. JWT operator không dùng được cho API nghiệp vụ.
6. Sau tạo chủ spa, mở Quản lý & Bàn giao: kiểm tra tên/SĐT hiện tại, tải PNG từng trang hoặc PDF đầy đủ, sao chép tin nhắn link. PDF có trang quản lý, chỉ gửi riêng chủ spa; PNG trang khách/chi nhánh dùng để chia sẻ công khai. QR/link không chứa password/token. Gửi mật khẩu ban đầu hoặc link khôi phục qua tin nhắn riêng, không nhập vào file bàn giao.
7. Bộ bàn giao dùng origin hiện đang mở. Xuất trên tên miền HTTPS chính thức trước khi gửi; file đã tải không tự cập nhật khi đổi domain/thông tin. Không gửi ảnh localhost/QA cho khách. Không có file bàn giao lưu sẵn trên server.
8. Khôi phục chủ spa: xác minh danh tính ngoài app, nhập mật khẩu operator và cấp link 30 phút. Link chỉ hiện trong phiên hiện tại, không lưu plaintext tại server; mất link thì cấp mới (link cũ bị thu hồi). Chủ tự đặt mật khẩu, rồi đăng nhập /admin/login; các phiên cũ toàn chi nhánh bị thu hồi.
9. Entry: / dành cho khách (1 branch → chi nhánh đó, nhiều → danh sách); /admin/login dành cho chủ/nhân viên; /operator/login dành cho vận hành. Nút quản lý trên header và liên kết Quản trị hệ thống ở login.
10. PWA có manifest riêng cho /admin và từng chi nhánh; icon cấp ứng dụng vẫn dùng tài sản SpaOS hiện có, logo spa hiển thị trong UI/ảnh bàn giao chi nhánh. Các manifest cùng origin không tách kho dữ liệu đăng nhập; giữ guard và quyền như cũ. PWA đã cài từ manifest cũ có thể cần gỡ/cài lại để đổi ID/start_url; không tự migrate shortcut trên điện thoại.
11. Hướng dẫn & Cài ứng dụng có thể bỏ qua/mở lại. Android dùng install prompt khi browser cung cấp; iOS hướng dẫn Safari/Share/Add to Home Screen. Không tự xin Notification permission. Kiểm tra thực tế HTTPS trên Android/iPhone, Zalo/Messenger in-app browser, start_url và push trước nghiệm thu; Chromium giả lập không xác nhận native install.

Phụ thuộc mới qrcode và jspdf dùng tại trình duyệt cho xuất tài liệu. npm audit hiện còn cảnh báo của Next 14.2.15/PostCSS sẵn có; không tự nâng major Next trong đợt này. Cần xử lý riêng trước chốt production security readiness.

## Hotfix deploy Render 0.2.1
Xem [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md). Với Root Directory=backend và Build=pip install -r requirements.txt, Start Command phải là `python -m scripts.start_service`. Uvicorn trực tiếp không chạy migration. Lifespan từ chối schema cũ trước khi mở API/worker; advisory lock serialize DDL. Migration phải dùng MIGRATION_DATABASE_URL có quyền owner/DDL trỏ đúng database runtime; backup trước nâng cấp. /health 200 chỉ xuất hiện sau khi startup schema guard đạt; vẫn cần kiểm tra nghiệp vụ và release FE/BE. Không tự reset DB hoặc stamp head khi gặp tenants.address does not exist.
