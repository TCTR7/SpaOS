# Backend SpaOS trên Render

Cấu hình native Python của service hiện tại:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: **`python -m scripts.start_service`**
- Health Check Path: `/health`

Start Command cũ `uvicorn app.main:app --host 0.0.0.0 --port $PORT` mở API trực tiếp và bỏ qua migration. Đó là nguyên nhân code mới đọc `tenants.address` trong khi database chưa có cột này.

## Trước khi redeploy

1. Backup database production và xác nhận khả năng restore. Giữ nguyên database/dữ liệu đang có; không reset, không xóa bảng, không chạy seed_demo.
2. Trong Environment, kiểm tra `DATABASE_URL` và `MIGRATION_DATABASE_URL` trỏ đến **cùng database Render**. `DATABASE_URL` dùng role runtime không bypass RLS; `MIGRATION_DATABASE_URL` dùng role có quyền DDL/owner. Cả hai dùng driver `postgresql+asyncpg://...` như cấu hình hiện hành. Không gửi URL chứa mật khẩu vào chat hoặc log.
3. Giữ secrets JWT/VAPID/operator đã có. `ENVIRONMENT=production`. Seed chỉ bootstrap operator từ cấu hình và không đổi tài khoản đã tồn tại.
4. Push toàn bộ source đã cập nhật, gồm migration `0009_role_experience` và `0010_owner_recovery`. Đổi Start Command như trên, Save và deploy bản mới. File này không tự thay đổi settings của service Render hiện có.

## Thứ tự khởi động

`scripts.start_service` chạy lần lượt:

1. `alembic upgrade head` bằng `MIGRATION_DATABASE_URL`.
2. `python -m app.seed`: chỉ bootstrap operator từ secrets, không seed dữ liệu demo hoặc reset credentials hiện có.
3. Uvicorn qua đúng Python interpreter, host `0.0.0.0`, port từ `$PORT`, không có `--reload`.

Migration có advisory lock theo database để hai tiến trình deploy không chạy DDL đồng thời. Bất kỳ bước chuẩn bị thất bại thì API không được mở cổng. FastAPI còn kiểm tra revision bằng **runtime DATABASE_URL**, đồng thời kiểm tra cột address/contact_phone trước khi khởi động notification worker. Nếu hai URL trỏ nhầm database khác nhau, schema guard sẽ từ chối bản runtime còn cũ.

Không chạy `alembic stamp head` để bỏ qua lỗi: stamp chỉ ghi revision, không tạo cột/bảng. Nếu DB từng bị stamp sai, cần đối chiếu schema và backup trước khi sửa, không tự thêm mỗi cột address rồi bỏ qua các bảng/chính sách còn thiếu.

## Kiểm tra sau deploy

- Logs có upgrade tới migration head hiện hành (`0010_owner_recovery` trong bản này) hoặc xác nhận đã ở head, sau đó server start thành công.
- `/health` HTTP 200; `/api/v1/branches/public` HTTP 200.
- Swagger `/docs` hiển thị đúng version/release. Operator → Hệ thống & Phiên bản đối chiếu đúng FE/BE cùng release mong đợi.
- Kiểm tra đăng nhập và đọc dữ liệu hiện có; không thử reset mật khẩu hoặc tạo dữ liệu QA trên production để xác minh deploy.

Nếu vẫn lỗi, gửi log lỗi đã che thông tin nhạy cảm. Không đổi URL/secrets ngẫu nhiên hoặc reset DB. Bộ kiểm thử local/QA không tự áp migration trên database Render.

Nếu Render plan có Pre-deploy Command, có thể chạy migration ở bước đó trước khi thay traffic; đây là lựa chọn tối ưu cho nhiều instance. Quy trình Start Command ở trên vẫn hoạt động khi không có tính năng pre-deploy. Tham khảo [Render Deploys](https://render.com/docs/deploys#pre-deploy-command) và [FastAPI trên Render](https://render.com/docs/deploy-fastapi).
