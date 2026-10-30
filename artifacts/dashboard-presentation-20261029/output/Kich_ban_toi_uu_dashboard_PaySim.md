# Tối ưu dashboard PaySim

Đánh giá Control Room gốc và Workspace hiện tại. **8 slide · Dự kiến 6 phút 30 giây · Chưa gồm hỏi đáp.**

Bản cũ là renderer gốc được dựng lại để đối chiếu, không đồng nhất với toàn bộ checkpoint 03ac9a5. Bản mới là Workspace trong mã nguồn hiện tại, có bằng chứng kiểm thử; chưa xác nhận triển khai production. Report, Operations, Studio và bản pastel với hero tĩnh là các phương án lịch sử.

Ảnh dashboard dùng cùng snapshot pipeline đã lưu ngày 23/10/2026, phát lại trong bộ nhớ. Nhãn RUNNING mô tả thời điểm lưu, không xác nhận backend đang chạy. Không có phép đo hiệu quả thao tác của người dùng hoặc benchmark hiệu năng dashboard trước–sau. Các tình huống sử dụng là minh họa, không phải phản hồi người dùng đã thu thập. Bộ ảnh dashboard-english dùng các nhãn Overview, Pipeline metrics, Fraud & business, Transactions. Ảnh bổ sung từ mã hiện tại có nhãn điều hướng khác, còn pha Việt–Anh. Bài mô tả bốn nhóm chức năng bằng tiếng Việt để tránh đồng nhất hai mốc giao diện.

Bản HTML cùng thư mục nhúng đầy đủ ảnh và chú thích, có chế độ trình chiếu và phóng to. Bản Markdown này thuận tiện chỉnh lời thoại.

## Slide 1 · Vai trò của dashboard PaySim · 35 giây

**Thông điệp chính:** Mục tiêu tối ưu là giúp người xem theo dõi và kiểm tra giao dịch rõ ràng hơn.

**Nội dung trên slide**

- Theo dõi luồng giao dịch, độ trễ và cảnh báo của mô hình
- Đối tượng phân tích: người vận hành và người phân tích giao dịch
- Phạm vi: giao diện và thao tác trên dữ liệu đã có

**Lời thoại dùng trực tiếp**

Trong PaySim, dashboard giúp người xem biết dữ liệu đã được xử lý đến đâu và giao dịch nào đang được mô hình cảnh báo. Bài này xét hai vai trò sử dụng: người vận hành theo dõi luồng dữ liệu và người phân tích kiểm tra giao dịch. Mục tiêu tối ưu là làm thông tin và thao tác rõ hơn, trong khi giữ nguyên cách tính chỉ số. Đây là các vai trò phân tích trong bài, chưa phải kết quả khảo sát người dùng.

**Lời nói khi chỉ hình**

Ở hình bên phải là Workspace trong bộ ảnh kiểm chứng. Khối hình kính chỉ dùng để trang trí, không báo trạng thái pipeline.

**Câu chuyển**

Trước hết, ta xem bản gốc đã đáp ứng tốt những việc gì.

**Bằng chứng:** Đối tượng sử dụng là giả định phân tích; ảnh thật từ replay.

**Nguồn:** dashboard/app.py:1–5; dashboard/dashboard_core.py:14,222–450; docs/07_Dashboard_Pastel_Redesign.md

## Slide 2 · Điểm mạnh của dashboard gốc · 45 giây

**Thông điệp chính:** Bản cũ đã có nền tảng theo dõi vận hành và đánh giá mô hình khá đầy đủ.

**Nội dung trên slide**

- Sáu KPI cùng các biểu đồ throughput, lag và độ trễ
- Có 10 nhóm chỉ số, so sánh rule–model và ma trận nhầm lẫn
- Tự làm mới mỗi 2 giây, có tương tác biểu đồ cơ bản

**Lời thoại dùng trực tiếp**

