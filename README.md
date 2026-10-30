# PaySim Big Data Baseline

Big Data baseline end-to-end:

![PaySim Big Data end-to-end architecture](docs/images/paysim-big-data-architecture.png)

## Yêu cầu

- Docker Desktop bản có Docker Compose hỗ trợ `--wait-timeout`, chạy Linux containers.
- Máy có **8 GB RAM**: cấp **4 GB cho Docker** ở Settings → Resources → Memory.
  Script tự chọn chế độ nhẹ khi Docker được cấp khoảng 4–6 GB. Máy dư RAM có thể
  cấp từ 6 GB cho Docker để chạy cấu hình tiêu chuẩn. Đây là RAM của Docker VM,
  không phải tổng RAM của máy.
- Ít nhất 10 GB dung lượng trống cho image, dataset và dữ liệu thực hành.
- Mac Intel và Mac Apple Silicon dùng cùng một lệnh khởi động; không cần bật Rosetta
  hoặc ép `platform: linux/amd64`. Script tự chọn kiến trúc của Docker.
- Internet trong lần chạy đầu để tải image và dataset.

## Khởi động

```bash
git clone https://github.com/thuanbui1309/paysim-big-data-baseline.git
cd paysim-big-data-baseline
```

macOS/Linux:

```bash
chmod +x start.sh stop.sh reset.sh scripts/prepare-data.sh
./start.sh
```

Windows:

```bat
start.bat
```

Dataset được tải và kiểm SHA-256 tự động nếu `data/paysim.csv` chưa có.
Script chỉ báo thành công khi các dịch vụ đã sẵn sàng, gồm HDFS thoát safe mode,
có DataNode hoạt động và Spark/dashboard healthy. Lần đầu có thể mất nhiều phút.

### Máy 8 GB RAM

Chạy `start.sh`/`start.bat` như bình thường. Chế độ nhẹ tự ghép cấu hình
`docker-compose.low-memory.yml`: Spark dùng heap 768 MiB, chạy một tác vụ tại một
thời điểm; Hadoop/Kafka dùng heap nhỏ hơn; mỗi batch tối đa 250 events và replayer
phát 10 events/s. Vẫn giữ đủ Kafka, Spark, HDFS, MongoDB, dashboard và cùng bộ dữ
liệu huấn luyện. Không xóa hay huấn luyện lại model đã lưu chỉ vì đổi chế độ RAM.

Chế độ này chậm hơn cấu hình tiêu chuẩn; nên đóng ứng dụng nặng và các stack
Docker khác khi thực hành. Các giá trị 10 events/s và 250 events/batch của chế độ
nhẹ ghi đè `EVENTS_PER_SECOND`/`MAX_OFFSETS_PER_TRIGGER` trong `.env`.
Nếu Docker có ít hơn khoảng 4 GB, script hiện dung lượng thực Docker nhìn thấy
và hướng dẫn tăng lên 4 GB, không yêu cầu cấp 6 GB trên máy 8 GB.

Khi khởi động thủ công bằng Compose để dùng chế độ nhẹ:

```bash
docker compose -f docker-compose.yml -f docker-compose.low-memory.yml up -d --build --wait
```

### Cập nhật bản sửa khởi động trên Mac

Sau khi nhận source mới, chạy lại `./start.sh` (Windows: `start.bat`). Script build
lại image Hadoop và Compose thay container khi image thay đổi. Không cần chạy reset:
các volume, metadata HDFS và dữ liệu hiện có được giữ lại.

Hadoop vẫn dùng phiên bản 3.4.1, nhưng chạy trên Java 11 native AMD64/ARM64.
Image cũ chỉ cung cấp các tệp Hadoop lúc build, không được chạy trong hệ thống mới.
Các thư viện Hadoop native AMD64 tùy chọn được bỏ đi; HDFS dùng Java fallback trên
cả hai kiến trúc. Healthcheck đọc HTTP/JMX, không khởi động thêm JVM mỗi lần.
Ảnh nguồn và Java runtime được cố định bằng digest trong `hadoop/Dockerfile`.

## Giao diện

- [Hướng dẫn dashboard PaySim Workspace](docs/05_Huong_Dan_Cai_Tien_Dashboard.md)
- [Biên bản kiểm thử và ảnh evidence gốc](docs/06_Kiem_Thu_Dashboard_Va_Khoi_Dong.md)

- Dashboard: <http://127.0.0.1:8501>
- HDFS: <http://127.0.0.1:9870>
- Spark: <http://127.0.0.1:4040>
- Kafka: `localhost:29092`
- MongoDB: `localhost:27017`

## Vận hành

macOS/Linux:

```bash
./stop.sh
./start.sh
./reset.sh
docker compose ps
docker compose logs -f spark replayer streamlit
```

Windows:

```bat
stop.bat
start.bat
reset.bat
docker compose ps
docker compose logs -f spark replayer streamlit
```

`reset.sh` và `reset.bat` xóa các volume Kafka, HDFS và MongoDB của riêng
baseline, nhưng không xóa `data/paysim.csv`. Chỉ reset khi chủ động muốn bỏ toàn bộ
kết quả thực hành. Safe mode trong lúc khởi động không phải lý do để xóa dữ liệu.
Nếu bước build/khởi động dịch vụ thất bại, script lưu `startup-output.log` và
`startup-diagnostics.txt` để tra nguyên nhân. Đây là tệp chẩn đoán, không phải tên lỗi.
Xem [hướng dẫn phân loại lỗi và kết quả kiểm thử script](docs/07_Kiem_Thu_Script_Va_Chan_Doan_Khoi_Dong.md). Nếu metadata HDFS không đầy đủ, bản mới
dừng và báo lỗi thay vì tự format đè lên dữ liệu có thể khôi phục.

Mặc định hệ thống phát liên tục 50 events/s, xử lý theo micro-batch 10 giây và
lặp lại dataset sau 6.362.620 giao dịch. Copy `.env.example` thành `.env` để đổi
cấu hình hoặc bật fault injection.

Nhãn PaySim không đi vào Kafka. Replayer lưu nhãn trong MongoDB `ground_truth`;
evaluator chỉ đọc nhãn sau khi Spark hoàn tất scoring.

Đây là deployment single-node dành cho thực hành.
