# Chuyển sang shared SaaS — runbook

Mã nguồn đã có migration mở rộng `0012_shared_spas` và công cụ mapping. **Chưa áp dụng vào DB ứng dụng hiện hành.** Chỉ thực hiện cutover thật khi đã xác định môi trường, người vận hành và mapping được đối chiếu. Không dùng seed_demo hoặc test fixtures vào DB thật.

## Chuẩn bị

1. Đọc technical design và kết quả QA. Ghi nhận release frontend/backend cùng phiên bản, cấu hình origin HTTPS công khai và runtime role không bypass RLS.
2. Sao lưu custom-format ra nơi bảo mật ngoài server; thử restore sang DB riêng, kiểm tra rows/IDs/FK/policies và quyền runtime. Có bản sao cấu hình/role ở nơi quản lý secrets; không đưa chúng vào git/log/argv.
3. Dừng mọi nguồn ghi khi chốt mapping, gồm web/API/job/worker có ghi. Bản sao staging và bản thật phải được kiểm tra độc lập; không lấy kết quả mẫu làm xác nhận dữ liệu khách thật.
4. Chạy schema mở rộng trên **bản sao** trước. Cột spa_id cũ để null có chủ ý: API từ chối business access đến khi mapping; không tự nhận mọi tenant là cùng chủ.

## Inventory và mapping

Chạy trong backend đúng môi trường. DATABASE_URL dùng runtime role; MIGRATION_DATABASE_URL chỉ dành công cụ vận hành. Không in các biến này.

```powershell
python -m alembic upgrade head
python -m scripts.shared_spa_migration
python -m scripts.shared_spa_migration --mapping reviewed-mapping.json
```

Hai lệnh công cụ trên mặc định **không ghi dữ liệu**. Inventory chỉ xuất ID, quan hệ owner/account/branch, tài khoản cần chuẩn hóa và xung đột lịch; không xuất mật khẩu/SĐT khách. Lưu output/mapping trong nơi bảo mật, không commit dữ liệu thật.

Ví dụ cấu trúc mapping, UUID phải lấy từ inventory đã đối chiếu:

```json
{"spas":[{"id":"UUID-MOI-ON-DINH","slug":"spa-sen","name":"Spa Sen","theme_color":"#116633","owner_account_id":"UUID-CHU","tenant_ids":["UUID-CN1","UUID-CN2"]}]}
```

Mỗi chi nhánh cũ chưa mapping phải có đúng một đích và chủ đã có membership owner tại tất cả nhánh của nhóm. Dừng nếu nhiều chủ không rõ, account nối nhiều spa, operational user chưa có membership, SĐT chưa chuẩn hóa/xung đột, lịch tuần/ngoại lệ mâu thuẫn hoặc booking không khớp nơi làm. Không sửa hàng loạt theo tên/hash. Nếu cần chuẩn hóa SĐT hoặc giải quyết lịch cũ, thực hiện một đợt đối chiếu riêng trên bản sao rồi duyệt kế hoạch dữ liệu trước DB thật.

Tên/màu trong mapping là lựa chọn tường minh cho từng spa. Logo/bìa có thể được chủ cập nhật sau mapping bằng màn hình nhận diện; không tự áp singleton branding cũ cho mọi chủ. Legacy provision của operator giữ nguyên ID và được kiểm tra owner/account/spa khi hỗ trợ.

## Áp mapping và kiểm tra

Sau khi backup/restore đạt, đã dừng ghi và mapping đúng môi trường được duyệt:

```powershell
python -m scripts.shared_spa_migration --mapping reviewed-mapping.json --apply --confirm-maintenance
python -m scripts.shared_spa_migration --mapping reviewed-mapping.json
```

Apply chạy một transaction. Retry cùng mapping giữ ID và không nhân bản phân công đã có. Lỗi giữa chừng rollback; không đổi dữ liệu nghiệp vụ cũ. Xác minh trước khi mở ghi:

