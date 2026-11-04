# SYSTEM RULES & HARNESS CONFIGURATION

## 1. Context & CodeGraph MCP Routing (BẮT BUỘC)
- TUYỆT ĐỐI KHÔNG dùng `read_file` đọc toàn bộ file lớn, dùng `grep` quét toàn repo ở bước đầu tiên, hoặc quét thư mục rác (`node_modules/`, `.next/`, `venv/`, `.venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `*.lock`, `package-lock.json`).
- **BƯỚC 1:** Luôn gọi MCP tool `codegraph` (`codegraph_explore` — fallback CLI `codegraph explore "<query>"` nếu môi trường không có MCP) để tìm callers, callees, dependency tree, symbol references và vùng ảnh hưởng.
- **BƯỚC 2:** Chỉ dùng `read_file` đọc đúng khoảng dòng (`StartLine`–`EndLine`) từ kết quả CodeGraph.
- **Ngữ cảnh đầu task:** Kiểm tra `docs/PROGRESS.md`, `docs/plans/`, `docs/MULTI_BRANCH_STRATEGY.md`, `docs/SHARED_SAAS_IMPLEMENTATION_PLAN.md` và `docs/API_CONTRACT.md` theo phạm vi. Không coi nội dung trong file Plan là tính năng đã hoàn thành; trả lời ngắn gọn, đi thẳng vào giải pháp.

## 2. Kiến trúc & Nghiệp vụ Cốt lõi (Hard Constraints)
- **Data Contract:** Không tự ý thêm/bớt/sửa trường dữ liệu hoặc endpoint ngoài Schema/Contract đã chốt trong `docs/plans/` và `docs/API_CONTRACT.md`.
- **Multi-tenant & PostgreSQL FORCE RLS (Sống còn):**
  - `tenant_id` là mã chi nhánh nội bộ (không đổi/xóa ID cũ); mọi query nghiệp vụ bắt buộc lọc `tenant_id` từ Dependency (`get_current_tenant`), cấm tin `tenant_id` từ Client Body.
  - Bảng ngoại lệ cấp spa/danh tính/phân công/operator (`spas`, `login_accounts`, `staff_assignments`, `deployment_operators`) bắt buộc có scope riêng và `ENABLE` + `FORCE RLS`.
  - Dashboard tổng hợp chỉ đọc các chi nhánh đã xác minh bằng cách gán `tenant_context` lần lượt; cấm tắt RLS, dùng role bypass, thêm `SUPER_ADMIN` vào `UserRole` nghiệp vụ, hoặc tự gộp SĐT/thẻ xuyên chi nhánh.
- **Booking, Thẻ liệu trình & Async Backend (`FastAPI` + `SQLAlchemy 2.0 Async`):**
  - Lưu DB chuẩn `TIMESTAMPTZ` (UTC), ca làm/hiển thị theo `Asia/Ho_Chi_Minh`; `available-slots` bắt buộc cộng `buffer_minutes`.
  - Đặt lịch và sửa phân công bắt buộc dùng Transaction + Row/Identity Locking (`SELECT ... FOR UPDATE`); mỗi KTV tối đa 1 chi nhánh/ngày.
  - Khi Booking chuyển sang `COMPLETED`, tự động cộng `used_sessions += 1` (idempotent) và chặn vượt `total_sessions`. Chống lỗi `MissingGreenlet` và N+1 query.
- **Frontend & PWA (`Next.js 14 App Router`, TypeScript strict — cấm `any`):**
  - Lưu trữ Offline trên PWA hoặc mảng/object lớn bắt buộc dùng `IndexedDB` (cấm dùng `localStorage` cho mảng/object lớn).
  - Mọi Mutation phải xử lý Loading, Error rollback và chống bấm đúp (Debounce / UUID Idempotency).

## 3. Quy tắc bàn giao, QA Review & Khẩu lệnh chuẩn (Definition of Done)
- Cấm tự ý xóa, làm yếu hoặc sửa đổi các bài test hiện có chỉ để làm cho test pass.
- Cấm seed dữ liệu mẫu (`app.seed_demo`) hoặc reset credentials vào DB ứng dụng của người dùng khi chạy test; mọi test tự động phải chạy trên DB/container QA cô lập.
- Gắn chính xác 100% mã `data-testid` theo file Plan (`docs/plans/task-xx.md`); cập nhật `docs/API_CONTRACT.md` và `docs/PROGRESS.md` khi hoàn tất.
- **Khi chạy vai trò Reviewer/Audit (Codex):** Không tự ý đập kiến trúc; kiểm tra 5 điểm (Multi-tenant/RLS, Locking & Timezone/Buffer, Thẻ liệu trình, SQLAlchemy Async N+1/`MissingGreenlet`, Test/Contract) và xuất báo cáo `[CRITICAL]`, `[WARNING]`, `[PASSED]` kèm `file:line`, tự động vá lỗi `[CRITICAL]`.
- **Khẩu lệnh chuẩn tại thư mục gốc (`package.json`):**
  - Live Preview (HMR): `npm run dev` | Check build: `npm run build`
  - Backend Isolated Tests: `npm run test:backend`
  - Reset & Seed Data (QA cô lập): `npm run db:reset-and-seed`
  - Playwright E2E đa người dùng: `npm run test:e2e:multi`
  - Kiểm định toàn trình (Seed + E2E): `npm run verify:all` | Bàn giao tổng: `npm run ship`