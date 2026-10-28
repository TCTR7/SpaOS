# Đối chiếu yêu cầu và automation SpaOS

Ngày 28/10/2026. Phạm vi: các nhóm nghiệp vụ MVP trong PRD, P0–P6 shared SaaS và auto-migration. Đây là đối chiếu test hiện có với yêu cầu; không phải chứng nhận mọi tình huống đã có test hoặc số đo line/branch coverage. Tên ca dưới đây đã được kiểm tra tồn tại trong source. Có test không đồng nghĩa lượt chạy mới nhất của toàn bộ bản cuối đều PASS.

## Cách chạy mặc định

Từ root dự án:

```powershell
# Toàn bộ backend, gồm shared SaaS/migration/startup; DB tạm riêng.
docker compose exec -T backend python -m scripts.test_isolated -q --tb=short

# Production E2E mặc định: features + shared SaaS, không cần chỉ định file mới.
& automation_test/.venv/Scripts/python.exe -B -m automation_test.run_ui_qa

# Kiểm tra runner, không mở API/browser hoặc ghi DB.
& automation_test/.venv/Scripts/python.exe -B -m unittest discover -s automation_test/harness_tests -q
```

`automation_test/pytest.ini` là nguồn chọn E2E mặc định duy nhất: `features` và `reviews/test_shared_saas.py`. Runner chạy pytest với config này từ thư mục automation_test. Lệnh chỉ có option (ví dụ `-- -k deep_link`) vẫn dùng bộ mặc định; lệnh có path cụ thể chỉ chạy path đó. Các path `automation_test/...` từ root được chuyển thành đường dẫn tuyệt đối, kể cả node `::test_...`. Các review/probe lịch sử khác còn chạy riêng theo nhu cầu, không được tự coi đã tương thích shared SaaS.

Backend testpaths là `backend/tests`; bộ auto-migration nằm trong `test_startup.py`, đã thuộc mặc định. Test tải/restore riêng qua `automation_test.run_shared_pilot`, không lẫn vào E2E browser. Kiểm thử không được dùng DB ứng dụng, seed demo/credential vào DB thật hoặc nới JWT để tránh lỗi clock.

## Yêu cầu đã có test tự động

Mỗi mục là bằng chứng đại diện cho yêu cầu; các file tương ứng còn các ca lỗi/biên khác. Các giới hạn cần bổ sung nằm ở phần sau.

### CORE-01 — Đăng nhập, quyền và cô lập chi nhánh

`backend/tests/test_auth.py::test_rls_blocks_cross_tenant_and_no_context`; `backend/tests/test_auth.py::test_same_phone_in_two_tenants_and_isolation`.

### CORE-02 — CRUD dịch vụ, nhân viên, khách và thẻ

`backend/tests/test_sprint2_crud.py::test_services_crud_and_permissions`; `backend/tests/test_sprint2_crud.py::test_customers_and_packages_crud`.

### CORE-03 — Slots, buffer và giờ Việt Nam

`backend/tests/test_booking_concurrency.py::test_available_slots_rules`; `backend/tests/test_audit_regressions.py::test_buffer_includes_booking_on_following_day`.

### CORE-04 — Đặt lịch đồng thời và auto-assign

`backend/tests/test_booking_concurrency.py::test_concurrent_booking_same_staff_only_one_succeeds`; `backend/tests/test_booking_concurrency.py::test_concurrent_auto_assign_distributes_staff`.

### CORE-05 — Đặt/dùng thẻ, giữ buổi và hoàn thành idempotent

`backend/tests/test_booking_concurrency.py::test_concurrent_package_overbooking_blocked`; `backend/tests/test_booking_concurrency.py::test_package_booking_and_auto_deduct_on_completed`.

### CORE-06 — Batch nguyên tử và retry không tạo trùng

`backend/tests/test_manual_batches.py::test_second_row_failure_rolls_back_customer_package_bookings_and_audit`; `backend/tests/test_manual_batches.py::test_concurrent_same_request_replays_ids_and_checks_permissions`.

### CORE-07 — Thu tiền, hoàn tác, cạnh tranh và audit

