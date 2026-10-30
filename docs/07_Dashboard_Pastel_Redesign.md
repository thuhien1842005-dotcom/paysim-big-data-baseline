# GHI CHÚ TRIỂN KHAI GIAO DIỆN PAYSIM WORKSPACE

## 1. Quyết định thiết kế

- Sử dụng một giao diện Workspace thống nhất. Gỡ bỏ `view_operations.py`, `view_report.py`, `view_studio.py` cùng bộ chọn `AFTER` trong tệp khởi chạy.
- Tuân theo thiết kế Framer tham chiếu do người dùng cung cấp: kết hợp phông chữ không chân và có chân (sans/serif), thẻ kính mờ (translucent glass cards), viền mảnh, khoảng cách thoáng và hình minh họa dải kính 3D.
- Áp dụng bảng màu hồng pastel và kem đã chọn, bộ biểu tượng cục bộ và các thông số chuyển động nguyên bản từ mẫu tham chiếu. Không cần bất kỳ dịch vụ animation trả phí nào để chạy dashboard.
- Giữ nguyên 4 nhóm nội dung gốc và nguồn dữ liệu snapshot, chỉ áp dụng bộ lọc ở tầng trình bày (presentation layer).
- Hiển thị thanh điều hướng, nhãn, phần giải thích, trạng thái rỗng, bộ lọc, chi tiết giao dịch và nội dung hero của Workspace theo thiết kế mới, trong khi các mã định danh nội bộ và giá trị lưu trữ từ pipeline vẫn giữ nguyên ý nghĩa ban đầu.

## 2. Ranh giới dữ liệu và bảo toàn công thức

Các truy vấn cơ sở dữ liệu và công thức tính toán trong [`dashboard_core.py`](../dashboard/dashboard_core.py), mã nguồn Spark ([`spark/pipeline.py`](../spark/pipeline.py)), trình phát lại ([`replayer/app.py`](../replayer/app.py)), mô hình MLlib và cấu hình pipeline được **giữ nguyên hoàn toàn**. Thay đổi duy nhất trong phần lõi là dịch thông báo trạng thái sẵn sàng của pipeline. Mười nhóm chỉ số (10 metric tracks) tái sử dụng đúng các biểu thức gốc, và các bài kiểm thử hồi quy (regression tests) đối chiếu kết quả hiển thị khớp với bộ render ban đầu. Phần đánh giá mô hình tiếp tục sử dụng hàm `detector_metrics()`.

Bộ lọc giao dịch và cảnh báo hoạt động trên các bản ghi đã nạp sẵn trong snapshot. Các chỉ số KPI toàn đợt chạy (6 run KPIs) và các biểu đồ tổng hợp không bị thay đổi theo danh sách lọc cục bộ. Cảnh báo từ mô hình vẫn là kết quả dự đoán (`predictedFraud`) và được phân biệt rõ với nhãn thực tế (`actualFraud`). Việc lọc theo khoảng điểm rủi ro (`risk score`) không làm thay đổi ngưỡng phát hiện (`threshold`) hay chạy lại quá trình suy luận (inference).

## 3. Tương tác và hiệu ứng chuyển động

