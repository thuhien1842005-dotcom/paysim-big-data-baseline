"""Add the verified running dashboard to the deck while preserving edited notes."""
from pathlib import Path
import base64
import html
import re
import struct

BUILD = Path(__file__).resolve().parent
OUT = BUILD.parent / 'output' / 'Thuyet_trinh_toi_uu_dashboard_PaySim.html'
LIVE = BUILD / 'running-dashboard-review'


def figure(name, caption, crop, marks=()):
    path = LIVE / name
    with path.open('rb') as f:
        width, height = struct.unpack('>II', f.read(24)[16:24])
    x, y, cw, ch = crop
    data = base64.b64encode(path.read_bytes()).decode('ascii')
    style = f'width:{width/cw*100:.5f}%;left:{-x/cw*100:.5f}%;top:{-y/ch*100:.5f}%;'
    overlays = ''.join(
        f'<span class="mark" style="left:{(bx-x)/cw*100:.3f}%;top:{(by-y)/ch*100:.3f}%;width:{bw/cw*100:.3f}%;height:{bh/ch*100:.3f}%"><b>{html.escape(str(label))}</b></span>'
        for label, bx, by, bw, bh in marks
    )
    safe = html.escape(caption, quote=True)
    return (f'<figure class="shot "><div class="imageview" tabindex="0" role="button" '
            f'aria-label="Phóng to ảnh {safe}" style="aspect-ratio:{cw}/{ch}">'
            f'<img alt="{safe}" src="data:image/png;base64,{data}" style="{style}">{overlays}'
            f'</div><figcaption>{safe}</figcaption></figure>')


EXTRA = {
    1: 'Ảnh bên phải chụp dashboard màu hồng đang chạy ngày 29/10/2026. Dữ liệu trên ảnh là giá trị tại thời điểm chụp và có thể đã thay đổi.',
    2: 'Bản gốc đã có sáu KPI, biểu đồ, so sánh mô hình và tự làm mới. Các số trên hình thuộc snapshot ngày 23/10/2026, dùng để minh họa cách đọc.',
    3: 'Hình này chỉ là tab giao dịch: bản gốc có bảng, nhưng chưa có luồng lọc kết hợp và inspector riêng theo Event ID. Không nên khái quát thành toàn dashboard cũ không có biểu đồ; trang Overview gốc đã có biểu đồ vận hành.',
    4: 'Mỗi thay đổi xuất phát từ một nhu cầu sử dụng: tìm thông tin cần theo dõi, thu hẹp giao dịch và hiểu đúng phạm vi của từng chỉ số. Lợi ích thao tác cần được đo thêm.',
    5: '60 micro-batch: b?n c? tr?nh b?y b?ng history; duration chart n?m ri?ng tr?n Overview. Workspace gh?p ???ng duration v?i b?ng l?ch s? trong c?ng expander ?? v?a xem xu h??ng v?a tra t?ng batch. Bi?u ?? duration v?n ?? c? ? Overview c?, v? v?y thay ??i l? c?ch gh?p n?i dung, kh?ng ph?i bi?u ?? ho?n to?n m?i.',
    6: 'Ảnh số 1 là bộ lọc trên dashboard đang chạy. Ảnh số 2 là bản ghi thật trong snapshot phát lại để minh họa vùng chi tiết. Bộ lọc chỉ tác động tập đã nạp, không đổi KPI toàn đợt chạy hay ngưỡng mô hình.',
    7: '? m?c 60 micro-batch, b?n c? hi?n th? b?ng history; bi?u ?? duration ? Overview ???c tr?nh b?y t?ch ri?ng. Workspace ??t bi?u ?? ???ng duration ngay c?ng b?ng l?ch s? trong expander. C? th? quan s?t xu h??ng v? sau ?? tra t?ng d?ng; c?n cu?n ??n m?c r?i b?m m?. To?n dashboard c? v?n c? bi?u ?? v?n h?nh.',
    8: 'Thu gọn hero, tra cứu lịch sử phía máy chủ và lựa chọn ngôn ngữ là đề xuất. Nên đánh giá cùng tác vụ, cùng dữ liệu và cùng thiết bị để biết người dùng hoàn thành đúng và nhanh hơn hay không.',
}


def replace_figure(slide, index, replacement):
    figures = list(re.finditer(r'<figure class="shot[^\"]*">.*?</figure>', slide, flags=re.DOTALL))
    if index >= len(figures):
        raise ValueError(f'Figure {index} missing')
    match = figures[index]
    return slide[:match.start()] + replacement + slide[match.end():]