`backend/tests/test_manual_payments.py::test_concurrent_receipts_same_key_and_overpayment`; `backend/tests/test_manual_payments.py::test_ledger_and_audit_append_only_and_rls`.

### CORE-08 — Báo cáo, tổng hợp và ranh giới ngày

`backend/tests/test_sprint4_reports_notifications.py::test_report_timezone_boundaries`; `backend/tests/test_branches.py::test_dashboard_sums_receipts_and_outstanding_without_double_charge`.

### CORE-09 — Hồ sơ/kỹ năng/ảnh nhân viên và tự phục vụ khách

`backend/tests/test_staff_profile.py::test_skills_filter_auto_assignment_and_available_slots`; `backend/tests/test_customer_self_service.py::test_my_packages_isolation_and_permissions`.

### CORE-10 — Thông báo bền vững và retry push (mock)

`backend/tests/test_role_experience.py::test_durable_event_recovers_after_failed_background_and_dedupes`; `backend/tests/test_role_experience.py::test_push_retry_survives_failure_without_duplicate_in_app`.

### CORE-11 — Khôi phục một lần, password/version và quyền hồ sơ

`backend/tests/test_role_experience.py::test_recovery_link_is_verified_single_use_branch_scoped_and_revokes_old_sessions`; `backend/tests/test_role_experience.py::test_shared_staff_account_updates_all_branches_and_revokes_tokens`.

### CORE-12 — Operator riêng, provision retry/rollback và version

`backend/tests/test_operator.py::test_owner_provision_retry_and_conflicts_rollback`; `automation_test/features/operator_portal/tests/test_operator_lifecycle_ui.py::test_version_reload_and_mismatch_states`.

### SAAS-01 — P0/P1: mapping rõ ràng và giữ ID dữ liệu cũ

`backend/tests/test_shared_migration.py::test_legacy_mapping_rehearsal_preserves_ids_and_is_repeatable`.

### SAAS-02 — P1: ranh giới spa/account/membership, FORCE RLS

`backend/tests/test_shared_saas.py::test_assignment_database_constraints_and_runtime_rls`; `backend/tests/test_shared_saas.py::test_workforce_cannot_assign_foreign_branch_or_escalate_staff`.

### SAAS-03 — P1/P4: directory và header SSR không lẫn spa

`backend/tests/test_shared_saas.py::test_brands_directory_and_owner_isolation`; `automation_test/reviews/test_shared_saas.py::test_scoped_sessions_and_public_directory_do_not_mix`.

### SAAS-04 — P2: provision nhận diện riêng và chủ tự cập nhật

`backend/tests/test_operator.py::test_production_provisions_separate_spa_without_claiming_legacy_data`; `automation_test/features/operator_portal/tests/test_operator_ui.py::test_operator_provisions_independent_brand_colors_and_owner_can_update`.

### SAAS-05 — P2: ảnh/branding rollback nguyên tử, slug ổn định

`backend/tests/test_shared_saas.py::test_spa_images_are_atomic_and_brand_patch_preserves_omitted_assets`.

### SAAS-06 — P2: quota, staff duy nhất và cạnh tranh tạo staff

`backend/tests/test_shared_saas.py::test_limits_and_staff_create_grants_are_atomic`; `backend/tests/test_shared_saas.py::test_tenth_staff_slot_is_serialized_and_phone_normalized`.

### SAAS-07 — P3: ngày phân công chi phối login, directory và slots

`backend/tests/test_shared_saas.py::test_assignment_day_changes_slots_and_login`; `automation_test/features/customer_regressions/tests/test_display_pagination.py::test_public_staff_follows_daily_workplace_and_returns_on_next_working_day`.

### SAAS-08 — P3: mẫu tuần, nghỉ/ngoại lệ và trở về ca tuần

`automation_test/reviews/test_shared_saas.py::test_week_editor_saves_branch_per_day_and_brand_settings`; `backend/tests/test_shared_saas.py::test_remove_daily_exception_restores_week_without_moving_existing_bookings`.

### SAAS-09 — P3: đổi ca/booking đồng thời, lịch xa và một nơi suốt ngày