- Hỗ trợ lọc theo loại giao dịch, số tiền, điểm rủi ro, kết quả dự đoán, `Event ID`, thời gian UTC và thứ tự hiển thị.
- Hỗ trợ đặt lại (reset) bộ lọc, chọn một dòng hoặc `Event ID`, xem chi tiết giao dịch và xuất các bản ghi đang hiển thị ra tệp CSV có gắn UTF-8 BOM.
- Giữ nguyên lựa chọn gắn với `Event ID` khi thứ tự hoặc độ dài snapshot thay đổi qua các lần làm mới. Tự động xóa lựa chọn kèm thông báo giải thích khi bản ghi đó rời khỏi tập dữ liệu hiển thị.
- Bổ sung phản hồi khi di chuột (hover), trạng thái đang chọn, các mục mở rộng (expandable sections) và thông báo một lần khi có bản ghi mới xuất hiện. Tránh việc chạy lại animation của toàn bộ trang sau mỗi chu kỳ làm mới dữ liệu 2 giây.
- Nhúng trực tiếp ảnh PNG dải kính Framer gốc vào `dashboard/assets/fluid-glass.png` và hiển thị qua [`hero.html`](../dashboard/assets/hero.html). Dữ liệu byte của ảnh PNG không đổi; thuộc tính CSS `hue-rotate(105deg)` chuyển màu ảnh gốc sang tông hồng chủ đạo.
- Chuyển nguyên bản hiệu ứng chuyển động `fluidFloat` chu kỳ 10 giây, quầng sáng `fluidGlowMotion` chu kỳ 8 giây và 7 thanh sóng âm chu kỳ 0.95 giây với độ trễ lệch pha. Thẻ kính thông tin và nhãn trạng thái giữ nguyên trạng thái tĩnh như module gốc. Các nhãn danh mục trên thẻ mô tả các góc nhìn của không gian phân tích thay vì giả lập tiến trình xử lý pipeline.
- Gắn iframe trang trí bên ngoài fragment làm mới dữ liệu. Tự động tạm dừng chuyển động khi cuộn khuất hoặc ẩn tab, tôn trọng thiết lập `prefers-reduced-motion` và dành sẵn không gian hiển thị trên thiết bị di động phía trên thanh điều hướng.
- Đóng gói toàn bộ tài nguyên runtime vào trong Docker image. Bản triển khai cuối cùng chỉ sử dụng PNG và CSS thuần, không cần Three.js, WebGL, Node.js hay bước build npm.

Liên kết tham chiếu: [trang Framer đã xuất bản](https://little-assistant-921809.framer.app/), [module do người dùng cung cấp](https://framer.com/m/NovaAIWorkspace-we4woi.js@XOdWXg6mBixFPNlr1Zps) và [ảnh minh họa dải kính gốc](https://framerusercontent.com/images/dcjF6157kwSMfrYalKVakR6JKiI.png?width=1536&height=1024). Xem mục 5 của [hướng dẫn cải tiến dashboard](05_Huong_Dan_Cai_Tien_Dashboard.md) để biết chi tiết các thông số chuyển động.

## 4. Kiểm chứng và vận hành

Tài liệu [hướng dẫn cải tiến dashboard](05_Huong_Dan_Cai_Tien_Dashboard.md) trình bày đầy đủ cách khởi chạy, kiểm thử và khôi phục. Mốc checkpoint cục bộ trước khi thiết kế lại là `03ac9a5`; nhánh làm việc là `dashboard/pastel-framer-redesign`. Để build và khởi chạy lại riêng container dashboard:

```powershell
docker compose -f docker-compose.yml up -d --build --no-deps streamlit
```

Giữ nguyên cờ cấu hình `docker-compose.low-memory.yml` nếu hệ thống đang chạy ở chế độ tiết kiệm bộ nhớ. Lệnh trên chỉ cập nhật giao diện mà không tự khởi động các dịch vụ backend còn thiếu. Truy cập <http://127.0.0.1:8501> sau khi container dashboard sẵn sàng.

Bằng chứng kiểm thử trình duyệt hiện tại nằm trong `docs/evidence/dashboard-english/`; ảnh chụp và kết quả kiểm thử animation nằm trong `docs/evidence/dashboard-motion/`. Các tệp kết quả kiểm thử ghi rõ phạm vi đã kiểm tra. Các bằng chứng trước đó trong `docs/evidence/dashboard-pastel/` và `docs/evidence/dashboard-ui/` mô tả các phiên bản lịch sử.

Khi phát lại trên trình duyệt (browser replay), dữ liệu được xác định rõ là một snapshot đã lưu được phát lại trong bộ nhớ. Nhãn `RUNNING` trong snapshot đã lưu chỉ ghi nhận trạng thái tại thời điểm chụp chứ không khẳng định tiến trình producer hay Spark hiện tại đang hoạt động. Việc thay đổi giao diện không làm thay đổi độ chính xác phát hiện gian lận hay thông lượng xử lý của pipeline.