Dashboard gốc đã cung cấp một nền tảng khá đầy đủ. Sáu KPI cho biết số bản ghi nguồn đã phát, Spark đã xử lý, số cảnh báo và các chỉ số tốc độ, độ trễ. Trong snapshot minh họa, nguồn phát 5.200 bản ghi còn Spark xử lý 4.700, tức còn 500 bản ghi chờ xử lý. Người vận hành có thể đối chiếu với biểu đồ để nhận biết tình trạng tồn đọng. Bản cũ cũng đã có mười nhóm chỉ số, so sánh rule với mô hình và ma trận nhầm lẫn. Nó tự làm mới và có tương tác biểu đồ cơ bản. Những khả năng này được kế thừa khi thiết kế lại.

**Lời nói khi chỉ hình**

Vùng số 1 là sáu KPI. Vùng số 2 là các biểu đồ đã xuất hiện ngay trong màn hình này. Đây là giá trị snapshot, không phải số liệu cải thiện.

**Câu chuyển**

Tuy vậy, có đủ thông tin chưa chắc đã giúp người dùng kiểm tra một giao dịch thuận tiện.

**Bằng chứng:** Quan sát từ ảnh và mã nguồn; dữ liệu minh họa cùng snapshot.

**Nguồn:** dashboard/dashboard_core.py:222–288,378–449,454; docs/evidence/dashboard-english/baseline-1-desktop.png; docs/evidence/dashboard-english/browser-results.json

## Slide 3 · Khó khăn khi kiểm tra giao dịch · 45 giây

**Thông điệp chính:** Bản cũ thiếu một luồng kiểm tra giao dịch theo điều kiện nghiệp vụ do ứng dụng thiết kế.

**Nội dung trên slide**

- Tình huống minh họa: tìm TRANSFER số tiền lớn đang có cảnh báo
- Bảng nhiều cột nhưng chưa có bộ lọc nghiệp vụ kết hợp
- Chưa có vùng chi tiết và cơ chế giữ lựa chọn theo Event ID riêng

**Lời thoại dùng trực tiếp**

Giả sử người phân tích cần tìm một giao dịch TRANSFER có số tiền lớn và đang bị mô hình cảnh báo. Ở bản gốc, họ bắt đầu từ bảng giao dịch gần nhất và phải đối chiếu nhiều cột. Ứng dụng chưa có bộ lọc kết hợp loại giao dịch, số tiền và trạng thái cảnh báo, cũng chưa có vùng chi tiết riêng gắn với Event ID. Khi dữ liệu làm mới, việc giữ đúng giao dịch đang xem là một nhu cầu cần giải quyết. Đây là tình huống minh họa từ cấu trúc giao diện, chưa phải khó khăn đã được khảo sát. Thanh công cụ của bảng vẫn có thể hỗ trợ tìm kiếm hoặc tải dữ liệu cơ bản.

**Lời nói khi chỉ hình**

Vùng số 1 là bảng giao dịch với nhiều cột cần đối chiếu. Việc chưa có bộ lọc kết hợp còn được kiểm tra trong mã nguồn, ngoài quan sát từ ảnh.

**Câu chuyển**

Từ tình huống này, ta có thể xác định rõ từng mục tiêu cải tiến.

**Bằng chứng:** Tình huống minh họa, chưa có nghiên cứu người dùng.

**Nguồn:** dashboard/dashboard_core.py:417–435; dashboard/ui_transactions.py:162–198,263–328; docs/evidence/dashboard-english/baseline-4-desktop.png

## Slide 4 · Hạn chế và mục tiêu cải tiến · 45 giây

**Thông điệp chính:** Mỗi thay đổi cần gắn với một việc người dùng phải làm.

**Nội dung trên slide**

- Nhiều nội dung trình bày nối tiếp: cần phân cấp theo nhiệm vụ
- Đối chiếu nhiều cột: cần bộ lọc và chi tiết giao dịch
- Các phạm vi dữ liệu khác nhau: cần ghi rõ tổng toàn run và cửa sổ đã nạp

