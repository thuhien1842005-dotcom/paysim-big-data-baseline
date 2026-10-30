# KIỂM CHỨNG GIAO DIỆN PAYSIM WORKSPACE

## 1. Phạm vi

Không gian làm việc sử dụng văn bản hiển thị tiếng Anh và hình minh họa Framer tông hồng pastel. Toàn bộ truy vấn, công thức tính toán, mô hình và kết quả pipeline được bảo toàn nguyên vẹn. Thay đổi duy nhất trong [`dashboard_core.py`](../../../dashboard/dashboard_core.py) là dịch thông báo trạng thái sẵn sàng của pipeline. Mốc checkpoint trước khi thiết kế lại: `03ac9a5`; nhánh làm việc: `dashboard/pastel-framer-redesign`.

## 2. Kiểm thử tự động

Bộ kiểm thử hoàn chỉnh ghi nhận **34 passed, 12 skipped, 12 subtests passed**, bao gồm: đối chiếu 6 KPI toàn đợt chạy trên cả 4 trang, toàn bộ 10 nhóm chỉ số (10 metric tracks), đánh giá mô hình MLlib và tập luật (Rule baseline), giới hạn truy vấn và thứ tự sắp xếp, cô lập đợt chạy (`run isolation`), bộ lọc, xuất CSV, đặt lại bộ lọc (reset), giữ lựa chọn giao dịch qua các chu kỳ làm mới, nhãn hiển thị và các trạng thái rỗng. Các bài kiểm thử launcher/nền tảng được bỏ qua (skipped) do điều kiện môi trường không phải là kiểm thử pipeline end-to-end.

## 3. Phát lại trên trình duyệt (Browser replay)

[Kết quả trình duyệt](browser-results.json) ghi nhận 8 ảnh chụp giao diện máy tính (desktop) và 4 ảnh chụp giao diện di động (mobile): 4 trang cho bản gốc (baseline) và 4 trang cho bản Workspace mới, cộng thêm trang Tổng quan (Overview) và Giao dịch (Transactions) trên mobile cho mỗi bộ render. Sáu chỉ số KPI của đợt chạy khớp nhau trên cả 4 cặp trang. Không có lỗi ngoại lệ trình duyệt (browser exceptions) hay tràn khung ngang (horizontal overflow) ở cấp độ trang. Thao tác tìm kiếm không có bản ghi khớp và thao tác đặt lại bộ lọc đã được kiểm tra trực tiếp trên trình duyệt.

Nguồn dữ liệu là snapshot pipeline đã lưu tại `../dashboard-ui/snapshot.json`, được phát lại thông qua MongoDB giả lập trong bộ nhớ. Không có dữ liệu nào bị ghi vào cơ sở dữ liệu thật. Nhãn `RUNNING` đã lưu mô tả trạng thái của snapshot tại thời điểm chụp, không phản ánh hoạt động của backend hiện tại. Ảnh chụp màn hình thể hiện vùng nhìn thấy (viewport) của Streamlit; các phần dài hơn cần cuộn trang để xem hết.

## 4. Hiệu ứng chuyển động (Animation)

[Kết quả kiểm thử chuyển động](../dashboard-motion/results.json) xác nhận chuyển động thực tế của hình minh họa khi không cần di chuột (hover), khớp thông số chuẩn gồm chu kỳ trôi nổi 10 giây (`fluidFloat`), quầng sáng 8 giây (`fluidGlowMotion`), 7 thanh sóng âm 0.95 giây (`waveAnimation`) và thẻ kính thông tin đứng yên. Hình minh họa duy trì ổn định qua nhiều chu kỳ làm mới dữ liệu 2 giây, tự động tạm dừng khi cuộn khuất màn hình và dừng hoàn toàn khi bật chế độ giảm chuyển động (`prefers-reduced-motion`). Trên thiết bị di động, phần hình minh họa vẫn hiển thị gọn phía trên thanh điều hướng. Bài kiểm thử đạt yêu cầu ngay cả khi tắt WebGL và không phát sinh lỗi ngoại lệ trên trình duyệt.

Hình ảnh được đóng gói cục bộ và nhúng trực tiếp vào tài liệu hero. Nguồn gốc tài nguyên gốc được ghi nhận tại `dashboard/assets/framer-reference.json`. Hình minh họa được chuyển tông màu bằng CSS trong khi dữ liệu byte gốc của tệp ảnh hoàn toàn không thay đổi.

## 5. Vận hành

Xem [hướng dẫn cải tiến dashboard](../../05_Huong_Dan_Cai_Tien_Dashboard.md) để biết cách khởi chạy và khôi phục checkpoint. Cần chạy lệnh build lại Docker image của `streamlit` để nạp mã nguồn và tài nguyên mới vào container đang có.