`backend/tests/test_shared_saas.py::test_booking_schedule_race_never_leaves_wrong_workplace`; `backend/tests/test_shared_saas.py::test_weekly_edit_checks_far_future_bookings`; `backend/tests/test_shared_saas.py::test_completed_visit_keeps_one_workplace_for_the_whole_day`.

### SAAS-10 — P3: buffer giữa hai nhánh qua nửa đêm

`backend/tests/test_shared_saas.py::test_buffer_across_midnight_when_next_day_is_another_branch`.

### SAAS-11 — P3/P4: bàn giao/thu hồi và chặn request đang đợi

`backend/tests/test_shared_saas.py::test_transfer_requires_handover_and_revokes_old_token`; `backend/tests/test_shared_saas.py::test_queued_staff_write_rechecks_revocation_after_workforce_lock`; `backend/tests/test_shared_saas.py::test_revocation_preserves_newer_week_at_remaining_branch`.

### SAAS-12 — P3: tạm ngưng/mở lại nhánh và quota reactivation

`backend/tests/test_shared_saas.py::test_branch_pause_handover_scope_and_reactivation_limit`; `backend/tests/test_shared_saas.py::test_booking_and_branch_pause_are_serialized`; `automation_test/reviews/test_shared_saas.py::test_owner_pauses_and_reopens_branch_without_losing_brand`.

### SAAS-13 — P4: form/ghi đang chờ, nhiều tab và đổi phiên

`automation_test/features/customer_regressions/tests/test_branch_work_guard.py::test_other_tab_pending_write_blocks_branch_until_response`; `automation_test/features/customer_regressions/tests/test_branch_work_guard.py::test_switch_in_flight_does_not_replay_other_tab_write`.

### SAAS-14 — P4: thu hồi quyền tự mở nhánh còn quyền

`automation_test/reviews/test_shared_saas.py::test_revoked_staff_tab_automatically_opens_remaining_branch`.

### SAAS-15 — P5: manifest/worker/login canonical và scope brand

`automation_test/reviews/test_shared_saas.py::test_canonical_login_routes_brand_manifest_and_worker`; `automation_test/reviews/test_shared_saas.py::test_customer_route_preserves_brand_manifest`.

### SAAS-16 — P5: notification/deep link sau login/hết phiên và mất quyền

`automation_test/reviews/test_shared_saas.py::test_in_app_notification_keeps_spa_scope`; `automation_test/reviews/test_shared_saas.py::test_booking_deep_link_opens_verified_target_after_login`; `automation_test/reviews/test_shared_saas.py::test_booking_deep_link_without_membership_does_not_load_booking`.

### SAAS-17 — P5: kit bàn giao, cập nhật và recovery operator

`automation_test/features/operator_portal/tests/test_operator_lifecycle_ui.py::test_handover_update_recovery_and_concurrent_claim`.

### START-01 — Auto-migration: DB hiện hành bỏ qua, DB cũ nâng trước guard

`backend/tests/test_startup.py::test_current_revision_skips_upgrade_but_keeps_guard`; `backend/tests/test_startup.py::test_pending_revision_upgrades_before_guard`.

### START-02 — Auto-migration: lifespan DB trống/cũ, nhiều worker và ownership

`backend/tests/test_startup.py::test_uvicorn_lifespan_prepares_disposable_database_concurrently`; `backend/tests/test_startup.py::test_failed_automatic_migration_stops_api_without_leaking_child_output`.

## Bao phủ một phần và khoảng trống

