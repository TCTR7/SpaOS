# AI_ORCHESTRATION_PLAYBOOK.md
> **Sổ tay Quy chuẩn Điều phối Multi-Agent & Kiểm định Hệ thống Thực chiến**
> **Mục tiêu:** Vận hành mô hình "One-Person Squad" — Tối ưu hóa Token qua MCP, Khóa kiến trúc bằng Data Contract, Kiểm chứng chéo độc lập (Dual-Session TDD) và Tự động hóa E2E đa người dùng.

---

## PHẦN 1: QUY TRÌNH KHỞI TẠO DỰ ÁN MỚI (PROJECT BOOTSTRAP CHECKLIST)

Mỗi khi bắt đầu một dự án mới (hoặc chuẩn hóa dự án đang chạy), thực hiện 4 bước thiết lập nền móng sau trước khi viết tính năng đầu tiên:

- [ ] **Bước 1 — Thiết lập `AGENTS.md`:** Tạo file luật chơi tinh gọn ở thư mục gốc để khóa kiến trúc và ép Agent dùng `codegraph` MCP (Xem mẫu ở Phần 2).
- [ ] **Bước 2 — Tạo thư mục lưu trữ Plan:** Tạo thư mục `docs/plans/` để lưu trữ các bản đặc tả kỹ thuật và hợp đồng dữ liệu (`task-xx.md`) cho từng tính năng.
- [ ] **Bước 3 — Chuẩn hóa lệnh điều khiển (`package.json`):** Gắn bộ script chuẩn hóa (`db:reset-and-seed`, `test:e2e:multi`, `verify:all`, `ship`) để mọi Agent đều dùng chung một khẩu lệnh (Xem mẫu ở Phần 6).
- [ ] **Bước 4 — Bật môi trường Live Preview:** Khởi chạy `npm run dev` (HMR) chia đôi màn hình với Terminal/IDE để quan sát giao diện cập nhật thời gian thực trong lúc Agent code.

---

## PHẦN 2: KỸ NĂNG 1 — QUẢN TRỊ NGỮ CẢNH & ĐIỀU HƯỚNG CÔNG CỤ (CONTEXT & MCP ROUTING)

### 1. Nguyên tắc cốt lõi
- Không để Agent dùng `read_file` đọc tràn lan toàn bộ file hoặc dùng `grep` quét mù quáng gây tốn token và làm "loãng" bộ nhớ ngữ cảnh (Context Pollution).
- Không để AI viết những mô tả thư mục hiển nhiên vào `AGENTS.md`. Chỉ ghi **Quy tắc điều hướng công cụ (Routing Rules)** và **Danh sách cấm kỵ (Anti-patterns)**.

### 2. Mẫu chuẩn file `/AGENTS.md` (Copy vào thư mục gốc của Project)
```markdown
# SYSTEM RULES & HARNESS CONFIGURATION

## 1. Context & CodeGraph MCP Routing (BẮT BUỘC)
- TUYỆT ĐỐI KHÔNG dùng `read_file` đọc toàn bộ file lớn hoặc dùng `grep` quét toàn repo ở bước đầu tiên.
- BƯỚC 1: Luôn gọi MCP tool của `codegraph` (tìm callers, callees, dependency tree, symbol references) để xác định chính xác file và dòng lệnh bị ảnh hưởng.
- BƯỚC 2: Chỉ dùng `read_file` đọc đúng khoảng dòng (line range) nằm trong kết quả của CodeGraph.

## 2. Kiến trúc & Dữ liệu (Hard Constraints)
- Không tự ý thêm/bớt/sửa trường dữ liệu ngoài file Schema/Contract đã chốt trong `docs/plans/`.
- Với lưu trữ Offline trên PWA: Bắt buộc dùng IndexedDB (cấm dùng `localStorage` cho mảng dữ liệu hoặc object lớn).
- Mọi hàm thay đổi dữ liệu (Mutation) phải xử lý trạng thái Loading, Error rollback và chống bấm đúp (Debounce / Idempotency).

## 3. Quy tắc bàn giao (Definition of Done)
- Cấm tự ý xóa, làm yếu hoặc sửa đổi các bài test hiện có chỉ để làm cho test pass.
- Bắt buộc gắn chính xác 100% các mã `data-testid` đã được định nghĩa trong file Plan của task.