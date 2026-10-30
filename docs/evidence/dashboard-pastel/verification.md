# Kiểm chứng PaySim Workspace — 27/10/2026

Ảnh ở thư mục này ghi lại bố cục pastel trước khi thay phần trang trí tĩnh bằng khối kính 3D. Kiểm chứng animation sau đó nằm ở `../dashboard-motion/`; không dùng các ảnh tĩnh dưới đây để khẳng định hiệu ứng có chuyển động.

## Phạm vi

Một giao diện Workspace mới thay ba phương án AFTER cũ. Nhánh `dashboard/pastel-framer-redesign`; mốc khôi phục `03ac9a5`. Không thay `dashboard_core.py`, Spark hoặc Replayer so với mốc này.

## Kiểm thử

Lệnh `.venv/Scripts/python.exe -m pytest -q tests --disable-warnings --maxfail=1`:

```text
33 passed, 12 skipped, 12 subtests passed
```

Trong đó 28 test dashboard kiểm tra sáu KPI trên đủ bốn trang, toàn bộ metric 10 tracks và `Benchmark-only`, evaluation model/rule, entrypoint thật, database rỗng, run chưa có telemetry, query limits/order/run isolation, bộ lọc kết hợp, UTC, CSV, reset và giữ lựa chọn theo ID qua refresh. Các test bị skip là kiểm thử nền tảng/launcher không đáp ứng điều kiện chạy trong môi trường này; đây không phải kết quả pipeline end-to-end.

## Browser replay

```powershell
.\.venv\Scripts\python.exe tests/capture_dashboard.py --views workspace baseline --output docs/evidence/dashboard-pastel --snapshot-file docs/evidence/dashboard-ui/snapshot.json
```

- Chrome headless; desktop 1600 × 1100, mobile 390 × 844.
- 8 trang desktop: bốn trang của renderer gốc và bốn trang Workspace.
- 4 ảnh mobile: tổng quan và giao dịch của mỗi renderer.
- Sáu KPI khớp trên cả bốn cặp trang; không có browser exception hoặc tràn ngang trang.
- Đã kiểm tra tìm kiếm không khớp và reset bằng thao tác trình duyệt, không chỉ AppTest.
- [Metadata đầy đủ](browser-results.json).

Dữ liệu là snapshot pipeline thật đã lưu từ ngày 23/10/2026, được replay bằng Mongo giả **trong bộ nhớ**. Không ghi hoặc thay thế MongoDB nguồn. RUNNING trong ảnh là trạng thái lưu trong snapshot. Ảnh viewport không thể hiện toàn bộ phần phải cuộn trong vùng chính của Streamlit.

## Vận hành

Đã build/chạy riêng service `streamlit` bằng `docker compose -f docker-compose.yml up -d --build --no-deps streamlit`. Không restart hoặc cấu hình lại pipeline. UI tiếp tục cập nhật snapshot mỗi 2 giây.

Đã mở đủ bốn trang của container đang chạy, chờ qua chu kỳ refresh, kiểm tra reset bộ lọc và chế độ giảm chuyển động: không có browser exception. [Kết quả Docker smoke](docker-smoke.json). MongoDB hiện trả run `run-20260930-115737` ở trạng thái `STOPPED`, chưa có cửa sổ giao dịch đã xử lý; bộ lọc vẫn hiển thị trong trạng thái chờ. Không chèn dữ liệu mẫu hoặc khởi động lại producer/Spark để thay đổi kết quả này.

CSS và icon local được COPY vào image; không phụ thuộc tài nguyên trả phí. Giảm chuyển động theo thiết lập hệ điều hành được hỗ trợ. Những kết quả này không chứng minh pipeline xử lý nhanh hơn hoặc model tốt hơn.
