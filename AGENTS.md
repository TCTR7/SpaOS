> **LUẬT BẮT BUỘC DÒNG ĐẦU TIÊN (`codegraph` MCP — QUY TRÌNH PHỄU):** Luôn bắt đầu bằng `codegraph_query` để lấy danh sách tên symbol và tọa độ dòng trước; sau đó mới dùng `codegraph_callers`/`callees`/`impact` và `codegraph_node` (chỉ truyền tên hàm/class cụ thể). TUYỆT ĐỐI KHÔNG dùng `read_file` đọc tràn lan, KHÔNG dùng `grep` quét mù toàn repo, và CẤM gọi `codegraph_explore` ở bước đầu tiên.

# SYSTEM RULES & HARNESS CONFIGURATION — SpaOS Monorepo

## 1. Context & CodeGraph MCP Routing (BẮT BUỘC TUÂN THỦ THEO THỨ TỰ)
- TUYỆT ĐỐI KHÔNG dùng `read_file` đọc toàn bộ các file lớn (như `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `backend/app/api/v1/experience.py`, `models.py`), KHÔNG dùng `grep` quét toàn repo, và KHÔNG quét thư mục rác (`node_modules/`, `.next/`, `venv/`, `.venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `automation_test/artifacts/`).
- **BƯỚC 1 — Tìm tên Symbol (Siêu nhẹ):** Luôn gọi `codegraph_query` (fallback CLI: `codegraph query "<từ_khóa>"`) với từ khóa ngắn gọn để lấy tên hàm/class/endpoint và vị trí dòng. Khi chưa biết tên symbol, BẮT BUỘC dùng `codegraph_query` để dò tìm, KHÔNG được lấy lý do chưa biết symbol để gọi `codegraph_explore`.
- **BƯỚC 2 — Kiểm tra liên đới:** Gọi `codegraph_callers`, `codegraph_callees` hoặc `codegraph_impact` trên tên symbol vừa tìm được để nắm luồng gọi hàm và vùng ảnh hưởng.
- **BƯỚC 3 — Đọc mã nguồn nội soi (`Surgical Read`):**
  - Gọi `codegraph_node` với **chính xác tên hàm/class cụ thể** (TUYỆT ĐỐI KHÔNG truyền đường dẫn cả file dài vào `codegraph_node`).
  - Chỉ dùng `read_file` đọc đúng khoảng dòng (`StartLine`–`EndLine`, tối đa 80–120 dòng/lần) từ kết quả của CodeGraph.
  - Chỉ được phép gọi `codegraph_explore` (tối đa 1 lần/task) nếu đã thử `codegraph_query` với 2 từ khóa khác nhau mà không ra kết quả.
- **BƯỚC 4 — Khoanh vùng Test sau khi sửa:** Chạy `codegraph affected <file-vừa-sửa>` để xác định đúng file test `.py` bị ảnh hưởng trước khi chạy kiểm thử.
- **Ngữ cảnh đầu task:** Kiểm tra có chọn lọc `docs/PROGRESS.md`, `docs/plans/`, `docs/MULTI_BRANCH_STRATEGY.md`, `docs/SHARED_SAAS_IMPLEMENTATION_PLAN.md` và `docs/API_CONTRACT.md` theo phạm vi. Không coi nội dung trong file Plan là tính năng đã hoàn thành; trả lời ngắn gọn, đi thẳng vào giải pháp.

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

## 3. Quy tắc bàn giao & Khẩu lệnh chuẩn (Definition of Done)
- Cấm tự ý xóa hoặc làm yếu các bài test hiện có chỉ để làm cho test pass.
- Cấm seed dữ liệu mẫu (`app.seed_demo`) hoặc reset credentials vào DB ứng dụng của người dùng khi chạy test; mọi test tự động phải chạy trên DB/container QA cô lập.
- Gắn chính xác 100% mã `data-testid` theo file Plan (`docs/plans/task-xx.md`); cập nhật `docs/API_CONTRACT.md` và `docs/PROGRESS.md` khi hoàn tất.
- **Khi chạy vai trò Reviewer/Audit (Codex):** Không tự ý đập kiến trúc; kiểm tra 5 điểm (Multi-tenant/RLS, Locking & Timezone/Buffer, Thẻ liệu trình, SQLAlchemy Async N+1/`MissingGreenlet`, Test/Contract) và xuất báo cáo `[CRITICAL]`, `[WARNING]`, `[PASSED]` kèm `file:line`, tự động vá lỗi `[CRITICAL]`.
- **Trong quá trình sửa lỗi (Iterative Debugging):** TUYỆT ĐỐI KHÔNG chạy `npm run verify:all` hay chạy toàn bộ test suite. Bắt buộc dùng `codegraph affected <file-vừa-sửa>` để tìm file test, sau đó chỉ chạy ĐÚNG 1 bài test đang lỗi với cờ rút gọn (`--maxfail=1 --tb=short -q`).
- **Khẩu lệnh chuẩn kiểm thử tiết kiệm token:**
  - AI Unit/Backend Test: `npm run test:ai:unit -- <file_test> -k "<test_name>"`
  - AI Playwright E2E Test: `npm run test:ai:e2e -- <file_test> -k "<test_name>"`
- **Khẩu lệnh điều phối hệ thống:**
  - Live Preview (HMR): `npm run dev` | Check build: `npm run build`
  - Backend Isolated Tests: `npm run test:backend`
  - Reset & Seed Data (QA cô lập): `npm run db:reset-and-seed`
  - Playwright E2E đa người dùng: `npm run test:e2e:multi`
  - Kiểm định toàn trình (Seed + E2E): `npm run verify:all` | Bàn giao tổng: `npm run ship`

## 4. Chốt chặn chống tràn Token (Strict Token Guardrails)
- **Cấm tự ý chụp và đọc ảnh (Anti-Vision Bloat):** TUYỆT ĐỐI KHÔNG tự ý chạy các script chụp màn hình hàng loạt (`layout_evidence.py`, `layout_probe.py`, `run_ui_qa.py`, hoặc script `fullPage: true`) và TUYỆT ĐỐI KHÔNG dùng công cụ đọc/xem file ảnh (`.png`, `.jpg`, `.webp`) trong `automation_test/artifacts/` để debug giao diện trừ khi chủ dự án yêu cầu rõ ràng. Mọi kiểm tra vị trí, hiển thị phải thực hiện qua Playwright Assertions (`expect(locator).to_be_visible()`, `bounding_box()`, `evaluate()`).
- **Cấm đọc log rác & DOM Snapshot:** TUYỆT ĐỐI KHÔNG quét hoặc đọc các file trong `automation_test/artifacts/`, `error-context.md`, `trace.zip`, hoặc `.pytest_cache/`. Khi chạy pytest, luôn giữ cờ `--tb=short -q --maxfail=1` để chỉ đọc thông báo lỗi ngắn gọn từ stdout.
- **Circuit Breaker (Cầu chì ngắt vòng lặp):** Nếu 1 bài test FAIL liên tiếp sau **2 lần sửa code**, DỪNG NGAY LẬP TỨC việc chạy lệnh và sửa tiếp. Báo cáo nguyên nhân gốc rễ ngắn gọn (dưới 10 dòng) và chờ chủ dự án chỉ đạo.