**Lời thoại dùng trực tiếp**

Có ba mối liên hệ cần làm rõ. Khi nhiều nội dung nối tiếp nhau, người xem phải tìm đâu là phần cần chú ý, nên mục tiêu là nhóm nội dung và cho phép mở chi tiết khi cần. Khi kiểm tra giao dịch đòi hỏi đối chiếu nhiều cột, mục tiêu là có bộ lọc kết hợp và vùng chi tiết theo ID. Khi KPI toàn đợt chạy và bảng giao dịch gần nhất có phạm vi khác nhau, cần ghi rõ để tránh suy diễn sai. Ví dụ, không tìm thấy một ID trong cửa sổ hiện tại chưa có nghĩa giao dịch đó không tồn tại. Các mục tiêu này liên quan trực tiếp đến cách đọc và sử dụng dữ liệu.

**Lời nói khi chỉ hình**

Mỗi hàng của sơ đồ nối một hạn chế với ảnh hưởng có thể xảy ra và mục tiêu tương ứng. Đây là phân tích kỳ vọng, không phải kết quả đo.

**Câu chuyển**

Tiếp theo là những thay đổi đã có trong Workspace để đáp ứng các mục tiêu đó.

**Bằng chứng:** Sơ đồ phân tích; tác động và lợi ích thao tác là kỳ vọng.

**Nguồn:** dashboard/dashboard_core.py:154–182,246–288; dashboard/ui_pages.py:40–74,162–170; dashboard/ui_transactions.py:263–268

## Slide 5 · Workspace tổ chức lại thông tin · 60 giây

**Thông điệp chính:** Bản mới thay đổi thứ tự ưu tiên và cách biểu diễn, đồng thời giữ các công thức cũ.

**Nội dung trên slide**

- Bốn nhóm: tổng quan vận hành, chỉ số, gian lận và nghiệp vụ, giao dịch
- Throughput ở vùng lớn, lag và độ trễ bên dưới, trạng thái bên cạnh
- Thu gọn lịch sử và phần lớn nhóm chỉ số, thêm cửa sổ 15/30/60 micro-batch
- Biểu đồ thanh cho Precision/Recall/F1 và cơ cấu giao dịch

**Lời thoại dùng trực tiếp**

Workspace giữ bốn nhóm nội dung: tổng quan vận hành, chỉ số, gian lận và nghiệp vụ, giao dịch. Trong phần vận hành, biểu đồ throughput chiếm vùng lớn, lag và độ trễ nằm bên dưới, còn trạng thái xử lý ở bên cạnh. Người xem có thể chọn cửa sổ mười lăm, ba mươi hoặc sáu mươi micro-batch từ dữ liệu đã nạp. Lịch sử và phần lớn nhóm chỉ số được thu gọn để giảm lượng nội dung mở cùng lúc. Ở trang nghiệp vụ, Precision, Recall và F1 của rule với mô hình được trình bày bằng các thanh cạnh nhau. Đây là cách biểu diễn mới cho phép so sánh đã có. Cơ cấu giao dịch dùng thanh ngang sắp theo số lượng. Các thay đổi này kỳ vọng giúp đối chiếu dễ hơn, nhưng người cần chi tiết phải bấm mở thêm. Phần nội dung chủ yếu dùng tiếng Anh, còn điều hướng trong mã hiện tại vẫn pha Việt–Anh. Chưa có lựa chọn ngôn ngữ.

**Lời nói khi chỉ hình**

Ảnh số 1 đã cuộn xuống vùng throughput và trạng thái. Ảnh số 2 cho thấy các thanh so sánh rule với mô hình. Đây là ảnh thật từ replay snapshot.

**Câu chuyển**

Thay đổi tiếp theo tập trung vào tình huống tìm và kiểm tra một giao dịch cụ thể.