- Không còn tenant/account vận hành chưa mapping; quan hệ chủ/chi nhánh chính xác và membership không xuyên spa.
- So row counts/ID khách, thẻ, booking, tiền và các FK/policies với bản sao nguồn. Lịch cũ một nơi chuyển thành phiên bản tuần; nghỉ/ngoại lệ đúng ngày.
- Hai chủ đăng nhập chỉ thấy spa của mình; staff đa nhánh ưu tiên ca hôm nay, mất quyền chặn ở tab cũ; reset credentials chặn token cũ kể cả resolve.
- Đặt lịch, dời lịch, auto-assign, batch, hoàn thành thẻ và thu tiền hoạt động; chỉ một request thắng khi tranh cùng tài nguyên.
- Cập nhật branding riêng từng spa; link/QR/PWA/khôi phục và deep link mở đúng scope; public directory không liệt kê toàn nền tảng.
- Các bản ghi vượt gói cũ vẫn giữ; chỉ tạo/kích hoạt thêm bị chặn khi đạt giới hạn.

## Quay lui

Chưa mở ghi sau mapping: giữ maintenance, ghi lại lỗi; rollback transaction thất bại hoặc phục hồi bản backup đã kiểm chứng vào **DB riêng**, so sánh rồi mới chuyển kết nối/release theo quyết định vận hành. Không restore đè DB đang chạy.

Đã có phát sinh mới: dừng ghi, chụp bản sao trạng thái mới, đối chiếu phát sinh rồi forward-fix hoặc phục hồi có reconciliation. `alembic downgrade` tự động bị chặn ở 0012 để tránh xóa spa/phân công mới. Giữ bảng lịch cũ đến khi nghiệm thu, không dùng chúng thay phân công mới sau cutover.

## Lệnh QA có thể chạy lại

```powershell
docker compose exec -T backend python -m scripts.test_isolated -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/reviews/test_shared_saas.py -q --tb=short
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_shared_pilot
```

Runner tạo DB QA tạm, không seed/reset ứng dụng thật. Pilot chạy ba spa × 10 staff, tổng 60 request tranh giờ và 600 lượt đọc, sau đó backup/restore QA vào PostgreSQL tạm không network. Dump QA chỉ tồn tại trong thư mục tạm khi chạy; role/grants/secrets không được sao chép bởi rehearsal này.

Lượt đo 28/10/2026 sau sửa pool/auto-assign: đúng 30 lịch được nhận/30 conflict, 600 reads thành công; p95 booking 3,746.0–4,599.3 ms, p95 đọc lớn nhất 2,534.0 ms, đạt ngân sách local 5,000 ms. Backend snapshot sau tải 137.3 MiB/5.80% CPU, DB QA 10,681,367 bytes; không phải peak resource hoặc sức chứa production. Backup 197,226 bytes; 31 bảng và policies/RLS probes khớp sau restore. Có tải QA khác cùng máy và quan sát clock Docker điều chỉnh, cần đo lại trên staging đích trước chọn cấu hình/hạn mức; chưa thể suy ra số spa tối đa hay lợi nhuận.

## Gate trước pilot thật

- Chọn hosting và ngân sách theo đo trên cấu hình đích; chưa mua dịch vụ hoặc tự deploy trong đợt code này.
- Kiểm tra native Android/iOS HTTPS: cài hai spa trên cùng máy, logo/tên đúng, mở lại/hết phiên/đổi tài khoản/offline, subscribe/unsubscribe và push thật mở đúng booking/nhánh còn quyền.
- Backup ngoài môi trường ứng dụng, lịch retention, khôi phục cả role/secrets, giám sát lỗi/DB/worker/dung lượng/chi phí; xác định người xử lý và ngưỡng dừng pilot.
- Đối chiếu dữ liệu thật và duyệt cutover riêng. Chưa có thiết bị/môi trường đích thì gate để mở, không đánh dấu production-ready.


## Đồng hồ và kiểm chứng hồi quy

QA local đã từng ghi nhận clock Docker nhảy lùi, gây `ImmatureSignatureError` dù JWT vừa được cấp. Giữ nguyên tolerance hai giây và kiểm tra chữ ký/thời hạn/iat; không tự retry mutation hoặc bỏ xác thực để biến kết quả thành đạt. Kiểm tra đồng bộ thời gian host/VM/container trước release; sau bảo trì môi trường chạy hồi quy lại, không khởi động lại Docker/đổi clock khi đang phục vụ dữ liệu người dùng.

Đã có lượt backend full 150/150 PASS và nhóm sau thay đổi cuối 27/27 PASS, production nhóm 37/37 PASS; full production E2E 265 PASS/2 lỗi fixture clock; shared production sau deep link cuối 11/11 PASS. Xem báo cáo để phân biệt phạm vi từng lượt. Một lượt đạt không chứng minh clock môi trường đã được sửa lâu dài.
