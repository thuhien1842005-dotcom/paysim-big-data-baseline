"""Clarify where the old transaction table and operational charts belong."""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'output' / 'Thuyet_trinh_toi_uu_dashboard_PaySim.html'
html = OUT.read_text(encoding='utf-8')

replacements = [
    ('Bản gốc • bảng giao dịch trong cửa sổ dữ liệu gần nhất',
     'Tab giao dịch bản gốc • bảng trong cửa sổ dữ liệu gần nhất'),
    ('Thu gọn lịch sử và phần lớn nhóm chỉ số, thêm cửa sổ 15/30/60 micro-batch',
     'Duration chart đã có ở Overview bản gốc; Workspace gom biểu đồ và bảng lịch sử batch trong expander.'),
    ('Nhiều nội dung mở trực tiếp</td><td>Thu gọn nhiều phần, cần bấm thêm',
     'Overview đã có biểu đồ duration và batch gần nhất</td><td>Biểu đồ duration + history trong expander; cần bấm mở'),
    ('Cùng snapshot 23/10 để so sánh bố cục. Nhãn Workspace trong ảnh là phiên bản lưu trước đó.',
     'Cặp ảnh cùng snapshot 23/10. Bản gốc đã có duration; Workspace gom duration và history vào expander.'),
]

for old, new in replacements:
    count = html.count(old)
    if count != 1:
        raise ValueError(f'Expected one occurrence, found {count}: {old[:70]}')
    html = html.replace(old, new, 1)

OUT.write_text(html, encoding='utf-8')
print('Clarified the transaction tab, operational chart, and duration/history comparison.')
