# SpaOS dùng chung nhiều chủ spa — tổng hợp và kịch bản sử dụng

Ngày: 28/10/2026.

**Trạng thái:** PO duyệt toàn bộ P0–P6 ngày 28/10/2026; code shared SaaS đang kiểm chứng trên QA riêng. Xem [kế hoạch](SHARED_SAAS_IMPLEMENTATION_PLAN.md), [thiết kế kỹ thuật](SHARED_SAAS_TECHNICAL_DESIGN.md), [runbook](SHARED_SAAS_MIGRATION_RUNBOOK.md) và PROGRESS để phân biệt phần đã kiểm chứng với gate native PWA/cutover. Chưa đổi database ứng dụng hoặc deploy pilot.

## 1. Mục tiêu và các lựa chọn đã trao đổi

- Khách hàng mục tiêu: spa nhỏ, thường dưới 10 nhân viên. Sản phẩm gọn, thao tác nhanh, ưu tiên PWA.
- Gói thử nghiệm được PO đồng ý để đưa vào kế hoạch: 10 USD/tháng cho mỗi chủ/thương hiệu, tối đa hai chi nhánh và 10 nhân viên duy nhất. Chưa công bố hạn mức dung lượng trước khi đo; chưa triển khai thu phí tự động.
- Hướng mới: một hệ thống dùng chung phục vụ nhiều chủ spa. Mỗi chủ có một không gian thương hiệu và dữ liệu riêng, có thể có nhiều chi nhánh.
- Một codebase và quy trình cập nhật phục vụ các chủ. Thêm một chủ không mặc định tạo thêm nguyên bộ frontend/backend/database trả phí riêng.
- Mỗi spa có tên, logo/avatar, màu, ảnh và thông tin liên hệ riêng. Người dùng chỉ thấy không gian spa liên quan đến mình, không thấy danh bạ các chủ spa khác.
- Mặc định dùng địa chỉ HTTPS miễn phí do nhà triển khai cấp. Mỗi spa có đường dẫn riêng theo tên; tên miền riêng chỉ tính khi chủ yêu cầu.
- Operator tạo spa và tài khoản chủ cùng cấu hình nhận diện. Chủ tạo chi nhánh, nhân viên và quyền làm việc. Quan hệ này được lưu ngay khi tạo/phân công.
- Nhân viên có quyền ở một hoặc nhiều chi nhánh của cùng chủ, nhưng mỗi ngày chỉ làm tại một chi nhánh theo giờ Việt Nam. Có một chi nhánh thì vào thẳng; có nhiều thì dùng dropdown theo quyền, giữ vai trò STAFF. Dropdown không thay phân công nhận lịch.
- Việc chuyển toàn bộ FastAPI sang Next.js ban đầu được nêu để giảm công vận hành. Chưa có quyết định triển khai chuyển framework. Hướng đề xuất hiện tại là tận dụng FastAPI + Next.js + PostgreSQL, ưu tiên thay đổi mô hình chia sẻ hạ tầng trước.
- Railway, Render và VPS + Coolify đã được bàn luận. Chưa chọn nhà cung cấp hoặc mua gói. Managed giúp giảm việc quản trị máy chủ; VPS cần tự chịu trách nhiệm vận hành nhiều hơn.

### Chi phí cần hiểu đúng

Con số khoảng 20 USD/tháng đã trao đổi là ví dụ thuê hai web service nhỏ và một PostgreSQL trả phí trên Render, chưa gồm lưu trữ và các khoản phát sinh. Không phải kết quả đo tài nguyên SpaOS, không phải báo giá cuối cùng cho hệ thống dùng chung.

Nếu có ba chủ trả 10 USD thì doanh thu là 30 USD. Giả sử hạ tầng là 20 USD thì còn 10 USD trước phí thanh toán, hỗ trợ, backup, thuế và các chi phí khác. Chưa có căn cứ cam kết ba chủ là có lãi hoặc cấu hình đó đủ tải. Cần đo khi triển khai thử và theo dõi chi phí trên tổng số chủ hoạt động.