**Bằng chứng:** Đã có trong mã nguồn; lợi ích về tốc độ đọc chưa được đo.

**Nguồn:** dashboard/ui_pages.py:40–74,77–99,119–128,162–170; dashboard/ui_theme.py:102–118; docs/07_Dashboard_Pastel_Redesign.md

## Slide 6 · Luồng kiểm tra giao dịch mới · 60 giây

**Thông điệp chính:** Bộ lọc, Event ID và CSV tạo thành một quy trình kiểm tra rõ ràng hơn.

**Nội dung trên slide**

- Lọc loại, tiền, điểm rủi ro, dự đoán, Event ID và thời gian UTC
- Chọn dòng hoặc ID để xem chi tiết, giữ lựa chọn theo ID qua refresh
- Reset và xuất CSV đúng tập lọc, theo thứ tự đang hiển thị
- Chỉ lọc dữ liệu đã nạp: tối đa 60 giao dịch hoặc 300 cảnh báo

**Lời thoại dùng trực tiếp**

Với tình huống vừa nêu, người phân tích có thể chọn TRANSFER, đặt khoảng tiền và chọn trạng thái Alert. Họ chọn một dòng hoặc Event ID để xem điểm rủi ro, dự đoán, thời điểm chấm và độ trễ. Ứng dụng giữ lựa chọn theo ID khi thứ tự dữ liệu thay đổi. Nếu bản ghi rời cửa sổ hoặc tập lọc, ứng dụng bỏ chọn và giải thích lý do. Nút Download visible CSV xuất đúng tập đang lọc. Tuy nhiên, bộ lọc chỉ áp dụng cho tối đa sáu mươi giao dịch hoặc ba trăm cảnh báo đã nạp, không tìm toàn bộ lịch sử. Sáu KPI và chất lượng mô hình toàn đợt chạy không đổi theo bộ lọc. Lọc điểm rủi ro cũng không đổi ngưỡng mô hình. Cuối cùng, Alert là dự đoán, chưa xác nhận giao dịch gian lận. Quy trình đã được triển khai, còn mức tiết kiệm thời gian cần đo thêm.

**Lời nói khi chỉ hình**

Vùng số 1 là bộ lọc thực tế. Vùng số 2 có Event ID, nút CSV và chi tiết một bản ghi thực trong snapshot. Ảnh chi tiết không mô tả kết quả lọc TRANSFER vừa nêu.

**Câu chuyển**

Khi đặt hai phiên bản cạnh nhau, lợi ích và đánh đổi hiện ra rõ hơn.

**Bằng chứng:** Chức năng đã có trong mã và bằng chứng kiểm thử; chưa đo thời gian thao tác.

**Nguồn:** dashboard/ui_transactions.py:113–126,162–198,206–328; dashboard/dashboard_core.py:154–180; docs/05_Huong_Dan_Cai_Tien_Dashboard.md:42–52

## Slide 7 · So sánh trước và sau · 55 giây

**Thông điệp chính:** Workspace mở rộng thao tác, nhưng phải đánh đổi diện tích màn hình và số lần mở chi tiết.

**Nội dung trên slide**

- Bản gốc đưa biểu đồ lên sớm trong viewport đã kiểm tra
- Workspace có bộ lọc và vùng chi tiết rõ hơn, hero chiếm thêm chiều cao
- Thu gọn giảm nội dung mở cùng lúc nhưng cần bấm thêm
- Chưa có benchmark tốc độ render, CPU/RAM hoặc hiệu quả tác vụ

**Lời thoại dùng trực tiếp**

