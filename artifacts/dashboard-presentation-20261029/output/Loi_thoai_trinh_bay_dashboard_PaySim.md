# Lời thoại thuyết trình tối ưu dashboard PaySim

**Bản luyện nói · 8 slide · khoảng 6 phút 30 giây**

Bản lời thoại này được viết để nói thành tiếng. Các ghi chú trong ngoặc vuông là chỉ dẫn cho người trình bày, không đọc thành lời. Thời lượng dự kiến gồm những nhịp dừng ngắn và thao tác chỉ hình; tốc độ nói thực tế có thể khiến bài dài hoặc ngắn hơn một chút.

**Lưu ý về bằng chứng:** Ảnh cũ và mới dùng cùng snapshot pipeline đã lưu ngày 23/10/2026, phát lại trong bộ nhớ. Trạng thái RUNNING chỉ mô tả lúc lưu. Chưa có phép đo thời gian thao tác của người dùng hoặc so sánh hiệu năng dashboard trước và sau. Vì vậy, khi nói về việc đọc, tìm và ra quyết định thuận lợi hơn, hãy dùng ngôn ngữ “kỳ vọng” thay vì coi đó là kết quả đã đo.

## Slide 1 · Vai trò của dashboard PaySim · 35 giây

*[Nhìn khán giả. Bắt đầu chậm, rõ.]*

Hãy hình dung một luồng dữ liệu giao dịch đang đi qua Replayer, Kafka và Spark. Để hiểu hệ thống đang ở đâu, ta cần một nơi có thể nhìn được nhịp xử lý, độ trễ và những giao dịch đang được mô hình cảnh báo. Đó là vai trò của dashboard.

Trong bài trình bày này, tôi sẽ nhìn giao diện từ hai góc độ: người vận hành theo dõi luồng dữ liệu, và người phân tích cần kiểm tra một giao dịch cụ thể. Mục tiêu là xem những gì đã được sắp xếp lại, điều đó có thể giúp người dùng ra sao, và giới hạn nào vẫn còn.

*[Chỉ vào hình bên phải.]* Khối kính là hình minh họa của giao diện. Nó không phải tín hiệu cho biết pipeline đang chạy.

**Chuyển slide:** Trước khi nói về thay đổi, chúng ta hãy ghi nhận những gì bản gốc đã làm tốt.

## Slide 2 · Điểm mạnh của dashboard gốc · 45 giây

*[Chỉ lần lượt vào vùng đánh dấu 1, rồi 2.]*

Ở đây, bản gốc đã làm được một việc quan trọng: đưa nhiều thông tin vận hành về cùng một nơi. Sáu KPI cho biết nguồn đã phát bao nhiêu bản ghi, Spark xử lý được bao nhiêu, số cảnh báo, tốc độ ingest, thông lượng xử lý và độ trễ p95.

Trong snapshot minh họa, nguồn đã phát **5.200** bản ghi, Spark xử lý **4.700**. Như vậy, chỉ riêng hai con số này đã cho ta thấy còn **500** bản ghi đang chờ. Đây là một ví dụ rất cụ thể về cách KPI giúp người vận hành đặt câu hỏi tiếp theo: hệ thống đang bắt kịp, hay đang có độ trễ?

*[Ngừng nửa nhịp, chuyển sang biểu đồ.]* Bản gốc còn có biểu đồ vận hành, mười nhóm chỉ số, so sánh rule với mô hình và ma trận nhầm lẫn. Giao diện cũng tự cập nhật. Nói cách khác, dashboard cũ đã có nền tảng giám sát đáng kể. Những phần này là thế mạnh được giữ lại, không phải tính năng mới của lần thiết kế lại.

*[Nhấn nhẹ: “cùng snapshot”.]* Các con số này mô tả ảnh chụp dữ liệu đang xem. Chúng không chứng minh phiên bản mới xử lý nhanh hơn.

**Chuyển slide:** Nhưng theo dõi toàn hệ thống và kiểm tra một giao dịch cụ thể là hai nhu cầu khác nhau.

## Slide 3 · Khó khăn khi kiểm tra giao dịch · 45 giây

*[Nhìn vào hình, rồi nhìn khán giả.]*

Hãy xét một tình huống minh họa. Một người phân tích muốn tìm giao dịch **TRANSFER**, số tiền lớn, đang có cảnh báo. Ở bản gốc, họ có bảng giao dịch và nhiều cột hữu ích. Tuy nhiên, ứng dụng chưa có một luồng lọc kết hợp loại giao dịch, khoảng tiền và trạng thái cảnh báo để dẫn họ đến đúng tập kết quả.

Người dùng vẫn có thể dùng công cụ sẵn có của bảng. Vì vậy, sẽ thiếu chính xác nếu nói rằng bản cũ hoàn toàn không có tìm kiếm hay tải dữ liệu. Điểm khác biệt nằm ở chỗ: bản gốc chưa xây dựng một quy trình riêng để lọc theo điều kiện nghiệp vụ, mở hồ sơ theo Event ID và duy trì đúng giao dịch đang xem khi dữ liệu cập nhật.

