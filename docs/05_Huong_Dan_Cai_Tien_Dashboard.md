# HƯỚNG DẪN ĐỌC VÀ CẢI TIẾN GIAO DIỆN DASHBOARD PAYSIM WORKSPACE

## 1. Phạm vi

Dashboard sử dụng **một giao diện Workspace mới thống nhất**, lấy cảm hứng từ [trang Framer tham chiếu do người dùng cung cấp](https://little-assistant-921809.framer.app/) cùng bảng màu hồng pastel và kem đã chọn. Ba phương án `AFTER` cũ (`9A`, `9B`, `9C`) đã được gỡ bỏ khỏi ứng dụng theo yêu cầu.

Bản cải tiến chỉ thay đổi lớp trình bày và tương tác người dùng nhưng **giữ nguyên hoàn toàn các truy vấn cơ sở dữ liệu, công thức tính toán, mô hình và kết quả pipeline**. Dashboard đọc cùng một snapshot từ [`dashboard_core.py`](../dashboard/dashboard_core.py); tuyệt đối không huấn luyện lại mô hình hay chấm điểm lại giao dịch. Thay đổi duy nhất bên trong [`dashboard_core.py`](../dashboard/dashboard_core.py) là câu thông báo trạng thái sẵn sàng của pipeline. Nội dung hiển thị trên giao diện Workspace mới sử dụng tiếng Anh; các mã định danh trang nội bộ và dữ liệu pipeline vẫn tương thích hoàn toàn với dự án gốc.

## 2. Cấu trúc kiến trúc

```text
Kafka → Spark → HDFS / MongoDB
                       ↓
           dashboard_core.load_snapshot()
                       ↓
           app.py → view_workspace.py
                       ↓
    Overview / Pipeline metrics / Fraud & business / Transactions
```

| Tệp | Vai trò |
|---|---|
| [app.py](../dashboard/app.py) | Điểm khởi chạy ứng dụng PaySim Workspace |
| [view_workspace.py](../dashboard/view_workspace.py) | Điều phối hiển thị bốn trang chức năng |
| [ui_theme.py](../dashboard/ui_theme.py) | Bố cục dùng chung, biểu tượng (icons), thanh điều hướng, 6 KPI của đợt chạy và khung nhúng hero |
| [dashboard.css](../dashboard/assets/dashboard.css) | Giao diện tông hồng và kem, thẻ kính mờ (glass cards), bố cục đáp ứng (responsive) và hiệu ứng tương tác |
| [hero.html](../dashboard/assets/hero.html) | Minh họa tham chiếu từ Framer, hiệu ứng chuyển động CSS và xử lý chế độ giảm chuyển động (`reduced-motion`) |
| [ui_pages.py](../dashboard/ui_pages.py) | Các biểu đồ, phần đánh giá mô hình và 10 nhóm chỉ số (10 metric tracks) |
| [ui_transactions.py](../dashboard/ui_transactions.py) | Bộ lọc bản ghi, bảng dữ liệu, chi tiết từng giao dịch và xuất tệp CSV |
| [dashboard_core.py](../dashboard/dashboard_core.py) | Nguồn truy vấn snapshot và công thức tính toán gốc (giữ nguyên) |

Không còn các khối `AFTER` cần phải comment hay bỏ comment. Tệp [`app.py`](../dashboard/app.py) gọi trực tiếp `render(view)` thông qua [`view_workspace.py`](../dashboard/view_workspace.py).

## 3. Các trang chức năng

- **Overview (Tổng quan):** 6 chỉ số KPI chính, thông lượng (throughput), độ trễ (lag/latency), tiến độ xử lý và hoạt động gần đây. Cửa sổ biểu đồ 15/30/60 micro-batch lọc trực tiếp từ dữ liệu đã nạp sẵn.
- **Pipeline metrics (Chỉ số Pipeline):** Các nhóm mở rộng cho 10 nhóm chỉ số (10 metric tracks), định nghĩa công thức và điều kiện đối soát. Các phép đo chưa thực hiện giữ nguyên nhãn `Benchmark-only`.
- **Fraud & business (Gian lận & Nghiệp vụ):** So sánh mô hình MLlib và tập luật (Rule baseline), Precision, Recall, F1, ma trận nhầm lẫn (Confusion matrix), cơ cấu loại giao dịch và danh sách cảnh báo.
- **Transactions (Giao dịch):** Lọc bản ghi, chọn một dòng hoặc `Event ID`, tra cứu chi tiết giao dịch và tải xuống các bản ghi đang hiển thị dưới dạng CSV.

## 4. Bộ lọc dữ liệu

Bộ lọc hỗ trợ lọc theo loại giao dịch (`type`), số tiền tối thiểu/tối đa (`amount`), khoảng điểm rủi ro (`risk score`), dự đoán cảnh báo (`alert prediction`), tìm kiếm theo `Event ID`, và khoảng ngày giờ UTC. Người dùng có thể đặt lại (reset) bộ lọc và chọn thứ tự sắp xếp hiển thị.

**Phạm vi dữ liệu không thay đổi:** các truy vấn gốc nạp tối đa 60 micro-batch gần nhất, 60 giao dịch gần nhất và 300 cảnh báo gần nhất của đợt chạy (`run_id`) đang chọn. Ví dụ, `12/60` có nghĩa là 12 trong số 60 bản ghi đã nạp khớp với bộ lọc — đây không phải là truy vấn tìm kiếm trên toàn bộ lịch sử giao dịch trong cơ sở dữ liệu.

- Bộ lọc không làm thay đổi 6 KPI toàn đợt chạy và kết quả đánh giá mô hình.
- Bộ lọc điểm rủi ro chỉ lọc trên kết quả đã chấm sẵn mà không làm thay đổi ngưỡng phát hiện (`threshold`) của mô hình.
- Chi tiết giao dịch vẫn gắn liền với `Event ID` đang chọn khi có các dòng dữ liệu mới đổ về.
- Nếu bản ghi đang chọn rời khỏi cửa sổ snapshot hoặc không còn khớp với bộ lọc, giao diện sẽ xóa lựa chọn và hiển thị thông báo giải thích lý do.
- Tệp CSV xuất ra chứa các bản ghi đã lọc theo đúng thứ tự hiển thị, kèm UTF-8 BOM. Các chuỗi văn bản mà ứng dụng bảng tính có thể hiểu nhầm thành công thức đều được escape an toàn khi xuất.

## 5. Giao diện, biểu tượng và hiệu ứng chuyển động

Bảng màu sử dụng hồng pastel `#FFCFD9`, hồng đào `#FFDEDE`, kem `#FFF5DF` và vàng bơ `#FFE9C7`, kết hợp với màu chữ và màu biểu đồ đậm hơn để đảm bảo độ tương phản rõ ràng.

Biểu tượng (icons), CSS và hình ảnh minh họa được đóng gói cục bộ ngay trong dự án. Việc chạy dashboard không yêu cầu tài khoản Framer, dịch vụ animation trả phí hay CDN lúc chạy. Giấy phép biểu tượng được đính kèm tại [LICENSE-icons.txt](../dashboard/assets/LICENSE-icons.txt).

Hiệu ứng chuyển động ở phần hero tuân theo [module NovaAIWorkspace do người dùng cung cấp](https://framer.com/m/NovaAIWorkspace-we4woi.js@XOdWXg6mBixFPNlr1Zps). Thiết kế tham chiếu đó sử dụng ảnh PNG trong suốt và biến đổi CSS (`CSS transforms`). Dashboard tích hợp cùng [hình ảnh minh họa đã xuất bản](https://framerusercontent.com/images/dcjF6157kwSMfrYalKVakR6JKiI.png?width=1536&height=1024) tại `dashboard/assets/fluid-glass.png`; dữ liệu byte của ảnh được giữ nguyên, và bộ lọc CSS `hue-rotate(105deg)` chuyển tông màu sang chủ đề hồng pastel.

Các thông số chuyển động được chuyển nguyên bản từ mẫu tham chiếu:

| Thành phần | Hiệu ứng chuyển động |
|---|---|
| Dải kính 3D (Glass ribbon artwork) | `fluidFloat`, 10 giây, `ease-in-out`, lặp vô hạn (`infinite`) |
| Quầng sáng nền (Background glow) | `fluidGlowMotion`, 8 giây, `ease-in-out`, lặp đảo chiều vô hạn (`infinite alternate`) |
| 7 thanh sóng âm (Equalizer bars) | `waveAnimation`, 0.95 giây, `ease-in-out`, lặp đảo chiều vô hạn; độ trễ lệch nhau `−0.13` giây |
| Thẻ kính thông tin và nhãn trạng thái | Đứng yên (tĩnh), khớp với hành vi của bản tham chiếu |

Hình minh họa sử dụng các keyframe biến đổi sau:

```css
0%, 100% { transform: translate3d(0, 0, 0) rotate(-1deg) scale(1); }
35% { transform: translate3d(8px, -6px, 0) rotate(.8deg) scale(1.015); }
70% { transform: translate3d(-5px, 6px, 0) rotate(-.7deg) scale(.995); }
```

Khung hero là phần minh họa không gian làm việc mang tính trang trí. Các nhãn danh mục trên đó mô tả các góc nhìn phân tích chứ không tuyên bố rằng pipeline đang chạy mô phỏng giả lập. Khung hero được gắn bên ngoài fragment làm mới dữ liệu 2 giây (`@st.fragment(run_every="2s")`), nhờ đó mỗi lần làm mới snapshot không làm khởi động lại hiệu ứng chuyển động. Chuyển động tự động tạm dừng khi hình minh họa cuộn khuất khỏi màn hình hoặc khi tab trình duyệt bị ẩn, đồng thời thiết lập `prefers-reduced-motion` của hệ điều hành sẽ tắt hoàn toàn hiệu ứng động. Bố cục trên thiết bị di động dành riêng không gian cho hình minh họa và thẻ thông tin nằm phía trên thanh điều hướng.

Triển khai này không cần Three.js, WebGL, Node.js hay bước build npm. Để thay đổi diện mạo, chỉ cần chỉnh sửa [`hero.html`](../dashboard/assets/hero.html) hoặc tệp CSS của dashboard, sau đó build lại riêng container dashboard theo hướng dẫn bên dưới.

## 6. Khởi chạy Dashboard

Nếu các dịch vụ backend đã đang chạy trên Docker, chỉ cần build và cập nhật lại riêng container dashboard:

```powershell
docker compose -f docker-compose.yml up -d --build --no-deps streamlit
```

Nếu dự án đang chạy ở cấu hình tiết kiệm bộ nhớ (`low-memory`), hãy giữ nguyên tệp overlay tương ứng:

```powershell
docker compose -f docker-compose.yml -f docker-compose.low-memory.yml up -d --build --no-deps streamlit
```

Mở <http://127.0.0.1:8501>. `Dockerfile` sao chép mã nguồn và tài nguyên vào trong image khi build, vì vậy việc chỉ tải lại trình duyệt hoặc restart một image cũ sẽ không nạp được giao diện mới. Các lệnh trên chỉ cập nhật container dashboard; cờ `--no-deps` không tự khởi động các dịch vụ backend còn thiếu. Để khởi động toàn bộ dự án từ đầu, hãy dùng `start.bat` trên Windows hoặc `./start.sh` trên macOS/Linux.

Để chạy dashboard trực tiếp trên máy host kết nối tới một MongoDB đang mở sẵn:

```powershell
$env:MONGO_URI = 'mongodb://127.0.0.1:27017'
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

## 7. Kiểm chứng (Verification)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r dashboard/requirements.txt -r tests/requirements.txt
.\.venv\Scripts\python.exe -m pytest -q tests
```

Tệp [`tests/test_dashboard.py`](../tests/test_dashboard.py) đối chiếu giao diện Workspace mới với bộ render gốc trên cùng dữ liệu MongoDB trong bộ nhớ: kiểm tra đủ 6 KPI, toàn bộ 10 nhóm chỉ số (10 metric tracks), kết quả đánh giá mô hình/tập luật, giới hạn truy vấn, thứ tự sắp xếp, cô lập đợt chạy (`run isolation`), bộ lọc, xuất CSV, thao tác đặt lại bộ lọc (reset) và việc giữ lựa chọn giao dịch qua các chu kỳ làm mới. Bộ kiểm thử cũng kiểm tra trực tiếp entrypoint [`app.py`](../dashboard/app.py) và các nhãn hiển thị.

Kiểm thử trình duyệt (Browser QA) có thể phát lại (replay) một snapshot pipeline đã lưu **ngay trong bộ nhớ**, mà không ghi đè vào cơ sở dữ liệu MongoDB nguồn:

```powershell
.\.venv\Scripts\python.exe tests/capture_dashboard.py --output docs/evidence/dashboard-english --snapshot-file docs/evidence/dashboard-ui/snapshot.json
```

Bỏ tùy chọn `--snapshot-file` nếu muốn đọc trực tiếp từ cơ sở dữ liệu MongoDB thật. Việc đối chiếu khớp tuyệt đối các con số đòi hỏi phải chạy trên cùng một snapshot đã lưu. Độ tươi mới của dữ liệu (`freshness`) và độ trễ truy vấn (`query latency`) phụ thuộc vào thời điểm quan sát thực tế chứ không phải là hằng số nghiệp vụ cố định.

Tệp [`tests/check_hero_motion.py`](../tests/check_hero_motion.py) kiểm tra chuyển động thực tế của hình minh họa khi ở trạng thái nghỉ, thông số animation, hành vi `reduced-motion`, bố cục mobile và tính bền vững của iframe qua các lần làm mới dữ liệu. Chế độ xem trước độc lập (`--preview`) cho phép kiểm tra hiệu ứng chuyển động mà không cần khởi động lại dashboard chính:

```powershell
.\.venv\Scripts\python.exe tests/check_hero_motion.py --preview --output docs/evidence/dashboard-motion
```

Bằng chứng kiểm thử trình duyệt của giao diện Workspace hiện tại nằm trong `docs/evidence/dashboard-english/`; bằng chứng kiểm thử chuyển động nằm trong `docs/evidence/dashboard-motion/`. Hãy đọc các tệp kết quả và chú thích để nắm rõ nguồn dữ liệu cũng như phạm vi kiểm thử. Các snapshot đã lưu chỉ phản ánh trạng thái pipeline tại thời điểm ghi nhận, không dùng để khẳng định rằng pipeline trực tiếp hiện tại đang chạy.

Hình ảnh và báo cáo trong `docs/evidence/dashboard-ui/`, `docs/evidence/dashboard-pastel/` và [tài liệu kiểm thử trước đó](06_Kiem_Thu_Dashboard_Va_Khoi_Dong.md) mô tả các phiên bản lịch sử trước đây. Xem thêm [ghi chú triển khai](07_Dashboard_Pastel_Redesign.md) để nắm rõ các quyết định thiết kế và ranh giới dữ liệu.

## 8. Khôi phục mốc Checkpoint trước khi thiết kế lại

Mốc checkpoint cục bộ trước khi thiết kế lại giao diện là commit `03ac9a5` — `chore: checkpoint before dashboard redesign` (bao gồm cả hướng dẫn 4 phiên bản `BEFORE` / `AFTER 9A, 9B, 9C` ban đầu). Công việc thiết kế lại nằm trên nhánh `dashboard/pastel-framer-redesign`.

Sau khi lưu lại công việc hiện tại, bạn có thể mở lại mốc checkpoint đó trên một nhánh riêng bằng lệnh:

```powershell
git switch -c dashboard/checkpoint-review 03ac9a5
```

Checkpoint này bảo toàn nguyên trạng thái mã nguồn đã lưu trước đó. Lưu ý rằng Git chỉ khôi phục mã nguồn được theo dõi (tracked files), không tự động quay lui dữ liệu trong volumes MongoDB/HDFS hay các tệp nằm trong `.gitignore`.