Hai ảnh sử dụng cùng snapshot và cùng kích thước màn hình. Bản gốc đã cho thấy các biểu đồ ngay trong vùng nhìn đầu tiên. Ở Workspace, khối hero và các thẻ KPI đẩy biểu đồ xuống dưới, nên người vận hành phải cuộn thêm. Điều này cho thấy giao diện mới không thuận lợi hơn ở mọi nhiệm vụ. Việc thu gọn cũng đổi lượng thông tin đang mở lấy thêm lần bấm. Về dữ liệu, sáu KPI khớp nhau trên bốn cặp trang trong kết quả kiểm thử lưu ở dự án. Nhưng truy vấn và công thức lõi vẫn được giữ nguyên, chưa có benchmark chứng minh dashboard nhanh hơn. Chỉ số Snapshot response cũng chỉ đo thời gian nạp snapshot, không đại diện cho toàn bộ thời gian hiển thị trình duyệt.

**Lời nói khi chỉ hình**

Hai ảnh cùng kích thước 1600 × 1100. Bên cũ đã thấy biểu đồ, bên mới chủ yếu thấy hero và KPI. Bảng dưới ảnh tóm tắt các khác biệt.

**Câu chuyển**

Vì vậy, bước tiếp theo cần tập trung vào kiểm chứng lợi ích cho từng nhiệm vụ sử dụng.

**Bằng chứng:** So sánh quan sát được; không có số liệu tăng tốc trước–sau.

**Nguồn:** docs/evidence/dashboard-english/browser-results.json; dashboard/dashboard_core.py:154–182,365,454; dashboard/ui_theme.py:71–72; dashboard/assets/dashboard.css:116–124

## Slide 8 · Giá trị và bước đánh giá tiếp theo · 45 giây

**Thông điệp chính:** Giá trị đã thấy là quy trình kiểm tra rõ hơn; hiệu quả thực tế cần được đánh giá bằng tác vụ.

**Nội dung trên slide**

- Đã có: tổ chức lại nội dung, bộ lọc, chi tiết theo ID và CSV theo tập lọc
- Đề xuất: thu gọn hero, tra cứu lịch sử phía máy chủ, chọn Việt/Anh
- Đánh giá cùng dữ liệu và thiết bị: thời gian, độ đúng, số thao tác và mức cuộn
- Đo riêng thời gian render, CPU/RAM và khả năng tiếp cận

**Lời thoại dùng trực tiếp**

Giá trị quan sát được của lần tối ưu là cách tổ chức nội dung và quy trình kiểm tra giao dịch rõ ràng hơn, trong khi giữ các chỉ số cốt lõi. Những điểm cần tiếp tục xem xét là diện tích hero, giới hạn cửa sổ dữ liệu và ngôn ngữ hiển thị. Thu gọn hero, truy vấn lịch sử phía máy chủ và lựa chọn Việt–Anh hiện là đề xuất. Để đánh giá hiệu quả, nên cho người dùng thực hiện cùng tác vụ trên hai bản với cùng dữ liệu và thiết bị, rồi đo thời gian, độ đúng, số thao tác và mức cuộn. Hiệu năng trình duyệt và khả năng tiếp cận cần đánh giá riêng.

**Lời nói khi chỉ hình**

Ở ảnh mobile này, phần đầu Workspace vẫn chiếm nhiều chiều cao. Không tràn ngang cấp trang trong kiểm thử chưa chứng minh mọi tác vụ đều thuận tiện.

**Câu chuyển**

Tôi xin kết thúc phần trình bày và chuyển sang trao đổi về các giới hạn cũng như cách kiểm chứng tiếp theo.

**Bằng chứng:** Các hướng cải tiến và kế hoạch đánh giá là đề xuất, chưa triển khai.

**Nguồn:** docs/evidence/dashboard-english/verification.md; docs/evidence/dashboard-motion/results.json; docs/evidence/dashboard-english/baseline-1-mobile.png; docs/evidence/dashboard-english/workspace-1-mobile.png

## Bảng so sánh đầy đủ

