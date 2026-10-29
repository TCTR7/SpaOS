# Backend SpaOS trên Render

Cấu hình native Python của service hiện tại:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command cố định: **`uvicorn app.main:app --host 0.0.0.0 --port $PORT`**
- Health Check Path: `/health`

**Cập nhật 28/10/2026:** FastAPI lifespan tự đọc revision DB runtime và migration head của code. Chỉ khi khác version mới chạy `python -m alembic upgrade head`, sau đó kiểm tra cấu trúc/ownership trước nhận request. Vì vậy Uvicorn trực tiếp đã hỗ trợ auto-migration. Sự cố Uvicorn bỏ qua migration được mô tả trước đây là hành vi của bản cũ.

## Trước khi redeploy

1. Backup database production và xác nhận khả năng restore. Giữ nguyên database/dữ liệu đang có; không reset, không xóa bảng, không chạy seed_demo.
2. Trong Environment, kiểm tra `DATABASE_URL` và `MIGRATION_DATABASE_URL` trỏ đến **cùng database PostgreSQL**. `DATABASE_URL` dùng role runtime không bypass RLS; `MIGRATION_DATABASE_URL` dùng role có quyền DDL/owner. Cả hai dùng driver `postgresql+asyncpg://...` như cấu hình hiện hành. Không gửi URL chứa mật khẩu vào chat hoặc log.
3. Giữ secrets JWT/VAPID/operator đã có. `ENVIRONMENT=production`. Seed chỉ bootstrap operator từ cấu hình và không đổi tài khoản đã tồn tại.
4. Push toàn bộ source đã cập nhật, gồm migration tới `0012_shared_spas` và startup mới. Đặt Start Command như trên, Save và deploy bản mới. File này không tự thay đổi settings của service Render hiện có.

## Thứ tự khởi động

Với Uvicorn trực tiếp, trước khi phục vụ API:

1. Đọc revision qua `DATABASE_URL`, so với Alembic head trong code.
2. Nếu thiếu migration, chạy Alembic bằng `MIGRATION_DATABASE_URL`; nếu đã khớp thì bỏ qua bước nâng version. Nhiều worker được serialize bởi advisory lock hiện có trong Alembic.
3. Kiểm tra lại revision, cột/bảng bắt buộc và mapping ownership production. Migration/guard lỗi thì startup thất bại, chưa chạy worker hoặc phục vụ API. Không dùng `--lifespan off` vì sẽ tắt bước chuẩn bị này.

Auto-migration chỉ nâng schema; không tự map dữ liệu cũ, reset DB, seed demo hoặc đổi credentials. Với cài đặt mới cần bootstrap operator, chạy `python -m app.seed` từ secrets cấu hình một lần. `python -m scripts.start_service` vẫn được hỗ trợ và giữ bootstrap operator như trước.

Entry `scripts.start_service` chạy lần lượt:

Trước các bước dưới đây, `python -m scripts.check_database` kiểm tra cả hai kết nối bằng SELECT 1, in nguồn cấu hình (environment hoặc dotenv/default) và kết quả, không in URL/mật khẩu. Có thể chạy riêng lệnh này để chẩn đoán, không migrate/seed. Kết nối OK chưa chứng minh đủ quyền DDL hoặc schema đúng.

1. `alembic upgrade head` bằng `MIGRATION_DATABASE_URL`.
2. `python -m app.seed`: chỉ bootstrap operator từ secrets, không seed dữ liệu demo hoặc reset credentials hiện có.
3. Uvicorn qua đúng Python interpreter, host `0.0.0.0`, port từ `$PORT`, không có `--reload`.

Migration có advisory lock theo database để hai tiến trình deploy không chạy DDL đồng thời. Bất kỳ bước chuẩn bị thất bại thì API không được mở cổng. FastAPI còn kiểm tra revision bằng **runtime DATABASE_URL**, đồng thời kiểm tra cột address/contact_phone trước khi khởi động notification worker. Nếu hai URL trỏ nhầm database khác nhau, schema guard sẽ từ chối bản runtime còn cũ.

Không chạy `alembic stamp head` để bỏ qua lỗi: stamp chỉ ghi revision, không tạo cột/bảng. Nếu DB từng bị stamp sai, cần đối chiếu schema và backup trước khi sửa, không tự thêm mỗi cột address rồi bỏ qua các bảng/chính sách còn thiếu.

## Kiểm tra sau deploy

- API startup thành công sau kiểm tra schema; `python -m alembic current` trong console riêng cho revision head hiện hành (`0012_shared_spas` trong bản này).
- `/health` HTTP 200; `/api/v1/branches/public` HTTP 200.
- Swagger `/docs` hiển thị đúng version/release. Operator → Hệ thống & Phiên bản đối chiếu đúng FE/BE cùng release mong đợi.
- Kiểm tra đăng nhập và đọc dữ liệu hiện có; không thử reset mật khẩu hoặc tạo dữ liệu QA trên production để xác minh deploy.

Nếu vẫn lỗi, gửi log lỗi đã che thông tin nhạy cảm. Không đổi URL/secrets ngẫu nhiên hoặc reset DB. Bộ kiểm thử local/QA không tự áp migration trên database Render.

### Xác thực bị từ chối (28P01)

Log Alembic bị từ chối xác thực user postgres xảy ra khi kết nối MIGRATION_DATABASE_URL, trước khi chạy DDL. Điều này chưa xác định mật khẩu đã bị đổi hay người dùng nhập sai: cần đối chiếu giá trị có hiệu lực, endpoint, username và cách mã hóa password trong URL. Không gửi URL hoặc secrets vào chat.

Với Uvicorn mới, nếu schema đã ở head thì không cần dùng migration URL trong lượt khởi động đó. Nếu có migration mới, Alembic bắt buộc dùng MIGRATION_DATABASE_URL; lỗi kết nối sẽ dừng startup. Nếu migration từng thành công, cần so cấu hình của lần đó với môi trường hiện tại. Biến môi trường được ưu tiên hơn dotenv; script start_service chuyển cwd về backend trước khi gọi các bước chuẩn bị.

Có thể giữ Start Command Uvicorn cố định như trên; script start_service là lựa chọn tương thích có thêm kiểm tra kết nối/bootstrap operator. Xem kết quả kiểm tra riêng hai biến trên Render; chỉ điều chỉnh giá trị sau khi đối chiếu với nhà cung cấp database đang dùng (database không nhất thiết nằm trên Render). Giữ runtime role không bypass RLS, không dùng postgres thay runtime để né lỗi. Khi tự ghép URL, percent-encode riêng password có ký tự đặc biệt, không encode hai lần. Chỉ xác nhận production hoàn tất sau khi kết nối, migration và /health đều đạt.

Nếu Render plan có Pre-deploy Command, có thể chạy migration ở bước đó trước khi thay traffic; đây là lựa chọn tối ưu cho nhiều instance. Quy trình Start Command ở trên vẫn hoạt động khi không có tính năng pre-deploy. Tham khảo [Render Deploys](https://render.com/docs/deploys#pre-deploy-command) và [FastAPI trên Render](https://render.com/docs/deploy-fastapi).