*[Chỉ vào những cột Event ID, Amount và Alert.]* Hình cho thấy các trường có sẵn; nhu cầu nối các trường đó thành một quy trình là điều ta đang phân tích. Đây là tình huống minh họa từ giao diện, chưa phải kết quả khảo sát người dùng.

**Chuyển slide:** Vậy mỗi điểm cần tối ưu phải gắn với một mục tiêu sử dụng cụ thể.

## Slide 4 · Hạn chế và mục tiêu cải tiến · 45 giây

*[Lần lượt chỉ qua ba cột của sơ đồ.]*

Sơ đồ nối ba vấn đề với ba mục tiêu. Khi nội dung xuất hiện nối tiếp, người xem cần tìm đâu là phần quan trọng; mục tiêu là phân nhóm thông tin, rồi mở phần chi tiết khi cần. Khi phải đối chiếu nhiều cột để tìm một giao dịch, mục tiêu là lọc theo nhiều điều kiện và xem chi tiết theo mã ID. Khi KPI toàn đợt chạy đứng cạnh một cửa sổ chỉ chứa các giao dịch gần nhất, giao diện cần nói rõ hai phạm vi đó khác nhau.

*[Dừng một nhịp. Nhấn vào ví dụ.]* Chẳng hạn, không tìm thấy một Event ID trong danh sách đang nạp **không có nghĩa** giao dịch ấy không tồn tại. Có thể giao dịch nằm ngoài cửa sổ đang xem.

Các điểm ở giữa sơ đồ là tác động có thể xảy ra, không phải số liệu đã đo. Xuyên suốt quá trình này, nguyên tắc quan trọng là giữ nguyên công thức chỉ số và kết quả mô hình khi chỉ thay đổi cách trình bày.

**Chuyển slide:** Với những mục tiêu đó, bây giờ ta xem Workspace đã thay đổi những gì.

## Slide 5 · Workspace tổ chức lại thông tin · 60 giây

*[Chỉ hình đầu tiên, rồi hình thứ hai. Nói với nhịp vừa phải.]*

Workspace sắp xếp nội dung quanh bốn nhu cầu: tổng quan vận hành, chỉ số, gian lận và nghiệp vụ, và giao dịch. Ở phần vận hành, biểu đồ thông lượng được đặt nổi bật, trạng thái đặt bên cạnh, còn lag và độ trễ nằm phía dưới. Người xem cũng có thể chọn cửa sổ mười lăm, ba mươi hoặc sáu mươi micro-batch đã nạp.

*[Chỉ vào các nhóm được thu gọn.]* Các nhóm chỉ số và lịch sử có thể mở khi cần. Cách này giảm lượng nội dung hiện cùng lúc, nhưng cũng đồng nghĩa với thêm thao tác để xem chi tiết.

Ở phần nghiệp vụ, thay vì chỉ xem bảng số liệu, Precision, Recall và F1 của rule với Spark MLlib được đặt cạnh nhau bằng biểu đồ thanh. Cơ cấu giao dịch được biểu diễn bằng thanh ngang. Đây là thay đổi về **cách đọc dữ liệu đã có**. Việc so sánh mô hình và ma trận nhầm lẫn vốn đã tồn tại trong bản gốc.

*[Ngừng nửa nhịp.]* Mục tiêu của cách trình bày mới là giúp người xem đối chiếu nhanh hơn. Nhưng khi chưa thử với người dùng, đó vẫn là kỳ vọng. Các ảnh bổ sung trên slide dùng nhãn điều hướng hiện tại; tên trong bộ ảnh so sánh được lưu từ một mốc giao diện khác.

**Chuyển slide:** Thay đổi dễ thấy nhất trong công việc hằng ngày nằm ở cách kiểm tra một giao dịch.

## Slide 6 · Luồng kiểm tra giao dịch mới · 60 giây

*[Chỉ vùng số 1, quét theo các trường lọc.]*

Trong Workspace, người phân tích có thể kết hợp điều kiện theo loại giao dịch, số tiền, điểm rủi ro, trạng thái dự đoán, Event ID và thời gian UTC. Họ có thể đặt lại bộ lọc, đổi thứ tự kết quả, chọn một dòng hoặc tìm theo mã ID.

*[Chỉ vùng số 2. Nhấn vào Event ID và nút CSV.]* Khi đã chọn giao dịch, vùng chi tiết hiển thị điểm rủi ro, trạng thái dự đoán, thời điểm chấm và độ trễ. Lựa chọn được gắn với Event ID để không nhầm một dòng khác khi thứ tự dữ liệu thay đổi. Nút **Download visible CSV** xuất chính tập bản ghi đang hiển thị. Hình này cho thấy một giao dịch có thật trong snapshot; nó minh họa vùng chi tiết, chứ không phải kết quả của tình huống TRANSFER ở slide trước.