| Tiêu chí | Cũ | Mới | Hạn chế và đánh đổi |
| --- | --- | --- | --- |
| Bố cục và vùng nhìn đầu | KPI, sơ đồ luồng và điều hướng trước biểu đồ. Đã thấy biểu đồ ở viewport đối chiếu. | Hero, điều hướng, KPI rồi biểu đồ. Riêng Transactions ưu tiên explorer trước KPI. | Workspace có nhận diện rõ, cần cuộn thêm để thấy dữ liệu. Chưa có chế độ thu gọn hero. |
| Phân cấp và 10 nhóm chỉ số | Nhiều nội dung và nhóm chỉ số hiển thị nối tiếp. | 10 nhóm dùng expander, mặc định mở nhóm 1 và 6. Duration và lịch sử được thu gọn. | Ít nội dung mở đồng thời, nhưng cần thêm lần bấm để xem sâu. |
| Khả năng đọc | KPI và biểu đồ đã có nhãn, chú thích, đơn vị. Việt–Anh đan xen. | Phong cách pastel/kem, nội dung chủ yếu tiếng Anh, giữ định nghĩa và đơn vị KPI. Điều hướng hiện vẫn pha Việt–Anh. | Độ dễ đọc tốt hơn là kỳ vọng. Chưa đo tương phản và khả năng tiếp cận đầy đủ. Chưa chọn Việt/Anh. |
| Biểu đồ vận hành | Throughput, lag, latency và batch duration trình bày trực tiếp. | Throughput lớn, lag/latency bên dưới, trạng thái bên cạnh; chọn 15/30/60 micro-batch đã nạp. | Thứ tự ưu tiên rõ hơn theo thiết kế. Duration và history cần mở thêm. Không tăng lượng dữ liệu nguồn. |
| Biểu đồ nghiệp vụ | Có bảng so sánh rule–model, confusion matrix, scatter; cơ cấu giao dịch dùng donut ở trang giao dịch. | Thanh nhóm cho Precision/Recall/F1; thanh ngang sắp số lượng cho cơ cấu giao dịch. Vẫn có confusion matrix và scatter. | Thay cách biểu diễn dữ liệu đã có. Không bổ sung mô hình mới và không làm độ chính xác tăng. |
| Bộ lọc | Chưa có bộ lọc nghiệp vụ kết hợp riêng; bảng có thanh công cụ nguyên bản của Streamlit. | Kết hợp loại, tiền, risk score, prediction, Event ID, UTC và thứ tự; có Reset. | Chỉ lọc ≤60 giao dịch hoặc ≤300 cảnh báo đã nạp. Không truy vấn toàn lịch sử, không đổi KPI tổng. |
| Thao tác và xem chi tiết | Bảng giao dịch cập nhật; chưa có inspector và giữ lựa chọn theo ID do ứng dụng thiết kế. | Chọn dòng/ID, xem chi tiết; giữ ID qua refresh, giải thích khi bỏ chọn. | Luồng kiểm tra được triển khai rõ hơn. Bản ghi có thể rời cửa sổ và cần tìm lại ngoài phạm vi hiện tại. |
| Xuất dữ liệu | Toolbar bảng có thể cung cấp tải xuống cơ bản; không khẳng định bản cũ không xuất được. | Nút Download visible CSV xuất đúng tập lọc/thứ tự; UTF-8 BOM. | Thuận tiện cho tập đang xem, không phải xuất toàn bộ lịch sử. Chưa đo số thao tác giảm được. |
| Hiệu năng và làm mới | Làm mới 2 giây; đã cache kết nối MongoDB bằng cache_resource. | Giữ truy vấn và công thức lõi. Hero ngoài fragment, cache tài nguyên cục bộ, giảm chuyển động được hỗ trợ. | Chưa có benchmark render, CPU/RAM hay thời gian tác vụ. Không chứng minh tăng throughput pipeline hoặc giảm độ trễ. |
| Mobile và kiểm chứng | Ảnh Overview/Transactions trên mobile không ghi nhận tràn ngang cấp trang trong replay. | Cùng phạm vi kiểm tra; hero hiển thị và reduced-motion có bằng chứng hành vi. | Cả hai chưa được chứng minh tối ưu mọi tác vụ. 0 lỗi ghi nhận không thay cho kiểm thử tải hoặc kiểm toán accessibility. |

