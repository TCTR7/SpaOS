# Automation SpaOS

Chạy từ root repository bằng Python của môi trường automation:

```powershell
# Bộ production E2E mặc định, gồm features và 11 ca shared SaaS hiện tại.
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa

# Lọc trong bộ mặc định, vẫn chọn được test shared SaaS.
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- -k deep_link -q

# Chạy đích cụ thể; path từ root và node pytest vẫn được hỗ trợ.
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa -- automation_test/reviews/test_shared_saas.py -q

# Harness/collection regression; không mở API/browser hay ghi DB.
& automation_test/.venv/Scripts/python.exe -B -m unittest discover -s automation_test/harness_tests -q
```

`pytest.ini` là nguồn chọn bộ E2E mặc định. Runner chạy pytest từ automation_test với config này; explicit path được giữ để chạy riêng. Không chạy pytest trực tiếp vào ứng dụng đang deploy: runner kiểm tra frontend/rewrite/SSR và tạo backend/database QA riêng, dọn tài nguyên do nó tạo. Test backend dùng `docker compose exec -T backend python -m scripts.test_isolated`.

Các reviews/probe lịch sử khác chạy opt-in; không đưa toàn bộ thư mục reviews vào mặc định. Bài tải ba spa/backup-restore là `automation_test.run_shared_pilot`, tách khỏi browser E2E.

Đối chiếu yêu cầu → test, kết quả collection và các khoảng trống: [TEST_COVERAGE](../docs/TEST_COVERAGE.md). Số test collect hoặc số test PASS không phải line/branch coverage hay chứng nhận PWA/push trên thiết bị thật.