*[Ngừng một nhịp để người nghe nhìn chú thích.]* Điều cần nhớ là các bộ lọc chỉ chạy trên cửa sổ dữ liệu đã nạp: tối đa sáu mươi giao dịch hoặc ba trăm cảnh báo. KPI toàn đợt chạy không đổi khi ta lọc. Lọc điểm rủi ro cũng không đổi ngưỡng của mô hình. Và một cảnh báo là dự đoán của mô hình, không phải bằng chứng xác nhận gian lận.

Quy trình này đã có trong mã nguồn. Ta chưa đo xem người dùng hoàn thành nhanh hơn bao nhiêu.

**Chuyển slide:** Đặt hai phiên bản cạnh nhau sẽ cho thấy rõ cả phần được lợi lẫn phần phải đánh đổi.

## Slide 7 · So sánh trước và sau · 55 giây

*[Chỉ lần lượt vào hai ảnh; giữ mắt ở ảnh mới lâu hơn một nhịp.]*

Hai ảnh được chụp trên cùng snapshot và cùng kích thước màn hình. Hãy chú ý vùng người xem nhìn thấy đầu tiên: ở bản gốc, các biểu đồ đã xuất hiện trong viewport này. Ở Workspace, hero và các thẻ KPI chiếm thêm diện tích, nên để xem biểu đồ vận hành, người dùng phải cuộn xuống.

*[Nhấn giọng vừa phải: “đánh đổi”.]* Đó là một đánh đổi thực sự. Hero tạo điểm nhận diện cho Workspace; đổi lại, nó đẩy dữ liệu vận hành xuống thấp hơn. Việc thu gọn các nhóm chỉ số cũng bớt nội dung đang mở cùng lúc, nhưng cần thêm lần bấm.

Về tính nhất quán dữ liệu, kết quả kiểm thử đã lưu trong dự án cho thấy sáu KPI khớp nhau trên các cặp trang được đối chiếu. Còn về hiệu năng, mã truy vấn và công thức lõi vẫn được giữ nguyên. Hiện chưa có phép đo so sánh tốc độ render, mức sử dụng CPU hay thời gian hoàn thành tác vụ giữa hai phiên bản.

Vì vậy, ta có thể khẳng định giao diện và quy trình thao tác đã đổi. Ta chưa thể khẳng định dashboard xử lý nhanh hơn hoặc người dùng ra quyết định nhanh hơn.

**Chuyển slide:** Kết quả có ý nghĩa nhất sẽ đến từ việc kiểm tra người dùng thực hiện những tác vụ này ra sao.

## Slide 8 · Giá trị và bước đánh giá tiếp theo · 45 giây

*[Giọng kết luận, chậm hơn một chút.]*

Lần tối ưu này giữ lại nền tảng giám sát của bản gốc và bổ sung một luồng rõ ràng hơn để lọc, chọn, kiểm tra và xuất dữ liệu giao dịch. Đồng thời, ta đã thấy những điểm cần cân nhắc: hero chiếm diện tích, một số nội dung cần bấm để mở, việc tìm kiếm chỉ giới hạn trong cửa sổ dữ liệu đã nạp, và nhãn tiếng Anh có thể chưa phù hợp với mọi người dùng.

*[Chỉ vào danh sách đề xuất.]* Thu gọn hero, tra cứu lịch sử phía máy chủ và thêm lựa chọn Việt–Anh là các hướng đề xuất tiếp theo. Chúng chưa được triển khai.

Để đánh giá hiệu quả, hãy giao cùng một tác vụ và cùng một bộ dữ liệu cho người dùng trên cả hai phiên bản. Ghi lại họ trả lời có đúng không, mất bao lâu, thực hiện bao nhiêu thao tác và phải cuộn đến đâu. Đo hiệu năng trình duyệt và khả năng tiếp cận riêng, thay vì suy ra chúng từ một ảnh chụp.

*[Dừng một nhịp, nhìn khán giả.]* Giao diện mới đã mở thêm cách làm việc. Mức cải thiện thực tế sẽ được xác định bằng kết quả của những tác vụ đó.

**Kết thúc:** Xin cảm ơn mọi người. Tôi xin mời các câu hỏi.

## Nhắc nhanh trước khi trình bày

- Khi nêu **5.200, 4.700 và 500**, nói rõ đây là các giá trị trong snapshot minh họa.
- Với lợi ích chưa được đo, dùng cụm **“kỳ vọng giúp”** hoặc **“cần đánh giá thêm”**.
- Không nói bản cũ hoàn toàn không tìm kiếm hoặc xuất CSV; bảng cũ có toolbar nguyên bản.
- Không nói dashboard mới tăng tốc pipeline, cải thiện độ chính xác mô hình hoặc tìm trên toàn bộ lịch sử.
- Phân biệt **dự đoán cảnh báo** với **nhãn gian lận thực tế**.