## Năm câu hỏi phản biện

### 1. Có bằng chứng người dùng tìm giao dịch nhanh hơn không?

Chưa có phép đo thời gian hay tỷ lệ hoàn thành đúng. Bộ lọc, chi tiết, CSV và giữ Event ID đã có trong mã và bằng chứng kiểm thử. Tìm nhanh hơn là lợi ích kỳ vọng. Nên kiểm tra cùng tác vụ trên cùng snapshot, cùng thiết bị, đổi thứ tự hai phiên bản để giảm ảnh hưởng làm quen.

### 2. Không tìm thấy Event ID có nghĩa giao dịch không tồn tại?

Không. Explorer chỉ tìm trong tối đa 60 giao dịch hoặc 300 cảnh báo đã nạp của run hiện tại. Giao dịch có thể nằm ngoài cửa sổ hoặc bị loại bởi bộ lọc. Tra cứu toàn lịch sử và phân trang phía máy chủ là đề xuất, chưa triển khai.

### 3. Lọc risk score có đổi ngưỡng hoặc cải thiện Recall của mô hình?

Không. Bộ lọc chỉ chọn từ các kết quả đã chấm điểm. Nó không chạy lại suy luận, đổi threshold hay thay đánh giá toàn run. Alert là dự đoán của mô hình, phải phân biệt với nhãn actualFraud.

### 4. Hero lớn có đi ngược mục tiêu tối ưu dashboard vận hành?

Có đánh đổi. Ở viewport đối chiếu, bản gốc đã thấy biểu đồ trong khi Workspace cần cuộn thêm. Nếu ưu tiên giám sát thường xuyên, nên thử chế độ thu gọn hoặc ẩn hero. Đó là đề xuất tiếp theo, cần đánh giá tác vụ thay vì mặc định giao diện mới tốt hơn.

### 5. RUNNING và kết quả kiểm thử không lỗi có chứng minh hệ thống production ổn định?

Không. Ảnh là replay snapshot đã lưu, RUNNING chỉ là trạng thái lúc lưu. Kết quả lưu trong dự án ghi nhận 34 passed, 12 skipped và 12 subtests passed, cùng kiểm tra trình duyệt trong phạm vi cụ thể. Chúng không thay thế kiểm thử tải, độ bền, kiểm toán accessibility hay xác nhận backend hiện tại đang hoạt động.

## Kế hoạch đánh giá đề xuất

Dùng cùng snapshot, cùng thiết bị và cùng tác vụ. Đổi thứ tự phiên bản để giảm hiệu ứng làm quen. Chưa đặt tỷ lệ cải thiện khi chưa có số đo gốc.

| Tác vụ | Thiết kế đánh giá | Cần ghi nhận |
| --- | --- | --- |
| Nhận biết backlog | Xác định số bản ghi chờ và chỉ số cần kiểm tra tiếp | Thời gian, câu trả lời đúng, mức cuộn |
| Tìm giao dịch | Tìm giao dịch theo cùng điều kiện trong cùng snapshot | Tỷ lệ hoàn thành đúng, thời gian, số thao tác |
| Đọc đánh giá mô hình | So sánh Precision/Recall/F1 giữa rule và model | Độ đúng, thời gian trả lời, lỗi diễn giải |
| Hiệu năng và khả năng tiếp cận | Cùng thiết bị/viewport; thử desktop, mobile và giảm chuyển động | Render hoàn chỉnh, phản hồi tương tác, CPU/RAM, bàn phím, tương phản, screen reader |

Ảnh và sơ đồ thực sự được nhúng trong bản HTML. Các hình so sánh dùng cùng snapshot ngày 23/10/2026. Ảnh bổ sung dùng replay theo mã hiện tại, không ghi cơ sở dữ liệu nguồn.