- **GAP-01 — PWA native/push thật (gate bên ngoài):** browser test kiểm tra metadata/scope/deep link, push backend dùng mock. Chưa chứng nhận Android/iOS cài hai spa, mở lại app, icon, permission, push background và tap notification trên HTTPS. Cần thiết bị thật/staging.
- **GAP-02 — Qua nửa đêm khi form đang mở (cần thêm automation):** đã có test phân công ngày và buffer ngày kế tiếp. Chưa có E2E điều khiển đồng hồ trình duyệt qua 00:00 để khẳng định banner đổi ca nhưng draft/nhánh đang ghi giữ nguyên.
- **GAP-03 — Quota dữ liệu legacy vượt gói (cần thêm automation):** đã test tạo/grant/giới hạn nhân viên đồng thời và mở lại nhánh. Chưa có fixture legacy vượt hai nhánh/10 staff để xác minh vẫn đọc dữ liệu cũ và chỉ chặn tăng; chưa có đầy đủ tổ hợp reactivation STAFF đồng thời.
- **GAP-04 — Đăng nhập ưu tiên theo ngày (bao phủ một phần):** backend kiểm tra nơi làm hôm nay; E2E kiểm tra directory theo ngày và đổi nhánh. Chưa có một hành trình browser dùng đồng hồ kiểm soát, đăng xuất/đăng nhập ngày kế tiếp và khẳng định chi nhánh ưu tiên tự đổi, manual dropdown không thay phân công.
- **GAP-05 — Cutover trên bản sao dữ liệu thật (gate bên ngoài):** mapping/dry-run/rollback/retry đã diễn tập dữ liệu tổng hợp. Chưa thay bằng kiểm kê đối chiếu bản sao DB dev/production thực tế, các xung đột số điện thoại/lịch thực tế và diễn tập bảo trì toàn bộ nguồn ghi.
- **GAP-06 — Backup/vận hành (bao phủ một phần):** pilot QA đã backup/restore 31 bảng, RLS/policies/context. Chưa kiểm chứng restore roles/grants/secrets, backup ngoài máy chủ theo lịch/retention, cảnh báo và RPO/RTO trên cấu hình đích.
- **GAP-07 — Hiệu năng production (gate bên ngoài):** ba spa × 10 staff đã có bài tải ngắn; chưa là soak test nhiều ngày, ảnh/dữ liệu lịch sử đại diện, peak RAM/CPU hoặc giới hạn sức chứa/chi phí production.
- **GAP-08 — Hồi quy sạch của bản cuối (gate chất lượng):** các lượt trước có fixture JWT lỗi vì clock Docker; giữ nguyên kiểm tra. Cần một lượt backend/E2E đầy đủ trên môi trường clock ổn định sau mọi thay đổi, không cộng kết quả từng nhóm thành full PASS.
- **GAP-09 — Coverage dòng/nhánh (chưa đo):** hiện chưa bật công cụ coverage và chưa có ngưỡng đo đáng tin cậy. Số test collect/đạt và danh sách yêu cầu này không phải phần trăm code coverage.
- **GAP-10 — Review/probe cũ (ngoài bộ mặc định):** các script reviews ngoài shared SaaS là kiểm tra chuyên biệt/lịch sử. Chưa audit từng script theo kiến trúc mới; không đưa toàn bộ reviews vào mặc định vì có giả định/fixture cũ và các probe không phải regression ổn định.

Ưu tiên test tiếp theo: GAP-02/04 (ngày mới và draft), GAP-03 (grandfather/quota reactivation). Các gate thiết bị/hosting/dữ liệu thật vẫn cần môi trường tương ứng. Không mở rộng phạm vi sản phẩm thành các chức năng chưa được PO duyệt.

## Bằng chứng cho đợt gộp test mặc định

- Backend mặc định: **156 test cases được collect**, gồm shared SaaS/mapping và 13 ca startup; runner tạo/dọn DB QA tạm. Đây không phải lượt chạy 156 tests.
- E2E mặc định: **271 cases được collect**, trong đó **11 shared SaaS**, không trùng node và không lẫn backend/review probe lịch sử.
- Harness: **30/30 PASS (2.653s)**, gồm default CLI, option-only selection, explicit node từ root, collection thật và cleanup/exit code/isolation.
- Đã xác minh **31 nhóm yêu cầu / 61 tham chiếu test** tồn tại bằng AST; không import backend hoặc kết nối DB để kiểm tra tài liệu.
- Smoke production qua lệnh mặc định `-- -k canonical_login_routes_brand_manifest_and_worker`: **1/1 PASS (4.53s), 270 deselected**; build/TypeScript PASS, SSR/rewrite isolation PASS. Không chỉ định file shared SaaS; output xác nhận testpaths mặc định và 271 cases. Collection chỉ chứng minh các ca được chọn, không chạy fixture/API/browser và không phải kết quả nghiệp vụ PASS. Các kết quả chạy nghiệp vụ trước đây xem PROGRESS và SHARED_SAAS_IMPLEMENTATION_REPORT.
