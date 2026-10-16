# HIẾN PHÁP DỰ ÁN & ĐIỀU PHỐI MULTI-AGENT (AGENTS.md)

Dự án **SpaOS (Nền tảng Quản lý và Đặt lịch Spa chuẩn SaaS)**[cite: 1, 2] sử dụng quy trình kết hợp 2 AI Agent: **Antigravity (Model Argon)** làm Builder và **Codex** làm Reviewer/QA. Mọi Agent BẮT BUỘC tuân thủ tuyệt đối các quy tắc dưới đây.

---

## 1. QUY TẮC TIẾT KIỆM QUOTA & CÔ LẬP MONOREPO (`backend/` & `frontend/`)
- **Bỏ qua thư mục rác (Ignore Paths):** TUYỆT ĐỐI KHÔNG quét, đọc hoặc index: `node_modules/`, `.next/`, `venv/`, `.venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `*.lock`, `package-lock.json`.
- **Trả lời ngắn gọn:** Đi thẳng vào code và giải pháp. Không chào hỏi, không giải thích khái niệm cơ bản, không tóm tắt lại yêu cầu ở cuối câu.
- **Cấu trúc Monorepo:**
  - `backend/`: Chứa mã nguồn Python (FastAPI)[cite: 1, 3], `requirements.txt`, `alembic/`, `app/`, `tests/`.
  - `frontend/`: Chứa mã nguồn Next.js (PWA & Web Admin)[cite: 1, 3], `package.json`, `src/app/`.
  - `docker-compose.yml`: Đặt tại thư mục gốc (Root).
- **Cô lập Context theo Sprint:**
  - **Sprint 1 -> Sprint 4 (Backend):** CHỈ làm việc trong `backend/`, `docs/`[cite: 3] và `docker-compose.yml`. TUYỆT ĐỐI KHÔNG đọc hay chạm vào `frontend/`[cite: 3].
  - **Sprint 5 -> Sprint 6 (Frontend):** CHỈ làm việc trong `frontend/`[cite: 3] và đọc `docs/API_CONTRACT.md`[cite: 3]. TUYỆT ĐỐI KHÔNG đọc lại source code trong `backend/`[cite: 3] trừ khi được yêu cầu sửa bug API.

---

## 2. QUY TẮC KIẾN TRÚC & BẢO MẬT MULTI-TENANT (SỐNG CÒN)
- **Cô lập dữ liệu (Data Isolation):** Mọi bảng nghiệp vụ trong PostgreSQL BẮT BUỘC có cột `tenant_id` (Foreign Key)[cite: 1].
- **Bảo mật tầng Backend (FastAPI):**
  - Bắt buộc viết Dependency Injection `get_current_tenant()` trích xuất `tenant_id` từ JWT Token (cho Admin/Staff)[cite: 1] hoặc từ Header/Slug (cho Customer).
  - Mọi câu lệnh `SELECT`, `INSERT`, `UPDATE`, `DELETE` qua SQLAlchemy BẮT BUỘC phải lọc theo `tenant_id` từ Dependency này[cite: 1]. Không bao giờ tin tưởng `tenant_id` gửi từ Client Body.
- **Bảo mật tầng Database (PostgreSQL RLS):** Thiết lập Row-Level Security (RLS) trên PostgreSQL làm lớp bảo vệ thứ 2 chống rò rỉ dữ liệu chéo giữa các Spa.

---

## 3. QUY CHUẨN KỸ THUẬT (TECH STACK STANDARDS)
- **Backend (Python FastAPI):**[cite: 1] Dùng `SQLAlchemy 2.0+` (AsyncSession), `asyncpg`, `Pydantic v2`, `Alembic`.
- **Thời gian & Chống trùng lịch (Concurrency & Timezone):**
  - Mọi cột thời gian (`start_time`, `end_time`, `created_at`) trong DB phải lưu chuẩn `TIMESTAMPTZ` (UTC). Khi tính toán ca làm việc/hiển thị thì quy đổi về `Asia/Ho_Chi_Minh`.
  - API Đặt lịch (`POST /api/v1/bookings`) BẮT BUỘC dùng Database Transaction + Row Locking (`SELECT ... FOR UPDATE`) để chặn Race Condition khi 2 khách đặt trùng 1 kỹ thuật viên cùng lúc[cite: 1].
- **Frontend (Next.js App Router):** Dùng TypeScript nghiêm ngặt (cấm dùng `any`), TailwindCSS[cite: 1] + `shadcn/ui`. Phân tách `/app/(admin)/*` và `/app/[tenant_slug]/*`.

---

## 4. QUẢN LÝ BỘ NHỚ (`docs/`) & LỆNH THỰC THI
- **Luồng tài liệu (`docs/`):**[cite: 3]
  1. Đọc `docs/Spa_SaaS_PRD.md` để lấy yêu cầu nghiệp vụ, DB Schema và lộ trình Sprint[cite: 1, 3].
  2. Đọc `docs/PROGRESS.md` trước mỗi yêu cầu mới để nắm trạng thái hiện tại; đánh dấu `[x]` sau khi hoàn thành Sprint[cite: 3].
  3. Cập nhật mọi Endpoint mới viết vào `docs/API_CONTRACT.md`[cite: 3].
- **Lệnh Terminal chuẩn:**
  - DB: `docker compose up -d`
  - Backend: `cd backend && alembic upgrade head && uvicorn app.main:app --reload --port 8000`
  - Test Backend: `cd backend && pytest -v`
  - Frontend: `cd frontend && npm run dev` | Check build: `cd frontend && npm run build`

---

## 5. PHÂN CÔNG VAI TRÒ (BUILDER vs REVIEWER)

### Vai trò 1: BUILDER AGENT (Antigravity - Model Argon)
- Thực thi viết code theo từng Sprint trong `docs/Spa_SaaS_PRD.md`[cite: 3].
- Sau mỗi Sprint: Tự chạy test (`pytest` hoặc `npm run build`), cập nhật `docs/API_CONTRACT.md` và `docs/PROGRESS.md`[cite: 3].

### Vai trò 2: REVIEWER & QA AGENT (Codex)
Khi người dùng yêu cầu Review sau mỗi Sprint, Codex KHÔNG tự ý đập đi xây lại kiến trúc mà thực hiện Audit theo **Checklist 5 điểm**:
1. **Rò rỉ Multi-tenant:** Có query nào thiếu `WHERE tenant_id == current_tenant_id` không[cite: 1]? RLS đã bật chưa?
2. **Chống trùng lịch:** API Booking đã có `SELECT ... FOR UPDATE` chưa[cite: 1]? Tính `available-slots` đã cộng `buffer_minutes` và chuẩn Timezone chưa?
3. **Nghiệp vụ Thẻ liệu trình:** Khi Booking chuyển sang `COMPLETED`[cite: 1], có tự động cộng `used_sessions += 1` và chặn vượt quá `total_sessions` không?
4. **Hiệu năng Async:** Có lỗi `MissingGreenlet` hay N+1 query trong SQLAlchemy Async không?
5. **Báo cáo:** Xuất kết quả theo 3 mức `[CRITICAL]`, `[WARNING]`, `[PASSED]` kèm tên file, dòng lỗi và tự động vá các lỗi `[CRITICAL]`.