Nguồn giá để kiểm tra lại khi mua: [Railway](https://railway.com/pricing), [Render](https://render.com/pricing). Gói Vercel Hobby có giới hạn sử dụng cá nhân/phi thương mại; không lấy gói này làm giả định chi phí production của sản phẩm bán cho spa: [điều kiện Hobby](https://vercel.com/docs/plans/hobby).

## 2. Hiện trạng cần phân biệt với hướng mới

Theo MULTI_BRANCH_STRATEGY và API_CONTRACT hiện hành:

- Kiến trúc đang lưu là một deployment riêng cho mỗi chủ spa; nhiều chi nhánh trong deployment đó. Màu thương hiệu có phần cấu hình singleton cấp deployment.
- Đã có danh tính đăng nhập chung, branch_memberships, đăng nhập quản trị không cần slug, API liệt kê/chuyển chi nhánh và dashboard tổng hợp theo quyền.
- Đã có POST /branches/{branch_id}/staff-access để cấp nhân viên ở nguồn sang chi nhánh đích cùng danh tính đăng nhập. Vì vậy, phát biểu trước đó rằng cần đổi toàn bộ backend từ quan hệ một chi nhánh sang nhiều chi nhánh là chưa chính xác. Cần tận dụng cơ chế này, rà giao diện hiện tại và bổ sung phần còn thiếu.
- Hồ sơ nhân viên theo chi nhánh vẫn có thể là các bản ghi users khác nhau cùng liên kết một tài khoản. Không được coi các staff_id khác nhau là những người khác nhau khi kiểm tra trùng lịch liên chi nhánh.
- Khách, thẻ, dịch vụ, giá, thu tiền và dữ liệu nghiệp vụ vẫn theo chi nhánh. Được cấp thêm chi nhánh không làm các dữ liệu này tự dùng chung.
- Native PWA và Web Push trên thiết bị thật còn các mục nghiệm thu mở. Các lượt build/E2E đã ghi chỉ chứng minh phạm vi tương ứng, không chứng minh mô hình nhiều chủ dùng chung đã hoạt động.

Thay đổi lớn sắp tới là thêm ranh giới **chủ spa/thương hiệu** bên trên chi nhánh, chuyển cấu hình cấp deployment phù hợp xuống cấp thương hiệu và sửa mọi đường truy cập đang giả định database chỉ có một chủ.

## 3. Mô hình sử dụng dự kiến

Một hệ thống SpaOS có nhiều không gian spa. Mỗi không gian thuộc một chủ, có nhận diện riêng và một hoặc nhiều chi nhánh. Mỗi chi nhánh có dữ liệu nghiệp vụ riêng.

- **Operator:** cấp và hỗ trợ tài khoản chủ/không gian spa qua cổng riêng. Không mặc nhiên có quyền đọc hồ sơ khách hoặc tài chính của tất cả spa.
- **Chủ spa:** quản lý thương hiệu, chi nhánh và nhân viên thuộc phạm vi của mình; có thể xem tổng hợp các chi nhánh được cấp quyền.
- **Nhân viên:** một danh tính đăng nhập, có hồ sơ/quyền tại một hoặc nhiều chi nhánh của cùng chủ; chỉ làm các thao tác STAFF đã được cho phép.
- **Khách hàng:** vào qua link/QR của spa, chọn chi nhánh khi cần và sử dụng hồ sơ/thẻ trong phạm vi hiện hành. Chưa mở hồ sơ hoặc thẻ dùng xuyên chi nhánh.

Bốn thông tin tách biệt:

1. Spa sở hữu tài khoản vận hành.
2. Các chi nhánh tài khoản được phép làm việc.
3. Chi nhánh được phân công làm việc theo từng ngày, có mẫu tuần và ngoại lệ ngày.
4. Chi nhánh đang mở trong phiên và lựa chọn mặc định/gần nhất còn hợp lệ; đăng nhập STAFF ưu tiên chi nhánh được phân công hôm nay.

Việc chuyển chi nhánh là chuyển nơi làm việc trong phiên. Việc thêm/thu hồi quyền là thay đổi phân công. Không dùng thao tác thứ nhất để tự cấp quyền của thao tác thứ hai.

## 4. Ví dụ xuyên suốt: Spa Sen và Mai Beauty

Toàn bộ tên, lịch và nhân vật dưới đây là ví dụ minh họa, không phải dữ liệu thật cần tạo.

- Chị Hương là chủ **Spa Sen**, có chi nhánh **Quận 1** và **Quận 7**. Thương hiệu màu xanh, logo hoa sen.
- Chị Mai là chủ **Mai Beauty**, có chi nhánh **Bình Thạnh**. Thương hiệu màu hồng, logo riêng.
- **Lan** làm ở cả Quận 1 và Quận 7 của Spa Sen.
- **Thảo** chỉ làm ở Quận 1 của Spa Sen.
- **Linh** là khách đặt lịch tại Spa Sen Quận 1.

### Bước 1 — Operator tạo Spa Sen

Operator vào cổng vận hành và chọn tạo spa/chủ spa. Nhập tên Spa Sen, thông tin tài khoản chị Hương, tên chi nhánh đầu là Quận 1 và nhận diện: logo, màu, ảnh/thông tin liên hệ phù hợp.

Sau khi lưu thành công:

- Có một không gian Spa Sen và chi nhánh Quận 1 thuộc không gian đó.
- Tài khoản chị Hương có quyền chủ đối với Spa Sen và quyền tại Quận 1.
- Có link/QR theo tên spa để bàn giao. Ví dụ nếu deployment có địa chỉ spaos-demo.onrender.com thì đường dẫn dự kiến là /s/spa-sen/.
- Có lối đăng nhập quản lý nằm trong phạm vi Spa Sen, ví dụ /s/spa-sen/admin/login. Đây là URL đề xuất, chưa phải route đã triển khai.
- Thao tác phải nguyên tử và chống tạo trùng khi người dùng bấm lại/retry. Không để trạng thái có tài khoản nhưng không có spa hoặc thiếu quyền chủ.

Tên miền ví dụ không được coi là địa chỉ đã đăng ký. Hệ thống sinh link dựa trên địa chỉ công khai được cấu hình khi deploy. Slug trùng tên được thêm hậu tố; đổi tên hiển thị không tự làm hỏng link và QR đã phát.

### Bước 2 — Operator tạo Mai Beauty

Operator tạo chị Mai và Mai Beauty tương tự. Link dự kiến là /s/mai-beauty/; cấu hình màu/logo được lưu riêng.

Chị Mai đăng nhập chỉ thấy Mai Beauty và Bình Thạnh. Chị Hương không thấy Mai Beauty trong dropdown, báo cáo hoặc danh sách chi nhánh công khai của Spa Sen. Hai spa sử dụng cùng phiên bản phần mềm nhưng tách quyền và dữ liệu.

### Bước 3 — Chị Hương đăng nhập và tạo chi nhánh

Chị Hương mở link quản lý được bàn giao, thấy logo/màu Spa Sen trước đăng nhập. Nhập SĐT và mật khẩu; hệ thống xác minh tài khoản, quyền chủ và mở Quận 1 vì đây là chi nhánh duy nhất.

Chị chọn tạo chi nhánh Quận 7. Hệ thống tự gắn Quận 7 vào Spa Sen và cấp quyền phù hợp cho chị Hương. Không phải chọn lại tên chủ hoặc tạo tài khoản chủ mới.

Dropdown của chị có Quận 1, Quận 7 và chế độ tổng hợp theo quyền. Tổng hợp là chế độ xem; thao tác tạo lịch/thu tiền luôn xác định chi nhánh cụ thể. Chi nhánh mới cần thiết lập dịch vụ, nhân sự và giờ làm; không tự sao chép dữ liệu nghiệp vụ của Quận 1.

PO đồng ý chủ tự cập nhật nhận diện spa trong Cài đặt, operator hỗ trợ khi cần. Thay đổi ở cấp Spa Sen áp dụng cho không gian của Spa Sen, không làm đổi màu Mai Beauty. Cần bổ sung quyền sửa này vì màu hiện tại do operator quản lý ở cấp deployment.

### Bước 4 — Chị Hương tạo nhân viên

Tại màn hình Nhân viên, chị tạo Lan và chọn hai ô Quận 1, Quận 7; chọn Quận 1 là chi nhánh mở mặc định. Khi tạo Thảo, chị chỉ chọn Quận 1. Chi nhánh đang quản lý được chọn sẵn để giảm thao tác.

Spa sở hữu được suy ra từ quyền đã xác minh của chị Hương; form không cho chọn spa của người khác. Mỗi nhân viên dùng một tài khoản đăng nhập trong Spa Sen. Lan có quyền STAFF ở hai chi nhánh; việc đánh dấu nhiều chi nhánh không làm Lan thành ADMIN.

Chị phân Lan thứ Hai làm Quận 1 từ 08:00–17:00, thứ Ba làm Quận 7 từ 09:00–18:00, thứ Tư nghỉ. Lịch có thể lặp theo tuần và sửa riêng một ngày. Mỗi ngày chỉ một chi nhánh, không chia sáng/chiều sang hai nơi. Ca và kỹ năng phải phù hợp trước khi Lan xuất hiện trong danh sách nhận lịch; được cấp quyền không đồng nghĩa được nhận lịch ở mọi nơi/ngày.

### Bước 5 — Nhân viên mở app và làm việc

Lan mở lối vào Spa Sen và đăng nhập bằng SĐT/mật khẩu:

- Nếu hôm nay thứ Hai, mở Quận 1 theo phân công; đăng nhập thứ Ba ưu tiên Quận 7. Nếu hôm nay không có ca, dùng chi nhánh mặc định còn quyền theo kế hoạch và hiển thị rõ không có ca.
- Header hiển thị thương hiệu Spa Sen và chi nhánh Quận 1.
- Dropdown chỉ có Quận 1 và Quận 7, không có Mai Beauty hoặc chế độ tổng hợp của chủ.
- Dữ liệu lịch/khách/thông báo tuân theo quyền STAFF tại chi nhánh. Được xem lịch được giao không tự mở toàn bộ hồ sơ sức khỏe, thẻ hay thu tiền.

Lan chọn Quận 7. Backend kiểm tra quyền còn hiệu lực rồi xác lập phạm vi mới. UI hủy request cũ, xử lý bản nháp đang mở và tải dữ liệu Quận 7; không ghép dữ liệu hai chi nhánh. Chi nhánh hiển thị phải khớp chi nhánh nhận thao tác ghi.

Lần đăng nhập sau ưu tiên phân công hôm nay; khi không có ca mới dùng mặc định/lựa chọn hợp lệ. Dropdown cho Lan xem công việc tại chi nhánh được cấp nhưng không đổi phân công nhận lịch. Không còn quyền thì hiển thị liên hệ chủ spa, không tự chuyển sang spa khác. Qua ngày mới không tự chuyển chi nhánh giữa form đang nhập.

Thảo đăng nhập thì vào thẳng Quận 1 và không cần dropdown. Cả Lan và Thảo không cần nhập mã spa/chi nhánh.

### Bước 6 — Linh cài PWA và đặt lịch

Linh quét QR của Spa Sen. Trang hiển thị tên/logo/màu Spa Sen và chỉ các chi nhánh của Spa Sen. Link QR riêng Quận 1 có thể đưa thẳng vào chi nhánh đó.

Linh chọn Quận 1, xem dịch vụ và đặt lịch theo luồng đang có. Nếu cần đăng nhập, giữ lựa chọn hợp lệ để Linh tiếp tục sau đăng nhập. Thẻ tại Quận 1 tiếp tục chỉ sử dụng tại Quận 1.

Khi Linh cài PWA từ không gian Spa Sen, ứng dụng dự kiến dùng tên/icon Spa Sen và mở lại lối vào Spa Sen. Hết phiên đăng nhập vẫn hiển thị nhận diện Spa Sen. Chi nhánh nhớ lần trước chỉ được khôi phục nếu còn hoạt động; chuyển chi nhánh phải kiểm tra lại phiên khách theo phạm vi hiện hành, không mặc nhiên dùng token của chi nhánh trước.

Thông báo lịch dẫn về đúng spa, chi nhánh và lịch; backend kiểm tra người nhận còn quyền trước khi trả nội dung. Người dùng chưa đăng nhập qua trang chung / chưa có ngữ cảnh thì hệ thống không thể tự biết họ thuộc spa nào; dùng link/QR hoặc đăng nhập để xác định.

### Bước 7 — Đặt đúng chi nhánh theo ngày và chặn xung đột

Thứ Hai Lan được phân công Quận 1. Khách chọn Quận 1/thứ Hai thấy Lan nếu còn giờ trống; khách chọn Quận 7 cùng ngày không thấy Lan trong danh sách có thể đặt. Thứ Ba Lan xuất hiện tại Quận 7 theo phân công.

Nếu gọi API trực tiếp để đặt Lan sai chi nhánh/ngày thì server vẫn chặn. Nếu chủ đổi phân công thứ Hai sang Quận 7 trong lúc khách đặt Lan tại Quận 1, hai thao tác phải được phối hợp giao dịch: lịch đã nhận thì đổi phân công bị chặn đến khi xử lý, hoặc phân công đổi trước thì booking sai nơi bị từ chối. Vẫn giữ khóa chống trùng giờ và buffer trong chi nhánh.

Đây là yêu cầu mở rộng cần thiết kế/kiểm chứng, không khẳng định engine hiện tại đã làm được. Không xây thời gian di chuyển giữa chi nhánh. Phải nhận diện cùng người qua account chung để bảo vệ phân công/booking, không chỉ khóa hai staff_id riêng biệt.

### Bước 8 — Cấp thêm và điều chuyển nhân viên

**Cấp thêm:** Thảo đang ở Quận 1. Chị Hương chọn thêm Quận 7. Thảo giữ quyền Quận 1, được thêm quyền Quận 7 và thấy dropdown sau khi phiên đồng bộ. Không cần tạo mật khẩu thứ hai.

**Điều chuyển:** Chị muốn Lan chỉ làm tại Quận 7 từ nay. Giao diện thể hiện bỏ quyền Quận 1 và giữ Quận 7. Quy tắc PO đồng ý: chặn hoàn tất đến khi xử lý lịch tương lai/đang phục vụ và khách đang phụ trách tại Quận 1; không tự hủy/dời lịch. Khi xử lý xong, thu hồi quyền và cập nhật phân công tương lai liên quan có hiệu lực ngay; lịch sử vẫn giữ nguyên.

Sau khi điều chuyển có hiệu lực:

- Backend chặn ngay các thao tác mới bằng quyền Quận 1 đã thu hồi, kể cả tab cũ.
- Khi nhận cập nhật hoặc kiểm tra phiên tiếp theo, app chuyển về Quận 7 nếu đó là chi nhánh duy nhất còn quyền. Không cam kết đổi tức thời trên thiết bị đang offline.
- Form ở Quận 1 không được âm thầm gửi sang Quận 7; chặn gửi theo quyền cũ và giải thích cho nhân viên.
- Lịch sử làm việc/thu tiền ở Quận 1 giữ nguyên. Không chuyển khách, thẻ, lịch hay bút toán sang Quận 7 chỉ vì điều chuyển nhân viên.
- Thông báo và link cũ không vượt qua kiểm tra quyền đã thu hồi.

### Bước 9 — Chủ xem báo cáo, operator phục vụ thêm khách

Chị Hương xem tổng Spa Sen từ các chi nhánh được cấp quyền. Chị Mai chỉ xem Mai Beauty. Quyền quản lý nhiều chi nhánh không mở dữ liệu của chủ khác.

Operator thêm chủ spa tiếp theo qua cùng luồng tạo không gian, nhận diện và tài khoản. Hệ thống dùng chung tài nguyên triển khai; khi tải tăng mới đánh giá nâng tài nguyên dựa trên số đo. Subscription thu phí SaaS của operator và sổ thu tiền khách spa là hai nghiệp vụ khác nhau; phiên này chưa thiết kế cổng thu phí SaaS tự động.

## 5. Link, đăng nhập và PWA

- URL thương hiệu dự kiến: /s/{spa_slug}/. Các trang đăng nhập/quản lý/khách cần tổ chức để nằm trong scope PWA tương ứng. Không coi các route ví dụ là contract đã triển khai.
- Đăng nhập từ lối chung có thể tự điều hướng sau khi xác minh được một danh tính vận hành duy nhất. Trước xác thực không công khai danh sách spa liên quan đến một SĐT.
- SĐT tài khoản vận hành duy nhất toàn nền tảng, mỗi danh tính thuộc một chủ trong MVP. Xung đột dữ liệu cũ cần đối chiếu, không chọn spa đầu tiên hoặc tự ghép tài khoản. Khách vẫn có thể dùng cùng SĐT ở các phạm vi riêng.
- Một PWA theo thương hiệu spa, giao diện sau đăng nhập theo vai trò; operator có cổng riêng. Manifest có id ổn định, name/icons, start_url và scope phù hợp; đối chiếu tương thích với các lối cài PWA cũ.
- Nhiều PWA trên cùng origin không được trình duyệt coi là các vùng bảo mật hoàn toàn độc lập. Phải xử lý storage/cache/service worker/push có phạm vi và nghiệm thu Android/iOS, nhất là khi một máy cài hai spa.
- Tên/logo thay đổi trong giao diện có thể cập nhật sớm hơn icon/tên đã cài do trình duyệt quản lý; cần hướng dẫn cập nhật nếu cần.
- Địa chỉ miễn phí là địa chỉ của nhà cung cấp, tên spa nằm ở đường dẫn. Không tự sinh quyền sở hữu tên miền mới chỉ từ tên spa.
- Chuyển sang tên miền riêng hoặc đổi nhà cung cấp có thể đổi origin và ảnh hưởng PWA đã cài, phiên và push. Cần kế hoạch chuyển link/cài lại; redirect đơn thuần không bảo đảm giữ nguyên danh tính PWA.

Nguồn tham khảo: [Manifest](https://web.dev/learn/pwa/web-app-manifest), [nhiều PWA cùng tên miền](https://web.dev/articles/building-multiple-pwas-on-the-same-domain), [địa chỉ Render](https://render.com/docs/web-services).

## 6. Những thay đổi sản phẩm và kỹ thuật dự kiến

1. Thêm phạm vi chủ spa/thương hiệu và quan hệ sở hữu chi nhánh. Giữ tenant_id và ID nghiệp vụ cũ; xây quy trình đối chiếu/mapping dữ liệu thay vì tự gộp.
2. Chuyển các cấu hình hiện đang chung toàn deployment sang đúng phạm vi spa: nhận diện, danh sách chi nhánh công khai, onboarding và các chức năng liên quan.
3. Operator tạo và hỗ trợ nhiều không gian spa trong cùng hệ thống, vẫn dùng danh tính/JWT riêng; không bypass RLS để thao tác mọi dữ liệu.
4. Hoàn thiện form tạo/sửa nhân viên chọn nhiều chi nhánh, chi nhánh mặc định và hai hành động cấp thêm/điều chuyển; tận dụng login_accounts và branch_memberships hiện có sau khi bổ sung phạm vi chủ.
5. Hoàn thiện tự điều hướng và dropdown theo quyền, kiểm tra phiên khi quyền thay đổi, xử lý nhiều tab, bản nháp và request trả về muộn.
6. Phân công tuần/ngày theo danh tính nhân viên chung, một ngày một chi nhánh; booking kiểm tra ca/kỹ năng và tranh chấp với thay đổi phân công/thu hồi quyền. Không trả chi tiết khách chi nhánh khác để báo bận.
7. Cập nhật đường dẫn thương hiệu, manifest, bộ QR/bàn giao, notification deep link và tương thích URL cũ.
8. Giữ filter và RLS của dữ liệu chi nhánh; bổ sung kiểm soát cấp chủ cho dữ liệu mới. Dashboard chỉ tổng hợp phạm vi đã xác minh. Không mở policy toàn cục để tiện triển khai.

## 7. Quyết định sản phẩm đã được PO đồng ý

PO đã đồng ý các đề xuất sau, với điều chỉnh phân công theo ngày thay cho thời gian di chuyển. Kế hoạch kỹ thuật vẫn chờ duyệt tại SHARED_SAAS_IMPLEMENTATION_PLAN.md.

- **Danh tính:** SĐT vận hành duy nhất toàn hệ thống; một danh tính thuộc một chủ trong MVP; khách vẫn riêng theo phạm vi hiện hành. Không tự gộp dữ liệu cũ.
- **Điều chuyển:** chặn bỏ quyền cho đến khi xử lý lịch còn tồn và khách cần bàn giao; hiệu lực ngay sau hoàn tất, không tự hủy/dời lịch.
- **Phân công:** mỗi ngày một chi nhánh hoặc nghỉ, mẫu tuần và sửa riêng ngày, giờ Việt Nam. Không xây cấu hình thời gian di chuyển. STAFF login ưu tiên phân công hôm nay; dropdown không sửa phân công.
- **Nhận diện/PWA:** chủ được chỉnh nhận diện của spa mình; một PWA thương hiệu với chức năng theo vai trò, operator riêng. Native PWA và tương thích cài cũ cần kiểm chứng.
- **Gói thử nghiệm:** 10 USD/tháng, một chủ/thương hiệu, hai chi nhánh, 10 nhân viên duy nhất, nghiệp vụ hiện có và nhận diện/link/QR. Không bao gồm tên miền/SMS trả phí; không tự thu phí định kỳ hoặc khóa dữ liệu vì vượt gói. Hạn mức GB xác định sau đo.
- **Vận hành còn lại:** chọn nhà cung cấp, đo tải/chi phí và xác định dung lượng; không cam kết cấu hình đủ tải hoặc có lãi khi chưa có số đo.

## 8. Trình tự triển khai đề xuất và tiêu chí nghiệm thu

### Trình tự

1. Thiết kế kỹ thuật theo quy tắc đã đồng ý; lập mapping chủ/chi nhánh/tài khoản/lịch cũ và kế hoạch rollback.
2. Làm ranh giới chủ, RLS và operator provisioning trên DB QA riêng; kiểm chứng hai chủ độc lập trước khi thêm UX.
3. Làm branding/link theo spa và tự điều hướng sau đăng nhập; không đưa dữ liệu chưa xác minh vào trang chung.
4. Hoàn thiện gán nhiều chi nhánh, phân công một nơi/ngày, thu hồi quyền và khóa đồng bộ booking/phân công.
5. Làm PWA/QR/push, tương thích link cũ và kiểm chứng thiết bị thật.
6. Chạy regression, đo tải/chi phí, backup/restore và triển khai pilot có theo dõi.

### Các ca phải chứng minh

- Hai spa khác màu/logo/dữ liệu; API, public directory, dashboard, ảnh và thông báo không lẫn chủ.
- Chủ mới được tạo nguyên tử, retry không tạo trùng; recovery và sửa tài khoản đúng chủ, không tiếp quản tài khoản legacy tự động.
- Nhân viên một chi nhánh vào thẳng; nhiều chi nhánh có đúng dropdown, không tăng quyền; mọi thao tác ghi khớp nhãn chi nhánh đang hiển thị.
- Thu hồi quyền trong lúc còn tab/phiên cũ hoặc form đang mở không cho ghi tiếp bằng quyền cũ và không gửi nhầm sang chi nhánh mới.
- Khách chỉ thấy KTV có phân công phù hợp nơi/ngày; API chặn lịch sai nơi, hai request booking/đổi ca đồng thời không tạo lịch trái phân công; thay quyền/ca không làm lịch mồ côi. Không phân cùng người hai nơi trong một ngày.
- Hồ sơ/thẻ/giá/thu tiền giữ phạm vi chi nhánh; trừ buổi, chống ghi lặp, audit và timezone không hồi quy.
- PWA hết phiên vẫn giữ thương hiệu; cài hai spa trên cùng thiết bị, mở lại, đổi tài khoản, nhận push và mở link được kiểm chứng Android/iOS thật.
- Kiểm thử backend dùng python -m scripts.test_isolated; E2E dùng QA riêng, không seed/reset dữ liệu hoặc credentials người dùng.

Tài liệu này mô tả đích đến và tiêu chí thực hiện. API_CONTRACT vẫn là nguồn mô tả API hiện có cho đến khi từng thay đổi được triển khai và kiểm chứng.


## Ghi chú phần đã triển khai (28/10/2026)

Luồng mô tả trong tài liệu đã có mã nguồn shared SaaS và đang nghiệm thu QA. Thêm ca hôm nay tự cập nhật khi qua ngày mà không chuyển form; tạm ngưng nhánh yêu cầu xử lý lịch/khách và thực hiện từ một nhánh hoạt động khác, mở lại kiểm tra gói rồi phân công ca. Ngay cả sau COMPLETED/NO_SHOW, không chuyển nơi làm của ngày đã phát sinh buổi hẹn. Kết quả đã kiểm chứng và các gate native/clock/hosting ghi tại [báo cáo](SHARED_SAAS_IMPLEMENTATION_REPORT.md); chưa cutover DB ứng dụng.