def update_slide(number, text):
    if number == 1:
        text = replace_figure(text, 0, figure('live-overview-top.png',
            'Workspace đang chạy • ảnh chụp ngày 29/10/2026', (65, 55, 1470, 525)))
        text = text.replace('Hình kính là trang trí. RUNNING trong ảnh là trạng thái đã lưu.',
                            'Hình kính là trang trí. Giá trị trong ảnh thay đổi theo thời gian.')
        text = text.replace('Ảnh thật từ snapshot replay • Chú thích được phủ lên ảnh, không thay số liệu.',
                            'Ảnh dashboard đang chạy tại thời điểm chụp • Không dùng số liệu ảnh để so sánh hiệu năng.')
    elif number == 5:
        text = replace_figure(text, 0, figure('live-overview-charts.png',
            '1 • Overview đang chạy • biểu đồ vận hành', (65, 110, 1470, 950)))
        text = replace_figure(text, 1, figure('live-metrics.png',
            '10 nhóm chỉ số • ảnh dashboard đang chạy', (65, 110, 1470, 920)))
        text = replace_figure(text, 2, figure('live-business.png',
            '2 • So sánh rule–model • dashboard đang chạy', (65, 115, 1470, 430), [(2, 72, 130, 850, 385)]))
        text = text.replace('Bốn nhóm: tổng quan vận hành, chỉ số, gian lận và nghiệp vụ, giao dịch',
                            'Bốn mục: Live Control Room, Metrics theo 10 tracks, Fraud &amp; Business, New data streams')
        text = text.replace('Ảnh thật từ snapshot replay • Chú thích được phủ lên ảnh, không thay số liệu. Nhãn điều hướng trong mã hiện tại khác bộ ảnh dashboard-english.',
                            'Ảnh dashboard đang chạy ngày 29/10/2026, được chụp lần lượt • Các số có thể thay đổi.')
    elif number == 6:
        text = replace_figure(text, 0, figure('live-page-4.png',
            '1 • Bộ lọc trên dashboard màu hồng đang chạy', (65, 690, 1470, 390), [(1, 71, 700, 1457, 375)]))
        text = text.replace('2 • Một ID có thật: vùng chọn, nút CSV và chi tiết giao dịch',
                            '2 • Ví dụ chọn ID và chi tiết • snapshot phát lại')
        text = text.replace('Ảnh thật từ snapshot replay • Chú thích được phủ lên ảnh, không thay số liệu. Nhãn điều hướng trong mã hiện tại khác bộ ảnh dashboard-english.',
                            'Ảnh 1: dashboard đang chạy • Ảnh 2: snapshot phát lại ngày 23/10/2026.')
    elif number == 7:
        text = text.replace('Cũ • Control Room gốc, 1600 × 1100',
                            'Cũ • Control Room gốc • snapshot 23/10')
        text = text.replace('Mới • Workspace trong bộ ảnh đối chiếu, 1600 × 1100',
                            'Mới • Workspace ở mốc ảnh đối chiếu • cùng snapshot')
        text = text.replace('Cùng snapshot. Sáu KPI khớp trên bốn cặp trang trong bằng chứng lưu. Không có benchmark render hoặc tác vụ.',
                            'Cùng snapshot 23/10 để so sánh bố cục. Nhãn Workspace trong ảnh là phiên bản lưu trước đó.')
        text = text.replace('Ảnh thật từ snapshot replay • Chú thích được phủ lên ảnh, không thay số liệu.',
                            'Ảnh cùng snapshot 23/10 • Xem dashboard đang chạy ở slide 1, 5 và 6 • Chưa có benchmark tác vụ.')
    elif number == 8:
        text = text.replace('Workspace • 390 × 844 • ảnh replay',
                            'Workspace mobile • 390 × 844 • ảnh replay 23/10')
    # The original editable paragraphs are never replaced or reordered. Existing
    # browser-local edits remain mapped to those paragraphs on the next reload.
    extra = ('<h3 class="running-comparison-heading">Gợi ý bổ sung khi thuyết trình</h3>'
             '<p class="running-comparison-caption">Phần này có thể dùng thêm khi cần, ngoài thời lượng chính.</p>'
             f'<p class="spoken running-comparison-extra">{html.escape(EXTRA[number])}</p>')
    text = re.sub(r'<h3 class="running-comparison-heading">.*?</p><p class="spoken running-comparison-extra">.*?</p>', '', text, flags=re.DOTALL)
    marker = '<p class="status"><strong>Mức độ bằng chứng:'
    if marker not in text:
        raise ValueError(f'Missing evidence marker in slide {number}')
    return text.replace(marker, extra + marker, 1)


def main():
    original = OUT.read_text(encoding='utf-8')
    pattern = re.compile(r'<article id="slide-(\d+)".*?</article>', re.DOTALL)
    slides = pattern.findall(original)
    if slides != list('12345678'):
        raise ValueError(f'Unexpected slide order: {slides}')
    updated = pattern.sub(lambda m: update_slide(int(m.group(1)), m.group(0)), original)
    intro_old = 'Ảnh dashboard dùng cùng snapshot pipeline đã lưu ngày 23/10/2026, phát lại trong bộ nhớ.'
    intro_new = ('Cặp ảnh so sánh ở slide 7 dùng cùng snapshot ngày 23/10/2026 phát lại trong bộ nhớ. '
                 'Các ảnh dashboard màu hồng ở slide 1, 5 và 6 được chụp từ hệ thống đang chạy ngày 29/10/2026; '
                 'giá trị trong các ảnh này thay đổi theo thời gian và không dùng để so sánh hiệu năng.')
    if intro_old in updated:
        updated = updated.replace(intro_old, intro_new, 1)
    if updated.count('<img ') != original.count('<img '):
        raise ValueError('Image count unexpectedly changed')
    if updated.count('class="spoken running-comparison-extra"') != 8:
        raise ValueError('Expected eight additional explanations')
    OUT.write_text(updated, encoding='utf-8')
    print('Updated live dashboard images and comparison explanations on eight slides.')


if __name__ == '__main__':
    main()
