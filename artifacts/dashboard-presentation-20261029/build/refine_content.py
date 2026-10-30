import json
from pathlib import Path
p=Path(__file__).with_name('content.json')
d=json.loads(p.read_text(encoding='utf-8'))
d['disclosure']='Ảnh dashboard dùng cùng snapshot pipeline đã lưu ngày 23/10/2026, phát lại trong bộ nhớ. Nhãn RUNNING mô tả thời điểm lưu, không xác nhận backend đang chạy. Không có phép đo hiệu quả thao tác của người dùng hoặc benchmark hiệu năng dashboard trước–sau. Các tình huống sử dụng là minh họa, không phải phản hồi người dùng đã thu thập. Bộ ảnh dashboard-english dùng các nhãn Overview, Pipeline metrics, Fraud & business, Transactions. Ảnh bổ sung từ mã hiện tại có nhãn điều hướng khác, còn pha Việt–Anh. Bài mô tả bốn nhóm chức năng bằng tiếng Việt để tránh đồng nhất hai mốc giao diện.'
s=d['slides'][4]
s['bullets'][0]='Bốn nhóm: tổng quan vận hành, chỉ số, gian lận và nghiệp vụ, giao dịch'
s['speech']=s['speech'].replace('Workspace tổ chức nội dung thành bốn trang với nhãn tiếng Anh thống nhất.','Workspace giữ bốn nhóm nội dung: tổng quan vận hành, chỉ số, gian lận và nghiệp vụ, giao dịch.').replace('Nhãn tiếng Anh thống nhất cũng có thể gây khó cho người dùng quen tiếng Việt.','Phần nội dung chủ yếu dùng tiếng Anh, còn điều hướng trong mã hiện tại vẫn pha Việt–Anh. Chưa có lựa chọn ngôn ngữ.')
d['comparison'][2][2]='Phong cách pastel/kem, nội dung chủ yếu tiếng Anh, giữ định nghĩa và đơn vị KPI. Điều hướng hiện vẫn pha Việt–Anh.'
points=[
'Ở hình bên phải là Workspace trong bộ ảnh kiểm chứng. Khối hình kính chỉ dùng để trang trí, không báo trạng thái pipeline.',
'Vùng số 1 là sáu KPI. Vùng số 2 là các biểu đồ đã xuất hiện ngay trong màn hình này. Đây là giá trị snapshot, không phải số liệu cải thiện.',
'Vùng số 1 là bảng giao dịch với nhiều cột cần đối chiếu. Việc chưa có bộ lọc kết hợp còn được kiểm tra trong mã nguồn, ngoài quan sát từ ảnh.',
'Mỗi hàng của sơ đồ nối một hạn chế với ảnh hưởng có thể xảy ra và mục tiêu tương ứng. Đây là phân tích kỳ vọng, không phải kết quả đo.',
'Ảnh số 1 đã cuộn xuống vùng throughput và trạng thái. Ảnh số 2 cho thấy các thanh so sánh rule với mô hình. Đây là ảnh thật từ replay snapshot.',
'Vùng số 1 là bộ lọc thực tế. Vùng số 2 có Event ID, nút CSV và chi tiết một bản ghi thực trong snapshot. Ảnh chi tiết không mô tả kết quả lọc TRANSFER vừa nêu.',
'Hai ảnh cùng kích thước 1600 × 1100. Bên cũ đã thấy biểu đồ, bên mới chủ yếu thấy hero và KPI. Bảng dưới ảnh tóm tắt các khác biệt.',
'Ở ảnh mobile này, phần đầu Workspace vẫn chiếm nhiều chiều cao. Không tràn ngang cấp trang trong kiểm thử chưa chứng minh mọi tác vụ đều thuận tiện.'
]
for s,pt in zip(d['slides'],points): s['point']=pt
assert '?' not in d['disclosure']
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
