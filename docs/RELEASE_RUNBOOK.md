# Chạy thử trước phát hành SpaOS

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
